# StatMind — Multi-Agent Productivity Assistant for Statistics

> *Turning Uncertainty Into Insight* — RF

StatMind is a production-grade multi-agent AI assistant designed to streamline the academic lifecycle of statistics students and researchers. It bridges the gap between raw data analysis, academic project management, and knowledge organization.

---

## 🚀 Key Features

*   **Multi-Agent Intelligence:** A specialized **Coordinator** routes your requests to three expert sub-agents:
    *   **Analysis Agent:** Your "Personal Statistician" for 12+ tests including Cronbach's α, ANOVA, Regression, and Normality.
    *   **Schedule Agent:** Your "Academic Project Manager" for tracking thesis milestones and deadlines.
    *   **Research Agent:** Your "Knowledge Librarian" for cataloging datasets and research notes.
*   **Production-Ready Stack:** Built with `google-genai` (Gemini 2.5 Flash), FastAPI, and Cloud SQL (PostgreSQL).
*   **Structured Data Reference:** Native support for `dataset_id:column` references, allowing the agent to perform complex stats without the user pasting raw data repeatedly.
*   **Bilingual Expertise:** Seamless support for both **English** and **Bahasa Indonesia**, matching the academic context of regional universities (like UNJ).
*   **Academic Report Export:** Generate structured analysis reports ready to be pasted directly into Word documents for thesis or journal submissions.

---

## 🏗️ Architecture

```mermaid
graph TD
    User((User)) -->|POST /chat| API[FastAPI - api/main.py]
    API -->|Session Data| DB[(Cloud SQL / SQLite)]
    API -->|Prompt| Coordinator[CoordinatorAgent - agents/runner.py]
    
    subgraph "Expert Sub-Agents"
        Coordinator -->|Tool Call| Analysis[AnalysisAgent]
        Coordinator -->|Tool Call| Schedule[ScheduleAgent]
        Coordinator -->|Tool Call| Research[ResearchAgent]
    end
    
    subgraph "Native Tools"
        Analysis -->|Python| StatTools[stat_tools.py: α, r, t, F, χ²]
        Schedule -->|CRUD| TaskTools[Task Management]
        Research -->|Catalog| NoteTools[Note & Dataset Store]
    end
    
    Coordinator -->|Synthesized Reply| API
    API -->|Response| User
```

---

## 📊 Statistical Toolkit

| Category | Available Tests |
|---|---|
| **Psychometrics** | Cronbach's Alpha, Item Analysis (r_itc, α-if-deleted), KMO & Bartlett |
| **Comparison** | Independent T-Test (Welch), One-Way ANOVA, Mann-Whitney U |
| **Relationship** | Pearson Correlation, Spearman Rank Correlation, Simple Linear Regression |
| **Distribution** | Normality Tests (Shapiro-Wilk / Skewness-Kurtosis), Descriptive Stats |
| **Planning** | Sample Size Calculators (Cochran, T-test, ANOVA, Correlation) |
| **Categorical** | Chi-Square (Goodness-of-Fit & Independence) |

---

## 📂 File Structure

```text
statmind/
├── agents/
│   ├── prompts.py           # Unified system prompts for all 4 agents
│   ├── tool_declarations.py # FunctionDeclaration objects for Gemini
│   └── runner.py            # Stateless agent loop using direct google-genai client
├── api/
│   ├── main.py              # FastAPI application & session management
│   └── static/              # Frontend assets (index.html)
├── db/
│   ├── models.py            # SQLAlchemy models: ChatSession, Task, AnalysisJob, ResearchNote, Dataset
│   └── database.py          # Database engine (SQLite for dev / Cloud SQL for prod)
├── tools/
│   └── stat_tools.py        # 12+ Pure-Python statistical & management tools
├── deploy.sh                # Cloud Run deployment script
└── setup_gcp.sh             # GCP resource & IAM provisioning script
```

---

## 🛠️ Local Development

1.  **Environment Setup:**
    ```bash
    cp .env.example .env
    # Edit .env and set GOOGLE_API_KEY
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run Application:**
    ```bash
    python -m api.main
    # Access at http://localhost:8080
    ```

---

## ☁️ Deployment (Google Cloud)

StatMind is optimized for the Google Cloud ecosystem:

1.  **Provision Resources:** `chmod +x setup_gcp.sh && ./setup_gcp.sh`
2.  **Store Secrets:** 
    ```bash
    echo -n "YOUR_API_KEY" | gcloud secrets create statmind-api-key --data-file=-
    ```
3.  **Deploy to Cloud Run:** `chmod +x deploy.sh && ./deploy.sh`
