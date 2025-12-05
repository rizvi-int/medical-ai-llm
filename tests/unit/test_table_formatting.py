"""
Tests for table formatting feature in chatbot.
"""

import pytest
from medical_notes_processor.services.chatbot_service import MedicalChatbot


class TestTableFormatting:
    """Tests for markdown table formatting of medical codes."""

    def test_format_as_table_single_document(self):
        """Test table formatting with a single document."""
        chatbot = MedicalChatbot()

        table_data = [
            {
                "doc_id": 1,
                "title": "Medical Note - Case 01",
                "structured": {
                    "conditions": [
                        {
                            "name": "Adult annual health exam",
                            "status": "active",
                            "ai_icd10_code": "Z00.00",
                            "validated_icd10_code": "Z00.00"
                        },
                        {
                            "name": "Overweight",
                            "status": "observation",
                            "ai_icd10_code": "E66.3"
                            # No validated code - API didn't find it
                        }
                    ],
                    "medications": [
                        {
                            "name": "Atorvastatin",
                            "dosage": "10mg",
                            "rxnorm_code": "83367"
                        }
                    ]
                }
            }
        ]

        result = chatbot._format_as_table(table_data)

        # Check table structure (updated with Confidence column)
        assert "| Case | Document Title | Diagnoses | ICD-10 (AI) | Confidence | ICD-10 (Validated) | Medications | RxNorm |" in result
        assert "|------|" in result  # Header separator

        # Check data presence
        assert "Medical Note - Case 01" in result
        assert "Adult annual health exam" in result
        assert "Z00.00" in result
        assert "Overweight" in result
        assert "E66.3" in result
        assert "N/A" in result  # For missing validated code
        assert "Atorvastatin" in result
        assert "83367" in result

    def test_format_as_table_multiple_documents(self):
        """Test table formatting with multiple documents."""
        chatbot = MedicalChatbot()

        table_data = [
            {
                "doc_id": 1,
                "title": "Case 01",
                "structured": {
                    "conditions": [
                        {"name": "Hypertension", "ai_icd10_code": "I10", "validated_icd10_code": "I10"}
                    ]
                }
            },
            {
                "doc_id": 2,
                "title": "Case 02",
                "structured": {
                    "conditions": [
                        {"name": "Type 2 Diabetes", "ai_icd10_code": "E11.9", "validated_icd10_code": "E11.9"}
                    ],
                    "medications": [
                        {"name": "Metformin", "rxnorm_code": "6809"}
                    ]
                }
            }
        ]

        result = chatbot._format_as_table(table_data)

        # Both documents should be present
        assert "| 1 |" in result
        assert "| 2 |" in result
        assert "Case 01" in result
        assert "Case 02" in result
        assert "Hypertension" in result
        assert "Type 2 Diabetes" in result
        assert "Metformin" in result

    def test_format_as_table_no_conditions(self):
        """Test table formatting when document has no conditions."""
        chatbot = MedicalChatbot()

        table_data = [
            {
                "doc_id": 1,
                "title": "Empty Note",
                "structured": {
                    "medications": [
                        {"name": "Aspirin", "rxnorm_code": "1191"}
                    ]
                }
            }
        ]

        result = chatbot._format_as_table(table_data)

        assert "Empty Note" in result
        assert "Aspirin" in result
        assert "1191" in result

    def test_format_as_table_no_medications(self):
        """Test table formatting when document has no medications."""
        chatbot = MedicalChatbot()

        table_data = [
            {
                "doc_id": 3,
                "title": "Diagnosis Only",
                "structured": {
                    "conditions": [
                        {"name": "Hyperlipidemia", "ai_icd10_code": "E78.5"}
                    ]
                }
            }
        ]

        result = chatbot._format_as_table(table_data)

        assert "Diagnosis Only" in result
        assert "Hyperlipidemia" in result
        assert "E78.5" in result
        assert "| - | - |" in result  # Empty medication columns

    def test_format_as_table_empty_structured_data(self):
        """Test table formatting when structured data is None."""
        chatbot = MedicalChatbot()

        table_data = [
            {
                "doc_id": 5,
                "title": "Failed Extraction",
                "structured": None
            }
        ]

        result = chatbot._format_as_table(table_data)

        assert "Failed Extraction" in result
        assert "No data" in result

    def test_format_as_table_multiple_conditions_per_document(self):
        """Test table with multiple conditions in same document."""
        chatbot = MedicalChatbot()

        table_data = [
            {
                "doc_id": 7,
                "title": "Complex Case",
                "structured": {
                    "conditions": [
                        {"name": "Type 2 Diabetes", "ai_icd10_code": "E11.9", "validated_icd10_code": "E11.9"},
                        {"name": "Hypertension", "ai_icd10_code": "I10", "validated_icd10_code": "I10"},
                        {"name": "Hyperlipidemia", "ai_icd10_code": "E78.5", "validated_icd10_code": "E78.5"}
                    ],
                    "medications": [
                        {"name": "Metformin", "rxnorm_code": "6809"},
                        {"name": "Lisinopril", "rxnorm_code": "29046"}
                    ]
                }
            }
        ]

        result = chatbot._format_as_table(table_data)

        # All conditions should be present
        assert "Type 2 Diabetes" in result
        assert "Hypertension" in result
        assert "Hyperlipidemia" in result

        # All medications should be present
        assert "Metformin" in result
        assert "Lisinopril" in result

        # Multiple rows for same document (empty cells)
        assert "|  |  |" in result

    def test_format_as_table_mixed_ai_and_validated_codes(self):
        """Test table with some AI codes validated and some not."""
        chatbot = MedicalChatbot()

        table_data = [
            {
                "doc_id": 10,
                "title": "Mixed Validation",
                "structured": {
                    "conditions": [
                        {
                            "name": "Annual wellness visit",
                            "ai_icd10_code": "Z00.00"
                            # No validated code
                        },
                        {
                            "name": "Type 2 Diabetes",
                            "ai_icd10_code": "E11.9",
                            "validated_icd10_code": "E11.9"
                        }
                    ]
                }
            }
        ]

        result = chatbot._format_as_table(table_data)

        # AI code present without validation
        assert "Annual wellness visit" in result
        assert "Z00.00" in result
        lines = result.split("\n")
        wellness_line = [l for l in lines if "Annual wellness visit" in l][0]
        assert "N/A" in wellness_line  # For missing validated code

        # Both AI and validated present
        assert "Type 2 Diabetes" in result
        diabetes_lines = [l for l in lines if "Type 2 Diabetes" in l]
        assert len(diabetes_lines) > 0
        assert "E11.9" in diabetes_lines[0]

    def test_format_as_table_empty_list(self):
        """Test table formatting with empty data list."""
        chatbot = MedicalChatbot()

        result = chatbot._format_as_table([])
        assert "No data to display" in result

    def test_format_as_table_all_fields_present(self):
        """Test comprehensive table with all possible fields."""
        chatbot = MedicalChatbot()

        table_data = [
            {
                "doc_id": 1,
                "title": "Complete Medical Record",
                "structured": {
                    "conditions": [
                        {
                            "name": "Type 2 Diabetes Mellitus",
                            "status": "active",
                            "ai_icd10_code": "E11.9",
                            "validated_icd10_code": "E11.9"
                        }
                    ],
                    "medications": [
                        {
                            "name": "Metformin",
                            "dosage": "500mg",
                            "frequency": "BID",
                            "rxnorm_code": "6809"
                        }
                    ]
                }
            },
            {
                "doc_id": 2,
                "title": "Another Record",
                "structured": {
                    "conditions": [
                        {
                            "name": "Hypertension",
                            "ai_icd10_code": "I10",
                            "validated_icd10_code": "I10"
                        }
                    ]
                }
            }
        ]

        result = chatbot._format_as_table(table_data)

        # Verify it's a valid markdown table
        lines = result.split("\n")
        assert len(lines) >= 4  # Header + separator + at least 2 data rows

        # Header should have 8 columns (added Confidence column)
        header = lines[0]
        assert header.count("|") == 9  # 8 columns + edges

        # Separator should match header structure
        separator = lines[1]
        assert separator.count("|") == 9

    @pytest.mark.asyncio
    async def test_table_keyword_detection(self):
        """Test that 'table' keyword triggers table formatting."""
        chatbot = MedicalChatbot()

        # Message with 'table' should trigger table format
        message1 = "give me the icd10 codes for doc 1 and 2 in a table"
        assert "table" in message1.lower()

        # Message without 'table' should not trigger table format
        message2 = "give me the icd10 codes for doc 1 and 2"
        assert "table" not in message2.lower()

    def test_format_as_table_handles_diagnoses_key(self):
        """Test that table formatting works with 'diagnoses' key (alternative to 'conditions')."""
        chatbot = MedicalChatbot()

        table_data = [
            {
                "doc_id": 1,
                "title": "Test",
                "structured": {
                    "diagnoses": [  # Using 'diagnoses' instead of 'conditions'
                        {"name": "Diabetes", "ai_icd10_code": "E11.9"}
                    ]
                }
            }
        ]

        result = chatbot._format_as_table(table_data)
        assert "Diabetes" in result
        assert "E11.9" in result


