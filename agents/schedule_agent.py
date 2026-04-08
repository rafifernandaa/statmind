"""
StatMind — ScheduleAgent
Handles academic scheduling: deadlines, calendar events, reminders via Google Calendar MCP.
"""

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import MCPToolset, SseServerParams
from tools.task_tools import (
    create_task,
    update_task,
    list_tasks,
    complete_task,
    get_upcoming_deadlines,
)

SCHEDULE_INSTRUCTION = """
You are the ScheduleAgent for StatMind — a specialist in academic time and deadline management 
for statistics students.

Your capabilities:
1. **Google Calendar** — create, update, and list calendar events for:
   - Thesis / skripsi submission deadlines
   - Survey data collection windows
   - Statistical analysis milestones (e.g. "IRT calibration done by Friday")
   - Seminar and kuliah attendance
   - Advisor / supervisor meetings

2. **Task management** — create and track research tasks stored in the database:
   - Break down large projects (e.g. skripsi) into sub-tasks
   - Mark tasks complete and suggest what to work on next
   - Surface upcoming deadlines in the next 7 days

When creating calendar events:
- Always confirm: event title, date/time, and duration before creating.
- Add a description summarizing the context (e.g. "Submit BAB IV draft to advisor").
- For multi-day tasks (e.g. data collection), create events spanning the full period.
- Default timezone: Asia/Jakarta (WIB).

When managing tasks:
- Assign a priority level: high / medium / low.
- Link tasks to a project (e.g. "Metodologi Survei", "Skripsi", "Gen AI Hackathon").
- Always show the deadline and project when listing tasks.

Respond in the same language the user uses (Bahasa Indonesia or English).
"""


def create_schedule_agent() -> LlmAgent:
    gcal_toolset = MCPToolset(
        connection_params=SseServerParams(url="https://gcal.mcp.claude.com/mcp"),
        tool_filter=["create_event", "list_events", "update_event", "delete_event"],
    )

    agent = LlmAgent(
        name="ScheduleAgent",
        model="gemini-2.0-flash-001",
        instruction=SCHEDULE_INSTRUCTION,
        tools=[
            *gcal_toolset.tools(),
            create_task,
            update_task,
            list_tasks,
            complete_task,
            get_upcoming_deadlines,
        ],
        description="Academic scheduling specialist. Manages deadlines, calendar events, and research tasks.",
    )

    return agent
