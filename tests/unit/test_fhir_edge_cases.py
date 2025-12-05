import pytest
import os
from medical_notes_processor.services.fhir_service import fhir_service
from medical_notes_processor.models.schemas import (
    StructuredMedicalData,
    PatientInfo,
    Condition,
    Medication,
    VitalSigns,
    PlanAction,
)

# Skip tests requiring OpenAI API
pytestmark = pytest.mark.skipif(
    os.getenv("OPENAI_API_KEY", "").startswith("your-") or not os.getenv("OPENAI_API_KEY"),
    reason="OpenAI API key not configured"
)


def test_convert_patient_with_missing_fields():
    """Test patient conversion with minimal data."""
    patient_data = PatientInfo(name="John Doe")

    structured_data = StructuredMedicalData(patient=patient_data)
    fhir_bundle = fhir_service.convert_to_fhir(structured_data)

    assert fhir_bundle.patient is not None
    assert fhir_bundle.patient.name == "John Doe"


def test_convert_patient_with_special_characters():
    """Test patient conversion with special characters in name."""
    patient_data = PatientInfo(
        name="José María García-Müller",
        date_of_birth="1980-05-15"
    )

    structured_data = StructuredMedicalData(patient=patient_data)
    fhir_bundle = fhir_service.convert_to_fhir(structured_data)

    assert fhir_bundle.patient.name == "José María García-Müller"


def test_convert_conditions_without_codes():
    """Test condition conversion when ICD-10 codes are missing."""
    conditions = [
        Condition(name="Rare Disease", status="active"),
        Condition(name="Unspecified Condition", status="resolved"),
    ]

    structured_data = StructuredMedicalData(
        conditions=conditions,
        patient=PatientInfo(patient_id="12345")
    )

    fhir_bundle = fhir_service.convert_to_fhir(structured_data)

    assert len(fhir_bundle.conditions) == 2
    assert fhir_bundle.conditions[0].code == "Rare Disease"


def test_convert_conditions_with_various_statuses():
    """Test condition conversion with different status values."""
    conditions = [
        Condition(name="Active Condition", status="active"),
        Condition(name="Resolved Condition", status="resolved"),
        Condition(name="Inactive Condition", status="inactive"),
        Condition(name="Unknown Status", status="unknown"),
    ]

    structured_data = StructuredMedicalData(
        conditions=conditions,
        patient=PatientInfo(patient_id="12345")
    )

    fhir_bundle = fhir_service.convert_to_fhir(structured_data)

    assert len(fhir_bundle.conditions) == 4


def test_convert_medications_without_rxnorm():
    """Test medication conversion when RxNorm codes are missing."""
    medications = [
        Medication(
            name="Experimental Drug XYZ",
            dosage="100mg",
            frequency="daily",
            route="oral"
        )
    ]

    structured_data = StructuredMedicalData(
        medications=medications,
        patient=PatientInfo(patient_id="12345")
    )

    fhir_bundle = fhir_service.convert_to_fhir(structured_data)

    assert len(fhir_bundle.medications) == 1
    med = fhir_bundle.medications[0]
    assert med.medicationCodeableConcept["text"] == "Experimental Drug XYZ"


def test_convert_medications_with_minimal_info():
    """Test medication conversion with only name."""
    medications = [Medication(name="Aspirin")]

    structured_data = StructuredMedicalData(
        medications=medications,
        patient=PatientInfo(patient_id="12345")
    )

    fhir_bundle = fhir_service.convert_to_fhir(structured_data)

    assert len(fhir_bundle.medications) == 1


def test_convert_medications_complex_dosing():
    """Test medication conversion with complex dosing instructions."""
    medications = [
        Medication(
            name="Insulin",
            dosage="10-20 units based on glucose",
            frequency="before meals and at bedtime",
            route="subcutaneous",
            duration="ongoing"
        )
    ]

    structured_data = StructuredMedicalData(
        medications=medications,
        patient=PatientInfo(patient_id="12345")
    )

    fhir_bundle = fhir_service.convert_to_fhir(structured_data)

    assert len(fhir_bundle.medications) == 1


def test_convert_vital_signs_partial_data():
    """Test vital signs conversion with only some vitals."""
    vital_signs = VitalSigns(
        blood_pressure="120/80 mmHg"
    )

    structured_data = StructuredMedicalData(
        vital_signs=vital_signs,
        patient=PatientInfo(patient_id="12345")
    )

    fhir_bundle = fhir_service.convert_to_fhir(structured_data)

    # Should only create observation for BP
    assert len(fhir_bundle.observations) == 1


def test_convert_vital_signs_abnormal_values():
    """Test vital signs conversion with abnormal values."""
    vital_signs = VitalSigns(
        blood_pressure="200/120 mmHg",
        heart_rate="140 bpm",
        temperature="104 F",
        respiratory_rate="30 breaths/min",
        oxygen_saturation="85% on room air"
    )

    structured_data = StructuredMedicalData(
        vital_signs=vital_signs,
        patient=PatientInfo(patient_id="12345")
    )

    fhir_bundle = fhir_service.convert_to_fhir(structured_data)

    assert len(fhir_bundle.observations) == 5


