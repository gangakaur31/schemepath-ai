"""
scheme_agent.py — LangGraph state machine for AVSAR.

Orchestrates the full scheme discovery pipeline in five sequential nodes:
  1. parse_profile       — Validate and extract key attributes from StudentProfile
  2. fetch_schemes       — Scrape + load known schemes; combine & deduplicate
  3. embed_and_store     — Push raw schemes into ChromaDB; retrieve relevant ones
  4. check_eligibility   — Score each scheme with EligibilityChecker
  5. rank_and_generate   — Sort, filter, generate checklists, compute total benefit
"""

import logging
import os
import re
import time
import uuid
from typing import List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph
from langchain_core.messages import HumanMessage  # noqa: F401 – kept for LangGraph compat

from models.schemas import (
    SchemeCategory,
    SchemeDiscoveryRequest,
    SchemeDiscoveryResponse,
    SchemeResult,
    StudentProfile,
)
from services.rag_service import RAGService
from tools.eligibility_tool import EligibilityChecker
from tools.myscheme_scraper import MySchemeScaper, get_known_student_schemes

logger = logging.getLogger("schemepath.scheme_agent")

# ─── LangGraph state ──────────────────────────────────────────────────────────


class SchemeState(TypedDict):
    profile: dict           # StudentProfile serialised as dict
    raw_schemes: list       # list of raw scheme dicts from scraper / known list
    eligible_schemes: list  # list of SchemeResult dicts after eligibility check
    session_id: str
    error: Optional[str]
    log_messages: list
    auto_apply: bool


# ─── Node helpers ─────────────────────────────────────────────────────────────


def _log(state: SchemeState, msg: str) -> None:
    """Append a log message to state (mutates in-place)."""
    logger.info(msg)
    state["log_messages"].append(msg)


# ─── Node 1: parse_profile ────────────────────────────────────────────────────


def parse_profile(state: SchemeState) -> SchemeState:
    """
    Validate the incoming profile dict and log its key attributes.
    If validation fails the error is recorded but processing continues
    with whatever data is available.
    """
    try:
        raw = state["profile"]
        profile = StudentProfile(**raw)
        # Re-serialise to normalise enum values to their string representations
        state["profile"] = profile.model_dump(mode="json")
        _log(
            state,
            f"[parse_profile] Profile parsed — name={profile.name}, "
            f"state={profile.state}, category={profile.category.value}, "
            f"education={profile.education_level.value}, "
            f"income=₹{profile.annual_family_income:,}, "
            f"marks={profile.percentage_marks}%",
        )
    except Exception as exc:
        err = f"[parse_profile] Validation error: {exc}"
        logger.error(err)
        state["error"] = err
        state["log_messages"].append(err)
    return state


# ─── Node 2: fetch_schemes ────────────────────────────────────────────────────


def fetch_schemes(state: SchemeState) -> SchemeState:
    """
    Call MySchemeScaper and get_known_student_schemes; merge and deduplicate
    results by scheme name (case-insensitive).
    """
    import asyncio

    async def _fetch_async(profile):
        scraper = MySchemeScaper()
        scraped = await scraper.fetch_schemes_by_profile(profile)
        known = await get_known_student_schemes()
        return scraped, known

    try:
        profile_dict = state["profile"]
        profile = StudentProfile(**profile_dict)

        _log(state, "[fetch_schemes] Fetching schemes from MyScheme + known list…")
        try:
            loop = asyncio.new_event_loop()
            scraped, known = loop.run_until_complete(_fetch_async(profile))
            loop.close()
            _log(state, f"[fetch_schemes] Scraper returned {len(scraped)} | Known: {len(known)}")
        except Exception as e:
            logger.warning(f"Async fetch failed ({e}), using known schemes only.")
            loop2 = asyncio.new_event_loop()
            known = loop2.run_until_complete(get_known_student_schemes())
            loop2.close()
            scraped = []

        # Deduplicate by normalised name
        seen_names: set = set()
        combined: list = []
        for scheme in scraped + known:
            normalised = scheme.get("name", "").strip().lower()
            if normalised and normalised not in seen_names:
                seen_names.add(normalised)
                combined.append(scheme)

        state["raw_schemes"] = combined
        _log(state, f"[fetch_schemes] Combined unique schemes: {len(combined)}")
    except Exception as exc:
        err = f"[fetch_schemes] Error: {exc}"
        logger.exception(err)
        state["error"] = err
        state["log_messages"].append(err)
        if not state.get("raw_schemes"):
            try:
                loop3 = asyncio.new_event_loop()
                state["raw_schemes"] = loop3.run_until_complete(get_known_student_schemes())
                loop3.close()
            except Exception:
                state["raw_schemes"] = []
    return state


