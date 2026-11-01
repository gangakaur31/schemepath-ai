"""
browser_agent.py — Playwright-based browser automation agent for AVSAR.

Navigates real government portals and assists with form filling for scheme
applications on behalf of students.
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional

from playwright.async_api import Browser, Page, async_playwright

from models.schemas import (
    ApplicationRequest,
    ApplicationResponse,
    ApplicationStep,
    SchemeResult,
    StudentProfile,
)

logger = logging.getLogger("schemepath.browser_agent")

# ─── Portal automation configs ───────────────────────────────────────────────

PORTAL_CONFIGS: Dict[str, Dict] = {
    "scholarships.gov.in": {
        "name": "National Scholarship Portal (NSP)",
        # Go directly to NEW student registration — public page, has fillable fields
        "login_url": "https://scholarships.gov.in/fresh/newstudentregistrations",
        "type": "nsp",
    },
    "vidyalakshmi.co.in": {
        "name": "Vidya Lakshmi Portal",
        # Go directly to student registration form
        "login_url": "https://www.vidyalakshmi.co.in/Students/scholarshipregister",
        "type": "vidya_lakshmi",
    },
    "pminternship.mca.gov.in": {
        "name": "PM Internship Portal",
        # Registration page is public
        "login_url": "https://pminternship.mca.gov.in/register/",
        "type": "pm_internship",
    },
    "pmkvyproject.org": {
        "name": "PMKVY Portal",
        "login_url": "https://www.pmkvyproject.org",
        "type": "pmkvy",
    },
    "pmkvyofficial.org": {
        "name": "PMKVY Portal",
        "login_url": "https://www.pmkvyproject.org",
        "type": "pmkvy",
    },
    "myscheme.gov.in": {
        "name": "MyScheme Portal",
        "login_url": "https://www.myscheme.gov.in",
        "type": "myscheme",
    },
    "ugcnet.nta.nic.in": {
        "name": "UGC NET Portal",
        "login_url": "https://ugcnet.nta.nic.in",
        "type": "generic",
    },
    "online-inspire.gov.in": {
        "name": "DST INSPIRE Portal",
        "login_url": "https://online-inspire.gov.in",
        "type": "generic",
    },
    "nosmsje.gov.in": {
        "name": "National Overseas Scholarship Portal",
        "login_url": "https://nosmsje.gov.in",
        "type": "generic",
    },
}


# ─── BrowserAgent ────────────────────────────────────────────────────────────


class BrowserAgent:
    """
    Playwright-based automation agent.

    Launches a Chromium browser, navigates to a government scheme portal,
    analyses the application form, pre-fills fields with student data, and
    returns a step-by-step progress report with screenshots.
    """

    def __init__(
        self,
        headless: bool = True,
        screenshots_dir: str = "./screenshots",
    ) -> None:
        self.headless = headless
        self.screenshots_dir = screenshots_dir
        os.makedirs(screenshots_dir, exist_ok=True)

    # ── Public API ────────────────────────────────────────────────────────────

    async def navigate_to_scheme(
        self,
        portal_url: str,
        profile: StudentProfile,
        scheme_name: str,
    ) -> ApplicationResponse:
        """
        Navigate to a scheme's portal, extract info, and assist with form navigation.

        Returns step-by-step progress and any tracking information found.
        """
        steps: List[ApplicationStep] = []

        async with async_playwright() as p:
            browser: Browser = await p.chromium.launch(
                headless=self.headless,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()

            try:
                # ── Step 1: Navigate to portal ────────────────────────────────
                step1 = ApplicationStep(
                    step_number=1,
                    description=f"Opening {scheme_name} portal",
                    status="pending",
                )
                steps.append(step1)

                await page.goto(portal_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)

                ss_path1 = os.path.join(self.screenshots_dir, "step1_portal.png")
                await page.screenshot(path=ss_path1, full_page=False)
                step1.status = "completed"
                step1.screenshot_path = ss_path1
                logger.info("[browser_agent] Step 1 complete — portal loaded: %s", portal_url)

                # ── Step 2: Analyse form structure ────────────────────────────
                step2 = ApplicationStep(
                    step_number=2,
                    description="Analyzing application form structure",
                    status="pending",
                )
                steps.append(step2)

                portal_type = self._detect_portal_type(portal_url)
                form_info = await self._extract_form_info(page)
                logger.info(
                    "[browser_agent] Step 2 complete — portal_type=%s, fields_found=%d",
                    portal_type,
                    len(form_info.get("fields", [])),
                )

                ss_path2 = os.path.join(self.screenshots_dir, "step2_form.png")
                await page.screenshot(path=ss_path2, full_page=False)
                step2.status = "completed"
                step2.screenshot_path = ss_path2

                # ── Step 3: Navigate to registration / application section ────
                step3 = ApplicationStep(
                    step_number=3,
                    description="Navigating to application section",
                    status="pending",
                )
                steps.append(step3)

                await self._navigate_to_application(page, portal_type, profile)
                logger.info("[browser_agent] Step 3 complete — navigated to application section.")

                ss_path3 = os.path.join(self.screenshots_dir, "step3_application.png")
                await page.screenshot(path=ss_path3, full_page=False)
                step3.status = "completed"
                step3.screenshot_path = ss_path3

                # ── Step 4: Pre-fill form fields ──────────────────────────────
                step4 = ApplicationStep(
                    step_number=4,
                    description="Pre-filling form with student details",
                    status="pending",
                )
                steps.append(step4)

                filled_fields = await self._prefill_form(page, profile)
                logger.info(
                    "[browser_agent] Step 4 complete — %d field(s) pre-filled.",
                    len(filled_fields),
                )

                ss_path4 = os.path.join(self.screenshots_dir, "step4_filled.png")
                await page.screenshot(path=ss_path4, full_page=False)
                step4.status = "completed"
                step4.screenshot_path = ss_path4

                # ── Step 5: Extract page instructions ─────────────────────────
                step5 = ApplicationStep(
                    step_number=5,
                    description="Extracting application instructions",
                    status="pending",
                )
                steps.append(step5)

                instructions = await self._extract_instructions(page)
                logger.info(
                    "[browser_agent] Step 5 complete — %d instruction(s) extracted.",
                    len(instructions),
                )
                step5.status = "completed"

                current_url = page.url

                return ApplicationResponse(
                    success=True,
                    tracking_id=None,  # Would be extracted after actual submission
                    confirmation_url=current_url,
                    message=(
                        f"Successfully navigated to {scheme_name} portal. "
                        f"{len(filled_fields)} field(s) pre-filled. "
                        "Student needs to log in / register to complete submission."
                    ),
                    steps_completed=steps,
                )

            except Exception as exc:
                logger.error("[browser_agent] Navigation error: %s", exc, exc_info=True)
                ss_path_err = os.path.join(self.screenshots_dir, "error.png")
                try:
                    await page.screenshot(path=ss_path_err)
                except Exception:
                    pass

                return ApplicationResponse(
                    success=False,
                    message=(
                        f"Navigation encountered an issue: {exc}. "
                        f"Please visit {portal_url} directly."
                    ),
                    steps_completed=steps,
                    error_details=str(exc),
                )

            finally:
                await browser.close()

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _detect_portal_type(self, url: str) -> str:
        """Return the portal type key based on the URL domain."""
        for domain, config in PORTAL_CONFIGS.items():
            if domain in url:
                return config["type"]
        return "generic"

    async def _extract_form_info(self, page: Page) -> Dict:
        """Extract form fields and structure from the current page."""
        try:
            form_info = await page.evaluate(
                """
                () => {
                    const inputs = Array.from(
                        document.querySelectorAll('input, select, textarea')
                    );
                    return inputs.map(el => ({
                        type: el.type || el.tagName.toLowerCase(),
                        name: el.name || el.id || '',
                        placeholder: el.placeholder || '',
                        label: el.labels && el.labels[0]
                            ? el.labels[0].textContent.trim()
                            : '',
                        required: el.required,
                    })).filter(f => f.name || f.placeholder);
                }
                """
            )
            return {"fields": form_info}
        except Exception as exc:
            logger.debug("[browser_agent] _extract_form_info failed: %s", exc)
            return {"fields": []}

    async def _navigate_to_application(
        self, page: Page, portal_type: str, profile: StudentProfile
    ) -> None:
        """Navigate to the application / registration section of the portal."""
        try:
            if portal_type == "nsp":
                candidates = [
                    'a:has-text("New Registration")',
                    'a:has-text("Fresh Application")',
                    'a:has-text("Applicant Corner")',
                    'a:has-text("Apply")',
                    '[href*="registration"]',
                    '[href*="apply"]',
                ]
            elif portal_type == "vidya_lakshmi":
                candidates = [
                    'a:has-text("Student Registration")',
                    'a:has-text("Apply")',
                    ".btn-apply",
                ]
            elif portal_type == "pm_internship":
                candidates = [
                    'a:has-text("Register")',
                    'a:has-text("Apply")',
                    'button:has-text("Apply Now")',
                ]
            elif portal_type == "pmkvy":
                candidates = [
                    'a:has-text("Find a Training Centre")',
                    'a:has-text("Enroll")',
                    'a:has-text("Apply")',
                ]
            elif portal_type == "myscheme":
                candidates = [
                    'a:has-text("Check Eligibility")',
                    'a:has-text("Apply")',
                    '[data-testid="apply-button"]',
                ]
            else:
                candidates = [
                    'a:has-text("Apply")',
                    'a:has-text("Register")',
                    'button:has-text("Apply")',
                    '[class*="apply"]',
                    '[class*="register"]',
                ]

            for selector in candidates:
                try:
                    el = page.locator(selector).first
                    if await el.count() > 0:
                        await el.click(timeout=3000)
                        await page.wait_for_timeout(2000)
                        logger.debug(
                            "[browser_agent] Clicked application link via selector: %s", selector
                        )
                        break
                except Exception:
                    continue

        except Exception as exc:
            logger.debug("[browser_agent] _navigate_to_application skipped: %s", exc)

    async def _prefill_form(self, page: Page, profile: StudentProfile) -> List[str]:
        """Attempt to pre-fill visible form fields with student data."""
        filled: List[str] = []

        field_map = {
            # Name fields
            'input[name*="name" i], input[placeholder*="name" i], input[id*="name" i]': profile.name,
            # State
            'select[name*="state" i], select[id*="state" i]': profile.state,
            # District
            'select[name*="district" i], input[name*="district" i]': profile.district or "",
            # Gender (text inputs only — selects handled separately below)
            'input[name*="gender" i], input[id*="gender" i]': profile.gender.value,
            # Category / caste
            'select[name*="category" i], select[id*="category" i], select[name*="caste" i]': profile.category.value.upper(),
            # Course / program
            'input[name*="course" i], input[placeholder*="course" i], input[name*="program" i]': profile.course,
        }

        for selector, value in field_map.items():
            if not value:
                continue
            try:
                elements = page.locator(selector)
                count = await elements.count()
                if count > 0:
                    tag = await elements.first.evaluate("el => el.tagName.toLowerCase()")
                    if tag == "select":
                        # Try to select a matching option by label; fall back to value
                        try:
                            await elements.first.select_option(label=value, timeout=2000)
                        except Exception:
                            try:
                                await elements.first.select_option(value=value, timeout=2000)
                            except Exception:
                                continue
                    else:
                        await elements.first.fill(value, timeout=2000)
                    filled.append(selector)
            except Exception:
                continue

        return filled

    async def _extract_instructions(self, page: Page) -> List[str]:
        """Extract any application instructions visible on the page."""
        try:
            instructions = await page.evaluate(
                """
                () => {
                    const items = [];
                    document.querySelectorAll(
                        'li, .instruction, .note, .alert, .info, [class*="instruction"], [class*="guideline"]'
                    ).forEach(el => {
                        const text = el.textContent.trim();
                        if (text.length > 20 && text.length < 300) items.push(text);
                    });
                    return items.slice(0, 10);
                }
                """
            )
            return instructions
        except Exception as exc:
            logger.debug("[browser_agent] _extract_instructions failed: %s", exc)
            return []


# ─── Public entry point ───────────────────────────────────────────────────────


async def run_browser_agent(
    request: ApplicationRequest,
    scheme: Optional[SchemeResult] = None,
) -> ApplicationResponse:
    """
    Entry point for browser automation, called from the FastAPI router.

    Parameters
    ----------
    request:
        The ApplicationRequest containing session_id, scheme_id, and the
        student's StudentProfile.
    scheme:
        The SchemeResult object resolved from the session cache by the router.
        When provided, its portal_url is used for navigation.  If None, falls
        back to the MyScheme portal with the scheme_id slug.
    """
    profile: StudentProfile = request.profile

    if scheme is not None and scheme.portal_url:
        portal_url = scheme.portal_url
        scheme_name = scheme.name
    else:
        # Fallback: construct a MyScheme detail URL from the scheme_id
        portal_url = f"https://www.myscheme.gov.in/schemes/{request.scheme_id}"
        scheme_name = request.scheme_id

    logger.info(
        "[browser_agent] run_browser_agent — scheme_id=%s, portal_url=%s",
        request.scheme_id,
        portal_url,
    )

    agent = BrowserAgent(headless=True, screenshots_dir="./screenshots")
    return await agent.navigate_to_scheme(portal_url, profile, scheme_name)
