# Chatbot Architecture Refactoring

## Overview

Refactored chatbot from non-deterministic agent-based architecture to deterministic linear RAG pipeline.

## Previous Architecture (Agentic)

**Pattern**: LLM-driven tool calling via LangChain function calling

**Flow**:
1. User message → LLM
2. LLM decides whether to call tools
3. If yes: LLM calls `get_documents_list`, `get_document_content`, `summarize_medical_note`, etc.
4. Tools execute, return results
5. LLM generates final answer

**Problems**:
- Non-deterministic: LLM can skip retrieval
- Hallucination risk: LLM may answer without checking context
- Token waste: Multiple LLM calls (tool decision + answer generation)
- Conversational filler: "I will check that for you" responses
- Tool chaining complexity: Multi-step agent logic

## New Architecture (Linear Pipeline)

**Pattern**: Deterministic 5-stage pipeline

**Flow**:
1. **Context Loading**: Load note content if `note_id` provided
2. **Summary Generation**: Generate concise summary of loaded note
3. **RAG Retrieval**: Query Qdrant for top-k relevant chunks
4. **Prompt Construction**: Build structured prompt with XML tags
5. **LLM Generation**: Single LLM call with complete context

**Benefits**:
- Deterministic: Code controls execution, not LLM
- No hallucination: LLM sees context before answering
- Token efficiency: Single LLM call
- Clean responses: No conversational filler
- Simplified logic: No agent coordination

## Implementation Details

### Prompt Construction

Uses XML-style tags to isolate context:

```
<system_instructions>
You are a clinical information assistant.
- Answer using ONLY provided context
- If not in context: "Not specified in provided documents"
- No internal knowledge, no inference
</system_instructions>

<current_note>
[Summary of specific note if loaded]
</current_note>

<retrieved_context>
[RAG-retrieved chunks]
</retrieved_context>

<sources>
- Document 1: Medical Note - Case 01
- Document 3: Medical Note - Case 03
</sources>

<user_question>
What medications is the patient taking?
</user_question>
```

XML tags prevent context leakage by clearly delineating boundaries.

### Temperature Settings

- **Chatbot LLM**: `temperature=0.0` (deterministic answers)
- **RAG LLM**: `temperature=0.0` (consistent retrieval summaries)
- **Summary LLM**: `temperature=0.0` (reproducible summaries)

Zero temperature across all components ensures reproducibility.

### API Changes

**Old API**:
```json
{
  "message": "What documents do you have?",
  "reset_conversation": false
}
```

**New API**:
```json
{
  "message": "What medications is the patient taking?",
  "note_id": 3
}
```

- Removed `reset_conversation` (stateless design)
- Added `note_id` for focused context
- Response no longer includes `conversation_length`

### Code Structure

**`services/chatbot_service.py`**:
- `MedicalChatbot.chat()`: Main pipeline orchestrator
- `_load_note()`: Fetch document content
- `_generate_summary()`: Create note summary
- `_retrieve_context()`: RAG query execution
- `_build_prompt()`: Structured prompt construction
- `_generate_answer()`: Single LLM call

**`api/chat.py`**:
- Simplified endpoint: passes `message` and `note_id` to service
- No conversation state management
- Clean error handling

## Comparison

| Aspect | Agent (Old) | Pipeline (New) |
|--------|-------------|----------------|
| LLM calls | 2-4 per query | 1 per query |
| Determinism | Low (LLM decides) | High (code decides) |
| Hallucination risk | High (can skip tools) | Low (forced context) |
| Token usage | High (multiple calls) | Low (single call) |
| Complexity | High (agent logic) | Low (linear flow) |
| Temperature | 0.7 | 0.0 |
| Conversation state | Stateful (6 messages) | Stateless |

## Verification Strategy

**Test Cases**:
1. Query without note_id: Should retrieve general context via RAG
2. Query with note_id: Should include note summary + RAG context
3. Query for information not in context: Should respond "Not specified in provided documents"
4. Same query twice: Should produce identical answers (determinism)

**Expected Behavior**:
- No "I will check that for you" responses
- Answers cite specific context
- Consistent results across runs
- Clear "not found" responses for missing information

## Performance Considerations

**Token Optimization**:
- Note summary instead of full note content (500 chars vs 5000+ chars)
- Top-k=3 RAG chunks (controllable retrieval size)
- Single LLM call eliminates round-trip overhead

**Caching Opportunities** (Future):
- Cache note summaries by document ID
- Cache RAG results for common queries
- Pre-warm summaries on document upload

## Migration Notes

**Breaking Changes**:
- Removed conversation history tracking
- Changed ChatResponse schema
- Removed `/chat/reset` endpoint

**Frontend Compatibility**:
- Frontend must pass `note_id` for focused queries
- Response handling simplified (no `conversation_length`)

**Backward Compatibility**:
- None. This is a breaking change requiring frontend updates.

## Architecture Decision Rationale

**Why Linear Over Agentic?**

For medical applications:
1. **Safety**: Deterministic behavior reduces unpredictability
2. **Auditability**: Clear execution path for compliance
3. **Reliability**: No tool-calling failures or LLM indecision
4. **Efficiency**: Lower token costs, faster responses

Agents are valuable for:
- Complex multi-step reasoning
- Dynamic tool selection
- Exploratory tasks

Medical Q&A requires:
- Consistent answers
- Clear sourcing
- Reproducibility

Linear pipeline matches these requirements better than agentic approach.