# ─── Node 3: embed_and_store ─────────────────────────────────────────────────


def embed_and_store(state: SchemeState) -> SchemeState:
    """
    Store raw scheme dicts in ChromaDB via RAGService, then perform a semantic
    search with profile-derived keywords to surface the most relevant schemes.
    The retrieved results replace raw_schemes so downstream nodes only process
    semantically relevant schemes.
    """
    import asyncio

    try:
        raw_schemes = state["raw_schemes"]
        if not raw_schemes:
            _log(state, "[embed_and_store] No raw schemes to embed — skipping.")
            return state

        profile = StudentProfile(**state["profile"])
        rag = RAGService()

        # Build a rich semantic query from the student profile
        interests_str = ", ".join(profile.interests) if profile.interests else "general"
        query = (
            f"{profile.education_level.value} student "
            f"{profile.category.value} category "
            f"{profile.gender.value} "
            f"from {profile.state} "
            f"income {profile.annual_family_income} "
            f"marks {profile.percentage_marks} percent "
            f"interests {interests_str} "
            f"scheme scholarship fellowship loan hostel"
        )

        # ChromaDB operations need to run in an event loop
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(rag.add_schemes(raw_schemes))
            _log(state, f"[embed_and_store] Upserted {len(raw_schemes)} schemes into ChromaDB.")

            retrieved = loop.run_until_complete(rag.search_schemes(query, n_results=50))
            _log(state, f"[embed_and_store] Semantic search returned {len(retrieved)} relevant schemes.")
        finally:
            loop.close()

        # Use retrieved results if non-empty, else keep the full raw list
        state["raw_schemes"] = retrieved if retrieved else raw_schemes
    except Exception as exc:
        err = f"[embed_and_store] RAG error: {exc}"
        logger.exception(err)
        state["error"] = err
        state["log_messages"].append(err)
        # Keep raw_schemes unchanged so eligibility check can still run
    return state


# ─── Node 4: check_eligibility ───────────────────────────────────────────────


def check_eligibility(state: SchemeState) -> SchemeState:
    """
    Run EligibilityChecker.check_batch() over all raw schemes and store the
    resulting SchemeResult dicts in state["eligible_schemes"].
    Falls back to rule-based scoring if Gemini is unavailable.
    """
    import asyncio

    try:
        raw_schemes = state["raw_schemes"]
        if not raw_schemes:
            _log(state, "[check_eligibility] No schemes to check — skipping.")
            state["eligible_schemes"] = []
            return state

        profile = StudentProfile(**state["profile"])
        api_key = os.environ.get("GOOGLE_API_KEY", "")

        if api_key:
            try:
                checker = EligibilityChecker(api_key=api_key)
                _log(state, f"[check_eligibility] Checking {len(raw_schemes)} schemes with Gemini…")
                loop = asyncio.new_event_loop()
                results: List[SchemeResult] = loop.run_until_complete(
                    checker.check_batch(profile, raw_schemes)
                )
                loop.close()
                state["eligible_schemes"] = [r.model_dump(mode="json") for r in results]
                _log(state, f"[check_eligibility] Gemini check complete — {len(results)} results.")
                return state
            except Exception as gemini_exc:
                logger.warning(f"Gemini eligibility check failed ({gemini_exc}), using rule-based fallback.")

        # ── Rule-based fallback (no Gemini needed) ────────────────────────────
        _log(state, "[check_eligibility] Using rule-based eligibility scoring.")
        results = _rule_based_eligibility(profile, raw_schemes)
        state["eligible_schemes"] = [r.model_dump(mode="json") for r in results]
        _log(state, f"[check_eligibility] Rule-based check done — {len(results)} results.")

    except Exception as exc:
        err = f"[check_eligibility] Error: {exc}"
        logger.exception(err)
        state["error"] = err
        state["log_messages"].append(err)
        state["eligible_schemes"] = []
    return state


