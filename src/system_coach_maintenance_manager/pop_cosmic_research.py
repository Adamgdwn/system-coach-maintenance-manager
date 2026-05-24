"""Source-aware Pop!_OS/COSMIC research helpers."""

from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
import json
import urllib.error
import urllib.parse
import urllib.request

from .pop_cosmic_deep_scan import sanitize_output


ALLOWED_DOMAINS = (
    "system76.com",
    "support.system76.com",
    "blog.system76.com",
    "github.com",
    "api.github.com",
    "ai.google.dev",
    "deepmind.google",
    "ollama.com",
)
OFFICIAL_SYSTEM76_SOURCES = (
    ("Pop!_OS Downloads And Release Notes", "https://system76.com/pop/download/"),
    ("COSMIC Epoch Updates", "https://blog.system76.com/post/cosmic-epoch-1-updates/"),
    ("Pop!_OS Upgrade Guide", "https://support.system76.com/articles/upgrade-pop/"),
    ("Package Manager Repair Guide", "https://support.system76.com/articles/package-manager-pop/"),
    ("System Firmware Guide", "https://support.system76.com/articles/system-firmware/"),
)


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _domain_allowed(url: str, allowed_domains: tuple[str, ...] = ALLOWED_DOMAINS) -> bool:
    host = urllib.parse.urlparse(url).netloc.lower()
    return any(host == domain or host.endswith(f".{domain}") for domain in allowed_domains)


def _source_record(
    *,
    source_id: str,
    provider: str,
    title: str,
    url: str,
    trust_level: str,
    summary: str,
    published_or_updated: str = "unknown",
    relevant_evidence: list[str] | None = None,
    risk_notes: list[str] | None = None,
    applies_to: dict | None = None,
    record_mode: str = "official-metadata",
) -> dict:
    return {
        "source_id": source_id,
        "provider": provider,
        "title": title,
        "url": url,
        "published_or_updated": published_or_updated,
        "retrieved_at": _now(),
        "trust_level": trust_level,
        "summary": sanitize_output(summary, max_chars=1600),
        "relevant_evidence": relevant_evidence or [],
        "risk_notes": risk_notes or [],
        "applies_to": applies_to or {"pop_version": "unknown", "cosmic_version": "unknown", "hardware": "unknown"},
        "record_mode": record_mode,
    }


class ResearchProvider:
    def search(self, query: str, *, max_results: int = 8) -> list[dict]:
        raise NotImplementedError

    def fetch(self, url: str) -> dict:
        raise NotImplementedError


@dataclass
class OfficialSystem76Provider(ResearchProvider):
    enabled: bool = False

    def search(self, query: str, *, max_results: int = 8) -> list[dict]:
        records = []
        lowered = query.lower()
        for index, (title, url) in enumerate(OFFICIAL_SYSTEM76_SOURCES[:max_results], 1):
            if not any(term in lowered for term in ("pop", "cosmic", "package", "firmware", "upgrade", "update", "display", "panel")):
                continue
            records.append(
                _source_record(
                    source_id=f"system76-{index}",
                    provider="system76",
                    title=title,
                    url=url,
                    trust_level="official",
                    summary="Official System76 source selected for Pop!_OS/COSMIC troubleshooting context.",
                    risk_notes=[
                        "Treat package repair, firmware, refresh, and upgrade instructions as approval-required actions.",
                    ],
                    applies_to={"pop_version": "24.04|22.04|unknown", "cosmic_version": "Epoch 1|unknown", "hardware": "unknown"},
                    record_mode="official-source-metadata",
                )
            )
        return records

    def fetch(self, url: str) -> dict:
        if not self.enabled:
            return _source_record(
                source_id="system76-fetch-disabled",
                provider="system76",
                title="Fetch disabled",
                url=url,
                trust_level="official",
                summary="Web research is disabled. Enable it before fetching source text.",
                record_mode="local-only-disabled-fetch",
            )
        if not _domain_allowed(url):
            raise ValueError("URL domain is not allowed for Pop/COSMIC research.")
        with urllib.request.urlopen(url, timeout=12) as response:
            text = response.read(25000).decode("utf-8", errors="replace")
        return _source_record(
            source_id=f"system76-fetched-{abs(hash(url))}",
            provider="system76",
            title=url,
            url=url,
            trust_level="official",
            summary=sanitize_output(text, max_chars=2400),
            record_mode="live-web-fetch",
        )


