from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from typing import Dict, Any
import json
import logging

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
        """Use LLM to extract structured data from medical note."""
        system_prompt = """You are a medical information extraction expert.
Extract structured data from the medical note and return it as valid JSON.

Extract the following information:
1. Patient information (name, DOB, gender, patient_id)
2. Encounter date
3. Chief complaint
4. Subjective findings
5. Objective findings
6. Vital signs (BP, HR, temperature, respiratory rate, O2 saturation)
7. Conditions/diagnoses (name, status)
8. Medications (name, dosage, frequency, route)
9. Lab results (test_name, value, unit, reference_range)
10. Assessment
11. Plan actions (action_type, description, timing)

Return ONLY valid JSON matching this schema:
{
  "patient": {"name": "...", "date_of_birth": "YYYY-MM-DD", "gender": "...", "patient_id": "..."},
  "encounter_date": "YYYY-MM-DD",
  "chief_complaint": "...",
  "subjective": "...",
  "objective": "...",
  "vital_signs": {"blood_pressure": "...", "heart_rate": "...", "temperature": "...", "respiratory_rate": "...", "oxygen_saturation": "..."},
  "conditions": [{"name": "...", "status": "..."}],
  "medications": [{"name": "...", "dosage": "...", "frequency": "...", "route": "..."}],
  "lab_results": [{"test_name": "...", "value": "...", "unit": "...", "reference_range": "..."}],
  "assessment": "...",
  "plan_actions": [{"action_type": "...", "description": "...", "timing": "..."}]
}

If information is not present in the note, omit that field or use null/empty array."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Medical Note:\n\n{medical_note}")
        ]

        try:
            response = await self.llm.ainvoke(messages)
            content = response.content.strip()

            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            data = json.loads(content)
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {str(e)}")
            logger.error(f"Response content: {content}")
            raise ValueError(f"LLM returned invalid JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Error extracting structured data: {str(e)}")
            raise


extraction_agent = MedicalExtractionAgent()