def _rule_based_eligibility(profile: StudentProfile, schemes: list) -> List[SchemeResult]:
    """
    Strict, accurate rule-based eligibility evaluation.
    Enforces real hard disqualifications (caste, gender, state, income, disability, education level)
    so students only see schemes they genuinely qualify for.
    """
    results = []
    
    # Normalised student profile attributes
    cat = (profile.category.value if hasattr(profile.category, "value") else str(profile.category)).lower()
    gender = (profile.gender.value if hasattr(profile.gender, "value") else str(profile.gender)).lower()
    income = profile.annual_family_income
    marks = profile.percentage_marks
    edu = (profile.education_level.value if hasattr(profile.education_level, "value") else str(profile.education_level)).lower()
    state_name = (profile.state or "").strip().lower()
    has_disability = bool(profile.has_disability)
    user_interests = [i.lower() for i in (profile.interests or [])]

    # Northeast states list for Ishan Uday
    ne_states = {"assam", "arunachal pradesh", "manipur", "meghalaya", "mizoram", "nagaland", "sikkim", "tripura"}

    for raw in schemes:
        sid = (raw.get("scheme_id") or "").lower()
        name_lower = (raw.get("name") or "").lower()
        tags = [t.lower() for t in raw.get("tags", [])]
        eligibility_text = (raw.get("eligibility", "") + " " + raw.get("description", "")).lower()
        raw_category = (raw.get("category") or "").lower()

        score = 0.5
        match_reasons = []
        ineligibility_reasons = []
        is_disqualified = False

        # ── 1. HARD DISQUALIFICATION: Gender ──────────────────────────────────
        if "girl" in tags or "female" in tags or "women" in tags or "girl students" in name_lower or raw_category == "female":
            if gender == "male":
                is_disqualified = True
                ineligibility_reasons.append("Exclusive to girl/female applicants")
            else:
                score += 0.25
                match_reasons.append("Specially targeted for girl/female students")

        # ── 2. HARD DISQUALIFICATION: Disability ──────────────────────────────
        if "disabled" in tags or "differently-abled" in tags or "saksham" in sid or raw_category == "disabled":
            if not has_disability:
                is_disqualified = True
                ineligibility_reasons.append("Requires ≥40% certified disability")
            else:
                score += 0.35
                match_reasons.append("Exclusive scholarship for differently-abled students")

        # ── 3. HARD DISQUALIFICATION: Caste / Social Category ─────────────────
        # SC only schemes
        if "sc" in tags and "st" not in tags and "obc" not in tags and "all" not in tags and raw_category == "sc":
            if cat != "sc":
                is_disqualified = True
                ineligibility_reasons.append(f"Restricted to SC students (your profile: {cat.upper()})")
            else:
                score += 0.3
                match_reasons.append("Targeted financial aid for Scheduled Caste students")

        # SC/ST combined schemes (e.g. Ambedkar Hostels)
        elif raw_category == "sc_st" or ("sc" in tags and "st" in tags):
            if cat not in ["sc", "st"]:
                is_disqualified = True
                ineligibility_reasons.append(f"Restricted to SC/ST students (your profile: {cat.upper()})")
            else:
                score += 0.25
                match_reasons.append("Reserved welfare scheme for SC/ST students")

        # OBC only schemes
        elif "obc" in tags or raw_category == "obc" or "for obc" in name_lower:
            if cat != "obc":
                is_disqualified = True
                ineligibility_reasons.append(f"Restricted to OBC category (your profile: {cat.upper()})")
            else:
                score += 0.3
                match_reasons.append("Targeted scholarship for OBC students")

        # Minority only schemes
        elif "minority" in tags or raw_category == "minority" or "minority" in name_lower:
            if cat != "minority":
                is_disqualified = True
                ineligibility_reasons.append(f"Restricted to recognized minority communities (your profile: {cat.upper()})")
            else:
                score += 0.3
                match_reasons.append("Merit-cum-means assistance for minority communities")

        # ── 4. HARD DISQUALIFICATION: State / Regional Domicile ───────────────
        if "ishan-uday" in sid or "north east" in tags or "north east" in name_lower:
            if state_name not in ne_states and "north east" not in state_name:
                is_disqualified = True
                ineligibility_reasons.append(f"Requires domicile in North Eastern states (your state: {profile.state})")
            else:
                score += 0.3
                match_reasons.append(f"Dedicated North East development scholarship for {profile.state}")

        # ── 5. HARD DISQUALIFICATION: Strict Income Limits ───────────────────
        # OBC Post Matric: ≤ 1 Lakh
        if "obc-postmatric" in sid:
            if income > 100000:
                is_disqualified = True
                ineligibility_reasons.append(f"Annual family income exceeds ₹1,00,000 ceiling (your income: ₹{income:,})")

        # SC Post Matric / Minority: ≤ 2.5 Lakh
        elif "nsp-postmatric" in sid or "nsp-merit-cum-means" in sid:
            if income > 250000:
                is_disqualified = True
                ineligibility_reasons.append(f"Annual family income exceeds ₹2,50,000 ceiling (your income: ₹{income:,})")

        # Pragati / Saksham / NOS: ≤ 8 Lakh
        elif any(k in sid for k in ["pragati", "saksham", "overseas"]):
            if income > 800000:
                is_disqualified = True
                ineligibility_reasons.append(f"Annual family income exceeds ₹8,00,000 ceiling (your income: ₹{income:,})")

        # ── 6. HARD DISQUALIFICATION: Education Level & Age ───────────────────
        # UGC-JRF: strictly post-graduate / PhD
        if "ugc-jrf" in sid or "jrf" in tags:
            if edu not in ["postgraduate", "phd"]:
                is_disqualified = True
                ineligibility_reasons.append("UGC-JRF requires Master's (PG) completion or ongoing PhD")
            else:
                score += 0.25
                match_reasons.append("Qualifies for national research fellowship level")

        # National Overseas Scholarship: strictly Masters / PhD
        if "national-overseas" in sid or "overseas" in tags:
            if edu not in ["undergraduate", "postgraduate", "phd"]:
                is_disqualified = True
                ineligibility_reasons.append("Overseas scholarship requires Bachelor degree for PG/PhD abroad")
            else:
                score += 0.2
                match_reasons.append("Advanced degree study abroad opportunity")

        # PM Internship: youth age 21-24, typically diploma/graduates
        if "pm-internship" in sid:
            if profile.age < 21 or profile.age > 24:
                is_disqualified = True
                ineligibility_reasons.append(f"PM Internship requires age between 21 and 24 (your age: {profile.age})")
            else:
                score += 0.2
                match_reasons.append("Age-eligible for flagship PM 1-year corporate internship")

        # ── 7. Soft Merit & General Boosts ────────────────────────────────────
        if not is_disqualified:
            if marks >= 80:
                score += 0.15
                match_reasons.append(f"High academic merit ({marks}%) increases selection probability")
            elif marks >= 60:
                score += 0.05
                match_reasons.append(f"Academic score ({marks}%) satisfies minimum criteria")

            # Income consideration
            if income <= 150000:
                score += 0.1
                match_reasons.append("Prioritized for economically weaker students")

            # Interests
            for interest in user_interests:
                if interest in tags or interest in eligibility_text:
                    score += 0.1
                    match_reasons.append(f"Aligns with your interest in {interest}")

            # General universal scheme match reason
            if not match_reasons:
                match_reasons.append("Universal student welfare program open to your category and level")

        final_score = 0.0 if is_disqualified else min(1.0, max(0.1, round(score, 2)))

        # Scheme Category mapping
        scheme_cat = SchemeCategory.SCHOLARSHIP
        for tag in tags:
            if "loan" in tag:
                scheme_cat = SchemeCategory.EDUCATION_LOAN
            elif "hostel" in tag:
                scheme_cat = SchemeCategory.HOSTEL
            elif "skill" in tag or "vocational" in tag or "training" in tag:
                scheme_cat = SchemeCategory.SKILL_DEVELOPMENT
            elif "research" in tag or "fellowship" in tag:
                scheme_cat = SchemeCategory.RESEARCH_FELLOWSHIP
            elif "abroad" in tag or "overseas" in tag:
                scheme_cat = SchemeCategory.STUDY_ABROAD
            elif "girl" in tag or "women" in tag:
                scheme_cat = SchemeCategory.GIRL_CHILD
            elif "sport" in tag or "athlete" in tag:
                scheme_cat = SchemeCategory.SPORTS
            elif "internship" in tag:
                scheme_cat = SchemeCategory.INTERNSHIP
            elif "laptop" in tag or "digital" in tag:
                scheme_cat = SchemeCategory.DIGITAL_ACCESS
            elif "fee" in tag:
                scheme_cat = SchemeCategory.FEE_REIMBURSEMENT
            elif "disabled" in tag or "disability" in tag:
                scheme_cat = SchemeCategory.DIFFERENTLY_ABLED

        results.append(SchemeResult(
            scheme_id=raw.get("scheme_id", "") or str(uuid.uuid4()),
            name=raw.get("name", "Unknown Scheme"),
            category=scheme_cat,
            description=raw.get("description", ""),
            benefit_amount=raw.get("benefit_amount", ""),
            eligibility_summary=raw.get("eligibility", ""),
            application_portal=raw.get("ministry", "Government Portal"),
            portal_url=raw.get("portal_url", "https://www.myscheme.gov.in"),
            deadline=raw.get("deadline"),
            documents_required=raw.get("documents_required", []),
            eligibility_score=final_score,
            match_reasons=match_reasons,
            ineligibility_reasons=ineligibility_reasons,
            source=raw.get("source", "myscheme"),
        ))

    return results


