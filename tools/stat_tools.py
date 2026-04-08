"""
Pure-Python statistical tools — no R, no scipy dependency needed for hackathon demo.
Called as function declarations by the google-genai client directly.
"""

import json
import statistics
import math
from typing import Optional
from datetime import datetime, timedelta

from db.database import get_db
from db.models import Task, AnalysisJob, ResearchNote, Dataset


# ─── Statistical computation ──────────────────────────────────────────────────

def cronbach_alpha(items_json: str) -> dict:
    """
    Calculate Cronbach's alpha reliability for a survey instrument.

    Args:
        items_json: 2D JSON array — rows = respondents, columns = items.
                    Example: "[[4,3,5],[3,2,4],[5,5,5],[4,4,4]]"

    Returns:
        dict with alpha, interpretation, item-total correlations, and flagged items.
    """
    try:
        data = json.loads(items_json)
        n_items = len(data[0])
        n_subjects = len(data)
        if n_subjects < 2:
            return {"error": "Need at least 2 respondents to compute alpha."}

        item_vars = [statistics.variance([row[i] for row in data]) for i in range(n_items)]
        totals = [sum(row) for row in data]
        total_var = statistics.variance(totals)

        alpha = round((n_items / (n_items - 1)) * (1 - sum(item_vars) / total_var), 4)

        if alpha >= 0.9:
            label = "Excellent (α ≥ 0.9)"
        elif alpha >= 0.8:
            label = "Good (α ≥ 0.8)"
        elif alpha >= 0.7:
            label = "Acceptable (α ≥ 0.7)"
        elif alpha >= 0.6:
            label = "Questionable (α ≥ 0.6) — consider revising items"
        else:
            label = "Poor (α < 0.6) — instrument needs revision"

        # Item-total correlations (corrected)
        itc = {}
        for i in range(n_items):
            item_scores = [row[i] for row in data]
            rest = [sum(row) - row[i] for row in data]
            m_i, m_r = statistics.mean(item_scores), statistics.mean(rest)
            cov = sum((a - m_i) * (b - m_r) for a, b in zip(item_scores, rest)) / (n_subjects - 1)
            sd_i = statistics.stdev(item_scores)
            sd_r = statistics.stdev(rest)
            corr = round(cov / (sd_i * sd_r), 4) if sd_i > 0 and sd_r > 0 else 0.0
            itc[f"item_{i+1}"] = corr

        return {
            "alpha": alpha,
            "interpretation": label,
            "n_items": n_items,
            "n_respondents": n_subjects,
            "item_total_correlations": itc,
            "flagged_items": [k for k, v in itc.items() if v < 0.3],
        }
    except Exception as e:
        return {"error": str(e)}


