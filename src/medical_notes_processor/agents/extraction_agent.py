from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from typing import Dict, Any
import json
import logging
from openai import AsyncOpenAI
from pydantic import BaseModel

from ..core.config import settings
from ..models.schemas import StructuredMedicalData
from ..utils.external_apis import external_api_client

logger = logging.getLogger(__name__)


class MedicalExtractionAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.0,
        )
        # Use native OpenAI client for structured outputs
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def extract_structured_data(self, medical_note: str) -> StructuredMedicalData:
        """
        Multi-step agent that:
        1. Extracts raw structured data from medical note
        2. Enriches medications with RxNorm codes
        3. Enriches conditions with ICD-10 codes
        4. Returns validated structured data
        """
        # Step 1: Extract raw data using LLM
        raw_data = await self._extract_raw_data(medical_note)

        # Step 2: Enrich medications with RxNorm codes
        if raw_data.get("medications"):
            # raw_data is already a dict from LLM, not Pydantic models
            enriched_meds = await external_api_client.enrich_medications(
                raw_data["medications"]
            )
            raw_data["medications"] = enriched_meds

        # Step 3: Enrich conditions with ICD-10 codes
        if raw_data.get("conditions"):
            enriched_conditions = await external_api_client.enrich_conditions(
                raw_data["conditions"]
            )
            raw_data["conditions"] = enriched_conditions

        # Step 4: Validate and return structured data
        structured_data = StructuredMedicalData(**raw_data)
        return structured_data

    async def _extract_raw_data(self, medical_note: str) -> Dict[str, Any]:
        """Use LLM with structured outputs to extract data from medical note."""
        system_prompt = """You are a medical information extraction expert with expertise in medical coding.
Extract structured data from the medical note.

Extract the following information:
1. Patient information (name, DOB, gender, patient_id)
2. Encounter date
3. Chief complaint
4. Subjective findings
5. Objective findings
6. Vital signs (BP, HR, temperature, respiratory rate, O2 saturation)
7. Conditions/diagnoses (name, status, suggested_icd10_code)
8. Medications (name, dosage, frequency, route)
9. Lab results (test_name, value, unit, reference_range)
10. Assessment
11. Plan actions (action_type, description, timing)

IMPORTANT for conditions: Assign the most appropriate ICD-10 code based on clinical reasoning.
- For routine encounters: Use Z codes (e.g., Z00.00 for general adult exam)
- For family history: Use Z8x codes (e.g., Z83.42 for family history of hyperlipidemia)
- For screening/observations: Use appropriate codes (e.g., E66.3 for overweight)
- Be clinically intelligent - assign codes even when not explicitly stated in documentation

For each condition, also provide:
- confidence: "high", "medium", or "low" based on documentation clarity
- code_reasoning: brief explanation (1 sentence) for the code assignment

Confidence Levels:
- HIGH: Explicitly stated diagnosis with clear documentation
- MEDIUM: Implied or inferred from context, symptoms, or medications
- LOW: Uncertain or ambiguous, may need review"""

        try:
            # Try structured outputs with Pydantic (works with gpt-4o-2024-08-06+)
            try:
                completion = await self.openai_client.beta.chat.completions.parse(
                    model=settings.openai_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Medical Note:\n\n{medical_note}"}
                    ],
                    response_format=StructuredMedicalData,
                    temperature=0.0,
                )
                parsed_data = completion.choices[0].message.parsed
                return parsed_data.model_dump()

            except Exception as struct_error:
                # Fallback to JSON mode with manual parsing for older models
                logger.warning(f"Structured outputs not supported, using JSON mode: {str(struct_error)}")

                # Add explicit JSON schema to prompt for json_object mode
                schema_prompt = system_prompt + """\n\nReturn valid JSON with this exact structure:
{
  "patient": {"name": "string", "date_of_birth": "YYYY-MM-DD", "gender": "string", "patient_id": "string"},
  "encounter_date": "YYYY-MM-DD",
  "chief_complaint": "string",
  "subjective": "string",
  "objective": "string",
  "vital_signs": {"blood_pressure": "string", "heart_rate": "string", "temperature": "string", "respiratory_rate": "string", "oxygen_saturation": "string"},
  "conditions": [{"name": "string", "status": "string", "suggested_icd10_code": "string", "confidence": "high|medium|low", "code_reasoning": "string"}],
  "medications": [{"name": "string", "dosage": "string", "frequency": "string", "route": "string"}],
  "lab_results": [{"test_name": "string", "value": "string", "unit": "string", "reference_range": "string"}],
  "assessment": "string",
  "plan_actions": [{"action_type": "string", "description": "string", "timing": "string"}]
}"""

                completion = await self.openai_client.chat.completions.create(
                    model=settings.openai_model,
                    messages=[
                        {"role": "system", "content": schema_prompt},
                        {"role": "user", "content": f"Medical Note:\n\n{medical_note}"}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                )

                content = completion.choices[0].message.content
                data = json.loads(content)

                # Validate with Pydantic
                validated = StructuredMedicalData(**data)
                return validated.model_dump()

        except Exception as e:
            logger.error(f"Error extracting structured data: {str(e)}")
            raise


extraction_agent = MedicalExtractionAgent()
