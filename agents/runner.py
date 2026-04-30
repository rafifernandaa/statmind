"""
StatMind agent runner.

CRITICAL LESSON FROM PREVIOUS BUILDS:
- Professor Stats hit SessionNotFoundError when using ADK Runner + session service
- Fix: bypass ADK Runner entirely, use google-genai client directly
- StatScout: BigQueryToolset used natively (not via remote MCP)
- This file is fully stateless per request — sessions stored in DB by api/main.py

Pattern: build messages list from DB history → call client.models.generate_content
with tools → dispatch tool calls → loop until text response → return text.
"""

import json
import os
import google.genai as genai
import google.genai.types as genai_types

from agents.prompts import (
    COORDINATOR_SYSTEM_PROMPT,
    ANALYSIS_AGENT_SYSTEM_PROMPT,
    SCHEDULE_AGENT_SYSTEM_PROMPT,
    RESEARCH_AGENT_SYSTEM_PROMPT,
)
from agents.tool_declarations import (
    COORDINATOR_TOOLS,
    ANALYSIS_TOOLS,
    SCHEDULE_TOOLS,
    RESEARCH_TOOLS,
)
from tools.stat_tools import (
    cronbach_alpha,
    descriptive_stats,
    pearson_correlation,
    spearman_correlation,
    independent_ttest,
    one_way_anova,
    normality_test,
    simple_linear_regression,
    sample_size_calculator,
    item_analysis,
    create_analysis_job,
    list_analysis_jobs,
    create_task,
    list_tasks,
    complete_task,
    complete_task_by_title,
    get_upcoming_deadlines,
    save_research_note,
    search_research_notes,
    list_research_notes,
    register_dataset,
    list_datasets,
    store_dataset_columns,
    list_dataset_columns,
    chi_square_test,
    mann_whitney_u,
    kmo_bartlett,
    export_analysis_report,
)

MODEL = "gemini-2.5-flash"

MAX_TOOL_ROUNDS = 6  # prevent infinite loops

# Maps tool name → Python function
TOOL_DISPATCH = {
    "cronbach_alpha": cronbach_alpha,
    "descriptive_stats": descriptive_stats,
    "pearson_correlation": pearson_correlation,
    "spearman_correlation": spearman_correlation,
    "independent_ttest": independent_ttest,
    "one_way_anova": one_way_anova,
    "normality_test": normality_test,
    "simple_linear_regression": simple_linear_regression,
    "sample_size_calculator": sample_size_calculator,
    "item_analysis": item_analysis,
    "chi_square_test": chi_square_test,
    "mann_whitney_u": mann_whitney_u,
    "kmo_bartlett": kmo_bartlett,
    "export_analysis_report": export_analysis_report,
    "create_analysis_job": create_analysis_job,
    "list_analysis_jobs": list_analysis_jobs,
    "create_task": create_task,
    "list_tasks": list_tasks,
    "complete_task": complete_task,
    "complete_task_by_title": complete_task_by_title,
    "get_upcoming_deadlines": get_upcoming_deadlines,
    "save_research_note": save_research_note,
    "search_research_notes": search_research_notes,
    "list_research_notes": list_research_notes,
    "register_dataset": register_dataset,
    "list_datasets": list_datasets,
    "store_dataset_columns": store_dataset_columns,
    "list_dataset_columns": list_dataset_columns,
}


def _get_client() -> genai.Client:
    return genai.Client(
        vertexai=True,
        project="my-project-31-491314",
        location="us-central1"
    )


