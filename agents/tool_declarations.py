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

spearman_correlation_decl = genai_types.FunctionDeclaration(
    name="spearman_correlation",
    description="Compute Spearman rank correlation. Use for ordinal data or when Pearson normality assumptions are violated.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "x_json": genai_types.Schema(type=genai_types.Type.STRING, description='JSON array for variable X. E.g. "[3,1,4,1,5]"'),
            "y_json": genai_types.Schema(type=genai_types.Type.STRING, description='JSON array for variable Y.'),
            "x_label": genai_types.Schema(type=genai_types.Type.STRING, description="Name of X variable."),
            "y_label": genai_types.Schema(type=genai_types.Type.STRING, description="Name of Y variable."),
        },
        required=["x_json", "y_json"],
    ),
)

independent_ttest_decl = genai_types.FunctionDeclaration(
    name="independent_ttest",
    description="Welch independent samples t-test comparing means of two groups. Use when comparing a numeric variable across two categories.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "group1_json": genai_types.Schema(type=genai_types.Type.STRING, description='JSON array of scores for group 1. E.g. "[5,4,6,5]"'),
            "group2_json": genai_types.Schema(type=genai_types.Type.STRING, description='JSON array of scores for group 2.'),
            "group1_label": genai_types.Schema(type=genai_types.Type.STRING, description="Label for group 1."),
            "group2_label": genai_types.Schema(type=genai_types.Type.STRING, description="Label for group 2."),
        },
        required=["group1_json", "group2_json"],
    ),
)

one_way_anova_decl = genai_types.FunctionDeclaration(
    name="one_way_anova",
    description="One-way ANOVA testing whether means differ across 2 or more groups. Reports F-statistic, eta-squared effect size, and group descriptives.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "groups_json": genai_types.Schema(type=genai_types.Type.STRING, description='2D JSON array — each inner array is one group. E.g. "[[5,4,3],[7,6,8],[4,3,2]]"'),
            "group_labels": genai_types.Schema(type=genai_types.Type.STRING, description="Optional JSON array of group names. E.g. '[\"A\",\"B\",\"C\"]'"),
        },
        required=["groups_json"],
    ),
)

normality_test_decl = genai_types.FunctionDeclaration(
    name="normality_test",
    description="Test whether a variable is normally distributed using Shapiro-Wilk (n≤50) or skewness/kurtosis z-scores (n>50). Always run this before choosing parametric vs non-parametric tests.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "values_json": genai_types.Schema(type=genai_types.Type.STRING, description='JSON array of numeric values.'),
            "variable_name": genai_types.Schema(type=genai_types.Type.STRING, description="Variable label for the report."),
        },
        required=["values_json"],
    ),
)

simple_linear_regression_decl = genai_types.FunctionDeclaration(
    name="simple_linear_regression",
    description="Simple linear regression Y = b0 + b1*X. Reports coefficients, R², adjusted R², F-statistic, and significance of the predictor.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "x_json": genai_types.Schema(type=genai_types.Type.STRING, description="JSON array for predictor variable X."),
            "y_json": genai_types.Schema(type=genai_types.Type.STRING, description="JSON array for outcome variable Y."),
            "x_label": genai_types.Schema(type=genai_types.Type.STRING, description="Name of predictor variable."),
            "y_label": genai_types.Schema(type=genai_types.Type.STRING, description="Name of outcome variable."),
        },
        required=["x_json", "y_json"],
    ),
)