@dataclass
class GitHubCosmicProvider(ResearchProvider):
    enabled: bool = False

    def search(self, query: str, *, max_results: int = 8) -> list[dict]:
        if not self.enabled:
            return []
        safe_query = urllib.parse.quote_plus(f"{query} repo:pop-os/cosmic-epoch repo:pop-os/pop repo:pop-os/pop-upgrade")
        url = f"https://api.github.com/search/issues?q={safe_query}&per_page={max_results}"
        try:
            with urllib.request.urlopen(url, timeout=12) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, json.JSONDecodeError):
            return []
        records = []
        for item in payload.get("items", [])[:max_results]:
            records.append(
                _source_record(
                    source_id=f"github-{item.get('number', abs(hash(item.get('html_url', ''))))}",
                    provider="github",
                    title=item.get("title", "GitHub issue"),
                    url=item.get("html_url", ""),
                    published_or_updated=item.get("updated_at", "unknown"),
                    trust_level="maintainer",
                    summary=item.get("title", ""),
                    relevant_evidence=[item.get("state", "unknown")],
                    applies_to={"pop_version": "unknown", "cosmic_version": "Epoch 1|unknown", "hardware": "unknown"},
                    record_mode="live-web-search",
                )
            )
        return records

    def fetch(self, url: str) -> dict:
        if not self.enabled:
            raise ValueError("GitHub research is disabled.")
        if not _domain_allowed(url):
            raise ValueError("URL domain is not allowed for Pop/COSMIC research.")
        with urllib.request.urlopen(url, timeout=12) as response:
            text = response.read(25000).decode("utf-8", errors="replace")
        return _source_record(
            source_id=f"github-fetched-{abs(hash(url))}",
            provider="github",
            title=url,
            url=url,
            trust_level="maintainer",
            summary=sanitize_output(text, max_chars=2400),
            record_mode="live-web-fetch",
        )


@dataclass
class ManualSourceProvider(ResearchProvider):
    notes: str = ""

    def search(self, query: str, *, max_results: int = 8) -> list[dict]:
        if not self.notes.strip():
            return []
        return [
            _source_record(
                source_id="manual-source-1",
                provider="manual",
                title="User-provided source notes",
                url="manual://user-notes",
                trust_level="unknown",
                summary=self.notes,
                relevant_evidence=[query],
                record_mode="manual-local",
            )
        ]

    def fetch(self, url: str) -> dict:
        return self.search(url)[0]


def safe_research_query(symptom: str, profile: dict) -> str:
    parts = [
        "Pop!_OS",
        str(profile.get("pop_version", "unknown")),
        "COSMIC",
        symptom,
    ]
    query = " ".join(parts)
    return sanitize_output(" ".join(query.split()), max_chars=240)


def research_pop_cosmic_issue(
    symptom: str,
    profile: dict,
    *,
    enabled: bool = False,
    include_github: bool = False,
    manual_notes: str = "",
    max_results: int = 8,
    governance: dict | None = None,
) -> dict:
    query = safe_research_query(symptom, profile)
    live_web_enabled = bool(enabled)
    providers: list[ResearchProvider] = [
        OfficialSystem76Provider(enabled=live_web_enabled),
        ManualSourceProvider(manual_notes),
    ]
    if include_github:
        providers.append(GitHubCosmicProvider(enabled=live_web_enabled))
    records: list[dict] = []
    for provider in providers:
        records.extend(provider.search(query, max_results=max_results))
        if len(records) >= max_results:
            break
    if live_web_enabled and include_github:
        research_mode = "live-web-search"
    elif manual_notes.strip():
        research_mode = "local-manual-and-official-metadata"
    else:
        research_mode = "official-source-metadata-only"
    return {
        "generated_at": _now(),
        "enabled": live_web_enabled,
        "live_web_enabled": live_web_enabled,
        "research_mode": research_mode,
        "query": query,
        "records": records[:max_results],
        "governance": governance or {},
        "privacy": "Raw local logs are not sent to research providers; only the sanitized symptom/profile query is used.",
    }
