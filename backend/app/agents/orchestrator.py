"""
Master Orchestrator Agent — LangGraph State Machine
=====================================================
Coordinates sub-agents: scraping, applying, outreach, follow-up.

Improvements v2:
  - Per-node error isolation (one node failure doesn't crash the whole run)
  - Circuit breaker: auto-pause after N consecutive failures
  - Rich status reporting for WebSocket real-time updates
  - Dry-run mode (no real applications submitted — for testing)
  - Job fit pre-screening before applying (saves quota)
"""
from __future__ import annotations

from typing import Annotated, Optional, TypedDict

import structlog
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.core.websocket_manager import ws_manager

log = structlog.get_logger()

# Max consecutive errors before auto-pause
_MAX_ERRORS_BEFORE_PAUSE = 5
# Min fit score to auto-apply (0-100)
_MIN_FIT_SCORE_TO_APPLY = 60


# ─── State ────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    user_id: str
    run_id: str
    preferences: dict
    resume_content: str
    proxy_config: dict
    dry_run: bool                    # NEW: if True, don't submit real applications
    jobs_found: list
    jobs_screened: list              # NEW: fit-analyzed jobs
    jobs_applied: list
    jobs_skipped: list               # NEW: jobs below fit threshold
    contacts_found: list
    emails_drafted: list
    flags: list
    errors: list
    status: str                      # running | paused | completed | failed
    current_platform: Optional[str]
    stats: dict                      # NEW: running metrics


def _empty_stats() -> dict:
    return {
        "jobs_found": 0,
        "jobs_applied": 0,
        "jobs_skipped_low_fit": 0,
        "emails_drafted": 0,
        "errors": 0,
        "start_time": None,
    }


# ─── Helper: broadcast with error swallow ────────────────────────────────────

async def _broadcast(user_id: str, event: str, data: dict) -> None:
    """Broadcast WebSocket update, swallowing errors so agent is never blocked."""
    try:
        await ws_manager.broadcast_agent_update(user_id, event, data)
    except Exception as e:
        log.warning("WebSocket broadcast failed", error=str(e))


# ─── Node: Pre-Screen Jobs with Fit Analysis ─────────────────────────────────

async def pre_screen_jobs_node(state: AgentState) -> AgentState:
    """
    NEW: Score each discovered job against the resume before applying.
    Only jobs above _MIN_FIT_SCORE_TO_APPLY proceed to the apply step.
    """
    from app.agents.llm import claude_analyze_job_fit

    jobs = state.get("jobs_found", [])
    if not jobs:
        return state

    await _broadcast(state["user_id"], "agent_action", {
        "action": "pre_screening",
        "message": f"Analyzing fit for {len(jobs)} jobs before applying...",
        "count": len(jobs),
    })

    screened, skipped = [], []
    resume = state["resume_content"]

    for job in jobs:
        try:
            analysis = await claude_analyze_job_fit(
                resume_text=resume,
                job_description=job.get("description", ""),
                job_title=job.get("title", ""),
                company=job.get("company", ""),
            )
            job["fit_analysis"] = {
                "score": analysis.fit_score,
                "grade": analysis.grade,
                "strengths": analysis.strengths,
                "gaps": analysis.gaps,
                "apply_recommendation": analysis.apply_recommendation,
                "reasoning": analysis.reasoning,
            }
            if analysis.fit_score >= _MIN_FIT_SCORE_TO_APPLY:
                screened.append(job)
                log.info("Job passed screening", company=job.get("company"), score=analysis.fit_score)
            else:
                skipped.append(job)
                log.info("Job skipped — low fit", company=job.get("company"), score=analysis.fit_score)
        except Exception as e:
            log.warning("Fit analysis failed for job", company=job.get("company"), error=str(e))
            screened.append(job)  # Include on analysis failure (safe default)

    state["jobs_screened"] = screened
    state["jobs_skipped"] = skipped
    state["stats"]["jobs_skipped_low_fit"] = len(skipped)

    await _broadcast(state["user_id"], "screening_complete", {
        "jobs_passing": len(screened),
        "jobs_skipped": len(skipped),
        "message": f"{len(screened)} jobs passed fit screen, {len(skipped)} below threshold",
    })
    return state


