# Error Fix Report: Agent Loop and Decision Logic

**Date:** 2025-12-03
**Project:** Cortex-R Agent

## Executive Summary
This report details the investigation and resolution of issues affecting the agent's ability to complete tasks. The primary symptoms were: repeating the same websearch despite having results, failing to synthesize final answers, and forwarding hard-to-read tool outputs.

## Identified Issues and Fixes

### 1. Perception Re-run Causing Repeat Websearch
* **Symptom:** After websearch returned results, subsequent steps re-ran the same search instead of synthesizing an answer.
* **Root Cause:** In `core/loop.py`, perception was executed on every step even when `user_input_override` existed, causing fresh tool selection and repeated searches.
* **Fix:** Added skip-perception logic and caching:
  * Cache `last_perception` and `last_selected_servers` and reuse them when `user_input_override` is present.
  * Clear `user_input_override` after consumption to prevent indefinite persistence.

### 2. Planning Repetition (No Synthesis from Results)
* **Symptom:** Planning kept calling `duckduckgo_search_results` even when prior results were available in the forwarded override text.
* **Root Cause:** The decision prompt lacked explicit guidance to synthesize answers from already-fetched search results.
* **Fix:** Updated `prompts/decision_prompt_conservative.txt` with a new example and guidance:
  * Example demonstrating synthesis of `FINAL_ANSWER` from "Your last tool produced this result:" search summaries.
  * Critical rule: When search results include titles + summaries + URLs, DO NOT call search again; synthesize immediately.

### 3. Forwarded Result Readability (Escaped JSON)
* **Symptom:** Forwarded websearch results contained escaped characters (e.g., `\n`, `\u20b9`) making them hard to read.
* **Root Cause:** Tool results were serialized into JSON and embedded verbatim in the forwarding text.
* **Fix:** Added `clean_tool_result()` in `core/loop.py` to extract and decode the inner `result` string from MCP `TextContent`, converting escapes to human-readable text before forwarding.

### 4. FAISS Index Staleness and Rebuild
* **Symptom:** Index became stale/corrupted after memory/document deletions, leading to missing or irrelevant chunks.
* **Root Cause:** Metadata referenced removed sources; incremental indexing cache not cleared.
* **Fix:** Added `rebuild_faiss_index(force)` tool and enhanced `ensure_faiss_ready()` in `mcp_server_2.py` to detect stale metadata and auto-rebuild. Documented manual cleanup of `faiss_index/`.

### 5. Miscellaneous
* Increased `max_steps` to 6 to allow synthesis after initial fetch.
* Removed leftover debug trap (`pdb.set_trace`) from `core/loop.py` continuation path.

## Verification
The fixes were verified using multiple scenarios:

1) Query: "What do you know about Don Tapscott and Anthony Williams?"
	- Step 1: Websearch returns 5 results with titles + summaries.
	- Step 2+: Perception skipped; planning synthesizes `FINAL_ANSWER` from prior results (no repeated search).

2) Query: "Gold rate today India"
	- Forwarded websearch result displayed cleanly (₹ symbol and newlines decoded) via `clean_tool_result()`.

3) Document queries after index deletion
	- FAISS auto-rebuild detects stale metadata; search returns relevant chunks post-rebuild.

Overall, agent avoids repeated identical tool calls, forwards readable intermediate results, and synthesizes final answers when sufficient data is already available.

## Files Changed
- `core/loop.py`: Skip perception on override, clear override, add `clean_tool_result()`, remove debug trap.
- `prompts/decision_prompt_conservative.txt`: Add synthesis example and guidance to avoid repeated searches.
- `mcp_server_2.py`: Add `rebuild_faiss_index()` and stale metadata detection.
- `README.md`: Add project overview, structure, setup, and troubleshooting.
