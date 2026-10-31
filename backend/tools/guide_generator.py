"""
Application Guide Generator — uses Gemini to produce a personalized,
step-by-step application guide for a specific scheme and student profile.
"""

import os
import logging
import google.generativeai as genai
from models.schemas import StudentProfile, SchemeResult

logger = logging.getLogger(__name__)


class ApplicationGuideGenerator:
    def __init__(self):
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
            self.available = True
        else:
            self.available = False

    def generate(self, profile: StudentProfile, scheme: SchemeResult) -> dict:
        """
        Generate a personalized application guide for a student + scheme combo.
        Returns a dict with steps, pre-filled values, document checklist, tips.
        """
        if self.available:
            try:
                return self._generate_with_gemini(profile, scheme)
            except Exception as e:
                logger.warning(f"Gemini guide generation failed: {e}. Using rule-based.")

        return self._generate_rule_based(profile, scheme)

    def _generate_with_gemini(self, profile: StudentProfile, scheme: SchemeResult) -> dict:
        prompt = f"""You are an expert in Indian government scholarship applications.

Generate a detailed, personalized application guide for this student to apply for this scheme.

STUDENT PROFILE:
- Name: {profile.name}
- Age: {profile.age}, Gender: {profile.gender.value}
- State: {profile.state}
- Category: {profile.category.value.upper()}
- Annual Family Income: ₹{profile.annual_family_income:,}
- Education: {profile.education_level.value} — {profile.course}
- Marks: {profile.percentage_marks}%
- Has Disability: {"Yes" if profile.has_disability else "No"}

SCHEME:
- Name: {scheme.name}
- Portal: {scheme.portal_url}
- Benefit: {scheme.benefit_amount or "As per scheme"}
- Eligibility: {scheme.eligibility_summary}
- Documents Required: {", ".join(scheme.documents_required) if scheme.documents_required else "Standard documents"}

Generate a JSON response with exactly this structure:
{{
  "pre_filled_values": {{
    "Full Name": "{profile.name}",
    "State": "{profile.state}",
    "Category": "{profile.category.value.upper()}",
    "Annual Family Income": "₹{profile.annual_family_income:,}",
    "Course": "{profile.course}",
    "Percentage": "{profile.percentage_marks}%",
    "Gender": "{profile.gender.value.title()}"
  }},
  "steps": [
    "Step 1: ...",
    "Step 2: ...",
    "Step 3: ..."
  ],
  "documents_checklist": [
    {{"doc": "Aadhar Card", "note": "Original + photocopy", "ready": true}},
    {{"doc": "OBC Certificate", "note": "Must be current year non-creamy layer", "ready": true}}
  ],
  "pro_tips": [
    "Tip 1...",
    "Tip 2..."
  ],
  "deadline_note": "Apply before deadline — check portal for current dates",
  "estimated_time": "45 minutes"
}}

Make steps very specific to this scheme's portal. Include exact menu items to click.
Return ONLY valid JSON."""

        response = self.model.generate_content(prompt)
        text = response.text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        import json
        return json.loads(text)

    def _generate_rule_based(self, profile: StudentProfile, scheme: SchemeResult) -> dict:
        """Portal-specific guides hardcoded per government portal."""
        portal = scheme.portal_url
        name = profile.name
        state = profile.state
        category = profile.category.value.upper()
        income = f"₹{profile.annual_family_income:,}"
        course = profile.course
        marks = f"{profile.percentage_marks}%"
        edu = profile.education_level.value.replace("_", " ").title()

        # ── NSP — National Scholarship Portal ────────────────────────────────
        if "scholarships.gov.in" in portal:
            # Determine which specific NSP scholarship type to select
            scheme_name_lower = scheme.name.lower()
            if "minority" in scheme_name_lower or "merit-cum-means" in scheme_name_lower:
                scholarship_type = "Central Schemes → Minority Affairs → Merit-cum-Means"
                extra_doc_step = f"Upload Minority community certificate (issued by gazetted officer)"
                category_note = "Select 'Minority' as community — NOT general category"
            elif "obc" in scheme_name_lower:
                scholarship_type = "Central Schemes → Social Justice → OBC Post Matric"
                extra_doc_step = "Upload non-creamy layer OBC certificate (current year)"
                category_note = f"Select 'OBC' category — income limit is ₹1 lakh/year for OBC"
            elif "ishan" in scheme_name_lower or "north east" in scheme_name_lower:
                scholarship_type = "Central Schemes → UGC → Ishan Uday"
                extra_doc_step = f"Upload NE state domicile certificate for {state}"
                category_note = "Must be domiciled in a North East state"
            elif "sc" in scheme_name_lower or "scheduled caste" in scheme_name_lower:
                scholarship_type = "Central Schemes → Social Justice → SC Post Matric"
                extra_doc_step = "Upload SC caste certificate (original) — must be from competent authority"
                category_note = f"Income limit is ₹2.5 lakh/year — your income {income} should be within limit"
            else:
                scholarship_type = "Central Schemes (browse list and select your scheme)"
                extra_doc_step = f"Upload {category} category certificate as required"
                category_note = f"Select your category: {category}"

            steps = [
                "Navigate to scholarships.gov.in",
                "Click 'Applicant Corner' → 'New Registration' (first-time applicants)",
                f"Select Academic Year → State: {state} → Scholarship Type: {scholarship_type}",
                "Enter full name, DOB, mobile number → verify with OTP",
                "Enter 12-digit Aadhar number → Aadhar OTP verification",
                "Set login password → note down your Registration ID (e.g., NTR2024XXXXXXXXX)",
                "Login with Registration ID + password",
                "Click 'Application Form' → Part I (Institute details first)",
                f"Search and select your college → enter course: {course}",
                f"Enter marks: {marks} | Family income: {income}",
                extra_doc_step,
                "Upload each document: PDF only, size < 200KB (compress if needed)",
                "Fill Part II → review all details → click 'Final Submit'",
                "Print or save the Acknowledgment Number for tracking",
            ]
            tips = [
                category_note,
                f"Income {income} must exactly match your income certificate — no rounding",
                "Use Chrome or Firefox — NSP doesn't work properly on Safari/Edge",
                "After submission → track under 'Check Your Status' with Reg ID",
                "Institute must verify your application — follow up with your college",
                "Renewal students: click 'Renewal Application' → don't re-register",
            ]

        # ── Vidya Lakshmi — Education Loan Portal ────────────────────────────
        elif "vidyalakshmi" in portal:
            steps = [
                "Navigate to vidyalakshmi.co.in",
                "Click 'Student Registration' on the homepage",
                f"Fill: Name: {name} | Email | Mobile | DOB",
                "Verify your email ID (check inbox for OTP)",
                "Login with email and password",
                "Click 'Search & Apply for Loan Schemes'",
                f"Enter course: {course} | Institution name | Annual fee amount",
                "Browse banks offering education loans for your course",
                "Select 2-3 banks to apply simultaneously",
                f"Fill loan application form — income: {income}, course: {course}",
                "Upload admission letter, fee structure, income documents",
                "Submit applications → each bank sends separate response",
                "Track status under 'Your Applications' dashboard",
            ]
            tips = [
                "Apply to multiple banks at once — it's free and increases chances",
                "Vidya Lakshmi loans have 0 collateral up to ₹7.5 lakh",
                "Keep your admission confirmation letter ready before starting",
                f"Course: {course} qualifies for technical/professional loan rates",
                "Bank will contact you within 15 working days",
            ]

        # ── PM Internship Portal ──────────────────────────────────────────────
        elif "pminternship" in portal:
            steps = [
                "Navigate to pminternship.mca.gov.in",
                "Click 'Register as Candidate' button",
                "Enter mobile number → verify with OTP",
                f"Fill profile: Name: {name} | DOB | Gender | State: {state}",
                f"Select highest qualification: {edu}",
                "Upload your resume (PDF, max 2MB)",
                "Browse internship opportunities by sector, location, company",
                "Filter by your preferred industry or city",
                "Click 'Apply' on your preferred company listing",
                "Write a brief cover note explaining your interest",
                "Submit — you'll get a confirmation SMS/email",
                "Track application status in your dashboard",
            ]
            tips = [
                "₹5,000/month stipend + ₹6,000 one-time grant — apply now!",
                "Top 500 companies like Tata, Reliance, Infosys are listed",
                f"Your {marks} marks are a strong point — mention in cover note",
                "Apply to 5+ companies to increase your chances",
                "Internship is 1 year — plan your college schedule accordingly",
            ]

        # ── PMKVY — Skill Development ─────────────────────────────────────────
        elif "pmkvy" in portal or "skillindia" in portal:
            steps = [
                "Navigate to pmkvyproject.org",
                "Click 'Find a Training Center Near You'",
                f"Select State: {state} → Select your District",
                "Choose a skill sector (IT, Construction, Healthcare, etc.)",
                "Browse available courses and their duration",
                "Click on preferred course → note the Training Center details",
                "Visit the Training Center in person with your documents",
                "Register on-site: Aadhar + Photo + Bank passbook",
                "Training is FREE — no fees charged",
                "Attend all sessions → appear for assessment exam",
                "Pass assessment → get NSDC skill certificate",
                "Certificate helps in job placements through NSDC network",
            ]
            tips = [
                "Training is completely FREE — never pay any fee to anyone",
                "Certificate is nationally recognized by 40+ sector skill councils",
                "PMKVY provides ₹500 reward on successful certification",
                "Choose a course matching your career interest for better outcomes",
                "After certification, NSDC connects you with employers",
            ]

        # ── DST INSPIRE / KVPY ───────────────────────────────────────────────
        elif "inspire" in portal or "kvpy" in portal:
            steps = [
                "Navigate to online-inspire.gov.in",
                "Click 'New User Registration'",
                f"Fill personal details: Name: {name} | DOB | Gender | State: {state}",
                "Enter Class 12 board exam details and roll number",
                f"Enter marks/percentage: {marks}",
                "Upload Class 12 marksheet and admission proof",
                "Verify that you are in top 1% of your board exam",
                "Select your BSc/BS course and institution",
                "Submit application → DST will verify your rank",
                "Scholarship credited annually to your bank account",
            ]
            tips = [
                f"Your {marks} must be in top 1% of your board — verify this first",
                "INSPIRE-SHE replaced KVPY — apply only on online-inspire.gov.in",
                "Only natural sciences streams (Physics, Chemistry, Biology, Maths) eligible",
                "Scholarship continues for 5 years if you maintain 60% each year",
                "Summer research internship at IITs/IISc also available",
            ]

        # ── NSP Generic (NOS, Ishan Uday, other NSP schemes) ─────────────────
        elif "nosmsje.gov.in" in portal:
            steps = [
                "Navigate to nosmsje.gov.in",
                "Click 'New Applicant Registration'",
                f"Fill: Name: {name} | DOB | Category: {category} | State: {state}",
                "Upload all documents — must be self-attested",
                "Enter foreign university admission letter details",
                "Submit online application",
                "Application is reviewed by Ministry of Social Justice",
                "If selected, you receive full tuition + living allowance abroad",
            ]
            tips = [
                f"NOS is only for {category} students — your category qualifies",
                "Family income must be ≤ ₹8 lakh — ensure certificate is ready",
                "Only for Masters and PhD level — UG not eligible",
                "Apply well in advance — selection process takes 3-4 months",
            ]

        # ── Generic fallback for all other portals ───────────────────────────
        else:
            steps = [
                f"Navigate to {portal}",
                "Look for 'Register', 'Apply Now', or 'New Application' button",
                "Complete the registration with your mobile and email",
                f"Fill personal details: Name: {name} | State: {state} | Category: {category}",
                "Enter Aadhar number and verify with OTP",
                f"Fill academic details: Course: {course} | Marks: {marks}",
                f"Enter family income: {income}",
                "Upload all required documents in PDF format",
                "Review the application carefully before submitting",
                "Save your application/tracking number after submission",
            ]
            tips = [
                "Keep all documents ready as PDF before starting",
                f"Your category {category} and income {income} make you eligible",
                "Apply early — don't wait for the deadline",
                "Use a stable internet connection while uploading documents",
            ]

        # Build documents checklist from scheme data (with portal-specific notes)
        docs = []
        doc_notes = {
            "aadhar card": f"12-digit number needed for Aadhar OTP verification on portal",
            "income certificate": f"Must show exactly {income}/year — issued by tehsildar/SDM",
            "caste certificate": f"Must be {category} certificate — issued by competent authority, current year",
            "obc certificate": f"Must be non-creamy layer OBC — issued this financial year",
            "sc certificate": "Scheduled Caste certificate from state authority — original required",
            "st certificate": "Scheduled Tribe certificate from state authority — original required",
            "marksheet": f"Shows {marks} — get attested copy from institution",
            "previous year marksheet": f"Last year result showing {marks} — get attested copy",
            "bank passbook": "Student's own savings account, IFSC visible, no joint/parent accounts",
            "admission letter": "Official letter showing course name, duration, and fee structure",
            "institution verification": "To be filled and signed by your college/university principal",
            "passport": "Valid passport — apply if not available (takes 2-3 weeks)",
            "disability certificate": "≥40% disability — issued by Civil Surgeon or government hospital",
        }
        for d in (scheme.documents_required or []):
            note = doc_notes.get(d.lower(), "Self-attested photocopy + original for verification")
            docs.append({"doc": d, "note": note, "ready": True})
        if not docs:
            docs = [
                {"doc": "Aadhar Card", "note": "12-digit — needed for OTP verification", "ready": True},
                {"doc": f"{category} Certificate", "note": "Issued by competent authority, current year", "ready": True},
                {"doc": "Income Certificate", "note": f"Must show {income}/year — from tehsildar/SDM", "ready": True},
                {"doc": f"{edu} Marksheet", "note": f"Shows {marks} — get attested copy", "ready": True},
                {"doc": "Bank Passbook", "note": "Student's own account, IFSC code visible", "ready": True},
                {"doc": "Passport Size Photos", "note": "4 recent photos, white background, < 50KB each", "ready": True},
                {"doc": "Bonafide / Enrollment Certificate", "note": "From your college/institution principal", "ready": True},
            ]

        # Portal-specific estimated times
        if "scholarships.gov.in" in portal:
            estimated_time = "45–60 minutes (first-time registration takes longer)"
        elif "vidyalakshmi" in portal:
            estimated_time = "30–45 minutes (apply to 2–3 banks simultaneously)"
        elif "pminternship" in portal:
            estimated_time = "20–30 minutes (profile setup + application)"
        elif "pmkvy" in portal or "skillindia" in portal:
            estimated_time = "15–20 minutes (online + visit training center in person)"
        elif "inspire" in portal or "kvpy" in portal:
            estimated_time = "40–50 minutes (board rank verification required)"
        elif "nosmsje.gov.in" in portal:
            estimated_time = "60–90 minutes (overseas scholarship — many documents)"
        else:
            estimated_time = "30–45 minutes"

        return {
            "pre_filled_values": {
                "Full Name": name,
                "State": state,
                "Category": category,
                "Annual Family Income": income,
                "Course": course,
                "Percentage / Marks": marks,
                "Gender": profile.gender.value.title(),
                "Education Level": edu,
            },
            "steps": steps,
            "documents_checklist": docs,
            "pro_tips": tips,
            "deadline_note": scheme.deadline or "Check portal for current year deadline",
            "estimated_time": estimated_time,
        }
