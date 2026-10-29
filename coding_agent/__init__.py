"""
Coding Agent Package for Ayush AI.
Provides complete autonomous project creation, code execution, testing, and verification.
"""

from typing import Dict, Any, Optional
from coding_agent.planner import CodingPlanner
from coding_agent.file_manager import ProjectFileManager
from coding_agent.executor import ProjectExecutor
from coding_agent.tester import ProjectTester
from coding_agent.debugger import ProjectDebugger
from agent.logger import logger


def create_and_verify_project(
    project_name: str,
    project_type: str,
    description: str,
    files: Dict[str, str],
    run_entrypoint: bool = True
) -> Dict[str, Any]:
    """
    Executes the full coding agent lifecycle:
    1. Plan -> 2. Scaffold Folder -> 3. Write Files -> 4. Run -> 5. Test -> 6. Verify.
    """
    logger.info(f"Coding Agent initiating project '{project_name}' ({project_type})")
    
    # 1. Plan
    plan = CodingPlanner.plan_project(project_name, project_type, description)
    file_mgr = ProjectFileManager(project_name)
    
    # 2. Write Files
    written_files = []
    for rel_path, content in files.items():
        res = file_mgr.write_source_file(rel_path, content)
        if res.get("success"):
            written_files.append(rel_path)

    executor = ProjectExecutor(file_mgr.project_dir)
    tester = ProjectTester(file_mgr.project_dir)

    # 3. Run Entrypoint if requested
    exec_outcome = None
    if run_entrypoint:
        entrypoint = plan.get("entrypoint", "main.py")
        exec_outcome = executor.run_entrypoint(entrypoint)

    # 4. Run Tests if present
    test_outcome = None
    has_tests = any("test" in f.lower() for f in files.keys())
    if has_tests:
        test_outcome = tester.run_unittest()

    # 5. Verification
    all_files_exist = len(written_files) == len(files)
    run_ok = (exec_outcome is None) or exec_outcome.get("success", False)
    test_ok = (test_outcome is None) or test_outcome.get("passed", False)
    overall_ok = all_files_exist and run_ok and (test_ok if has_tests else True)

    return {
        "success": overall_ok,
        "result": {
            "project_name": project_name,
            "project_dir": str(file_mgr.project_dir),
            "files_created": written_files,
            "execution": exec_outcome.get("result") if exec_outcome else None,
            "tests": test_outcome
        },
        "error": exec_outcome.get("error") if exec_outcome and not run_ok else None,
        "verification": {
            "verified": overall_ok,
            "details": f"Created {len(written_files)} files. Program execution: {'Passed' if run_ok else 'Failed'}. Tests: {'Passed' if test_ok else 'N/A'}."
        }
    }


__all__ = [
    "CodingPlanner",
    "ProjectFileManager",
    "ProjectExecutor",
    "ProjectTester",
    "ProjectDebugger",
    "create_and_verify_project"
]
