from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response as FastResponse

from picoweb_core import dispatch, parse_request
from src.retail_demo_server import ROOT, RetailBridge, make_routes
from src.retail_voice_bridge import RetailBrowserVoiceBridge, retail_voice_settings_from_env
from src.retail_voice_tools import RetailVoiceToolContext, TOOL_DEFINITIONS


def create_app(library: Path | None = None, store: Path | None = None, seed: bool = True) -> FastAPI:
    bridge = RetailBridge(library or ROOT / "build" / "libpicostack_retail_demo.so", store or Path(tempfile.gettempdir()) / "picostack-retail-demo")
    if seed:
        bridge.ingest()
    routes = make_routes(bridge)
    tools = RetailVoiceToolContext(bridge)
    app = FastAPI(title="PicoStack Retail Voice Demo")

    @app.get("/api/retail/voice/config")
    async def voice_config() -> dict[str, Any]:
        return {
            "enabled": retail_voice_settings_from_env() is not None,
            "websocket": "/ws/browser-voice",
            "tools": TOOL_DEFINITIONS,
        }

    @app.websocket("/ws/browser-voice")
    async def browser_voice(websocket: WebSocket) -> None:
        settings = retail_voice_settings_from_env()
        await websocket.accept()
        if settings is None:
            await websocket.send_text(json.dumps({"type": "error", "error": "Set VOICE_LIVE_ENDPOINT and credentials to enable retail voice."}))
            await websocket.close(code=1011)
            return
        bridge_runner = RetailBrowserVoiceBridge(websocket, settings, tools)
        try:
            await bridge_runner.run()
        except WebSocketDisconnect:
            return
        except Exception as exc:
            await websocket.send_text(json.dumps({"type": "error", "error": str(exc)}))
            await websocket.close(code=1011)

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "HEAD"])
    async def pico_dispatch(path: str, request: Request) -> FastResponse:
        body = await request.body()
        raw_path = "/" + path
        if request.url.query:
            raw_path += "?" + request.url.query
        pico_request = parse_request(request.method, raw_path, dict(request.headers), body)
        pico_response = dispatch(routes, pico_request)
        return FastResponse(
            content=pico_response.body,
            status_code=pico_response.status,
            media_type=pico_response.content_type,
            headers={k: v for k, v in pico_response.headers.items() if k.lower() != "content-type"},
        )

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="PicoStack retail ASGI + Voice Live demo")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--library", type=Path, default=ROOT / "build" / "libpicostack_retail_demo.so")
    parser.add_argument("--store", type=Path, default=Path(tempfile.gettempdir()) / "picostack-retail-demo")
    parser.add_argument("--no-seed", action="store_true")
    args = parser.parse_args()

    import uvicorn

    uvicorn.run(create_app(args.library, args.store, seed=not args.no_seed), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
