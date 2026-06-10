import uuid
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

from crew import run_agent, AGENT_MAP, CONTEXT_MAP

app = FastAPI(title="AI Agents API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store: session_id -> list of {role, content} dicts
_sessions: dict[str, list[dict]] = {}


class ChatRequest(BaseModel):
    agent: str
    message: str
    project: str = "ironroad"
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    agent: str
    project: str
    session_id: str


@app.get("/")
def serve_ui():
    return FileResponse("ui/index.html")


@app.get("/agents")
def list_agents():
    return {"agents": list(AGENT_MAP.keys())}


@app.get("/projects")
def list_projects():
    return {"projects": list(CONTEXT_MAP.keys())}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    sid = req.session_id or str(uuid.uuid4())
    history = _sessions.get(sid, [])

    result = run_agent(
        agent_type=req.agent,
        message=req.message,
        project=req.project,
        history=history,
    )

    _sessions[sid] = history + [
        {"role": "user",      "content": req.message},
        {"role": "assistant", "content": result},
    ]

    return ChatResponse(response=result, agent=req.agent, project=req.project, session_id=sid)


@app.delete("/session/{session_id}")
def clear_session(session_id: str):
    _sessions.pop(session_id, None)
    return {"cleared": session_id}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "key_loaded": bool(os.getenv("ANTHROPIC_API_KEY")),
        "active_sessions": len(_sessions),
    }
