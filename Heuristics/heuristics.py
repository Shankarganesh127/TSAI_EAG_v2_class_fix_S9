# heuristics.py
import re
import os
import json
import requests
from dataclasses import dataclass

"""
===========================================================
 Heuristics Module
===========================================================
Provides:
1) sanitize_input(query, allowed_tools)
2) validate_input(query, allowed_tools)
3) run_heuristics(query, allowed_tools)
4) HeuristicResult class
===========================================================
"""

# -----------------------------------------
# Safety Patterns & Configuration
# -----------------------------------------

ADULT_KEYWORDS = [
    "porn", "xxx", "bdsm", "nude", "adult video",
    "deep-throat", "sex ", "hookup", "horny"
]

RACIAL_SLURS = [
    "nigger", "chink", "spic", "kike", "faggot",
    "wetback", "porch monkey"
]

SYSTEM_OVERRIDE_PATTERNS = [
    r"ignore (all )?previous instructions",
    r"override system prompt",
    r"reset your rules",
    r"break free from your constraints",
    r"i command you to",
]

SECRET_KEY_PATTERNS = [
    r"api[_-]?key\s*=\s*['\"]?[A-Za-z0-9_\-]{12,}['\"]?",
    r"password\s*=\s*['\"].+?['\"]",
    r"sk-[A-Za-z0-9]{18,}",
]

MAX_ALLOWED_INPUT_SIZE_MB = 5  # adjustable limit


# -------------------------------------------------
# Result Object Returned by Heuristic Pipeline
# -------------------------------------------------

@dataclass
class HeuristicResult:
    is_valid: bool
    sanitized_query: str
    error_message: str = None


# -------------------------------------------------
#  Function 1: Sanitizer
# -------------------------------------------------

def sanitize_input(query: str, allowed_tools: list):
    """Removes sensitive, malicious, or disallowed content."""

    sanitized = query

    # (1) Remove secret keys
    for pattern in SECRET_KEY_PATTERNS:
        sanitized = re.sub(pattern, "[REDACTED_SECRET]", sanitized, flags=re.I)

    # (2) Remove prompt override attacks
    for pattern in SYSTEM_OVERRIDE_PATTERNS:
        sanitized = re.sub(pattern, "[SYSTEM_OVERRIDE_BLOCKED]", sanitized, flags=re.I)

    # (3) Remove adult content
    for word in ADULT_KEYWORDS:
        sanitized = re.sub(word, "[ADULT_BLOCKED]", sanitized, flags=re.I)

    # (4) Remove oversized inputs
    if len(sanitized.encode("utf-8")) > MAX_ALLOWED_INPUT_SIZE_MB * 1024 * 1024:
        return "[ERROR: Input too large]"

    # (5) Remove query-inside-query
    sanitized = re.sub(r"(query\s*:\s*\{.*?\})",
                       "[NESTED_QUERY_REMOVED]", sanitized, flags=re.I | re.S)

    # (10) Remove racial slurs
    for slur in RACIAL_SLURS:
        sanitized = re.sub(slur, "[OFFENSIVE_CONTENT_REMOVED]", sanitized, flags=re.I)

    # (11) Remove “prompt inside prompt”
    sanitized = re.sub(r"(prompt\s*:\s*\{.*?\})",
                       "[PROMPT_REMOVED]", sanitized, flags=re.I | re.S)

    # (12) Remove non-ASCII
    sanitized = sanitized.encode("ascii", "ignore").decode()

    # (13) Remove/replace unknown tool names
    tool_pattern = re.findall(r"\btool:([A-Za-z_]+)\b", sanitized)
    for t in tool_pattern:
        if t not in allowed_tools:
            sanitized = sanitized.replace(t, "[UNKNOWN_TOOL]")

    return sanitized


# -------------------------------------------------
#  Function 2: Validator
# -------------------------------------------------

def validate_input(query: str, allowed_tools: list):
    """Validates URLs, files, JSON, and tool references."""

    # (6) URL existence check
    urls = re.findall(r"https?://\S+", query)
    for url in urls:
        try:
            r = requests.head(url, timeout=4)
            if r.status_code >= 400:
                return False, f"[ERROR: URL does not exist → {url}]"
        except Exception:
            return False, f"[ERROR: Invalid or unreachable URL → {url}]"

    # (7) File existence check
    files = re.findall(r"(?:file:|path:)\s*(\S+)", query)
    for f in files:
        if not os.path.exists(f):
            return False, f"[ERROR: File not found → {f}]"

    # (8) Corrupted file check
    for f in files:
        try:
            with open(f, "rb") as fp:
                fp.read(2048)  # attempt to read basic header
        except Exception:
            return False, f"[ERROR: Corrupted or unreadable file → {f}]"

    # (9) Invalid JSON detection
    json_candidates = re.findall(r"\{.*?\}", query, flags=re.S)
    for block in json_candidates:
        try:
            json.loads(block)
        except Exception:
            return False, "[ERROR: Invalid JSON detected]"

    # (13) Tool validation
    for tool in re.findall(r"tool:([A-Za-z_]+)", query):
        if tool not in allowed_tools:
            return False, f"[ERROR: Tool '{tool}' is not allowed]"

    return True, None


# -------------------------------------------------
#  Single Wrapper Used by the AI Agent
# -------------------------------------------------

def run_heuristics(raw_query: str, allowed_tools: list) -> HeuristicResult:
    """
    Main function used by the agent.
    
    1. Sanitizes unsafe content.
    2. Validates cleaned input.
    3. Returns a structured result.
    """
    sanitized = sanitize_input(raw_query, allowed_tools)

    # If sanitization produced a direct error
    if sanitized.startswith("[ERROR"):
        return HeuristicResult(is_valid=False, sanitized_query=sanitized, error_message=sanitized)

    is_valid, err = validate_input(sanitized, allowed_tools)

    if is_valid:
        return HeuristicResult(is_valid=True, sanitized_query=sanitized)
    else:
        return HeuristicResult(is_valid=False, sanitized_query=sanitized, error_message=err)
