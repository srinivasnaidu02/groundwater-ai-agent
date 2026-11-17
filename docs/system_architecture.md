# Groundwater AI Agent — System Architecture

## 1. Overview

**Groundwater AI Agent** is an end-to-end, enterprise-grade Natural Language to Database Query Agent built on top of official groundwater resource assessment data from the **Central Ground Water Board (CGWB)**, Ministry of Jal Shakti, Government of India, and the **IN-GRES** (India-Groundwater Resource Estimation System) platform developed in collaboration with IIT Hyderabad.

The primary mission is to convert natural language hydrogeological queries into deterministic, verified database operations without allowing LLMs to hallucinate numerical values.

```
                      +-----------------------------------+
                      |          USER INTERFACE           |
                      |   React 19 + Vite + Tailwind CSS  |
                      |   Recharts Analytics Dashboard    |
                      +-----------------+-----------------+
                                        |  HTTP REST
                                        v
                      +-----------------------------------+
                      |          FASTAPI BACKEND          |
                      |       (Uvicorn ASGI Server)       |
                      +-----------------+-----------------+
                                        |
                 +----------------------+-----------------------+
                 |                                              |
                 v                                              v
+-----------------------------------+          +-----------------------------------+
|         NLP PARSER ENGINE         |          |        METADATA & ANALYTICS       |
| - Intent Classifier (Rule-based)  |          | - National Aggregations           |
| - Entity Extractor (Geography/Yr) |          | - Category Distributions          |
| - Parameter & Aggregation Parser  |          | - Health & Status Endpoints       |
+-----------------+-----------------+          +-----------------+-----------------+
                  |                                              |
                  v                                              |
+-----------------------------------+                            |
|           QUERY PLANNER           |                            |
| - Intent-to-Function Mapping      |                            |
| - Parameter Validation Guardrails |                            |
| - Trace Logging (10 Steps)        |                            |
+-----------------+-----------------+                            |
                  |                                              |
                  v                                              |
+-----------------------------------+                            |
|     DATABASE FUNCTION REGISTRY    |                            |
|   (Predefined Parameterized ORM)  |                            |
|   Strictly No Arbitrary SQL       |                            |
+-----------------+-----------------+                            |
                  |                                              |
                  v                                              |
+-----------------------------------+                            |
|          SQLITE DATABASE          |<---------------------------+
| - CGWB 2022 Assessment Data       |
| - States & Districts Entities     |
| - Query Logs & Benchmark Audits   |
+-----------------+-----------------+
                  |
                  v
+-----------------------------------+
|     FACTUAL ANSWER GENERATOR      |
| - Grounded Natural Language Text  |
| - Precise Units (Ham / %)         |
| - Provenance Attribution          |
+-----------------------------------+
```

---

## 2. Component Breakdown

### 2.1 Frontend (`/frontend`)
- **Framework:** React 19 + Vite
- **Styling:** Tailwind CSS v4
- **Charting:** Recharts
- **Icons:** Lucide React
- **Routing:** React Router v7
- **Key Modules:**
  1. `ChatPage.jsx`: Natural language interaction, query chips, real-time 10-step trace inspection.
  2. `AnalyticsDashboard.jsx`: State comparisons, category distributions, district breakdowns.
  3. `SupportedQueriesPage.jsx`: Interactive catalog of all 14 registered database functions.
  4. `EvaluationPage.jsx`: Live benchmark metrics, filterable test runs, response latency stats.
  5. `DataSourcesPage.jsx`: Data provenance, official CGWB metadata, ingestion pipeline guides.

### 2.2 FastAPI Backend (`/backend/app`)
- **API Server:** FastAPI running on Uvicorn.
- **REST Endpoints:**
  - `POST /api/query`: Primary NL query parsing, function dispatch, execution, and trace generation.
  - `POST /api/query/structured`: Programmatic structured query execution.
  - `GET /api/health`: System health, record count, and connected assessment years.
  - `GET /api/metadata`: Application metadata, totals, and provenance details.
  - `GET /api/states`: List of available states and union territories.
  - `GET /api/districts/{state}`: Districts for a given state.
  - `GET /api/assessment-years`: Available assessment years (`2022`).
  - `GET /api/functions`: Complete registry metadata for supported functions.
  - `GET /api/query-history`: Audit log of executed queries.
  - `GET /api/evaluation/summary`: Benchmark KPI metrics.
  - `GET /api/evaluation/details`: Detailed test case execution log.
  - `GET /api/sources`: Connected source dataset metadata.
  - `GET /api/analytics/state-comparison`: State-level recharge and extraction aggregations.
  - `GET /api/analytics/category-distribution`: Safe, Semi-Critical, Critical, Over-Exploited breakdown.
  - `GET /api/analytics/district-data/{state}`: Granular district figures for charts.

### 2.3 NLP Engine (`/backend/app/nlp`)
- **Deterministic Intent Classification (`intent_classifier.py`):**
  - Priority-ordered regular expressions targeting specific domain intents.
  - Ambiguity detection: Questions mentioning "groundwater" without an operational parameter prompt the user for clarification rather than making assumptions.
- **Entity Extractor (`entity_extractor.py`):**
  - Robust dictionary of all 28 States & 8 UTs + state acronyms (UP, MP, WB, AP, HP, J&K).
  - Reverse mapping from district to state (e.g. "Patna" automatically infers "Bihar").
  - Assessment year extractor (`\b20\d{2}\b`).
  - Groundwater parameter extractor (`recharge`, `extraction`, `extractable`, `stage`, `category`, `level`).

### 2.4 Query Planner & Agent Executor (`/backend/app/agent`)
- Maps classified intents to the strictly registered database functions.
- Validates all required parameters.
- Records a 10-step execution trace with microsecond-level step durations.
- Invokes factual answer formatting that quotes numbers exclusively from database records.

### 2.5 Database Function Registry (`/backend/app/database`)
- Predefined repository functions (`get_groundwater_recharge`, `get_groundwater_extraction`, `get_stage_of_extraction`, `get_assessment_category`, `get_overexploited_units`, `compare_locations`, etc.).
- Fully parameterized SQLAlchemy queries protecting against SQL injection.
- Zero raw SQL generated by AI models.

