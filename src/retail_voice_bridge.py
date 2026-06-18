from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from starlette.websockets import WebSocket

from src.retail_voice_tools import TOOL_DEFINITIONS, RetailVoiceToolContext

logger = logging.getLogger("picostack.retail.voice")

BRITISH_VOICES = [
    "en-GB-SoniaNeural",
    "en-GB-RyanNeural",
    "en-GB-LibbyNeural",
    "en-GB-AbbiNeural",
]


def load_dotenv(path: Path | str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        clean_value = value.strip().strip('"').strip("'")
        if "VOICE_LIVE_" in clean_value or "PUBLIC_HOST=" in clean_value or "APP_PORT=" in clean_value:
            continue
        os.environ.setdefault(key.strip(), clean_value)


@dataclass(frozen=True)
class RetailVoiceSettings:
    voice_live_endpoint: str
    voice_live_api_key: str | None = None
    voice_live_model: str = "gpt-realtime-mini"

    @property
    def voice_live_ws_url(self) -> str:
        base = self.voice_live_endpoint.rstrip("/")
        if base.startswith("https://"):
            ws_base = "wss://" + base.removeprefix("https://")
        elif base.startswith("http://"):
            ws_base = "ws://" + base.removeprefix("http://")
        else:
            ws_base = base
        return f"{ws_base}/voice-live/realtime?api-version=2026-04-10&model={self.voice_live_model}"


def retail_voice_settings_from_env() -> RetailVoiceSettings | None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    endpoint = os.getenv("VOICE_LIVE_ENDPOINT")
    if not endpoint:
        return None
    return RetailVoiceSettings(
        voice_live_endpoint=endpoint,
        voice_live_api_key=os.getenv("VOICE_LIVE_API_KEY"),
        voice_live_model=os.getenv("VOICE_LIVE_MODEL", "gpt-realtime-mini"),
    )


class RetailBrowserVoiceBridge:
    def __init__(self, browser_websocket: WebSocket, settings: RetailVoiceSettings, tools: RetailVoiceToolContext):
        self.browser_websocket = browser_websocket
        self.settings = settings
        self.tools = tools
        self.voice_live = None
        self.credential = None
        self.completed_tool_calls: set[str] = set()
        self.session_voice = random.choice(BRITISH_VOICES)
        self.demo_context = ""

    async def run(self) -> None:
        headers = await self._auth_headers()
        self.voice_live = await self._connect_voice_live(headers)
        await self._configure_session()
        await self._safe_browser_send({"type": "event", "event": "voice.selected", "voice": self.session_voice})

        try:
            browser_task = asyncio.create_task(self._browser_to_voice_live())
            voice_task = asyncio.create_task(self._voice_live_to_browser())
            done, pending = await asyncio.wait({browser_task, voice_task}, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                exc = None if task.cancelled() else task.exception()
                if exc:
                    logger.exception("Retail voice bridge failed", exc_info=exc)
                    await self._safe_browser_send({"type": "error", "error": str(exc)})
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
        finally:
            if self.voice_live:
                await self.voice_live.close()
            if self.credential:
                await self.credential.close()

    async def _auth_headers(self) -> dict[str, str]:
        if self.settings.voice_live_api_key:
            return {"api-key": self.settings.voice_live_api_key}
        from azure.identity.aio import DefaultAzureCredential

        self.credential = DefaultAzureCredential()
        token = await self.credential.get_token("https://ai.azure.com/.default")
        return {"Authorization": f"Bearer {token.token}"}

    async def _connect_voice_live(self, headers: dict[str, str]):
        import websockets

        try:
            return await websockets.connect(
                self.settings.voice_live_ws_url,
                additional_headers=headers,
                max_size=None,
                ping_interval=20,
                ping_timeout=20,
            )
        except TypeError:
            return await websockets.connect(
                self.settings.voice_live_ws_url,
                extra_headers=headers,
                max_size=None,
                ping_interval=20,
                ping_timeout=20,
            )

    async def _send_voice_live(self, payload: dict[str, Any]) -> None:
        await self.voice_live.send(json.dumps(payload))

    async def _browser_to_voice_live(self) -> None:
        while True:
            raw = await self.browser_websocket.receive_text()
            message = json.loads(raw)
            message_type = message.get("type")

            if message_type == "input_audio":
                chunk = message.get("audio")
                if chunk and _is_base64_audio(chunk):
                    await self._send_voice_live({"type": "input_audio_buffer.append", "audio": chunk})
                continue

            if message_type == "context_update":
                self.demo_context = str(message.get("context") or "").strip()
                await self._configure_session()
                await self._safe_browser_send({"type": "event", "event": "context.updated"})
                continue

            if message_type == "greeting":
                greeting = str(message.get("text") or "").strip()
                if greeting:
                    await self._send_voice_live(
                        {
                            "type": "conversation.item.create",
                            "item": {
                                "type": "message",
                                "role": "user",
                                "content": [
                                    {
                                        "type": "input_text",
                                        "text": (
                                            "Use the following as your opening greeting. "
                                            "Speak it naturally and do not mention the control panel: "
                                            f"{greeting}"
                                        ),
                                    }
                                ],
                            },
                        }
                    )
                    await self._send_voice_live({"type": "response.create"})
                continue

            if message_type == "text":
                text = str(message.get("text") or "").strip()
                if text:
                    await self._send_voice_live(
                        {
                            "type": "conversation.item.create",
                            "item": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": text}]},
                        }
                    )
                    await self._send_voice_live({"type": "response.create"})

    async def _configure_session(self) -> None:
        products = self.tools.bridge.products()
        instructions = (
            "You are a concise British retail voice concierge for the Pico Outfitters demo store.\n"
            "You can help callers find items, order items, check shipping status, and check stock.\n"
            "Use tools whenever the caller asks for product search, stock, orders or shipping.\n"
            "This is a demo: do not claim payment has been taken and do not collect real card details.\n"
            "If the caller asks for a person, explain that the store can request a callback using the Call me panel.\n"
            f"Current catalog snapshot: {json.dumps(products)[:3500]}"
        )
        if self.demo_context:
            instructions += f"\nPresenter supplied context:\n{self.demo_context}"
        await self._send_voice_live(
            {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": instructions,
                    "input_audio_sampling_rate": 24000,
                    "input_audio_transcription": {"model": "azure-speech", "language": "en-GB"},
                    "turn_detection": {
                        "type": "azure_semantic_vad",
                        "silence_duration_ms": 500,
                        "interrupt_response": True,
                    },
                    "input_audio_noise_reduction": {"type": "azure_deep_noise_suppression"},
                    "tools": TOOL_DEFINITIONS,
                    "tool_choice": "auto",
                    "voice": {"name": self.session_voice, "type": "azure-standard"},
                },
            }
        )

    async def _voice_live_to_browser(self) -> None:
        async for raw in self.voice_live:
            event = json.loads(raw)
            event_type = event.get("type", "")
            if event_type.endswith("audio.delta"):
                delta = event.get("delta")
                if delta:
                    await self._safe_browser_send({"type": "audio", "audio": delta})
                continue
            if await self._handle_tool_call_event(event):
                await self._safe_browser_send({"type": "tool_call", "name": event.get("name") or (event.get("item") or {}).get("name")})
                continue
            if event_type.endswith("audio_transcript.delta"):
                delta = event.get("delta")
                if delta:
                    await self._safe_browser_send({"type": "transcript_delta", "text": delta})
                continue
            if event_type in {"response.done", "session.updated", "session.created"}:
                await self._safe_browser_send({"type": "event", "event": event_type})
            if event_type == "error":
                await self._safe_browser_send({"type": "error", "error": event})

    async def _handle_tool_call_event(self, event: dict[str, Any]) -> bool:
        event_type = event.get("type", "")
        call_id = event.get("call_id")
        name = event.get("name")
        arguments = event.get("arguments")
        item = event.get("item") or {}
        if item.get("type") == "function_call":
            call_id = call_id or item.get("call_id")
            name = name or item.get("name")
            arguments = arguments or item.get("arguments")
        if event_type not in {"response.function_call_arguments.done", "response.output_item.done"}:
            return False
        if not call_id or not name:
            return False
        if call_id in self.completed_tool_calls:
            return True
        self.completed_tool_calls.add(call_id)
        try:
            parsed_arguments = json.loads(arguments or "{}")
            result = self.tools.call_tool(name, parsed_arguments)
        except Exception as exc:
            result = {"error": str(exc)}
        await self._send_voice_live(
            {"type": "conversation.item.create", "item": {"type": "function_call_output", "call_id": call_id, "output": json.dumps(result)}}
        )
        await self._send_voice_live({"type": "response.create"})
        return True

    async def _safe_browser_send(self, payload: dict[str, Any]) -> None:
        try:
            await self.browser_websocket.send_text(json.dumps(payload))
        except Exception:
            logger.debug("Could not send retail voice payload", exc_info=True)


def _is_base64_audio(value: str) -> bool:
    try:
        base64.b64decode(value, validate=True)
        return True
    except Exception:
        return False
