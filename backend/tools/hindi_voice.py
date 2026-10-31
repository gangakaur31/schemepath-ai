"""
Hindi Voice Summary Generator
Generates a concise Hindi summary of a government scheme using Gemini,
then converts it to speech audio using gTTS.
Returns base64-encoded MP3 audio bytes.
"""

import os
import io
import base64
import logging

import google.generativeai as genai
from gtts import gTTS

logger = logging.getLogger(__name__)


class HindiVoiceGenerator:
    def __init__(self):
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        if api_key and api_key != "your_gemini_api_key_here" and len(api_key) > 15:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel("gemini-1.5-flash")
                self.gemini_available = True
            except Exception as e:
                logger.warning(f"Failed to configure Gemini: {e}")
                self.gemini_available = False
        else:
            self.gemini_available = False
            logger.info("GOOGLE_API_KEY not configured — using detailed rule-based Hindi summaries.")

    def generate_hindi_summary(self, scheme: dict) -> str:
        """
        Generates a comprehensive, logical Hindi plain-language summary of the scheme.
        Falls back to a structured, detailed rule-based summary if Gemini is unavailable.
        """
        if self.gemini_available:
            try:
                return self._gemini_hindi_summary(scheme)
            except Exception as exc:
                logger.warning("Gemini Hindi summary failed: %s. Using enhanced fallback.", exc)

        return self._fallback_hindi_summary(scheme)

    def _gemini_hindi_summary(self, scheme: dict) -> str:
        name        = scheme.get("name", "यह योजना")
        description = scheme.get("description", "")
        benefit     = scheme.get("benefit_amount", "")
        eligibility = scheme.get("eligibility_summary", "")
        category    = scheme.get("category", "scholarship")
        portal      = scheme.get("application_portal", "") or scheme.get("portal_url", "आधिकारिक पोर्टल")
        docs        = scheme.get("documents_required", [])

        prompt = f"""आप भारत सरकार के एक अनुभवी छात्र कल्याण और छात्रवृत्ति विशेषज्ञ हैं।
छात्रों के लिए निम्नलिखित सरकारी योजना का एक स्पष्ट, तार्किक और सटीक हिंदी ऑडियो सारांश (Audio Script) तैयार करें।

समय सीमा निर्देश:
- इस ऑडियो की बोलने की अवधि अधिकतम 1 मिनट होनी चाहिए (लगभग 80 से 100 शब्द, 3 से 4 वाक्य)।
- यह शुष्क तथ्यों को पढ़ने के बजाय सुनने में सहज, तार्किक और मार्गदर्शक होना चाहिए।

सारांश में ये 4 मुख्य बातें तार्किक क्रम में शामिल करें:
1. योजना का नाम व उद्देश्य (विद्यार्थियों की पढ़ाई में कैसे सहायक है)।
2. मिलने वाली वित्तीय सहायता ({benefit if benefit else "सरकारी नियमानुसार"})।
3. मुख्य पात्रता शर्तें ({eligibility})।
4. आवेदन पोर्टल ({portal}) तथा ज़रूरी सलाह (बैंक खाता आधार से लिंक/DBT सक्रिय होना और कॉलेज से सत्यापन)।

योजना की जानकारी:
- नाम: {name}
- श्रेणी: {category}
- मिलने वाला लाभ: {benefit if benefit else "सरकारी नियमानुसार"}
- पात्रता शर्तें: {eligibility}
- पोर्टल: {portal}

निर्देश:
- कुल लंबाई 80 से 100 शब्द (अधिकतम 1 मिनट का ऑडियो)।
- कोई बुलेट पॉइंट, नंबरिंग, हेडिंग या स्टार (*) न लगाएं। एक धाराप्रवाह पैराग्राफ में लिखें।
- केवल शुद्ध देवनागरी हिंदी में लिखें, अंग्रेज़ी अक्षरों का प्रयोग न करें।"""

        response = self.model.generate_content(prompt)
        text = response.text.strip()
        # Safety: strip any markdown artifacts
        for prefix in ["**", "##", "#", "- ", "* "]:
            if text.startswith(prefix):
                text = text[len(prefix):]
        return text.strip()

    def _fallback_hindi_summary(self, scheme: dict) -> str:
        name        = scheme.get("name", "यह योजना")
        benefit     = scheme.get("benefit_amount", "")
        cat         = scheme.get("category", "scholarship")
        eligibility = scheme.get("eligibility_summary", "")
        portal      = scheme.get("application_portal", "") or scheme.get("portal_url", "आधिकारिक पोर्टल")
        docs        = scheme.get("documents_required", [])

        cat_names = {
            "scholarship": "छात्रवृत्ति योजना",
            "education_loan": "सुलभ शिक्षा ऋण योजना",
            "hostel": "छात्रावास सहायता योजना",
            "fee_reimbursement": "शुल्क प्रतिपूर्ति योजना",
            "digital_access": "डिजिटल उपकरण सहायता योजना",
            "skill_development": "कौशल विकास योजना",
            "research_fellowship": "शोध फेलोशिप",
            "study_abroad": "विदेश अध्ययन छात्रवृत्ति",
            "girl_child": "बालिका शिक्षा प्रोत्साहन योजना",
            "differently_abled": "दिव्यांगजन शिक्षा सहायता",
            "sports": "खेल छात्रवृत्ति",
            "health_insurance": "स्वास्थ्य बीमा योजना",
            "book_grant": "पुस्तक अनुदान योजना",
            "internship": "इंटर्नशिप सहायता योजना",
        }
        cat_hindi = cat_names.get(cat, "कल्याणकारी योजना")

        # Clean up common English tokens for natural Hindi TTS pronunciation
        def _hindi_clean(text: str) -> str:
            if not text:
                return ""
            replacements = [
                ("/year", " प्रति वर्ष"),
                ("/month", " प्रति माह"),
                ("per year", " प्रति वर्ष"),
                ("per month", " प्रति माह"),
                ("contingency", "अतिरिक्त भत्ता"),
                ("LPA", " लाख रुपये प्रति वर्ष"),
                ("lpa", " लाख रुपये प्रति वर्ष"),
                ("<= 8", "अधिकतम आठ"),
                ("<=8", "अधिकतम आठ"),
                ("<= 2.5", "अधिकतम ढाई"),
                ("<= 1.5", "अधिकतम डेढ़"),
                ("<= 2", "अधिकतम दो"),
                ("<= 5", "अधिकतम पांच"),
                ("1st year", "प्रथम वर्ष"),
                ("2nd year", "द्वितीय वर्ष"),
                ("max 2 girls per family", "प्रति परिवार अधिकतम दो बालिकाओं को"),
                ("degree/diploma", "डिग्री या डिप्लोमा"),
                ("AICTE approved institution", "मान्यता प्राप्त तकनीकी संस्थान"),
                ("merit-cum-means", "मेरिट और आवश्यकता आधारित"),
            ]
            cleaned = text
            for eng, hi in replacements:
                cleaned = cleaned.replace(eng, hi)
            return cleaned

        benefit_clean = _hindi_clean(benefit)
        eligibility_clean = _hindi_clean(eligibility)

        # 1. Purpose (Crisp & direct — strictly under 1 min total)
        intro = (
            f"{name} भारत सरकार की एक प्रमुख {cat_hindi} है, "
            f"जो विद्यार्थियों को उच्च शिक्षा हेतु वित्तीय सहायता प्रदान करती है।"
        )

        # 2. Financial Benefit
        if benefit_clean and benefit_clean != "—":
            benefit_text = (
                f"इसके तहत चयनित छात्रों को {benefit_clean} की सीधी सहायता मिलती है, "
                f"जिससे कॉलेज फीस का खर्च आसानी से पूरा हो सके।"
            )
        else:
            benefit_text = (
                f"इसके तहत विद्यार्थियों को सरकारी नियमानुसार आवश्यक शिक्षण शुल्क और वित्तीय सहायता दी जाती है।"
            )

        # 3. Eligibility (Concise key criteria)
        if eligibility_clean:
            # Take the primary criteria clause
            parts = [p.strip() for p in eligibility_clean.split(';') if p.strip()]
            main_criteria = parts[0] if parts else eligibility_clean
            if len(main_criteria) > 85:
                main_criteria = main_criteria[:85].rsplit(' ', 1)[0]
            elig_text = f"पात्रता के अनुसार, {main_criteria}।"
        else:
            elig_text = (
                f"संबंधित पाठ्यक्रम में नियमित अध्ययनरत वे छात्र आवेदन कर सकते हैं "
                f"जिनकी पारिवारिक आय तय सीमा में हो।"
            )

        # 4. Action & Key advice
        action_text = (
            f"आवेदन {portal} पर ऑनलाइन होता है। "
            f"बैंक खाता आधार से लिंक रखें और फॉर्म जमा कर कॉलेज से सत्यापन जरूर करवाएं।"
        )

        return f"{intro} {benefit_text} {elig_text} {action_text}"

    def generate_audio_base64(self, scheme: dict) -> dict:
        """
        Full pipeline: generate Hindi text summary → TTS → base64 MP3.
        Returns {"text": <hindi_text>, "audio_b64": <base64_string>}
        """
        hindi_text = self.generate_hindi_summary(scheme)

        # Convert to speech
        tts = gTTS(text=hindi_text, lang="hi", slow=False)
        audio_buf = io.BytesIO()
        tts.write_to_fp(audio_buf)
        audio_buf.seek(0)
        audio_b64 = base64.b64encode(audio_buf.read()).decode("utf-8")

        return {
            "text": hindi_text,
            "audio_b64": audio_b64,
        }