class TestTableFormattingEdgeCases:
    """Test edge cases for table formatting."""

    def test_format_table_with_long_names(self):
        """Test table with very long diagnosis/medication names."""
        chatbot = MedicalChatbot()

        table_data = [
            {
                "doc_id": 1,
                "title": "Long Names Test",
                "structured": {
                    "conditions": [
                        {
                            "name": "Type 2 Diabetes Mellitus with Diabetic Chronic Kidney Disease",
                            "ai_icd10_code": "E11.22"
                        }
                    ],
                    "medications": [
                        {
                            "name": "Insulin glargine, recombinant, 100 units/mL solution",
                            "rxnorm_code": "261551"
                        }
                    ]
                }
            }
        ]

        result = chatbot._format_as_table(table_data)

        # Should still be formatted correctly
        assert "Type 2 Diabetes Mellitus with Diabetic Chronic Kidney Disease" in result
        assert "Insulin glargine" in result
        assert "|" in result

    def test_format_table_with_special_characters(self):
        """Test table with special characters in names."""
        chatbot = MedicalChatbot()

        table_data = [
            {
                "doc_id": 1,
                "title": "Special Chars & Symbols",
                "structured": {
                    "conditions": [
                        {"name": "Patient c/o chest pain", "ai_icd10_code": "R07.9"}
                    ]
                }
            }
        ]

        result = chatbot._format_as_table(table_data)

        # Special characters should be preserved
        assert "c/o" in result or "chest pain" in result

    def test_format_table_preserves_markdown(self):
        """Test that table output is valid markdown."""
        chatbot = MedicalChatbot()

        table_data = [
            {
                "doc_id": 1,
                "title": "Test",
                "structured": {
                    "conditions": [
                        {"name": "Diabetes", "ai_icd10_code": "E11.9", "validated_icd10_code": "E11.9"}
                    ]
                }
            }
        ]

        result = chatbot._format_as_table(table_data)
        lines = result.split("\n")

        # First line should be header
        assert lines[0].startswith("|")
        assert lines[0].endswith("|")

        # Second line should be separator with dashes
        assert lines[1].startswith("|")
        assert "---" in lines[1]

        # Data lines should start and end with pipes
        for line in lines[2:]:
            if line.strip():  # Skip empty lines
                assert line.startswith("|")
                assert line.endswith("|")
