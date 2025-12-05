# Dual ICD-10 Code Extraction Feature

## Overview

The medical notes chatbot now provides **dual ICD-10 code extraction**, showing both:
1. **AI-Inferred Codes**: Clinically intelligent code assignments from the LLM
2. **API-Validated Codes**: Codes confirmed by the NLM Clinical Tables database

This gives you transparency and utility - you can see what the AI thinks the code should be, AND what can be verified through authoritative sources.

## Why This Matters

Previously, the system was conservative - it only showed codes when the API could find an exact match. This meant:
- ❌ "Annual health exam" → No code (should be Z00.00)
- ❌ "Family history of hyperlipidemia" → No code (should be Z83.42)
- ❌ "Possible overweight" → No code (should be E66.3)

Now with dual codes:
- ✅ **AI Code**: Z00.00 | **Validated**: Not found → You see the clinically correct code
- ✅ **AI Code**: Z83.42 | **Validated**: Not found → Family history codes are captured
- ✅ **AI Code**: E66.3 | **Validated**: E66.3 → Both agree, high confidence

## How to Use

### Table Format (Recommended for Multiple Documents)

Ask for codes "in a table":

```
"give me the icd10 codes for doc 1, 2, and 3 in a table"
```

Response:
```
| Case | Document Title        | Diagnoses                        | ICD-10 (AI) | ICD-10 (Validated) | Medications  | RxNorm |
|------|-----------------------|----------------------------------|-------------|-------------------|--------------|--------|
| 1    | Medical Note - Case 01| Annual health exam               | Z00.00      | N/A               | -            | -      |
|      |                       | Overweight                       | E66.3       | E66.3             |              |        |
|      |                       | Family hx hyperlipidemia         | Z83.42      | N/A               |              |        |
| 2    | Medical Note - Case 02| Type 2 Diabetes                  | E11.9       | E11.9             | Metformin    | 6809   |
```

### List Format (Good for Single Documents)

Ask without "table":

```
"what are the icd10 codes for document 5"
```

Response:
```
Extracted from: Medical Note - Case 05

Diagnoses (AI-Inferred Codes):
  • Annual health examination (ICD-10: Z00.00)
  • Overweight (ICD-10: E66.3)
  • Family history of hyperlipidemia (ICD-10: Z83.42)

Diagnoses (API-Validated Codes):
  • Annual health examination (ICD-10: Not found in database)
  • Overweight (ICD-10: E66.3)
  • Family history of hyperlipidemia (ICD-10: Not found in database)
```

## Multi-Document Queries

The chatbot supports querying multiple documents in various formats:

- `"doc 1, 2, and 3"`
- `"documents 5 and 12"`
- `"patients 1, 3, 7, 10"`
- `"extract codes from all patients"` (processes all documents in parallel)

## Code Intelligence Examples

### Routine Encounters
**Input**: "Annual wellness visit"
- **AI Code**: Z00.00 (Encounter for general adult medical examination)
- **API**: May not find (generic wording)
- **Benefit**: You still get the correct Z code

### Family History
**Input**: "Family history of diabetes"
- **AI Code**: Z83.3 (Family history of diabetes mellitus)
- **API**: May not find (requires exact phrasing)
- **Benefit**: Family history codes are captured

### Screening & Observations
**Input**: "BMI 28, appears overweight"
- **AI Code**: E66.3 (Overweight)
- **API**: E66.3 (Confirmed)
- **Benefit**: Both agree - high confidence

### Confirmed Diagnoses
**Input**: "Type 2 Diabetes Mellitus"
- **AI Code**: E11.9 (Type 2 diabetes mellitus without complications)
- **API**: E11.9 (Confirmed)
- **Benefit**: Both sources align - verified diagnosis

## Technical Implementation

### Architecture

1. **LLM Extraction** ([extraction_agent.py:52-91](src/medical_notes_processor/agents/extraction_agent.py))
   - Enhanced prompt instructs LLM to assign ICD-10 codes based on clinical reasoning
   - Returns `suggested_icd10_code` field for each condition

