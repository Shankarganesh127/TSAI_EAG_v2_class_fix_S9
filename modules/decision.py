from typing import List, Optional
from modules.perception import PerceptionResult
from modules.memory import MemoryItem
from modules.model_manager import ModelManager
from modules.tools import load_prompt
import re

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


# prompt_path = "prompts/decision_prompt.txt"

async def generate_plan(
    user_input: str, 
    perception: PerceptionResult,
    memory_items: List[MemoryItem],
    tool_descriptions: Optional[str],
    prompt_path: str,
    step_num: int = 1,
    max_steps: int = 3,
) -> str:

    """Generates the full solve() function plan for the agent."""

    memory_texts = "\n".join(f"- {m.text}" for m in memory_items) or "None"

    prompt_template = load_prompt(prompt_path)

    prompt = prompt_template.format(
        tool_descriptions=tool_descriptions,
        user_input=user_input
    )

    # 🧠 Dynamic Memory Injection (does not modify prompt file)
    if memory_texts and memory_texts != "None":
        prompt += f"\n\n📜 History / Memory:\n{memory_texts}\n"
        prompt += "\n❗ IMPORTANT: If the History above shows that you have already retrieved the necessary information, DO NOT call the tool again. Instead, synthesize the answer and return 'FINAL_ANSWER: ...'."

    log("decision", "=" * 50)
    log("decision", f"DECISION STEP STARTED (Step {step_num}/{max_steps})")
    log("decision", f"User Input: {user_input}")
    log("decision", f"Intent: {perception.intent}")
    log("decision", f"Entities: {perception.entities}")
    log("decision", f"Memory Items: {len(memory_items)}")
    log("decision", f"Prompt:\n{prompt}")
    log("decision", "=" * 50)


    try:
        raw = (await model.generate_text(prompt)).strip()
        log("plan", f"LLM output: {raw}")

        # If fenced in ```python ... ```, extract
        if raw.startswith("```"):
            raw = raw.strip("`").strip()
            if raw.lower().startswith("python"):
                raw = raw[len("python"):].strip()

        if re.search(r"^\s*(async\s+)?def\s+solve\s*\(", raw, re.MULTILINE):
            return raw  # ✅ Correct, it's a full function
        elif "FINAL_ANSWER:" in raw:
            return raw # ✅ Correct, it's a final answer
        else:
            log("plan", "⚠️ LLM did not return a valid solve(). Defaulting to FINAL_ANSWER")
            return "FINAL_ANSWER: [Could not generate valid solve()]"


    except Exception as e:
        log("plan", f"⚠️ Planning failed: {e}")
        return "FINAL_ANSWER: [unknown]"
