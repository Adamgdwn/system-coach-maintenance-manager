"""Export helpers for shareable summaries."""

from __future__ import annotations


def build_share_text(report: dict, system_map: dict | None = None, maintenance_report: dict | None = None) -> str:
    lines = [
        "System Stack Review and Coach",
        "",
        f"Generated: {report['generated_at']}",
        f"Operating system: {report['environment'].get('os', 'Unknown')}",
        f"Desktop: {report['environment'].get('desktop', 'Unknown')}",
        f"Shell: {report['environment'].get('shell', 'Unknown')}",
        "",
        f"Installed components: {report['summary']['installed_component_count']}",
        "Detected tools:",
    ]

    for component in report["components"][:18]:
        lines.append(f"- {component['label']} ({component['category']})")

    if report["summary"]["primary_stack_matches"]:
        lines.append("")
        lines.append("Likely stack patterns:")
        for match in report["summary"]["primary_stack_matches"]:
            lines.append(f"- {match['title']}: {match['summary']}")

    if system_map:
        lines.append("")
        lines.append("Filesystem mapping:")
        lines.append(f"- Roots scanned: {system_map['summary']['roots_scanned']}")
        lines.append(f"- Projects detected: {system_map['summary']['projects_detected']}")
        lines.append(f"- Configs detected: {system_map['summary']['configs_detected']}")
        for scan in system_map.get("scans", [])[:8]:
            lines.append(f"- {scan['root']}: {scan['summary']['projects_detected']} projects")

    if maintenance_report:
        lines.append("")
        lines.append("Maintenance diagnostics:")
        lines.append(f"- Findings: {maintenance_report['summary']['finding_count']}")
        lines.append(f"- Severity counts: {maintenance_report['summary']['severity_counts']}")
        lines.append(f"- Approval-required plans: {maintenance_report['summary']['approval_required_count']}")
        for finding in maintenance_report.get("findings", [])[:8]:
            lines.append(f"- {finding['title']} [{finding['severity']}]: {finding['summary']}")

    lines.append("")
    lines.append("This summary was generated locally.")
    return "\n".join(lines)