# ─── Node: Scrape Jobs ────────────────────────────────────────────────────────

async def scrape_jobs_node(state: AgentState) -> AgentState:
    """Discover job listings across connected platforms."""
    from app.browser.linkedin_agent import LinkedInAgent

    log.info("Scraping jobs", user_id=state["user_id"])
    await _broadcast(state["user_id"], "agent_action", {
        "action": "scraping_jobs",
        "platform": "linkedin",
        "message": "Searching for matching job listings on LinkedIn...",
    })

    state["current_platform"] = "linkedin"

    async def on_flag(flag_data: dict) -> None:
        state["flags"].append(flag_data)
        await _broadcast(state["user_id"], "human_flag", flag_data)

    async def on_job_found(job: dict) -> None:
        state["jobs_found"].append(job)
        state["stats"]["jobs_found"] += 1

    try:
        agent = LinkedInAgent(
            user_id=state["user_id"],
            preferences=state["preferences"],
            resume_content=state["resume_content"],
            proxy_config=state["proxy_config"],
        )
        results = await agent.run(
            callbacks={"on_flag": on_flag, "on_job_found": on_job_found}
        )
        state["jobs_found"].extend(results.get("jobs_found", []))
        state["stats"]["jobs_found"] = len(state["jobs_found"])
    except Exception as e:
        err = f"LinkedIn scraper failed: {e}"
        log.error("Scraper error", error=err)
        state["errors"].append(err)
        state["stats"]["errors"] += 1

    return state


# ─── Node: Apply to Jobs ──────────────────────────────────────────────────────

async def apply_jobs_node(state: AgentState) -> AgentState:
    """Apply to pre-screened jobs (or skip if dry_run=True)."""
    jobs_to_apply = state.get("jobs_screened") or state.get("jobs_found", [])
    if not jobs_to_apply:
        return state

    if state.get("dry_run"):
        log.info("DRY RUN: skipping real applications", count=len(jobs_to_apply))
        await _broadcast(state["user_id"], "agent_action", {
            "action": "dry_run_apply",
            "message": f"[DRY RUN] Would apply to {len(jobs_to_apply)} jobs",
        })
        state["jobs_applied"] = jobs_to_apply  # Mark as "applied" for dry run stats
        state["stats"]["jobs_applied"] = len(jobs_to_apply)
        return state

    from app.browser.linkedin_agent import LinkedInAgent

    async def on_application(job: dict) -> None:
        state["jobs_applied"].append(job)
        state["stats"]["jobs_applied"] += 1
        await _broadcast(state["user_id"], "application_submitted", {
            **job,
            "total_applied": state["stats"]["jobs_applied"],
        })

    try:
        agent = LinkedInAgent(
            user_id=state["user_id"],
            preferences=state["preferences"],
            resume_content=state["resume_content"],
            proxy_config=state["proxy_config"],
        )
        await agent.apply_to_jobs(
            jobs=jobs_to_apply,
            callbacks={"on_application": on_application},
        )
    except Exception as e:
        err = f"Apply step failed: {e}"
        log.error("Apply error", error=err)
        state["errors"].append(err)
        state["stats"]["errors"] += 1

    return state


# ─── Node: Outreach ───────────────────────────────────────────────────────────

async def outreach_node(state: AgentState) -> AgentState:
    """Find hiring managers and draft cold emails for applied jobs."""
    if state["status"] == "paused":
        return state

    applied = state.get("jobs_applied", [])
    if not applied:
        return state

    log.info("Starting outreach", user_id=state["user_id"], jobs=len(applied))
    await _broadcast(state["user_id"], "agent_action", {
        "action": "outreach_starting",
        "message": f"Finding hiring managers for {len(applied)} applications...",
    })

    try:
        from app.agents.outreach_agent import OutreachAgent
        outreach_agent = OutreachAgent(
            user_id=state["user_id"],
            preferences=state["preferences"],
            resume_content=state["resume_content"],
        )
        contacts = await outreach_agent.find_and_draft(applied)
        state["contacts_found"] = contacts
        state["stats"]["emails_drafted"] = len(contacts)
        await _broadcast(state["user_id"], "outreach_complete", {
            "contacts_found": len(contacts),
        })
    except Exception as e:
        err = f"Outreach failed: {e}"
        log.error("Outreach error", error=err)
        state["errors"].append(err)
        state["stats"]["errors"] += 1

    return state