def _run_agent(system_prompt: str, tools: genai_types.Tool,
               messages: list, user_message: str,
               _accumulated_stats: dict = None) -> str:
    """
    Core stateless agent loop.
    Appends user_message to messages, then calls the model in a loop
    dispatching tool calls until a final text response is returned.
    Populates _accumulated_stats in-place with raw tool results when provided.
    """
    if _accumulated_stats is None:
        _accumulated_stats = {}
    client = _get_client()

    # Build contents list from history + new message
    contents = []
    for msg in messages:
        role = msg.get("role", "user")
        if role == "assistant":
            role = "model"
        contents.append(genai_types.Content(
            role=role,
            parts=[genai_types.Part(text=msg.get("content", ""))]
        ))
    contents.append(genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=user_message)]
    ))

    config = genai_types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=[tools],
        temperature=0.2,
        thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
    )

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=config,
        )

        if not response.candidates:
            return "I'm sorry, I couldn't generate a response."

        candidate = response.candidates[0]
        finish_reason = str(candidate.finish_reason)

        if not candidate.content or not candidate.content.parts:
            if "SAFETY" in finish_reason:
                return "I can't respond to that request due to safety filters."
            return f"The model failed to generate a response (reason: {finish_reason})."

        # Collect all parts from this response turn
        response_parts = list(candidate.content.parts)

        # Check for tool calls
        tool_calls = [p for p in response_parts if p.function_call]

        if not tool_calls:
            # No tool calls — extract text and return
            text_parts = [p.text for p in response_parts if hasattr(p, "text") and p.text]
            return "\n".join(text_parts) if text_parts else "(no response)"

        # Append model's response (with tool calls) to contents
        contents.append(genai_types.Content(role="model", parts=response_parts))

        # Execute each tool call and collect results
        tool_result_parts = []
        for part in tool_calls:
            fn_name = part.function_call.name
            fn_args = dict(part.function_call.args) if part.function_call.args else {}

            if fn_name in TOOL_DISPATCH:
                try:
                    result = TOOL_DISPATCH[fn_name](**fn_args)
                except Exception as e:
                    result = {"error": str(e)}
            else:
                result = {"error": f"Unknown tool: {fn_name}"}

            # ── Capture raw stat results + auto-create analysis job ────────
            # Fires every time a stat tool runs so the job counter increments
            # without the agent needing to explicitly call create_analysis_job.
            _STAT_TOOLS = {
                "cronbach_alpha", "pearson_correlation", "descriptive_stats",
                "spearman_correlation", "independent_ttest", "one_way_anova",
                "normality_test", "simple_linear_regression",
                "sample_size_calculator", "item_analysis",
                "chi_square_test", "mann_whitney_u", "kmo_bartlett",
            }
            if fn_name in _STAT_TOOLS and isinstance(result, dict) and "error" not in result:
                if _accumulated_stats is not None:
                    _accumulated_stats.update(result)
                    _accumulated_stats["_tool"] = fn_name
                # Auto-register job so counter is always accurate
                try:
                    # Improved label extraction
                    _arg_label = (
                        fn_args.get("variable_name") or 
                        fn_args.get("x_label") or 
                        fn_args.get("group1_label") or
                        fn_args.get("observed_json") or
                        fn_args.get("items_json")
                    )
                    if isinstance(_arg_label, list):
                        _label = _arg_label[0] if _arg_label else "list"
                    elif isinstance(_arg_label, str):
                        # Extract column from "42:score" or just take start of JSON
                        _label = _arg_label.split(":")[-1] if ":" in _arg_label else _arg_label[:20]
                    else:
                        _label = "result"

                    create_analysis_job(
                        name=f"{fn_name.replace('_', ' ').title()} — {_label}",
                        method=fn_name,
                        dataset_ref="inline",
                        notes=json.dumps({
                            k: v for k, v in result.items()
                            if k in ("alpha", "r", "r_squared", "n", "chi2", "U",
                                     "z_statistic", "kmo_overall", "f_stat", "t_stat",
                                     "mean", "std", "interpretation")
                        }),

                    )
                except Exception:
                    pass  # Never let job creation break the stat response

            tool_result_parts.append(
                genai_types.Part(
                    function_response=genai_types.FunctionResponse(
                        name=fn_name,
                        response={"result": result},
                    )
                )
            )

        # Append tool results as user turn
        contents.append(genai_types.Content(role="user", parts=tool_result_parts))

    return "StatMind reached the maximum number of reasoning steps. Please try a more specific request."


def _detect_language(text: str) -> str:
    """
    Naive but fast language detector.
    Returns 'ID' if the text contains common Indonesian function words,
    otherwise returns 'EN'. Handles the coordinator forgetting to tag.
    """
    id_markers = [
        "saya", "anda", "tolong", "tampilkan", "buat", "daftar", "cari",
        "deadline", "tugas", "minggu", "hari", "berikan", "lihat", "tambah",
        "hapus", "semua", "dengan", "untuk", "yang", "dan", "atau", "tidak",
        "adalah", "dalam", "pada", "dari", "ke", "ini", "itu", "ada",
    ]
    lower = text.lower()
    score = sum(1 for w in id_markers if f" {w} " in f" {lower} " or lower.startswith(w))
    return "ID" if score >= 2 else "EN"


