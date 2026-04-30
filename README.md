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
*   **Bilingual Expertise:** Seamless support for both **English** and **Bahasa Indonesia**.
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
├── Dockerfile               # Container definition for Cloud Run
├── requirements.txt         # Project dependencies
├── deploy.sh                # Cloud Run deployment script
└── setup_gcp.sh             # GCP resource & IAM provisioning script
```

---

## 🛠️ Local Development

1.  **Environment Setup:**
    ```bash
    cp .env.example .env
    # Note: Vertex AI uses IAM. No GOOGLE_API_KEY needed if authenticated via gcloud.
    ```

2.  **Authenticate:**
    ```bash
    gcloud auth application-default login
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run Application:**
    ```bash
    python -m api.main
    # Access at http://localhost:8080
    ```

---

## ☁️ Deployment (Google Cloud)

StatMind is optimized for the Google Cloud ecosystem using **Vertex AI** and **IAM-based security**:

1.  **Provision Resources:** `chmod +x setup_gcp.sh && ./setup_gcp.sh`
    *   This script creates a Service Account with `roles/aiplatform.user`.
2.  **Deploy to Cloud Run:** `chmod +x deploy.sh && ./deploy.sh`
    *   The service automatically authenticates via the assigned Service Account.
    *   No API keys are stored or managed in the cloud environment.

---

## 🚀 Step-by-Step Google Cloud Deployment

Follow these steps to deploy StatMind to a production environment on Google Cloud:

### 1. Initial GCP Setup
*   Create a new project in the [Google Cloud Console](https://console.cloud.google.com/).
*   Note your **Project ID** (e.g., `my-project-123`).
*   Enable the following APIs:
    ```bash
    gcloud services enable \
        run.googleapis.com \
        sqladmin.googleapis.com \
        secretmanager.googleapis.com \
        aiplatform.googleapis.com \
        compute.googleapis.com \
        artifactregistry.googleapis.com \
        cloudbuild.googleapis.com
    ```

### 2. Provision Infrastructure
StatMind includes a `setup_gcp.sh` script that automates the creation of Service Accounts, IAM roles, and the Cloud SQL database.
*   Open `setup_gcp.sh` and update the `PROJECT_ID` variable with your ID.
*   Run the script:
    ```bash
    chmod +x setup_gcp.sh
    ./setup_gcp.sh
    ```
*   **Note:** This script will generate a random password for your database and store it securely in **Secret Manager**.

### 3. Deploy the Application
Once the infrastructure is ready, use the `deploy.sh` script to build and deploy the container.
*   Open `deploy.sh` and ensure the `PROJECT_ID` and `REGION` match your setup.
*   Run the deployment:
    ```bash
    chmod +x deploy.sh
    ./deploy.sh
    ```
*   The script will:
    1.  Build your Docker image using **Cloud Build**.
    2.  Push it to **Artifact Registry**.
    3.  Deploy it to **Cloud Run** with the correct environment variables and secret bindings.

### 4. Verification
*   After the script finishes, it will print a Service URL (e.g., `https://statmind-xxx.a.run.app`).
*   Visit the URL to access the StatMind web interface.
*   Check the logs in the Cloud Run console if you encounter any issues.

---

## 💡 Lessons from Evolution

StatMind was built to address critical failure points identified in earlier prototypes:
*   **Stability:** Moved from ADK-based session management to a **custom SQLAlchemy session store** to eliminate `SessionNotFoundError`.
*   **Precision:** Replaced LLM-based calculations with **native Python tool calls** to ensure zero-hallucination statistical outputs.
*   **Scalability:** Implemented a **Coordinator-Specialist pattern** to manage long-running research workflows without overwhelming the context window.
