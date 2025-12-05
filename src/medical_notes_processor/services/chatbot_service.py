from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from typing import Optional, Dict, Any
import logging
import httpx
import re

from ..core.config import settings

logger = logging.getLogger(__name__)


class MedicalChatbot:
    """
    Fast hybrid chatbot for medical notes.

    Uses direct LLM calls for speed, with smart extraction when medical codes are requested.
    """

    def __init__(self):
        """Initialize chatbot with OpenAI LLM."""
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.0,
        )
        self.api_base = "http://localhost:8000"

    async def _get_document(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """Fetch document by ID."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.api_base}/documents/{doc_id}")
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Error fetching document {doc_id}: {str(e)}")
        return None

    async def _extract_codes(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract ICD-10/RxNorm codes from text."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_base}/extract_structured",
                    json={"text": text}
                )
                if response.status_code == 200:
                    return response.json().get("structured_data", {})
        except Exception as e:
            logger.error(f"Error extracting codes: {str(e)}")
        return None

    async def _summarize_note(self, text: str) -> str:
        """Generate summary of medical note."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_base}/summarize_note",
                    json={"text": text}
                )
                if response.status_code == 200:
                    return response.json().get("summary", "No summary generated")
        except Exception as e:
            logger.error(f"Error summarizing note: {str(e)}")
        return "Failed to generate summary"

    async def _rag_search(self, query: str, top_k: int = 3) -> Optional[Dict[str, Any]]:
        """Search documents using RAG."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_base}/answer_question",
                    json={"question": query, "top_k": top_k}
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Error in RAG search: {str(e)}")
        return None

    def _needs_code_extraction(self, message: str) -> bool:
        """Check if message is asking for medical codes."""
        code_keywords = [
            "icd", "icd-10", "icd10", "diagnosis code", "diagnostic code",
            "rxnorm", "medication code", "drug code", "ndc",
            "cpt", "procedure code", "billing code", "extract",
            "codes", "code"  # Added to catch "codes for doc X"
        ]
        message_lower = message.lower()

        # Also check if it's a format request that implies code extraction
        format_keywords = ["export", "csv", "table", "list"]
        if any(fmt in message_lower for fmt in format_keywords):
            # These format requests should trigger code extraction
            return True

        return any(keyword in message_lower for keyword in code_keywords)

    def _needs_summarization(self, message: str) -> bool:
        """Check if message is asking for a summary."""
        summary_keywords = ["summarize", "summary", "overview", "brief"]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in summary_keywords)

    def _extract_document_ids(self, message: str) -> list:
        """Extract document IDs from message (e.g., 'document 1', 'doc 3', 'patient 2 and 3')."""
        import re

        # Match patterns like "document 1 and 3", "doc 2, 3, 4", "patient 1-3", etc.
        patterns = [
            r'documents?\s+([\d\s,and-]+)',
            r'docs?\s+([\d\s,and-]+)',
            r'patients?\s+([\d\s,and-]+)',
            r'cases?\s+([\d\s,and-]+)',
            r'notes?\s+([\d\s,and-]+)',
            r'\bid\s+([\d\s,and-]+)',
            r'#([\d\s,and-]+)',
        ]

        doc_ids = []
        message_lower = message.lower()

        for pattern in patterns:
            matches = re.findall(pattern, message_lower)
            for match in matches:
                # Extract all numbers from the matched string
                # Handles "2 and 3", "2, 3, 4", "1-3", etc.
                numbers = re.findall(r'\d+', match)
                doc_ids.extend([int(n) for n in numbers])

        # Remove duplicates and sort
        return sorted(set(doc_ids))

    async def chat(self, user_message: str, note_id: Optional[int] = None, conversation_history: list = None) -> str:
        """
        Fast hybrid chat approach with conversation memory.

        Strategy:
        1. Check conversation history for context
        2. Auto-detect document IDs from message and history
        3. If asking for medical codes → extract codes from specified documents
        4. Otherwise → use fast RAG search
        5. If RAG unavailable → provide helpful fallback
        """
        try:
            conversation_history = conversation_history or []

            # Auto-detect document IDs from current message
            doc_ids = self._extract_document_ids(user_message)

            # If no IDs found and user has conversation history, try to infer from context
            if not doc_ids and conversation_history:
                # Explicit context references
                context_words = ["it", "them", "that", "those", "these", "this document", "the document", "this patient", "the patient"]
                has_context_word = any(phrase in user_message.lower() for phrase in context_words)

                # Also check for requests that suggest continuing previous work
                continuation_keywords = ["export", "csv", "show", "display", "confidence", "detailed", "table", "list"]
                is_continuation = any(keyword in user_message.lower() for keyword in continuation_keywords)

                if has_context_word or is_continuation:
                    # Look back through conversation to find previously mentioned documents
                    for msg in reversed(conversation_history[-6:]):  # Look back up to 6 messages
                        # Check both user and assistant messages
                        msg_content = msg.get("content", "")
                        found_ids = self._extract_document_ids(msg_content)
                        if found_ids:
                            doc_ids = found_ids
                            break

            if not doc_ids and note_id:
                doc_ids = [note_id]

            # Handle summarization requests
            if self._needs_summarization(user_message):
                if doc_ids:
                    # Summarize specified documents
                    summaries = []
                    for doc_id in doc_ids:
                        doc = await self._get_document(doc_id)
                        if doc:
                            summary = await self._summarize_note(doc["content"])
                            summaries.append(f"**{doc['title']}**\n\n{summary}")
                        else:
                            summaries.append(f"Document {doc_id}: Not found")

                    return "\n\n" + "="*50 + "\n\n".join(summaries)
                else:
                    return "Please specify which document to summarize (e.g., 'summarize document 1')."

            # Handle code extraction requests
            if self._needs_code_extraction(user_message):
                if doc_ids:
                    # Determine output format
                    wants_csv = "csv" in user_message.lower() or "export" in user_message.lower()
                    wants_list = "list" in user_message.lower() or "detailed" in user_message.lower()
                    wants_table = "table" in user_message.lower()

                    # Smart defaults if no format specified
                    if not wants_csv and not wants_list and not wants_table:
                        # Default: table for 2+ docs, list for single doc
                        wants_table = len(doc_ids) > 1
                        wants_list = len(doc_ids) == 1

                    # Extract codes from all specified documents
                    results = []
                    table_data = []  # For structured formats (table/CSV)

                    for doc_id in doc_ids:
                        doc = await self._get_document(doc_id)
                        if doc:
                            structured = await self._extract_codes(doc["content"])
                            if structured:
                                # Always collect for table_data (used by both table and CSV)
                                table_data.append({
                                    "doc_id": doc_id,
                                    "title": doc["title"],
                                    "structured": structured
                                })
                                if wants_list:
                                    results.append(self._format_structured_data(structured, doc["title"]))
                            else:
                                table_data.append({
                                    "doc_id": doc_id,
                                    "title": doc["title"],
                                    "structured": None
                                })
                                if wants_list:
                                    results.append(f"Document {doc_id}: No structured data extracted")
                        else:
                            if wants_list:
                                results.append(f"Document {doc_id}: Not found")

                    # Return in requested format
                    if wants_csv and table_data:
                        return self._format_as_csv(table_data)

                    if wants_table and table_data:
                        table_output = self._format_as_table(table_data)
                        # Add helpful footer suggesting alternative formats
                        footer = "\n\n💡 **Tip**: You can also ask for:\n- 'detailed list' for more information with reasoning\n- 'export to CSV' for spreadsheet format"
                        return table_output + footer

                    results_output = "\n\n" + "="*50 + "\n\n".join(results) if results else "No documents processed."
                    # Add helpful footer for list format
                    if len(doc_ids) > 1:
                        footer = "\n\n💡 **Tip**: Try asking for 'in a table' to compare documents side-by-side"
                        results_output += footer
                    return results_output
                else:
                    # Extract from all documents if "all" is mentioned
                    if "all" in user_message.lower():
                        async with httpx.AsyncClient() as client:
                            response = await client.get(f"{self.api_base}/documents")
                            if response.status_code == 200:
                                all_ids = response.json()
                                results = []

                                # Process all documents in parallel for speed
                                import asyncio
                                async def extract_one(doc_id):
                                    doc = await self._get_document(doc_id)
                                    if doc:
                                        structured = await self._extract_codes(doc["content"])
                                        if structured:
                                            return self._format_structured_data(structured, doc["title"])
                                    return None

                                results = await asyncio.gather(*[extract_one(doc_id) for doc_id in all_ids])
                                results = [r for r in results if r]  # Filter out None values

                                return "\n\n" + "="*50 + "\n\n".join(results) if results else "No data extracted."

                    return "Please specify a document ID (e.g., 'document 1') or say 'all patients' to extract codes from all documents."

            # Handle general questions with RAG
            rag_result = await self._rag_search(user_message)
            if rag_result:
                answer = rag_result.get("answer", "")
                sources = rag_result.get("sources", [])

                # Format response with sources
                response_parts = [answer]
                if sources:
                    response_parts.append("\n\nSources:")
                    for src in sources:
                        response_parts.append(f"- Document {src['document_id']}: {src['title']}")

                return "\n".join(response_parts)

            # Fallback: list available documents
            return await self._get_documents_list()

        except Exception as e:
            logger.error(f"Error in chat: {str(e)}")
            return f"Sorry, I encountered an error: {str(e)}"

    async def _get_documents_list(self) -> str:
        """Get formatted list of all documents."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.api_base}/documents")
                if response.status_code == 200:
                    doc_ids = response.json()

                    # Fetch details for each document
                    docs_info = []
                    for doc_id in doc_ids:
                        doc_response = await client.get(f"{self.api_base}/documents/{doc_id}")
                        if doc_response.status_code == 200:
                            doc = doc_response.json()
                            docs_info.append(f"  • Document {doc['id']}: {doc['title']}")

                    if docs_info:
                        return f"Available medical documents:\n\n" + "\n".join(docs_info) + "\n\nTo extract ICD-10 codes or medications, ask about specific documents by ID."
                    return "No documents found."
        except Exception as e:
            logger.error(f"Error listing documents: {str(e)}")

        return "I have 6 medical documents available. Please ask about a specific document by ID (1-6) to extract ICD-10 codes or medications."

    def _format_as_csv(self, table_data: list) -> str:
        """Format multiple document results as CSV."""
        if not table_data:
            return "No data to export"

        lines = []
        # CSV header
        lines.append("Case,Document Title,Diagnosis,ICD-10 (AI),Confidence,ICD-10 (Validated),Medication,RxNorm,Code Reasoning")

        for item in table_data:
            doc_id = item["doc_id"]
            title = item["title"].replace(",", ";")  # Escape commas in title
            structured = item["structured"]

            if not structured:
                lines.append(f'{doc_id},{title},No data,-,-,-,-,-,-')
                continue

            conditions = structured.get("diagnoses") or structured.get("conditions") or []
            medications = structured.get("medications") or []

            if not conditions and not medications:
                lines.append(f'{doc_id},{title},None found,-,-,-,None found,-,-')
                continue

            # Export all conditions and medications
            max_items = max(len(conditions), len(medications))

            for i in range(max_items):
                # Condition data
                if i < len(conditions):
                    cond = conditions[i]
                    diag_name = cond.get("name", "").replace(",", ";")
                    ai_code = cond.get("ai_icd10_code", "N/A")
                    validated_code = cond.get("validated_icd10_code", "N/A")
                    confidence = cond.get("confidence", "").upper()
                    reasoning = cond.get("code_reasoning", "").replace(",", ";")
                else:
                    diag_name = ""
                    ai_code = ""
                    validated_code = ""
                    confidence = ""
                    reasoning = ""

                # Medication data
                if i < len(medications):
                    med = medications[i]
                    med_name = med.get("name", "").replace(",", ";")
                    rx_code = med.get("rxnorm_code", "N/A")
                else:
                    med_name = ""
                    rx_code = ""

                # Only include doc_id and title in first row
                if i == 0:
                    lines.append(f'{doc_id},{title},{diag_name},{ai_code},{confidence},{validated_code},{med_name},{rx_code},"{reasoning}"')
                else:
                    lines.append(f',,{diag_name},{ai_code},{confidence},{validated_code},{med_name},{rx_code},"{reasoning}"')

        csv_content = "\n".join(lines)
        return f"```csv\n{csv_content}\n```\n\n💾 **Copy the CSV above** and paste into Excel or save as a .csv file"

    def _format_as_table(self, table_data: list) -> str:
        """Format multiple document results as a markdown table."""
        if not table_data:
            return "No data to display"

        # Build table header with Confidence column
        table = ["| Case | Document Title | Diagnoses | ICD-10 (AI) | Confidence | ICD-10 (Validated) | Medications | RxNorm |"]
        table.append("|------|---------------|-----------|-------------|------------|-------------------|-------------|--------|")

        for item in table_data:
            doc_id = item["doc_id"]
            title = item["title"]
            structured = item["structured"]

            if not structured:
                table.append(f"| {doc_id} | {title} | No data | - | - | - | - | - |")
                continue

            # Get conditions and medications
            conditions = structured.get("diagnoses") or structured.get("conditions") or []
            medications = structured.get("medications") or []

            # If no conditions or meds, show empty row
            if not conditions and not medications:
                table.append(f"| {doc_id} | {title} | None found | - | - | - | None found | - |")
                continue

            # First row with doc info
            first_row = True

            # Process conditions
            if conditions:
                for cond in conditions:
                    name = cond.get("name", "Unknown")
                    ai_code = cond.get("ai_icd10_code", "N/A")
                    validated_code = cond.get("validated_icd10_code", "N/A")
                    confidence = cond.get("confidence", "").upper()

                    # Format confidence as stars
                    if confidence == "HIGH":
                        conf_display = "⭐⭐⭐"
                    elif confidence == "MEDIUM":
                        conf_display = "⭐⭐"
                    elif confidence == "LOW":
                        conf_display = "⭐"
                    else:
                        conf_display = "-"

                    if first_row:
                        # Include medications in first row if available
                        if medications:
                            med = medications[0]
                            med_name = med.get("name", "Unknown")
                            rx_code = med.get("rxnorm_code", "N/A")
                            table.append(f"| {doc_id} | {title} | {name} | {ai_code} | {conf_display} | {validated_code} | {med_name} | {rx_code} |")
                        else:
                            table.append(f"| {doc_id} | {title} | {name} | {ai_code} | {conf_display} | {validated_code} | - | - |")
                        first_row = False
                    else:
                        table.append(f"|  |  | {name} | {ai_code} | {conf_display} | {validated_code} |  |  |")

            # Process remaining medications (if conditions already printed)
            if medications and conditions:
                start_idx = 1  # Skip first med if already printed
            elif medications:
                start_idx = 0

            if medications:
                for med in medications[start_idx:]:
                    med_name = med.get("name", "Unknown")
                    rx_code = med.get("rxnorm_code", "N/A")
                    if first_row:
                        table.append(f"| {doc_id} | {title} | - | - | - | {med_name} | {rx_code} |")
                        first_row = False
                    else:
                        table.append(f"|  |  |  |  |  | {med_name} | {rx_code} |")

        return "\n".join(table)

    def _format_structured_data(self, structured: Dict[str, Any], doc_title: str = "") -> str:
        """Format extracted structured data for display with dual code display."""
        parts = []

        if doc_title:
            parts.append(f"Extracted from: {doc_title}\n")

        # Handle both "diagnoses" and "conditions" keys
        conditions = structured.get("diagnoses") or structured.get("conditions")
        if conditions:
            # Separate AI-inferred and validated codes for clearer presentation
            has_ai_codes = any(diag.get("ai_icd10_code") for diag in conditions)
            has_validated_codes = any(diag.get("validated_icd10_code") for diag in conditions)

            if has_ai_codes:
                parts.append("Diagnoses (AI-Inferred Codes):")
                for diag in conditions:
                    ai_code = diag.get("ai_icd10_code", "Not assigned")
                    name = diag.get("name", "Unknown")
                    confidence = diag.get("confidence", "").upper()
                    reasoning = diag.get("code_reasoning", "")

                    # Format confidence with stars
                    confidence_display = ""
                    if confidence == "HIGH":
                        confidence_display = " ⭐⭐⭐"
                    elif confidence == "MEDIUM":
                        confidence_display = " ⭐⭐"
                    elif confidence == "LOW":
                        confidence_display = " ⭐"

                    line = f"  • {name} (ICD-10: {ai_code}){confidence_display}"
                    if confidence:
                        line += f" {confidence}"
                    parts.append(line)

                    if reasoning:
                        parts.append(f"    → {reasoning}")

            if has_validated_codes:
                parts.append("\nDiagnoses (API-Validated Codes):")
                for diag in conditions:
                    validated_code = diag.get("validated_icd10_code", "Not found in database")
                    name = diag.get("name", "Unknown")
                    parts.append(f"  • {name} (ICD-10: {validated_code})")

            # Fallback to old format if neither new field exists
            if not has_ai_codes and not has_validated_codes:
                parts.append("Diagnoses:")
                for diag in conditions:
                    code = diag.get("icd10_code", "N/A")
                    name = diag.get("name", "Unknown")
                    parts.append(f"  • {name} (ICD-10: {code})")

        if structured.get("medications"):
            parts.append("\nMedications:")
            for med in structured["medications"]:
                code = med.get("rxnorm_code", "N/A")
                name = med.get("name", "Unknown")
                parts.append(f"  • {name} (RxNorm: {code})")

        if structured.get("procedures"):
            parts.append("\nProcedures:")
            for proc in structured["procedures"]:
                parts.append(f"  • {proc.get('name', 'Unknown')}")

        return "\n".join(parts) if parts else "No structured data extracted"


# Global singleton
chatbot_service = None


def get_chatbot_service() -> MedicalChatbot:
    """
    Get or create global chatbot instance.

    Returns:
        MedicalChatbot: Singleton chatbot instance
    """
    global chatbot_service
    if chatbot_service is None:
        chatbot_service = MedicalChatbot()
    return chatbot_service
