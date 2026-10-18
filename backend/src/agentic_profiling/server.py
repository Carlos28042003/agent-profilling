"""Local web interface: serves the results page (docs/) and runs the agent live.

    agentic-ui            # opens http://localhost:8000

The page's "Ask" tab only works while this API is running; on GitHub Pages
(static) the page shows the results only.
"""

import argparse
import json
import queue
import re
import threading
import webbrowser
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import llm_from_config, run_meta
from .agent import run_task

ROOT = Path(__file__).resolve().parents[2]  # backend/
CONFIGS = ROOT / "configs"
DOCS = ROOT.parent / "docs"  # the built frontend (cd frontend && npm run build)
ASK_TRACES = ROOT / "traces" / "ask"

app = FastAPI(title="agentic-profiling")


def _configs() -> dict[str, dict]:
    return {p.stem: yaml.safe_load(p.read_text(encoding="utf-8")) for p in sorted(CONFIGS.glob("*.yaml"))}


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "configs": [{"name": n, "model": c["model"]} for n, c in _configs().items()]}


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.get("/api/ask")
def ask(question: str = Query(..., min_length=3, max_length=500),
        config: str = "ollama", max_steps: int = Query(8, ge=1, le=15)) -> StreamingResponse:
    cfgs = _configs()
    if config not in cfgs:
        raise HTTPException(404, f"config {config!r} does not exist")
    cfg = cfgs[config]
    events: queue.Queue = queue.Queue()

    def worker() -> None:
        try:
            trace = run_task(llm_from_config(cfg), "ask", question, max_steps=max_steps,
                             on_step=lambda step: events.put(("step", asdict(step))))
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            slug = re.sub(r"[^a-z0-9]+", "-", question.lower())[:40].strip("-")
            ASK_TRACES.mkdir(parents=True, exist_ok=True)
            path = ASK_TRACES / f"{stamp}-{slug}.json"
            record = {"meta": run_meta(cfg, "ui", stamp), **trace.to_dict()}
            path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
            events.put(("done", {"answer": trace.answer, "finished": trace.finished,
                                 "stop_reason": trace.stop_reason, "total_s": trace.total_s,
                                 "model": cfg["model"], "saved_to": str(path.relative_to(ROOT))}))
        except Exception as e:  # noqa: BLE001 — send the error to the browser instead of dropping the connection
            events.put(("error", {"message": f"{type(e).__name__}: {e}"}))

    threading.Thread(target=worker, daemon=True).start()

    def stream():
        yield _sse("start", {"question": question, "model": cfg["model"]})
        while True:
            kind, data = events.get()
            yield _sse(kind, data)
            if kind in ("done", "error"):
                break

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache"})


if (DOCS / "index.html").exists():
    app.mount("/", StaticFiles(directory=DOCS, html=True), name="docs")
else:
    @app.get("/")
    def no_frontend() -> dict:
        return {"error": "frontend not built", "fix": "cd frontend && npm install && npm run build"}


def main() -> None:
    import uvicorn

    p = argparse.ArgumentParser(prog="agentic-ui")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--no-browser", action="store_true")
    args = p.parse_args()
    if not args.no_browser:
        threading.Timer(1.5, webbrowser.open, [f"http://localhost:{args.port}"]).start()
    uvicorn.run(app, host="127.0.0.1", port=args.port)
