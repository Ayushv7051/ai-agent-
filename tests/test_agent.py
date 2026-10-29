"""
Core Functionality Tests for Ayush AI.
Validates office file generators, web search, memory persistence,
computer tool allowlists, sandboxed file operations, command executor,
coding agent, and task manager.
"""

import os
import sys
import unittest
from pathlib import Path

# Ensure project root is dynamically in sys.path when running directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from config import WORD_DIR, EXCEL_DIR, PPT_DIR, WORKSPACE_DIR
from agent.brain import check_ollama
from agent.memory import load_memory, save_memory, add_memory, get_relevant_memory
from agent.documents import create_word
from agent.excel import create_excel
from agent.powerpoint import create_powerpoint
from agent.search import web_search
from agent.computer import is_application_allowed, open_file
from agent.file_ops import create_file, read_file, list_files, copy_file
from agent.command_executor import execute_sandboxed_command
from agent.task_manager import task_manager
from agent.task_state import TaskStatus
import coding_agent
from main import app


class TestAgentCore(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_01_ollama_check(self):
        """Validates that check_ollama returns status without throwing exceptions."""
        is_online, msg, details = check_ollama()
        self.assertIsInstance(is_online, bool)
        self.assertIsInstance(msg, str)
        self.assertIsInstance(details, dict)

    def test_02_memory_operations(self):
        """Tests reading, updating, and formatting personal memory."""
        orig_mem = load_memory()
        self.assertIn("name", orig_mem)
        
        # Test adding preference
        updated = add_memory(key="unit_test_pref", value="testing_value_123")
        self.assertEqual(updated["preferences"].get("unit_test_pref"), "testing_value_123")

        # Test prompt context formatting
        prompt_ctx = get_relevant_memory()
        self.assertIn("Ayush", prompt_ctx)
        self.assertIn("testing_value_123", prompt_ctx.lower())

    def test_03_word_creation(self):
        """Tests creation and on-disk verification of Microsoft Word document."""
        res = create_word(
            filename="unit_test_doc.docx",
            title="Automated Unit Test Document",
            content="## Overview\nThis is a test paragraph.\n- Bullet point one\n- Bullet point two"
        )
        self.assertTrue(res["success"])
        self.assertTrue(res["verification"]["verified"])
        expected_file = WORD_DIR / "unit_test_doc.docx"
        self.assertTrue(expected_file.exists())
        self.assertGreater(expected_file.stat().st_size, 1000)

    def test_04_excel_creation(self):
        """Tests creation, styling, and verification of an Excel spreadsheet."""
        headers = ["ID", "Name", "Role", "Rating"]
        rows = [
            [1, "Ayush", "Engineer", 9.8],
            [2, "Assistant", "AI Agent", 9.9],
            [3, "Tester", "QA", 9.5]
        ]
        res = create_excel(
            filename="unit_test_sheet.xlsx",
            headers=headers,
            rows=rows
        )
        self.assertTrue(res["success"])
        self.assertTrue(res["verification"]["verified"])
        expected_file = EXCEL_DIR / "unit_test_sheet.xlsx"
        self.assertTrue(expected_file.exists())
        self.assertGreater(expected_file.stat().st_size, 1000)

    def test_05_powerpoint_creation(self):
        """Tests creation and verification of PowerPoint presentation slides."""
        slides = [
            {"title": "Ayush AI Architecture", "content": "Autonomous Local Assistant"},
            {"title": "Core Modules", "content": "Ollama LLM\nPlaywright Automation\nOffice Generators"},
            {"title": "Security", "content": "Strict Path Containment\nHuman-in-the-loop Approvals"}
        ]
        res = create_powerpoint(
            filename="unit_test_pres.pptx",
            slides=slides
        )
        self.assertTrue(res["success"])
        self.assertTrue(res["verification"]["verified"])
        expected_file = PPT_DIR / "unit_test_pres.pptx"
        self.assertTrue(expected_file.exists())
        self.assertEqual(res["result"]["slide_count"], 3)

    def test_06_web_search(self):
        """Tests DuckDuckGo search provider integration."""
        results = web_search("Python programming language", max_results=3)
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        first = results[0]
        self.assertIn("title", first)
        self.assertIn("url", first)
        self.assertIn("description", first)

    def test_07_computer_allowlist(self):
        """Verifies safe application allowlist enforcement."""
        self.assertTrue(is_application_allowed("notepad"))
        self.assertTrue(is_application_allowed("calc"))
        self.assertTrue(is_application_allowed("calculator"))
        self.assertTrue(is_application_allowed("mspaint"))
        self.assertTrue(is_application_allowed("browser"))
        self.assertTrue(is_application_allowed("chrome"))
        self.assertTrue(is_application_allowed("edge"))
        self.assertTrue(is_application_allowed("vscode"))
        self.assertTrue(is_application_allowed("code"))

        # Dangerous or unpermitted apps must be rejected
        self.assertFalse(is_application_allowed("cmd.exe"))
        self.assertFalse(is_application_allowed("powershell.exe"))
        self.assertFalse(is_application_allowed("regedit"))

    def test_08_sandboxed_file_ops(self):
        """Tests safe file creation, reading, and copying inside workspace/."""
        # 1. Create file
        cf_res = create_file("test_sandbox_file.txt", "Sample sandboxed file content.")
        self.assertTrue(cf_res["success"])
        self.assertTrue(cf_res["verification"]["verified"])

        # 2. Read file
        rf_res = read_file("test_sandbox_file.txt")
        self.assertTrue(rf_res["success"])
        self.assertIn("Sample sandboxed", rf_res["result"]["content"])

        # 3. Copy file
        cp_res = copy_file("test_sandbox_file.txt", "test_sandbox_copy.txt")
        self.assertTrue(cp_res["success"])

        # 4. List files
        lf_res = list_files()
        self.assertTrue(lf_res["success"])
        names = [item["name"] for item in lf_res["result"]["items"]]
        self.assertIn("test_sandbox_file.txt", names)

    def test_09_command_executor(self):
        """Tests sandboxed execution of allowlisted python command inside workspace/."""
        cmd_res = execute_sandboxed_command('python -c "print(10 + 20)"')
        self.assertTrue(cmd_res["success"])
        self.assertEqual(cmd_res["result"]["stdout"].strip(), "30")

    def test_10_coding_agent_project_lifecycle(self):
        """Tests autonomous coding agent creating, running, and testing a Python project."""
        files = {
            "calculator.py": "def add(a, b):\n    return a + b\n\ndef multiply(a, b):\n    return a * b\n",
            "main.py": "from calculator import add, multiply\nprint('Add:', add(2, 3))\nprint('Mul:', multiply(3, 4))\n",
            "test_calculator.py": (
                "import unittest\nfrom calculator import add, multiply\n"
                "class TestCalc(unittest.TestCase):\n"
                "    def test_add(self):\n"
                "        self.assertEqual(add(2, 3), 5)\n"
                "    def test_mul(self):\n"
                "        self.assertEqual(multiply(3, 4), 12)\n"
                "if __name__ == '__main__':\n"
                "    unittest.main()\n"
            )
        }
        res = coding_agent.create_and_verify_project(
            project_name="unit_test_calc_proj",
            project_type="python",
            description="Simple calculator project for testing",
            files=files,
            run_entrypoint=True
        )
        self.assertTrue(res["success"])
        self.assertTrue(res["verification"]["verified"])
        self.assertIn("calculator.py", res["result"]["files_created"])
        self.assertTrue(res["result"]["tests"]["passed"])

    def test_11_task_manager(self):
        """Tests task creation, step tracking, and completion."""
        task = task_manager.create_task("Sample user request", max_steps=8)
        self.assertEqual(task.status, TaskStatus.RUNNING)
        task_manager.update_step(task.task_id, 2, "web_search")
        task_manager.set_status(task.task_id, TaskStatus.COMPLETED, summary="Completed sample.")
        retrieved = task_manager.get_task(task.task_id)
        self.assertEqual(retrieved.status, TaskStatus.COMPLETED)
        self.assertIn("web_search", retrieved.tools_used)

    def test_12_api_health_endpoint(self):
        """Validates /health endpoint structure and decoupling."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("ollama", data)

    def test_13_cli_commands(self):
        """Validates all CLI slash commands (/status, /tools, /memory, /files, /tasks, /help, /exit)."""
        from ayush import handle_slash_command
        import io
        import sys

        for cmd in ["/status", "/tools", "/memory", "/files", "/tasks", "/help"]:
            captured = io.StringIO()
            sys.stdout = captured
            try:
                res = handle_slash_command(cmd)
                self.assertTrue(res)
            finally:
                sys.stdout = sys.__stdout__
        
        # /exit should return False to terminate CLI loop
        captured = io.StringIO()
        sys.stdout = captured
        try:
            self.assertFalse(handle_slash_command("/exit"))
        finally:
            sys.stdout = sys.__stdout__


if __name__ == "__main__":
    unittest.main()

