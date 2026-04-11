"""
Master Orchestrator Agent — LangGraph State Machine
Coordinates all sub-agents: scraping, applying, outreach, follow-up.
"""
from typing import TypedDict, Annotated, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import structlog

from app.core.websocket_manager import ws_manager

log = structlog.get_logger()


class AgentState(TypedDict):
    user_id: str
    run_id: str
    preferences: dict
    resume_content: str
    proxy_config: dict
    jobs_found: list
    jobs_applied: list
    contacts_found: list
    emails_drafted: list
    flags: list
    errors: list
    status: str  # running | paused | completed
    current_platform: Optional[str]


async def scrape_jobs_node(state: AgentState) -> AgentState:
    """Discover job listings across connected platforms."""
    from app.browser.linkedin_agent import LinkedInAgent
    from app.browser.indeed_agent import IndeedAgent

    log.info("Scraping jobs", user_id=state["user_id"])
    await ws_manager.broadcast_agent_update(state["user_id"], "agent_action", {
        "action": "scraping_jobs",
        "message": "Searching for matching job listings...",
    })

    all_jobs = []

    # LinkedIn
    state["current_platform"] = "linkedin"
    agent = LinkedInAgent(
        user_id=state["user_id"],
        preferences=state["preferences"],
        resume_content=state["resume_content"],
        proxy_config=state["proxy_config"],
    )

    async def on_flag(flag_data):
        state["flags"].append(flag_data)
        await ws_manager.broadcast_agent_update(state["user_id"], "human_flag", flag_data)

    async def on_application(job):
        state["jobs_applied"].append(job)
        await ws_manager.broadcast_agent_update(state["user_id"], "application_submitted", job)

    results = await agent.run(callbacks={"on_flag": on_flag, "on_application": on_application})
    state["jobs_applied"] = results.get("applied_jobs", [])

    return state


async def outreach_node(state: AgentState) -> AgentState:
    """Find hiring managers and draft cold emails."""
    from app.agents.outreach_agent import OutreachAgent

    if state["status"] == "paused":
        return state

    log.info("Starting outreach", user_id=state["user_id"])
    await ws_manager.broadcast_agent_update(state["user_id"], "agent_action", {
        "action": "outreach_starting",
        "message": "Finding hiring managers and drafting emails...",
    })

    outreach_agent = OutreachAgent(
        user_id=state["user_id"],
        preferences=state["preferences"],
        resume_content=state["resume_content"],
    )
    contacts = await outreach_agent.find_and_draft(state["jobs_applied"])
    state["contacts_found"] = contacts

    return state


async def follow_up_node(state: AgentState) -> AgentState:
    """Schedule follow-up email sequences."""
    log.info("Scheduling follow-ups", user_id=state["user_id"])
    await ws_manager.broadcast_agent_update(state["user_id"], "agent_action", {
        "action": "followup_scheduled",
        "message": "Scheduling follow-up sequences (day 3, 7, 14)...",
    })
    return state


def should_continue(state: AgentState) -> str:
    if state["status"] == "paused":
        return "end"
    if len(state["flags"]) > 3:
        log.warning("Too many flags, pausing agent", flags=len(state["flags"]))
        state["status"] = "paused"
        return "end"
    return "outreach"


def build_agent_graph() -> StateGraph:
    """Construct the LangGraph agent workflow."""
    graph = StateGraph(AgentState)

    graph.add_node("scrape_jobs", scrape_jobs_node)
    graph.add_node("outreach", outreach_node)
    graph.add_node("follow_up", follow_up_node)

    graph.set_entry_point("scrape_jobs")
    graph.add_conditional_edges("scrape_jobs", should_continue, {
        "outreach": "outreach",
        "end": END,
    })
    graph.add_edge("outreach", "follow_up")
    graph.add_edge("follow_up", END)

    return graph.compile(checkpointer=MemorySaver())


# Singleton graph
agent_graph = build_agent_graph()


async def run_orchestrator(
    user_id: str,
    run_id: str,
    preferences: dict,
    resume_content: str,
    proxy_config: dict,
) -> dict:
    """Entry point for the Celery task."""
    initial_state = AgentState(
        user_id=user_id,
        run_id=run_id,
        preferences=preferences,
        resume_content=resume_content,
        proxy_config=proxy_config,
        jobs_found=[],
        jobs_applied=[],
        contacts_found=[],
        emails_drafted=[],
        flags=[],
        errors=[],
        status="running",
        current_platform=None,
    )

    config = {"configurable": {"thread_id": f"{user_id}_{run_id}"}}

    try:
        result = await agent_graph.ainvoke(initial_state, config)
        return result
    except Exception as e:
        log.error("Orchestrator failed", error=str(e), user_id=user_id)
        return {**initial_state, "status": "failed", "errors": [str(e)]}
