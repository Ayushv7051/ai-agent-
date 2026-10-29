"""
AYUSH AI — Primary CLI Personal Computer Agent for Windows.
Direct terminal interface supporting natural language task execution,
interactive approvals, slash commands, and real-time step progress streaming.
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, Any

# Ensure project root is in sys.path dynamically
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import OLLAMA_MODEL, WORKSPACE_DIR, FILES_DIR, DATA_DIR
from agent.brain import check_ollama
from agent.memory import load_memory, add_memory, get_relevant_memory
from agent.tools import REGISTRY
from agent.orchestrator import orchestrator
from agent.task_manager import task_manager
from agent.file_ops import list_files
from agent.logger import logger

# Terminal color tokens for clean Windows presentation
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def print_banner():
    """Prints the Ayush AI startup banner."""
    ollama_ok, msg, _ = check_ollama()
    status_str = f"{GREEN}Connected{RESET}" if ollama_ok else f"{RED}Disconnected ({msg}){RESET}"
    
    banner = f"""
{CYAN}============================================================
                    AYUSH AI
              Personal AI Agent
============================================================{RESET}

Ollama: {status_str}
Model: {BOLD}{OLLAMA_MODEL}{RESET}
Memory: {GREEN}Enabled{RESET}
Tools: {BOLD}{len(REGISTRY)}{RESET}
Workspace: {GREEN}Ready{RESET} ({WORKSPACE_DIR.name})

{BOLD}Ayush AI is ready.{RESET} Type your task, or {DIM}/help{RESET} for commands.
"""
    print(banner)


def cli_progress_callback(step: int, max_steps: int, action: str, detail: str) -> None:
    """Prints real-time execution step to the terminal."""
    if "✓" in detail:
        print(f"  {GREEN}{detail}{RESET}")
    elif "✗" in detail:
        print(f"  {RED}{detail}{RESET}")
    else:
        print(f"  {CYAN}[{step}/{max_steps}]{RESET} {detail}")


def cli_approval_callback(approval_data: Dict[str, Any]) -> bool:
    """
    Halts execution and interactively asks user for approval in the terminal.
    """
    tool = approval_data.get("tool", "Unknown")
    args = approval_data.get("arguments", {})
    reason = approval_data.get("reason", "Sensitive operation requires confirmation.")

    print(f"\n{YELLOW}{BOLD}" + "=" * 60)
    print("⚠️  APPROVAL REQUIRED")
    print("=" * 60 + f"{RESET}")
    print(f"Tool:   {BOLD}{tool}{RESET}")
    print(f"Reason: {reason}")
    print(f"Parameters:")
    print(json.dumps(args, indent=2))
    print(f"\n{YELLOW}This action cannot be undone.{RESET}")

    try:
        decision = input(f"\nType {BOLD}APPROVE{RESET} or {BOLD}REJECT{RESET}: ").strip().upper()
        if decision == "APPROVE":
            print(f"{GREEN}✓ Action APPROVED. Resuming task execution...{RESET}\n")
            return True
        else:
            print(f"{RED}✗ Action REJECTED. Halting operation safely.{RESET}\n")
            return False
    except (KeyboardInterrupt, EOFError):
        print(f"\n{RED}Action rejected by interrupt.{RESET}\n")
        return False


def handle_slash_command(cmd: str) -> bool:
    """
    Handles CLI slash commands. Returns False if session should terminate.
    """
    clean = cmd.strip().lower()

    if clean in ("/exit", "exit", "quit"):
        print(f"\n{CYAN}Goodbye Ayush! Exiting Ayush AI.{RESET}")
        return False

    elif clean in ("/clear", "clear", "cls"):
        os.system("cls" if os.name == "nt" else "clear")
        print_banner()

    elif clean == "/help":
        print(f"""
{BOLD}Available Commands:{RESET}
  {CYAN}/status{RESET}   - Show system health, Ollama status, tools, and memory
  {CYAN}/tools{RESET}    - List all available tools and categories
  {CYAN}/memory{RESET}   - View your persistent personal memory profile
  {CYAN}/files{RESET}    - List all generated Word, Excel, PPT, and workspace files
  {CYAN}/tasks{RESET}    - Show task execution history
  {CYAN}/clear{RESET}    - Clear the terminal screen
  {CYAN}/restart{RESET}  - Re-initialize session banner
  {CYAN}/exit{RESET}     - Exit the CLI agent

