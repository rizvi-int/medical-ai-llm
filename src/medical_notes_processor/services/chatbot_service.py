from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from typing import Optional, List, Dict, Any
import logging
import httpx

from ..core.config import settings

logger = logging.getLogger(__name__)


class MedicalChatbot:
    """
    Agent-based chatbot for medical notes with tool calling capabilities.

    The LLM can intelligently call tools to:
    - List available documents
    - Get document content
    - Extract structured data with ICD-10/RxNorm codes
    - Summarize medical notes
    - Query RAG system for relevant information
    """

    def __init__(self):
        """Initialize chatbot with OpenAI LLM and tools."""
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.0,
        )
        self.api_base = "http://localhost:8000"
        self.tools = self._create_tools()
        self.agent = self._create_agent()

    def _create_tools(self) -> List:
        """Create tools that the agent can use."""

        @tool
        async def get_documents_list() -> str:
            """Get list of all available medical document IDs."""
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{self.api_base}/documents")
                    if response.status_code == 200:
                        doc_ids = response.json()
                        return f"Available document IDs: {', '.join(map(str, doc_ids))}"
                    return "Failed to retrieve document list"
            except Exception as e:
                logger.error(f"Error getting documents list: {str(e)}")
                return f"Error: {str(e)}"

        @tool
        async def get_document_content(document_id: int) -> str:
            """Get the full content of a specific medical document by ID."""
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{self.api_base}/documents/{document_id}")
                    if response.status_code == 200:
                        doc = response.json()
                        return f"Document {doc['id']} - {doc['title']}:\n{doc['content']}"
                    return f"Document {document_id} not found"
            except Exception as e:
                logger.error(f"Error getting document {document_id}: {str(e)}")
                return f"Error: {str(e)}"

        @tool
        async def extract_structured_data(text: str) -> str:
            """
            Extract structured medical data from text including ICD-10 codes, RxNorm codes,
            diagnoses, medications, and procedures using the medical coding agent.
            """
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.api_base}/extract_structured",
                        json={"text": text}
                    )
                    if response.status_code == 200:
                        data = response.json()
                        structured = data.get("structured_data", {})

                        parts = []

                        if structured.get("diagnoses"):
                            parts.append("Diagnoses:")
                            for diag in structured["diagnoses"]:
                                code = diag.get("icd10_code", "N/A")
                                name = diag.get("name", "Unknown")
                                parts.append(f"  - {name} (ICD-10: {code})")

                        if structured.get("medications"):
                            parts.append("\nMedications:")
                            for med in structured["medications"]:
                                code = med.get("rxnorm_code", "N/A")
                                name = med.get("name", "Unknown")
                                parts.append(f"  - {name} (RxNorm: {code})")

                        if structured.get("procedures"):
                            parts.append("\nProcedures:")
                            for proc in structured["procedures"]:
                                parts.append(f"  - {proc.get('name', 'Unknown')}")

                        return "\n".join(parts) if parts else "No structured data extracted"

                    return "Failed to extract structured data"
            except Exception as e:
                logger.error(f"Error extracting structured data: {str(e)}")
                return f"Error: {str(e)}"

        @tool
        async def summarize_medical_note(text: str) -> str:
            """Generate a concise summary of a medical note highlighting key clinical information."""
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.api_base}/summarize_note",
                        json={"text": text}
                    )
                    if response.status_code == 200:
                        data = response.json()
                        return data.get("summary", "No summary generated")
                    return "Failed to generate summary"
            except Exception as e:
                logger.error(f"Error summarizing note: {str(e)}")
                return f"Error: {str(e)}"

        @tool
        async def search_medical_documents(query: str) -> str:
            """
            Search across all medical documents using semantic similarity (RAG).
            Returns relevant document chunks based on the query.
            """
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.api_base}/answer_question",
                        json={"question": query, "top_k": 3}
                    )
                    if response.status_code == 200:
                        data = response.json()
                        answer = data.get("answer", "")
                        sources = data.get("sources", [])

                        result = f"Answer: {answer}\n\nSources:\n"
                        for src in sources:
                            result += f"- Document {src['document_id']}: {src['title']}\n"

                        return result
                    return "Failed to search documents"
            except Exception as e:
                logger.error(f"Error searching documents: {str(e)}")
                # Fallback: return all documents
                return "RAG search unavailable. Use get_documents_list and get_document_content instead."

        return [
            get_documents_list,
            get_document_content,
            extract_structured_data,
            summarize_medical_note,
            search_medical_documents
        ]

    def _create_agent(self) -> AgentExecutor:
        """Create the LangChain agent with tools."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a medical information assistant with access to medical documents and tools.

When users ask questions:
1. Use search_medical_documents for general questions to find relevant information
2. Use get_documents_list to see available documents
3. Use get_document_content to read specific documents
4. Use extract_structured_data to get ICD-10 codes, RxNorm codes, and structured medical data
5. Use summarize_medical_note to create concise summaries

IMPORTANT:
- When asked about ICD-10 codes, diagnoses, or medications, ALWAYS use extract_structured_data
- Answer based ONLY on the tools and provided data
- Be precise and cite sources
- If information is not available, say so clearly"""),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_openai_tools_agent(self.llm, self.tools, prompt)
        return AgentExecutor(agent=agent, tools=self.tools, verbose=True)

    async def chat(self, user_message: str, note_id: Optional[int] = None) -> str:
        """
        Process user message through the agent.

        Args:
            user_message: User's question
            note_id: Optional document ID to focus on

        Returns:
            Agent's response
        """
        try:
            # Add note context if provided
            if note_id:
                user_message = f"[Context: User is asking about document {note_id}] {user_message}"

            result = await self.agent.ainvoke({"input": user_message})
            return result["output"]

        except Exception as e:
            logger.error(f"Error in chat: {str(e)}")
            return f"Error processing query: {str(e)}"


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