# ─── Node 5: rank_and_generate ───────────────────────────────────────────────

# Minimum eligibility score for a scheme to be included in the final output
# We require at least 0.50 so disqualified (0.0) and poor matches are filtered out!
_MIN_SCORE = 0.50

# Documents every applicant almost certainly needs
_BASE_DOCUMENTS = [
    "Aadhaar card (original + photocopy)",
    "Bank passbook / cancelled cheque (account in student's name)",
    "Income certificate issued by competent authority",
    "Passport-size photographs (at least 4)",
]

# Category-specific additional documents
_CATEGORY_DOCS = {
    "sc": ["Caste / SC certificate issued by competent authority"],
    "st": ["Tribe certificate issued by competent authority"],
    "obc": ["OBC non-creamy layer certificate (current year)"],
    "ews": ["EWS income & asset certificate"],
    "minority": ["Minority community certificate / self-declaration"],
}

# Education-level-specific documents
_EDU_DOCS = {
    "class_10": ["Class 10 marksheet"],
    "class_12": ["Class 10 & 12 marksheets"],
    "diploma": ["Diploma enrollment certificate", "Previous semester marksheets"],
    "undergraduate": ["Class 12 marksheet", "College enrollment / bonafide certificate", "Previous semester marksheets"],
    "postgraduate": ["UG degree certificate", "Enrollment certificate", "Previous semester marksheets"],
    "phd": ["PG degree certificate", "Research enrollment letter from university"],
    "vocational": ["Vocational training enrollment certificate"],
}


