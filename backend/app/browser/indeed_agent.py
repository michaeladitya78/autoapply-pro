"""
Indeed Quick Apply agent — full implementation.
Searches jobs, detects Quick Apply, fills forms, submits.
"""
import asyncio
import random
from playwright.async_api import Page
import structlog

from app.browser.engine import StealthBrowserEngine
from app.core.config import settings
from app.agents.llm import claude_tailor_resume, claude_generate_cover_letter

log = structlog.get_logger()
INDEED_BASE = "https://www.indeed.com"
INDEED_JOBS = "https://www.indeed.com/jobs"


class IndeedAgent:
    def __init__(self, user_id: str, preferences: dict, resume_content: str, proxy_config: dict):
        self.user_id = user_id
        self.preferences = preferences
        self.resume_content = resume_content
        self.proxy_config = proxy_config
        self.daily_cap = settings.INDEED_DAILY_CAP
        self.jobs_applied = 0

    async def run(self, callbacks: dict = None) -> dict:
        results = {"applied": 0, "skipped": 0, "flags": [], "errors": []}

        async with StealthBrowserEngine(
            user_id=self.user_id, platform="indeed", proxy_config=self.proxy_config
        ) as engine:
            page = await engine.new_page()
            await page.goto(INDEED_BASE, wait_until="domcontentloaded")

            challenge = await engine.detect_auth_challenges(page)
            if challenge:
                results["flags"].append(challenge)
                if callbacks and "on_flag" in callbacks:
                    await callbacks["on_flag"]({"type": challenge, "platform": "indeed"})
                return results

            await engine.session_warm_up(page, INDEED_JOBS)
            job_listings = await self._search_jobs(page, engine)
            log.info("Indeed jobs found", count=len(job_listings), user_id=self.user_id)

            for job in job_listings:
                if self.jobs_applied >= self.daily_cap:
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
                    log.error("Indeed apply failed", job=job.get("title"), error=str(e))
                    results["errors"].append(str(e))

                await engine.human_delay(random.uniform(20, 60), random.uniform(60, 120))

        return results

    async def _search_jobs(self, page: Page, engine: StealthBrowserEngine) -> list:
        jobs = []
        query = self.preferences.get("job_titles", ["Software Engineer"])[0]
        location = self.preferences.get("locations", ["Remote"])[0]
        # remotejob GUID = Indeed's remote filter
        search_url = (
            f"{INDEED_JOBS}?q={query.replace(' ', '+')}"
            f"&l={location.replace(' ', '+')}"
            f"&remotejob=032b3046-06a3-4876-8dfd-474eb5e7ed11"
            f"&sort=date"
        )
        await page.goto(search_url, wait_until="networkidle")
        await engine.human_delay(2, 4)

        # Indeed uses data-jk attribute on job cards
        job_cards = await page.query_selector_all("[data-jk]")
        for card in job_cards[:40]:
            try:
                jk = await card.get_attribute("data-jk")
                title_el = await card.query_selector(".jobTitle span")
                company_el = await card.query_selector("[data-testid='company-name']")
                title = await title_el.inner_text() if title_el else ""
                company = await company_el.inner_text() if company_el else ""
                if title and jk:
                    jobs.append({
                        "title": title.strip(),
                        "company": company.strip(),
                        "url": f"{INDEED_BASE}/viewjob?jk={jk}",
                        "jk": jk,
                    })
            except Exception:
                continue
        return jobs

    async def _apply_to_job(
        self, page: Page, engine: StealthBrowserEngine, job: dict, callbacks: dict
    ) -> bool:
        await page.goto(job["url"], wait_until="networkidle")
        await engine.human_delay(2, 5)

        # Check for auth challenge
        challenge = await engine.detect_auth_challenges(page)
        if challenge:
            if callbacks and "on_flag" in callbacks:
                await callbacks["on_flag"]({"type": challenge, "platform": "indeed", "job": job["title"]})
            return False

        # Find Apply button — Indeed has "Apply now" or "Easily apply"
        apply_btn = (
            await page.query_selector("button[id='indeedApplyButton']")
            or await page.query_selector(".ia-IndeedApplyButton")
            or await page.query_selector("a[data-indeed-apply-joburl]")
        )
        if not apply_btn:
            log.debug("No quick apply button", job=job["title"])
            return False

        # Extract job description for tailoring
        desc_el = await page.query_selector("#jobDescriptionText")
        job_description = await desc_el.inner_text() if desc_el else ""

        tailored_resume = await claude_tailor_resume(
            self.resume_content, job_description, job["title"], job["company"]
        )
        cover_letter = await claude_generate_cover_letter(
            self.resume_content, job_description, job["title"], job["company"]
        )

        await apply_btn.click()
        await engine.human_delay(1, 3)

        # Indeed Indeed Apply modal — multi-step
        for step in range(8):
            await engine.human_delay(1, 2)

            # CAPTCHA check
            if await page.query_selector(".g-recaptcha, iframe[title*='reCAPTCHA']"):
                if callbacks and "on_flag" in callbacks:
                    await callbacks["on_flag"]({"type": "captcha", "platform": "indeed", "job": job["title"]})
                return False

            # Fill cover letter field
            cover_area = await page.query_selector("textarea[name*='coverletter'], textarea[data-testid*='cover']")
            if cover_area:
                await cover_area.fill(cover_letter[:2000])
                await engine.human_delay(0.5, 1.5)

            # Continue / Next / Submit
            submit = await page.query_selector("button[data-testid='ia-IndeedApplyButton-primary']") \
                       or await page.query_selector("button[type='submit']:has-text('Submit')")
            next_btn = await page.query_selector("button[data-testid='ia-continueButton']") \
                        or await page.query_selector("button:has-text('Continue')")

            if submit and await submit.is_visible():
                await submit.click()
                await engine.human_delay(2, 3)
                log.info("Indeed application submitted", job=job["title"], company=job["company"])
                return True
            elif next_btn and await next_btn.is_visible():
                await next_btn.click()
            else:
                break

        return False
