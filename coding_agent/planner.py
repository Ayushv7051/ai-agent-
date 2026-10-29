"""
Coding Agent Planner.
Determines file architecture, dependencies, and execution steps for requested projects.
"""

from typing import Dict, Any, List
from coding_agent.project_types import get_project_type_config


class CodingPlanner:
    """Plans project structure and required source code components."""

    @staticmethod
    def plan_project(project_name: str, project_type: str, goal_description: str) -> Dict[str, Any]:
        """Produces a structured architectural blueprint for a new software project."""
        cfg = get_project_type_config(project_type)
        return {
            "project_name": project_name.strip().replace(" ", "_"),
            "project_type": project_type.lower(),
            "goal": goal_description,
            "entrypoint": cfg.get("entrypoint", "main.py"),
            "test_runner": cfg.get("test_runner", "python -m unittest"),
            "standard_files": cfg.get("standard_files", ["main.py", "README.md"]),
            "steps": [
                "Create project folder",
                "Generate module source code",
                "Generate unit tests",
                "Execute program",
                "Run test suite",
                "Verify completion"
            ]
        }
