"""
FHIR conversion service.

This module provides services to convert structured medical data into
FHIR (Fast Healthcare Interoperability Resources) format, the global
standard for exchanging healthcare information electronically.

Converts to simplified FHIR R4 resources including:
- Patient demographics
- Conditions (diagnoses) with ICD-10 codes
- MedicationRequests with RxNorm codes
- Observations (vitals and labs) with LOINC codes
- CarePlan for treatment plans
"""

from typing import Dict, Any, List
import logging

from ..models.schemas import (
    StructuredMedicalData,
    FHIRBundle,
    FHIRPatient,
    FHIRCondition,
    FHIRMedication,
    FHIRObservation,
    FHIRCarePlan,
)

logger = logging.getLogger(__name__)


class FHIRService:
    """
    Service for converting medical data to FHIR format.

    This service transforms structured medical data (patient demographics,
    diagnoses, medications, vital signs, labs, and care plans) into
    FHIR-compliant resource representations.

    FHIR (Fast Healthcare Interoperability Resources) is the HL7 standard
    for healthcare data exchange. This implementation uses a simplified
    FHIR R4 format suitable for basic interoperability needs.
    """

    def convert_to_fhir(self, structured_data: StructuredMedicalData) -> FHIRBundle:
        """
        Convert structured medical data to FHIR bundle.

        Transforms all components of structured medical data into their
        corresponding FHIR resource types:
        - Patient → FHIR Patient resource
        - Conditions → FHIR Condition resources (with ICD-10 codes)
        - Medications → FHIR MedicationRequest resources (with RxNorm codes)
        - Vital Signs → FHIR Observation resources (with LOINC codes)
        - Lab Results → FHIR Observation resources (with LOINC codes)
        - Plan Actions → FHIR CarePlan resource

        Args:
            structured_data (StructuredMedicalData): Validated structured medical data
                containing patient info, conditions, medications, vitals, labs, and plan

        Returns:
            FHIRBundle: Bundle containing all FHIR resources

        Example:
            >>> service = FHIRService()
            >>> structured = StructuredMedicalData(...)
            >>> fhir_bundle = service.convert_to_fhir(structured)
            >>> print(fhir_bundle.patient.resourceType)
            "Patient"
        """
        fhir_bundle = FHIRBundle()

        # Convert Patient
        if structured_data.patient:
            fhir_bundle.patient = self._convert_patient(structured_data.patient)

        # Convert Conditions
        if structured_data.conditions:
            fhir_bundle.conditions = [
                self._convert_condition(cond, structured_data.patient)
                for cond in structured_data.conditions
            ]

        # Convert Medications
        if structured_data.medications:
            fhir_bundle.medications = [
                self._convert_medication(med, structured_data.patient)
                for med in structured_data.medications
            ]

        # Convert Vital Signs and Lab Results to Observations
        observations = []
        if structured_data.vital_signs:
            observations.extend(
                self._convert_vital_signs(
                    structured_data.vital_signs, structured_data.patient
                )
            )
        if structured_data.lab_results:
            observations.extend(
                self._convert_lab_results(
                    structured_data.lab_results, structured_data.patient
                )
            )
        fhir_bundle.observations = observations

        # Convert Plan to CarePlan
        if structured_data.plan_actions:
            fhir_bundle.care_plan = self._convert_care_plan(
                structured_data.plan_actions, structured_data.patient
            )

        return fhir_bundle

    def _convert_patient(self, patient_data) -> FHIRPatient:
        return FHIRPatient(
            id=patient_data.patient_id,
            name=patient_data.name,
            gender=patient_data.gender.lower() if patient_data.gender else None,
            birthDate=patient_data.date_of_birth,
        )

    def _convert_condition(self, condition_data, patient_data) -> FHIRCondition:
        patient_ref = None
        if patient_data and patient_data.patient_id:
            patient_ref = {"reference": f"Patient/{patient_data.patient_id}"}

        # Determine clinical status
        clinical_status = "active"
        if condition_data.status:
            status_lower = condition_data.status.lower()
            if "resolved" in status_lower or "inactive" in status_lower:
                clinical_status = "resolved"

        return FHIRCondition(
            code=condition_data.name,
            clinicalStatus=clinical_status,
            verificationStatus="confirmed",
            subject=patient_ref,
        )

    def _convert_medication(self, medication_data, patient_data) -> FHIRMedication:
        patient_ref = None
        if patient_data and patient_data.patient_id:
            patient_ref = {"reference": f"Patient/{patient_data.patient_id}"}

        med_codeable = {"text": medication_data.name}
        if medication_data.rxnorm_code:
            med_codeable["coding"] = [
                {
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "code": medication_data.rxnorm_code,
                    "display": medication_data.name,
                }
            ]

        dosage_instruction = None
        if any([medication_data.dosage, medication_data.frequency, medication_data.route]):
            dosage_instruction = [
                {
                    "text": f"{medication_data.dosage or ''} {medication_data.frequency or ''} {medication_data.route or ''}".strip(),
                    "route": {"text": medication_data.route} if medication_data.route else None,
                }
            ]

        return FHIRMedication(
            medicationCodeableConcept=med_codeable,
            subject=patient_ref,
            dosageInstruction=dosage_instruction,
        )

    def _convert_vital_signs(self, vital_signs_data, patient_data) -> List[FHIRObservation]:
        observations = []
        patient_ref = None
        if patient_data and patient_data.patient_id:
            patient_ref = {"reference": f"Patient/{patient_data.patient_id}"}

        vital_mappings = {
            "blood_pressure": ("Blood Pressure", "85354-9"),
            "heart_rate": ("Heart Rate", "8867-4"),
            "temperature": ("Body Temperature", "8310-5"),
            "respiratory_rate": ("Respiratory Rate", "9279-1"),
            "oxygen_saturation": ("Oxygen Saturation", "2708-6"),
        }

        for field, (display, loinc_code) in vital_mappings.items():
            value = getattr(vital_signs_data, field, None)
            if value:
                observations.append(
                    FHIRObservation(
                        code={
                            "coding": [
                                {
                                    "system": "http://loinc.org",
                                    "code": loinc_code,
                                    "display": display,
                                }
                            ],
                            "text": display,
                        },
                        status="final",
                        subject=patient_ref,
                        valueString=value,
                    )
                )

        return observations

    def _convert_lab_results(self, lab_results_data, patient_data) -> List[FHIRObservation]:
        observations = []
        patient_ref = None
        if patient_data and patient_data.patient_id:
            patient_ref = {"reference": f"Patient/{patient_data.patient_id}"}

        for lab in lab_results_data:
            observation = FHIRObservation(
                code={"text": lab.test_name},
                status="final",
                subject=patient_ref,
            )

            if lab.value and lab.unit:
                observation.valueQuantity = {
                    "value": lab.value,
                    "unit": lab.unit,
                }
            elif lab.value:
                observation.valueString = lab.value

            observations.append(observation)

        return observations

    def _convert_care_plan(self, plan_actions_data, patient_data) -> FHIRCarePlan:
        patient_ref = None
        if patient_data and patient_data.patient_id:
            patient_ref = {"reference": f"Patient/{patient_data.patient_id}"}

        activities = []
        for action in plan_actions_data:
            activity = {
                "detail": {
                    "kind": action.action_type,
                    "description": action.description,
                    "status": "scheduled",
                }
            }
            if action.timing:
                activity["detail"]["scheduledString"] = action.timing
            activities.append(activity)

        return FHIRCarePlan(
            status="active",
            intent="plan",
            subject=patient_ref,
            activity=activities if activities else None,
        )


fhir_service = FHIRService()
