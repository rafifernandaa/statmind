"""
StatMind — FastAPI application.

Session management: sessions stored in DB (not ADK session service).
Agent calls: google-genai client directly (not ADK Runner).
Both lessons from Professor Stats / StatScout failures applied here.
"""

import os
import uuid
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

from db.database import get_db, get_engine
from db.models import ChatSession, Task, AnalysisJob, ResearchNote, Dataset, DatasetColumn, Base
from agents.runner import run_coordinator
from tools.stat_tools import (
    list_tasks,
    get_upcoming_deadlines,
    list_analysis_jobs,
    list_datasets,
    list_research_notes,
)

# Path to the static folder (api/static/)
STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="StatMind",
    description="Multi-agent productivity assistant for statistics students and researchers.",
    version="1.0.0",
    # Disable default / redirect so our own route takes it
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    """Create all DB tables on startup if they don't exist."""
    Base.metadata.create_all(bind=get_engine())

# Mount static assets (CSS, JS, images if any)
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ─── Request / response schemas ───────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    agent_used: str = "coordinator"
    stat_results: dict = {}   # raw numbers from stat tools — no regex needed


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _load_history(session_id: str) -> list:
    """Load conversation history from DB for this session."""
    with get_db() as db:
        session = db.get(ChatSession, session_id)
        if session and session.history_json:
            return json.loads(session.history_json)
        db.commit()
        return []


