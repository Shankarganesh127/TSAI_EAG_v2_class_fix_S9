# Enhanced Agent Logging

All agent logs are now written to `logs/agent.log` with detailed information about each step.

## Logging Structure

### 1. **PERCEPTION STEP**
Located in: `modules/perception.py`

Logs:
- User input
- Available MCP servers
- Full perception prompt sent to LLM
- Raw LLM output
- Parsed perception result (intent, entities, selected servers)

### 2. **MEMORY STEP**
Located in: `core/loop.py`

Logs:
- Number of memory items retrieved
- Preview of each memory item (first 100 characters)
- Memory items used for context

### 3. **DECISION STEP**
Located in: `modules/decision.py`

Logs:
- Current step number (e.g., Step 2/5)
- User input
- Perceived intent
- Extracted entities
- Number of memory items available
- Full decision prompt (including tool descriptions and memory)
- LLM-generated plan output

### 4. **ACTION STEP**
Located in: `modules/action.py`

Logs:
- Code to be executed in sandbox
- Each tool call with:
  - Tool name
  - Arguments passed
  - Tool result received
- Final execution result

## Log File Location

**File:** `logs/agent.log`

All logs include timestamps in format: `[HH:MM:SS] [stage] message`

## Example Log Flow

```
[21:30:00] [perception] ==================================================
[21:30:00] [perception] PERCEPTION STEP STARTED
[21:30:00] [perception] User Input: What is AI?
[21:30:00] [perception] Available Servers: ['math', 'documents', 'websearch']
[21:30:00] [perception] Prompt:
You are a perception module...
[21:30:00] [perception] ==================================================
[21:30:01] [perception] Raw output: {"intent": "...", ...}

[21:30:01] [memory] ==================================================
[21:30:01] [memory] MEMORY STEP
[21:30:01] [memory] Retrieved 2 memory items
[21:30:01] [memory]   Item 1: Previous query about AI...
[21:30:01] [memory]   Item 2: Tool call result...
[21:30:01] [memory] ==================================================

[21:30:02] [decision] ==================================================
[21:30:02] [decision] DECISION STEP STARTED (Step 1/5)
[21:30:02] [decision] User Input: What is AI?
[21:30:02] [decision] Intent: Find information about AI
[21:30:02] [decision] Entities: ['AI']
[21:30:02] [decision] Memory Items: 2
[21:30:02] [decision] Prompt:
You are an AI assistant. Generate an async Python function...
[21:30:02] [decision] ==================================================
[21:30:03] [plan] LLM output: async def solve():...

[21:30:03] [action] ==================================================
[21:30:03] [action] ACTION STEP STARTED
[21:30:03] [action] Code to execute:
async def solve():
    ...
[21:30:03] [action] ==================================================
[21:30:04] [action] Calling tool: search_stored_documents with args: {...}
[21:30:05] [action] Tool result: CallToolResult(...)
```

## Benefits

1. **Full Transparency**: See exactly what prompts are sent to the LLM
2. **Debugging**: Track down issues in any of the 4 steps
3. **Performance Analysis**: See which steps take the most time
4. **Audit Trail**: Complete record of agent decision-making process
