from crewai import Task, Crew, Process, LLM
from agents.dev_agent import create_dev_agent
from agents.marketing_agent import create_marketing_agent
from agents.business_agent import create_business_agent
from agents.research_agent import create_research_agent
from context.ironroad import IRONROAD_CONTEXT
from context.default import DEFAULT_CONTEXT

AGENT_MAP = {
    "dev": create_dev_agent,
    "marketing": create_marketing_agent,
    "business": create_business_agent,
    "research": create_research_agent,
}

CONTEXT_MAP = {
    "ironroad": IRONROAD_CONTEXT,
    "default": DEFAULT_CONTEXT,
}

claude_llm = LLM(model="claude-sonnet-4-5", max_tokens=4096)

def run_agent(agent_type: str, message: str, project: str = "ironroad") -> str:
    context = CONTEXT_MAP.get(project, DEFAULT_CONTEXT)
    create_agent = AGENT_MAP.get(agent_type)
    if not create_agent:
        return f"Unknown agent type: {agent_type}. Choose from: {list(AGENT_MAP.keys())}"

    agent = create_agent(context=context)
    agent.llm = claude_llm

    task = Task(
        description=message,
        expected_output="A thorough, actionable response.",
        agent=agent,
    )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )

    result = crew.kickoff()
    return str(result)
