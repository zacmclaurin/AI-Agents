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

class ChatRequest(BaseModel):
    agent: str
    message: str
    project: str = "ironroad"

class ChatResponse(BaseModel):
    response: str
    agent: str
    project: str

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
    result = run_agent(
        agent_type=req.agent,
        message=req.message,
        project=req.project,
    )
    return ChatResponse(response=result, agent=req.agent, project=req.project)

@app.get("/health")
def health():
    return {"status": "ok", "key_loaded": bool(os.getenv("ANTHROPIC_API_KEY"))}