sample_size_calculator_decl = genai_types.FunctionDeclaration(
    name="sample_size_calculator",
    description="Calculate required sample size. Methods: cochran (survey), correlation, ttest, anova.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "method": genai_types.Schema(type=genai_types.Type.STRING, description='"cochran", "correlation", "ttest", or "anova"'),
            "p":          genai_types.Schema(type=genai_types.Type.NUMBER, description="Cochran: estimated proportion (default 0.5)"),
            "e":          genai_types.Schema(type=genai_types.Type.NUMBER, description="Cochran: margin of error (default 0.05)"),
            "confidence": genai_types.Schema(type=genai_types.Type.NUMBER, description="Confidence level: 0.90, 0.95, or 0.99 (default 0.95)"),
            "r":          genai_types.Schema(type=genai_types.Type.NUMBER, description="Correlation: expected r value"),
            "d":          genai_types.Schema(type=genai_types.Type.NUMBER, description="T-test: Cohens d effect size (default 0.5)"),
            "f":          genai_types.Schema(type=genai_types.Type.NUMBER, description="ANOVA: Cohen's f effect size (default 0.25)"),
            "k":          genai_types.Schema(type=genai_types.Type.NUMBER, description="ANOVA: number of groups (default 3)"),
            "alpha":      genai_types.Schema(type=genai_types.Type.NUMBER, description="Significance level (default 0.05)"),
            "power":      genai_types.Schema(type=genai_types.Type.NUMBER, description="Desired statistical power (default 0.80)"),
        },
        required=["method"],
    ),
)

item_analysis_decl = genai_types.FunctionDeclaration(
    name="item_analysis",
    description="Full item analysis: difficulty index, discriminating power, corrected item-total correlation, and alpha-if-deleted for each item. Standard output for reliability reporting in Indonesian academic papers.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "items_json": genai_types.Schema(type=genai_types.Type.STRING, description='2D JSON array — rows = respondents, columns = items.'),
            "item_labels_json": genai_types.Schema(type=genai_types.Type.STRING, description="Optional JSON array of item names. E.g. [Q1, Q2, Q3]"),
        },
        required=["items_json"],
    ),
)


store_dataset_columns_decl = genai_types.FunctionDeclaration(
    name="store_dataset_columns",
    description=(
        "Store column data for a registered dataset so stat tools can reference it by ID. "
        "Call this after register_dataset. Once stored, use 'dataset_id:column_name' "
        "in any stat tool instead of pasting raw JSON arrays."
    ),
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "dataset_id": genai_types.Schema(
                type=genai_types.Type.INTEGER,
                description="Dataset ID returned by register_dataset.",
            ),
            "columns_json": genai_types.Schema(
                type=genai_types.Type.STRING,
                description=(
                    "JSON object mapping column names to arrays of values. "
                    'E.g. {"score": [4,3,5,4], "anxiety": [2,3,2,1]}'
                ),
            ),
        },
        required=["dataset_id", "columns_json"],
    ),
)

list_dataset_columns_decl = genai_types.FunctionDeclaration(
    name="list_dataset_columns",
    description=(
        "List all stored columns for a dataset with basic stats. "
        "Use to discover available column names before running analyses."
    ),
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "dataset_id": genai_types.Schema(
                type=genai_types.Type.INTEGER,
                description="Dataset ID to inspect.",
            ),
        },
        required=["dataset_id"],
    ),
)


chi_square_test_decl = genai_types.FunctionDeclaration(
    name="chi_square_test",
    description=(
        "Chi-square test. Pass a 1D array for goodness-of-fit or a 2D array for "
        "test of independence (contingency table). Reports chi2, df, Cramer's V effect size."
    ),
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "observed_json": genai_types.Schema(
                type=genai_types.Type.STRING,
                description="1D array e.g. [30,20,25] or 2D contingency table [[10,20],[30,40]]",
            ),
            "expected_json": genai_types.Schema(
                type=genai_types.Type.STRING,
                description="Optional 1D expected frequencies for goodness-of-fit.",
            ),
            "variable_name": genai_types.Schema(
                type=genai_types.Type.STRING,
                description="Variable label for reporting.",
            ),
        },
        required=["observed_json"],
    ),
)

