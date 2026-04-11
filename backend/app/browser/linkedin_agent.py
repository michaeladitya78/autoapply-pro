"""
LinkedIn Easy Apply Agent
Autonomous job application submission on LinkedIn with stealth.
"""
import asyncio
import random
from typing import Optional
from playwright.async_api import Page
import structlog

from app.browser.engine import StealthBrowserEngine
from app.core.config import settings
from app.agents.llm import claude_tailor_resume, claude_generate_cover_letter

log = structlog.get_logger()

LINKEDIN_BASE = "https://www.linkedin.com"
LINKEDIN_JOBS = "https://www.linkedin.com/jobs/search/"


class LinkedInAgent:
    """
    Automates LinkedIn Easy Apply job applications.
    Handles multi-step forms, file uploads, and Q&A detection.
    """

    def __init__(self, user_id: str, preferences: dict, resume_content: str, proxy_config: dict):
        self.user_id = user_id
        self.preferences = preferences
        self.resume_content = resume_content
        self.proxy_config = proxy_config
        self.jobs_applied = 0
        self.daily_cap = settings.LINKEDIN_DAILY_CAP

    async def run(self, callbacks: dict = None) -> dict:
        """
        Main agent run. Returns summary dict with stats.
        callbacks = { on_flag: async fn, on_application: async fn, on_action: async fn }
        """
        results = {"applied": 0, "skipped": 0, "flags": [], "errors": []}

        engine = StealthBrowserEngine(
            user_id=self.user_id,
            platform="linkedin",
            proxy_config=self.proxy_config,
        )

        async with engine:
            page = await engine.new_page()

            # Check session or go to login
            await page.goto(LINKEDIN_BASE, wait_until="domcontentloaded")

            challenge = await engine.detect_auth_challenges(page)
            if challenge:
                log.warning("Auth challenge detected on launch", challenge=challenge)
                if callbacks and "on_flag" in callbacks:
                    await callbacks["on_flag"]({
                        "type": challenge,
                        "platform": "linkedin",
                        "description": f"LinkedIn requires human input: {challenge}",
                    })
                results["flags"].append(challenge)
                return results

            # Warm-up session
            await engine.session_warm_up(page, LINKEDIN_JOBS)

            # Search for jobs
            job_listings = await self._search_jobs(page, engine)
            log.info("Jobs found", count=len(job_listings))

            for job in job_listings:
                if self.jobs_applied >= self.daily_cap:
                    log.info("Daily cap reached", cap=self.daily_cap, platform="linkedin")
                    break

                try:
                    applied = await self._apply_to_job(page, engine, job, callbacks)
                    if applied:
                        self.jobs_applied += 1
                        results["applied"] += 1
                        if callbacks and "on_application" in callbacks:
                            await callbacks["on_application"](job)
                    else:
                        results["skipped"] += 1
                except Exception as e:
                    log.error("Application failed", job=job.get("title"), error=str(e))
                    results["errors"].append(str(e))

                # Cool-down between applications (human-plausible)
                await engine.human_delay(
                    random.uniform(30, 90),  # 30-90 seconds between apps
                    random.uniform(90, 180),
                )

            # Save session for next run
            session_data = await engine.save_session()

        return results

    async def _search_jobs(self, page: Page, engine: StealthBrowserEngine) -> list:
        """Search LinkedIn jobs matching user preferences."""
        jobs = []
        query = self.preferences.get("job_titles", ["Software Engineer"])[0]
        location = self.preferences.get("locations", ["Remote"])[0]

        search_url = (
            f"{LINKEDIN_JOBS}?keywords={query.replace(' ', '%20')}"
            f"&location={location.replace(' ', '%20')}"
            f"&f_LF=f_AL"  # Easy Apply filter
            f"&sortBy=DD"  # Most recent
        )

        await page.goto(search_url, wait_until="networkidle")
        await engine.human_delay(2, 4)

        # Extract job cards
        job_cards = await page.query_selector_all(".job-search-card")

        for card in job_cards[:50]:  # Max 50 per search
            try:
                title_el = await card.query_selector(".job-search-card__title")
                company_el = await card.query_selector(".job-search-card__subtitle")
                link_el = await card.query_selector("a.job-search-card__list-date")

                title = await title_el.inner_text() if title_el else ""
                company = await company_el.inner_text() if company_el else ""
                href = await link_el.get_attribute("href") if link_el else ""

                if title and href:
                    jobs.append({
                        "title": title.strip(),
                        "company": company.strip(),
                        "url": href,
                    })
            except Exception:
                continue

        return jobs

    async def _apply_to_job(
        self, page: Page, engine: StealthBrowserEngine, job: dict, callbacks: dict
    ) -> bool:
        """Click Easy Apply and fill the multi-step form."""
        await page.goto(job["url"], wait_until="networkidle")
        await engine.human_delay(2, 5)

        # Check for Easy Apply button
        easy_apply_btn = await page.query_selector(".jobs-apply-button")
        if not easy_apply_btn:
            log.debug("No Easy Apply button", job=job["title"])
            return False

        # Get job description for tailoring
        desc_el = await page.query_selector(".jobs-description__content")
        job_description = await desc_el.inner_text() if desc_el else ""

        # Tailor resume with Claude
        tailored_resume = await claude_tailor_resume(
            self.resume_content, job_description, job["title"], job["company"]
        )

        # Generate cover letter
        cover_letter = await claude_generate_cover_letter(
            self.resume_content, job_description, job["title"], job["company"]
        )

        # Click Easy Apply
        await engine.human_click(page, ".jobs-apply-button")
        await engine.human_delay(1, 3)

        # Handle multi-step form
        max_steps = 10
        for step in range(max_steps):
            # Check for auth challenges mid-flow
            challenge = await engine.detect_auth_challenges(page)
            if challenge:
                if callbacks and "on_flag" in callbacks:
                    await callbacks["on_flag"]({
                        "type": challenge,
                        "platform": "linkedin",
                        "description": f"Challenge during application: {challenge}",
                        "job": job["title"],
                    })
                return False

            # Check for CAPTCHA
            if await page.query_selector(".recaptcha-checkbox"):
                if callbacks and "on_flag" in callbacks:
                    await callbacks["on_flag"]({
                        "type": "captcha",
                        "platform": "linkedin",
                        "description": "CAPTCHA detected during application form",
                    })
                return False

            # Try to advance to next step
            next_btn = await page.query_selector("button[aria-label='Continue to next step']")
            review_btn = await page.query_selector("button[aria-label='Review your application']")
            submit_btn = await page.query_selector("button[aria-label='Submit application']")

            if submit_btn:
                await engine.human_click(page, "button[aria-label='Submit application']")
                await engine.human_delay(2, 4)
                log.info("Application submitted", job=job["title"], company=job["company"])
                return True
            elif review_btn:
                await engine.human_click(page, "button[aria-label='Review your application']")
                await engine.human_delay(1, 3)
            elif next_btn:
                # Fill any visible fields first
                await self._fill_form_fields(page, engine, tailored_resume, cover_letter)
                await engine.human_click(page, "button[aria-label='Continue to next step']")
                await engine.human_delay(1, 3)
            else:
                break

        return False

    async def _fill_form_fields(
        self, page: Page, engine: StealthBrowserEngine,
        tailored_resume: str, cover_letter: str
    ):
        """Auto-fill common form fields: cover letter textarea, standard Q&A."""
        # Cover letter textarea
        cover_textarea = await page.query_selector("textarea[name*='cover']")
        if cover_textarea:
            await cover_textarea.click()
            await cover_textarea.fill("")
            await engine.human_type(page, "textarea[name*='cover']", cover_letter[:2000])

        # Phone number (from preferences)
        phone_inputs = await page.query_selector_all("input[name*='phone']")
        for inp in phone_inputs:
            val = await inp.get_attribute("value")
            if not val:
                phone = self.preferences.get("phone", "")
                if phone:
                    await engine.human_type(page, "input[name*='phone']", phone)

        # Yes/No radio buttons (common LinkedIn screening questions)
        # Strategy: select "Yes" for positive screens, "No" for authorizations
        yes_radios = await page.query_selector_all("input[type='radio'][value='Yes']")
        for radio in yes_radios:
            is_checked = await radio.get_attribute("checked")
            if not is_checked:
                await radio.click()
                await engine.human_delay(0.3, 0.8)