def _save_history(session_id: str, user_id: str, history: list):
    """Persist conversation history. Keep last 20 turns to control token growth."""
    with get_db() as db:
        session = db.get(ChatSession, session_id)
        trimmed = history[-20:]
        if session:
            session.history_json = json.dumps(trimmed)
        else:
            db.add(ChatSession(
                id=session_id,
                user_id=user_id,
                history_json=json.dumps(trimmed),
            ))
        db.commit()


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def root():
    """Serve the StatMind UI."""
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index), media_type="text/html")
    # Fallback JSON if static file is missing (e.g. during development without UI)
    return {
        "service": "StatMind",
        "tagline": "Turning Uncertainty Into Insight",
        "version": "1.0.0",
        "note": "UI not found. Place index.html in api/static/",
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "StatMind"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Main conversational endpoint.
    Routes to AnalysisAgent, ScheduleAgent, or ResearchAgent via CoordinatorAgent.
    Sessions persisted in DB — no ADK session service.
    """
    session_id = request.session_id or str(uuid.uuid4())

    history = _load_history(session_id)

    try:
        reply, agent_used, stat_results = run_coordinator(
            user_message=request.message,
            history=history,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    history.append({"role": "user", "content": request.message})
    history.append({"role": "assistant", "content": reply})
    _save_history(session_id, request.user_id or "default", history)

    return ChatResponse(session_id=session_id, reply=reply,
                        agent_used=agent_used, stat_results=stat_results)


@app.get("/tasks")
def get_tasks(project: Optional[str] = None, status: Optional[str] = "pending"):
    """List tasks. Filter by project or status."""
    return list_tasks(project=project, status=status)


@app.get("/tasks/upcoming")
def upcoming_tasks(days: int = 7):
    """Get tasks with deadlines in the next N days."""
    return get_upcoming_deadlines(days_ahead=days)


@app.get("/analysis/jobs")
def get_analysis_jobs(status: Optional[str] = None):
    """List analysis jobs. Filter by status."""
    return list_analysis_jobs(status_filter=status)


@app.get("/datasets")
def get_datasets(search: Optional[str] = None):
    """List registered datasets."""
    return list_datasets(search=search)


@app.get("/notes")
def get_notes(project: Optional[str] = None, tag: Optional[str] = None):
    """List research notes. Filter by project or tag."""
    return list_research_notes(project=project, tag=tag)


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    """Delete a task by ID."""
    with get_db() as db:
        task = db.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found.")
        db.delete(task)
        db.commit()
        return {"message": f"Task {task_id} deleted."}


@app.patch("/tasks/{task_id}/complete")
def complete_task_route(task_id: int):
    """Mark a task as completed."""
    with get_db() as db:
        task = db.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found.")
        task.status = "completed"
        from datetime import datetime
        task.completed_at = datetime.utcnow()
        db.commit()
        return {"message": f"Task {task_id} marked completed.", "title": task.title}


@app.delete("/notes/{note_id}")
def delete_note(note_id: int):
    """Delete a research note by ID."""
    with get_db() as db:
        note = db.get(ResearchNote, note_id)
        if not note:
            raise HTTPException(status_code=404, detail=f"Note {note_id} not found.")
        db.delete(note)
        db.commit()
        return {"message": f"Note {note_id} deleted."}


@app.delete("/datasets/{dataset_id}")
def delete_dataset(dataset_id: int):
    """Delete a dataset by ID."""
    with get_db() as db:
        dataset = db.get(Dataset, dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found.")
        db.delete(dataset)
        db.commit()
        return {"message": f"Dataset {dataset_id} deleted."}


@app.patch("/analysis/jobs/{job_id}/status")
def update_job_status(job_id: int, status: str):
    """Update analysis job status: pending → running → completed / failed."""
    valid = {"pending", "running", "completed", "failed"}
    if status not in valid:
        raise HTTPException(status_code=400, detail=f"Status must be one of {valid}.")
    with get_db() as db:
        job = db.get(AnalysisJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
        job.status = status
        db.commit()
        return {"job_id": job_id, "status": status, "name": job.name}


@app.post("/datasets/{dataset_id}/columns")
async def upload_dataset_columns(dataset_id: int, columns_json: str = Form(...)):
    """Store column data for a dataset via form POST."""
    result = store_dataset_columns(dataset_id, columns_json)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/datasets/{dataset_id}/columns")
def get_dataset_columns(dataset_id: int):
    """List all columns and basic stats for a dataset."""
    return list_dataset_columns(dataset_id)


@app.post("/datasets/upload-csv")
async def upload_csv(
    file: UploadFile = File(...),
    dataset_name: str = Form(...),
    source: str = Form(default="CSV Upload"),
    description: str = Form(default=""),
):
    """
    Upload a CSV file, auto-register it as a dataset, and store all columns.
    Returns dataset_id and column list so the agent can reference them immediately.
    """
    import io, csv as csv_mod
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")  # handles BOM from Excel CSV exports
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    reader = csv_mod.DictReader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV file is empty.")

    # Filter out None keys (happens if CSV has more columns than headers)
    # and ensure they are strings.
    columns = {str(col): [] for col in rows[0].keys() if col is not None}
    
    for row in rows:
        for col, val in row.items():
            if col in columns:
                columns[col].append(val.strip() if val else None)

    # Register dataset
    try:
        with get_db() as db:
            ds = Dataset(
                name=dataset_name,
                source=source,
                description=description or f"Uploaded CSV: {file.filename}",
                variables=", ".join(columns.keys()),
                sample_size=len(rows),
                collection_method="CSV Upload",
            )
            db.add(ds)
            db.flush()
            ds_id = ds.id

            # Store columns — auto-detect numeric vs categorical
            import json as json_mod
            for col_name, values in columns.items():
                numeric_vals = []
                dtype = "categorical"
                for v in values:
                    try:
                        # Attempt numeric conversion
                        if v in (None, ""):
                            numeric_vals.append(None)
                        else:
                            numeric_vals.append(float(v))
                            dtype = "numeric"
                    except (TypeError, ValueError):
                        numeric_vals.append(v)
                
                db.add(DatasetColumn(
                    dataset_id=ds_id,
                    column_name=col_name,
                    data_json=json_mod.dumps(numeric_vals),
                    dtype=dtype,
                    n_rows=len(values),
                ))
            # No need for explicit db.commit() as get_db() context manager does it
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return {
        "dataset_id": ds_id,
        "dataset_name": dataset_name,
        "n_rows": len(rows),
        "columns": list(columns.keys()),
        "message": (f"Dataset '{dataset_name}' registered as ID {ds_id}. "
                    f"Reference columns as '{ds_id}:column_name' in any stat tool."),
    }


@app.delete("/sessions/{session_id}")
def clear_session(session_id: str):
    """Clear conversation history for a session."""
    with get_db() as db:
        session = db.get(ChatSession, session_id)
        if session:
            session.history_json = "[]"
            db.commit()
            return {"message": f"Session {session_id} cleared."}
        return {"message": "Session not found."}


# ─── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, reload=False)