def _run_sub_agent(agent_type: str, task: str, history: list,
                   _accumulated_stats: dict = None) -> str:
    """Run a specific sub-agent for the given task."""
    agent_map = {
        "analysis": (ANALYSIS_AGENT_SYSTEM_PROMPT, ANALYSIS_TOOLS),
        "schedule": (SCHEDULE_AGENT_SYSTEM_PROMPT, SCHEDULE_TOOLS),
        "research": (RESEARCH_AGENT_SYSTEM_PROMPT, RESEARCH_TOOLS),
    }
    system_prompt, tools = agent_map[agent_type]

    # Ensure language tag is present — inject it if coordinator omitted it
    if not task.startswith("[LANG:"):
        # Try to detect from the original user message (last user turn in history)
        source_text = task
        for msg in reversed(history):
            if msg.get("role") == "user":
                source_text = msg.get("content", task)
                break
        lang = _detect_language(source_text)
        task = f"[LANG:{lang}] {task}"

    # Sub-agents get a clean history slice (last 6 turns for context)
    return _run_agent(system_prompt, tools, history[-6:], task,
                      _accumulated_stats=_accumulated_stats)


def run_coordinator(user_message: str, history: list) -> tuple[str, str, dict]:
    """
    Run the coordinator agent.
    Returns (reply_text, agent_used, stat_results) 3-tuple.
    stat_results contains raw numbers from stat tools (alpha, r, n, etc.)
    so the frontend never needs to regex-parse the agent's prose.
    agent_used is one of: coordinator, analysis, schedule, research
    """
    client = _get_client()

    # Shared dict — populated in-place by _run_agent when stat tools fire
    stat_results: dict = {}

    contents = []
    for msg in history:
        role = "model" if msg.get("role") == "assistant" else "user"
        contents.append(genai_types.Content(
            role=role,
            parts=[genai_types.Part(text=msg.get("content", ""))]
        ))
    contents.append(genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=user_message)]
    ))

    config = genai_types.GenerateContentConfig(
        system_instruction=COORDINATOR_SYSTEM_PROMPT,
        tools=[COORDINATOR_TOOLS],
        temperature=0.2,
        thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
    )

    agent_used = "coordinator"

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=config,
        )

        if not response.candidates:
            return "I'm sorry, I couldn't generate a response.", agent_used, stat_results

        candidate = response.candidates[0]
        finish_reason = str(candidate.finish_reason)

        if not candidate.content or not candidate.content.parts:
            if "SAFETY" in finish_reason:
                return "I can't respond to that request due to safety filters.", agent_used, stat_results
            return f"The model failed to generate a response (reason: {finish_reason}).", agent_used, stat_results

        response_parts = list(candidate.content.parts)
        tool_calls = [p for p in response_parts if p.function_call]

        if not tool_calls:
            text_parts = [p.text for p in response_parts if hasattr(p, "text") and p.text]
            return ("\n".join(text_parts) if text_parts else "(no response)"), agent_used, stat_results

        contents.append(genai_types.Content(role="model", parts=response_parts))

        tool_result_parts = []
        for part in tool_calls:
            fn_name = part.function_call.name
            fn_args = dict(part.function_call.args) if part.function_call.args else {}

            if fn_name == "call_analysis_agent":
                agent_used = "analysis"
                result_text = _run_sub_agent(
                    "analysis", fn_args.get("task", ""), history,
                    _accumulated_stats=stat_results,
                )
                result = {"agent": "AnalysisAgent", "response": result_text}
            elif fn_name == "call_schedule_agent":
                agent_used = "schedule"
                result_text = _run_sub_agent(
                    "schedule", fn_args.get("task", ""), history,
                    _accumulated_stats=stat_results,
                )
                result = {"agent": "ScheduleAgent", "response": result_text}
            elif fn_name == "call_research_agent":
                agent_used = "research"
                result_text = _run_sub_agent(
                    "research", fn_args.get("task", ""), history,
                    _accumulated_stats=stat_results,
                )
                result = {"agent": "ResearchAgent", "response": result_text}
            else:
                result = {"error": f"Unknown coordinator tool: {fn_name}"}

            tool_result_parts.append(
                genai_types.Part(
                    function_response=genai_types.FunctionResponse(
                        name=fn_name,
                        response={"result": result},
                    )
                )
            )

        contents.append(genai_types.Content(role="user", parts=tool_result_parts))

    return "StatMind reached the maximum reasoning steps. Please try a more specific request.", agent_used, stat_results
