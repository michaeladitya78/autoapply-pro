# AutoApply Pro 🤖

> AI-powered autonomous job application & cold outreach engine

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](https://nextjs.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-blue)](https://langchain-ai.github.io/langgraph)
[![Playwright](https://img.shields.io/badge/Playwright-1.49-green?logo=playwright)](https://playwright.dev)

## What It Does

AutoApply Pro runs a multi-agent AI system that:

1. **Scrapes** matching jobs from LinkedIn, Indeed, Glassdoor, Wellfound, and 10+ platforms
2. **Tailors** your resume per job using Claude API (semantic keyword injection)
3. **Applies** via Playwright browser automation with full stealth (residential proxies, human-speed behavior)
4. **Outreaches** to hiring managers with Claude-drafted cold emails via Hunter.io contact discovery
5. **Follows up** at day 3, 7, and 14 automatically
6. **Notifies you** for CAPTCHAs, 2FA triggers, and interview invitations

## Architecture

```
Next.js Dashboard ──→ FastAPI Backend ──→ Celery Task Queue
                            │
                    ┌───────┴────────┐
                    │                │
              LangGraph           HashiCorp
              Orchestrator         Vault
                    │
         ┌──────────┼──────────┐
         │          │          │
      LinkedIn   Indeed    Outreach
       Agent     Agent      Agent
         │          │          │
    Playwright  Playwright  Hunter.io
    (Stealth)   (Stealth)   + Claude
         │
   Brightdata Proxy ← Residential IP per user
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+
- Python 3.12+

### 1. Clone & Configure

```bash
cp .env.example .env
# Fill in: ANTHROPIC_API_KEY, CLERK keys, BRIGHTDATA credentials
```

### 2. Start Infrastructure

```bash
docker-compose up -d postgres redis chromadb vault
```

### 3. Start Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
playwright install chromium
uvicorn app.main:app --reload --port 8080
```

### 4. Start Celery Worker (separate terminal)

```bash
cd backend
celery -A app.workers.celery_app worker --loglevel=info --concurrency=4 -Q agent,email
```

### 5. Start Frontend

```bash
cd frontend
npm run dev
# Open http://localhost:3000
```

## Configuration

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Claude API key for resume tailoring & email generation |
| `CLERK_SECRET_KEY` | Clerk auth secret |
| `CLERK_WEBHOOK_SECRET` | Webhook signature verification |
| `BRIGHTDATA_USERNAME` | Residential proxy username |
| `BRIGHTDATA_PASSWORD` | Residential proxy password |
| `HUNTER_API_KEY` | Hunter.io for contact discovery |
| `VAULT_TOKEN` | HashiCorp Vault root token |

## Platform Support

| Platform | Method | Status |
|----------|--------|--------|
| LinkedIn | Easy Apply | ✅ MVP |
| Indeed | Quick Apply | ✅ MVP |
| Glassdoor | Easy Apply | 🔜 Week 3 |
| Wellfound | Direct Apply | 🔜 Week 4 |
| Naukri | Quick Apply | 🔜 Week 4 |
| ZipRecruiter | 1-Click | 🔜 Week 5 |
| Dice | Easy Apply | 🔜 Week 5 |
| Upwork | Proposal | 🔜 Month 2 |
| Remotive | Direct | 🔜 Month 2 |
| Toptal | Screening | 🔜 Month 3 |

## Security

- **Session Storage**: AES-256-GCM encrypted cookies in PostgreSQL
- **Raw Credentials**: HashiCorp Vault exclusively (KV v2) — never in DB
- **Transport**: TLS 1.3 only
- **Proxy**: Dedicated residential IP per user session (Brightdata)
- **Anti-Detection**: Stealth JS injection, fingerprint normalization, human-timing simulation
- **Data Deletion**: Full credential + session purge on account deletion

## Legal Notice

Automated activity may violate the Terms of Service of LinkedIn, Indeed, and other platforms. Users accept full responsibility. This software is provided as-is. See Terms of Service.

## License

MIT © 2025 AutoApply Pro
