"""
StatMind — Task management tools for ScheduleAgent.
"""

from typing import Optional
from datetime import datetime, timedelta
from google.adk.tools import tool
from db.database import get_db_session
from db.models import Task


@tool
def create_task(
    title: str,
    project: str,
    due_date: Optional[str] = None,
    priority: str = "medium",
    notes: Optional[str] = None,
) -> dict:
    """
    Create a new research/academic task.

    Args:
        title: Task title. E.g. "Submit BAB IV draft to advisor"
        project: Project name. E.g. "Skripsi", "Metodologi Survei", "Gen AI Hackathon"
        due_date: ISO date string. E.g. "2025-05-15" or "2025-05-15T14:00:00"
        priority: "high", "medium", or "low". Default: "medium"
        notes: Optional extra context.

    Returns:
        dict with the created task details.
    """
    with get_db_session() as session:
        task = Task(
            title=title,
            project=project,
            due_date=datetime.fromisoformat(due_date) if due_date else None,
            priority=priority,
            status="pending",
            notes=notes,
        )
        session.add(task)
        session.commit()
        session.refresh(task)
        return {
            "task_id": task.id,
            "title": task.title,
            "project": task.project,
            "due_date": str(task.due_date) if task.due_date else None,
            "priority": task.priority,
            "status": task.status,
            "message": f"Task '{title}' created successfully.",
        }


@tool
def update_task(
    task_id: int,
    title: Optional[str] = None,
    due_date: Optional[str] = None,
    priority: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    """
    Update an existing task's details.

    Args:
        task_id: The integer ID of the task to update.
        title: New title (optional).
        due_date: New due date ISO string (optional).
        priority: New priority: "high", "medium", or "low" (optional).
        notes: Updated notes (optional).

    Returns:
        dict with updated task details.
    """
    with get_db_session() as session:
        task = session.get(Task, task_id)
        if not task:
            return {"error": f"No task found with ID {task_id}."}
        if title:
            task.title = title
        if due_date:
            task.due_date = datetime.fromisoformat(due_date)
        if priority:
            task.priority = priority
        if notes:
            task.notes = notes
        session.commit()
        return {
            "task_id": task.id,
            "title": task.title,
            "project": task.project,
            "due_date": str(task.due_date) if task.due_date else None,
            "priority": task.priority,
            "status": task.status,
        }


@tool
def complete_task(task_id: int) -> dict:
    """
    Mark a task as completed.

    Args:
        task_id: The integer ID of the task.

    Returns:
        dict confirming the task completion.
    """
    with get_db_session() as session:
        task = session.get(Task, task_id)
        if not task:
            return {"error": f"No task found with ID {task_id}."}
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        session.commit()
        return {
            "task_id": task.id,
            "title": task.title,
            "status": "completed",
            "message": f"Task '{task.title}' marked as completed.",
        }


@tool
def list_tasks(
    project: Optional[str] = None,
    status_filter: Optional[str] = "pending",
    priority_filter: Optional[str] = None,
) -> list:
    """
    List research tasks, optionally filtered by project, status, or priority.

    Args:
        project: Filter by project name (optional).
        status_filter: "pending", "completed", or None for all. Default: "pending"
        priority_filter: "high", "medium", or "low" (optional).

    Returns:
        list of task summaries sorted by due date.
    """
    with get_db_session() as session:
        query = session.query(Task)
        if project:
            query = query.filter(Task.project.ilike(f"%{project}%"))
        if status_filter:
            query = query.filter(Task.status == status_filter)
        if priority_filter:
            query = query.filter(Task.priority == priority_filter)
        tasks = query.order_by(Task.due_date.asc()).limit(30).all()
        return [
            {
                "task_id": t.id,
                "title": t.title,
                "project": t.project,
                "due_date": str(t.due_date) if t.due_date else "No deadline",
                "priority": t.priority,
                "status": t.status,
            }
            for t in tasks
        ]


@tool
def get_upcoming_deadlines(days_ahead: int = 7) -> list:
    """
    Get all tasks with deadlines in the next N days.

    Args:
        days_ahead: Number of days to look ahead. Default: 7.

    Returns:
        list of upcoming tasks sorted by due date.
    """
    cutoff = datetime.utcnow() + timedelta(days=days_ahead)
    with get_db_session() as session:
        tasks = (
            session.query(Task)
            .filter(Task.status == "pending")
            .filter(Task.due_date <= cutoff)
            .filter(Task.due_date >= datetime.utcnow())
            .order_by(Task.due_date.asc())
            .all()
        )
        return [
            {
                "task_id": t.id,
                "title": t.title,
                "project": t.project,
                "due_date": str(t.due_date),
                "priority": t.priority,
                "days_remaining": (t.due_date - datetime.utcnow()).days,
            }
            for t in tasks
        ]
