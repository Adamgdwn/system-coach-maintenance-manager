"""Reporting helpers for read-only maintenance diagnostics."""

from __future__ import annotations

from collections import Counter
import shlex


SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


def _status_counts(findings: list[dict]) -> dict:
    return dict(Counter(finding["status"] for finding in findings))


def _severity_counts(findings: list[dict]) -> dict:
    return dict(Counter(finding["severity"] for finding in findings))


def _build_recommendations(findings: list[dict]) -> list[str]:
    recommendations = []
    actionable = [finding for finding in findings if finding.get("can_prepare_action")]
    critical = [finding for finding in findings if finding["severity"] == "critical"]
    warnings = [finding for finding in findings if finding["severity"] == "warning"]

    if critical:
        recommendations.append(
            "Start with critical findings and preserve the evidence before changing services, packages, or files."
        )
    if warnings:
        recommendations.append(
            "Review warning findings as troubleshooting leads. Each one should become a narrow plan before any execution."
        )
    if actionable:
        recommendations.append(
            "Action plans are approval-required previews. They are not executed automatically in this version."
        )
    if not critical and not warnings:
        recommendations.append(
            "No urgent maintenance issues were detected by the current read-only checks. Keep using diagnostics as a baseline before larger changes."
        )
    return recommendations


def _platform_key(os_name: str | None) -> str:
    normalized = (os_name or "").strip().lower()
    if normalized.startswith("win"):
        return "windows"
    if normalized == "linux":
        return "linux"
    return "unknown"


def _os_name_from_diagnostics(diagnostics: dict) -> str:
    return str(diagnostics.get("metrics", {}).get("platform", {}).get("os") or "Unknown")


def _quote_posix(value: str) -> str:
    return shlex.quote(value)


