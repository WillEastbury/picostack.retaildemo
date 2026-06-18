from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PICOSCRIPT_ROOT = ROOT.parent / "picoscript"
if str(PICOSCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(PICOSCRIPT_ROOT))

from picoscript_cfront import compile_c  # noqa: E402
from picoscript_il import lower_to_bytecode_safe  # noqa: E402
from picoscript_vm import PicoVM  # noqa: E402


def _s32(value: int) -> int:
    return value - 0x100000000 if value & 0x80000000 else value


def run_int_outputs(source: str) -> list[int]:
    words = lower_to_bytecode_safe(compile_c(source))
    vm = PicoVM().run(words)
    return [_s32(int.from_bytes(chunk, "big")) for chunk in vm.output]


@lru_cache(maxsize=1)
def checkout_policy_template() -> str:
    return (ROOT / "scripts" / "checkout_policy.pc").read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def route_policy_template() -> str:
    return (ROOT / "scripts" / "route_policy.pc").read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def cms_render_template() -> str:
    return (ROOT / "scripts" / "cms_render.pc").read_text(encoding="utf-8")


def route_action(action: int, method: int = 0, path: int = 0) -> tuple[int, int]:
    source = (
        route_policy_template()
        .replace("{{action}}", str(action))
        .replace("{{method}}", str(method))
        .replace("{{path}}", str(path))
    )
    words = lower_to_bytecode_safe(compile_c(source))
    vm = PicoVM().run(words)
    raw = b"".join(vm.output)
    if len(raw) != 2:
        raise RuntimeError(f"route policy emitted {len(raw)} bytes, expected 2")
    return raw[0], raw[1]


def checkout_totals_pence(subtotal_pence: int, shipping_pence: int, discount_percent: int) -> dict[str, int]:
    source = (
        checkout_policy_template()
        .replace("{{subtotal_pence}}", str(max(0, subtotal_pence)))
        .replace("{{shipping_pence}}", str(max(0, shipping_pence)))
        .replace("{{discount_percent}}", str(max(0, discount_percent)))
    )
    words = lower_to_bytecode_safe(compile_c(source))
    vm = PicoVM().run(words)
    raw = b"".join(vm.output)
    if len(raw) != 12:
        raise RuntimeError(f"checkout policy emitted {len(raw)} bytes, expected 12")
    discount = int.from_bytes(raw[0:4], "big")
    tax = int.from_bytes(raw[4:8], "big")
    total = int.from_bytes(raw[8:12], "big")
    return {"discount": discount, "tax": tax, "total": total}


def _setbytes(base: int, data: bytes) -> str:
    return "".join(f"Memory.Set({base + i}, {byte});" for i, byte in enumerate(data))


def render_template(template: str, model: dict[str, str]) -> str:
    template_bytes = template.encode("utf-8")
    model_text = "\n".join(f"{key}={value}" for key, value in model.items())
    model_bytes = model_text.encode("utf-8")
    template_base = 1000
    model_base = template_base + len(template_bytes) + 1024
    source = (
        cms_render_template()
        .replace("{{template_bytes}}", _setbytes(template_base, template_bytes))
        .replace("{{model_bytes}}", _setbytes(model_base, model_bytes))
        .replace("{{template_base}}", str(template_base))
        .replace("{{template_len}}", str(len(template_bytes)))
        .replace("{{model_base}}", str(model_base))
        .replace("{{model_len}}", str(len(model_bytes)))
    )
    words = lower_to_bytecode_safe(compile_c(source))
    vm = PicoVM().run(words)
    return b"".join(vm.output).decode("utf-8")
