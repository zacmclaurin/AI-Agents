import asyncio
import threading
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

from crew import run_agent, AGENT_MAP, CONTEXT_MAP
import tools.memory_tools as memory

app = FastAPI(title="AI Agents API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_memory_available = bool(
    os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY")
)

# Fallback in-memory store used when Supabase env vars are absent
_sessions: dict[str, list[dict]] = {}

# Job store: job_id -> {status, result, error, agent, project, session_id}
_jobs: dict[str, dict] = {}


def _load_history(session_id: str) -> list[dict]:
    if _memory_available:
        return memory.load_history(session_id)
    return _sessions.get(session_id, [])


def _save_turn(session_id: str, agent_type: str, project: str, user_msg: str, assistant_msg: str) -> None:
    if _memory_available:
        memory.save_message(session_id, agent_type, project, "user",      user_msg)
        memory.save_message(session_id, agent_type, project, "assistant", assistant_msg)
    else:
        prev = _sessions.get(session_id, [])
        _sessions[session_id] = prev + [
            {"role": "user",      "content": user_msg},
            {"role": "assistant", "content": assistant_msg},
        ]


def _clear_session(session_id: str) -> None:
    if _memory_available:
        memory.clear_session(session_id)
    else:
        _sessions.pop(session_id, None)


def _run_job_sync(job_id: str, agent: str, message: str, project: str, sid: str) -> None:
    """Runs entirely in a worker thread: load history, run agent, save turn."""
    try:
        history = _load_history(sid)
    except Exception as e:
        print(f"[WARN] Failed to load history for job {job_id}: {e}")
        history = []

    try:
        result = run_agent(agent, message, project, history)
        _jobs[job_id]["status"] = "complete"
        _jobs[job_id]["result"] = result
    except Exception as e:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(e)
        print(f"[ERROR] Job {job_id} failed: {e}")
        return

    try:
        _save_turn(sid, agent, project, message, result)
    except Exception as e:
        print(f"[WARN] Failed to save turn for job {job_id}: {e}")


class GitHubWriteRequest(BaseModel):
    repo: str
    file_path: str
    content: str
    commit_message: str
    branch: str = "main"


class ChatRequest(BaseModel):
    agent: str
    message: str
    project: str = "ironroad"
    session_id: str | None = None


class ChatSubmitResponse(BaseModel):
    job_id: str
    session_id: str


class JobStatusResponse(BaseModel):
    status: str          # "pending" | "complete" | "error"
    result: str | None = None
    error: str | None = None
    agent: str | None = None
    project: str | None = None
    session_id: str | None = None


@app.get("/")
def serve_ui():
    return FileResponse("ui/index.html")


@app.get("/agents")
def list_agents():
    return {"agents": list(AGENT_MAP.keys())}


@app.get("/projects")
def list_projects():
    return {"projects": list(CONTEXT_MAP.keys())}


@app.post("/chat", response_model=ChatSubmitResponse)
def chat(req: ChatRequest):
    sid = req.session_id or str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    _jobs[job_id] = {
        "status":     "pending",
        "result":     None,
        "error":      None,
        "agent":      req.agent,
        "project":    req.project,
        "session_id": sid,
    }

    threading.Thread(
        target=_run_job_sync,
        args=(job_id, req.agent, req.message, req.project, sid),
        daemon=True,
    ).start()

    return ChatSubmitResponse(job_id=job_id, session_id=sid)


@app.get("/status/{job_id}", response_model=JobStatusResponse)
def get_status(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return JobStatusResponse(**job)


@app.delete("/session/{session_id}")
def clear_session(session_id: str):
    try:
        _clear_session(session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"cleared": session_id}


@app.post("/github")
def github_write(req: GitHubWriteRequest):
    """Write a file directly to GitHub, bypassing CrewAI entirely."""
    from tools.github_tools import github_write_file
    result = github_write_file(
        repo_name=req.repo,
        file_path=req.file_path,
        content=req.content,
        commit_message=req.commit_message,
        branch=req.branch,
    )
    if result.startswith("GitHub error") or result.startswith("Error"):
        raise HTTPException(status_code=500, detail=result)
    return {"result": result}


@app.get("/health")
def health():
    pending = sum(1 for j in _jobs.values() if j["status"] == "pending")
    return {
        "status":          "ok",
        "key_loaded":      bool(os.getenv("ANTHROPIC_API_KEY")),
        "memory_backend":  "supabase" if _memory_available else "in-memory",
        "pending_jobs":    pending,
        "total_jobs":      len(_jobs),
    }
