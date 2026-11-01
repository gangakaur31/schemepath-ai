"""
Pydantic schemas for AVSAR — the universal student government scheme navigator.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid


# ─── Enumerations ─────────────────────────────────────────────────────────────

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class Category(str, Enum):
    GENERAL = "general"
    SC = "sc"
    ST = "st"
    OBC = "obc"
    EWS = "ews"
    MINORITY = "minority"


class EducationLevel(str, Enum):
    CLASS_8 = "class_8"
    CLASS_10 = "class_10"
    CLASS_12 = "class_12"
    DIPLOMA = "diploma"
    UNDERGRADUATE = "undergraduate"
    POSTGRADUATE = "postgraduate"
    PHD = "phd"
    VOCATIONAL = "vocational"


class InstitutionType(str, Enum):
    GOVERNMENT = "government"
    PRIVATE = "private"
    AIDED = "aided"
    DEEMED = "deemed"


class SchemeCategory(str, Enum):
    SCHOLARSHIP = "scholarship"
    EDUCATION_LOAN = "education_loan"
    HOSTEL = "hostel"
    FEE_REIMBURSEMENT = "fee_reimbursement"
    DIGITAL_ACCESS = "digital_access"
    SKILL_DEVELOPMENT = "skill_development"
    RESEARCH_FELLOWSHIP = "research_fellowship"
    STUDY_ABROAD = "study_abroad"
    GIRL_CHILD = "girl_child"
    DIFFERENTLY_ABLED = "differently_abled"
    SPORTS = "sports"
    HEALTH_INSURANCE = "health_insurance"
    BOOK_GRANT = "book_grant"
    INTERNSHIP = "internship"


# ─── Student Profile ───────────────────────────────────────────────────────────

class StudentProfile(BaseModel):
    name: str = Field(..., description="Full name of the student")
    age: int = Field(..., ge=5, le=40)
    gender: Gender
    state: str = Field(..., description="State of domicile")
    district: Optional[str] = None

    category: Category
    annual_family_income: int = Field(..., ge=0, description="Annual family income in INR")

    education_level: EducationLevel
    course: str = Field(..., description="Name of current course/class")
    stream: Optional[str] = Field(None, description="Science / Arts / Commerce / Engineering / Medical / Law / Vocational")
    institution_name: Optional[str] = None
    institution_type: InstitutionType = InstitutionType.GOVERNMENT

    percentage_marks: float = Field(..., ge=0, le=100, description="Latest percentage or CGPA converted to %")

    has_disability: bool = False
    disability_type: Optional[str] = None
    disability_percentage: Optional[int] = None

    is_domicile: bool = True  # Is domicile of the selected state
    interests: List[str] = Field(default=[], description="e.g. sports, research, arts, coding")

    aadhar_available: bool = True
    bank_account_available: bool = True
    income_certificate_available: bool = True

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Priya Sharma",
                "age": 19,
                "gender": "female",
                "state": "Maharashtra",
                "district": "Pune",
                "category": "obc",
                "annual_family_income": 180000,
                "education_level": "undergraduate",
                "course": "B.Tech Computer Science",
                "stream": "Engineering",
                "institution_type": "government",
                "percentage_marks": 82.5,
                "has_disability": False,
                "interests": ["research", "coding"],
                "aadhar_available": True,
                "bank_account_available": True,
                "income_certificate_available": True,
            }
        }


# ─── Scheme Data ───────────────────────────────────────────────────────────────

class SchemeResult(BaseModel):
    scheme_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    category: SchemeCategory
    description: str
    benefit_amount: Optional[str] = None          # e.g. "₹12,000/year"
    benefit_type: Optional[str] = None            # "cash", "loan", "in-kind"
    eligibility_summary: str
    application_portal: str                        # Portal name
    portal_url: str
    deadline: Optional[str] = None
    documents_required: List[str] = []
    eligibility_score: float = Field(default=0.0, ge=0.0, le=1.0)
    match_reasons: List[str] = []
    ineligibility_reasons: List[str] = []
    source: str = "myscheme"                       # Data source
    last_updated: Optional[str] = None


# ─── API Request / Response ────────────────────────────────────────────────────

class SchemeDiscoveryRequest(BaseModel):
    profile: StudentProfile
    auto_apply: bool = False
    categories_filter: Optional[List[SchemeCategory]] = None  # Filter by category


class SchemeDiscoveryResponse(BaseModel):
    session_id: str
    eligible_schemes: List[SchemeResult]
    total_found: int
    categories_covered: List[str]
    estimated_total_benefit: str
    top_recommendations: List[str]           # scheme names
    next_steps: List[str]
    processing_time_seconds: float


class ApplicationRequest(BaseModel):
    session_id: str
    scheme_id: str
    profile: StudentProfile


class ApplicationStep(BaseModel):
    step_number: int
    description: str
    status: str  # "pending" | "completed" | "failed"
    screenshot_path: Optional[str] = None


class ApplicationResponse(BaseModel):
    success: bool
    tracking_id: Optional[str] = None
    confirmation_url: Optional[str] = None
    message: str
    steps_completed: List[ApplicationStep] = []
    error_details: Optional[str] = None


# ─── Agent State (LangGraph) ───────────────────────────────────────────────────

class AgentState(BaseModel):
    """Internal state passed between LangGraph nodes."""
    profile: Optional[StudentProfile] = None
    raw_schemes: List[Dict[str, Any]] = []
    eligible_schemes: List[SchemeResult] = []
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    current_step: str = "start"
    error: Optional[str] = None
    auto_apply: bool = False
    selected_scheme_id: Optional[str] = None
    application_result: Optional[ApplicationResponse] = None
    log_messages: List[str] = []
