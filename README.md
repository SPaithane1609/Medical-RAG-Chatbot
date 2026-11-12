# 🩺 Medical RAG Chatbot — End-to-End LLMOps & Cloud Deployment

An end-to-end, production-ready **Retrieval-Augmented Generation (RAG)** conversational assistant designed for medical knowledge retrieval. Built with **LangChain**, **Groq**, **HuggingFace Embeddings**, and **FAISS**, this project goes beyond local prototyping by implementing a complete **LLMOps & DevSecOps lifecycle**—featuring containerized builds, automated vulnerability scanning with **Trivy**, **Jenkins CI/CD**, **AWS ECR** image registry, and serverless container orchestration on **AWS ECS Fargate**.
<img width="1920" height="1080" alt="Screenshot (251)" src="https://github.com/user-attachments/assets/ecb982c3-1cbb-46b4-a75d-e43cf58c21e1" />
<img width="1920" height="1080" alt="Screenshot (255)" src="https://github.com/user-attachments/assets/a8bdb07c-6874-45ff-93c1-ce8b12968198" />



## 🏗️ System Architecture & LLMOps Pipeline

The platform decouples core generative AI inference from automated build, security scanning, and cloud deployment workflows:

```
flowchart TB
    subgraph CI_CD["🔄 CI/CD & DevSecOps Pipeline (Jenkins)"]
        GH["GitHub Repository<br/>(main branch)"] --> JK["Jenkins Pipeline"]
        JK --> DB["Docker Build<br/>(python:3.10-slim)"]
        DB --> TV["Trivy Security Scan<br/>(HIGH & CRITICAL CVEs)"]
        TV --> ECR["AWS ECR<br/>(medical-rag-repo)"]
    end

    subgraph AWS_PROD["☁️ Serverless Production Runtime (AWS us-east-1)"]
        ECR -->|Rolling Deployment| ECS["AWS ECS Cluster<br/>(medical-rag-cluster)"]
        ECS --> FG["AWS Fargate Service<br/>(llmops-medical-service :5000)"]
    end

    subgraph RAG_ENGINE["🧠 Medical RAG Application"]
        USER["User Query"] --> FL["Flask Web App<br/>(Session & XSS Hardened)"]
        FL --> EMB["HuggingFace / SentenceTransformers<br/>Query Embedding"]
        EMB --> VDB[("FAISS Vector Store<br/>Medical PDF Knowledge Base")]
        VDB -->|Top-K Context| LLM["Groq LLM Inference<br/>(LangChain QA Chain)"]
        LLM -->|Grounded Response| FL
    end

    FG --- RAG_ENGINE

```

## ✨ Key Engineering Highlights

### 🧠 Generative AI & RAG Architecture

* **Grounded Medical Q&A:** Combines semantic retrieval over medical PDF corpora (`pypdf`, `langchain-text-splitters`) with high-speed LLM inference via `langchain-groq` to minimize hallucinations.

* **Dense Vector Retrieval:** Utilizes `HuggingFace` and `sentence-transformers` embeddings indexed in `FAISS` (`faiss-cpu`) for low-latency similarity search inside stateless containers.

* **Stateful Multi-Turn Context:** Manages server-side conversation history via `Flask-Session` with a sliding window (`MAX_MESSAGES = 50`) to maintain dialogue continuity without unbounded memory growth.

### 🛡️ LLMOps, DevSecOps & Cloud Infrastructure

* **Automated CI/CD (`Jenkinsfile`):** Automates repository checkout, Docker image builds, vulnerability auditing, ECR pushes, and zero-downtime ECS rolling deployments (`--force-new-deployment`) with service stability verification (`aws ecs wait services-stable`).

* **Container Vulnerability Scanning:** Integrates **Aqua Trivy** into the CI pipeline to scan container images for `HIGH` and `CRITICAL` CVEs prior to registry push, archiving structured JSON audit reports (`trivy-report.json`) as Jenkins build artifacts.

* **Serverless Container Orchestration:** Deployed on **AWS ECS with Fargate**, eliminating EC2 server management while enabling elastic scaling and isolated task execution.

* **Application Security:** Implements strict HTML escaping (`markupsafe`) before rendering newline formatting (`nl2br`) to prevent Cross-Site Scripting (XSS) in chat outputs, alongside environment-based secret management.

* **Automated Cloud FinOps (`teardown.py`):** Includes an idempotent `boto3` infrastructure cleanup utility that drains Fargate tasks, deletes ECS services/clusters, purges ECR repositories, and revokes IAM credentials/policies to prevent idle cloud spend.

## 🛠️ Tech Stack

| Layer | Technologies | 
| ----- | ----- | 
| **LLM & Orchestration** | LangChain (`langchain`, `langchain-community`, `langchain-groq`), Groq API | 
| **Embeddings & Vector DB** | HuggingFace Hub, `sentence-transformers`, FAISS (`faiss-cpu`), `pypdf` | 
| **Backend & Frontend** | Python 3.10, Flask, Flask-Session, Jinja2, MarkupSafe | 
| **Containerization** | Docker (`python:3.10-slim`), Editable Python Packaging (`setup.py`) | 
| **CI/CD & DevSecOps** | Jenkins Declarative Pipeline, Trivy Container Scanner, GitHub | 
| **Cloud & Infrastructure** | AWS ECS, AWS Fargate, AWS ECR, AWS IAM, AWS SDK for Python (`boto3`) | 

