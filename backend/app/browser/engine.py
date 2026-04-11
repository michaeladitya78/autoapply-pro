"""
Browser Automation Engine — Stealth Playwright with Anti-Detection
Core layer for all job platform interactions.
"""
import asyncio
import json
import random
import os
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright, BrowserContext, Page
import structlog

from app.core.config import settings
from app.core.encryption import encrypt, decrypt
from app.core.vault import retrieve_session_data, store_session_data

log = structlog.get_logger()

# Real device fingerprints pool for normalization
FINGERPRINT_POOL = [
    {
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "viewport": {"width": 1920, "height": 1080},
        "locale": "en-US",
        "timezoneId": "America/New_York",
        "platform": "Win32",
    },
    {
        "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "viewport": {"width": 1440, "height": 900},
        "locale": "en-US",
        "timezoneId": "America/Los_Angeles",
        "platform": "MacIntel",
    },
    {
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
        "viewport": {"width": 1680, "height": 1050},
        "locale": "en-GB",
        "timezoneId": "Europe/London",
        "platform": "Win32",
    },
]


class StealthBrowserEngine:
    """
    Manages persistent Chromium profiles per user with full stealth.
    Handles session storage, restoration, and human-behavior simulation.
    """

    def __init__(self, user_id: str, platform: str, proxy_config: Optional[dict] = None):
        self.user_id = user_id
        self.platform = platform
        self.proxy_config = proxy_config
        self.fingerprint = random.choice(FINGERPRINT_POOL)
        self.profile_dir = Path(settings.BROWSER_PROFILES_PATH) / user_id / platform
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = None
        self._browser = None
        self._context: Optional[BrowserContext] = None

    async def __aenter__(self):
        await self.launch()
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def launch(self):
        """Launch browser with stealth config and restored session."""
        self._playwright = await async_playwright().start()

        launch_args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--window-size=1920,1080",
            f"--user-agent={self.fingerprint['userAgent']}",
        ]

        proxy = None
        if self.proxy_config:
            proxy = {
                "server": f"http://{self.proxy_config['host']}:{self.proxy_config['port']}",
                "username": self.proxy_config["username"],
                "password": self.proxy_config["password"],
            }

        self._browser = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.profile_dir),
            headless=True,
            args=launch_args,
            proxy=proxy,
            viewport=self.fingerprint["viewport"],
            locale=self.fingerprint["locale"],
            timezone_id=self.fingerprint["timezoneId"],
            user_agent=self.fingerprint["userAgent"],
            java_script_enabled=True,
            accept_downloads=True,
            # Anti-detection headers
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "no-cache",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-Mode": "navigate",
            },
        )
        self._context = self._browser

        # Inject stealth scripts on every page
        await self._context.add_init_script(self._stealth_script())
        log.info("Browser launched", user_id=self.user_id, platform=self.platform)

    def _stealth_script(self) -> str:
        """Anti-bot-detection JS injection."""
        return """
        // Remove WebDriver flag
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

        // Realistic plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5].map(() => ({ length: 0 })),
        });

        // Chrome runtime present (headless Chromium misses this)
        window.chrome = { runtime: {} };

        // Languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });

        // Permission status override
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) =>
            parameters.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : originalQuery(parameters);

        // WebGL vendor/renderer spoofing
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) return 'Intel Inc.';
            if (parameter === 37446) return 'Intel Iris OpenGL Engine';
            return getParameter.call(this, parameter);
        };
        """

    async def new_page(self) -> Page:
        """Open a new stealth page."""
        page = await self._context.new_page()
        return page

    async def session_warm_up(self, page: Page, platform_url: str):
        """
        Simulate organic browsing for 5-10 minutes before applying.
        Helps avoid detection on first run.
        """
        log.info("Session warm-up started", platform=self.platform)
        await page.goto(platform_url, wait_until="networkidle")
        await self.human_delay(3, 6)

        # Scroll naturally
        for _ in range(random.randint(3, 7)):
            scroll_amount = random.randint(300, 800)
            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            await self.human_delay(1, 3)

        log.info("Session warm-up complete", platform=self.platform)

    async def detect_auth_challenges(self, page: Page) -> Optional[str]:
        """
        Detect 2FA, CAPTCHA, suspicious activity, session expiry.
        Returns flag type or None if clean.
        """
        url = page.url
        content = await page.content()

        if "captcha" in content.lower() or "recaptcha" in content.lower() or "hcaptcha" in content.lower():
            return "captcha"
        if "two-factor" in content.lower() or "verification code" in content.lower() or "2fa" in content.lower():
            return "2fa"
        if "unusual sign-in" in content.lower() or "verify your identity" in content.lower():
            return "suspicious_login"
        if "login" in url.lower() or "signin" in url.lower() or "auth" in url.lower():
            return "session_expired"

        return None

    async def save_session(self):
        """Serialize and encrypt browser state to PostgreSQL."""
        if not self._context:
            return
        cookies = await self._context.cookies()
        session_data = json.dumps({"cookies": cookies})
        encrypted = encrypt(session_data)
        return encrypted

    async def restore_session(self, encrypted_session: str):
        """Restore encrypted session into the browser context."""
        if not self._context or not encrypted_session:
            return
        try:
            session_data = json.loads(decrypt(encrypted_session))
            await self._context.add_cookies(session_data["cookies"])
            log.info("Session restored", user_id=self.user_id, platform=self.platform)
        except Exception as e:
            log.warning("Session restore failed", error=str(e))

    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    # ─── Human Behavior Simulation ─────────────────────────────────────────
    @staticmethod
    async def human_delay(min_s: float = 0.5, max_s: float = 2.0):
        """Random delay to simulate human timing."""
        await asyncio.sleep(random.uniform(min_s, max_s))

    @staticmethod
    async def human_type(page: Page, selector: str, text: str):
        """Type like a human — variable speed with occasional hesitations."""
        element = await page.wait_for_selector(selector, timeout=10000)
        await element.click()
        await asyncio.sleep(random.uniform(0.2, 0.5))
        for char in text:
            await element.type(char)
            # Slower on special chars, faster on common letters
            delay = random.uniform(50, 200) if char.isalpha() else random.uniform(100, 400)
            await asyncio.sleep(delay / 1000)

    @staticmethod
    async def human_scroll(page: Page):
        """Scroll down the page naturally."""
        scroll = random.randint(200, 600)
        await page.evaluate(f"window.scrollBy(0, {scroll})")
        await asyncio.sleep(random.uniform(0.3, 1.5))

    @staticmethod
    async def human_click(page: Page, selector: str):
        """Click with random offset within element bounds."""
        element = await page.wait_for_selector(selector, timeout=10000)
        box = await element.bounding_box()
        if box:
            x = box["x"] + random.uniform(5, box["width"] - 5)
            y = box["y"] + random.uniform(5, box["height"] - 5)
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.3))
            await page.mouse.click(x, y)
        else:
            await element.click()
