import pytest
from medical_notes_processor.services.fhir_service import fhir_service
from medical_notes_processor.models.schemas import (
    StructuredMedicalData,
    PatientInfo,
    Condition,
    Medication,
    VitalSigns,
    PlanAction,
)


def test_convert_patient():
    """Test patient conversion to FHIR."""
    patient_data = PatientInfo(
        name="John Doe",
        date_of_birth="1980-05-15",
        gender="Male",
        patient_id="12345"
    )

    structured_data = StructuredMedicalData(patient=patient_data)
    fhir_bundle = fhir_service.convert_to_fhir(structured_data)

    assert fhir_bundle.patient is not None
    assert fhir_bundle.patient.name == "John Doe"
    assert fhir_bundle.patient.gender == "male"
    assert fhir_bundle.patient.birthDate == "1980-05-15"
    assert fhir_bundle.patient.id == "12345"


def test_convert_conditions():
    """Test condition conversion to FHIR."""
    conditions = [
        Condition(name="Type 2 Diabetes", status="active", icd10_code="E11.9"),
        Condition(name="Hypertension", status="active", icd10_code="I10"),
    ]

    structured_data = StructuredMedicalData(
        conditions=conditions,
        patient=PatientInfo(patient_id="12345")
    )

    fhir_bundle = fhir_service.convert_to_fhir(structured_data)

    assert len(fhir_bundle.conditions) == 2
    assert fhir_bundle.conditions[0].code == "Type 2 Diabetes"
    assert fhir_bundle.conditions[0].clinicalStatus == "active"
    assert fhir_bundle.conditions[1].code == "Hypertension"


def test_convert_medications():
    """Test medication conversion to FHIR."""
    medications = [
        Medication(
            name="Metformin",
            dosage="500mg",
            frequency="twice daily",
            route="oral",
            rxnorm_code="6809"
        )
    ]

    structured_data = StructuredMedicalData(
        medications=medications,
        patient=PatientInfo(patient_id="12345")
    )

    fhir_bundle = fhir_service.convert_to_fhir(structured_data)

    assert len(fhir_bundle.medications) == 1
    med = fhir_bundle.medications[0]
    assert med.medicationCodeableConcept["text"] == "Metformin"
    assert "coding" in med.medicationCodeableConcept
    assert med.medicationCodeableConcept["coding"][0]["code"] == "6809"


def test_convert_vital_signs():
    """Test vital signs conversion to FHIR observations."""
    vital_signs = VitalSigns(
        blood_pressure="120/80 mmHg",
        heart_rate="72 bpm",
        temperature="98.6 F"
    )

    structured_data = StructuredMedicalData(
        vital_signs=vital_signs,
        patient=PatientInfo(patient_id="12345")
    )

    fhir_bundle = fhir_service.convert_to_fhir(structured_data)

    assert len(fhir_bundle.observations) == 3
    bp_obs = next(
        (obs for obs in fhir_bundle.observations
         if "Blood Pressure" in obs.code.get("text", "")),
        None
    )
    assert bp_obs is not None
    assert bp_obs.valueString == "120/80 mmHg"


def test_convert_care_plan():
    """Test care plan conversion to FHIR."""
    plan_actions = [
        PlanAction(
            action_type="follow-up",
            description="Schedule follow-up in 3 months",
            timing="3 months"
        ),
        PlanAction(
            action_type="lab-test",
            description="HbA1c test",
            timing="at follow-up"
        )
    ]

    structured_data = StructuredMedicalData(
        plan_actions=plan_actions,
        patient=PatientInfo(patient_id="12345")
    )

    fhir_bundle = fhir_service.convert_to_fhir(structured_data)

    assert fhir_bundle.care_plan is not None
    assert fhir_bundle.care_plan.status == "active"
    assert fhir_bundle.care_plan.intent == "plan"
    assert len(fhir_bundle.care_plan.activity) == 2


def test_empty_structured_data():
    """Test conversion with minimal/empty data."""
    structured_data = StructuredMedicalData()
    fhir_bundle = fhir_service.convert_to_fhir(structured_data)

    assert fhir_bundle.patient is None
    assert len(fhir_bundle.conditions) == 0
    assert len(fhir_bundle.medications) == 0
    assert len(fhir_bundle.observations) == 0
    assert fhir_bundle.care_plan is None
