"""
StatMind — Research notes and dataset registry tools for ResearchAgent.
"""

from typing import Optional
from google.adk.tools import tool
from db.database import get_db_session
from db.models import ResearchNote, Dataset


@tool
def save_research_note(
    title: str,
    content: str,
    tags: str,
    project: Optional[str] = None,
    source_reference: Optional[str] = None,
) -> dict:
    """
    Save a research note (paper summary, method note, dataset observation, etc.).

    Args:
        title: Short title for the note. E.g. "Rasch model assumptions summary"
        content: Full note content.
        tags: Comma-separated tags. E.g. "IRT,Rasch,psychometrics,validity"
        project: Optional project association. E.g. "Skripsi", "Metodologi Survei"
        source_reference: Optional citation or URL. E.g. "Bond & Fox (2015)"

    Returns:
        dict with the saved note ID.
    """
    with get_db_session() as session:
        note = ResearchNote(
            title=title,
            content=content,
            tags=tags,
            project=project,
            source_reference=source_reference,
        )
        session.add(note)
        session.commit()
        session.refresh(note)
        return {
            "note_id": note.id,
            "title": note.title,
            "tags": note.tags,
            "message": f"Note '{title}' saved successfully.",
        }


@tool
def list_research_notes(
    project: Optional[str] = None,
    tag_filter: Optional[str] = None,
    limit: int = 15,
) -> list:
    """
    List saved research notes, optionally filtered by project or tag.

    Args:
        project: Filter by project name (optional).
        tag_filter: Filter notes that contain this tag (optional).
        limit: Max number of notes to return. Default: 15.

    Returns:
        list of note summaries.
    """
    with get_db_session() as session:
        query = session.query(ResearchNote)
        if project:
            query = query.filter(ResearchNote.project.ilike(f"%{project}%"))
        if tag_filter:
            query = query.filter(ResearchNote.tags.ilike(f"%{tag_filter}%"))
        notes = query.order_by(ResearchNote.created_at.desc()).limit(limit).all()
        return [
            {
                "note_id": n.id,
                "title": n.title,
                "tags": n.tags,
                "project": n.project,
                "source": n.source_reference,
                "created_at": str(n.created_at),
                "preview": n.content[:200] + "..." if len(n.content) > 200 else n.content,
            }
            for n in notes
        ]


@tool
def search_research_notes(query_text: str) -> list:
    """
    Full-text search across research note titles and content.

    Args:
        query_text: Search terms. E.g. "Rasch model fit statistics"

    Returns:
        list of matching notes sorted by relevance (recency proxy).
    """
    with get_db_session() as session:
        results = (
            session.query(ResearchNote)
            .filter(
                ResearchNote.title.ilike(f"%{query_text}%")
                | ResearchNote.content.ilike(f"%{query_text}%")
                | ResearchNote.tags.ilike(f"%{query_text}%")
            )
            .order_by(ResearchNote.created_at.desc())
            .limit(10)
            .all()
        )
        return [
            {
                "note_id": n.id,
                "title": n.title,
                "tags": n.tags,
                "project": n.project,
                "preview": n.content[:300] + "..." if len(n.content) > 300 else n.content,
            }
            for n in results
        ]


@tool
def register_dataset(
    name: str,
    source: str,
    description: str,
    variables: str,
    sample_size: Optional[int] = None,
    collection_method: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    """
    Register a dataset in the StatMind dataset catalog.

    Args:
        name: Dataset name. E.g. "SMARVUS OSF", "UNJ Statistics 2023 Survey"
        source: Where it lives. E.g. "OSF", "BigQuery: statmind_data.survey_responses", "local CSV"
        description: What the dataset is about.
        variables: Comma-separated key variables. E.g. "fear_of_embarrassment,GPA,semester"
        sample_size: Number of observations (optional).
        collection_method: E.g. "Online questionnaire", "Google Forms", "Secondary data"
        notes: Data quality or usage notes (optional).

    Returns:
        dict with the registered dataset ID.
    """
    with get_db_session() as session:
        dataset = Dataset(
            name=name,
            source=source,
            description=description,
            variables=variables,
            sample_size=sample_size,
            collection_method=collection_method,
            notes=notes,
        )
        session.add(dataset)
        session.commit()
        session.refresh(dataset)
        return {
            "dataset_id": dataset.id,
            "name": dataset.name,
            "source": dataset.source,
            "message": f"Dataset '{name}' registered with ID {dataset.id}.",
        }


@tool
def list_datasets(search: Optional[str] = None) -> list:
    """
    List all registered datasets, optionally filtered by name or description.

    Args:
        search: Optional search term to filter datasets.

    Returns:
        list of dataset summaries.
    """
    with get_db_session() as session:
        query = session.query(Dataset)
        if search:
            query = query.filter(
                Dataset.name.ilike(f"%{search}%")
                | Dataset.description.ilike(f"%{search}%")
                | Dataset.variables.ilike(f"%{search}%")
            )
        datasets = query.order_by(Dataset.created_at.desc()).all()
        return [
            {
                "dataset_id": d.id,
                "name": d.name,
                "source": d.source,
                "description": d.description,
                "sample_size": d.sample_size,
                "variables": d.variables,
                "collection_method": d.collection_method,
            }
            for d in datasets
        ]


@tool
def get_dataset_info(dataset_id: int) -> dict:
    """
    Get full details for a specific registered dataset.

    Args:
        dataset_id: The integer ID of the dataset.

    Returns:
        Full dataset record.
    """
    with get_db_session() as session:
        d = session.get(Dataset, dataset_id)
        if not d:
            return {"error": f"No dataset found with ID {dataset_id}."}
        return {
            "dataset_id": d.id,
            "name": d.name,
            "source": d.source,
            "description": d.description,
            "variables": d.variables,
            "sample_size": d.sample_size,
            "collection_method": d.collection_method,
            "notes": d.notes,
            "created_at": str(d.created_at),
        }
