"""
Tool declarations for the google-genai client.
Based on the pattern that worked in Professor Stats / StatScout:
- Use google.genai.types.Tool with FunctionDeclaration
- No ADK Runner, no ADK session service
"""

import google.genai.types as genai_types

# ─── Statistical tools ────────────────────────────────────────────────────────

cronbach_alpha_decl = genai_types.FunctionDeclaration(
    name="cronbach_alpha",
    description="Calculate Cronbach's alpha reliability for a survey instrument. "
                "Input is a 2D array of scores (rows=respondents, cols=items).",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "items_json": genai_types.Schema(
                type=genai_types.Type.STRING,
                description='2D JSON array, e.g. "[[4,3,5],[3,2,4],[5,5,5]]"',
            ),
        },
        required=["items_json"],
    ),
)

descriptive_stats_decl = genai_types.FunctionDeclaration(
    name="descriptive_stats",
    description="Compute descriptive statistics (mean, median, SD, quartiles, skewness) "
                "for a list of numeric values.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "values_json": genai_types.Schema(
                type=genai_types.Type.STRING,
                description='JSON array of numbers, e.g. "[4.2, 3.8, 5.0, 4.5]"',
            ),
            "variable_name": genai_types.Schema(
                type=genai_types.Type.STRING,
                description="Label for the variable, e.g. 'total_stress_score'",
            ),
        },
        required=["values_json"],
    ),
)

pearson_correlation_decl = genai_types.FunctionDeclaration(
    name="pearson_correlation",
    description="Compute Pearson r correlation between two numeric variables.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "x_json": genai_types.Schema(type=genai_types.Type.STRING,
                                          description="JSON array for variable X"),
            "y_json": genai_types.Schema(type=genai_types.Type.STRING,
                                          description="JSON array for variable Y"),
            "x_label": genai_types.Schema(type=genai_types.Type.STRING,
                                           description="Name of X variable"),
            "y_label": genai_types.Schema(type=genai_types.Type.STRING,
                                           description="Name of Y variable"),
        },
        required=["x_json", "y_json"],
    ),
)

create_analysis_job_decl = genai_types.FunctionDeclaration(
    name="create_analysis_job",
    description="Register a statistical analysis job (IRT, SEM, regression, etc.) for tracking.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "name": genai_types.Schema(type=genai_types.Type.STRING,
                                        description="Job name, e.g. 'Rasch calibration survey batch 2'"),
            "method": genai_types.Schema(type=genai_types.Type.STRING,
                                          description="Method, e.g. 'IRT_Rasch', 'SEM_PLS', 'CFA'"),
            "dataset_ref": genai_types.Schema(type=genai_types.Type.STRING,
                                               description="Dataset reference, e.g. 'BigQuery: statmind_data.survey_responses'"),
            "parameters_json": genai_types.Schema(type=genai_types.Type.STRING,
                                                   description="Optional JSON of model parameters"),
            "notes": genai_types.Schema(type=genai_types.Type.STRING,
                                         description="Optional notes about this job"),
        },
        required=["name", "method", "dataset_ref"],
    ),
)

list_analysis_jobs_decl = genai_types.FunctionDeclaration(
    name="list_analysis_jobs",
    description="List registered analysis jobs, optionally filtered by status.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "status_filter": genai_types.Schema(
                type=genai_types.Type.STRING,
                description="One of: pending, running, completed, failed. Optional.",
            ),
        },
    ),
)

# ─── Task tools ───────────────────────────────────────────────────────────────

create_task_decl = genai_types.FunctionDeclaration(
    name="create_task",
    description="Create an academic or research task with an optional deadline.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "title": genai_types.Schema(type=genai_types.Type.STRING,
                                         description="Task title, e.g. 'Submit BAB IV draft to advisor'"),
            "project": genai_types.Schema(type=genai_types.Type.STRING,
                                           description="Project name, e.g. 'Skripsi', 'Gen AI Hackathon'"),
            "due_date": genai_types.Schema(type=genai_types.Type.STRING,
                                            description="ISO date, e.g. '2025-05-20' or '2025-05-20T14:00:00'"),
            "priority": genai_types.Schema(type=genai_types.Type.STRING,
                                            description="'high', 'medium', or 'low'"),
            "notes": genai_types.Schema(type=genai_types.Type.STRING,
                                         description="Optional extra context"),
        },
        required=["title", "project"],
    ),
)

list_tasks_decl = genai_types.FunctionDeclaration(
    name="list_tasks",
    description="List research tasks, optionally filtered by project or status.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "project": genai_types.Schema(type=genai_types.Type.STRING,
                                           description="Filter by project name. Optional."),
            "status": genai_types.Schema(type=genai_types.Type.STRING,
                                          description="'pending' or 'completed'. Default: pending"),
        },
    ),
)

complete_task_decl = genai_types.FunctionDeclaration(
    name="complete_task",
    description="Mark a task as completed by its ID.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "task_id": genai_types.Schema(type=genai_types.Type.INTEGER,
                                           description="The integer ID of the task"),
        },
        required=["task_id"],
    ),
)

get_upcoming_deadlines_decl = genai_types.FunctionDeclaration(
    name="get_upcoming_deadlines",
    description="Get pending tasks with deadlines in the next N days.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "days_ahead": genai_types.Schema(type=genai_types.Type.INTEGER,
                                              description="Days to look ahead. Default: 7"),
        },
    ),
)

