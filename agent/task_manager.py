"""
Task Manager for Ayush AI.
Tracks task execution history, status transitions, and long-running processes.
"""

import uuid
import datetime
from typing import Dict, List, Optional
from agent.task_state import TaskRecord, TaskStatus
from agent.logger import logger


class TaskManager:
    """Manages active and past agent tasks."""

    def __init__(self):
        self._tasks: Dict[str, TaskRecord] = {}
        self._active_task_id: Optional[str] = None

    def create_task(self, user_request: str, max_steps: int = 8) -> TaskRecord:
        """Creates and registers a new task."""
        task_id = str(uuid.uuid4())[:8]
        record = TaskRecord(
            task_id=task_id,
            user_request=user_request,
            status=TaskStatus.RUNNING,
            max_steps=max_steps
        )
        self._tasks[task_id] = record
        self._active_task_id = task_id
        logger.info(f"Task [{task_id}] started: '{user_request}'")
        return record

    def get_active_task(self) -> Optional[TaskRecord]:
        """Returns the currently running task if any."""
        if self._active_task_id and self._active_task_id in self._tasks:
            return self._tasks[self._active_task_id]
        return None

    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        return self._tasks.get(task_id)

    def list_tasks(self) -> List[TaskRecord]:
        return list(self._tasks.values())

    def update_step(self, task_id: str, step: int, tool_name: Optional[str] = None) -> None:
        if task_id in self._tasks:
            self._tasks[task_id].current_step = step
            if tool_name and tool_name not in self._tasks[task_id].tools_used:
                self._tasks[task_id].tools_used.append(tool_name)

    def set_status(self, task_id: str, status: TaskStatus, error: Optional[str] = None, summary: Optional[str] = None) -> None:
        if task_id in self._tasks:
            task = self._tasks[task_id]
            task.status = status
            if error:
                task.errors.append(error)
            if summary:
                task.summary = summary
            if status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                task.end_time = datetime.datetime.now().isoformat()
                if self._active_task_id == task_id:
                    self._active_task_id = None
            logger.info(f"Task [{task_id}] status transitioned to {status.value}")


task_manager = TaskManager()