def _build_document_checklist(profile: StudentProfile, scheme: dict) -> List[str]:
    """Generate a tailored document checklist for the given scheme and profile."""
    docs = list(_BASE_DOCUMENTS)

    # Category-specific docs
    category_val = profile.category.value if hasattr(profile.category, "value") else str(profile.category)
    docs.extend(_CATEGORY_DOCS.get(category_val, []))

    # Education-level-specific docs
    edu_val = profile.education_level.value if hasattr(profile.education_level, "value") else str(profile.education_level)
    docs.extend(_EDU_DOCS.get(edu_val, []))

    # Scheme-specific docs (from the raw scheme dict)
    scheme_docs = scheme.get("documents_required", [])
    for doc in scheme_docs:
        if doc and doc not in docs:
            docs.append(doc)

    # Disability docs if applicable
    if profile.has_disability:
        docs.append("Disability certificate from competent medical authority (with % indicated)")

    return docs


def _parse_benefit_amount(benefit_str: Optional[str]) -> float:
    """
    Attempt to extract a numeric rupee amount from a benefit string such as
    "₹12,000/year" or "Up to ₹1,50,000".  Returns 0.0 if unparseable.
    """
    if not benefit_str:
        return 0.0
    # Remove currency symbols and commas, then find the first number
    cleaned = benefit_str.replace("₹", "").replace(",", "").replace("Rs.", "").replace("Rs", "")
    match = re.search(r"[\d]+(?:\.\d+)?", cleaned)
    if match:
        try:
            return float(match.group())
        except ValueError:
            return 0.0
    return 0.0