{BOLD}Natural Language Examples:{RESET}
  • Open Notepad and type: Hello Ayush
  • Search Google for Python jobs in Mumbai and create an Excel file
  • Create a Word document named ai_v1.docx titled 'Architecture of Local AI'
  • Create a PowerPoint presentation with 5 slides about Qwen 2.5
  • Create a Python calculator project in workspace
  • Remember that I prefer short, bullet-point answers
  • Take a desktop screenshot
""")

    elif clean == "/status":
        ollama_ok, msg, details = check_ollama()
        active = task_manager.get_active_task()
        print(f"""
{BOLD}System Status:{RESET}
  Ollama:       {GREEN if ollama_ok else RED}{'Connected' if ollama_ok else 'Disconnected'}{RESET}
  Model:        {OLLAMA_MODEL}
  Memory:       Enabled (data/memory.json)
  Browser:      Ready (Playwright Chromium)
  Workspace:    {WORKSPACE_DIR}
  Files:        {FILES_DIR}
  Tools:        {len(REGISTRY)} registered
  Active Task:  {active.user_request if active else 'None'}
""")

    elif clean == "/tools":
        print(f"\n{BOLD}Registered Agent Tools ({len(REGISTRY)}):{RESET}")
        for name, tool_def in sorted(REGISTRY.items()):
            level_color = RED if tool_def.permission_level == "DANGEROUS" else (YELLOW if tool_def.permission_level == "CONFIRM" else GREEN)
            print(f"  • {BOLD}{name:<24}{RESET} [{level_color}{tool_def.permission_level:<9}{RESET}] {tool_def.description}")
        print()

    elif clean == "/memory":
        data = load_memory()
        print(f"\n{BOLD}Personal Memory Profile:{RESET}")
        print(json.dumps(data, indent=2))
        print()

    elif clean == "/files":
        print(f"\n{BOLD}Files inside Sandbox:{RESET}")
        for sub in ["word", "excel", "ppt"]:
            folder = FILES_DIR / sub
            files = [f.name for f in folder.iterdir() if f.is_file() and not f.name.startswith(".")] if folder.exists() else []
            print(f"  {CYAN}{sub.upper()} ({len(files)}):{RESET} {', '.join(files) if files else 'None'}")
        
        ws_files = [f.name for f in WORKSPACE_DIR.iterdir() if not f.name.startswith(".")] if WORKSPACE_DIR.exists() else []
        print(f"  {CYAN}WORKSPACE ({len(ws_files)}):{RESET} {', '.join(ws_files) if ws_files else 'None'}\n")

    elif clean == "/tasks":
        tasks = task_manager.list_tasks()
        print(f"\n{BOLD}Task Execution History ({len(tasks)}):{RESET}")
        for t in reversed(tasks[-10:]):
            st_color = GREEN if t.status.value == "COMPLETED" else (RED if t.status.value == "FAILED" else YELLOW)
            print(f"  [{t.task_id}] [{st_color}{t.status.value:<10}{RESET}] {t.user_request[:50]} (Tools: {', '.join(t.tools_used) or 'None'})")
        print()

    elif clean == "/restart":
        print_banner()

    else:
        print(f"{RED}Unknown command '{cmd}'. Type /help for available commands.{RESET}")

    return True


def run_cli_loop():
    """Main terminal loop."""
    print_banner()

    # Pre-check Ollama warning
    ollama_ok, msg, _ = check_ollama()
    if not ollama_ok:
        print(f"{YELLOW}[WARNING] Ollama is not running on http://localhost:11434.{RESET}")
        print(f"{YELLOW}Please start Ollama ('ollama serve') so Ayush AI can reason.{RESET}\n")

    while True:
        try:
            user_input = input(f"{BOLD}You:{RESET}\n> ").strip()
            if not user_input:
                continue

            # Check for slash commands
            if user_input.startswith("/"):
                should_continue = handle_slash_command(user_input)
                if not should_continue:
                    break
                continue

            print(f"\n{CYAN}{BOLD}Ayush AI:{RESET}")
            
            # Execute with live terminal progress streaming and interactive approvals
            response = orchestrator.run(
                user_message=user_input,
                progress_callback=cli_progress_callback,
                approval_callback=cli_approval_callback
            )

            print(f"\n{response.response}\n")

        except KeyboardInterrupt:
            print(f"\n\n{YELLOW}Interrupted. Type /exit to quit or enter a new command.{RESET}\n")
        except EOFError:
            print(f"\n{CYAN}Session closed. Goodbye!{RESET}")
            break
        except Exception as e:
            print(f"\n{RED}[Error] Unexpected exception: {str(e)}{RESET}\n")
            logger.error(f"CLI loop error: {e}")


if __name__ == "__main__":
    run_cli_loop()