def _quote_powershell(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _base_plan(finding: dict, *, title: str, risk: str, reversible: bool, requires_privilege: bool) -> dict:
    return {
        "id": f"plan-{finding['id']}",
        "finding_id": finding["id"],
        "title": title,
        "approval_required": True,
        "execution_enabled": False,
        "risk": risk,
        "reversible": reversible,
        "requires_privilege": requires_privilege,
    }


def _triage_plan(finding: dict, platform: str) -> dict:
    plan = _base_plan(
        finding,
        title=f"Triage {finding['title']}",
        risk="unknown",
        reversible=False,
        requires_privilege=False,
    )
    plan.update(
        {
            "id": f"plan-{finding['id']}-triage",
            "platform": platform,
            "commands": [],
            "manual_steps": [
                f"Confirm the operating system and tooling before preparing commands for {finding['category']}.",
                "Collect only read-only evidence until a platform-specific plan exists.",
                "Prepare a narrow plan with exact commands, risk, reversibility, and rollback notes before execution.",
            ],
            "expected_effect": "Avoid guessing at maintenance commands on an unsupported or ambiguous platform.",
            "approval_prompt": "Do not execute anything until this finding has a concrete platform-specific plan.",
        }
    )
    return plan


def _disk_plan(finding: dict, platform: str) -> dict:
    path = str(finding["evidence"]["path"])
    if platform == "linux":
        plan = _base_plan(
            finding,
            title=f"Investigate disk pressure on {path}",
            risk="medium",
            reversible=False,
            requires_privilege=False,
        )
        plan.update(
            {
                "platform": "Linux",
                "commands": [
                    f"du -h --max-depth=1 {_quote_posix(path)}",
                    "journalctl --disk-usage",
                ],
                "manual_steps": [
                    "Review the largest directories before choosing any cleanup target.",
                    "Check whether logs, package caches, containers, or user downloads are responsible.",
                ],
                "expected_effect": "Identify large directories and log usage before preparing any cleanup command.",
                "approval_prompt": "Approve only after the large target is known and the command is narrowed to that target.",
            }
        )
        return plan

    if platform == "windows":
        plan = _base_plan(
            finding,
            title=f"Investigate disk pressure on {path}",
            risk="medium",
            reversible=False,
            requires_privilege=False,
        )
        plan.update(
            {
                "platform": "Windows",
                "commands": [
                    'powershell -NoProfile -Command "Get-PSDrive -PSProvider FileSystem"',
                    (
                        'powershell -NoProfile -Command "Get-ChildItem -Force '
                        f'{_quote_powershell(path)} | Sort-Object Length -Descending | '
                        'Select-Object -First 20 Name,Length,FullName"'
                    ),
                ],
                "manual_steps": [
                    "Open Settings > System > Storage to inspect the largest categories.",
                    "Review user downloads, recycle bin, logs, and app caches before deleting anything.",
                ],
                "expected_effect": "Identify large locations and storage categories before preparing cleanup.",
                "approval_prompt": "Approve cleanup only after a specific folder or Windows storage category is selected.",
            }
        )
        return plan

    return _triage_plan(finding, "Unknown")


def _failed_services_plan(finding: dict, platform: str) -> dict:
    if platform == "linux":
        plan = _base_plan(
            finding,
            title="Inspect failed services",
            risk="low",
            reversible=True,
            requires_privilege=False,
        )
        plan.update(
            {
                "platform": "Linux",
                "commands": ["systemctl --failed", "systemctl status <service-name>"],
                "manual_steps": [
                    "Identify the named failed service before preparing a restart.",
                    "Read recent service logs and configuration errors first.",
                ],
                "expected_effect": "Identify which failed service matters before preparing a restart or configuration change.",
                "approval_prompt": "Approve a restart only for a named service after reviewing its status and logs.",
            }
        )
        return plan

    if platform == "windows":
        plan = _base_plan(
            finding,
            title="Inspect Windows service failures",
            risk="low",
            reversible=True,
            requires_privilege=False,
        )
        plan.update(
            {
                "platform": "Windows",
                "commands": [
                    'powershell -NoProfile -Command "Get-Service | Where-Object {$_.Status -ne \'Running\'} | Select-Object -First 40 Name,DisplayName,Status"',
                    'wevtutil qe System /q:"*[System[Provider[@Name=\'Service Control Manager\'] and (Level=1 or Level=2 or Level=3)]]" /c:25 /f:text /rd:true',
                ],
                "manual_steps": [
                    "Open Event Viewer and group repeated Service Control Manager events.",
                    "Prepare a named-service plan before restarting or changing service startup settings.",
                ],
                "expected_effect": "Identify a specific Windows service failure before proposing a restart or settings change.",
                "approval_prompt": "Approve follow-up only for a named service with visible event evidence.",
            }
        )
        return plan

    return _triage_plan(finding, "Unknown")


def _journal_plan(finding: dict, platform: str) -> dict:
    if platform == "linux":
        plan = _base_plan(
            finding,
            title="Group recent critical log errors",
            risk="low",
            reversible=True,
            requires_privilege=False,
        )
        plan.update(
            {
                "platform": "Linux",
                "commands": ["journalctl -p 3 -n 100 --no-pager"],
                "manual_steps": [
                    "Group repeated log lines by service, device, or package.",
                    "Prepare follow-up commands only for the repeated source.",
                ],
                "expected_effect": "Collect enough log context to identify repeated services, devices, or package failures.",
                "approval_prompt": "Approve only targeted follow-up commands based on the repeated error source.",
            }
        )
        return plan

    if platform == "windows":
        plan = _base_plan(
            finding,
            title="Group recent Windows critical event log errors",
            risk="low",
            reversible=True,
            requires_privilege=False,
        )
        plan.update(
            {
                "platform": "Windows",
                "commands": [
                    'wevtutil qe System /q:"*[System[(Level=1 or Level=2)]]" /c:25 /f:text /rd:true',
                    "eventvwr.msc",
                ],
                "manual_steps": [
                    "Open Event Viewer > Windows Logs > System.",
                    "Group repeated event sources and event IDs before preparing repairs.",
                ],
                "expected_effect": "Collect event context without changing drivers, services, or registry settings.",
                "approval_prompt": "Approve only targeted follow-up based on a repeated event source and event ID.",
            }
        )
        return plan

    return _triage_plan(finding, "Unknown")


def _network_plan(finding: dict, platform: str) -> dict:
    if platform == "linux":
        plan = _base_plan(
            finding,
            title="Inspect network route and DNS state",
            risk="low",
            reversible=True,
            requires_privilege=False,
        )
        plan.update(
            {
                "platform": "Linux",
                "commands": ["ip route", "resolvectl status", "cat /etc/resolv.conf"],
                "manual_steps": [
                    "Compare the default route with the expected network connection.",
                    "Check DNS resolver state before changing NetworkManager, systemd-resolved, or router settings.",
                ],
                "expected_effect": "Gather network evidence before changing DNS, routes, or network manager settings.",
                "approval_prompt": "Approve configuration changes only after route and DNS evidence point to one specific issue.",
            }
        )
        return plan

    if platform == "windows":
        plan = _base_plan(
            finding,
            title="Inspect Windows route and DNS state",
            risk="low",
            reversible=True,
            requires_privilege=False,
        )
        plan.update(
            {
                "platform": "Windows",
                "commands": [
                    "route print",
                    "ipconfig /all",
                    'powershell -NoProfile -Command "Resolve-DnsName example.com"',
                ],
                "manual_steps": [
                    "Confirm the active adapter, default gateway, DNS server, and VPN state.",
                    "Prepare adapter or DNS changes only after the route and resolver evidence agree.",
                ],
                "expected_effect": "Gather Windows network evidence before changing adapters, DNS, routes, or VPN settings.",
                "approval_prompt": "Approve network changes only after identifying one adapter and one concrete setting.",
            }
        )
        return plan

    return _triage_plan(finding, "Unknown")


def _package_plan(finding: dict, platform: str) -> dict:
    manager = finding["evidence"].get("manager", "package manager")
    if platform == "linux":
        commands_by_manager = {
            "apt-get": ["apt-get check"],
            "dnf": ["dnf check"],
            "pacman": ["pacman -Dk"],
        }
        commands = commands_by_manager.get(manager)
        if not commands:
            return _triage_plan(finding, "Linux")
        plan = _base_plan(
            finding,
            title=f"Review {manager} package health",
            risk="medium",
            reversible=False,
            requires_privilege=True,
        )
        plan.update(
            {
                "platform": "Linux",
                "commands": commands,
                "manual_steps": [
                    "Read package-manager output before approving repair, install, remove, or cache cleanup commands.",
                    "Identify exact affected packages and package database state.",
                ],
                "expected_effect": "Review package database health before approving any repair, install, or remove command.",
                "approval_prompt": "Approve package repair only when the exact command and package impact are visible.",
            }
        )
        return plan

    if platform == "windows":
        commands_by_manager = {
            "winget": ["winget --info", "winget source list"],
            "choco": ["choco --version", "choco list --local-only --limit-output"],
        }
        commands = commands_by_manager.get(manager)
        if not commands:
            return _triage_plan(finding, "Windows")
        plan = _base_plan(
            finding,
            title=f"Review {manager} package health",
            risk="medium",
            reversible=False,
            requires_privilege=True,
        )
        plan.update(
            {
                "platform": "Windows",
                "commands": commands,
                "manual_steps": [
                    "Review package source health and installed package state before upgrades or repairs.",
                    "Prepare a named package or source repair plan before running any modifying command.",
                ],
                "expected_effect": "Review Windows package-manager state before approving repair, install, upgrade, or remove commands.",
                "approval_prompt": "Approve package changes only when the exact package/source impact is visible.",
            }
        )
        return plan

    return _triage_plan(finding, "Unknown")


def _plan_for_finding(finding: dict, platform: str) -> dict | None:
    if not finding.get("can_prepare_action"):
        return None

    if finding["category"] == "disk":
        return _disk_plan(finding, platform)

    if finding["id"] == "failed-services":
        return _failed_services_plan(finding, platform)

    if finding["id"] == "journal-errors":
        return _journal_plan(finding, platform)

    if finding["id"] == "network-basics":
        return _network_plan(finding, platform)

    if finding["id"] == "package-manager-health":
        return _package_plan(finding, platform)

    return _triage_plan(finding, "Unknown")


def _build_action_plans(findings: list[dict], os_name: str) -> list[dict]:
    platform = _platform_key(os_name)
    plans = []
    for finding in findings:
        plan = _plan_for_finding(finding, platform)
        if plan:
            plans.append(plan)
    return plans


def generate_maintenance_report(diagnostics: dict) -> dict:
    findings = sorted(
        diagnostics["findings"],
        key=lambda finding: (SEVERITY_ORDER.get(finding["severity"], 99), finding["category"], finding["title"]),
    )
    action_plans = _build_action_plans(findings, _os_name_from_diagnostics(diagnostics))
    return {
        "generated_at": diagnostics["generated_at"],
        "summary": {
            "finding_count": len(findings),
            "status_counts": _status_counts(findings),
            "severity_counts": _severity_counts(findings),
            "approval_required_count": len(action_plans),
            "execution_enabled": False,
        },
        "findings": findings,
        "action_plans": action_plans,
        "recommendations": _build_recommendations(findings),
        "command_log": diagnostics["command_log"],
        "metrics": diagnostics["metrics"],
    }
