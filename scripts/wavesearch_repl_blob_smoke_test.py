#!/usr/bin/env python3
"""Focused smoke test for wavesearch_repl.py's blob-replication path in
isolation from wavesearch_api's full auth/search stack: builds two
minimal FastAPI apps directly on top of wavesearch_repl's primitives
(no wavesearch_api import, no bearer-token auth needed), confirms a
blob written on the writer propagates to the replica's own local
store and triggers its reload callback.
"""
from __future__ import annotations

import json
import shutil
import sys
import threading
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from retail_v2.blob_store import LocalBlobStore  # noqa: E402
from wavesearch_api.wavesearch_repl import (  # noqa: E402
    ReplConfig,
    build_repl_router,
    record_blob_write,
    repl_init,
    start_background_tasks,
    stop_background_tasks,
)

TRACKED = ["cache/rules.json"]
NODE_A = "127.0.0.1:9301"
NODE_B = "127.0.0.1:9302"
TOKEN = "smoke-test-token"


def make_app(node_id: str, store_dir: Path, reload_counter: dict) -> tuple[FastAPI, object]:
    store = LocalBlobStore(store_dir)

    async def reload_cb() -> None:
        reload_counter["n"] += 1

    cfg = ReplConfig(
        node_id=node_id,
        followers=[NODE_A, NODE_B],
        write_token=TOKEN,
        tracked_blobs=TRACKED,
        store=store,
        reload_callback=reload_cb,
    )
    state = repl_init(cfg)
    app = FastAPI()
    app.include_router(build_repl_router(state))

    @app.on_event("startup")
    async def _startup() -> None:
        start_background_tasks(state)

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        await stop_background_tasks(state)

    return app, state


def run_uvicorn(app: FastAPI, port: int) -> uvicorn.Server:
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return server


def main() -> int:
    dir_a = Path("/tmp/wavesearch-repl-blob-a")
    dir_b = Path("/tmp/wavesearch-repl-blob-b")
    shutil.rmtree(dir_a, ignore_errors=True)
    shutil.rmtree(dir_b, ignore_errors=True)

    reload_a: dict = {"n": 0}
    reload_b: dict = {"n": 0}
    app_a, state_a = make_app(NODE_A, dir_a, reload_a)
    app_b, state_b = make_app(NODE_B, dir_b, reload_b)

    server_a = run_uvicorn(app_a, 9301)
    server_b = run_uvicorn(app_b, 9302)
    time.sleep(2)

    try:
        # Wait for gossip to elect a writer between the two in-process nodes.
        writer_state = None
        for _ in range(20):
            time.sleep(1)
            if state_a.role == "writer":
                writer_state, replica_state = state_a, state_b
                break
            if state_b.role == "writer":
                writer_state, replica_state = state_b, state_a
                break
        if not writer_state:
            print(f"FAIL: no writer elected. a.role={state_a.role} b.role={state_b.role}")
            return 1
        print(f"PASS: writer elected ({writer_state.cfg.node_id})")

        # Write a tracked blob into the writer's own local store + bump its generation
        # (record_blob_write is exactly what app.py's _save_json_blob calls after every write).
        payload = json.dumps({"tenant-a": {"rule-1": {"id": "rule-1", "boost": 5}}})
        writer_state.cfg.store.write_text("cache/rules.json", payload)
        record_blob_write(writer_state, "cache/rules.json", payload)
        print(f"Wrote tracked blob on writer, generation now {writer_state.generation}")

        # Wait for the replica to pick it up.
        replica_reload_counter = reload_a if replica_state is state_a else reload_b
        replicated = False
        for _ in range(15):
            time.sleep(1)
            replica_path = Path(replica_state.cfg.store.root) / "cache" / "rules.json"
            if replica_path.exists() and replica_path.read_text(encoding="utf-8") == payload:
                replicated = True
                break
        if not replicated:
            print(f"FAIL: replica ({replica_state.cfg.node_id}) never received the blob within 15s")
            return 1
        print(f"PASS: replica ({replica_state.cfg.node_id}) received the exact blob content")

        if replica_reload_counter["n"] < 1:
            print("FAIL: replica's reload_callback was never invoked after applying the replicated blob")
            return 1
        print(f"PASS: replica's reload_callback invoked ({replica_reload_counter['n']} time(s))")

        print("ALL PASS: wavesearch_repl blob replication works end-to-end")
        return 0
    finally:
        server_a.should_exit = True
        server_b.should_exit = True
        time.sleep(1)


if __name__ == "__main__":
    raise SystemExit(main())
