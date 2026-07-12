"""WaveStore voice orchestration: browser mic -> Azure Voice Live -> tool calls -> browser UI actions.

Design summary
--------------
The browser already owns the live shopper session (auth token, tenant, basket in
localStorage, browsing history). Rather than re-implement that state server-side,
the voice bridge is handed a compact "session key" snapshot when the websocket
connects (tenant, customerId, bearer token, current basket, recent browsing
history) and keeps it fresh via `context_update` messages sent whenever the
browser's own state changes.

Tool calls fall into two categories:
  * Read-only tools (search, recommend, offers, order history, invoices) call the
    existing `/v2/*` HTTP surface in-process using the browser's own bearer token,
    so results are consistent with what the shopper is already entitled to see.
  * State-mutating tools (add to basket, navigate, apply an offer) are relayed back
    to the browser as `ui_action` messages and executed by the browser's existing
    JS functions (`addToBasket`, `runSearch`, `applyOffer`, `checkout`, ...) so the
    live session updates exactly the way a click would have.
  * Checkout is a hybrid: the bridge calls the real `/erp/orders` endpoint itself
    (using the known basket from the session snapshot) so a genuine order is
    created, then tells the browser to clear its local basket and show the order.

Login is intentionally out of scope: the bridge never authenticates a user, it
only uses a bearer token the browser already obtained through the normal sign-in
flow.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import random
from dataclasses import dataclass, field
from typing import Any, Callable

from starlette.websockets import WebSocket, WebSocketDisconnect

logger = logging.getLogger("wavestore.voice")

BRITISH_VOICES = [
    "en-GB-SoniaNeural",
    "en-GB-RyanNeural",
    "en-GB-LibbyNeural",
    "en-GB-AbbiNeural",
]


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "search_catalog",
        "description": "Search the WaveStore catalog for matching products. Also updates the shopper's search box and results on screen.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search text, e.g. 'waterproof jacket'."},
                "category": {"type": "string", "description": "Optional category filter."},
                "brand": {"type": "string", "description": "Optional brand filter."},
                "availability": {"type": "string", "description": "Optional availability filter: IN_STOCK, LOW_STOCK, or OUT_OF_STOCK."},
            },
            "required": ["query"],
        },
    },
    {
        "type": "function",
        "name": "get_recommendations",
        "description": "Get related/recommended products, seeded from a product id or the shopper's recent browsing history if omitted. Also shows the recommendations on screen.",
        "parameters": {
            "type": "object",
            "properties": {
                "productId": {"type": "string", "description": "Seed product id. If omitted, uses the shopper's most recently viewed product."},
            },
        },
    },
    {
        "type": "function",
        "name": "get_offers",
        "description": "List current promotions and offers, and show the offers view on screen.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "get_basket",
        "description": "Read back what is currently in the shopper's basket (items, quantities, running total).",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "add_to_basket",
        "description": "Add a product to the shopper's basket.",
        "parameters": {
            "type": "object",
            "properties": {
                "productId": {"type": "string"},
                "query": {"type": "string", "description": "Alternative to productId: a search phrase identifying the product."},
                "quantity": {"type": "integer"},
            },
        },
    },
    {
        "type": "function",
        "name": "go_to_basket",
        "description": "Navigate the shopper's screen to the basket/cart view.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "checkout",
        "description": "Place an order for everything currently in the shopper's basket. This creates a real demo order.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "get_order_history",
        "description": "Look up the shopper's recent orders and show the account/order-history view on screen.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "get_invoices",
        "description": "Look up the shopper's invoices and show the account view on screen.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "navigate",
        "description": "Move the shopper's screen to a named view.",
        "parameters": {
            "type": "object",
            "properties": {
                "view": {"type": "string", "description": "One of: home, basket, account, search."},
            },
            "required": ["view"],
        },
    },
]


def load_dotenv(path: str = ".env") -> None:
    from pathlib import Path

    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class WaveVoiceSettings:
    voice_live_endpoint: str
    voice_live_api_key: str | None = None
    voice_live_model: str = "gpt-realtime-mini"
    # Voice-activity-detection tuning. Defaults lean towards noisy environments (open offices,
    # background conversations) to reduce false "the shopper started talking" interruptions:
    # a higher threshold requires clearer/louder speech, and a longer silence duration avoids
    # treating brief gaps or distant chatter as the end of a turn.
    vad_threshold: float = 0.7
    vad_silence_duration_ms: int = 500
    vad_prefix_padding_ms: int = 200
    # Deep noise suppression mode: "near_field" assumes a close mic (headset/lapel) with strong
    # voice vs. weak background noise and suppresses less aggressively; "far_field" assumes a
    # distant mic (laptop built-in, conference room) with relatively louder background noise
    # (including other people talking) and suppresses more aggressively. Default to far_field
    # since that is the common laptop-mic-in-a-noisy-room case.
    noise_reduction_mode: str = "far_field"

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


def wave_voice_settings_from_env() -> WaveVoiceSettings | None:
    load_dotenv()
    endpoint = os.environ.get("VOICE_LIVE_ENDPOINT")
    if not endpoint:
        return None

    def _float_env(name: str, default: float) -> float:
        try:
            return float(os.environ.get(name) or default)
        except (TypeError, ValueError):
            return default

    def _int_env(name: str, default: int) -> int:
        try:
            return int(os.environ.get(name) or default)
        except (TypeError, ValueError):
            return default

    return WaveVoiceSettings(
        voice_live_endpoint=endpoint,
        voice_live_api_key=os.environ.get("VOICE_LIVE_API_KEY"),
        voice_live_model=os.environ.get("VOICE_LIVE_MODEL", "gpt-realtime-mini"),
        vad_threshold=_float_env("VOICE_VAD_THRESHOLD", 0.7),
        vad_silence_duration_ms=_int_env("VOICE_VAD_SILENCE_MS", 500),
        vad_prefix_padding_ms=_int_env("VOICE_VAD_PREFIX_PADDING_MS", 200),
        noise_reduction_mode=str(os.environ.get("VOICE_NOISE_REDUCTION_MODE") or "far_field").strip().lower(),
    )


@dataclass
class WaveVoiceToolContext:
    """Holds the browser-supplied session snapshot plus callbacks onto the real /v2/* handlers."""

    do_search: Callable[[Any, Any, dict[str, Any], str], dict[str, Any]]
    do_recommend: Callable[[Any, Any, Any, str], dict[str, Any]]
    do_offers: Callable[[str], dict[str, Any]]
    do_checkout: Callable[[str, list[dict[str, Any]], str], dict[str, Any]]
    do_account_orders: Callable[[str, str], dict[str, Any]]
    do_account_invoices: Callable[[str, str], dict[str, Any]]
    tenant: str = "demo-tenant"
    customer_id: str = "guest"
    basket: list[dict[str, Any]] = field(default_factory=list)
    browsing_history: list[dict[str, Any]] = field(default_factory=list)

    def apply_context(self, context: dict[str, Any]) -> None:
        self.tenant = str(context.get("tenant") or self.tenant or "demo-tenant")
        self.customer_id = str(context.get("customerId") or self.customer_id or "guest")
        basket = context.get("basket")
        if isinstance(basket, list):
            self.basket = basket
        history = context.get("browsingHistory")
        if isinstance(history, list):
            self.browsing_history = history

    def basket_summary(self) -> dict[str, Any]:
        total = 0.0
        lines = []
        for item in self.basket:
            qty = int(item.get("quantity") or 0)
            price = float(item.get("price") or 0.0)
            total += qty * price
            lines.append({"productId": item.get("productId"), "title": item.get("title"), "quantity": qty, "price": price})
        return {"items": lines, "itemCount": sum(l["quantity"] for l in lines), "total": round(total, 2)}

    def call_tool(self, name: str, arguments: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
        """Returns (spoken_result, ui_action_or_none)."""
        if name == "search_catalog":
            query = str(arguments.get("query") or "")
            filters = {
                k: arguments.get(k)
                for k in ("category", "brand", "availability")
                if arguments.get(k)
            }
            result = self.do_search(query, 20, filters, self.tenant)
            ui_action = {"action": "search", "query": query, "filters": filters}
            return result, ui_action

        if name == "get_recommendations":
            product_id = arguments.get("productId") or (self.browsing_history[0].get("id") if self.browsing_history else None)
            result = self.do_recommend(product_id, "voice-shopper", 6, self.tenant)
            ui_action = {"action": "show_recommendations", "productId": product_id}
            return result, ui_action

        if name == "get_offers":
            result = self.do_offers(self.tenant)
            return result, {"action": "show_offers"}

        if name == "get_basket":
            return self.basket_summary(), None

        if name == "add_to_basket":
            product_id = arguments.get("productId")
            query = arguments.get("query")
            quantity = max(1, int(arguments.get("quantity") or 1))
            if not product_id and not query:
                return {"added": False, "message": "Tell me which product to add."}, None
            ui_action = {"action": "add_to_basket", "productId": product_id, "query": query, "quantity": quantity}
            return {"added": True, "queued": True, "productId": product_id, "query": query, "quantity": quantity}, ui_action

        if name == "go_to_basket":
            return {"navigated": True}, {"action": "navigate", "view": "basket"}

        if name == "checkout":
            items = [
                {"productId": item.get("productId"), "quantity": int(item.get("quantity") or 1)}
                for item in self.basket
                if item.get("productId")
            ]
            if not items:
                return {"ordered": False, "message": "The basket is empty, so there is nothing to check out yet."}, None
            result = self.do_checkout(self.customer_id, items, self.tenant)
            ui_action = {"action": "checkout_complete", "order": result.get("order") or result}
            return result, ui_action

        if name == "get_order_history":
            result = self.do_account_orders(self.customer_id, self.tenant)
            return result, {"action": "navigate", "view": "account"}

        if name == "get_invoices":
            result = self.do_account_invoices(self.customer_id, self.tenant)
            return result, {"action": "navigate", "view": "account"}

        if name == "navigate":
            view = str(arguments.get("view") or "home").strip().lower()
            return {"navigated": True, "view": view}, {"action": "navigate", "view": view}

        return {"error": f"Unknown WaveStore voice tool: {name}"}, None


class WaveBrowserVoiceBridge:
    def __init__(self, browser_websocket: WebSocket, settings: WaveVoiceSettings, tools: WaveVoiceToolContext):
        self.browser_websocket = browser_websocket
        self.settings = settings
        self.tools = tools
        self.voice_live = None
        self.credential = None
        self.completed_tool_calls: set[str] = set()
        self.session_voice = random.choice(BRITISH_VOICES)

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
                    if isinstance(exc, WebSocketDisconnect):
                        # Normal end of session: the shopper's page navigated away or the tab/mic
                        # was closed. This is expected (multi-page app: any ui_action navigation
                        # ends the current websocket) so it is not logged as a failure.
                        logger.info("WaveStore voice session ended (browser disconnected: %s)", exc.code)
                    else:
                        logger.exception("WaveStore voice bridge failed", exc_info=exc)
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
                compression=None,
                max_size=None,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=5,
            )
        except TypeError:
            return await websockets.connect(
                self.settings.voice_live_ws_url,
                extra_headers=headers,
                compression=None,
                max_size=None,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=5,
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

            if message_type in {"session_init", "context_update"}:
                self.tools.apply_context(message.get("context") or message)
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
        basket = self.tools.basket_summary()
        instructions = (
            "You are a concise British voice concierge for the WaveStore demo shop.\n"
            "You can search products, give recommendations, list offers, manage the shopper's basket, "
            "check out, and look up order/invoice history. Use tools whenever the shopper asks for any of these.\n"
            "You never handle sign-in or passwords: if an action needs an account and none is set, "
            "explain that the shopper should sign in via the Account page first.\n"
            "This is a demo: do not claim a real card was charged.\n"
            f"Current tenant: {self.tools.tenant}. Current customer: {self.tools.customer_id}.\n"
            f"Current basket: {json.dumps(basket)}"
        )
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
                        "threshold": self.settings.vad_threshold,
                        "prefix_padding_ms": self.settings.vad_prefix_padding_ms,
                        "silence_duration_ms": self.settings.vad_silence_duration_ms,
                        "interrupt_response": True,
                    },
                    "input_audio_noise_reduction": {"type": "azure_deep_noise_suppression", "mode": self.settings.noise_reduction_mode},
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
            if event_type.endswith("speech_started") or event_type.endswith("interrupted") or event_type.endswith("response.cancelled"):
                # The shopper started talking (server-side VAD) or the model's turn was cut short.
                # Tell the browser to immediately stop any audio it is still playing/queued so the
                # assistant doesn't talk over the shopper.
                await self._safe_browser_send({"type": "barge_in"})
                continue
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
            result, ui_action = await asyncio.to_thread(self.tools.call_tool, name, parsed_arguments)
        except Exception as exc:
            result, ui_action = {"error": str(exc)}, None
        if ui_action:
            await self._safe_browser_send({"type": "ui_action", **ui_action})
        await self._send_voice_live(
            {"type": "conversation.item.create", "item": {"type": "function_call_output", "call_id": call_id, "output": json.dumps(result)}}
        )
        await self._send_voice_live({"type": "response.create"})
        return True

    async def _safe_browser_send(self, payload: dict[str, Any]) -> None:
        try:
            await self.browser_websocket.send_text(json.dumps(payload))
        except Exception:
            logger.debug("Could not send WaveStore voice payload", exc_info=True)


def _is_base64_audio(value: str) -> bool:
    try:
        base64.b64decode(value, validate=True)
        return True
    except Exception:
        return False
