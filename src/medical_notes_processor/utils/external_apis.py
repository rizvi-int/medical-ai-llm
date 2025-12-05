"""
External API client for medical code lookups.

This module provides a client for interacting with external medical terminology APIs
to enrich medical data with standardized codes:
- NLM RxNorm API for medication codes
- NLM Clinical Tables API for ICD-10 diagnosis codes

The client includes automatic retry logic with exponential backoff for resilience.
"""

import httpx
from typing import Optional, Dict, Any, List
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

from ..core.config import settings

logger = logging.getLogger(__name__)


class ExternalAPIClient:
    """
    Client for external medical terminology APIs.

    This class provides methods to lookup standardized medical codes from
    authoritative sources:
    - RxNorm codes for medications (from NLM)
    - ICD-10 codes for diagnoses (from Clinical Tables)

    All methods include automatic retry logic with exponential backoff
    to handle transient network failures.

    Attributes:
        nlm_base_url (str): Base URL for NLM RxNorm API
        clinicaltables_base_url (str): Base URL for Clinical Tables API
        timeout (float): Request timeout in seconds
    """

    def __init__(self):
        """Initialize the external API client with configured endpoints."""
        self.nlm_base_url = settings.nlm_api_base_url
        self.clinicaltables_base_url = settings.clinicaltables_api_base_url
        self.timeout = 30.0

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def get_rxnorm_code(self, medication_name: str) -> Optional[str]:
        """
        Get RxNorm code for a medication using NLM RxNorm API.

        RxNorm is a standardized nomenclature for clinical drugs produced by
        the National Library of Medicine. Each medication has a unique RxNorm
        Concept Unique Identifier (RxCUI).

        This method uses automatic retry with exponential backoff (max 3 attempts).

        Args:
            medication_name (str): Name of the medication (e.g., "Metformin", "Lisinopril")

        Returns:
            Optional[str]: RxNorm code (RxCUI) if found, None otherwise

        Example:
            >>> client = ExternalAPIClient()
            >>> code = await client.get_rxnorm_code("Metformin")
            >>> print(code)
            "6809"

        Note:
            Returns the first RxCUI if multiple matches are found.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.nlm_base_url}/rxcui.json"
                params = {"name": medication_name}
                response = await client.get(url, params=params)
                response.raise_for_status()

                data = response.json()
                if "idGroup" in data and "rxnormId" in data["idGroup"]:
                    rxnorm_ids = data["idGroup"]["rxnormId"]
                    if rxnorm_ids and len(rxnorm_ids) > 0:
                        return rxnorm_ids[0]

                logger.warning(f"No RxNorm code found for medication: {medication_name}")
                return None
        except Exception as e:
            logger.error(f"Error fetching RxNorm code for {medication_name}: {str(e)}")
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def get_icd10_code(self, condition_name: str) -> Optional[str]:
        """
        Get ICD-10 code for a medical condition using NLM Clinical Tables API.

        ICD-10-CM (International Classification of Diseases, 10th Revision,
        Clinical Modification) is the standard for diagnosis coding in the US.

        This method uses automatic retry with exponential backoff (max 3 attempts).

        Args:
            condition_name (str): Name of the condition (e.g., "Type 2 Diabetes", "Hypertension")

        Returns:
            Optional[str]: ICD-10-CM code if found, None otherwise

        Example:
            >>> client = ExternalAPIClient()
            >>> code = await client.get_icd10_code("Type 2 Diabetes Mellitus")
            >>> print(code)
            "E11.9"

        Note:
            Returns the first (most relevant) ICD-10 code from search results.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.clinicaltables_base_url}/icd10cm/v3/search"
                params = {
                    "sf": "code,name",
                    "terms": condition_name,
                    "maxList": 1,
                }
                response = await client.get(url, params=params)
                response.raise_for_status()

                data = response.json()
                if data and len(data) >= 4 and data[3] and len(data[3]) > 0:
                    # data[3] contains the results, each result is [code, name]
                    return data[3][0][0]

                logger.warning(f"No ICD-10 code found for condition: {condition_name}")
                return None
        except Exception as e:
            logger.error(f"Error fetching ICD-10 code for {condition_name}: {str(e)}")
            return None

    async def enrich_medications(
        self, medications: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Enrich medication data with RxNorm codes from NLM API.

        Takes a list of medication dictionaries and adds RxNorm codes to each
        by looking them up via the NLM RxNorm API.

        Args:
            medications (List[Dict[str, Any]]): List of medication dictionaries,
                each containing at minimum a "name" field

        Returns:
            List[Dict[str, Any]]: Enriched medications with "rxnorm_code" field added

        Example:
            >>> medications = [{"name": "Metformin", "dosage": "500mg"}]
            >>> enriched = await client.enrich_medications(medications)
            >>> print(enriched)
            [{"name": "Metformin", "dosage": "500mg", "rxnorm_code": "6809"}]

        Note:
            Medications without a "name" field are skipped.
            If a code cannot be found, the medication is still included without the code.
        """
        enriched = []
        for med in medications:
            if "name" in med:
                rxnorm_code = await self.get_rxnorm_code(med["name"])
                med_copy = med.copy()
                if rxnorm_code:
                    med_copy["rxnorm_code"] = rxnorm_code
                enriched.append(med_copy)
        return enriched

    async def enrich_conditions(
        self, conditions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Enrich condition/diagnosis data with ICD-10 codes from Clinical Tables API.

        Takes a list of condition dictionaries and adds ICD-10-CM codes to each
        by looking them up via the NLM Clinical Tables API. Preserves AI-suggested
        codes and adds API-validated codes for comparison.

        Args:
            conditions (List[Dict[str, Any]]): List of condition dictionaries,
                each containing at minimum a "name" field and optionally
                "suggested_icd10_code" from AI extraction

        Returns:
            List[Dict[str, Any]]: Enriched conditions with both "ai_icd10_code"
                (from LLM suggestion) and "validated_icd10_code" (from API lookup)

        Example:
            >>> conditions = [{"name": "Type 2 Diabetes", "status": "chronic", "suggested_icd10_code": "E11.9"}]
            >>> enriched = await client.enrich_conditions(conditions)
            >>> print(enriched)
            [{"name": "Type 2 Diabetes", "status": "chronic", "ai_icd10_code": "E11.9", "validated_icd10_code": "E11.9"}]

        Note:
            Conditions without a "name" field are skipped.
            If API validation fails, only AI code is present.
        """
        enriched = []
        for cond in conditions:
            if "name" in cond:
                cond_copy = cond.copy()

                # Preserve AI-suggested code
                if "suggested_icd10_code" in cond_copy:
                    cond_copy["ai_icd10_code"] = cond_copy.pop("suggested_icd10_code")

                # Get API-validated code
                validated_code = await self.get_icd10_code(cond["name"])
                if validated_code:
                    cond_copy["validated_icd10_code"] = validated_code

                enriched.append(cond_copy)
        return enriched


# Global singleton instance for use throughout the application
external_api_client = ExternalAPIClient()
