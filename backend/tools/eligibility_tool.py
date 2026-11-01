"""
Eligibility checker — uses Gemini to reason over student profile vs scheme criteria.
Returns eligibility score, match reasons, and ineligibility reasons.
"""

import json
import logging
from typing import List, Dict, Tuple
import google.generativeai as genai
from models.schemas import StudentProfile, SchemeResult, SchemeCategory

logger = logging.getLogger(__name__)


class EligibilityChecker:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")
    
    async def check_batch(
        self, profile: StudentProfile, schemes: List[Dict]
    ) -> List[SchemeResult]:
        """
        Check eligibility for a batch of schemes against a student profile.
        Returns list of SchemeResult with eligibility_score and reasons.
        """
        results = []
        
        # Build profile summary for prompt
        profile_summary = self._profile_to_text(profile)
        
        # Process in batches of 5 to avoid token limits
        batch_size = 5
        for i in range(0, len(schemes), batch_size):
            batch = schemes[i:i + batch_size]
            batch_results = await self._check_batch_with_gemini(profile_summary, profile, batch)
            results.extend(batch_results)
        
        return results
    
    async def _check_batch_with_gemini(
        self, profile_summary: str, profile: StudentProfile, schemes: List[Dict]
    ) -> List[SchemeResult]:
        """Use Gemini to evaluate eligibility for a batch of schemes."""
        
        schemes_text = json.dumps([
            {
                "id": i,
                "name": s.get("name", ""),
                "description": s.get("description", ""),
                "eligibility": s.get("eligibility", ""),
                "category_tag": s.get("tags", []),
                "state": s.get("state", "Central"),
                "gender_restriction": s.get("gender", "all"),
            }
            for i, s in enumerate(schemes)
        ], indent=2)
        
        prompt = f"""You are a government scheme eligibility expert. 
        
Analyze this student's profile and determine eligibility for each scheme.

STUDENT PROFILE:
{profile_summary}

SCHEMES TO EVALUATE:
{schemes_text}

For each scheme, return a JSON array with objects containing:
- "scheme_index": integer (0-based index)
- "eligible": boolean (true if student clearly qualifies or likely qualifies)
- "eligibility_score": float 0.0-1.0 (1.0 = fully eligible, 0.0 = clearly ineligible)
- "match_reasons": list of strings (why this student qualifies)
- "ineligibility_reasons": list of strings (barriers to eligibility, if any)
- "category": one of: scholarship, education_loan, hostel, fee_reimbursement, digital_access, skill_development, research_fellowship, study_abroad, girl_child, differently_abled, sports, health_insurance, book_grant, internship

Rules:
- Be generous but accurate. If income/category/education matches, mark eligible.
- If a scheme says "female only" and student is male, mark ineligible.
- Central schemes apply to all states unless specified otherwise.
- If eligibility info is missing, give score 0.5 and note "eligibility details not fully available".
- Return ONLY the JSON array, no explanation.

Return format: [{{"scheme_index": 0, "eligible": true, "eligibility_score": 0.9, "match_reasons": ["..."], "ineligibility_reasons": [], "category": "scholarship"}}, ...]"""

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            # Extract JSON from response
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            evaluations = json.loads(text)
            
        except Exception as e:
            logger.error(f"Gemini eligibility check failed: {e}")
            raise e
        
        # Build SchemeResult objects
        results = []
        for eval_item in evaluations:
            idx = eval_item.get("scheme_index", 0)
            if idx >= len(schemes):
                continue
            
            raw = schemes[idx]
            
            # Map category string to enum
            cat_str = eval_item.get("category", "scholarship")
            try:
                cat = SchemeCategory(cat_str)
            except ValueError:
                cat = SchemeCategory.SCHOLARSHIP
            
            result = SchemeResult(
                scheme_id=raw.get("scheme_id", f"scheme_{idx}"),
                name=raw.get("name", "Unknown Scheme"),
                category=cat,
                description=raw.get("description", ""),
                benefit_amount=raw.get("benefit_amount", ""),
                eligibility_summary=raw.get("eligibility", ""),
                application_portal=raw.get("ministry", "Government Portal"),
                portal_url=raw.get("portal_url", "https://www.myscheme.gov.in"),
                deadline=raw.get("deadline"),
                documents_required=raw.get("documents_required", []),
                eligibility_score=float(eval_item.get("eligibility_score", 0.5)),
                match_reasons=eval_item.get("match_reasons", []),
                ineligibility_reasons=eval_item.get("ineligibility_reasons", []),
                source=raw.get("source", "myscheme"),
            )
            results.append(result)
        
        return results
    
    def _profile_to_text(self, profile: StudentProfile) -> str:
        """Convert student profile to readable text for prompting."""
        return f"""
Name: {profile.name}
Age: {profile.age} years
Gender: {profile.gender.value}
State: {profile.state}
Category: {profile.category.value.upper()}
Annual Family Income: ₹{profile.annual_family_income:,}
Education Level: {profile.education_level.value.replace("_", " ").title()}
Course: {profile.course}
Stream: {profile.stream or "Not specified"}
Institution Type: {profile.institution_type.value.title()}
Marks/Percentage: {profile.percentage_marks}%
Disability: {"Yes - " + (profile.disability_type or "type not specified") if profile.has_disability else "No"}
Interests: {", ".join(profile.interests) if profile.interests else "None specified"}
Aadhar Available: {"Yes" if profile.aadhar_available else "No"}
Bank Account: {"Yes" if profile.bank_account_available else "No"}
Income Certificate: {"Yes" if profile.income_certificate_available else "No"}
""".strip()