def rank_and_generate(state: SchemeState) -> SchemeState:
    """
    Sort eligible schemes by eligibility_score descending, filter out those
    below the minimum threshold, enrich each with a document checklist, compute
    the total estimated benefit, and build top_recommendations.
    """
    try:
        eligible_dicts = state.get("eligible_schemes", [])
        profile = StudentProfile(**state["profile"])

        # Sort descending by score
        eligible_dicts.sort(key=lambda s: s.get("eligibility_score", 0.0), reverse=True)

        # Filter below minimum score
        filtered = [s for s in eligible_dicts if s.get("eligibility_score", 0.0) >= _MIN_SCORE]
        _log(
            state,
            f"[rank_and_generate] {len(filtered)}/{len(eligible_dicts)} schemes pass "
            f"the score threshold ({_MIN_SCORE}).",
        )

        # Enrich document checklists
        for scheme_dict in filtered:
            existing_docs = scheme_dict.get("documents_required", [])
            if not existing_docs:
                scheme_dict["documents_required"] = _build_document_checklist(profile, scheme_dict)

        # Compute total estimated benefit
        total_benefit = sum(_parse_benefit_amount(s.get("benefit_amount")) for s in filtered)

        # Update state with the enriched, ranked list
        state["eligible_schemes"] = filtered
        _log(
            state,
            f"[rank_and_generate] Final ranked list: {len(filtered)} schemes. "
            f"Estimated total benefit: ₹{total_benefit:,.0f}",
        )
    except Exception as exc:
        err = f"[rank_and_generate] Error during ranking: {exc}"
        logger.exception(err)
        state["error"] = err
        state["log_messages"].append(err)
    return state


# ─── Graph construction ───────────────────────────────────────────────────────


def _build_graph() -> StateGraph:
    """Construct and compile the LangGraph state machine."""
    graph = StateGraph(SchemeState)

    graph.add_node("parse_profile", parse_profile)
    graph.add_node("fetch_schemes", fetch_schemes)
    graph.add_node("embed_and_store", embed_and_store)
    graph.add_node("check_eligibility", check_eligibility)
    graph.add_node("rank_and_generate", rank_and_generate)

    graph.add_edge(START, "parse_profile")
    graph.add_edge("parse_profile", "fetch_schemes")
    graph.add_edge("fetch_schemes", "embed_and_store")
    graph.add_edge("embed_and_store", "check_eligibility")
    graph.add_edge("check_eligibility", "rank_and_generate")
    graph.add_edge("rank_and_generate", END)

    return graph.compile()


# ─── Public entry point ───────────────────────────────────────────────────────


