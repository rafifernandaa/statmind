from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ChatSession(Base):
    """Stores conversation history per session_id. Replaces ADK session service."""
    __tablename__ = "chat_sessions"
    id = Column(String(64), primary_key=True)
    user_id = Column(String(100), nullable=True, default="default")
    history_json = Column(Text, nullable=True, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(300), nullable=False)
    project = Column(String(150), nullable=False)
    due_date = Column(DateTime, nullable=True)
    priority = Column(Enum("high", "medium", "low", name="task_priority"), default="medium")
    status = Column(Enum("pending", "completed", name="task_status"), default="pending")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(300), nullable=False)
    method = Column(String(100), nullable=False)
    dataset_ref = Column(String(200), nullable=True)
    status = Column(Enum("pending", "running", "completed", "failed", name="analysis_status"), default="pending")
    parameters_json = Column(Text, nullable=True)
    result_summary = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ResearchNote(Base):
    __tablename__ = "research_notes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    tags = Column(String(500), nullable=True)
    project = Column(String(150), nullable=True)
    source_ref = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Dataset(Base):
    __tablename__ = "datasets"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(300), nullable=False)
    source = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    variables = Column(Text, nullable=True)
    sample_size = Column(Integer, nullable=True)
    collection_method = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DatasetColumn(Base):
    """
    Stores actual column data for a registered dataset.
    Each row = one column/variable of a dataset.
    Values stored as a JSON array string for compact retrieval.
    This is what makes 'dataset_id:column_name' references work in stat tools.
    """
    __tablename__ = "dataset_columns"
    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(Integer, nullable=False, index=True)
    column_name = Column(String(200), nullable=False)
    data_json = Column(Text, nullable=False)   # JSON array of values
    dtype = Column(String(50), nullable=True)  # numeric / categorical / ordinal
    n_rows = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
