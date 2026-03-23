import asyncio
import json
import os
import threading
from typing import AsyncGenerator, List

import groq
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent.loop_controller import AgentLoopController
from agent.evaluator import Evaluator

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
MODEL = "llama-3.3-70b-versatile"

app = FastAPI(title="Self-Improving Coding Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://swarna7414.github.io",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

evaluator = Evaluator()


class AgentRequest(BaseModel):
    task: str
    test_cases: str = ""
    max_iterations: int = 5
    timeout: int = 10


async def _agent_event_stream(req: AgentRequest) -> AsyncGenerator[str, None]:
    q: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def _run_agent():
        try:
            controller = AgentLoopController(GROQ_API_KEY, MODEL)
            for event in controller.run(
                req.task, req.test_cases, req.max_iterations, req.timeout
            ):
                safe = _make_serialisable(event)
                loop.call_soon_threadsafe(q.put_nowait, safe)
        except Exception as exc:
            loop.call_soon_threadsafe(
                q.put_nowait,
                {"type": "failed", "message": str(exc), "timestamp": ""},
            )
        finally:
            loop.call_soon_threadsafe(q.put_nowait, None)

    thread = threading.Thread(target=_run_agent, daemon=True)
    thread.start()

    while True:
        event = await q.get()
        if event is None:
            break
        yield f"data: {json.dumps(event)}\n\n"

    yield "data: {\"type\": \"done\"}\n\n"


def _make_serialisable(obj):
    if isinstance(obj, dict):
        return {k: _make_serialisable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_serialisable(i) for i in obj]
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return str(obj)


@app.get("/")
def root():
    return {"status": "ok", "model": MODEL}


@app.get("/health")
def health():
    groq_configured = bool(GROQ_API_KEY)
    return {
        "status": "ok" if groq_configured else "degraded",
        "model": MODEL,
        "groq_configured": groq_configured,
    }


@app.post("/api/run-agent")
async def run_agent(req: AgentRequest):
    return StreamingResponse(
        _agent_event_stream(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/evaluate")
async def evaluate(session: dict):
    metrics = evaluator.compute_metrics(session)
    return metrics


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    mode: str = "fix"
    history: List[ChatMessage] = []


class FixCodeRequest(BaseModel):
    code: str
    language: str = "auto"


SYSTEM_PROMPTS = {
    "fix": (
        "You are an expert software engineer and code debugger. "
        "When the user shares broken or buggy code, carefully analyze it, "
        "explain what is wrong in plain language, and provide the corrected "
        "working code with clear explanations. Format code blocks with markdown."
    ),
    "learn": (
        "You are a patient and expert programming teacher. "
        "Explain concepts clearly with examples, break down complex topics "
        "into simple steps, and adapt your explanations so the user truly "
        "understands. Format code examples with markdown code blocks."
    ),
}

FIX_CODE_SYSTEM = """You are an expert code analyst, debugger, and software engineer.

When given code, follow these exact steps:

STEP 1 — Error Detection:
Carefully scan for ALL of the following:
- Syntax errors
- Runtime errors and exceptions
- Logic bugs and incorrect behaviour
- Security vulnerabilities
- Bad practices or deprecated usage

STEP 2 — Respond based on what you find:

If errors ARE found:
- Start with a short summary: "Found X issue(s) in your code."
- List each issue with: type, location (line number if possible), and a plain-language description
- Provide the COMPLETE fixed code in a properly labelled code block
- Below the fixed code, briefly explain every change made

If NO errors are found:
- Start with: "No errors found. Your code looks correct."
- Then write: "Would you like me to optimize this to industry standards? I can improve readability, performance, naming conventions, and apply best practices."
- Do NOT add unsolicited changes — wait for the user to confirm.

Always be specific, practical, and concise. Format all code with markdown code blocks and include the language label."""


async def _chat_stream(req: ChatRequest) -> AsyncGenerator[str, None]:
    client = groq.Groq(api_key=GROQ_API_KEY)
    system = SYSTEM_PROMPTS.get(req.mode, SYSTEM_PROMPTS["fix"])

    messages = [{"role": "system", "content": system}]
    for h in req.history:
        messages.append({"role": h.role, "content": h.content})
    messages.append({"role": "user", "content": req.message})

    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            stream=True,
        )
        for chunk in completion:
            delta = chunk.choices[0].delta.content
            if delta:
                yield f"data: {json.dumps({'type': 'chunk', 'content': delta})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    except Exception as exc:
        yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"


EXPLAIN_CODE_SYSTEM = """You are an expert programming teacher and code explainer.

When given code, provide a thorough, beginner-friendly explanation structured as follows:

## Overview
A 2–3 sentence summary of what this code does and its overall purpose.

## Line-by-Line / Section-by-Section Breakdown
Walk through the code in logical chunks. For each chunk:
- Quote or reference the specific lines
- Explain exactly what it does in plain English
- Explain WHY it does it that way (the reasoning, not just the mechanics)

## Key Concepts Used
List and explain every concept, technique, or pattern used in the code (e.g. recursion, list comprehension, closures, REST, async/await, etc.). Assume the reader may not know these terms — explain each one clearly.

## How It All Flows Together
Describe the execution flow from start to finish — what happens first, what calls what, and how data moves through the code.

## Things Worth Noting
Point out anything clever, unusual, potentially confusing, or worth remembering about this code.

Be thorough but clear. Use simple language. Format code references with inline backticks."""

async def _fix_code_stream(req: FixCodeRequest) -> AsyncGenerator[str, None]:
    client = groq.Groq(api_key=GROQ_API_KEY)
    lang_hint = f" The code appears to be {req.language}." if req.language != "auto" else ""
    user_message = f"Please analyze and fix this code:{lang_hint}\n\n```\n{req.code}\n```"

    messages = [
        {"role": "system", "content": FIX_CODE_SYSTEM},
        {"role": "user", "content": user_message},
    ]
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            stream=True,
        )
        for chunk in completion:
            delta = chunk.choices[0].delta.content
            if delta:
                yield f"data: {json.dumps({'type': 'chunk', 'content': delta})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    except Exception as exc:
        yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"


async def _explain_code_stream(req: FixCodeRequest) -> AsyncGenerator[str, None]:
    client = groq.Groq(api_key=GROQ_API_KEY)
    lang_hint = f" The code is written in {req.language}." if req.language != "auto" else ""
    user_message = f"Please explain this code in full detail:{lang_hint}\n\n```\n{req.code}\n```"

    messages = [
        {"role": "system", "content": EXPLAIN_CODE_SYSTEM},
        {"role": "user", "content": user_message},
    ]
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            stream=True,
        )
        for chunk in completion:
            delta = chunk.choices[0].delta.content
            if delta:
                yield f"data: {json.dumps({'type': 'chunk', 'content': delta})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    except Exception as exc:
        yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"


@app.post("/api/explain-code")
async def explain_code(req: FixCodeRequest):
    return StreamingResponse(
        _explain_code_stream(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/fix-code")
async def fix_code(req: FixCodeRequest):
    return StreamingResponse(
        _fix_code_stream(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/chat")
async def chat(req: ChatRequest):
    return StreamingResponse(
        _chat_stream(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=7860)