2. **API Validation** ([external_apis.py:174-218](src/medical_notes_processor/utils/external_apis.py))
   - Preserves AI-suggested code as `ai_icd10_code`
   - Looks up codes via NLM Clinical Tables API
   - Adds `validated_icd10_code` if API finds a match

3. **Dual Display** ([chatbot_service.py:355-402](src/medical_notes_processor/services/chatbot_service.py))
   - Formats both code types separately
   - Table format for multi-document comparison
   - List format for detailed single-document view

### Data Schema

Updated Condition model ([schemas.py:61-67](src/medical_notes_processor/models/schemas.py)):

```python
class Condition(BaseModel):
    name: str
    status: Optional[str] = None
    icd10_code: Optional[str] = None           # Legacy (backward compatible)
    suggested_icd10_code: Optional[str] = None  # From LLM
    ai_icd10_code: Optional[str] = None        # Transformed AI code
    validated_icd10_code: Optional[str] = None  # From API
```

## Testing

Comprehensive test suites have been created:

### Unit Tests
- **test_dual_code_extraction.py** (8 tests)
  - AI vs validated code scenarios
  - Routine exams, family history, screening codes
  - Backward compatibility with old format

- **test_chatbot_features.py** (25+ tests)
  - Multi-document queries
  - Conversation memory
  - Context detection
  - Keyword routing

- **test_table_formatting.py** (14 tests)
  - Table structure validation
  - Edge cases (long names, special chars)
  - Multiple conditions per document
  - Empty data handling

### Integration Tests
- **test_dual_code_end_to_end.py** (5 tests)
  - Complete flow: note → extraction → validation → formatting
  - Chatbot table format
  - Chatbot list format
  - Multi-document queries

Run tests:
```bash
# Unit tests
uv run pytest tests/unit/test_dual_code_extraction.py -v
uv run pytest tests/unit/test_chatbot_features.py -v
uv run pytest tests/unit/test_table_formatting.py -v

# Integration tests (requires running services)
uv run pytest tests/integration/test_dual_code_end_to_end.py -v
```

## Clinical Value

This dual-code approach provides:

1. **Better Code Coverage**: AI assigns codes for encounters/observations that API databases don't recognize
2. **Confidence Indicators**: When both agree, you have high confidence in the code
3. **Transparency**: You see what's AI-inferred vs. what's database-validated
4. **Clinical Intelligence**: Z codes, family history, and screening codes are properly captured
5. **Audit Trail**: Both code sources are preserved for compliance and review

## Example Use Cases

### Use Case 1: Annual Physical Coding
**Scenario**: Billing for annual wellness visits

**Before**: Many Z codes missed (showed as "None")

**After**:
- AI captures Z00.00 (wellness visit)
- AI captures Z83.x (family history)
- AI captures preventive service codes

### Use Case 2: Quality Metrics
**Scenario**: Tracking patient risk factors

**Before**: Observations like "overweight" not coded

**After**:
- E66.3 captured for overweight observations
- Risk stratification more complete
- Quality metrics more accurate

### Use Case 3: Research Data Extraction
**Scenario**: Extracting structured data for clinical studies

**Before**: Conservative coding missed many conditions

**After**:
- Comprehensive condition extraction
- Both inferred and validated codes for analysis
- Better phenotyping of patient populations

## Limitations & Considerations

1. **AI Codes Are Suggestions**: The AI-inferred codes should be reviewed for clinical accuracy
2. **API Coverage**: Some valid codes may not be in the Clinical Tables database
3. **Context Dependency**: Code accuracy depends on documentation quality
4. **Z-Code Emphasis**: The system is particularly good at capturing Z codes (encounters, screening, family history)

## Future Enhancements

Potential improvements:
- [ ] Add confidence scores for AI-inferred codes
- [ ] Support for additional code systems (CPT, SNOMED-CT)
- [ ] Code validation against multiple authoritative sources
- [ ] Machine learning from validated vs. AI code agreement patterns
- [ ] Export to billing systems with code source indicators

## Questions?

- Check [DOCKER.md](DOCKER.md) for deployment information
- See [README.md](README.md) for general system documentation
- Review test files for usage examples
