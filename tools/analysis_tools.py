"""
StatMind — Statistical analysis tools for AnalysisAgent.
"""

import json
import math
import statistics
from typing import Optional
from google.adk.tools import tool
from db.database import get_db_session
from db.models import AnalysisJob


@tool
def run_cronbach_alpha(items_json: str) -> dict:
    """
    Calculate Cronbach's alpha for a set of items from a survey/questionnaire.

    Args:
        items_json: JSON string of a 2D list — rows are respondents, columns are items.
                    Example: "[[4,3,5,4],[3,2,4,3],[5,5,5,4]]"

    Returns:
        dict with alpha value, interpretation, and item-total correlations.
    """
    try:
        data = json.loads(items_json)
        n_items = len(data[0])
        n_subjects = len(data)

        item_variances = [statistics.variance([row[i] for row in data]) for i in range(n_items)]
        total_scores = [sum(row) for row in data]
        total_variance = statistics.variance(total_scores)

        alpha = (n_items / (n_items - 1)) * (1 - sum(item_variances) / total_variance)
        alpha = round(alpha, 4)

        if alpha >= 0.9:
            interpretation = "Excellent reliability"
        elif alpha >= 0.8:
            interpretation = "Good reliability"
        elif alpha >= 0.7:
            interpretation = "Acceptable reliability"
        elif alpha >= 0.6:
            interpretation = "Questionable reliability — consider revising items"
        else:
            interpretation = "Poor reliability — instrument needs substantial revision"

        item_total_corr = []
        for i in range(n_items):
            item_scores = [row[i] for row in data]
            rest_scores = [sum(row) - row[i] for row in data]
            mean_item = statistics.mean(item_scores)
            mean_rest = statistics.mean(rest_scores)
            cov = sum((a - mean_item) * (b - mean_rest) for a, b in zip(item_scores, rest_scores)) / (n_subjects - 1)
            std_item = statistics.stdev(item_scores)
            std_rest = statistics.stdev(rest_scores)
            corr = round(cov / (std_item * std_rest), 4) if std_item > 0 and std_rest > 0 else 0.0
            item_total_corr.append(corr)

        return {
            "alpha": alpha,
            "interpretation": interpretation,
            "n_items": n_items,
            "n_subjects": n_subjects,
            "item_total_correlations": {f"Item {i+1}": item_total_corr[i] for i in range(n_items)},
            "low_correlation_items": [f"Item {i+1}" for i, c in enumerate(item_total_corr) if c < 0.3],
        }
    except Exception as e:
        return {"error": str(e), "hint": "Ensure items_json is a valid 2D JSON array."}


@tool
def run_descriptive_stats(values_json: str, variable_name: str = "variable") -> dict:
    """
    Compute descriptive statistics for a list of numeric values.

    Args:
        values_json: JSON array of numbers. Example: "[4.2, 3.8, 5.0, 4.5, 3.1]"
        variable_name: Name of the variable for labeling output.

    Returns:
        dict with mean, median, std dev, min, max, quartiles, and skewness.
    """
    try:
        values = json.loads(values_json)
        values = [float(v) for v in values if v is not None]
        n = len(values)
        sorted_vals = sorted(values)

        mean = statistics.mean(values)
        median = statistics.median(values)
        std = statistics.stdev(values) if n > 1 else 0.0
        min_v = min(values)
        max_v = max(values)
        q1 = sorted_vals[n // 4]
        q3 = sorted_vals[(3 * n) // 4]

        skewness = (3 * (mean - median) / std) if std > 0 else 0.0

        return {
            "variable": variable_name,
            "n": n,
            "mean": round(mean, 4),
            "median": round(median, 4),
            "std_dev": round(std, 4),
            "min": min_v,
            "max": max_v,
            "q1": q1,
            "q3": q3,
            "iqr": round(q3 - q1, 4),
            "skewness_pearson": round(skewness, 4),
            "skewness_interpretation": (
                "Approximately symmetric" if abs(skewness) < 0.5
                else "Moderately skewed" if abs(skewness) < 1.0
                else "Highly skewed"
            ),
        }
    except Exception as e:
        return {"error": str(e)}


@tool
def create_analysis_job(
    job_name: str,
    method: str,
    dataset_id: str,
    parameters_json: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    """
    Register a new statistical analysis job in the database.
    Use this for long-running jobs like IRT calibration, SEM, or bootstrap runs.

    Args:
        job_name: Short descriptive name. E.g. "Rasch calibration survey batch 2"
        method: Statistical method. E.g. "IRT_Rasch", "SEM_PLS", "logistic_regression"
        dataset_id: ID of the dataset in the datasets_registry table.
        parameters_json: Optional JSON of model parameters. E.g. '{"n_items": 20, "model": "2PL"}'
        notes: Optional free-text notes about this job.

    Returns:
        dict with the new job_id and status.
    """
    with get_db_session() as session:
        job = AnalysisJob(
            name=job_name,
            method=method,
            dataset_id=dataset_id,
            status="pending",
            parameters=parameters_json,
            notes=notes,
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        return {
            "job_id": job.id,
            "name": job.name,
            "status": job.status,
            "method": job.method,
            "message": f"Analysis job '{job_name}' created with ID {job.id}.",
        }


@tool
def get_analysis_job_status(job_id: int) -> dict:
    """
    Get the current status of a registered analysis job.

    Args:
        job_id: The integer ID of the job.

    Returns:
        dict with job details and current status.
    """
    with get_db_session() as session:
        job = session.get(AnalysisJob, job_id)
        if not job:
            return {"error": f"No analysis job found with ID {job_id}."}
        return {
            "job_id": job.id,
            "name": job.name,
            "method": job.method,
            "status": job.status,
            "dataset_id": job.dataset_id,
            "created_at": str(job.created_at),
            "notes": job.notes,
        }


@tool
def list_analysis_jobs(status_filter: Optional[str] = None) -> list:
    """
    List all registered analysis jobs, optionally filtered by status.

    Args:
        status_filter: Optional. One of: "pending", "running", "completed", "failed".

    Returns:
        list of job summaries.
    """
    with get_db_session() as session:
        query = session.query(AnalysisJob)
        if status_filter:
            query = query.filter(AnalysisJob.status == status_filter)
        jobs = query.order_by(AnalysisJob.created_at.desc()).limit(20).all()
        return [
            {
                "job_id": j.id,
                "name": j.name,
                "method": j.method,
                "status": j.status,
                "created_at": str(j.created_at),
            }
            for j in jobs
        ]
