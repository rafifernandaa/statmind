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
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from db.database import get_db, get_engine
from db.models import ChatSession, Base
from agents.runner import run_coordinator
from tools.stat_tools import (
    list_tasks,
    get_upcoming_deadlines,
    list_analysis_jobs,
    list_datasets,
    list_research_notes,
)

# Ensure tables exist on startup
Base.metadata.create_all(bind=get_engine())

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


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _load_history(session_id: str) -> list:
    """Load conversation history from DB for this session."""
    with get_db() as db:
        session = db.get(ChatSession, session_id)
        if session and session.history_json:
            return json.loads(session.history_json)
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
        reply = run_coordinator(
            user_message=request.message,
            history=history,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    history.append({"role": "user", "content": request.message})
    history.append({"role": "assistant", "content": reply})
    _save_history(session_id, request.user_id or "default", history)

    return ChatResponse(session_id=session_id, reply=reply)


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


@app.delete("/sessions/{session_id}")
def clear_session(session_id: str):
    """Clear conversation history for a session."""
    with get_db() as db:
        session = db.get(ChatSession, session_id)
        if session:
            session.history_json = "[]"
            return {"message": f"Session {session_id} cleared."}
        return {"message": "Session not found."}


# ─── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, reload=False)
