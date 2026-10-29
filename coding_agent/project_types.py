"""
Project Type Registry for Coding Agent.
Supports selecting proper workflow scaffolding and execution runners.
"""

from typing import Dict, Any, List

SUPPORTED_PROJECT_TYPES: Dict[str, Dict[str, Any]] = {
    "python": {
        "name": "Python Application",
        "entrypoint": "main.py",
        "runner": "python",
        "test_runner": "python -m unittest",
        "standard_files": ["main.py", "test_app.py", "README.md"]
    },
    "javascript": {
        "name": "JavaScript Application",
        "entrypoint": "index.js",
        "runner": "node",
        "test_runner": "npm test",
        "standard_files": ["index.js", "package.json"]
    },
    "node": {
        "name": "Node.js Server/CLI",
        "entrypoint": "server.js",
        "runner": "node",
        "test_runner": "npm test",
        "standard_files": ["server.js", "package.json"]
    },
    "html": {
        "name": "Static HTML/CSS/JS Website",
        "entrypoint": "index.html",
        "runner": "browser",
        "standard_files": ["index.html", "style.css", "script.js"]
    },
    "react": {
        "name": "React Web Application",
        "entrypoint": "src/App.jsx",
        "runner": "npm run dev",
        "standard_files": ["src/App.jsx", "package.json"]
    },
    "nextjs": {
        "name": "Next.js Fullstack Application",
        "entrypoint": "pages/index.js",
        "runner": "npm run dev",
        "standard_files": ["pages/index.js", "package.json"]
    }
}


def get_project_type_config(project_type: str) -> Dict[str, Any]:
    norm = project_type.strip().lower()
    return SUPPORTED_PROJECT_TYPES.get(norm, SUPPORTED_PROJECT_TYPES["python"])
