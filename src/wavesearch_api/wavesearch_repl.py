"""wavesearch_repl.py -- multi-reader/single-writer replication engine
for wavesearch-api, modeled directly on picowal's replication engine
(picoweb/src/picowal_repl.{c,h}, picowal_repl_client.{c,h},
picowal_gossip.{c,h}) -- see
docs/wavesearch-api-multi-reader-single-writer.md for the full design
writeup and an explicit list of what's deliberately NOT solved here.

Ported from "replicate a raw WAL byte-range over HTTP" (picowal) to
"replicate a JSON blob manifest over HTTP" (wavesearch-api), because
this service's durable state already IS a small set of named JSON
blobs (see app.py's *_BLOB path constants) rather than a single
append-only sector-addressed log.

Stdlib-only (urllib, matching the rest of this codebase's HTTP-client
style, e.g. app.py's own LLM/embedding calls) -- no new dependency for
inter-pod HTTP calls.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, Header, HTTPException, Query

logger = logging.getLogger("wavesearch_repl")

REPL_HEALTH_FAIL_THRESHOLD = 3   # consecutive failed status polls before the primary is "unhealthy" -- same constant/value as picowal_repl_client.c
POLL_IDLE_S = 0.5                # sleep between polls once caught up -- mirrors REPL_POLL_IDLE_MS
RETRY_S = 2.0                    # sleep after a connect/parse/timeout failure -- mirrors REPL_RETRY_MS
GOSSIP_TICK_S = 0.5              # mirrors GOSSIP_TICK_MS
HTTP_TIMEOUT_S = 3.0             # bounds every inter-pod HTTP call (status/blob/vote)


class BlobStoreProtocol:
    """Structural type matching retail_v2.blob_store.BlobStore -- avoids
    importing wavesearch_api.app (would be circular)."""

    def read_text(self, path: str) -> str: ...
    def write_text(self, path: str, value: str) -> None: ...
    def exists(self, path: str) -> bool: ...


@dataclass
class ReplConfig:
    node_id: str                       # this node's own id, e.g. "wavesearch-api-0.wavesearch-api-headless:8803"
    followers: list[str]                # ALL registered node ids (comma-split WAVESEARCH_FOLLOWERS), including self
    write_token: str                    # shared secret, presented via X-PW-Write-Token (mirrors picowal's)
    tracked_blobs: list[str]            # blob paths this engine replicates (see design doc for what's excluded and why)
    store: Any                          # this pod's own BlobStore (local or shared -- either works, see design doc)
    reload_callback: Callable[[], Awaitable[None]]  # rebuilds ALL in-memory state from the tracked blobs (reused from app startup)


@dataclass
class ReplState:
    cfg: ReplConfig
    role: str = "replica"               # "writer" | "replica"
    generation: int = 0
    blob_hashes: dict[str, str] = field(default_factory=dict)
    consecutive_failures: int = 0
    term: int = 0
    candidate: str = ""
    vote_bitmask: int = 0
    known_leader: str = ""              # see design doc's "documented improvement over the picowal reference"
    dead_candidates: set[str] = field(default_factory=set)  # see _pick_candidate: excludes nodes conclusively shown unhealthy, so re-election makes forward progress instead of re-nominating the same dead node forever
    current_poll_target: str = ""       # which node id consecutive_failures is currently counting against -- reset to 0 whenever this changes, so a newly-nominated candidate gets a fair REPL_HEALTH_FAIL_THRESHOLD chances rather than inheriting stale failures accrued against a DIFFERENT (previous) target
    stop_requested: bool = False
    _tasks: list[asyncio.Task] = field(default_factory=list)


def _sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _split_host_port(node_id: str) -> tuple[str, int] | None:
    if ":" not in node_id:
        return None
    host, _, port_s = node_id.rpartition(":")
    try:
        return host, int(port_s)
    except ValueError:
        return None


def _http_get(node_id: str, path: str, token: str, timeout: float = HTTP_TIMEOUT_S) -> tuple[int, bytes]:
    hostport = _split_host_port(node_id)
    if not hostport:
        return -1, b""
    host, port = hostport
    req = Request(f"http://{host}:{port}{path}", headers={"X-PW-Write-Token": token})
    try:
        with urlopen(req, timeout=timeout) as resp:  # nosec B310 - fixed, statically-configured internal peer set, not user input
            return resp.status, resp.read()
    except HTTPError as exc:
        return exc.code, b""
    except (URLError, TimeoutError, OSError):
        return -1, b""


def _http_post(node_id: str, path: str, token: str, body: bytes, timeout: float = HTTP_TIMEOUT_S) -> int:
    hostport = _split_host_port(node_id)
    if not hostport:
        return -1
    host, port = hostport
    req = Request(
        f"http://{host}:{port}{path}",
        data=body,
        method="POST",
        headers={"X-PW-Write-Token": token, "Content-Type": "application/json"},
    )
    try:
        with urlopen(req, timeout=timeout) as resp:  # nosec B310 - fixed, statically-configured internal peer set, not user input
            resp.read()
            return resp.status
    except HTTPError as exc:
        return exc.code
    except (URLError, TimeoutError, OSError):
        return -1


def record_blob_write(state: ReplState, path: str, value: str) -> None:
    """Call this from _save_json_blob AFTER a successful write, for every
    tracked path -- the direct analog of picowal's write_off advancing
    on every WAL append. Only meaningful on the writer (replicas write
    tracked blobs only as a side effect of applying a pulled blob, see
    _apply_pulled_blob, which updates blob_hashes directly instead)."""
    if state.role != "writer" or path not in state.cfg.tracked_blobs:
        return
    state.generation += 1
    state.blob_hashes[path] = _sha256_text(value)


def build_repl_router(state: ReplState) -> APIRouter:
    router = APIRouter()

    def _check_token(x_pw_write_token: str | None) -> None:
        if not x_pw_write_token or x_pw_write_token != state.cfg.write_token:
            raise HTTPException(status_code=401, detail="invalid or missing X-PW-Write-Token")

    @router.get("/repl/status")
    async def repl_status(x_pw_write_token: str | None = Header(default=None)) -> dict[str, Any]:
        _check_token(x_pw_write_token)
        if state.role != "writer":
            raise HTTPException(status_code=503, detail="this node is not the current writer")
        return {
            "role": "writer",
            "node_id": state.cfg.node_id,
            "generation": state.generation,
            "blobs": dict(state.blob_hashes),
        }

    @router.get("/repl/blob")
    async def repl_blob(path: str = Query(...), x_pw_write_token: str | None = Header(default=None)) -> dict[str, Any]:
        _check_token(x_pw_write_token)
        if state.role != "writer":
            raise HTTPException(status_code=503, detail="this node is not the current writer")
        if path not in state.cfg.tracked_blobs:
            raise HTTPException(status_code=404, detail="path is not a tracked replicated blob")
        try:
            content = state.cfg.store.read_text(path) if state.cfg.store.exists(path) else ""
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"failed to read blob: {exc}") from exc
        return {"path": path, "content": content}

    @router.get("/gossip/status")
    async def gossip_status() -> dict[str, Any]:
        quorum = len(state.cfg.followers) // 2 + 1
        return {
            "self": state.cfg.node_id,
            "role": state.role,
            "term": state.term,
            "candidate": state.candidate,
            "votes": bin(state.vote_bitmask).count("1"),
            "followers": len(state.cfg.followers),
            "quorum": quorum,
            "known_leader": state.known_leader,
        }

    @router.post("/gossip/vote")
    async def gossip_vote(payload: dict[str, Any], x_pw_write_token: str | None = Header(default=None)) -> dict[str, Any]:
        _check_token(x_pw_write_token)
        term = int(payload.get("term", 0))
        candidate = str(payload.get("candidate", ""))
        voter = str(payload.get("voter", ""))
        await _record_vote(state, term, candidate, voter)
        return {"accepted": True}

    return router


def _find_follower_index(state: ReplState, node_id: str) -> int:
    try:
        return state.cfg.followers.index(node_id)
    except ValueError:
        return -1


def _pick_candidate(state: ReplState) -> str:
    # Deterministic: lexicographically-smallest registered follower id
    # EXCLUDING any node already conclusively shown unhealthy this
    # process's lifetime (state.dead_candidates) -- every node computes
    # the same answer independently, mirroring picowal_gossip.c's
    # pick_candidate(), but with one deliberate improvement: the plain
    # "smallest of ALL followers, health ignored" version re-nominates
    # the SAME dead node forever once it's the alphabetically-first id
    # and has died (nobody can ever vote FOR a dead node reaching
    # quorum again, so election would never make forward progress).
    # Excluding known-dead candidates guarantees each re-election tries
    # a different node.
    candidates = [f for f in state.cfg.followers if f not in state.dead_candidates]
    if not candidates:
        candidates = list(state.cfg.followers)  # all marked dead (shouldn't happen with a live quorum) -- fall back rather than crash
    return min(candidates)


async def _promote_self(state: ReplState) -> None:
    if state.role == "writer":
        return
    state.role = "writer"
    state.stop_requested = True  # signals the repl-client poll loop to exit
    # Seed this writer's own blob-hash manifest from whatever is
    # currently on local disk (post-promotion, this node's local store
    # IS the new source of truth going forward).
    hashes: dict[str, str] = {}
    for p in state.cfg.tracked_blobs:
        try:
            if state.cfg.store.exists(p):
                hashes[p] = _sha256_text(state.cfg.store.read_text(p))
        except Exception:
            continue
    state.blob_hashes = hashes
    state.generation += 1
    logger.warning(
        "wavesearch_repl: *** %s PROMOTED TO WRITER via gossip quorum (term=%d) ***",
        state.cfg.node_id, state.term,
    )


async def _record_vote(state: ReplState, term: int, candidate: str, voter: str) -> None:
    if term > state.term:
        state.term = term
        state.candidate = candidate
        state.vote_bitmask = 0
    elif term == state.term and not state.candidate:
        state.candidate = candidate
    if term != state.term or candidate != state.candidate:
        return  # stale/mismatched ballot
    vi = _find_follower_index(state, voter)
    if vi >= 0:
        state.vote_bitmask |= (1 << vi)
    quorum = len(state.cfg.followers) // 2 + 1
    votes = bin(state.vote_bitmask).count("1")
    if votes >= quorum:
        # Symmetric: EVERY node (not just the winner) learns who the
        # leader is the moment quorum is observed -- see design doc's
        # "documented improvement over the picowal reference".
        state.known_leader = candidate
        if candidate == state.cfg.node_id:
            await _promote_self(state)


async def _apply_pulled_blob(state: ReplState, path: str, content: str, remote_hash: str) -> None:
    try:
        state.cfg.store.write_text(path, content)
        state.blob_hashes[path] = remote_hash
    except Exception as exc:
        logger.warning("wavesearch_repl: failed to write pulled blob %s locally: %s", path, exc)


async def _repl_client_tick(state: ReplState) -> bool:
    """One poll/pull iteration. Returns True if any blob was applied
    (caller uses this to decide idle-vs-retry sleep). Deliberately only
    polls a CONFIRMED leader (state.known_leader, set once gossip
    quorum has actually elected someone) -- never a speculative
    _pick_candidate() guess before any election has completed, since a
    nominated-but-not-yet-promoted candidate legitimately 503s its own
    /repl/status (it isn't the writer yet), which would otherwise be
    misread as "that candidate is dead" and wrongly blacklist a
    perfectly healthy future leader mid-election. Detecting "no
    confirmed leader yet" (bootstrap, or just after a dead leader was
    blacklisted) is entirely gossip_tick's job now, independent of this
    poll loop."""
    if not state.known_leader:
        return False  # nothing confirmed to replicate from yet -- gossip_tick drives election in this state
    primary = state.known_leader
    if primary != state.current_poll_target:
        # The confirmed leader changed -- give it a fair, fresh count
        # of REPL_HEALTH_FAIL_THRESHOLD failures rather than inheriting
        # stale failures accrued against a DIFFERENT, previous leader.
        state.current_poll_target = primary
        state.consecutive_failures = 0
    if primary == state.cfg.node_id:
        return False  # we ARE the confirmed leader (should already be promoted via _record_vote); nothing to poll

    status_code, body = await asyncio.to_thread(_http_get, primary, "/repl/status", state.cfg.write_token)
    if status_code != 200:
        state.consecutive_failures += 1
        return False
    state.consecutive_failures = 0

    try:
        remote = json.loads(body.decode("utf-8"))
    except Exception:
        return False
    remote_generation = int(remote.get("generation", 0))
    remote_blobs: dict[str, str] = dict(remote.get("blobs", {}))
    if remote_generation <= state.generation:
        return False

    applied_any = False
    for path, remote_hash in remote_blobs.items():
        if path not in state.cfg.tracked_blobs:
            continue
        if state.blob_hashes.get(path) == remote_hash:
            continue
        bstatus, bbody = await asyncio.to_thread(
            _http_get, primary, f"/repl/blob?path={path}", state.cfg.write_token
        )
        if bstatus != 200:
            continue
        try:
            payload = json.loads(bbody.decode("utf-8"))
        except Exception:
            continue
        await _apply_pulled_blob(state, path, str(payload.get("content", "")), remote_hash)
        applied_any = True

    if applied_any:
        try:
            await state.cfg.reload_callback()
        except Exception as exc:
            logger.warning("wavesearch_repl: reload_callback failed after applying replicated blobs: %s", exc)
        state.generation = remote_generation

    return applied_any


async def _repl_client_loop(state: ReplState) -> None:
    while not state.stop_requested:
        try:
            made_progress = await _repl_client_tick(state)
        except Exception as exc:
            logger.warning("wavesearch_repl: repl-client tick failed: %s", exc)
            made_progress = False
        await asyncio.sleep(POLL_IDLE_S if made_progress else RETRY_S)
    logger.warning("wavesearch_repl: repl-client loop stopped (promoted to writer)")


async def _gossip_tick(state: ReplState) -> None:
    if state.role == "writer":
        return

    if state.known_leader:
        # A leader is confirmed (via prior quorum) -- health is judged
        # purely by _repl_client_tick's real polls against THAT leader
        # (never a speculative pre-election candidate guess, see
        # _repl_client_tick's doc comment).
        primary_healthy = state.consecutive_failures < REPL_HEALTH_FAIL_THRESHOLD
        if primary_healthy:
            state.candidate = ""
            state.vote_bitmask = 0
            return
        # Confirmed leader has conclusively failed enough consecutive
        # health checks -- blacklist it so the next _pick_candidate()
        # call makes forward progress instead of re-nominating the
        # same dead node forever (see _pick_candidate's doc comment).
        if state.known_leader != state.cfg.node_id:
            state.dead_candidates.add(state.known_leader)
        state.known_leader = ""

    # No confirmed leader (bootstrap, or just cleared above after a
    # confirmed leader died) -- deterministically nominate/vote for the
    # smallest non-blacklisted follower id. Every node computes the
    # same candidate independently and votes for it immediately
    # (no separate "wait for a failure" gate here, since there's no
    # confirmed leader to have failed against yet) -- this is what
    # makes bootstrap converge in one election cycle instead of never,
    # and what makes failover retry with a fresh, un-blacklisted
    # candidate each round.
    candidate = _pick_candidate(state)
    if candidate != state.candidate:
        state.term += 1
        state.candidate = candidate
        state.vote_bitmask = 0
        logger.warning(
            "wavesearch_repl: no confirmed leader -- starting election term=%d, nominating %s",
            state.term, candidate,
        )
    self_idx = _find_follower_index(state, state.cfg.node_id)
    if self_idx >= 0:
        state.vote_bitmask |= (1 << self_idx)
    await _record_vote(state, state.term, state.candidate, state.cfg.node_id)

    term, candidate_copy = state.term, state.candidate
    body = json.dumps({"term": term, "candidate": candidate_copy, "voter": state.cfg.node_id}).encode("utf-8")
    for peer in state.cfg.followers:
        if peer == state.cfg.node_id:
            continue
        await asyncio.to_thread(_http_post, peer, "/gossip/vote", state.cfg.write_token, body)


async def _gossip_loop(state: ReplState) -> None:
    while not state.stop_requested:
        try:
            await _gossip_tick(state)
        except Exception as exc:
            logger.warning("wavesearch_repl: gossip tick failed: %s", exc)
        await asyncio.sleep(GOSSIP_TICK_S)


def repl_init(cfg: ReplConfig) -> ReplState:
    """Builds the ReplState and returns it; caller (app.py) is
    responsible for calling start_background_tasks()/stop() at
    FastAPI startup/shutdown, and mounting build_repl_router(state)."""
    if cfg.node_id not in cfg.followers:
        logger.warning(
            "wavesearch_repl: WAVESEARCH_NODE_ID '%s' is not present in WAVESEARCH_FOLLOWERS; "
            "this node can relay votes but can never be elected writer itself",
            cfg.node_id,
        )
    state = ReplState(cfg=cfg)
    return state


def start_background_tasks(state: ReplState) -> None:
    state._tasks.append(asyncio.create_task(_repl_client_loop(state)))
    state._tasks.append(asyncio.create_task(_gossip_loop(state)))


async def stop_background_tasks(state: ReplState) -> None:
    state.stop_requested = True
    for t in state._tasks:
        t.cancel()
    for t in state._tasks:
        try:
            await t
        except (asyncio.CancelledError, Exception):
            pass


def require_writer(state: ReplState) -> Callable[[], None]:
    """Returns a FastAPI dependency that 503s unless this node is
    currently the writer -- mirrors picowal_replica_mode_enabled()
    gating /wal/ mutation routes on a replica."""

    def _dep() -> None:
        if state.role != "writer":
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "not_writer",
                    "message": "this node is a read replica; retry against the current writer",
                    "known_leader": state.known_leader or None,
                },
            )

    return _dep
