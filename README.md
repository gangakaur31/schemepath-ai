# AVSAR

![Python](https://img.shields.io/badge/Python-3.11+-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green) ![Gemini](https://img.shields.io/badge/Gemini-1.5_Flash-orange) ![Playwright](https://img.shields.io/badge/Playwright-Automation-purple) ![Streamlit](https://img.shields.io/badge/Streamlit-Frontend-red)

> **India's first AI-powered autonomous navigator for student government schemes.**
> One profile. 500+ schemes. Zero confusion.

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

**AVSAR** is an autonomous AI system that:
1. Takes a student's profile (category, income, education, state, interests)
2. **Discovers all applicable schemes** across 14 categories from live government sources
3. Uses **Gemini AI** to reason through eligibility and rank schemes by benefit amount
4. Generates a **personalised, portal-specific application guide** with exact steps
5. Tracks which schemes the student has applied to

### Key Features

| Feature | Description |
|---|---|
| 🔍 **Universal Scheme Matcher** | Covers 14 categories — scholarships, loans, internships, skill development, research fellowships and more |
| 📋 **Smart Application Guide** | Portal-specific step-by-step instructions, documents checklist, pro tips — different for every scheme |
| 🎙️ **Voice Summary** | Reads out scheme details using text-to-speech |
| ✅ **Mark as Applied** | Track which schemes you've applied to with persistent local storage |
| 📊 **My Applications Dashboard** | See total, submitted, under review, and approved application counts |
| 🤖 **LangGraph AI Agent** | Multi-step reasoning pipeline with rule-based fallback |
| 🚫 **No Dummy Data** | All 15 schemes from live official government sources only |

---

## Technical Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              STUDENT  (Streamlit Frontend :8501)            │
│   Profile Form → Scheme Cards → Application Guide          │
│   Mark as Applied → My Applications Dashboard              │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API
┌──────────────────────────▼──────────────────────────────────┐
│               FastAPI Backend (:8000)                       │
│                                                             │
│   POST /api/discover → LangGraph Agent Pipeline:           │
│   parse_profile → fetch_schemes → embed_and_store          │
│        → check_eligibility → rank_and_generate             │
│                                                             │
│   POST /api/guide → ApplicationGuideGenerator:             │
│   Portal-specific steps + docs checklist + pro tips        │
│                                                             │
│   ┌────────────────┐  ┌──────────────────────────────┐    │
│   │ MyScheme        │  │  ChromaDB RAG                 │    │
│   │ Scraper         │  │  (Semantic Search)            │    │
│   └────────────────┘  └──────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                 REAL DATA SOURCES                           │
│  myscheme.gov.in  •  scholarships.gov.in                   │
│  vidyalakshmi.co.in  •  pmkvyproject.org                   │
│  pminternship.mca.gov.in  •  online-inspire.gov.in         │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites
- Python 3.9+
- Google Gemini API key (free at [aistudio.google.com](https://aistudio.google.com))

```bash
# 1. Clone the repo
git clone https://github.com/gangakaur31/schemepath-ai.git
cd schemepath-ai

# 2. Install dependencies
pip3 install -r requirements.txt
python3 -m playwright install chromium

# 3. Set up environment
cp .env.example .env
# Open .env and set your GOOGLE_API_KEY

# 4. Start backend (Terminal 1)
cd backend
PYTHONPATH=. python3 -m uvicorn main:app --reload --port 8000

# 5. Start frontend (Terminal 2)
cd frontend
python3 -m streamlit run app.py
```

Open **http://localhost:8501** in your browser.

> **Note:** Always start the backend first, then the frontend.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/discover` | Discover eligible schemes for a student profile |
| `POST` | `/api/guide` | Generate personalised application guide for a scheme |
| `GET` | `/health` | Backend health check |
| `GET` | `/docs` | Interactive API documentation (Swagger) |

---

## Scheme Categories Covered

| # | Category | Example Schemes |
|---|---|---|
| 1 | Scholarships | NSP Post-Matric OBC/SC, Minority Merit-cum-Means |
| 2 | Education Loans | Vidya Lakshmi (apply to multiple banks at once) |
| 3 | Hostel & Housing | Dr. Ambedkar Hostels, SC/ST Hostels |
| 4 | Skill Development | PMKVY, DDU-GKY, NAPS |
| 5 | Research Fellowships | UGC-JRF, DST INSPIRE-SHE (formerly KVPY) |
| 6 | Study Abroad | National Overseas Scholarship (NOS) |
| 7 | Girl Child Schemes | PRAGATI (AICTE), CBSE Single Girl Child |
| 8 | Differently Abled | AICTE Saksham Scholarship |
| 9 | Sports | TOPS Scheme, SAI Scholarships |
| 10 | Internships | PM Internship Scheme (₹5,000/month stipend) |
| 11 | Book Grants | Free textbook state schemes |
| 12 | Digital Access | PM e-Vidya, free laptop schemes |
| 13 | Health Insurance | Ayushman Bharat student coverage |
| 14 | Fee Reimbursement | State-level fee waiver schemes |

---

## Real Data Sources (No Dummy Data)

| Source | URL | Usage |
|---|---|---|
| MyScheme Portal | myscheme.gov.in | Primary scheme aggregator |
| National Scholarship Portal | scholarships.gov.in | Central + state scholarships |
| Vidya Lakshmi | vidyalakshmi.co.in | Education loan schemes |
| PMKVY | pmkvyproject.org | Skill development |
| PM Internship | pminternship.mca.gov.in | Internship programmes |
| DST INSPIRE | online-inspire.gov.in | Science research fellowships |
| NOS | nosmsje.gov.in | Overseas scholarship for SC students |

---

## AI / Tech Stack

| Component | Technology |
|---|---|
| LLM | Google Gemini 1.5 Flash |
| Agent Framework | LangGraph (state machine pipeline) |
| Vector DB | ChromaDB (semantic search) |
| Voice Summary | gTTS (Google Text-to-Speech) |
| Backend | FastAPI + Uvicorn |
| Frontend | Streamlit |
| HTTP Client | httpx (async) + requests |

---

## Team

| Name | Role |
|---|---|
| Ganga Kaur | Backend, AI Agent & Guide Generator |
| Shambhavi Verma | Frontend UI & Voice Summary Feature |
| Ishita Jain | Mark as Applied & My Applications Feature |

---

## License

MIT License — Built for the Gen AI Buildathon 2026.
