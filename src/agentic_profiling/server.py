"""API for the web UI (separate frontend repository): runs the agent live.

    agentic-ui                         # API + the built frontend, on http://localhost:8000
    agentic-ui --site PATH             # serve the frontend build from another folder
    agentic-ui --no-browser            # API only use, e.g. with the frontend's `npm run dev`

By default the built site is taken from the frontend repository next to this one
(../frontend/docs). Without it, only the API is served.
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

ROOT = Path(__file__).resolve().parents[2]  # repository root
CONFIGS = ROOT / "configs"
DEFAULT_SITE = ROOT.parent / "frontend" / "docs"  # the frontend repository, next to this one: npm run build
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


def mount_site(site: Path) -> bool:
    """Serve the built frontend at /, or a short help message if it is missing."""
    if (site / "index.html").exists():
        app.mount("/", StaticFiles(directory=site, html=True), name="site")
        return True

    @app.get("/")
    def no_frontend() -> dict:
        return {"api": "running", "site": f"not found at {site}",
                "fix": "build the frontend repository (npm install && npm run build) or pass --site PATH"}

    return False


def main() -> None:
    import uvicorn

    p = argparse.ArgumentParser(prog="agentic-ui")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--site", type=Path, default=DEFAULT_SITE, help="folder with the built frontend (index.html)")
    p.add_argument("--no-browser", action="store_true")
    args = p.parse_args()
    if mount_site(args.site.resolve()):
        print(f"Serving the frontend from {args.site.resolve()}")
    else:
        print(f"Frontend build not found at {args.site.resolve()}: serving the API only (/api/...)")
    if not args.no_browser:
        threading.Timer(1.5, webbrowser.open, [f"http://localhost:{args.port}"]).start()
    uvicorn.run(app, host="127.0.0.1", port=args.port)