async def run_scheme_agent(request: SchemeDiscoveryRequest) -> SchemeDiscoveryResponse:
    """
    Run the full scheme discovery pipeline and return results.

    This is the single entry point called by the FastAPI router.
    All graph nodes run synchronously inside LangGraph; this coroutine wraps
    them so FastAPI can await it without blocking the event loop long-term.
    """
    import asyncio

    start_time = time.perf_counter()
    session_id = str(uuid.uuid4())

    # Initialise state
    initial_state: SchemeState = {
        "profile": request.profile.model_dump(mode="json"),
        "raw_schemes": [],
        "eligible_schemes": [],
        "session_id": session_id,
        "error": None,
        "log_messages": [],
        "auto_apply": request.auto_apply,
    }

    logger.info("SchemeAgent starting — session_id=%s", session_id)

    try:
        app_graph = _build_graph()
        # LangGraph's .invoke() is synchronous; run it in a thread executor so
        # we don't block the FastAPI event loop.
        loop = asyncio.get_event_loop()
        final_state: SchemeState = await loop.run_in_executor(
            None, lambda: app_graph.invoke(initial_state)
        )
    except Exception as exc:
        logger.exception("Graph execution failed: %s", exc)
        # Return a minimal valid response rather than propagating the exception
        elapsed = time.perf_counter() - start_time
        return SchemeDiscoveryResponse(
            session_id=session_id,
            eligible_schemes=[],
            total_found=0,
            categories_covered=[],
            estimated_total_benefit="₹0",
            top_recommendations=[],
            next_steps=[
                "An internal error occurred while processing your profile.",
                "Please try again or contact support.",
            ],
            processing_time_seconds=round(elapsed, 2),
        )

    elapsed = time.perf_counter() - start_time

    # ── Build response from final state ──────────────────────────────────────

    eligible_dicts = final_state.get("eligible_schemes", [])

    # Reconstruct SchemeResult objects for the response
    eligible_results: List[SchemeResult] = []
    for scheme_dict in eligible_dicts:
        try:
            eligible_results.append(SchemeResult(**scheme_dict))
        except Exception as exc:
            logger.warning("Could not reconstruct SchemeResult from dict: %s", exc)

    # Apply categories filter if requested
    if request.categories_filter:
        allowed = set(request.categories_filter)
        eligible_results = [s for s in eligible_results if s.category in allowed]

    # Unique categories covered
    categories_covered = list({s.category.value for s in eligible_results})

    # Total estimated benefit
    total_benefit_float = sum(
        _parse_benefit_amount(s.benefit_amount) for s in eligible_results
    )
    if total_benefit_float > 0:
        estimated_total_benefit = f"₹{total_benefit_float:,.0f}"
    else:
        estimated_total_benefit = "Varies (see individual schemes)"

    # Top 5 recommendations (by score, already sorted)
    top_recommendations = [s.name for s in eligible_results[:5]]

    # Build actionable next steps
    next_steps: List[str] = []
    if eligible_results:
        next_steps.append(
            f"You are eligible for {len(eligible_results)} scheme(s). "
            "Review the top recommendations first."
        )
        portals = list({s.application_portal for s in eligible_results[:3]})
        for portal in portals:
            next_steps.append(f"Visit {portal} to start your application.")
        next_steps.append(
            "Gather your documents (Aadhaar, income certificate, marksheets, bank passbook) "
            "before applying."
        )
        if request.auto_apply:
            next_steps.append(
                "Auto-apply mode is enabled. Use POST /api/apply with a scheme_id to automate form filling."
            )
    else:
        next_steps.append(
            "No schemes matched your profile at the current threshold. "
            "Try updating your profile or check back during the next application cycle."
        )

    logger.info(
        "SchemeAgent complete — session=%s, schemes=%d, elapsed=%.2fs",
        session_id,
        len(eligible_results),
        elapsed,
    )

    return SchemeDiscoveryResponse(
        session_id=session_id,
        eligible_schemes=eligible_results,
        total_found=len(eligible_results),
        categories_covered=categories_covered,
        estimated_total_benefit=estimated_total_benefit,
        top_recommendations=top_recommendations,
        next_steps=next_steps,
        processing_time_seconds=round(elapsed, 2),
    )
