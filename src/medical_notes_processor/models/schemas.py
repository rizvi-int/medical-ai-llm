from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any


# Document Schemas
class DocumentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)


class DocumentCreate(DocumentBase):
    pass


class DocumentResponse(DocumentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# LLM Schemas
class SummarizeRequest(BaseModel):
    text: str = Field(..., description="Medical note text to summarize")


class SummarizeResponse(BaseModel):
    summary: str
    model_used: str


# RAG Schemas
class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1)


class QuestionResponse(BaseModel):
    answer: str
    sources: Optional[List[Dict[str, Any]]] = None


# Agent Schemas - Structured Medical Data
class VitalSigns(BaseModel):
    blood_pressure: Optional[str] = None
    heart_rate: Optional[str] = None
    temperature: Optional[str] = None
    respiratory_rate: Optional[str] = None
    oxygen_saturation: Optional[str] = None


class Medication(BaseModel):
    name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    route: Optional[str] = None
    rxnorm_code: Optional[str] = None


class Condition(BaseModel):
    name: str
    status: Optional[str] = None
    icd10_code: Optional[str] = None


class LabResult(BaseModel):
    test_name: str
    value: Optional[str] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None


class PlanAction(BaseModel):
    action_type: str
    description: str
    timing: Optional[str] = None


class PatientInfo(BaseModel):
    name: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    patient_id: Optional[str] = None


class StructuredMedicalData(BaseModel):
    patient: Optional[PatientInfo] = None
    encounter_date: Optional[str] = None
    chief_complaint: Optional[str] = None
    subjective: Optional[str] = None
    objective: Optional[str] = None
    vital_signs: Optional[VitalSigns] = None
    conditions: List[Condition] = Field(default_factory=list)
    medications: List[Medication] = Field(default_factory=list)
    lab_results: List[LabResult] = Field(default_factory=list)
    assessment: Optional[str] = None
    plan_actions: List[PlanAction] = Field(default_factory=list)


class ExtractStructuredRequest(BaseModel):
    text: str = Field(..., description="Medical note text to extract structured data from")


class ExtractStructuredResponse(BaseModel):
    structured_data: StructuredMedicalData


# FHIR Schemas
class FHIRPatient(BaseModel):
    resourceType: str = "Patient"
    id: Optional[str] = None
    name: Optional[str] = None
    gender: Optional[str] = None
    birthDate: Optional[str] = None


class FHIRCondition(BaseModel):
    resourceType: str = "Condition"
    code: str
    clinicalStatus: Optional[str] = None
    verificationStatus: Optional[str] = None
    subject: Optional[Dict[str, str]] = None
    recordedDate: Optional[str] = None


class FHIRMedication(BaseModel):
    resourceType: str = "MedicationRequest"
    medicationCodeableConcept: Dict[str, Any]
    subject: Optional[Dict[str, str]] = None
    dosageInstruction: Optional[List[Dict[str, Any]]] = None


class FHIRObservation(BaseModel):
    resourceType: str = "Observation"
    code: Dict[str, Any]
    status: str = "final"
    subject: Optional[Dict[str, str]] = None
    valueQuantity: Optional[Dict[str, Any]] = None
    valueString: Optional[str] = None


class FHIRCarePlan(BaseModel):
    resourceType: str = "CarePlan"
    status: str = "active"
    intent: str = "plan"
    subject: Optional[Dict[str, str]] = None
    activity: Optional[List[Dict[str, Any]]] = None


class FHIRBundle(BaseModel):
    patient: Optional[FHIRPatient] = None
    conditions: List[FHIRCondition] = Field(default_factory=list)
    medications: List[FHIRMedication] = Field(default_factory=list)
    observations: List[FHIRObservation] = Field(default_factory=list)
    care_plan: Optional[FHIRCarePlan] = None


class ToFHIRRequest(BaseModel):
    structured_data: StructuredMedicalData


class ToFHIRResponse(BaseModel):
    fhir_bundle: FHIRBundle
