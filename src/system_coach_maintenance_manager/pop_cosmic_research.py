"""Source-aware Pop!_OS/COSMIC research helpers."""

from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
import json
import os
import urllib.error
import urllib.parse
import urllib.request

from .pop_cosmic_deep_scan import sanitize_output


OFFICIAL_SYSTEM76_HOSTS = (
    "system76.com",
    "support.system76.com",
    "blog.system76.com",
)
OFFICIAL_POP_OS_REPOS = (
    "cosmic-comp",
    "cosmic-epoch",
    "cosmic-launcher",
    "cosmic-panel",
    "cosmic-session",
    "cosmic-settings",
    "cosmic-store",
    "pop",
    "pop-upgrade",
)
ALLOWED_DOMAINS = (
    *OFFICIAL_SYSTEM76_HOSTS,
    "github.com/pop-os",
    "api.github.com/repos/pop-os",
    "api.github.com/search/issues",
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


def _parsed_https_url(url: str) -> urllib.parse.ParseResult:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme.lower() != "https" or not parsed.netloc:
        raise ValueError("Pop/COSMIC research URLs must use HTTPS.")
    return parsed


def _path_segments(path: str) -> list[str]:
    return [segment for segment in path.split("/") if segment]


def is_official_system76_url(url: str) -> bool:
    try:
        parsed = _parsed_https_url(url)
    except ValueError:
        return False
    host = parsed.netloc.lower()
    return host in OFFICIAL_SYSTEM76_HOSTS


def is_official_pop_os_github_url(url: str) -> bool:
    try:
        parsed = _parsed_https_url(url)
    except ValueError:
        return False
    host = parsed.netloc.lower()
    segments = _path_segments(parsed.path)
    if host == "github.com":
        return len(segments) >= 2 and segments[0].lower() == "pop-os" and segments[1].lower() in OFFICIAL_POP_OS_REPOS
    if host == "api.github.com":
        if len(segments) >= 4 and segments[0] == "repos" and segments[1].lower() == "pop-os":
            return segments[2].lower() in OFFICIAL_POP_OS_REPOS
        return segments[:2] == ["search", "issues"]
    return False


def research_url_allowed(url: str) -> bool:
    return is_official_system76_url(url) or is_official_pop_os_github_url(url)


def _domain_allowed(url: str, allowed_domains: tuple[str, ...] = ALLOWED_DOMAINS) -> bool:
    if research_url_allowed(url):
        return True
    try:
        parsed = _parsed_https_url(url)
    except ValueError:
        return False
    host = parsed.netloc.lower()
    path = "/" + "/".join(_path_segments(parsed.path))
    for allowed in allowed_domains:
        allowed = allowed.strip().lower()
        if not allowed:
            continue
        allowed_parsed = urllib.parse.urlparse(allowed if "://" in allowed else f"https://{allowed}")
        allowed_host = allowed_parsed.netloc.lower()
        allowed_path = "/" + "/".join(_path_segments(allowed_parsed.path))
        if host == allowed_host and (allowed_path == "/" or path.startswith(allowed_path)):
            return True
    return False


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
            raise ValueError("URL is not an official System76 Pop/COSMIC source.")
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
            html_url = item.get("html_url", "")
            if not research_url_allowed(html_url):
                continue
            records.append(
                _source_record(
                    source_id=f"github-{item.get('number', abs(hash(item.get('html_url', ''))))}",
                    provider="github",
                    title=item.get("title", "GitHub issue"),
                    url=html_url,
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
            raise ValueError("URL is not an official Pop/COSMIC GitHub source.")
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


def _read_env_file_value(path: str, variable_name: str) -> str:
    if not path:
        return ""
    env_path = os.path.expanduser(path)
    if not os.path.exists(env_path):
        return ""
    try:
        lines = open(env_path, encoding="utf-8").read().splitlines()
    except OSError:
        return ""
    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        if key != variable_name:
            continue
        value = value.strip().strip("\"'")
        return value
    return ""


def _secret_from_env_or_master(variable_name: str, master_env_path: str) -> str:
    return os.environ.get(variable_name, "").strip() or _read_env_file_value(master_env_path, variable_name).strip()


@dataclass
class PerplexityResearchProvider(ResearchProvider):
    enabled: bool = False
    allowed_domains: tuple[str, ...] = ALLOWED_DOMAINS
    api_key_env_var: str = "PERPLEXITY_API_KEY"
    model_env_var: str = "PERPLEXITY_MODEL"
    master_env_path: str = ""
    default_model: str = "sonar-pro"

    def _api_key(self) -> str:
        return _secret_from_env_or_master(self.api_key_env_var, self.master_env_path)

    def _model(self) -> str:
        return _secret_from_env_or_master(self.model_env_var, self.master_env_path) or self.default_model

    def search(self, query: str, *, max_results: int = 8) -> list[dict]:
        if not self.enabled:
            return []
        secret_token = self._api_key()
        if not secret_token:
            return [
                _source_record(
                    source_id="perplexity-key-missing",
                    provider="perplexity",
                    title="Perplexity API key unavailable",
                    url="https://docs.perplexity.ai/",
                    trust_level="provider-config",
                    summary=f"Live Perplexity research is enabled, but {self.api_key_env_var} was not found in the environment or master env file.",
                    risk_notes=["No remote research call was made."],
                    record_mode="live-web-unavailable",
                )
            ]

        payload = {
            "model": self._model(),
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Research Pop!_OS and COSMIC desktop troubleshooting using concise, source-grounded findings. "
                        "Prefer official System76 and Pop!_OS GitHub sources. Do not recommend destructive fixes."
                    ),
                },
                {"role": "user", "content": query},
            ],
            "temperature": 0.1,
            "max_tokens": 900,
            "search_domain_filter": list(self.allowed_domains)[:20],
        }
        request = urllib.request.Request(
            "https://api.perplexity.ai/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {secret_token}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            return [
                _source_record(
                    source_id="perplexity-request-failed",
                    provider="perplexity",
                    title="Perplexity research request failed",
                    url="https://docs.perplexity.ai/",
                    trust_level="provider-config",
                    summary=f"Perplexity research failed: {exc}",
                    risk_notes=["No external research result was trusted for this run."],
                    record_mode="live-web-error",
                )
            ]

        answer = (
            (data.get("choices") or [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        records = []
        if answer:
            records.append(
                _source_record(
                    source_id=f"perplexity-answer-{abs(hash(answer))}",
                    provider="perplexity",
                    title="Perplexity source-grounded research summary",
                    url="https://www.perplexity.ai/",
                    trust_level="search-synthesis",
                    summary=answer,
                    relevant_evidence=[query],
                    risk_notes=["Treat synthesis as a research aid; verify risky fixes against cited sources and guarded catalogs."],
                    record_mode="live-web-search",
                )
            )

        seen_urls = set()
        result_items = data.get("search_results") or []
        for item in result_items:
            url = str(item.get("url", "")).strip()
            if not url or url in seen_urls or not _domain_allowed(url, self.allowed_domains):
                continue
            seen_urls.add(url)
            records.append(
                _source_record(
                    source_id=f"perplexity-result-{abs(hash(url))}",
                    provider="perplexity",
                    title=item.get("title") or url,
                    url=url,
                    published_or_updated=item.get("date") or "unknown",
                    trust_level="allowed-web",
                    summary=item.get("snippet") or item.get("title") or "Allowed Perplexity search result.",
                    relevant_evidence=[query],
                    record_mode="live-web-search",
                )
            )
            if len(records) >= max_results:
                break

        for url in data.get("citations", []):
            url = str(url).strip()
            if not url or url in seen_urls or not _domain_allowed(url, self.allowed_domains):
                continue
            seen_urls.add(url)
            records.append(
                _source_record(
                    source_id=f"perplexity-citation-{abs(hash(url))}",
                    provider="perplexity",
                    title=url,
                    url=url,
                    trust_level="allowed-web",
                    summary="Allowed Perplexity citation for the source-grounded answer.",
                    relevant_evidence=[query],
                    record_mode="live-web-search",
                )
            )
            if len(records) >= max_results:
                break
        return records[:max_results]

    def fetch(self, url: str) -> dict:
        raise ValueError("Perplexity provider supports source-grounded search records, not arbitrary URL fetches.")


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
    research_provider: str = "official",
    allowed_domains: list[str] | tuple[str, ...] | None = None,
    perplexity_config: dict | None = None,
) -> dict:
    query = safe_research_query(symptom, profile)
    live_web_enabled = bool(enabled)
    allowed_domain_tuple = tuple(allowed_domains or ALLOWED_DOMAINS)
    providers: list[ResearchProvider] = [
        OfficialSystem76Provider(enabled=live_web_enabled),
        ManualSourceProvider(manual_notes),
    ]
    if live_web_enabled and research_provider == "perplexity":
        config = perplexity_config or {}
        providers.append(
            PerplexityResearchProvider(
                enabled=True,
                allowed_domains=allowed_domain_tuple,
                api_key_env_var=str(config.get("api_key_env_var") or "PERPLEXITY_API_KEY"),
                model_env_var=str(config.get("model_env_var") or "PERPLEXITY_MODEL"),
                master_env_path=str(config.get("master_env_path") or ""),
            )
        )
    if include_github:
        providers.append(GitHubCosmicProvider(enabled=live_web_enabled))
    records: list[dict] = []
    for provider in providers:
        records.extend(provider.search(query, max_results=max_results))
        if len(records) >= max_results:
            break
    if live_web_enabled and research_provider == "perplexity":
        research_mode = "live-web-perplexity-search"
    elif live_web_enabled and include_github:
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
