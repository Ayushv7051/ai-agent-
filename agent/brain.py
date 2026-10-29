"""
AI Brain Module for Ayush AI.
Interfaces with local Ollama running qwen3:8b.
Handles tool-calling schema generation, structured inference, and fallback error handling.
"""

import json
import re
import httpx
import ollama
from typing import List, Dict, Any, Tuple, Generator, Optional

from config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_NUM_CTX, OLLAMA_NUM_THREADS
from agent.memory import get_relevant_memory
from agent.logger import logger
from agent.schemas import ToolInvocation

SYSTEM_PERSONALITY = """You are Ayush's personal AI assistant.
Be practical, helpful and concise.
Use simple language.
When a task requires a tool, use the appropriate tool.
Never pretend that a task was completed if it was not actually completed.
Do not execute any financial transactions, stock trades, or arbitrary shell commands.
If asked to create a Word, Excel, or PowerPoint document, use the corresponding tool and report the exact file name and path."""


def check_ollama() -> Tuple[bool, str, Dict[str, Any]]:
    """
    Checks if the local Ollama instance is accessible and whether the required model is loaded.
    Never raises an exception or crashes the application.
    """
    try:
        client = ollama.Client(host=OLLAMA_HOST)
        models_response = client.list()
        
        # Handle dict response or list of objects
        model_names = []
        if hasattr(models_response, "models"):
            for m in models_response.models:
                name = getattr(m, "model", getattr(m, "name", str(m)))
                model_names.append(name)
        elif isinstance(models_response, dict) and "models" in models_response:
            for m in models_response["models"]:
                model_names.append(m.get("name", m.get("model", "")))

        has_target = any(OLLAMA_MODEL in name for name in model_names)

        details = {
            "host": OLLAMA_HOST,
            "target_model": OLLAMA_MODEL,
            "model_found": has_target,
            "available_models": model_names
        }

        if has_target:
            return True, f"Ollama is online with model '{OLLAMA_MODEL}'.", details
        else:
            return True, f"Ollama is running, but model '{OLLAMA_MODEL}' was not found.", details

    except Exception as e:
        logger.warning(f"Ollama connection check failed: {e}")
        return False, "Cannot connect to Ollama. Please start Ollama and try again.", {
            "host": OLLAMA_HOST,
            "error": str(e)
        }


def build_system_prompt() -> str:
    """Combines base personality with active user memory context."""
    memory_context = get_relevant_memory()
    prompt_parts = [SYSTEM_PERSONALITY.strip()]
    if memory_context:
        prompt_parts.append("\n=== USER MEMORY & PREFERENCES ===\n" + memory_context)
    return "\n\n".join(prompt_parts)


def parse_tool_invocation_from_text(content: str) -> Optional[List[ToolInvocation]]:
    """
    Fallback parser for models that output structured JSON blocks in text
    instead of utilizing native tool_calls.
    """
    if not content:
        return None

    # Look for ```json ... ``` blocks or raw {"tool": ...}
    json_blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if not json_blocks:
        # Check if entire content is valid JSON tool invocation
        trimmed = content.strip()
        if trimmed.startswith("{") and trimmed.endswith("}"):
            json_blocks = [trimmed]

    invocations = []
    for block in json_blocks:
        try:
            parsed = json.loads(block)
            if isinstance(parsed, dict) and "tool" in parsed:
                invocations.append(
                    ToolInvocation(
                        tool=parsed["tool"],
                        arguments=parsed.get("arguments", {})
                    )
                )
            elif isinstance(parsed, dict) and "function" in parsed and "parameters" in parsed:
                invocations.append(
                    ToolInvocation(
                        tool=parsed["function"],
                        arguments=parsed.get("parameters", {})
                    )
                )
        except Exception:
            continue

    return invocations if invocations else None


def ask_model(
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Sends conversational messages to Ollama with optional tools schema.
    Returns structured output containing message content and any detected tool invocations.
    """
    online, msg, _ = check_ollama()
    if not online:
        return {
            "role": "assistant",
            "content": "Cannot connect to Ollama. Please start Ollama and try again.",
            "tool_calls": [],
            "error": msg
        }

    client = ollama.Client(host=OLLAMA_HOST, timeout=300.0)

    # Prepend system prompt if not present
    all_messages = []
    has_system = any(m.get("role") == "system" for m in messages)
    if not has_system:
        all_messages.append({"role": "system", "content": build_system_prompt()})
    all_messages.extend(messages)

    try:
        logger.info(f"Calling Ollama model '{OLLAMA_MODEL}' (tools provided: {len(tools) if tools else 0})")
        kwargs = {
            "model": OLLAMA_MODEL,
            "messages": all_messages,
            "options": {
                "num_ctx": OLLAMA_NUM_CTX,
                "num_thread": OLLAMA_NUM_THREADS,
                "num_gpu": 99,
            }
        }
        if tools:
            kwargs["tools"] = tools

        response = client.chat(**kwargs)
        resp_message = response.message

        content = resp_message.content or ""
        detected_tool_calls: List[ToolInvocation] = []

        # 1. Inspect Native Tool Calls
        if hasattr(resp_message, "tool_calls") and resp_message.tool_calls:
            for tc in resp_message.tool_calls:
                func = getattr(tc, "function", None)
                if func:
                    fn_name = getattr(func, "name", "")
                    fn_args = getattr(func, "arguments", {})
                    if isinstance(fn_args, str):
                        try:
                            fn_args = json.loads(fn_args)
                        except Exception:
                            fn_args = {}
                    detected_tool_calls.append(ToolInvocation(tool=fn_name, arguments=fn_args))

        # 2. Inspect fallback text JSON blocks if native tool_calls was empty
        if not detected_tool_calls:
            fallback_calls = parse_tool_invocation_from_text(content)
            if fallback_calls:
                detected_tool_calls.extend(fallback_calls)

        return {
            "role": "assistant",
            "content": content,
            "tool_calls": detected_tool_calls,
            "raw_response": response
        }

    except Exception as e:
        logger.error(f"Error calling Ollama: {e}")
        return {
            "role": "assistant",
            "content": f"An error occurred while communicating with the AI model: {str(e)}",
            "tool_calls": [],
            "error": str(e)
        }


def stream_model_response(messages: List[Dict[str, Any]]) -> Generator[str, None, None]:
    """Streams response tokens from Ollama for live chat generation."""
    online, msg, _ = check_ollama()
    if not online:
        yield "Cannot connect to Ollama. Please start Ollama and try again."
        return

    client = ollama.Client(host=OLLAMA_HOST, timeout=300.0)
    all_messages = []
    if not any(m.get("role") == "system" for m in messages):
        all_messages.append({"role": "system", "content": build_system_prompt()})
    all_messages.extend(messages)

    try:
        stream = client.chat(
            model=OLLAMA_MODEL,
            messages=all_messages,
            stream=True,
            options={
                "num_ctx": OLLAMA_NUM_CTX,
                "num_thread": OLLAMA_NUM_THREADS,
                "num_gpu": 99,
            }
        )
        for chunk in stream:
            content = chunk.message.content or ""
            if content:
                yield content
    except Exception as e:
        logger.error(f"Streaming error from Ollama: {e}")
        yield f"\n[Error: {str(e)}]"