## 📂 Repository Structure

```

Medical-RAG-Chatbot/
├── app/
│   ├── common/
│   │   ├── custom_exception.py # Custom error handling and stack trace formatting
│   │   └── logger.py           # Centralized application logging configuration
│   ├── components/
│   │   ├── data_loader.py      # Orchestrates document loading and chunking pipeline
│   │   ├── embeddings.py       # Embedding model initialization
│   │   ├── llm.py              # Large Language Model setup and parameters
│   │   ├── pdf_loader.py       # Medical PDF parsing and text extraction
│   │   ├── retriever.py        # LangChain QA chain & FAISS retriever initialization
│   │   └── vector_store.py     # FAISS vector database creation, saving, and loading
│   ├── config/
│   │   └── config.py           # Model, embedding, and file path configurations
│   ├── templates/
│   │   └── index.html          # Chat interface template
│   └── application.py          # Flask web server, session management, & XSS filtering
├── custom_jenkins/             # Custom Jenkins Docker image & CI/CD tool configurations
├── data/                       # Source medical PDF documents for knowledge base ingestion
├── vectorstore/                # Persisted local FAISS vector index files
├── Dockerfile                  # Multi-step slim Python 3.10 container definition
├── Jenkinsfile                 # End-to-end CI/CD & Trivy security pipeline
├── teardown.py                 # Automated AWS resource & IAM cleanup script (boto3)
├── setup.py                    # Package distribution & dependency configuration
├── requirements.txt            # Pinned AI, web, and AWS SDK dependencies
└── .gitignore                  # Excludes venv, logs, flask_session, .env, & egg-info

```

## 🚀 Getting Started (Local Development)

### Prerequisites

* Python **3.10+**

* [Groq API Key](https://console.groq.com/)

* [HuggingFace Access Token](https://huggingface.co/settings/tokens) (for embedding models)

* Docker (optional, for local container testing)

### 1. Clone the Repository

```
git clone https://github.com/SPaithane1609/Medical-RAG-Chatbot.git
cd Medical-RAG-Chatbot

```

### 2. Configure Environment Variables

Create a `.env` file in the root directory:

```
GROQ_API_KEY=your_groq_api_key_here
HF_TOKEN=your_huggingface_token_here
SECRET_KEY=your_secure_flask_session_secret
FLASK_DEBUG=0

```

### 3. Install & Run Locally

```
python -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate

# Install the project and dependencies in editable mode
pip install --no-cache-dir -e .

# Launch the Flask server
python app/application.py

```

Access the application at **`http://localhost:5000`**.

### 4. Run via Docker Locally

```
docker build -t medical-rag-chatbot:local .
docker run -p 5000:5000 --env-file .env medical-rag-chatbot:local

```

## ⚙️ CI/CD & AWS Deployment Workflow

The `Jenkinsfile` automates production releases on every push to `main`:

1. **Source Checkout:** Pulls the latest commit from `https://github.com/SPaithane1609/Medical-RAG-Chatbot.git`.

2. **Docker Build & Trivy Audit:**

   * Authenticates with AWS ECR (`us-east-1`) via AWS CLI.

   * Builds the lightweight `python:3.10-slim` production image.

   * Executes `trivy image --severity HIGH,CRITICAL` and archives `trivy-report.json` for compliance review.

3. **Artifact Registry Push:** Tags and pushes the verified image to `medical-rag-repo:latest` in AWS ECR.

4. **ECS Fargate Rolling Deployment:**

   * Forces a new deployment on ECS cluster `medical-rag-cluster` / service `llmops-medical-service`.

   * Blocks until `aws ecs wait services-stable` confirms healthy Fargate task replacement.

## 🧹 Infrastructure Teardown (Cost Optimization)

To cleanly decommission all AWS infrastructure after testing or demonstration and avoid ongoing Fargate/ECR charges, run the automated `boto3` teardown script:

```
python teardown.py

```

This script sequentially:

1. Scales active ECS services in `medical-rag-cluster` to `0`, deletes them, and waits for Fargate tasks to drain.

2. Deletes the ECS cluster (`medical-rag-cluster`).

3. Force-deletes the ECR repository (`medical-rag-repo`) and all stored container images.

4. Detaches managed policies, removes access keys, deletes custom IAM policies (`ECS-PassRole-Policy`), and removes the deployment IAM user (`medical-rag-user`).

## ⚠️ Medical Disclaimer

*This application is developed for educational, research, and software engineering demonstration purposes only. Responses generated by the RAG pipeline are derived from indexed reference documents and should **not** be used as a substitute for professional medical advice, diagnosis, or treatment.*

## 👤 Author

**Siddhant Paithane**

*AI Engineer | LLMOps & Cloud Deployment*

GitHub: [@SPaithane1609](https://github.com/SPaithane1609)
