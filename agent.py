# agent.py

import asyncio
from dotenv import load_dotenv
import os
import yaml
from core.loop import AgentLoop
from core.session import MultiMCP
from core.context import AgentContext
import datetime
import json
from pathlib import Path
from difflib import SequenceMatcher

def log(stage: str, msg: str):
    """Simple timestamped console logger."""
    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] [{stage}] {msg}")

class ConversationHistory:
    """Manages historical conversation storage and similarity matching."""
    def __init__(self, filepath: str = "historical_conversation_store.json"):
        self.filepath = Path(filepath)
        self.history = self._load()
    
    def _load(self) -> list:
        """Load conversation history from JSON file."""
        if self.filepath.exists():
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                log("history", f"Failed to load history: {e}")
                return []
        return []
    
    def _save(self):
        """Save conversation history to JSON file."""
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log("history", f"Failed to save history: {e}")
    
    def similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity ratio between two strings (0.0 to 1.0)."""
        return SequenceMatcher(None, str1.lower().strip(), str2.lower().strip()).ratio()
    
    def search_similar(self, query: str, threshold: float = 0.75) -> dict | None:
        """Search for similar queries in history. Returns best match above threshold."""
        best_match = None
        best_score = 0.0
        
        for entry in self.history:
            score = self.similarity(query, entry["query"])
            if score > best_score and score >= threshold:
                best_score = score
                best_match = entry
        
        if best_match:
            log("history", f"Found similar query (similarity: {best_score:.2%}): {best_match['query'][:60]}...")
            return best_match
        return None
    
    def add(self, query: str, answer: str):
        """Add new conversation to history."""
        entry = {
            "query": query,
            "answer": answer,
            "timestamp": datetime.datetime.now().isoformat()
        }
        self.history.append(entry)
        self._save()
        log("history", f"Saved conversation: {query[:60]}...")

async def main():
    # Load .env variables before anything else
    load_dotenv()
    print("🧠 Cortex-R Agent Ready (env loaded)")
    # Optional: brief sanity check for search keys
    for key in ["GOOGLE_API_KEY", "GOOGLE_CSE_ID"]:
        if os.getenv(key) is None:
            log("env", f"Warning: {key} not set.")
    current_session = None
    
    # Initialize conversation history
    conv_history = ConversationHistory()

    with open("config/profiles.yaml", "r") as f:
        profile = yaml.safe_load(f)
        mcp_servers_list = profile.get("mcp_servers", [])
        mcp_servers = {server["id"]: server for server in mcp_servers_list}

    multi_mcp = MultiMCP(server_configs=list(mcp_servers.values()))
    await multi_mcp.initialize()

    try:
        while True:
            user_input = input("🧑 What do you want to solve today? → ")
            if user_input.lower() == 'exit':
                break
            if user_input.lower() == 'new':
                current_session = None
                continue
            
            # Check conversation history for similar queries
            cached = conv_history.search_similar(user_input, threshold=0.75)
            if cached:
                print("\n💾 Found similar query in history:")
                print(f"   Previous: {cached['query']}")
                print(f"   Timestamp: {cached['timestamp']}")
                use_cached = input("   Use cached answer? (y/n) → ").lower().strip()
                if use_cached == 'y':
                    print(f"\n💡 Cached Answer: {cached['answer']}")
                    continue

            while True:
                context = AgentContext(
                    user_input=user_input,
                    session_id=current_session,
                    dispatcher=multi_mcp,
                    mcp_server_descriptions=mcp_servers,
                )
                agent = AgentLoop(context)
                if not current_session:
                    current_session = context.session_id

                result = await agent.run()

                if isinstance(result, dict):
                    answer = result["result"]
                    if "FINAL_ANSWER:" in answer:
                        final_answer = answer.split('FINAL_ANSWER:')[1].strip()
                        print(f"\n💡 Final Answer: {final_answer}")
                        # Save to conversation history ONLY for successful final answers
                        original_query = context.user_input if hasattr(context, 'user_input') else user_input
                        conv_history.add(original_query, final_answer)
                        break
                    elif "FURTHER_PROCESSING_REQUIRED:" in answer:
                        user_input = answer.split("FURTHER_PROCESSING_REQUIRED:")[1].strip()
                        print(f"\n🔁 Further Processing Required: {user_input}")
                        continue  # 🧠 Re-run agent with updated input
                    else:
                        # Non-final result; do NOT save to history
                        print(f"\n💡 Final Answer (raw): {answer}")
                        break
                else:
                    # Unexpected non-dict result; do NOT save to history
                    print(f"\n💡 Final Answer (unexpected): {result}")
                    break
    except KeyboardInterrupt:
        print("\n👋 Received exit signal. Shutting down...")

if __name__ == "__main__":
    asyncio.run(main())



# Find the ASCII values of characters in INDIA and then return sum of exponentials of those values.
# How much Anmol singh paid for his DLF apartment via Capbridge? 
# What do you know about Don Tapscott and Anthony Williams?
# What is the relationship between Gensol and Go-Auto?
# which course are we teaching on Canvas LMS? "H:\DownloadsH\How to use Canvas LMS.pdf"
# Summarize this page: https://theschoolof.ai/
# What is the log value of the amount that Anmol singh paid for his DLF apartment via Capbridge? 