# ─── Node: Follow-Up ─────────────────────────────────────────────────────────

async def follow_up_node(state: AgentState) -> AgentState:
    """Schedule follow-up email sequences for pending applications."""
    log.info("Scheduling follow-ups", user_id=state["user_id"])
    await _broadcast(state["user_id"], "agent_action", {
        "action": "followup_scheduled",
        "message": "Scheduling follow-up sequences (day 3, 7, 14)...",
    })
    # TODO: integrate with Celery Beat scheduler
    return state


# ─── Conditional Edge: should continue? ──────────────────────────────────────

def should_continue(state: AgentState) -> str:
    if state["status"] == "paused":
        return "end"
    if state["stats"]["errors"] >= _MAX_ERRORS_BEFORE_PAUSE:
        log.warning("Too many errors, auto-pausing agent", errors=state["stats"]["errors"])
        state["status"] = "paused"
        return "end"
    if len(state.get("flags", [])) > 3:
        log.warning("Too many human flags, pausing", flags=len(state["flags"]))
        state["status"] = "paused"
        return "end"
    # Skip outreach if we have no applied jobs
    if not state.get("jobs_applied"):
        return "end"
    return "outreach"


def has_jobs_to_screen(state: AgentState) -> str:
    return "screen" if state.get("jobs_found") else "end"


# ─── Graph Construction ───────────────────────────────────────────────────────

def build_agent_graph() -> StateGraph:
    """Construct the LangGraph agent workflow."""
    graph = StateGraph(AgentState)

    graph.add_node("scrape_jobs", scrape_jobs_node)
    graph.add_node("pre_screen", pre_screen_jobs_node)
    graph.add_node("apply_jobs", apply_jobs_node)
    graph.add_node("outreach", outreach_node)
    graph.add_node("follow_up", follow_up_node)

    graph.set_entry_point("scrape_jobs")
    graph.add_conditional_edges("scrape_jobs", has_jobs_to_screen, {
        "screen": "pre_screen",
        "end": END,
    })
    graph.add_edge("pre_screen", "apply_jobs")
    graph.add_conditional_edges("apply_jobs", should_continue, {
        "outreach": "outreach",
        "end": END,
    })
    graph.add_edge("outreach", "follow_up")
    graph.add_edge("follow_up", END)

    return graph.compile(checkpointer=MemorySaver())


# Singleton graph
agent_graph = build_agent_graph()


# ─── Entry Point ─────────────────────────────────────────────────────────────

async def run_orchestrator(
    user_id: str,
    run_id: str,
    preferences: dict,
    resume_content: str,
    proxy_config: dict,
    dry_run: bool = False,
) -> dict:
    """Entry point for the Celery task or direct invocation."""
    import time as _time

    stats = _empty_stats()
    stats["start_time"] = _time.time()

    initial_state = AgentState(
        user_id=user_id,
        run_id=run_id,
        preferences=preferences,
        resume_content=resume_content,
        proxy_config=proxy_config,
        dry_run=dry_run,
        jobs_found=[],
        jobs_screened=[],
        jobs_applied=[],
        jobs_skipped=[],
        contacts_found=[],
        emails_drafted=[],
        flags=[],
        errors=[],
        status="running",
        current_platform=None,
        stats=stats,
    )

    config = {"configurable": {"thread_id": f"{user_id}_{run_id}"}}

    try:
        result = await agent_graph.ainvoke(initial_state, config)
        result["status"] = "completed" if not result.get("errors") else "completed_with_errors"
        log.info(
            "Orchestrator complete",
            user_id=user_id,
            run_id=run_id,
            stats=result.get("stats"),
        )
        return result
    except Exception as e:
        log.error("Orchestrator failed", error=str(e), user_id=user_id)
        return {**initial_state, "status": "failed", "errors": [str(e)]}
