# StatMind — Multi-Agent Productivity Assistant for Statistics

> *Turning Uncertainty Into Insight* — Rafi Fernanda Aldin, Universitas Negeri Jakarta

---

## What is StatMind?

StatMind is a multi-agent AI productivity assistant designed specifically for **statistics students
and researchers**. It understands your academic context: IRT, SEM, Cronbach's α, survey data,
BigQuery datasets, thesis deadlines, and research notes.

**Stack:** `google-genai` (direct client) · FastAPI · Cloud Run · Cloud SQL (PostgreSQL) · SQLite (dev)

---

## Architecture

```
User
  │  POST /chat
  ▼
FastAPI  (api/main.py)
  │  loads session history from DB
  ▼
CoordinatorAgent  (agents/runner.py :: run_coordinator)
  │  calls one or more sub-agents as tools
  ├──► call_analysis_agent  →  AnalysisAgent
  │       tools: cronbach_alpha, descriptive_stats, pearson_correlation,
  │              create_analysis_job, list_analysis_jobs
  │
  ├──► call_schedule_agent  →  ScheduleAgent
  │       tools: create_task, list_tasks, complete_task, get_upcoming_deadlines
  │
  └──► call_research_agent  →  ResearchAgent
          tools: save_research_note, search_research_notes, list_research_notes,
                 register_dataset, list_datasets
  │
  ▼
FastAPI stores updated history in DB → returns reply to user
```

---

## Lessons Applied from Previous Builds

| App | Bug | Fix applied in StatMind |
|---|---|---|
| Professor Stats | `SessionNotFoundError` with ADK Runner + session service | **No ADK Runner. No session service.** Use `google-genai` client directly. Sessions in DB. |
| StatScout | Remote MCP endpoint for BigQuery failed tool resolution | **No remote MCP for DB tools.** Native Python functions declared as `FunctionDeclaration`. |
| StatQuery | Deployment failed without `--clear-base-image` | `--clear-base-image` in `deploy.sh` |
| StatQuery | AlloyDB SA missing `roles/aiplatform.user` | All required roles in `setup_gcp.sh` including `roles/aiplatform.user` |
| StatScout | `google-adk==1.28.0` + `gemini-2.5-flash-preview-04-17` confirmed working | Same versions pinned in `requirements.txt` |

---

## File Structure

```
statmind/
├── agents/
│   ├── prompts.py           # All system prompts (coordinator + 3 sub-agents)
│   ├── tool_declarations.py # FunctionDeclaration objects for google-genai
│   └── runner.py            # Stateless agent loop — google-genai client directly
├── api/
│   └── main.py              # FastAPI app, session management, all REST endpoints
├── db/
│   ├── models.py            # SQLAlchemy models: ChatSession, Task, AnalysisJob, etc.
│   └── database.py          # Engine factory: SQLite (dev) / Cloud SQL (prod)
├── tools/
│   └── stat_tools.py        # Pure-Python stats + DB CRUD tools
├── .env.example
├── Dockerfile
├── deploy.sh                # Cloud Run deployment (with --clear-base-image)
├── setup_gcp.sh             # One-time GCP resource setup
└── requirements.txt
```

---

## Example Workflows

### Workflow 1 — Cronbach's alpha
```
User: "Hitung Cronbach's alpha untuk data ini: [[4,3,5],[3,2,4],[5,5,5],[4,4,4]]"
→ Coordinator → AnalysisAgent → cronbach_alpha()
← α = 0.89, Good reliability, item-total correlations, flagged items
```

### Workflow 2 — Task + deadline
```
User: "Add task: submit BAB IV draft by May 20, project Skripsi, high priority"
→ Coordinator → ScheduleAgent → create_task()
← Task created with ID 1, due 2025-05-20, high priority
```

### Workflow 3 — Research note
```
User: "Save a note about SMARVUS dataset for my skripsi"
→ Coordinator → ResearchAgent → register_dataset() + save_research_note()
← Dataset registered, note saved with tags
```

### Workflow 4 — Multi-step
```
User: "Run descriptive stats on [4.2, 3.8, 5.0, 4.5] then save as a note"
→ Coordinator → AnalysisAgent (descriptive_stats)
→ Coordinator → ResearchAgent (save_research_note with results)
← Stats summary + note saved
```

---

## Core Requirements Checklist

| Requirement | Implementation |
|---|---|
| Primary agent + sub-agents | `CoordinatorAgent` routes to 3 domain sub-agents via tool calls |
| Structured database | Cloud SQL / SQLite — 5 tables via SQLAlchemy |
| Multiple tools via MCP pattern | `FunctionDeclaration` tools: stat tools, task tools, note tools |
| Multi-step workflows | Coordinator chains sub-agents in sequence within one request |
| API-based deployment | FastAPI on Cloud Run, `my-project-31-491314`, `us-central1` |

---

## Local Development

```bash
cp .env.example .env
# Edit .env: set GOOGLE_API_KEY

pip install -r requirements.txt
python -m api.main
# → http://localhost:8080
```

Test the chat endpoint:
```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hitung Cronbach alpha: [[4,3,5],[3,2,4],[5,5,5]]"}'
```

---

## Deployment

```bash
# Step 1 — one-time GCP setup
chmod +x setup_gcp.sh && ./setup_gcp.sh

# Step 2 — store API key
echo -n "YOUR_GOOGLE_API_KEY" | gcloud secrets create statmind-api-key --data-file=- \
  --project my-project-31-491314

# Step 3 — deploy
chmod +x deploy.sh && ./deploy.sh
```

---

## GCP Resources

| Resource | Value |
|---|---|
| Project | `my-project-31-491314` |
| Region | `us-central1` |
| Service account | `statmind-sa@my-project-31-491314.iam.gserviceaccount.com` |
| Cloud SQL | `statmind-db` (PostgreSQL 15) |
| Service name | `statmind` |

SA roles required: `bigquery.dataViewer`, `bigquery.jobUser`, `cloudsql.client`,
`secretmanager.secretAccessor`, `aiplatform.user`, `run.invoker`