def descriptive_stats(values_json: str, variable_name: str = "variable") -> dict:
    """
    Compute descriptive statistics for a numeric variable.

    Args:
        values_json: JSON array of numbers. Example: "[4.2, 3.8, 5.0, 4.5, 3.1]"
        variable_name: Label for the variable.

    Returns:
        dict with n, mean, median, std, min, max, quartiles, skewness, and interpretation.
    """
    try:
        vals = [float(v) for v in json.loads(values_json) if v is not None]
        n = len(vals)
        if n < 2:
            return {"error": "Need at least 2 values."}
        s = sorted(vals)
        mean = statistics.mean(vals)
        median = statistics.median(vals)
        std = statistics.stdev(vals)
        q1 = s[n // 4]
        q3 = s[(3 * n) // 4]
        skew = round((3 * (mean - median) / std), 4) if std > 0 else 0.0

        return {
            "variable": variable_name,
            "n": n,
            "mean": round(mean, 4),
            "median": round(median, 4),
            "std_dev": round(std, 4),
            "min": min(vals),
            "max": max(vals),
            "q1": q1,
            "q3": q3,
            "iqr": round(q3 - q1, 4),
            "skewness": skew,
            "skewness_note": (
                "Approximately symmetric" if abs(skew) < 0.5
                else "Moderately skewed" if abs(skew) < 1.0
                else "Highly skewed — consider transformation"
            ),
        }
    except Exception as e:
        return {"error": str(e)}


def pearson_correlation(x_json: str, y_json: str, x_label: str = "X", y_label: str = "Y") -> dict:
    """
    Compute Pearson correlation between two variables.

    Args:
        x_json: JSON array for variable X.
        y_json: JSON array for variable Y.
        x_label: Name of X variable.
        y_label: Name of Y variable.

    Returns:
        dict with r, r², interpretation, and significance note.
    """
    try:
        x = [float(v) for v in json.loads(x_json)]
        y = [float(v) for v in json.loads(y_json)]
        if len(x) != len(y):
            return {"error": "X and Y must have the same length."}
        n = len(x)
        mx, my = statistics.mean(x), statistics.mean(y)
        num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
        den = math.sqrt(sum((xi - mx)**2 for xi in x) * sum((yi - my)**2 for yi in y))
        r = round(num / den, 4) if den > 0 else 0.0
        r2 = round(r ** 2, 4)

        if abs(r) >= 0.7:
            strength = "Strong"
        elif abs(r) >= 0.4:
            strength = "Moderate"
        elif abs(r) >= 0.2:
            strength = "Weak"
        else:
            strength = "Negligible"
        direction = "positive" if r >= 0 else "negative"

        return {
            "r": r,
            "r_squared": r2,
            "n": n,
            "interpretation": f"{strength} {direction} correlation",
            "note": "Use α=0.05 significance table for n to confirm statistical significance.",
        }
    except Exception as e:
        return {"error": str(e)}


# ─── Task management ──────────────────────────────────────────────────────────

def create_task(title: str, project: str, due_date: Optional[str] = None,
                priority: str = "medium", notes: Optional[str] = None) -> dict:
    """
    Create an academic/research task with optional deadline.

    Args:
        title: Task description. E.g. "Submit BAB IV draft to advisor"
        project: Project name. E.g. "Skripsi", "Gen AI Hackathon", "Metodologi Survei"
        due_date: ISO date string, e.g. "2025-05-20" or "2025-05-20T14:00:00". Optional.
        priority: "high", "medium", or "low". Default: "medium"
        notes: Extra context. Optional.
    """
    with get_db() as db:
        t = Task(
            title=title, project=project,
            due_date=datetime.fromisoformat(due_date) if due_date else None,
            priority=priority, notes=notes,
        )
        db.add(t)
        db.flush()
        return {"task_id": t.id, "title": t.title, "project": t.project,
                "due_date": str(t.due_date) if t.due_date else None,
                "priority": t.priority, "message": f"Task created with ID {t.id}."}


def list_tasks(project: Optional[str] = None, status: str = "pending") -> list:
    """
    List research tasks. Optionally filter by project or status.

    Args:
        project: Filter by project name (partial match). Optional.
        status: "pending" or "completed". Default: "pending"
    """
    with get_db() as db:
        q = db.query(Task).filter(Task.status == status)
        if project:
            q = q.filter(Task.project.ilike(f"%{project}%"))
        tasks = q.order_by(Task.due_date.asc()).limit(25).all()
        return [{"task_id": t.id, "title": t.title, "project": t.project,
                 "due_date": str(t.due_date) if t.due_date else "No deadline",
                 "priority": t.priority, "status": t.status} for t in tasks]


def complete_task(task_id: int) -> dict:
    """Mark a task as completed by its ID."""
    with get_db() as db:
        t = db.get(Task, task_id)
        if not t:
            return {"error": f"Task {task_id} not found."}
        t.status = "completed"
        t.completed_at = datetime.utcnow()
        return {"task_id": t.id, "title": t.title, "status": "completed"}


def get_upcoming_deadlines(days_ahead: int = 7) -> list:
    """
    Get pending tasks with deadlines in the next N days.

    Args:
        days_ahead: How many days ahead to look. Default: 7.
    """
    now = datetime.utcnow()
    cutoff = now + timedelta(days=days_ahead)
    with get_db() as db:
        tasks = (db.query(Task)
                 .filter(Task.status == "pending")
                 .filter(Task.due_date >= now)
                 .filter(Task.due_date <= cutoff)
                 .order_by(Task.due_date.asc()).all())
        return [{"task_id": t.id, "title": t.title, "project": t.project,
                 "due_date": str(t.due_date),
                 "days_remaining": (t.due_date - now).days} for t in tasks]


# ─── Analysis job tracking ────────────────────────────────────────────────────

def create_analysis_job(name: str, method: str, dataset_ref: str,
                        parameters_json: Optional[str] = None,
                        notes: Optional[str] = None) -> dict:
    """
    Register a statistical analysis job for tracking.

    Args:
        name: Descriptive job name. E.g. "Rasch calibration - survey batch 2"
        method: Method used. E.g. "IRT_Rasch", "SEM_PLS", "CFA", "logistic_regression"
        dataset_ref: Where the data lives. E.g. "BigQuery: statmind_data.survey_responses"
        parameters_json: Optional JSON of model parameters.
        notes: Optional notes about the job.
    """
    with get_db() as db:
        job = AnalysisJob(name=name, method=method, dataset_ref=dataset_ref,
                          parameters_json=parameters_json, notes=notes)
        db.add(job)
        db.flush()
        return {"job_id": job.id, "name": job.name, "method": job.method,
                "status": "pending", "message": f"Analysis job created with ID {job.id}."}


def list_analysis_jobs(status_filter: Optional[str] = None) -> list:
    """
    List analysis jobs. Filter by status if provided.

    Args:
        status_filter: "pending", "running", "completed", or "failed". Optional.
    """
    with get_db() as db:
        q = db.query(AnalysisJob)
        if status_filter:
            q = q.filter(AnalysisJob.status == status_filter)
        jobs = q.order_by(AnalysisJob.created_at.desc()).limit(20).all()
        return [{"job_id": j.id, "name": j.name, "method": j.method,
                 "status": j.status, "dataset_ref": j.dataset_ref,
                 "created_at": str(j.created_at)} for j in jobs]


# ─── Research notes ───────────────────────────────────────────────────────────

def save_research_note(title: str, content: str, tags: str,
                       project: Optional[str] = None,
                       source_ref: Optional[str] = None) -> dict:
    """
    Save a research note (paper summary, method note, dataset observation).

    Args:
        title: Note title. E.g. "Rasch model fit statistics summary"
        content: Full note body.
        tags: Comma-separated keywords. E.g. "IRT,Rasch,validity,skripsi"
        project: Project association. E.g. "Skripsi". Optional.
        source_ref: Citation or URL. E.g. "Bond & Fox (2015)". Optional.
    """
    with get_db() as db:
        note = ResearchNote(title=title, content=content, tags=tags,
                            project=project, source_ref=source_ref)
        db.add(note)
        db.flush()
        return {"note_id": note.id, "title": note.title,
                "message": f"Note '{title}' saved with ID {note.id}."}


def search_research_notes(query: str) -> list:
    """
    Search saved research notes by keyword across title, content, and tags.

    Args:
        query: Search terms. E.g. "Cronbach reliability survey"
    """
    with get_db() as db:
        results = (db.query(ResearchNote)
                   .filter(ResearchNote.title.ilike(f"%{query}%")
                           | ResearchNote.content.ilike(f"%{query}%")
                           | ResearchNote.tags.ilike(f"%{query}%"))
                   .order_by(ResearchNote.created_at.desc()).limit(10).all())
        return [{"note_id": n.id, "title": n.title, "tags": n.tags,
                 "project": n.project,
                 "preview": n.content[:250] + "..." if len(n.content) > 250 else n.content}
                for n in results]


def list_research_notes(project: Optional[str] = None,
                        tag: Optional[str] = None) -> list:
    """
    List research notes, optionally filtered by project or tag.

    Args:
        project: Filter by project name. Optional.
        tag: Filter by tag keyword. Optional.
    """
    with get_db() as db:
        q = db.query(ResearchNote)
        if project:
            q = q.filter(ResearchNote.project.ilike(f"%{project}%"))
        if tag:
            q = q.filter(ResearchNote.tags.ilike(f"%{tag}%"))
        notes = q.order_by(ResearchNote.created_at.desc()).limit(20).all()
        return [{"note_id": n.id, "title": n.title, "tags": n.tags,
                 "project": n.project, "source": n.source_ref,
                 "created_at": str(n.created_at)} for n in notes]


# ─── Dataset registry ─────────────────────────────────────────────────────────

def register_dataset(name: str, source: str, description: str,
                     variables: str, sample_size: Optional[int] = None,
                     collection_method: Optional[str] = None,
                     notes: Optional[str] = None) -> dict:
    """
    Register a dataset in the StatMind catalog.

    Args:
        name: Dataset name. E.g. "SMARVUS OSF", "UNJ Statistics 2023 Survey"
        source: Where data lives. E.g. "OSF", "BigQuery: statmind_data.survey_responses"
        description: What the dataset covers.
        variables: Comma-separated key variables.
        sample_size: Number of observations. Optional.
        collection_method: E.g. "Google Forms", "Secondary data / OSF". Optional.
        notes: Data quality notes. Optional.
    """
    with get_db() as db:
        ds = Dataset(name=name, source=source, description=description,
                     variables=variables, sample_size=sample_size,
                     collection_method=collection_method, notes=notes)
        db.add(ds)
        db.flush()
        return {"dataset_id": ds.id, "name": ds.name, "source": ds.source,
                "message": f"Dataset '{name}' registered with ID {ds.id}."}


def list_datasets(search: Optional[str] = None) -> list:
    """
    List registered datasets. Optionally filter by name or description keyword.

    Args:
        search: Filter keyword. Optional.
    """
    with get_db() as db:
        q = db.query(Dataset)
        if search:
            q = q.filter(Dataset.name.ilike(f"%{search}%")
                         | Dataset.description.ilike(f"%{search}%")
                         | Dataset.variables.ilike(f"%{search}%"))
        datasets = q.order_by(Dataset.created_at.desc()).all()
        return [{"dataset_id": d.id, "name": d.name, "source": d.source,
                 "sample_size": d.sample_size, "variables": d.variables,
                 "collection_method": d.collection_method} for d in datasets]
