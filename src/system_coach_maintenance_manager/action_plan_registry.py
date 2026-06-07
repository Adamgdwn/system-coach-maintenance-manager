"""Short-lived server-side registry for executable action plans."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import datetime as dt
import threading
import uuid

from . import autonomy_controls
from .maintenance_actions import action_contract_fingerprint, execute_guarded_action


DEFAULT_PLAN_TTL_SECONDS = 600


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _iso(value: dt.datetime) -> str:
    return value.isoformat(timespec="seconds")


def _blocked_result(plan_id: str | None, error: str, *, stored: "StoredActionPlan | None" = None) -> dict:
    contract = stored.contract if stored else {}
    return {
        "action_id": contract.get("id"),
        "plan_id": contract.get("plan_id"),
        "server_plan_id": plan_id,
        "fingerprint": contract.get("fingerprint"),
        "status": "blocked",
        "started_at": _iso(_now()),
        "finished_at": _iso(_now()),
        "execution_enabled": False,
        "exit_code": None,
        "commands": contract.get("command_preview", []),
        "output": "",
        "error": error,
        "post_check": contract.get("post_check", []),
        "rollback": contract.get("rollback", []),
    }


@dataclass
class StoredActionPlan:
    server_plan_id: str
    plan: dict
    contract: dict
    fingerprint: str
    created_at: dt.datetime
    expires_at: dt.datetime
    used_at: dt.datetime | None = None

    def expired(self, now: dt.datetime | None = None) -> bool:
        return (now or _now()) >= self.expires_at

    def used(self) -> bool:
        return self.used_at is not None


class ActionPlanRegistry:
    """Owns executable action contracts for the local API process."""

    def __init__(self, ttl_seconds: int = DEFAULT_PLAN_TTL_SECONDS):
        self.ttl_seconds = ttl_seconds
        self._plans: dict[str, StoredActionPlan] = {}
        self._lock = threading.Lock()

    def register_plan(self, plan: dict) -> dict:
        contract = deepcopy(plan.get("action_contract", {}))
        if not isinstance(contract, dict) or not contract:
            raise ValueError("plan.action_contract must be present before registration")
        fingerprint = action_contract_fingerprint(contract)
        contract["fingerprint"] = fingerprint
        server_plan_id = f"plan-{uuid.uuid4().hex[:12]}"
        created_at = _now()
        expires_at = created_at + dt.timedelta(seconds=self.ttl_seconds)
        registered_plan = deepcopy(plan)
        registered_plan["action_contract"] = contract
        registered_plan["server_plan_id"] = server_plan_id
        registered_plan["server_plan_expires_at"] = _iso(expires_at)
        registered_plan["fingerprint"] = fingerprint
        contract["server_plan_id"] = server_plan_id
        contract["server_plan_expires_at"] = _iso(expires_at)
        stored = StoredActionPlan(
            server_plan_id=server_plan_id,
            plan=deepcopy(registered_plan),
            contract=deepcopy(contract),
            fingerprint=fingerprint,
            created_at=created_at,
            expires_at=expires_at,
        )
        with self._lock:
            self._plans[server_plan_id] = stored
            self._purge_expired_locked()
        return registered_plan

    def lookup(self, server_plan_id: str) -> StoredActionPlan | None:
        with self._lock:
            self._purge_expired_locked()
            stored = self._plans.get(server_plan_id)
            return deepcopy(stored) if stored else None

    def execute(self, server_plan_id: str, confirmation_text: str) -> dict:
        if not autonomy_controls.execution_allowed():
            return _blocked_result(server_plan_id, "autonomy level A0 disables action execution; set agent_autonomy_level to A1 or higher")
        with self._lock:
            self._purge_expired_locked()
            stored = self._plans.get(server_plan_id)
            if not stored:
                return _blocked_result(server_plan_id, "server-side action plan was not found or expired")
            if stored.expired():
                del self._plans[server_plan_id]
                return _blocked_result(server_plan_id, "server-side action plan expired", stored=stored)
            if stored.used():
                return _blocked_result(server_plan_id, "server-side action plan was already used", stored=stored)
            if action_contract_fingerprint(stored.contract) != stored.fingerprint:
                stored.used_at = _now()
                return _blocked_result(server_plan_id, "server-side action fingerprint did not match", stored=stored)
            stored.used_at = _now()
            contract = deepcopy(stored.contract)

        result = execute_guarded_action(contract, confirmation_text)
        result["server_plan_id"] = server_plan_id
        result["fingerprint"] = contract.get("fingerprint")
        return result

    def clear(self) -> None:
        with self._lock:
            self._plans.clear()

    def _purge_expired_locked(self) -> None:
        now = _now()
        expired = [plan_id for plan_id, stored in self._plans.items() if stored.expired(now) and not stored.used()]
        for plan_id in expired:
            del self._plans[plan_id]


ACTION_PLAN_REGISTRY = ActionPlanRegistry()


def register_action_plan(plan: dict, registry: ActionPlanRegistry = ACTION_PLAN_REGISTRY) -> dict:
    return registry.register_plan(plan)


def execute_registered_action(
    server_plan_id: str,
    confirmation_text: str,
    registry: ActionPlanRegistry = ACTION_PLAN_REGISTRY,
) -> dict:
    return registry.execute(server_plan_id, confirmation_text)


def reset_action_plan_registry(registry: ActionPlanRegistry = ACTION_PLAN_REGISTRY) -> None:
    registry.clear()