def test_convert_vital_signs_with_units():
    """Test vital signs conversion with various unit formats."""
    vital_signs = VitalSigns(
        blood_pressure="130/85",
        heart_rate="72",
        temperature="37.2",
        weight="75.5 kg",
        height="175 cm"
    )

    structured_data = StructuredMedicalData(
        vital_signs=vital_signs,
        patient=PatientInfo(patient_id="12345")
    )

    fhir_bundle = fhir_service.convert_to_fhir(structured_data)

    assert len(fhir_bundle.observations) == 5


def test_convert_care_plan_empty_actions():
    """Test care plan conversion with empty actions list."""
    plan_actions = []

    structured_data = StructuredMedicalData(
        plan_actions=plan_actions,
        patient=PatientInfo(patient_id="12345")
    )

    fhir_bundle = fhir_service.convert_to_fhir(structured_data)

    # Should not create care plan if no actions
    assert fhir_bundle.care_plan is None


def test_convert_care_plan_various_action_types():
    """Test care plan conversion with different action types."""
    plan_actions = [
        PlanAction(action_type="medication", description="Start Metformin"),
        PlanAction(action_type="lifestyle", description="Increase exercise"),
        PlanAction(action_type="follow-up", description="Return in 3 months"),
        PlanAction(action_type="lab-test", description="Check A1c"),
        PlanAction(action_type="referral", description="Cardiology consult"),
    ]

    structured_data = StructuredMedicalData(
        plan_actions=plan_actions,
        patient=PatientInfo(patient_id="12345")
    )

    fhir_bundle = fhir_service.convert_to_fhir(structured_data)

    assert fhir_bundle.care_plan is not None
    assert len(fhir_bundle.care_plan.activity) == 5


def test_convert_care_plan_with_timing_details():
    """Test care plan conversion with detailed timing."""
    plan_actions = [
        PlanAction(
            action_type="medication",
            description="Continue current medications",
            timing="ongoing"
        ),
        PlanAction(
            action_type="follow-up",
            description="Schedule appointment",
            timing="2 weeks"
        ),
    ]

    structured_data = StructuredMedicalData(
        plan_actions=plan_actions,
        patient=PatientInfo(patient_id="12345")
    )

    fhir_bundle = fhir_service.convert_to_fhir(structured_data)

    assert len(fhir_bundle.care_plan.activity) == 2


def test_convert_comprehensive_data():
    """Test conversion with all data types present."""
    patient = PatientInfo(
        name="John Smith",
        date_of_birth="1975-08-20",
        gender="Male",
        patient_id="98765"
    )

    conditions = [
        Condition(name="Diabetes", status="active", icd10_code="E11.9"),
        Condition(name="Hypertension", status="active", icd10_code="I10"),
    ]

    medications = [
        Medication(
            name="Metformin",
            dosage="1000mg",
            frequency="twice daily",
            route="oral",
            rxnorm_code="6809"
        ),
        Medication(
            name="Lisinopril",
            dosage="10mg",
            frequency="daily",
            route="oral"
        ),
    ]

    vital_signs = VitalSigns(
        blood_pressure="135/85 mmHg",
        heart_rate="78 bpm",
        temperature="98.6 F",
        weight="85 kg",
        height="175 cm"
    )

    plan_actions = [
        PlanAction(
            action_type="follow-up",
            description="Return in 3 months",
            timing="3 months"
        ),
        PlanAction(
            action_type="lab-test",
            description="A1c and lipid panel",
            timing="at follow-up"
        ),
    ]

    structured_data = StructuredMedicalData(
        patient=patient,
        conditions=conditions,
        medications=medications,
        vital_signs=vital_signs,
        plan_actions=plan_actions
    )

    fhir_bundle = fhir_service.convert_to_fhir(structured_data)

    # Verify all components are present
    assert fhir_bundle.patient is not None
    assert len(fhir_bundle.conditions) == 2
    assert len(fhir_bundle.medications) == 2
    assert len(fhir_bundle.observations) == 5
    assert fhir_bundle.care_plan is not None


def test_convert_null_patient():
    """Test conversion when patient is None."""
    structured_data = StructuredMedicalData(patient=None)
    fhir_bundle = fhir_service.convert_to_fhir(structured_data)

    assert fhir_bundle.patient is None


def test_convert_multiple_conditions_same_name():
    """Test conversion with duplicate condition names."""
    conditions = [
        Condition(name="Hypertension", status="active", icd10_code="I10"),
        Condition(name="Hypertension", status="active", icd10_code="I10"),
    ]

    structured_data = StructuredMedicalData(
        conditions=conditions,
        patient=PatientInfo(patient_id="12345")
    )

    fhir_bundle = fhir_service.convert_to_fhir(structured_data)

    # Should include both even if duplicates
    assert len(fhir_bundle.conditions) == 2


def test_convert_patient_gender_variations():
    """Test patient conversion with various gender values."""
    genders = ["Male", "Female", "Other", "Unknown", "male", "FEMALE"]

    for gender in genders:
        patient_data = PatientInfo(name="Test Patient", gender=gender)
        structured_data = StructuredMedicalData(patient=patient_data)
        fhir_bundle = fhir_service.convert_to_fhir(structured_data)

        assert fhir_bundle.patient is not None
        assert fhir_bundle.patient.gender.lower() in ["male", "female", "other", "unknown"]
