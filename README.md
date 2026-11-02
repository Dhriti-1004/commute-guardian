# 🧭 Commute Guardian

An autonomous multi-agent commute planning engine that dynamically chains calendar outings, predicts real-world activity commitments, and evaluates multi-modal transit decisions using real-time environmental friction and a local System 1 AI decision classifier.

---

## 📌 Problem Overview
Standard calendar and navigation platforms treat scheduled events as isolated, static data points. They fundamentally fail to:
1. **Chain multi-leg journeys dynamically:** Outings consist of sequential legs (e.g., *Base $\rightarrow$ Cinema $\rightarrow$ Restaurant $\rightarrow$ Retail*), where arrival and commitment times at earlier stops dictate subsequent departure windows.
2. **Account for contextual transit friction:** Static travel buffers fail under real-world conditions; departure times must adapt dynamically to live traffic delays, precipitation probabilities, and event-specific punctuality stakes.
3. **Execute low-latency decision reasoning:** Autoregressive LLMs introduce unacceptable latency, token costs, and non-deterministic hallucination risks when making strict operational decisions.

Commute Guardian resolves this by integrating deterministic geospatial routing, hyper-local weather risk analysis, RAG-driven behavioral rules, and a non-autoregressive **System 1 classifier (Laya / ModernBERT)** into an automated execution pipeline.

---

## 🏗️ Architecture & Pipeline

```text
               +--------------------------------------+
               |         Google Calendar API          |
               |        (Live OAuth 2.0 Sync)         |
               +------------------+-------------------+
                                  |
                                  v
+----------------------------------------------------------------------------------+
|                         Dynamic Itinerary Chainer                                |
|  - Evaluates inter-event time gaps (<= 120m chain, 120-240m buffer, >240m reset) |
|  - Chains dynamic origin coordinates across continuous journey legs              |
+--------------+------------------+---------------------------+--------------------+
               |                  |                           |
               v                  v                           v
      +-----------------+ +-----------------+        +------------------+
      | Duration Engine | | TomTom Routing  |        | Open-Meteo Client|
      |  (ModernBERT)   | |  Multi-Modal    |        | Hyper-Local Risk |
      |  Interval Regr. | |(Walk/Bike/Cab)  |        |(Rain Prob / Temp)|
      +--------+--------+ +--------+--------+        +--------+---------+
               |                  |                           |
               +----------------\ | /-------------------------+
                                v v v
+-----------------------------------------------------------------------------+
|                Laya System 1 Joint Decision Engine (JEV)                    |
|  - State Ingestion: Environmental Friction + Candidate Routes + RAG Rules   |
|  - Non-Autoregressive Classifier: Predicts Urgency Score & Transport Mode   |
|  - Dynamic Safety Buffer Allocation (10m / 20m / 45m thresholds)            |
+-------------------------------------+---------------------------------------+
                                      |
                                      v
                      +-------------------------------+
                      |   Streamlit Executive Board   |
                      |    (Interactive Dashboard)    |
                      +-------------------------------+
```

### 1. System 1 AI Decision Engine (`jev_engine.py`)
* Replaces brittle if-else trees with **`convaiinnovations/laya`**, an encoder-based model derived from ModernBERT.
* Evaluates complex multi-attribute states (scheduled start, destination profile, transit durations across modes, rain risk, and personal constraints) in a single forward pass over typed logits.
* Concurrently scores punctuality stakes (`urgency`) and selects the optimal transport mode (`walk`, `bike`, `cab`) based on calibrated physical thresholds and weather penalties.

### 2. Contextual Preference Retrieval via RAG (`preference_retriever.py`)
* Embeds user-specific constraints (e.g., maximum walking tolerance under heat, rain aversion thresholds) using `all-MiniLM-L6-v2` into a persistent **ChromaDB** vector store.
* Performs semantic search at runtime to retrieve and inject relevant behavioral guidelines directly into the decision engine's context state.

### 3. Probabilistic Duration Estimation (`duration_estimator.py`)
* Solves the static calendar limitation where users only enter start times without realistic end times.
* Employs anchored score regression across typical commitment scales to generate a 3-point duration estimation: minimum ($t_{min}$), expected ($t_{exp}$), and maximum ($t_{max}$) commitment windows.

### 4. Dynamic Multi-Leg Itinerary Chaining (`app.py`)
* Tracks previous arrival times and destination coordinates across scheduled entries.
* Automatically determines whether subsequent legs originate from the user's primary base or chain directly from the preceding venue based on temporal proximity.

---

## 🛠️ Tech Stack

| Domain | Technologies & Libraries |
| :--- | :--- |
| **Language & Core** | Python 3.11+, Pydantic v2 (Strict Schema Enforcement), SQLite |
| **AI / Machine Learning** | Laya (`convaiinnovations/laya`), ModernBERT, PyTorch, Hugging Face Hub |
| **Vector Search & RAG** | LangChain, `sentence-transformers` (`all-MiniLM-L6-v2`), ChromaDB |
| **APIs & Data Ingestion** | Google Calendar API (OAuth 2.0), TomTom Routing API, Open-Meteo Weather API |
| **Geospatial & Time** | `timezonefinder`, `geopy`, `httpx` |
| **Frontend UI** | Streamlit |

---

## 📂 Repository Structure

```text
commute-guardian/
|-- app.py                     # Streamlit frontend & main itinerary execution loop
|-- calendar_sync.py           # Google Calendar OAuth 2.0 flow & event ingestion
|-- duration_estimator.py      # Laya-based probabilistic activity duration estimator
|-- geocoder.py                # Geospatial location resolver with SQLite local caching
|-- jev_engine.py              # System 1 Joint Expected Value decision engine
|-- main.py                    # CLI entrypoint for testing multi-agent evaluations
|-- preference_retriever.py    # Local vector search & RAG pipeline (ChromaDB)
|-- preferences.md             # Baseline user behavioral rules & transit thresholds
|-- schemas.py                 # Pydantic data models for routes, events, and plans
|-- traffic_client.py          # TomTom Routing API client (multi-modal routing)
|-- weather_client.py          # Open-Meteo hyper-local weather ingestion
|-- requirements.txt           # Pinned environment dependencies
|-- .gitignore                 # Exclusion list for credentials, databases, and binaries
`-- README.md                  # Project documentation
```

---

## ⚙️ Getting Started

### 1. Prerequisites
* Python 3.11 or higher installed.
* A TomTom Developer API key ([TomTom Developer Portal](https://developer.tomtom.com/)).
* A Google Cloud project with the **Google Calendar API** enabled and an OAuth 2.0 Desktop Client created.

### 2. Clone and Install
```bash
git clone [https://github.com/Dhriti-1004/commute-guardian.git](https://github.com/Dhriti-1004/commute-guardian.git)
cd commute-guardian
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the root directory:
```ini
TOMTOM_API_KEY=your_tomtom_api_key_here
DEFAULT_ORIGIN_LAT=22.7770
DEFAULT_ORIGIN_LON=86.1441
```
Place your downloaded Google OAuth Desktop Client credentials file into the root directory and name it `credentials.json`.

### 4. Run Application
```bash
streamlit run app.py
```
* Authenticate via Google Calendar when prompted to sync live personal events, or switch to the **Demo Outing** option in the sidebar to test pipeline decisions across a multi-stop itinerary without live credentials.