# ─── Research note tools ──────────────────────────────────────────────────────

save_research_note_decl = genai_types.FunctionDeclaration(
    name="save_research_note",
    description="Save a research note: paper summary, method note, or dataset observation.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "title": genai_types.Schema(type=genai_types.Type.STRING,
                                         description="Note title"),
            "content": genai_types.Schema(type=genai_types.Type.STRING,
                                           description="Full note body"),
            "tags": genai_types.Schema(type=genai_types.Type.STRING,
                                        description="Comma-separated tags, e.g. 'IRT,Rasch,validity'"),
            "project": genai_types.Schema(type=genai_types.Type.STRING,
                                           description="Project association. Optional."),
            "source_ref": genai_types.Schema(type=genai_types.Type.STRING,
                                              description="Citation or URL. Optional."),
        },
        required=["title", "content", "tags"],
    ),
)

search_research_notes_decl = genai_types.FunctionDeclaration(
    name="search_research_notes",
    description="Full-text search across saved research notes (title, content, tags).",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "query": genai_types.Schema(type=genai_types.Type.STRING,
                                         description="Search terms"),
        },
        required=["query"],
    ),
)

list_research_notes_decl = genai_types.FunctionDeclaration(
    name="list_research_notes",
    description="List saved research notes, optionally filtered by project or tag.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "project": genai_types.Schema(type=genai_types.Type.STRING,
                                           description="Filter by project. Optional."),
            "tag": genai_types.Schema(type=genai_types.Type.STRING,
                                       description="Filter by tag keyword. Optional."),
        },
    ),
)

register_dataset_decl = genai_types.FunctionDeclaration(
    name="register_dataset",
    description="Register a dataset in the StatMind catalog with metadata.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "name": genai_types.Schema(type=genai_types.Type.STRING,
                                        description="Dataset name"),
            "source": genai_types.Schema(type=genai_types.Type.STRING,
                                          description="Where it lives, e.g. 'OSF', 'BigQuery: statmind_data.survey_responses'"),
            "description": genai_types.Schema(type=genai_types.Type.STRING,
                                               description="What the dataset covers"),
            "variables": genai_types.Schema(type=genai_types.Type.STRING,
                                             description="Comma-separated key variables"),
            "sample_size": genai_types.Schema(type=genai_types.Type.INTEGER,
                                               description="Number of observations. Optional."),
            "collection_method": genai_types.Schema(type=genai_types.Type.STRING,
                                                     description="E.g. 'Google Forms', 'Secondary data'"),
            "notes": genai_types.Schema(type=genai_types.Type.STRING,
                                         description="Data quality notes. Optional."),
        },
        required=["name", "source", "description", "variables"],
    ),
)

list_datasets_decl = genai_types.FunctionDeclaration(
    name="list_datasets",
    description="List registered datasets, optionally filtered by keyword.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "search": genai_types.Schema(type=genai_types.Type.STRING,
                                          description="Filter keyword. Optional."),
        },
    ),
)

# ─── Tool groups exported per agent ──────────────────────────────────────────

ANALYSIS_TOOLS = genai_types.Tool(function_declarations=[
    cronbach_alpha_decl,
    descriptive_stats_decl,
    pearson_correlation_decl,
    create_analysis_job_decl,
    list_analysis_jobs_decl,
])

SCHEDULE_TOOLS = genai_types.Tool(function_declarations=[
    create_task_decl,
    list_tasks_decl,
    complete_task_decl,
    get_upcoming_deadlines_decl,
])

RESEARCH_TOOLS = genai_types.Tool(function_declarations=[
    save_research_note_decl,
    search_research_notes_decl,
    list_research_notes_decl,
    register_dataset_decl,
    list_datasets_decl,
])

# Coordinator sees delegation tools only — no direct stat tools at coordinator level
COORDINATOR_TOOLS = genai_types.Tool(function_declarations=[
    genai_types.FunctionDeclaration(
        name="call_analysis_agent",
        description="Delegate a statistical analysis task to the AnalysisAgent. "
                    "Use for: Cronbach's alpha, descriptive stats, Pearson r, "
                    "analysis job tracking, BigQuery queries.",
        parameters=genai_types.Schema(
            type=genai_types.Type.OBJECT,
            properties={
                "task": genai_types.Schema(type=genai_types.Type.STRING,
                                            description="Full description of what to do, including any data"),
            },
            required=["task"],
        ),
    ),
    genai_types.FunctionDeclaration(
        name="call_schedule_agent",
        description="Delegate scheduling or task management to the ScheduleAgent. "
                    "Use for: creating tasks, deadlines, calendar events, upcoming reminders.",
        parameters=genai_types.Schema(
            type=genai_types.Type.OBJECT,
            properties={
                "task": genai_types.Schema(type=genai_types.Type.STRING,
                                            description="Full description of what to schedule or track"),
            },
            required=["task"],
        ),
    ),
    genai_types.FunctionDeclaration(
        name="call_research_agent",
        description="Delegate knowledge management to the ResearchAgent. "
                    "Use for: saving notes, searching notes, dataset registry, drafting emails.",
        parameters=genai_types.Schema(
            type=genai_types.Type.OBJECT,
            properties={
                "task": genai_types.Schema(type=genai_types.Type.STRING,
                                            description="Full description of what to save, search, or draft"),
            },
            required=["task"],
        ),
    ),
])
