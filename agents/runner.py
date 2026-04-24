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
    create_analysis_job,
    list_analysis_jobs,
    create_task,
    list_tasks,
    complete_task,
    get_upcoming_deadlines,
    save_research_note,
    search_research_notes,
    list_research_notes,
    register_dataset,
    list_datasets,
)

MODEL = "gemini-2.5-flash"
MAX_TOOL_ROUNDS = 6  # prevent infinite loops

# Maps tool name → Python function
TOOL_DISPATCH = {
    "cronbach_alpha": cronbach_alpha,
    "descriptive_stats": descriptive_stats,
    "pearson_correlation": pearson_correlation,
    "create_analysis_job": create_analysis_job,
    "list_analysis_jobs": list_analysis_jobs,
    "create_task": create_task,
    "list_tasks": list_tasks,
    "complete_task": complete_task,
    "get_upcoming_deadlines": get_upcoming_deadlines,
    "save_research_note": save_research_note,
    "search_research_notes": search_research_notes,
    "list_research_notes": list_research_notes,
    "register_dataset": register_dataset,
    "list_datasets": list_datasets,
}


def _get_client() -> genai.Client:
    return genai.Client(
        vertexai=True,
        project="my-project-31-491314",
        location="us-central1"
    )


def _run_agent(system_prompt: str, tools: genai_types.Tool,
               messages: list, user_message: str) -> str:
    """
    Core stateless agent loop.
    Appends user_message to messages, then calls the model in a loop
    dispatching tool calls until a final text response is returned.
    """
    client = _get_client()

    # Build contents list from history + new message
    contents = []
    for msg in messages:
        role = msg.get("role", "user")
        # google-genai only accepts "user" and "model" roles
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
    )

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=config,
        )

        candidate = response.candidates[0]
        finish_reason = candidate.finish_reason

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


def _run_sub_agent(agent_type: str, task: str, history: list) -> str:
    """Run a specific sub-agent for the given task."""
    agent_map = {
        "analysis": (ANALYSIS_AGENT_SYSTEM_PROMPT, ANALYSIS_TOOLS),
        "schedule": (SCHEDULE_AGENT_SYSTEM_PROMPT, SCHEDULE_TOOLS),
        "research": (RESEARCH_AGENT_SYSTEM_PROMPT, RESEARCH_TOOLS),
    }
    system_prompt, tools = agent_map[agent_type]
    # Sub-agents get a clean history slice (last 6 turns for context)
    return _run_agent(system_prompt, tools, history[-6:], task)


def run_coordinator(user_message: str, history: list) -> tuple[str, str]:
    """
    Run the coordinator agent.
    Returns (reply_text, agent_used) tuple.
    agent_used is one of: coordinator, analysis, schedule, research
    """
    client = _get_client()

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
    )

    agent_used = "coordinator"

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=config,
        )

        candidate = response.candidates[0]
        finish_reason = str(candidate.finish_reason)
        response_parts = list(candidate.content.parts)
        tool_calls = [p for p in response_parts if p.function_call]

        if not tool_calls:
            # Guard: check for non-STOP finish reasons
            if "SAFETY" in finish_reason:
                return "I can't respond to that request.", agent_used
            if "MAX_TOKENS" in finish_reason:
                # Still return what we have
                pass
            text_parts = [p.text for p in response_parts if hasattr(p, "text") and p.text]
            return ("\n".join(text_parts) if text_parts else "(no response)"), agent_used

        contents.append(genai_types.Content(role="model", parts=response_parts))

        tool_result_parts = []
        for part in tool_calls:
            fn_name = part.function_call.name
            fn_args = dict(part.function_call.args) if part.function_call.args else {}

            if fn_name == "call_analysis_agent":
                agent_used = "analysis"
                result_text = _run_sub_agent("analysis", fn_args.get("task", ""), history)
                result = {"agent": "AnalysisAgent", "response": result_text}
            elif fn_name == "call_schedule_agent":
                agent_used = "schedule"
                result_text = _run_sub_agent("schedule", fn_args.get("task", ""), history)
                result = {"agent": "ScheduleAgent", "response": result_text}
            elif fn_name == "call_research_agent":
                agent_used = "research"
                result_text = _run_sub_agent("research", fn_args.get("task", ""), history)
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

    return "StatMind reached the maximum reasoning steps. Please try a more specific request.", agent_used