mann_whitney_u_decl = genai_types.FunctionDeclaration(
    name="mann_whitney_u",
    description=(
        "Mann-Whitney U test — non-parametric alternative to independent t-test. "
        "Use for ordinal data or when normality is violated. Reports U, z, effect size r."
    ),
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "group1_json": genai_types.Schema(
                type=genai_types.Type.STRING,
                description="JSON array or dataset reference for group 1.",
            ),
            "group2_json": genai_types.Schema(
                type=genai_types.Type.STRING,
                description="JSON array or dataset reference for group 2.",
            ),
            "group1_label": genai_types.Schema(type=genai_types.Type.STRING, description="Label for group 1."),
            "group2_label": genai_types.Schema(type=genai_types.Type.STRING, description="Label for group 2."),
        },
        required=["group1_json", "group2_json"],
    ),
)

kmo_bartlett_decl = genai_types.FunctionDeclaration(
    name="kmo_bartlett",
    description=(
        "Kaiser-Meyer-Olkin (KMO) sampling adequacy and Bartlett sphericity test. "
        "Run before factor analysis. Reports overall KMO, per-item MSA, and Bartlett chi2."
    ),
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "items_json": genai_types.Schema(
                type=genai_types.Type.STRING,
                description="2D JSON array (rows=respondents, cols=items) or dataset_id:col1,col2,col3",
            ),
            "item_labels_json": genai_types.Schema(
                type=genai_types.Type.STRING,
                description="Optional JSON array of item labels.",
            ),
        },
        required=["items_json"],
    ),
)

export_analysis_report_decl = genai_types.FunctionDeclaration(
    name="export_analysis_report",
    description=(
        "Generate a formatted analysis report ready to paste into Word. "
        "Compile multiple stat results into one structured academic report. "
        "Always offer this after completing an analysis the user might want to document."
    ),
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "title": genai_types.Schema(
                type=genai_types.Type.STRING,
                description="Report title. E.g. Reliability Analysis Skala Stres Akademik",
            ),
            "sections_json": genai_types.Schema(
                type=genai_types.Type.STRING,
                description=(
                    "JSON array of sections. Each: "
                    '{heading, content, results} where results is a stat tool output dict.'
                ),
            ),
            "format": genai_types.Schema(
                type=genai_types.Type.STRING,
                description="text (default) or markdown",
            ),
        },
        required=["title", "sections_json"],
    ),
)

ANALYSIS_TOOLS = genai_types.Tool(function_declarations=[
    cronbach_alpha_decl,
    descriptive_stats_decl,
    pearson_correlation_decl,
    spearman_correlation_decl,
    independent_ttest_decl,
    one_way_anova_decl,
    normality_test_decl,
    simple_linear_regression_decl,
    sample_size_calculator_decl,
    item_analysis_decl,
    create_analysis_job_decl,
    list_analysis_jobs_decl,
    store_dataset_columns_decl,
    list_dataset_columns_decl,
    chi_square_test_decl,
    mann_whitney_u_decl,
    kmo_bartlett_decl,
    export_analysis_report_decl,
])

complete_task_by_title_decl = genai_types.FunctionDeclaration(
    name="complete_task_by_title",
    description="Mark the first pending task matching a title fragment as completed. "
                "Use this when you know the task name but not its numeric ID.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "title_fragment": genai_types.Schema(
                type=genai_types.Type.STRING,
                description="Partial or full task title, e.g. 'Submit BAB IV'",
            ),
        },
        required=["title_fragment"],
    ),
)

SCHEDULE_TOOLS = genai_types.Tool(function_declarations=[
    create_task_decl,
    list_tasks_decl,
    complete_task_decl,
    complete_task_by_title_decl,
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
                    "Use for: Cronbach's alpha, item analysis, KMO, Bartlett test, "
                    "Chi-Square, Mann-Whitney U, t-test, ANOVA, normality, "
                    "correlation (Pearson/Spearman), regression, sample size, "
                    "report export, and analysis job tracking.",
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
