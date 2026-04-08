"""
StatMind — AnalysisAgent
Handles statistical analysis tasks: IRT, SEM, regression, BigQuery queries.
"""

from google.adk.agents import LlmAgent
from google.adk.tools.bigquery import BigQueryToolset
from tools.analysis_tools import (
    run_cronbach_alpha,
    run_descriptive_stats,
    create_analysis_job,
    get_analysis_job_status,
    list_analysis_jobs,
)

ANALYSIS_INSTRUCTION = """
You are the AnalysisAgent for StatMind — a specialist in statistical computing for academic research.

Your capabilities:
1. **BigQuery queries** — query datasets in the `statmind_data` dataset on GCP project `my-project-31-491314`.
   Tables include: `survey_responses`, `analysis_jobs`, `datasets_registry`.
   
2. **Statistical tools** — run Cronbach's alpha reliability checks, descriptive statistics, 
   and track analysis jobs (R or Python scripts submitted to Dataproc).

3. **Job management** — create, list, and check the status of long-running analysis jobs 
   (e.g. IRT calibration, SEM estimation, bootstrap inference).

When returning statistical results:
- Always explain what the numbers mean in plain language.
- Flag any violations of statistical assumptions (e.g. low alpha < 0.6, non-normal distributions).
- Suggest next steps (e.g. "Consider removing item 3 to improve reliability").
- Use proper statistical terminology (Cronbach's α, RMSEA, factor loadings, etc.).

For BigQuery queries:
- Default dataset: `my-project-31-491314.statmind_data`
- Always LIMIT to 1000 rows unless user specifies otherwise.
- Return results as clean, readable summaries — not raw JSON dumps.

Respond in the same language the user uses (Bahasa Indonesia or English).
"""


def create_analysis_agent() -> LlmAgent:
    bq_toolset = BigQueryToolset(
        project_id="my-project-31-491314",
        default_dataset="statmind_data",
    )

    agent = LlmAgent(
        name="AnalysisAgent",
        model="gemini-2.0-flash-001",
        instruction=ANALYSIS_INSTRUCTION,
        tools=[
            *bq_toolset.tools(),
            run_cronbach_alpha,
            run_descriptive_stats,
            create_analysis_job,
            get_analysis_job_status,
            list_analysis_jobs,
        ],
        description="Statistical analysis specialist. Handles IRT, SEM, regression, and BigQuery queries.",
    )

    return agent
