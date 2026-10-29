"""
Task State Definitions for Ayush AI.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import datetime


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TaskRecord(BaseModel):
    task_id: str
    user_request: str
    status: TaskStatus = TaskStatus.PENDING
    current_step: int = 0
    max_steps: int = 8
    tools_used: List[str] = Field(default_factory=list)
    start_time: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    end_time: Optional[str] = None
    errors: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
