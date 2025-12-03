# modules/action.py

from typing import Dict, Any, Union
from pydantic import BaseModel
import asyncio
import types
import json


# Optional logging fallback
try:
    from agent import log
except ImportError:
    import datetime
    from pathlib import Path
    def log(stage: str, msg: str):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{now}] [{stage}] {msg}"
        print(log_msg)
        # Write to log file
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "agent.log"
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_msg + '\n')
        except Exception:
            pass

class ToolCallResult(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    result: Union[str, list, dict]
    raw_response: Any

MAX_TOOL_CALLS_PER_PLAN = 5

async def run_python_sandbox(code: str, dispatcher: Any) -> str:
    log("action", "=" * 50)
    log("action", "ACTION STEP STARTED")
    log("action", f"Code to execute:\n{code}")
    log("action", "=" * 50)

    # Create a fresh module scope
    sandbox = types.ModuleType("sandbox")

    try:
        # Patch MCP client with real dispatcher
        class SandboxMCP:
            def __init__(self, dispatcher):
                self.dispatcher = dispatcher
                self.call_count = 0

            async def call_tool(self, tool_name: str, input_dict: dict):
                self.call_count += 1
                if self.call_count > MAX_TOOL_CALLS_PER_PLAN:
                    raise RuntimeError(f"Exceeded max tool calls ({MAX_TOOL_CALLS_PER_PLAN}) in solve() plan.")
                # REAL tool call now
                log("action", f"Calling tool: {tool_name} with args: {input_dict}")
                result = await self.dispatcher.call_tool(tool_name, input_dict)
                log("action", f"Tool result: {result}")
                return result

        sandbox.mcp = SandboxMCP(dispatcher)

        # Preload safe built-ins into the sandbox
        import json, re
        sandbox.__dict__["json"] = json
        sandbox.__dict__["re"] = re

        # Execute solve fn dynamically
        exec(compile(code, "<solve_plan>", "exec"), sandbox.__dict__)

        solve_fn = sandbox.__dict__.get("solve")
        if solve_fn is None:
            raise ValueError("No solve() function found in plan.")

        if asyncio.iscoroutinefunction(solve_fn):
            result = await solve_fn()
        else:
            result = solve_fn()

        # Clean result formatting
        if isinstance(result, dict) and "result" in result:
            return f"{result['result']}"
        elif isinstance(result, dict):
            return f"{json.dumps(result)}"
        elif isinstance(result, list):
            return f"{' '.join(str(r) for r in result)}"
        else:
            return f"{result}"






    except Exception as e:
        log("sandbox", f"⚠️ Execution error: {e}")
        return f"[sandbox error: {str(e)}]"
