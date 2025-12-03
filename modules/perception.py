# modules/perception.py

from typing import List, Optional
from pydantic import BaseModel
from modules.model_manager import ModelManager
from modules.tools import load_prompt, extract_json_block
from core.context import AgentContext

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

model = ModelManager()


prompt_path = "prompts/perception_prompt.txt"

class PerceptionResult(BaseModel):
    intent: str
    entities: List[str] = []
    tool_hint: Optional[str] = None
    tags: List[str] = []
    selected_servers: List[str] = []  # 🆕 NEW field

async def extract_perception(user_input: str, mcp_server_descriptions: dict) -> PerceptionResult:
    """
    Extracts perception details and selects relevant MCP servers based on the user query.
    """

    server_list = []
    for server_id, server_info in mcp_server_descriptions.items():
        description = server_info.get("description", "No description available")
        server_list.append(f"- {server_id}: {description}")

    servers_text = "\n".join(server_list)

    prompt_template = load_prompt(prompt_path)
    

    prompt = prompt_template.format(
        servers_text=servers_text,
        user_input=user_input
    )
    
    log("perception", "=" * 50)
    log("perception", "PERCEPTION STEP STARTED")
    log("perception", f"User Input: {user_input}")
    log("perception", f"Available Servers: {list(mcp_server_descriptions.keys())}")
    log("perception", f"Prompt:\n{prompt}")
    log("perception", "=" * 50)
    

    try:
        raw = await model.generate_text(prompt)
        raw = raw.strip()
        log("perception", f"Raw output: {raw}")

        # Try parsing into PerceptionResult
        json_block = extract_json_block(raw)
        result = json.loads(json_block)

        # If selected_servers missing, fallback
        if "selected_servers" not in result:
            result["selected_servers"] = list(mcp_server_descriptions.keys())
        print("result", result)

        return PerceptionResult(**result)

    except Exception as e:
        log("perception", f"⚠️ Perception failed: {e}")
        # Fallback: select all servers
        return PerceptionResult(
            intent="unknown",
            entities=[],
            tool_hint=None,
            tags=[],
            selected_servers=list(mcp_server_descriptions.keys())
        )


async def run_perception(context: AgentContext, user_input: Optional[str] = None):

    """
    Clean wrapper to call perception from context.
    """
    return await extract_perception(
        user_input = user_input or context.user_input,
        mcp_server_descriptions=context.mcp_server_descriptions
    )

