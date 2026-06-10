# Agent HQ — Claude Code Instructions

## What this project is
A reusable multi-agent AI framework powered by CrewAI and Claude.
Four agents: dev, marketing, business, research.
FastAPI backend + web UI to chat with any agent.

## Environment variables
Add these to your `.env` file:

| Variable            | Required | Description                                      |
|---------------------|----------|--------------------------------------------------|
| `ANTHROPIC_API_KEY` | Yes      | Your Anthropic API key                           |
| `GITHUB_TOKEN`      | Yes*     | GitHub personal access token with `repo` scope. Required for Dev agent GitHub tools (read, write, push). |

## Running the server
cd C:\Users\zzac0\AI-Agents
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn api:app --reload

Then open http://localhost:8000

## Adding a new project
1. Create context/myapp.py with MYAPP_CONTEXT = "..."
2. In crew.py add to CONTEXT_MAP: "myapp": MYAPP_CONTEXT
3. Shows up automatically in the UI

## Adding a new agent
1. Create agents/newrole_agent.py
2. In crew.py add to AGENT_MAP
3. In ui/index.html add to agentLabels
