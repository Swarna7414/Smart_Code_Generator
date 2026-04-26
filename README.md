---
title: Smart Code Generator
emoji: ""
sdk: docker
sdk_version: "latest"
app_file: app.py
pinned: false
---

# Smart Code Generator Backend

<div align="center">

![Title](https://img.shields.io/badge/Smart_Code_Generator-blue?style=for-the-badge)
![SDK](https://img.shields.io/badge/SDK-Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Port](https://img.shields.io/badge/App_Port-7860-indigo?style=for-the-badge)
![Model](https://img.shields.io/badge/Model-LLaMA_3.3_70B-blueviolet?style=for-the-badge)
![Framework](https://img.shields.io/badge/Framework-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)

</div>
---

This is the backend for the Smart Code Generator project. It is built with FastAPI and uses the Groq API to run LLaMA 3.3 70B. The idea is straightforward you describe a coding task in plain English, the system writes the code, runs it, checks if it works, and if it does not, it reads the error and tries again. It keeps doing this until the code passes or it runs out of attempts. Alongside the agent loop, it also handles code fixing, code explanation, and a conversational chat assistant, all streamed back to the client in real time.

---

## Table of Contents

- [What it does](#what-it-does)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Running the Server](#running-the-server)
- [API Reference](#api-reference)
  - [GET /](#get-)
  - [POST /api/run-agent](#post-apirun-agent)
  - [POST /api/evaluate](#post-apievaluate)
  - [POST /api/fix-code](#post-apifix-code)
  - [POST /api/explain-code](#post-apiexplain-code)
  - [POST /api/chat](#post-apichat)
- [How the Agent Works](#how-the-agent-works)
- [Streaming Events](#streaming-events)

---

## What it does

The backend is designed around a few core ideas.

The main one is the self-improving agent loop. When you send it a task, it classifies what kind of task it is, generates Python code using the language model, actually executes that code on the server, and checks the result. If the code fails, it reads the error, sends everything back to the model for reflection, and generates a fixed version. This cycle repeats until the code works or the iteration limit is reached.

For tasks that involve multiple programming languages or comparisons  things like "compare sorting in Python and Java"  it switches to analysis mode instead. In that mode, it generates a structured response with working code examples in each language, a comparison, and a recommendation, without trying to execute anything.

The other endpoints handle more focused jobs. The code fixer takes broken code, scans it for bugs and issues, and returns a corrected version with explanations. The code explainer walks through any snippet in plain language, covering what each part does, how data flows through it, and what concepts are at play. The chat assistant lets you have a back-and-forth conversation either in a debugging mode or a teaching mode.

All of these stream their responses back to the client using Server-Sent Events, so you see output as it arrives rather than waiting for everything to finish.

---

## Project Structure

```
Backend/
├── main.py                      Entry point. Defines all API routes.
├── requirements.txt             Python dependencies.
├── Dockerfile                   Container setup for Hugging Face Spaces.
└── agent/
    ├── loop_controller.py       Runs the full agent loop from start to finish.
    ├── code_generator.py        Asks the LLM to write the initial code.
    ├── code_executor.py         Runs the code in a subprocess and captures output.
    ├── reflection.py            Sends errors back to the LLM and gets a fix.
    ├── error_parser.py          Reads stderr and stdout and extracts error details.
    ├── task_classifier.py       Decides whether a task needs execution or analysis.
    ├── multi_language_agent.py  Handles multi-language and comparison tasks.
    └── evaluator.py             Calculates performance metrics for a session.
```

---

## Requirements

You need Python 3.11 or higher and a Groq API key. You can get one at https://console.groq.com.

---

## Getting Started

Navigate to the Backend folder and set up a virtual environment.

```bash
cd Backend

python -m venv venv

# Windows
venv\Scripts\activate

# macOS and Linux
source venv/bin/activate

pip install -r requirements.txt
```

---

## Environment Variables

The server reads one required environment variable.

| Variable       | Description                                    |
|----------------|------------------------------------------------|
| `GROQ_API_KEY` | Your Groq API key. The server will not work without it. |

Set it before starting the server.

```bash
# Windows PowerShell
$env:GROQ_API_KEY = "your_api_key_here"

# macOS and Linux
export GROQ_API_KEY="your_api_key_here"
```

---

## Running the Server

```bash
python main.py
```

The server starts on port 7860. You can also start it directly with uvicorn.

```bash
uvicorn main:app --host 0.0.0.0 --port 7860
```

Once it is running, the interactive API docs are available at http://localhost:7860/docs.

---

## API Reference

### GET /

A simple health check. Returns the current status and model name.

```json
{ "status": "ok", "model": "llama-3.3-70b-versatile" }
```

---

### POST /api/run-agent

This is the main endpoint. It runs the self-improving agent loop and streams progress back as Server-Sent Events.

```json
{
  "task": "Write a function that returns the nth Fibonacci number",
  "test_cases": "assert fib(1) == 1\nassert fib(10) == 55",
  "max_iterations": 5,
  "timeout": 10
}
```

| Field          | Type   | Required | Description |
|----------------|--------|----------|-------------|
| task           | string | Yes      | What you want the agent to build, in plain English. |
| test_cases     | string | No       | Python assertions that will be appended to the generated code and run alongside it. |
| max_iterations | int    | No       | How many attempts the agent gets before giving up. Defaults to 5. |
| timeout        | int    | No       | How many seconds each code execution is allowed to run. Defaults to 10. |

The response is an SSE stream. See the Streaming Events section for details on what events are sent.

---

### POST /api/evaluate

Once an agent session is complete, you can send the session data here to get performance metrics back.

Send the full session object from the `complete` event. The response looks like this.

```json
{
  "total_iterations": 3,
  "success": true,
  "total_time_s": 12.4,
  "avg_exec_time_s": 0.312,
  "error_types": ["SyntaxError", "NameError"],
  "error_distribution": { "SyntaxError": 1, "NameError": 1 },
  "code_lengths": [12, 15, 15],
  "iterations_to_success": 3
}
```

---

### POST /api/fix-code

Send any code and an optional language hint. The model will scan it for bugs, explain what is wrong, and return the corrected version. Streams as SSE chunks.

```json
{
  "code": "def add(a, b)\n  return a + b",
  "language": "python"
}
```

| Field    | Type   | Required | Description |
|----------|--------|----------|-------------|
| code     | string | Yes      | The code you want analyzed and fixed. |
| language | string | No       | A hint for which language it is. Defaults to auto-detection. |

---

### POST /api/explain-code

Send any code snippet and get back a detailed, plain-language explanation. Streams as SSE chunks.

```json
{
  "code": "result = [x**2 for x in range(10) if x % 2 == 0]",
  "language": "python"
}
```

The explanation covers what the code does overall, a section-by-section breakdown, the key concepts it uses, how data flows through it, and anything worth noting.

---

### POST /api/chat

A conversational endpoint that supports full message history. Streams as SSE chunks.

```json
{
  "message": "Why does my list comprehension throw a TypeError?",
  "mode": "fix",
  "history": [
    { "role": "user", "content": "Hello!" },
    { "role": "assistant", "content": "Hi, how can I help?" }
  ]
}
```

| Field   | Type   | Required | Description |
|---------|--------|----------|-------------|
| message | string | Yes      | Your latest message. |
| mode    | string | No       | Use `fix` for debugging help or `learn` for explanations and teaching. Defaults to `fix`. |
| history | array  | No       | The conversation so far, as a list of role and content pairs. |

---

## How the Agent Works

When a request comes in to `/api/run-agent`, the first thing the system does is classify the task. It reads the description and looks for language names, framework names, and comparison keywords. If the task is straightforward Python, it goes into execute mode. If it involves multiple languages or asks for comparisons, it goes into analyze mode.

In execute mode, the agent generates an initial solution using the language model, then runs it in a temporary subprocess. If the code passes, it sends a success event and stops. If it fails, it reads the error, sends the broken code and the error details back to the model, and asks for a corrected version. This loop continues until the code works or the maximum number of iterations is reached.

In analyze mode, the agent makes a single call to the language model and asks for a structured JSON response containing code in each relevant language, comparisons between them, difficulty ratings, and a recommendation. Nothing gets executed in this mode.

The threading setup is worth mentioning. Because the agent loop runs synchronously and FastAPI is async, the loop runs in a background thread. It puts events into a queue, and the async route handler reads from that queue and streams them to the client. This keeps the server responsive while the agent is working.

---

## Streaming Events

Every streaming endpoint sends events in this format.

```
data: {"type": "event_type", "message": "a human-readable description", "timestamp": "HH:MM:SS"}
```

| Event Type    | When it is sent |
|---------------|-----------------|
| start         | The agent loop has begun. |
| classifying   | The system is reading the task to determine its type. |
| classified    | Classification is done. Includes the mode and detected languages. |
| generating    | The language model is writing the initial code. |
| code_ready    | The initial code is ready. |
| executing     | The code is being run in a subprocess. |
| success       | The code passed on this iteration. |
| error         | Execution failed. Includes the error type, message, and traceback. |
| reflecting    | The error has been sent back to the model for a fix. |
| refined       | A new version of the code has been generated. |
| analyzing     | The system is generating a multi-language analysis. |
| analysis_ready | The analysis is complete and ready to display. |
| complete      | The session has ended. Includes the final code, all iterations, and whether it succeeded. |
| failed        | Something went wrong and the session could not continue. |
| chunk         | A piece of streamed text from the chat, fix, or explain endpoints. |
| done          | The stream is closed. |
