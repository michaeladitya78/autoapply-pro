import asyncio
import json
import logging
import uuid
from pprint import pprint

from app.agents.llm import (
    claude_analyze_job_fit,
    claude_generate_cover_letter,
    claude_tailor_resume,
    claude_draft_cold_email,
)
from app.agents.orchestrator import run_orchestrator, AgentState

# Configure basic logging for the test
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# --- DEMO DATA ---

DEMO_USER_ID = "usr_demo_123"
DEMO_RUN_ID = f"run_{uuid.uuid4().hex[:8]}"

DEMO_RESUME = """
Michael C. Engineer
Location: San Francisco, CA | Email: michael.dev@example.com

SUMMARY:
Software Engineer with 4 years of experience building scalable backends and intelligent automation platforms. 
Proficient in Python, Go, and React. Passionate about machine learning and agentic workflows.

EXPERIENCE:
DataMinds Inc - Backend Engineer (2021 - Present)
- Architected a highly concurrent data ingestion pipeline in Go, reducing latency by 45%.
- Built RESTful and GraphQL APIs using FastAPI and Apollo.
- Migrated legacy monolithic services to a Kubernetes-managed microservices architecture on AWS.
- Mentored 2 junior developers.

WebSolutions - Full Stack Developer (2019 - 2021)
- Developed responsive web interfaces using React and Next.js for e-commerce clients.
- Implemented state management using Redux and Context API.
- Integrated Stripe for secure payment processing.
- Increased site performance score by 30% through code splitting and asset optimization.

SKILLS:
Python, Go, JavaScript, TypeScript, React, Next.js, Django, FastAPI, PostgreSQL, MongoDB, Redis, AWS, Docker, Kubernetes
"""

DEMO_JOB_1 = {
    "title": "Senior Backend Engineer (AI Platform)",
    "company": "Neural Dynamics",
    "description": """
    Neural Dynamics is building the next generation of autonomous AI agents. We are looking for a Senior Backend Engineer to join our core orchestration team.
    
    Responsibilities:
    - Design and build the orchestrator backend handling thousands of concurrent agent workflows.
    - Integrate with various LLM providers (Anthropic, OpenAI, local models).
    - Ensure high availability and fault tolerance of our distributed systems.
    
    Requirements:
    - 5+ years of software engineering experience.
    - Deep expertise in Python and async programming (e.g., FastAPI, asyncio).
    - Experience with workflow orchestration (Temporal, Celery, or similar).
    - Strong understanding of containerization and orchestration (Docker, Kubernetes).
    - Nice to have: Experience with AI/LLM integrations or LangChain/LangGraph.
    """,
}

DEMO_PREFERENCES = {
    "job_titles": ["Backend Engineer", "Software Engineer", "AI Engineer"],
    "salary_min": 130000,
    "salary_max": 200000,
    "work_type": ["Remote", "Hybrid"],
    "locations": ["San Francisco, CA", "Remote"],
}


async def test_llm_components():
    log.info("--- Testing LLM components ---")
    
    log.info("1. Testing Job Fit Analysis...")
    fit = await claude_analyze_job_fit(
        resume_text=DEMO_RESUME,
        job_description=DEMO_JOB_1["description"],
        job_title=DEMO_JOB_1["title"],
        company=DEMO_JOB_1["company"]
    )
    log.info(f"Fit Score: {fit.fit_score} (Grade: {fit.grade})")
    log.info(f"Recommendation to apply: {fit.apply_recommendation}")
    log.info(f"Reasoning: {fit.reasoning}")
    
    log.info("\n2. Testing Resume Tailoring...")
    tailored = await claude_tailor_resume(
        resume_text=DEMO_RESUME,
        job_description=DEMO_JOB_1["description"],
        job_title=DEMO_JOB_1["title"],
        company=DEMO_JOB_1["company"]
    )
    log.info(f"Changes summary: {tailored.changes_summary}")
    # Don't print the whole resume, just keywords and score
    log.info(f"ATS Estimate: {tailored.ats_score_estimate}%")
    log.info(f"Keywords injected: {tailored.keywords_injected}")
    
    log.info("\n3. Testing Cover Letter Gen...")
    cl = await claude_generate_cover_letter(
        resume_text=DEMO_RESUME,
        job_description=DEMO_JOB_1["description"],
        job_title=DEMO_JOB_1["title"],
        company=DEMO_JOB_1["company"]
    )
    log.info(f"Generated Subject: {cl.subject}")
    log.info(f"Word count: {cl.word_count}")
    
    log.info("\n4. Testing Cold Email...")
    cold = await claude_draft_cold_email(
        my_resume=DEMO_RESUME,
        contact_name="Sarah Hirer",
        contact_title="VP of Engineering",
        company=DEMO_JOB_1["company"],
        job_role=DEMO_JOB_1["title"]
    )
    log.info(f"Subject: {cold.subject}")
    log.info(f"Body snippet: {cold.body[:100]}...")


# We need to mock the LinkedIn agent for the orchestrator test so it doesn't actually hit the web
from unittest.mock import patch, MagicMock

async def test_orchestrator_dry_run():
    log.info("\n--- Testing Orchestrator Graph (Dry Run) ---")
    
    # We will mock LinkedInAgent so it just returns our DEMO_JOB_1
    with patch("app.browser.linkedin_agent.LinkedInAgent") as MockLinkedInAgent, \
         patch("app.agents.orchestrator.ws_manager") as MockWsManager:
        
        from unittest.mock import AsyncMock
        
        # Setup mock behavior
        mock_agent_instance = AsyncMock()
        mock_agent_instance.run.return_value = {"jobs_found": [DEMO_JOB_1]}
        MockLinkedInAgent.return_value = mock_agent_instance
        
        MockWsManager.broadcast_agent_update = AsyncMock()
        
        with patch("app.agents.llm.claude_analyze_job_fit", new_callable=AsyncMock) as MockAnalyze:
            from app.agents.llm import JobFitAnalysis
            MockAnalyze.return_value = JobFitAnalysis(
                fit_score=90, grade="A", apply_recommendation=True, reasoning="Mock reasoning", strengths=[], gaps=[], keywords_present=[], keywords_missing=[]
            )
            
            result = await run_orchestrator(
                user_id=DEMO_USER_ID,
                run_id=DEMO_RUN_ID,
                preferences=DEMO_PREFERENCES,
                resume_content=DEMO_RESUME,
                proxy_config={},
                dry_run=True  # Important!
            )
            
            log.info(f"Orchestrator finished with status: {result['status']}")
            
            stats = result.get("stats", {})
            log.info("Run stats:")
            log.info(f"  Jobs Found: {stats.get('jobs_found')}")
            log.info(f"  Jobs Applied/Mocked: {stats.get('jobs_applied')}")
            log.info(f"  Low Fit Skipped: {stats.get('jobs_skipped_low_fit')}")
            log.info(f"  Errors: {stats.get('errors')}")


async def main():
    await test_llm_components()
    await test_orchestrator_dry_run()

if __name__ == "__main__":
    asyncio.run(main())
