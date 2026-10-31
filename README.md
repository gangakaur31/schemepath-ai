# SchemePathAI

![Python](https://img.shields.io/badge/Python-3.11+-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green) ![Gemini](https://img.shields.io/badge/Gemini-1.5_Flash-orange) ![Playwright](https://img.shields.io/badge/Playwright-Automation-purple) ![Streamlit](https://img.shields.io/badge/Streamlit-Frontend-red)

> **India's autonomous navigator for student government schemes.**
> One profile. 500+ schemes. Clear guidance.

---

## Problem Statement

India has **500+ central and state government schemes** for students — scholarships, education loans, hostel benefits, skill development, research fellowships, and more. Yet the vast majority go unutilised because:

- Schemes are **scattered across 20+ different portals** (NSP, Vidya Lakshmi, PMKVY, state portals)
- No single source tells a student **which schemes they qualify for** across all categories
- Application processes are on **non-intuitive legacy web apps** with no guidance
- Language barriers and missed deadlines further reduce uptake

**Target Audience:** Students aged 14–30 from EWS/SC/ST/OBC backgrounds, rural/semi-urban regions, pursuing any level of education.

---

## Solution

SchemePathAI is an **autonomous agentic system** that:
1. Takes a student's profile (category, income, education, state, interests)
2. **Discovers all applicable schemes** across 14 categories from live government sources
3. Uses **Gemini AI** to reason through eligibility and rank schemes
4. **Navigates government portals autonomously** using Playwright browser automation
5. Pre-fills application forms and returns step-by-step guidance

### Key Features
- **Universal Scheme Matcher** — covers 14 categories, not just scholarships
- **Browser Agent** — Playwright navigates real government portals
- **Document Checklist Generator** — exact documents needed per scheme
- **LangGraph Agent** — multi-step AI reasoning with error recovery
- **No Dummy Data** — all data from live official government sources

---

## Technical Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              STUDENT  (Streamlit Frontend :8501)            │
│     Profile Form → Chat → Scheme Cards → Auto-Apply        │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API
┌──────────────────────────▼──────────────────────────────────┐
│               FastAPI Backend (:8000)                       │
│                                                             │
│   POST /api/discover → LangGraph Agent Pipeline:           │
│                                                             │
│   parse_profile → fetch_schemes → embed_and_store          │
│        → check_eligibility → rank_and_generate             │
│                                                             │
│   ┌────────────────┐  ┌──────────────────────────────┐    │
│   │ MyScheme        │  │  ChromaDB RAG                 │    │
│   │ Scraper         │  │  (Google text-embedding-004)  │    │
│   │ (Playwright)    │  │                               │    │
│   └────────────────┘  └──────────────────────────────┘    │
│                                                             │
│   POST /api/apply → Browser Agent (Playwright):            │
│   Navigate Portal → Detect Form → Pre-fill → Screenshot   │
└─────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                 REAL DATA SOURCES                           │
│  myscheme.gov.in  •  scholarships.gov.in                   │
│  vidyalakshmi.co.in  •  pmkvyofficial.org                  │
│  pminternship.mca.gov.in  •  data.gov.in                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- Google Gemini API key (free at [aistudio.google.com](https://aistudio.google.com))

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd schemepath-ai

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 4. Set up environment
cp .env.example .env
# Open .env and set your GOOGLE_API_KEY

# 5. Start backend (Terminal 1)
cd backend
uvicorn main:app --reload --port 8000

# 6. Start frontend (Terminal 2)
cd frontend
streamlit run app.py

# OR: Start everything at once
python start.py
```

Open **http://localhost:8501** in your browser.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/discover` | Discover eligible schemes for a student profile |
| `POST` | `/api/apply` | Trigger browser agent to navigate a scheme portal |
| `GET` | `/api/schemes/{session_id}` | Retrieve previously discovered schemes |
| `GET` | `/health` | Backend health check |
| `GET` | `/docs` | Interactive API documentation (Swagger) |

---

## Scheme Categories Covered

| # | Category | Example Schemes |
|---|---|---|
| 1 | Scholarships | NSP Post-Matric, Merit-cum-Means, Minority Scholarship |
| 2 | Education Loans | Vidya Lakshmi, PM Vidya Laxmi |
| 3 | Hostel & Housing | Dr. Ambedkar Hostels, SC/ST Hostels |
| 4 | Fee Reimbursement | AP Jagananna Vidya Deevena, state waivers |
| 5 | Digital Access | Free laptop schemes, PM e-Vidya |
| 6 | Skill Development | PMKVY, DDU-GKY, NAPS |
| 7 | Research Fellowships | UGC-JRF, CSIR, DST INSPIRE, KVPY |
| 8 | Study Abroad | National Overseas Scholarship |
| 9 | Girl Child Schemes | PRAGATI, CBSE Single Girl, Sukanya Samriddhi |
| 10 | Differently Abled | AICTE Saksham Scholarship |
| 11 | Sports | TOPS Scheme, SAI Scholarships |
| 12 | Health Insurance | Ayushman Bharat student coverage |
| 13 | Book Grants | Free textbook state schemes |
| 14 | Internships | PM Internship Scheme |

---

## Real Data Sources (No Dummy Data)

| Source | URL | Usage |
|---|---|---|
| MyScheme Portal | myscheme.gov.in | Primary scheme aggregator — 1000+ schemes |
| National Scholarship Portal | scholarships.gov.in | Central scholarship schemes |
| Vidya Lakshmi | vidyalakshmi.co.in | Education loan schemes |
| PMKVY | pmkvyofficial.org | Skill development |
| PM Internship | pminternship.mca.gov.in | Internship programs |
| Data.gov.in | data.gov.in/api | Open government datasets |

---

## AI / Tech Stack

| Component | Technology |
|---|---|
| LLM | Google Gemini 1.5 Flash |
| Embeddings | Google text-embedding-004 |
| Agent Framework | LangGraph (state machine) |
| Vector DB | ChromaDB (persistent) |
| Browser Automation | Playwright (async) |
| Backend | FastAPI + uvicorn |
| Frontend | Streamlit |
| HTTP Client | httpx (async) + requests |

---

## Team

| Name | Role |
|---|---|
| Team Member 1 | Backend & Agent Engineering |
| Team Member 2 | Data Pipeline & RAG |
| Team Member 3 | Frontend & Browser Automation |

---

## License

MIT License — Built for the Gen AI Buildathon 2026.
