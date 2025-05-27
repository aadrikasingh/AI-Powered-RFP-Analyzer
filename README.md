# 🤖 AI-Powered RFP Analyzer: An Azure-Based Multi-Agent Accelerator for RFP & Proposal Evaluation Using Semantic Kernel

A turnkey, multi-agent solution accelerator for automating the evaluation of RFPs/RFTs and Vendor/Supplier Proposals. This accelerator helps procurement teams reduce manual effort, ensure compliance, analyze vendor capabilities, and generate strategic negotiation recommendations—delivered as a structured, final evaluation report ; all deployed in your Azure tenant in under an hour.

---

## 🔍 Table of Contents

- [✨ Features](#✨-features)  
- [📐 Architecture](#📐-architecture)  
- [⚙️ Tech Stack](#⚙️-tech-stack)  
- [☁️ Provisioned Azure Services](#☁️-provisioned-azure-services)  
- [🔧 Environment Variables](#🔧-environment-variables)  
- [🚀 Step-by-Step Deployment](#🚀-step-by-step-deployment)
- [🤝 Contributing](#🤝-contributing)  
- [📄 License](#📄-license)  

---

## ✨ Features

The **AI-Powered RFP Analyzer** combines modular AI agents, LLM orchestration with Semantic Kernel Agent Framework, and vector-based reasoning to deliver a complete procurement intelligence system. Each feature corresponds to a specialized agent that independently analyzes vendor/supplier proposals and contributes to a unified evaluation.

---

### 🧾 RFP/RFT Compliance Scoring Agent
Evaluate how well a Vendor or Supplier Proposal aligns with the original RFP/RFT document:
- Extracts and compares proposal content against mandatory RFP requirements.
- Identifies key gaps or misalignments in scope, deliverables, or terms.
- Assigns a **compliance score (1–10)** based on completeness and relevance.
- Highlights critical missing elements that may disqualify the vendor.

---

### ⚖️ Legal & Regulatory Risk Assessment Agent
Ensure the proposal meets internal policies and external regulatory standards:
- Cross-references legal clauses using an Azure-hosted vector index of procurement laws and policies.
- Flags missing or non-compliant sections such as liability, dispute resolution, or contract termination terms.
- Outputs a **risk level: Low, Medium, or High**, with a structured explanation.
- Helps legal and procurement teams pre-empt contractual risks.

---

### 🏢 Vendor Reputation & Stability Evaluation Agent
Assess the historical performance, financial stability, and credibility of vendors:
- Reviews past projects, industries served, customer satisfaction, and compliance history.
- Integrates with sample vendor vector indexes (or real data) for factual reputation signals.
- Produces a **reputation score (1–10)** reflecting reliability, experience, and maturity.
- Avoids speculative or price-driven assessments—focuses purely on track record and signals.

---

### 🌍 Market Intelligence Integration Agent
Incorporate contextual industry insights to inform strategic decision-making:
- Simulates or integrates with APIs to gather market conditions.
- Benchmarks the vendor against competitors, highlighting differentiators or red flags.
- Evaluates macro risks such as economic conditions, supply chain volatility, or regulatory trends.
- Outputs a **market risk rating (Low, Medium, High)** with supporting narrative.

---

### 🧠 Negotiation Strategy Generator Agent
Craft actionable negotiation strategies tailored to each vendor:
- Synthesizes insights from compliance, legal, vendor, and market agents.
- Identifies leverage points (e.g. gaps, dependencies, differentiators).
- Recommends a strategy type: **Defensive**, **Balanced**, or **Aggressive**.
- Provides structured suggestions for mitigation, incentives, and fallback positions.

---

### 📊 Final Evaluation Report Compilation Agent
Consolidate all agent outputs into a clear, concise, and decision-ready report:
- Aggregates findings into a unified assessment with supporting justifications.
- Assigns a **final vendor score (1–10)** indicating overall suitability and risk level.
- Includes highlights, concerns, and strategic recommendations.
- Outputs a Markdown or PDF document for stakeholder circulation.

---

Together, these features allow procurement teams to move faster, reduce subjectivity, ensure compliance, and drive stronger vendor outcomes with confidence.

## 📐 Architecture

### 🔹 High-Level Infrastructure

![Architecture Diagram](docs/architecture.jpg)

- **User Interaction**: End users interact via a web browser to upload documents and trigger evaluations.
- **Azure Container Apps Environment**: Hosts the core containerized Python application.
- **Worker Container App**: Runs the multi-agent logic for evaluation and reporting.
- **Connected Azure Services**:
  - **Azure OpenAI** – Powers the intelligent agents using GPT-based models.
  - **Azure AI Search** – Enables semantic and vector-based retrieval of indexed data.
  - **Azure Document Intelligence** – Extracts structured data from RFPs and proposals.
  - **Azure Storage Account** – Stores document inputs and intermediate outputs.
  - **Azure Container Registry (ACR)** – Hosts the application’s Docker image.
  - **Azure Storage Account** – Stores uploaded documents and temporary data.

---

### 🔹 Solution Workflow

![Solution Flow](docs/solution-flow.png)

1. **📤 Upload**  
   Users upload RFPs and Vendor/Supplier Proposals via the web interface or API.

2. **📄 Document Parsing & Summarization**  
   The system extracts and summarizes content from both documents using Azure Document Intelligence.

3. **🤖 Multi-Agent Evaluation**  
   The `Semantic Kernel Orchestrator` initiates an agent group chat with specialized agents:
   - **RFP Compliance Agent**: Compares the proposal against RFP requirements.
   - **Legal Compliance Agent**: Identifies legal and regulatory risks.
   - **Vendor Evaluation Agent**: Assesses vendor reputation, stability, and performance.
   - **Market Intelligence Agent**: Evaluates market trends and competitive risks.
   - **Negotiation Strategy Agent**: Recommends negotiation approaches based on findings.

4. **📊 Report Generation**  
   The `Evaluation Report Generator Agent` consolidates all agent assessments into a final, structured **Vendor Proposal Evaluation Report**, including scores, risks, and recommendations.

---

## ⚙️ Tech Stack

- **Language**: Python 3.12.10  
- **Containerization**: Docker
- **Infrastructure-as-Code**: Bicep (located in `/infra` folder)  
- **Deployment Target**: Azure Container Apps  
- **Source Code**: Located in `/src` folder  
- **Image Registry**: Azure Container Registry  
- **Multi-Agent Orchestration**: Semantic Kernel
- **LLM Integration**: Azure OpenAI
- **Document Parsing**: Azure Document Intelligence  
- **Search/Indexing**: Azure AI Search (Vector + Semantic)

---

## ☁️ Provisioned Azure Services

The Bicep templates provision the following Azure resources:

- **Azure Container Apps** – Hosts the containerized multi-agent Python app.
- **Azure Container Apps Environment** – Provides isolated execution for the app.
- **Azure Container Registry (ACR)** – Stores and serves the app container image.
- **Azure Document Intelligence** – Extracts structured data from RFP documents.
- **Azure OpenAI** – Powers intelligent agents using GPT-based models.
- **Azure AI Search** – Enables semantic and vector-based search across processed content.
- **Azure Storage Account** – Stores uploaded documents and temporary data.

---

## 🔧 Environment Variables

Environment variables are used to configure service connections and runtime behavior. These are typically managed by AZD and include:

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_KEY`
- `AZURE_SEARCH_SERVICE_NAME`
- `AZURE_STORAGE_ACCOUNT`
- `AZURE_FORM_RECOGNIZER_ENDPOINT`

You can set or review these in `.env` or via the `azd env` commands.

---

## 🚀 Step-by-Step Deployment

Follow these steps to deploy the solution using AZD:

### 1. Prerequisites

- [Azure Developer CLI (AZD)](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)
- The accelerator expects two vector-indexes created on Azure AI Search to facilitate the run of *Legal Compliance Agent* and *Vendor Evaluation Agent*, named *legal-policy-index* and *supplier-insights-index* respectively. Please customize and create them per your use-case data or use the sample documents available under src/documents/sample-docs/index-creation.

### 2. Clone the Repository

```bash
# Clone the repository
git clone https://github.com/aadrikasingh/AI-Powered-RFP-Analyzer.git
cd into the clones repo (AI-Powered-RFP-Analyzer)

# Login to Azure
az login

# Initialize AZD environment (optional to specify a name)
azd init
azd env new <environment-name>  # Optional

# Deploy the solution
azd up
```
---

## 🤝 Contributing

We welcome contributions to enhance and evolve the **AI-Powered RFP Analyzer** accelerator. To get started:

- Fork the repo
- Create a feature branch
- Make your changes
- Push and open a PR

## 📄 License

This project is licensed under the [MIT License](LICENSE).
> ⚠️ **Note**: This solution is intended for internal Microsoft use as an accelerator for proofs of concept (POCs) and demo environments. It is not a production-ready offering. Use at your own discretion.