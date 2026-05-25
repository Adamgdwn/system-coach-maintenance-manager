"""Native GTK desktop shell for the system coach."""

from __future__ import annotations

import datetime as dt
import json
import threading

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")

from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from .agents import build_agents
from .ai_engine import analyze_action_result, answer_question, get_engine_status, reason_about_maintenance_plan, reason_about_request
from .diagnostics import collect_diagnostics
from .exporting import build_share_text
from .followup_plans import build_followup_request
from .maintenance_actions import execute_guarded_action
from .maintenance_history import (
    apply_recent_fix_overrides,
    format_history,
    load_history,
    record_learning_note,
    record_maintenance_report,
    record_request_plan,
)
from .maintenance_history import record_action_result
from .maintenance_reporting import generate_maintenance_report
from .model_providers import model_provider_status
from .pop_cosmic_actions import make_verification_lesson, prepare_pop_cosmic_action, prepare_verification_plan
from .pop_cosmic_brain import analyze_pop_cosmic_issue
from .pop_cosmic_controls import load_pop_cosmic_controls
from .pop_cosmic_deep_scan import run_pop_cosmic_deep_scan
from .pop_cosmic_knowledge import load_relevant_lessons, load_relevant_research, save_lesson, save_research_records
from .pop_cosmic_research import research_pop_cosmic_issue
from .reporting import generate_report
from .request_evidence import collect_request_evidence
from .request_plans import format_request_plan, prepare_request_plan, review_request_intake
from .scanner import map_filesystem, suggest_roots


DESKTOP_CSS = b"""
window {
  background-color: #f4efe6;
  color: #2b2115;
  font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
}

.app-scroll {
  background-color: #f4efe6;
  border: 0;
}

.app-root {
  padding: 20px;
  background-image:
    radial-gradient(circle at top left, rgba(12, 122, 97, 0.14), transparent 28%),
    radial-gradient(circle at top right, rgba(191, 95, 47, 0.16), transparent 24%),
    linear-gradient(to bottom, #faf5ec, #f4efe6);
}

.hero-panel {
  padding: 18px;
  border-radius: 22px;
  border: 1px solid rgba(84, 62, 34, 0.16);
  background-image: linear-gradient(135deg, rgba(255, 250, 243, 0.96), rgba(239, 226, 204, 0.92));
  box-shadow: 0 20px 45px rgba(86, 67, 39, 0.12);
}

.eyebrow-label {
  color: #0c7a61;
  letter-spacing: 0.18em;
  font-size: 11px;
  font-weight: 700;
}

.hero-title {
  color: #2b2115;
  font-size: 26px;
  font-weight: 800;
}

.hero-subtitle,
.muted-label {
  color: #705d43;
}

.status-strip {
  padding: 8px 12px;
  border-radius: 14px;
  border: 1px solid rgba(12, 122, 97, 0.15);
  background-color: rgba(12, 122, 97, 0.07);
  color: #2b2115;
}

.engine-strip {
  padding: 8px 12px;
  border-radius: 14px;
  border: 1px solid rgba(191, 95, 47, 0.16);
  background-color: rgba(191, 95, 47, 0.07);
  color: #705d43;
}

.working-drama {
  padding: 22px 26px;
  border-radius: 22px;
  border: 1px solid rgba(191, 95, 47, 0.26);
  background-color: rgba(255, 250, 243, 0.96);
  box-shadow: 0 22px 55px rgba(43, 33, 21, 0.18);
}

.working-symbol {
  color: #bf5f2f;
  font-size: 42px;
  font-weight: 900;
}

.working-title {
  color: #2b2115;
  font-size: 15px;
  font-weight: 900;
}

.working-detail {
  color: #705d43;
}

button {
  min-height: 38px;
  padding: 8px 16px;
  border-radius: 999px;
  border: 0;
  color: #ffffff;
  background-image: linear-gradient(135deg, #0c7a61, #0a5d4a);
  box-shadow: 0 10px 20px rgba(12, 122, 97, 0.22);
}

button label {
  color: #ffffff;
  font-weight: 700;
}

button:hover {
  background-image: linear-gradient(135deg, #108c70, #0b6954);
}

button:disabled {
  opacity: 0.62;
}

.secondary-button {
  background-image: linear-gradient(135deg, #bf5f2f, #9f461c);
  box-shadow: 0 10px 20px rgba(191, 95, 47, 0.18);
}

.secondary-button:hover {
  background-image: linear-gradient(135deg, #cf6b38, #aa4c20);
}

frame.panel-frame {
  padding: 8px;
  border-radius: 18px;
  border: 1px solid rgba(84, 62, 34, 0.16);
  background-color: rgba(255, 252, 247, 0.90);
  box-shadow: 0 14px 30px rgba(86, 67, 39, 0.10);
}

frame.panel-frame > label {
  margin-left: 12px;
  margin-bottom: 4px;
  color: #2b2115;
  font-weight: 800;
}

notebook {
  border: 0;
  background-color: transparent;
}

notebook tab {
  min-height: 34px;
  padding: 7px 12px;
  border-radius: 12px 12px 0 0;
  background-color: rgba(255, 252, 247, 0.68);
  border: 1px solid rgba(84, 62, 34, 0.12);
}

notebook tab:checked {
  background-color: #fffaf3;
  border-color: rgba(12, 122, 97, 0.22);
}

notebook tab label {
  color: #705d43;
  font-weight: 700;
}

entry,
textview,
list,
combobox,
scrolledwindow {
  border-radius: 14px;
  border: 1px solid rgba(84, 62, 34, 0.14);
  background-color: #fffaf3;
  color: #2b2115;
}

entry {
  padding: 9px 12px;
}

textview text,
textview.view text {
  padding: 12px;
  background-color: #fffaf3;
  color: #2b2115;
}

textview.view {
  background-color: #fffaf3;
  color: #2b2115;
}

checkbutton label,
label {
  color: #2b2115;
}

flowboxchild {
  border-radius: 999px;
}

paned separator {
  background-color: rgba(84, 62, 34, 0.14);
}
"""


def build_report() -> dict:
    results = [agent.run() for agent in build_agents()]
    return generate_report(results)


def build_maintenance_report() -> dict:
    return apply_recent_fix_overrides(generate_maintenance_report(collect_diagnostics()))


class SystemCoachWindow(Gtk.ApplicationWindow):
    DEFAULT_WINDOW_WIDTH = 1120
    DEFAULT_WINDOW_HEIGHT = 720
    MIN_VIEWPORT_WIDTH = 720
    MIN_VIEWPORT_HEIGHT = 420
    NARROW_LAYOUT_WIDTH = 1120
    REQUEST_BRAIN_TIMEOUT_SECONDS = 45

    def __init__(self, app: Gtk.Application):
        super().__init__(application=app, title="System Coach and Maintenance Manager")
        self._install_theme()
        self.set_default_size(self.DEFAULT_WINDOW_WIDTH, self.DEFAULT_WINDOW_HEIGHT)
        self.set_resizable(True)
        self.set_border_width(0)

        self.current_report: dict | None = None
        self.current_map: dict | None = None
        self.current_maintenance: dict | None = None
        self.current_request_plan: dict | None = None
        self.current_history: dict | None = None
        self.engine_status: dict | None = None
        self.queued_plans: list[dict] = []
        self.request_context: list[str] = []
        self.latest_request_reasoning: dict | None = None
        self.active_request_brain_token: int | None = None
        self.request_brain_sequence = 0
        self.pop_cosmic_scan: dict | None = None
        self.pop_cosmic_research: dict | None = None
        self.pop_cosmic_analysis: dict | None = None
        self.pop_cosmic_plan: dict | None = None
        self.pop_cosmic_result: dict | None = None
        self.working_pulse_id: int | None = None
        self.working_pulse_step = 0

        self.app_overlay = Gtk.Overlay()
        self.app_overlay.set_hexpand(True)
        self.app_overlay.set_vexpand(True)
        self.add(self.app_overlay)

        outer_scroll = Gtk.ScrolledWindow()
        self._add_class(outer_scroll, "app-scroll")
        outer_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        outer_scroll.set_min_content_width(self.MIN_VIEWPORT_WIDTH)
        outer_scroll.set_min_content_height(self.MIN_VIEWPORT_HEIGHT)
        outer_scroll.set_hexpand(True)
        outer_scroll.set_vexpand(True)
        self.app_overlay.add(outer_scroll)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self._add_class(root, "app-root")
        root.set_hexpand(True)
        root.set_vexpand(True)
        outer_scroll.add(root)

        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._add_class(header, "hero-panel")
        root.pack_start(header, False, False, 0)

        eyebrow = Gtk.Label(label="SYSTEM COACH AND MAINTENANCE MANAGER")
        self._add_class(eyebrow, "eyebrow-label")
        eyebrow.set_xalign(0)
        header.pack_start(eyebrow, False, False, 0)

        title = Gtk.Label()
        title.set_markup("<span size='24000' weight='bold'>System Coach and Maintenance Manager</span>")
        self._add_class(title, "hero-title")
        title.set_xalign(0)
        header.pack_start(title, False, False, 0)

        subtitle = Gtk.Label(
            label=(
                "A local teaching tool for understanding your environment, installed tools, "
                "and selected folders without sending data anywhere else."
            )
        )
        self._add_class(subtitle, "hero-subtitle")
        subtitle.set_xalign(0)
        subtitle.set_line_wrap(True)
        header.pack_start(subtitle, False, False, 0)

        action_row = self._make_wrapping_flow()
        root.pack_start(action_row, False, False, 0)

        self.review_button = Gtk.Button(label="Run Local Review")
        self.review_button.connect("clicked", self.on_run_review)
        action_row.add(self.review_button)

        self.map_button = Gtk.Button(label="Scan Selected Roots")
        self._add_class(self.map_button, "secondary-button")
        self.map_button.connect("clicked", self.on_run_map)
        action_row.add(self.map_button)

        self.maintenance_button = Gtk.Button(label="Run Maintenance Diagnostics")
        self._add_class(self.maintenance_button, "secondary-button")
        self.maintenance_button.connect("clicked", self.on_run_maintenance)
        action_row.add(self.maintenance_button)

        self.share_button = Gtk.Button(label="Copy Share Summary")
        self._add_class(self.share_button, "secondary-button")
        self.share_button.connect("clicked", self.on_copy_summary)
        action_row.add(self.share_button)

        self.status_label = Gtk.Label(label="Ready. Run a review to learn the environment.")
        self._add_class(self.status_label, "status-strip")
        self.status_label.set_hexpand(True)
        self.status_label.set_xalign(0)
        self.status_label.set_line_wrap(True)

        self.engine_label = Gtk.Label(label="Checking local AI engine...")
        self._add_class(self.engine_label, "engine-strip")
        self.engine_label.set_hexpand(True)
        self.engine_label.set_xalign(0)
        self.engine_label.set_line_wrap(True)

        status_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        status_row.pack_start(self.status_label, True, True, 0)
        status_row.pack_start(self.engine_label, True, True, 0)
        root.pack_start(status_row, False, False, 0)

        self.content_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.content_paned.set_wide_handle(True)
        root.pack_start(self.content_paned, True, True, 0)

        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.content_paned.add1(left)
        self.content_paned.add2(right)
        self.content_paned.set_position(540)

        self.summary_view = self._make_text_view()
        left.pack_start(self._frame("Summary", self.summary_view), True, True, 0)

        self.environment_view = self._make_text_view()
        left.pack_start(self._frame("Environment", self.environment_view), True, True, 0)

        self.learning_view = self._make_text_view()
        left.pack_start(self._frame("Learning Path", self.learning_view), True, True, 0)

        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        right.pack_start(self.notebook, True, True, 0)

        self.components_view = self._make_text_view()
        self.notebook.append_page(self._frame("Detected Components", self.components_view), Gtk.Label(label="Components"))

        self.stacks_view = self._make_text_view()
        self.notebook.append_page(self._frame("Stack Patterns And Tips", self.stacks_view), Gtk.Label(label="Stacks"))

        self.scan_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.scan_page.set_border_width(6)
        self.notebook.append_page(self.scan_page, Gtk.Label(label="Find And Map"))
        self._build_scan_page()

        self.maintenance_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.maintenance_page.set_border_width(6)
        self.notebook.append_page(self.maintenance_page, Gtk.Label(label="Maintenance"))
        self._build_maintenance_page()

        self.pop_cosmic_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.pop_cosmic_page.set_border_width(6)
        self.notebook.append_page(self.pop_cosmic_page, Gtk.Label(label="Pop!_OS + COSMIC"))
        self._build_pop_cosmic_page()

        self.request_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.request_page.set_border_width(6)
        self.notebook.append_page(self.request_page, Gtk.Label(label="Request Desk"))
        self._build_request_page()

        self.approval_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.approval_page.set_border_width(6)
        self.notebook.append_page(self.approval_page, Gtk.Label(label="Approval Queue"))
        self._build_approval_page()

        self.history_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.history_page.set_border_width(6)
        self.notebook.append_page(self.history_page, Gtk.Label(label="History"))
        self._build_history_page()

        self.coach_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.coach_page.set_border_width(6)
        self.notebook.append_page(self.coach_page, Gtk.Label(label="Ask The Coach"))
        self._build_coach_page()

        self.model_provider_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.model_provider_page.set_border_width(6)
        self.notebook.append_page(self.model_provider_page, Gtk.Label(label="Model Providers"))
        self._build_model_provider_page()

        self.command_view = self._make_text_view()
        self.notebook.append_page(self._frame("Command Log", self.command_view), Gtk.Label(label="Command Log"))

        self._build_working_overlay()
        self._content_orientation: Gtk.Orientation | None = None
        self.connect("size-allocate", self._on_size_allocate)
        self.show_all()
        self._hide_working_drama()
        self._refresh_engine_status()
        self._refresh_model_provider_status()
        self.on_run_review(None)
        self.on_run_maintenance(None)
        self.on_refresh_history(None)
        self._refresh_approval_queue()

    def _install_theme(self) -> None:
        provider = Gtk.CssProvider()
        provider.load_from_data(DESKTOP_CSS)
        screen = Gdk.Screen.get_default()
        if screen is not None:
            Gtk.StyleContext.add_provider_for_screen(
                screen,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

    def _add_class(self, widget: Gtk.Widget, class_name: str) -> None:
        widget.get_style_context().add_class(class_name)

    def _make_text_view(self) -> Gtk.TextView:
        view = Gtk.TextView()
        self._add_class(view, "report-view")
        view.set_editable(False)
        view.set_cursor_visible(False)
        view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        view.set_left_margin(10)
        view.set_right_margin(10)
        return view

    def _make_wrapping_flow(self) -> Gtk.FlowBox:
        flow = Gtk.FlowBox()
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_column_spacing(8)
        flow.set_row_spacing(8)
        flow.set_max_children_per_line(20)
        flow.set_homogeneous(False)
        flow.set_valign(Gtk.Align.START)
        return flow

    def _frame(self, title: str, widget: Gtk.Widget) -> Gtk.Frame:
        frame = Gtk.Frame(label=title)
        self._add_class(frame, "panel-frame")
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_hexpand(True)
        scroll.set_vexpand(True)
        scroll.add(widget)
        frame.add(scroll)
        frame.set_hexpand(True)
        frame.set_vexpand(True)
        return frame

    def _format_plan_details(self, plan: dict) -> str:
        commands = plan.get("commands", [])
        manual_steps = plan.get("manual_steps", [])
        rollback = plan.get("rollback", [])
        lines = [
            plan["title"],
            f"Family: {plan.get('family', plan.get('finding_id', 'maintenance'))}",
            f"Platform: {plan.get('platform', 'Current system')}",
            f"Risk: {plan['risk']}",
            f"Requires privilege: {plan['requires_privilege']}",
            f"Reversible: {plan['reversible']}",
            f"Approval required: {plan['approval_required']}",
            f"Execution enabled: {plan['execution_enabled']}",
            "Commands:",
            *[f"- {command}" for command in commands],
        ]
        if not commands:
            lines.append("- No commands prepared yet.")
        if manual_steps:
            lines.extend(["Manual steps:", *[f"- {step}" for step in manual_steps]])
        lines.extend([f"Expected effect: {plan['expected_effect']}"])
        if rollback:
            lines.extend(["Rollback:", *[f"- {step}" for step in rollback]])
        lines.append(f"Approval gate: {plan['approval_prompt']}")
        contract = plan.get("action_contract")
        if contract:
            gate_reasons = contract.get("execution_gate", {}).get("reasons", [])
            lines.extend(
                [
                    "Action runner contract:",
                    f"- Contract: {contract['contract_version']}",
                    f"- Action id: {contract['id']}",
                    f"- Eligible for guarded execution: {contract['eligible_for_guarded_execution']}",
                    f"- Execution enabled: {contract['execution_enabled']}",
                    f"- Execution mode: {contract.get('execution_mode', 'user')}",
                    f"- Confirmation phrase: {contract['confirmation_phrase']}",
                    *[f"- Gate: {reason}" for reason in gate_reasons],
                    *[f"- Post-check: {item}" for item in contract.get("post_check", [])],
                ]
            )
        return "\n".join(lines)

    def _build_scan_page(self) -> None:
        intro = Gtk.Label(
            label=(
                "Choose folders the app is allowed to inspect. Scans are opt-in and local-only. "
                "Use this to find projects, config files, and the general shape of the system."
            )
        )
        intro.set_xalign(0)
        intro.set_line_wrap(True)
        self.scan_page.pack_start(intro, False, False, 0)

        suggestions_label = Gtk.Label(label="Suggested roots")
        suggestions_label.set_xalign(0)
        self.scan_page.pack_start(suggestions_label, False, False, 0)

        self.roots_list = Gtk.ListBox()
        roots_scroll = Gtk.ScrolledWindow()
        roots_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        roots_scroll.set_min_content_height(120)
        roots_scroll.add(self.roots_list)
        self.scan_page.pack_start(roots_scroll, False, False, 0)

        for root in suggest_roots():
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            check = Gtk.CheckButton(label=root["path"])
            check.set_active(root["path"] == GLib.get_home_dir())
            box.pack_start(check, True, True, 0)
            row.add(box)
            row.check = check
            self.roots_list.add(row)

        custom_label = Gtk.Label(label="Custom roots, one per line")
        custom_label.set_xalign(0)
        self.scan_page.pack_start(custom_label, False, False, 0)

        self.custom_roots_view = Gtk.TextView()
        self.custom_roots_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        custom_scroll = Gtk.ScrolledWindow()
        custom_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        custom_scroll.set_min_content_height(90)
        custom_scroll.add(self.custom_roots_view)
        self.scan_page.pack_start(custom_scroll, False, False, 0)

        self.map_results_view = self._make_text_view()
        self.scan_page.pack_start(self._frame("System Map", self.map_results_view), True, True, 0)

    def _build_maintenance_page(self) -> None:
        intro = Gtk.Label(
            label=(
                "Run read-only diagnostics for system health, troubleshooting evidence, and approval-required "
                "maintenance plans. This phase prepares plans but does not execute fixes."
            )
        )
        intro.set_xalign(0)
        intro.set_line_wrap(True)
        self.maintenance_page.pack_start(intro, False, False, 0)

        action_row = self._make_wrapping_flow()
        self.maintenance_page.pack_start(action_row, False, False, 0)

        self.maintenance_page_button = Gtk.Button(label="Diagnose System Health")
        self.maintenance_page_button.connect("clicked", self.on_run_maintenance)
        action_row.add(self.maintenance_page_button)

        self.review_findings_button = Gtk.Button(label="Review Findings")
        self.review_findings_button.connect("clicked", self.on_review_findings)
        action_row.add(self.review_findings_button)

        self.review_backlog_fix_button = Gtk.Button(label="Review & Approve Backlog Fix")
        self.review_backlog_fix_button.set_tooltip_text(
            "Open the next executable maintenance plan from the latest diagnostics. Runs only after APPROVE."
        )
        self.review_backlog_fix_button.connect("clicked", self.on_review_next_backlog_fix)
        action_row.add(self.review_backlog_fix_button)

        self.maintenance_summary_view = self._make_text_view()
        self.maintenance_page.pack_start(
            self._frame("Maintenance Summary And Findings", self.maintenance_summary_view),
            True,
            True,
            0,
        )

        self.maintenance_plans_view = self._make_text_view()
        self.maintenance_page.pack_start(
            self._frame("Approval-Required Plans", self.maintenance_plans_view),
            True,
            True,
            0,
        )

    def _build_pop_cosmic_page(self) -> None:
        intro = Gtk.Label(
            label=(
                "Guided Pop!_OS + COSMIC agent: scan local evidence, optionally research trusted sources, "
                "ask the local model ladder, build one exact fix plan, execute only after approval, then verify and learn."
            )
        )
        intro.set_xalign(0)
        intro.set_line_wrap(True)
        self.pop_cosmic_page.pack_start(intro, False, False, 0)

        self.pop_cosmic_concern_view = Gtk.TextView()
        self.pop_cosmic_concern_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        concern_scroll = Gtk.ScrolledWindow()
        concern_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        concern_scroll.set_min_content_height(90)
        concern_scroll.add(self.pop_cosmic_concern_view)
        self.pop_cosmic_page.pack_start(self._frame("Concern", concern_scroll), False, False, 0)

        controls = self._make_wrapping_flow()
        self.pop_cosmic_page.pack_start(controls, False, False, 0)

        self.pop_cosmic_scope = Gtk.ComboBoxText()
        for scope in ("standard", "display", "updates", "full"):
            self.pop_cosmic_scope.append_text(scope)
        self.pop_cosmic_scope.set_active(0)
        controls.add(self.pop_cosmic_scope)

        for label, handler in [
            ("Run Deep Scan", self.on_pop_cosmic_scan),
            ("Research Current Issue", self.on_pop_cosmic_research),
            ("Ask Local Model", self.on_pop_cosmic_analyze),
            ("Build Fix Plan", self.on_pop_cosmic_plan),
            ("Execute Approved Step", self.on_pop_cosmic_execute),
            ("Verify Fix", self.on_pop_cosmic_verify),
        ]:
            button = Gtk.Button(label=label)
            button.connect("clicked", handler)
            controls.add(button)

        self.pop_cosmic_profile_view = self._make_text_view()
        self.pop_cosmic_page.pack_start(self._frame("Environment And Scan", self.pop_cosmic_profile_view), True, True, 0)

        self.pop_cosmic_analysis_view = self._make_text_view()
        self.pop_cosmic_page.pack_start(self._frame("Analysis, Research, And Actions", self.pop_cosmic_analysis_view), True, True, 0)

        self.pop_cosmic_action_view = self._make_text_view()
        self.pop_cosmic_page.pack_start(self._frame("Action Log", self.pop_cosmic_action_view), True, True, 0)

    def _build_request_page(self) -> None:
        intro = Gtk.Label(
            label=(
                "Describe the issue like you would to a technician. The desk will ask for missing details, "
                "then prepare a guarded plan with exact commands and rollback notes."
            )
        )
        intro.set_xalign(0)
        intro.set_line_wrap(True)
        self.request_page.pack_start(intro, False, False, 0)

        prompts_row = self._make_wrapping_flow()
        self.request_page.pack_start(prompts_row, False, False, 0)
        for label, prompt in [
            ("Display or Dock", "A monitor, dock, cursor, scaling, rotation, or display layout is acting wrong."),
            ("Audio", "My audio input or output is wrong."),
            ("Network", "DNS, Wi-Fi, routing, or internet connectivity seems broken."),
            ("Slow Computer", "My computer feels slow or laggy. Investigate and suggest the best fix."),
            ("Packages", "Package updates or installs are failing. Investigate before repairing."),
            ("Docker", "Review Docker disk usage and cleanup options."),
            ("Startup", "Review startup apps and services that may be slowing login."),
        ]:
            button = Gtk.Button(label=label)
            button.set_tooltip_text(prompt)
            button.connect("clicked", self.on_prompt_clicked, prompt)
            prompts_row.add(button)

        self.request_entry = Gtk.Entry()
        self.request_entry.set_placeholder_text("Type a request or answer a follow-up question...")
        self.request_entry.connect("activate", self.on_request_send)

        input_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        input_row.pack_start(self.request_entry, True, True, 0)
        self.request_send_button = Gtk.Button(label="Send")
        self.request_send_button.connect("clicked", self.on_request_send)
        input_row.pack_start(self.request_send_button, False, False, 0)
        self.request_page.pack_start(input_row, False, False, 0)

        action_row = self._make_wrapping_flow()
        self.request_page.pack_start(action_row, False, False, 0)
        self.prepare_request_button = Gtk.Button(label="Prepare Plan Now")
        self.prepare_request_button.connect("clicked", self.on_prepare_request_plan)
        action_row.add(self.prepare_request_button)

        self.execute_request_button = Gtk.Button(label="Execute Current Recommendation")
        self.execute_request_button.set_tooltip_text("Run the current recommendation when its guarded contract is enabled.")
        self.execute_request_button.set_sensitive(False)
        self.execute_request_button.connect("clicked", self.on_execute_current_request)
        action_row.add(self.execute_request_button)

        self.clear_request_button = Gtk.Button(label="Clear Conversation")
        self.clear_request_button.connect("clicked", self.on_clear_request_conversation)
        action_row.add(self.clear_request_button)

        self.request_plan_view = self._make_text_view()
        self.request_page.pack_start(self._frame("Current Recommendation", self.request_plan_view), True, True, 0)

        self.request_thread_view = self._make_text_view()
        self.request_page.pack_start(self._frame("Conversation", self.request_thread_view), True, True, 0)

    def _build_approval_page(self) -> None:
        intro = Gtk.Label(
            label=(
                "Review prepared maintenance and request plans before execution. "
                "Press Execute to run the selected plan when its guarded contract is enabled."
            )
        )
        intro.set_xalign(0)
        intro.set_line_wrap(True)
        self.approval_page.pack_start(intro, False, False, 0)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.approval_page.pack_start(controls, False, False, 0)

        self.approval_plan_picker = Gtk.ComboBoxText()
        self.approval_plan_picker.set_hexpand(True)
        self.approval_plan_picker.connect("changed", self.on_approval_selection_changed)
        controls.pack_start(self.approval_plan_picker, True, True, 0)

        self.review_action_button = Gtk.Button(label="Review Selected Plan")
        self.review_action_button.set_tooltip_text("Inspect risk, command preview, rollback, and execution gate reasons.")
        self.review_action_button.connect("clicked", self.on_review_selected_action)
        controls.pack_start(self.review_action_button, False, False, 0)

        self.execute_action_button = Gtk.Button(label="Execute Selected Fix")
        self.execute_action_button.set_tooltip_text("Open the guarded execution dialog. Execution remains locked until governance allows it.")
        self.execute_action_button.connect("clicked", self.on_execute_selected_action)
        controls.pack_start(self.execute_action_button, False, False, 0)

        self.execution_gate_label = Gtk.Label()
        self.execution_gate_label.set_xalign(0)
        self.execution_gate_label.set_line_wrap(True)
        self.approval_page.pack_start(self.execution_gate_label, False, False, 0)

        self.approval_selected_view = self._make_text_view()
        self.approval_page.pack_start(self._frame("Selected Fix", self.approval_selected_view), True, True, 0)

        self.approval_queue_view = self._make_text_view()
        self.approval_page.pack_start(self._frame("Queue", self.approval_queue_view), True, True, 0)

    def _build_history_page(self) -> None:
        intro = Gtk.Label(
            label=(
                "Review local diagnostic snapshots and request-plan records. The archive is local-only "
                "and intended for troubleshooting handoff and trend review."
            )
        )
        intro.set_xalign(0)
        intro.set_line_wrap(True)
        self.history_page.pack_start(intro, False, False, 0)

        action_row = self._make_wrapping_flow()
        self.history_page.pack_start(action_row, False, False, 0)

        self.refresh_history_button = Gtk.Button(label="Refresh History")
        self.refresh_history_button.connect("clicked", self.on_refresh_history)
        action_row.add(self.refresh_history_button)

        self.history_view = self._make_text_view()
        self.history_page.pack_start(self._frame("Maintenance History", self.history_view), True, True, 0)

    def _build_coach_page(self) -> None:
        intro = Gtk.Label(
            label=(
                "Ask questions about your stack and the app will answer using the local AI engine when available. "
                "Use Request Desk for plan preparation; this page stays focused on chat."
            )
        )
        intro.set_xalign(0)
        intro.set_line_wrap(True)
        self.coach_page.pack_start(intro, False, False, 0)

        prompts_row = self._make_wrapping_flow()
        self.coach_page.pack_start(prompts_row, False, False, 0)
        for prompt in [
            "What stands out about my stack?",
            "What should I learn next?",
            "How do these tools fit together?",
            "What did the folder scan reveal?",
            "What maintenance issue should I check first?",
        ]:
            button = Gtk.Button(label=prompt)
            button.connect("clicked", self.on_prompt_clicked, prompt)
            prompts_row.add(button)

        self.coach_question_entry = Gtk.Entry()
        self.coach_question_entry.set_placeholder_text("Ask a question about your environment, tools, or selected roots...")
        self.coach_question_entry.connect("activate", self.on_ask_coach)
        self.coach_page.pack_start(self.coach_question_entry, False, False, 0)

        coach_actions = self._make_wrapping_flow()
        self.coach_page.pack_start(coach_actions, False, False, 0)
        self.ask_button = Gtk.Button(label="Ask Local AI")
        self.ask_button.connect("clicked", self.on_ask_coach)
        coach_actions.add(self.ask_button)

        self.refresh_engine_button = Gtk.Button(label="Refresh AI Status")
        self.refresh_engine_button.connect("clicked", self.on_refresh_engine_clicked)
        coach_actions.add(self.refresh_engine_button)

        self.coach_view = self._make_text_view()
        self.coach_page.pack_start(self._frame("Coach Conversation", self.coach_view), True, True, 0)

    def _build_model_provider_page(self) -> None:
        intro = Gtk.Label(
            label=(
                "Model provider setup separates local Ollama mode, bring-your-own-key cloud readiness, "
                "and no-model deterministic fallback. Raw API keys are not stored by this app."
            )
        )
        intro.set_xalign(0)
        intro.set_line_wrap(True)
        self.model_provider_page.pack_start(intro, False, False, 0)

        actions = self._make_wrapping_flow()
        self.model_provider_page.pack_start(actions, False, False, 0)
        self.refresh_provider_button = Gtk.Button(label="Refresh Provider Health")
        self.refresh_provider_button.connect("clicked", self.on_refresh_provider_clicked)
        actions.add(self.refresh_provider_button)

        self.model_provider_view = self._make_text_view()
        self.model_provider_page.pack_start(self._frame("Provider Modes And Storage", self.model_provider_view), True, True, 0)

    def _set_text(self, view: Gtk.TextView, text: str) -> None:
        buffer_ = view.get_buffer()
        buffer_.set_text(text)

    def _set_status(self, text: str) -> None:
        self.status_label.set_text(text)

    def _build_working_overlay(self) -> None:
        self.working_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._add_class(self.working_box, "working-drama")
        self.working_box.set_halign(Gtk.Align.CENTER)
        self.working_box.set_valign(Gtk.Align.CENTER)
        self.working_box.set_no_show_all(True)

        badge_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        badge_row.set_halign(Gtk.Align.CENTER)
        self.working_spinner = Gtk.Spinner()
        badge_row.pack_start(self.working_spinner, False, False, 0)

        self.working_symbol_label = Gtk.Label(label="\u2623")
        self._add_class(self.working_symbol_label, "working-symbol")
        badge_row.pack_start(self.working_symbol_label, False, False, 0)
        self.working_box.pack_start(badge_row, False, False, 0)

        self.working_title_label = Gtk.Label(label="Working...")
        self._add_class(self.working_title_label, "working-title")
        self.working_title_label.set_xalign(0.5)
        self.working_box.pack_start(self.working_title_label, False, False, 0)

        self.working_detail_label = Gtk.Label(label="")
        self._add_class(self.working_detail_label, "working-detail")
        self.working_detail_label.set_xalign(0.5)
        self.working_detail_label.set_line_wrap(True)
        self.working_detail_label.set_max_width_chars(52)
        self.working_box.pack_start(self.working_detail_label, False, False, 0)

        self.app_overlay.add_overlay(self.working_box)
        if hasattr(self.app_overlay, "set_overlay_pass_through"):
            self.app_overlay.set_overlay_pass_through(self.working_box, True)

    def _pulse_working_symbol(self) -> bool:
        if not hasattr(self, "working_symbol_label") or not self.working_symbol_label.get_visible():
            return False
        spinners = ["|", "/", "-", "\\"]
        symbol = "\u2623" if self.working_pulse_step % 12 < 9 else "\u2622"
        self.working_symbol_label.set_text(f"{spinners[self.working_pulse_step % len(spinners)]} {symbol}")
        self.working_pulse_step += 1
        return True

    def _show_working_drama(self, title: str, detail: str = "") -> bool:
        if not hasattr(self, "working_box"):
            return False
        self.working_title_label.set_text(title)
        self.working_detail_label.set_text(detail)
        self.working_pulse_step = 0
        self.working_spinner.start()
        self.working_box.show_all()
        if self.working_pulse_id is not None:
            try:
                GLib.source_remove(self.working_pulse_id)
            except Exception:
                pass
        self.working_pulse_id = GLib.timeout_add(140, self._pulse_working_symbol)
        return False

    def _hide_working_drama(self) -> bool:
        if self.working_pulse_id is not None:
            try:
                GLib.source_remove(self.working_pulse_id)
            except Exception:
                pass
            self.working_pulse_id = None
        if hasattr(self, "working_spinner"):
            self.working_spinner.stop()
        if hasattr(self, "working_box"):
            self.working_box.hide()
        return False

    def _append_text(self, view: Gtk.TextView, text: str) -> None:
        buffer_ = view.get_buffer()
        existing = buffer_.get_text(buffer_.get_start_iter(), buffer_.get_end_iter(), True)
        buffer_.set_text(f"{existing}\n\n{text}".strip())

    def _refresh_engine_status(self) -> None:
        self.engine_status = get_engine_status()
        self.engine_label.set_text(f"Local AI engine: {self.engine_status['message']}")

    def _refresh_model_provider_status(self) -> None:
        status = model_provider_status()
        config = status.get("config", {})
        cloud = config.get("cloud", {})
        lines = [
            f"Active mode: {status.get('active_mode')}",
            f"Effective mode: {status.get('effective_mode')}",
            f"Config path: {config.get('config_path')}",
            status.get("privacy", ""),
            status.get("command_policy", ""),
            "",
            "Cloud key:",
            f"- Environment variable: {cloud.get('api_key_env_var')}",
            f"- Present: {'yes' if cloud.get('api_key_present') else 'no'}",
            f"- Storage: {cloud.get('api_key_storage')}",
            "",
            "Modes:",
        ]
        for mode in status.get("modes", []):
            state = "available" if mode.get("available") else "not ready"
            lines.append(f"- {mode.get('label')}: {state}. {mode.get('message', '')}")
        self._set_text(self.model_provider_view, "\n".join(lines))

    def on_refresh_provider_clicked(self, _button: Gtk.Button | None) -> None:
        self._refresh_model_provider_status()
        self._set_status("Model provider health refreshed.")

    def _on_size_allocate(self, _widget: Gtk.Widget, allocation: Gdk.Rectangle) -> None:
        if allocation.width < self.NARROW_LAYOUT_WIDTH:
            self._set_content_orientation(Gtk.Orientation.VERTICAL, int(allocation.height * 0.44))
            return

        self._set_content_orientation(Gtk.Orientation.HORIZONTAL, int(allocation.width * 0.46))

    def _set_content_orientation(self, orientation: Gtk.Orientation, position: int) -> None:
        if self._content_orientation == orientation:
            return
        self._content_orientation = orientation
        self.content_paned.set_orientation(orientation)
        self.content_paned.set_position(position)

    def _selected_roots(self) -> list[str]:
        roots = []
        for row in self.roots_list.get_children():
            if getattr(row, "check", None) and row.check.get_active():
                roots.append(row.check.get_label())

        custom_buffer = self.custom_roots_view.get_buffer()
        custom_text = custom_buffer.get_text(custom_buffer.get_start_iter(), custom_buffer.get_end_iter(), True)
        for line in custom_text.splitlines():
            line = line.strip()
            if line:
                roots.append(line)

        deduped = []
        seen = set()
        for root in roots:
            if root not in seen:
                deduped.append(root)
                seen.add(root)
        return deduped

    def on_run_review(self, _button: Gtk.Button | None) -> None:
        self.review_button.set_sensitive(False)
        self._show_working_drama("Running local review", "Mapping installed tools, environment hints, and learning notes.")
        self._set_status("Running local review...")
        threading.Thread(target=self._run_review_worker, daemon=True).start()

    def _run_review_worker(self) -> None:
        try:
            report = build_report()
            GLib.idle_add(self._apply_report, report)
        except Exception as exc:
            GLib.idle_add(self._hide_working_drama)
            GLib.idle_add(self._set_status, f"Review failed: {exc}")
            GLib.idle_add(self.review_button.set_sensitive, True)

    def _apply_report(self, report: dict) -> bool:
        self.current_report = report
        self._set_text(
            self.summary_view,
            "\n".join(
                [
                    f"Generated: {report['generated_at']}",
                    f"Installed components: {report['summary']['installed_component_count']}",
                    f"Category mix: {json.dumps(report['summary']['category_breakdown'], indent=2)}",
                    "",
                    "Recommendations:",
                    *[f"- {item}" for item in report["recommendations"]],
                ]
            ),
        )
        self._set_text(
            self.environment_view,
            "\n".join(
                [
                    *(f"{key.replace('_', ' ').title()}: {value}" for key, value in report["environment"].items()),
                    "",
                    "Capability profile:",
                    *self._plain_capability_summary(report.get("capabilities", {})),
                ]
            ),
        )
        self._set_text(self.learning_view, "\n".join(f"{index}. {step}" for index, step in enumerate(report["learning_path"], 1)))
        self._set_text(
            self.components_view,
            "\n\n".join(
                [
                    "\n".join(
                        [
                            f"{component['label']} [{component['category']}]",
                            f"Version: {component['version']}",
                            f"Path: {component['path']}",
                            component["role"],
                            f"Works well with: {', '.join(component['pairs_well_with']) or 'No built-in note yet'}",
                            f"Learning tip: {component['learning_tip']}",
                        ]
                    )
                    for component in report["components"]
                ]
            ),
        )
        self._set_text(
            self.stacks_view,
            "\n\n".join(
                [
                    f"{item['title']} ({item['confidence']} confidence)\n{item['summary']}\n{item['coaching']}"
                    for item in report["summary"]["primary_stack_matches"]
                ]
            )
            or "No strong stack pattern matched yet.",
        )
        self._set_text(
            self.command_view,
            "\n\n".join(
                f"{entry['command']}\nexit {entry['exit_code']} in {entry['duration_ms']}ms\n{entry['output'] or 'No output'}"
                for entry in report["command_log"]
            )
            or "No command log available.",
        )
        self._append_text(
            self.coach_view,
            "System: Review complete. Ask the coach things like what stands out, what to learn next, or how the tools fit together.",
        )
        self._hide_working_drama()
        self._set_status("Review complete. Explore the desktop app panels to learn the environment.")
        self.review_button.set_sensitive(True)
        return False

    def _plain_capability_summary(self, capabilities: dict) -> list[str]:
        if not capabilities:
            return ["No portable capability profile was returned."]
        os_info = capabilities.get("os", {})
        distro = os_info.get("distribution", {})
        desktop = capabilities.get("desktop", {})
        storage = capabilities.get("local_storage", {})
        lines = [
            f"Onboarding mode: {capabilities.get('onboarding_mode', 'unknown-machine-first-run')}",
            f"Distribution: {distro.get('pretty_name') or os_info.get('platform') or 'Unknown'}",
            f"Desktop family: {desktop.get('family', 'unknown')}",
            f"Display stack: {capabilities.get('display_stack', {}).get('display_server', 'unknown')}",
            f"Machine profile path: {storage.get('machine_profile_path', 'user config path')}",
            storage.get("summary", capabilities.get("privacy", "")),
            "",
            "Agent surfaces:",
        ]
        for surface in capabilities.get("surfaces", []):
            state = "available" if surface.get("available") else "blocked/advisory"
            lines.append(f"- {surface.get('label')}: {state}. {surface.get('reason', '')}")
        docs = capabilities.get("recommended_docs", [])
        if docs:
            lines.extend(["", "Recommended docs:", *(f"- {doc}" for doc in docs)])
        return lines

    def on_run_map(self, _button: Gtk.Button | None) -> None:
        roots = self._selected_roots()
        if not roots:
            self._set_status("Select at least one root before scanning.")
            return
        self.map_button.set_sensitive(False)
        self._show_working_drama("Scanning selected roots", "Reading local project markers and config hints.")
        self._set_status("Scanning the selected roots locally...")
        threading.Thread(target=self._run_map_worker, args=(roots,), daemon=True).start()

    def _run_map_worker(self, roots: list[str]) -> None:
        try:
            system_map = map_filesystem(roots)
            GLib.idle_add(self._apply_map, system_map)
        except Exception as exc:
            GLib.idle_add(self._hide_working_drama)
            GLib.idle_add(self._set_status, f"Filesystem map failed: {exc}")
            GLib.idle_add(self.map_button.set_sensitive, True)

    def _apply_map(self, system_map: dict) -> bool:
        self.current_map = system_map
        sections = [
            "Selected roots:",
            *[f"- {root}" for root in system_map["requested_roots"]],
            "",
            "Summary:",
            *[f"- {key.replace('_', ' ')}: {value}" for key, value in system_map["summary"].items()],
            "",
            "Teaching notes:",
            *[f"- {note}" for note in system_map["teaching_notes"]],
            "",
            "Config findings:",
        ]
        if system_map["config_findings"]:
            sections.extend(
                f"- {item['label']}: {item['path']} | {item['teaching']}" for item in system_map["config_findings"]
            )
        else:
            sections.append("- No common config markers found in the selected scope.")
        if system_map["missing_roots"]:
            sections.extend(["", "Missing roots:", *[f"- {item}" for item in system_map["missing_roots"]]])

        sections.append("")
        sections.append("Detected roots and projects:")
        for scan in system_map["scans"]:
            sections.append(f"- {scan['root']}")
            sections.append(
                f"  scanned {scan['summary']['entries_scanned']} entries, found {scan['summary']['projects_detected']} projects"
            )
            for project in scan["projects"][:10]:
                sections.append(f"  project: {project['path']} [{', '.join(project['types'])}]")
            if scan["permission_errors"]:
                sections.append(f"  permission limits: {', '.join(scan['permission_errors'][:5])}")

        self._set_text(self.map_results_view, "\n".join(sections))
        self._append_text(
            self.coach_view,
            "System: Filesystem map complete. You can now ask the coach what the selected roots reveal about the machine.",
        )
        self._hide_working_drama()
        self._set_status("Filesystem map complete.")
        self.map_button.set_sensitive(True)
        return False

    def on_run_maintenance(self, _button: Gtk.Button | None) -> None:
        self.maintenance_button.set_sensitive(False)
        self.maintenance_page_button.set_sensitive(False)
        self.review_backlog_fix_button.set_sensitive(False)
        self._show_working_drama("Running maintenance diagnostics", "Collecting read-only system health evidence.")
        self._set_status("Running read-only maintenance diagnostics...")
        threading.Thread(target=self._run_maintenance_worker, daemon=True).start()

    def _run_maintenance_worker(self) -> None:
        try:
            maintenance_report = build_maintenance_report()
            GLib.idle_add(self._apply_maintenance_report, maintenance_report)
        except Exception as exc:
            GLib.idle_add(self._hide_working_drama)
            GLib.idle_add(self._set_status, f"Maintenance diagnostics failed: {exc}")
            GLib.idle_add(self.maintenance_button.set_sensitive, True)
            GLib.idle_add(self.maintenance_page_button.set_sensitive, True)
            GLib.idle_add(self.review_backlog_fix_button.set_sensitive, True)

    def _apply_maintenance_report(self, maintenance_report: dict) -> bool:
        self.current_maintenance = maintenance_report
        record_maintenance_report(maintenance_report)
        self._hide_working_drama()
        summary = maintenance_report["summary"]
        sections = [
            f"Generated: {maintenance_report['generated_at']}",
            f"Findings: {summary['finding_count']}",
            f"Status counts: {json.dumps(summary['status_counts'], indent=2)}",
            f"Severity counts: {json.dumps(summary['severity_counts'], indent=2)}",
            f"Approval-required plans: {summary['approval_required_count']}",
            f"Execution enabled: {summary['execution_enabled']}",
            "",
            "Recommendations:",
            *[f"- {item}" for item in maintenance_report["recommendations"]],
            "",
            "Findings:",
        ]
        for finding in maintenance_report["findings"]:
            sections.extend(
                [
                    f"- {finding['title']} [{finding['severity']} / {finding['status']}]",
                    f"  {finding['summary']}",
                    f"  Next: {'; '.join(finding['recommended_next_steps'])}",
                ]
            )
        self._set_text(self.maintenance_summary_view, "\n".join(sections))

        if maintenance_report["action_plans"]:
            plan_sections = []
            for plan in maintenance_report["action_plans"]:
                plan_sections.extend([self._format_plan_details(plan), ""])
            self._set_text(self.maintenance_plans_view, "\n".join(plan_sections).strip())
        else:
            self._set_text(
                self.maintenance_plans_view,
                "No approval-required maintenance plans were prepared from the current diagnostics.",
            )

        self._append_text(
            self.coach_view,
            "System: Maintenance diagnostics complete. Ask the coach which finding to inspect first or how to prepare an approval-safe plan.",
        )
        executable_backlog = self._maintenance_backlog_plans()
        if executable_backlog:
            self._set_status(
                f"Maintenance diagnostics complete. {len(executable_backlog)} backlog plan(s) can be reviewed for approval."
            )
        else:
            self._set_status("Maintenance diagnostics complete. No executable backlog fixes are ready.")
        self.maintenance_button.set_sensitive(True)
        self.maintenance_page_button.set_sensitive(True)
        self.review_backlog_fix_button.set_sensitive(True)
        self._refresh_history_view()
        self._refresh_approval_queue()
        if self._maintenance_findings_dialog_needed(maintenance_report):
            self._show_maintenance_findings_dialog()
        return False

    def _maintenance_findings_dialog_needed(self, maintenance_report: dict) -> bool:
        urgent_findings = [
            finding
            for finding in maintenance_report.get("findings", [])
            if finding.get("severity") in {"critical", "warning"} and not finding.get("evidence", {}).get("history_resolution")
        ]
        return bool(urgent_findings or maintenance_report.get("action_plans"))

    def _maintenance_backlog_plans(self) -> list[dict]:
        if not self.current_maintenance:
            return []
        plans = self.current_maintenance.get("action_plans", [])
        return [
            plan
            for plan in plans
            if (plan.get("action_contract") or {}).get("execution_enabled", plan.get("execution_enabled", False))
        ]

    def _select_plan_in_approval_queue(self, plan: dict) -> None:
        if not hasattr(self, "approval_plan_picker"):
            return
        for index, queued_plan in enumerate(getattr(self, "queued_plans", [])):
            if queued_plan is plan or queued_plan.get("id") == plan.get("id"):
                self.approval_plan_picker.set_active(index)
                return

    def _show_approval_queue_page(self) -> None:
        if not hasattr(self, "notebook") or not hasattr(self, "approval_page"):
            return
        try:
            page_number = self.notebook.page_num(self.approval_page)
        except Exception:
            return
        if page_number is not None and page_number >= 0:
            self.notebook.set_current_page(page_number)

    def _show_request_page(self) -> None:
        if not hasattr(self, "notebook") or not hasattr(self, "request_page"):
            return
        try:
            page_number = self.notebook.page_num(self.request_page)
        except Exception:
            return
        if page_number is not None and page_number >= 0:
            self.notebook.set_current_page(page_number)

    def on_review_next_backlog_fix(self, _button: Gtk.Button | None) -> None:
        if not self.current_maintenance:
            self._set_status("Run maintenance diagnostics before reviewing backlog fixes.")
            self._show_action_dialog(
                "No Maintenance Backlog Yet",
                "Run maintenance diagnostics first. Then this button will open the next executable approval-required maintenance plan.",
            )
            return
        executable_backlog = self._maintenance_backlog_plans()
        if not executable_backlog:
            self._set_status("No executable maintenance backlog fixes are ready.")
            self._show_action_dialog(
                "No Executable Backlog Fix",
                (
                    "The latest diagnostics did not prepare an executable backlog fix. "
                    "Blocked or higher-risk findings still need narrower troubleshooting before approval."
                ),
            )
            return
        self._refresh_approval_queue()
        plan = executable_backlog[0]
        self._select_plan_in_approval_queue(plan)
        self._show_approval_queue_page()
        self._set_status("Thinking through the next maintenance backlog plan before approval...")
        self._start_plan_execution_with_reasoning(plan)

    def _refresh_history_view(self) -> None:
        self.current_history = load_history()
        self._set_text(self.history_view, format_history(self.current_history))

    def _refresh_approval_queue(self) -> None:
        queued_plans = []
        if self.current_maintenance:
            queued_plans.extend(self.current_maintenance.get("action_plans", []))
        if self.current_request_plan:
            queued_plans.append(self.current_request_plan)
        self.queued_plans = queued_plans
        self._refresh_approval_controls()

        if not queued_plans:
            self._set_text(
                self.approval_queue_view,
                "No approval-required plans are queued yet. Run maintenance diagnostics or prepare a request plan.",
            )
            self._set_text(self.approval_selected_view, "")
            return

        queue_sections = []
        for index, plan in enumerate(queued_plans, 1):
            queue_sections.append(self._queue_item_summary(index, plan))
        self._set_text(self.approval_queue_view, "\n".join(queue_sections).strip())
        self._refresh_selected_plan_preview()

    def _queue_item_summary(self, index: int, plan: dict) -> str:
        contract = plan.get("action_contract", {})
        can_execute = contract.get("execution_enabled", plan.get("execution_enabled", False))
        risk = plan.get("risk", "unknown")
        privilege = "privileged" if plan.get("requires_privilege") else "user-level"
        status = "can execute" if can_execute else "blocked"
        return f"{index}. {plan['title']} | {status} | risk: {risk} | {privilege}"

    def _refresh_approval_controls(self) -> None:
        self.approval_plan_picker.remove_all()
        if not self.queued_plans:
            self.approval_plan_picker.append_text("No queued plans")
            self.approval_plan_picker.set_active(0)
            self.review_action_button.set_sensitive(False)
            self._set_execution_buttons_sensitive(False)
            self.execution_gate_label.set_text("Execution is locked. Prepare a request plan or run diagnostics to review a queued fix.")
            if hasattr(self, "approval_selected_view"):
                self._set_text(self.approval_selected_view, "")
            return

        for index, plan in enumerate(self.queued_plans, 1):
            self.approval_plan_picker.append_text(f"{index}. {plan['title']}")
        self.approval_plan_picker.set_active(0)
        self.review_action_button.set_sensitive(True)
        self._set_execution_buttons_sensitive(True)
        self._refresh_selected_plan_preview()

    def _refresh_selected_plan_preview(self) -> None:
        if not hasattr(self, "approval_selected_view"):
            return
        plan = self._selected_queued_plan()
        if not plan:
            self._set_text(self.approval_selected_view, "")
            return
        contract = plan.get("action_contract", {})
        executable = contract.get("execution_enabled", False)
        execution_mode = contract.get("execution_mode", "user")
        elevation_prompt = contract.get("elevation_prompt") or {}
        gate_reasons = contract.get("execution_gate", {}).get("reasons", [])
        if executable:
            self.execution_gate_label.set_text("Selected plan can execute. Review the explanation, then press Execute when it looks right.")
        else:
            self.execution_gate_label.set_text(
                "Selected fix is blocked. Review the reason below, then prepare a narrower or lower-risk plan."
            )
        self._set_text(self.approval_selected_view, self._plain_plan_summary(plan))

    def on_approval_selection_changed(self, _combo: Gtk.ComboBoxText | None) -> None:
        self._refresh_selected_plan_preview()

    def _selected_queued_plan(self) -> dict | None:
        index = self.approval_plan_picker.get_active()
        if index < 0 or index >= len(self.queued_plans):
            return None
        return self.queued_plans[index]

    def _set_execution_buttons_sensitive(self, sensitive: bool) -> None:
        if hasattr(self, "execute_action_button"):
            self.execute_action_button.set_sensitive(sensitive and bool(self.queued_plans))
        if hasattr(self, "execute_request_button"):
            self.execute_request_button.set_sensitive(sensitive and self.current_request_plan is not None)

    def _show_action_dialog(
        self,
        title: str,
        body: str,
        entry_text: str | None = None,
        action_label: str | None = None,
    ) -> str | None:
        dialog = Gtk.Dialog(title=title, transient_for=self, modal=True)
        dialog.add_button("Close", Gtk.ResponseType.CLOSE)
        if action_label:
            dialog.add_button(action_label, Gtk.ResponseType.OK)
        dialog.set_default_size(780, 520)
        content = dialog.get_content_area()
        content.set_border_width(12)

        text_view = self._make_text_view()
        self._set_text(text_view, body)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_hexpand(True)
        scroll.set_vexpand(True)
        scroll.add(text_view)
        content.pack_start(scroll, True, True, 0)

        entry = None
        if entry_text is not None:
            entry = Gtk.Entry()
            entry.set_text(entry_text)
            entry.set_editable(False)
            content.pack_start(entry, False, False, 8)
        dialog.show_all()
        response = dialog.run()
        value = entry.get_text() if entry else None
        dialog.destroy()
        if action_label and response == Gtk.ResponseType.OK:
            return "__action__"
        return value

    def _finding_for_plan(self, plan: dict) -> dict | None:
        finding_id = plan.get("finding_id")
        if not finding_id or not self.current_maintenance:
            return None
        for finding in self.current_maintenance.get("findings", []):
            if finding.get("id") == finding_id:
                return finding
        return None

    def _maintenance_reasoning_lines(self, reasoning: dict | None) -> list[str]:
        if not reasoning:
            return []
        source = reasoning.get("source", "unknown")
        model = reasoning.get("model")
        lines = [
            "Reasoning pass:",
            f"Source: {source}" + (f" ({model})" if model else ""),
        ]
        if reasoning.get("working_problem"):
            lines.extend(["Working problem:", str(reasoning["working_problem"])])
        if reasoning.get("scenario_review"):
            lines.extend(["Scenario review:", str(reasoning["scenario_review"])])
        hypotheses = reasoning.get("hypotheses", [])
        if hypotheses:
            lines.append("Hypotheses considered:")
            for index, hypothesis in enumerate(hypotheses[:5], 1):
                if isinstance(hypothesis, dict):
                    lines.append(f"{index}. {hypothesis.get('summary', '')}")
                    supporting = hypothesis.get("supporting_evidence", [])
                    contradicting = hypothesis.get("contradicting_evidence", [])
                    if supporting:
                        lines.extend(f"   supports: {item}" for item in supporting[:3])
                    if contradicting:
                        lines.extend(f"   could disprove: {item}" for item in contradicting[:3])
                else:
                    lines.append(f"{index}. {hypothesis}")
        if reasoning.get("evidence_assessment"):
            lines.extend(["Evidence assessment:", str(reasoning["evidence_assessment"])])
        if reasoning.get("plan_fit"):
            lines.extend(["Plan fit:", str(reasoning["plan_fit"])])
        if reasoning.get("approval_guidance"):
            lines.extend(["Approval guidance:", str(reasoning["approval_guidance"])])
        stop_conditions = reasoning.get("stop_conditions", [])
        if stop_conditions:
            lines.append("Stop conditions:")
            lines.extend(f"- {item}" for item in stop_conditions[:6])
        if reasoning.get("model_error"):
            lines.extend(["Model note:", str(reasoning["model_error"])])
        return lines

    def _finding_evidence_summary(self, finding: dict) -> str:
        evidence = finding.get("evidence", {})
        if finding.get("id") == "journal-errors":
            sample = evidence.get("sample", []) if isinstance(evidence, dict) else []
            lines = [f"The scan saw {evidence.get('line_count', 'some')} recent critical log line(s)."]
            if sample:
                lines.append("Sample:")
                lines.extend(f"- {line}" for line in sample[:3])
            return "\n".join(lines)
        if finding.get("id") == "failed-services":
            services = evidence.get("services", []) if isinstance(evidence, dict) else []
            if services:
                return "Failed service candidates:\n" + "\n".join(f"- {service}" for service in services[:6])
            return "The system service scan reported failed services, but no service names were captured in the summary."
        if finding.get("id") == "package-manager-health":
            manager = evidence.get("manager", "the package manager") if isinstance(evidence, dict) else "the package manager"
            output = evidence.get("output", "") if isinstance(evidence, dict) else ""
            lines = [f"{manager} reported package-health trouble."]
            if output:
                lines.extend(["Package-manager output:", output[:1000]])
            return "\n".join(lines)
        if finding.get("id") == "network-basics":
            if isinstance(evidence, dict):
                route = evidence.get("default_route") or "No default route was captured."
                dns = "DNS resolution looked available." if evidence.get("dns_resolution_ok") else "DNS resolution needs review."
                return "\n".join([f"Default route: {route}", dns])
        return json.dumps(evidence, indent=2)

    def _maintenance_plan_why(self, plan: dict, finding: dict) -> str:
        finding_id = finding.get("id")
        if finding_id == "journal-errors":
            return (
                "Critical log lines are evidence, not a fix target by themselves. "
                "The next logical step is to collect a wider log sample and group repeated messages by service, device, or package. "
                "Only after that should the app propose a restart, package repair, driver path, or COSMIC/session fix."
            )
        if finding_id == "failed-services":
            return (
                "A failed service can be harmless, stale, or the main cause. "
                "The next step is to identify the exact failed service before any restart or configuration change."
            )
        if finding_id == "package-manager-health":
            return (
                "Package-manager problems can affect updates and installs, but repair commands can be intrusive. "
                "The safe path is to inspect package database health first, then prepare a narrower repair only if the output identifies one."
            )
        if finding_id == "network-basics":
            return (
                "Network symptoms need route and DNS evidence before changing adapters, resolvers, VPN settings, or router assumptions. "
                "This plan gathers that evidence without changing the connection."
            )
        return (
            "The maintenance scan found this condition in read-only diagnostics. "
            "The next step is to gather the smallest additional evidence needed before any machine-changing fix."
        )

    def _maintenance_plan_action(self, plan: dict, finding: dict, executable: bool, execution_mode: str | None) -> str:
        if not executable:
            return "This plan cannot run yet because the guarded runner blocked it. Review the gate reason and narrow the plan first."
        if finding.get("id") == "journal-errors":
            return (
                "Run a read-only journal query for the latest critical errors. "
                "This does not change services or settings; it gives the agent enough output to explain the repeated source and propose the next narrow fix."
            )
        if finding.get("id") == "failed-services":
            return (
                "List failed services first. This does not restart anything; it identifies the named service that would need a separate approved follow-up."
            )
        if finding.get("id") == "package-manager-health":
            if execution_mode == "elevated":
                return (
                    "Ask the operating system for administrator approval, then run only the package health check. "
                    "This is still inspection, not package repair, install, remove, or upgrade."
                )
            return "Run only the package health check so the next plan can name the exact package or database issue."
        if finding.get("id") == "network-basics":
            return "Collect route and DNS state without changing the network. The output determines whether a later adapter, DNS, or VPN fix is justified."
        return f"Run the approved diagnostic step: {plan.get('expected_effect', 'collect evidence for the next decision')}"

    def _maintenance_troubleshooting_steps(self, plan: dict, finding: dict) -> list[str]:
        steps = []
        if finding.get("id") == "journal-errors":
            steps.extend(
                [
                    "Treat the critical log finding as a symptom, not the root cause.",
                    "Collect a larger recent error sample.",
                    "Group repeated lines by service, device, package, or desktop component.",
                    "Propose a separate fix only for the repeated source.",
                ]
            )
        elif finding.get("id") == "package-manager-health":
            steps.extend(
                [
                    "Check package database health without installing or removing anything.",
                    "Read the exact package-manager failure.",
                    "Prepare a narrower repair only if the output identifies the affected package, lock, source, or database state.",
                ]
            )
        else:
            steps.extend(plan.get("manual_steps", [])[:4])
        if not steps:
            steps.append("Collect the next narrow evidence step before changing the machine.")
        return steps

    def _plain_plan_summary(self, plan: dict) -> str:
        finding = self._finding_for_plan(plan)
        contract = plan.get("action_contract", {})
        gate_reasons = contract.get("execution_gate", {}).get("reasons", [])
        commands = contract.get("command_preview", plan.get("commands", []))
        executable = contract.get("execution_enabled", False)
        execution_mode = contract.get("execution_mode")
        elevation_prompt = contract.get("elevation_prompt") or {}
        blocked_escalation = plan.get("blocked_escalation") or {}
        changes_system = plan.get("family") in {
            "cursor-size",
            "display-brightness",
            "display-night-light",
            "display-refresh-rate",
            "display-scaling",
            "display-layout-fix",
            "audio-routing",
            "pop-cosmic-panel-restart",
        }
        reasoning = plan.get("reasoning_brain", {})
        evidence_scopes = reasoning.get("evidence_scopes", [])
        evidence_count = reasoning.get("evidence_command_count", 0)
        source = str(reasoning.get("source", "deterministic"))
        is_evidence_plan = plan.get("family") in {
            "display-dock",
            "pop-cosmic-deep-scan",
            "pop-cosmic-display-evidence",
            "pop-cosmic-update-check",
        }

        if finding:
            problem = finding["summary"]
            evidence = self._finding_evidence_summary(finding)
            maintenance_reasoning = plan.get("maintenance_reasoning") or {}
            why = (
                maintenance_reasoning.get("scenario_review")
                or maintenance_reasoning.get("evidence_assessment")
                or self._maintenance_plan_why(plan, finding)
            )
        else:
            problem = plan.get("request") or plan.get("summary", "This plan came from a direct user request.")
            if evidence_scopes:
                evidence = f"Collected {evidence_count} read-only evidence command(s) for: {', '.join(evidence_scopes)}."
            else:
                evidence = "No extra request evidence was needed before preparing this plan."
            why_parts = []
            if reasoning.get("summary"):
                why_parts.append(f"Current hypothesis: {reasoning['summary']}")
            if reasoning.get("evidence_assessment"):
                why_parts.append(f"Evidence check: {reasoning['evidence_assessment']}")
            if source.startswith("deterministic"):
                why_parts.append(
                    "Planner note: I recognized this as a known troubleshooting lane and used guarded local rules for the first step."
                )
            alternates = reasoning.get("alternate_families", [])
            if alternates:
                why_parts.append(f"Alternates to keep in mind: {', '.join(alternates)}")
            steps = reasoning.get("investigation_steps", [])
            if steps:
                why_parts.append("Troubleshooting path:\n" + "\n".join(f"- {step}" for step in steps))
            if reasoning.get("permission_plan"):
                why_parts.append(f"Permission plan: {reasoning['permission_plan']}")
            why = "\n".join(why_parts) or plan.get("summary", "The request matched a known maintenance family.")

        if finding:
            maintenance_reasoning = plan.get("maintenance_reasoning") or {}
            action = maintenance_reasoning.get("recommended_next_step") or self._maintenance_plan_action(plan, finding, executable, execution_mode)
        elif executable and execution_mode == "elevated":
            action = (
                "Execute will request administrator permission with the operating-system password prompt, "
                "then run the exact elevated command(s)."
            )
        elif executable and changes_system:
            action = "Execute will apply this low-risk current-user setting change."
        elif executable and is_evidence_plan:
            action = (
                "Execute will collect read-only evidence. It will not fix the machine yet. "
                "After the evidence comes back, Request Desk should explain what it found and prepare the next narrow fix if one is supported."
            )
        elif executable:
            action = "Execute will run these guarded command(s), capture the output, and then explain the result in plain language."
        else:
            action = "Execute will not run this plan yet because the guarded runner blocked it."

        if finding:
            troubleshooting_items = (plan.get("maintenance_reasoning") or {}).get("troubleshooting_path") or self._maintenance_troubleshooting_steps(
                plan, finding
            )
        else:
            troubleshooting_items = plan.get("manual_steps", [])[:5]

        lines = [
            plan["title"],
            "",
            "Problem:",
            problem,
            "",
            "Evidence:",
            evidence,
            "",
            "Why:",
            why or "The diagnostic needs more evidence before naming a root cause.",
            "",
            *self._maintenance_reasoning_lines(plan.get("maintenance_reasoning") if finding else None),
            "",
            "How I would troubleshoot:",
            *(f"- {item}" for item in troubleshooting_items),
            "",
            "Recommended action:",
            action,
            "",
            "Can execute now:",
            "Yes" if executable else "No",
            "",
            "Fingerprint:",
            str(contract.get("fingerprint", "not available")),
            "",
            "Commands:",
            *(f"- {command}" for command in commands),
        ]
        if elevation_prompt:
            lines.extend(["", "Elevation:", elevation_prompt.get("message", "This action needs administrator approval.")])
        if gate_reasons:
            lines.extend(["", "Why blocked:", *(f"- {reason}" for reason in gate_reasons)])
        if blocked_escalation:
            lines.extend(
                [
                    "",
                    "Blocked escalation path:",
                    blocked_escalation.get("reason", "This action needs a narrower approved contract before execution."),
                    *(f"- {step}" for step in blocked_escalation.get("next_steps", [])),
                ]
            )
        lines.extend(
            [
                "",
                "Rollback or follow-up:",
                *(f"- {item}" for item in plan.get("rollback", []) or plan.get("manual_steps", [])),
            ]
        )
        return "\n".join(lines)

    def _show_maintenance_findings_dialog(self) -> None:
        if not self.current_maintenance:
            self._show_action_dialog("Maintenance Findings", "Run maintenance diagnostics before reviewing findings.")
            return

        findings = self.current_maintenance.get("findings", [])
        plans = self.current_maintenance.get("action_plans", [])
        if not findings:
            self._show_action_dialog(
                "Maintenance Findings",
                "No urgent maintenance problems were found by the current scan.",
            )
            return

        sections = [
            "Maintenance scan found items that need review.",
            "",
            "Plain-language summary:",
            "",
        ]
        for index, plan in enumerate(plans, 1):
            sections.extend([f"Item {index}", self._plain_plan_summary(plan), ""])

        if not plans:
            for index, finding in enumerate(findings, 1):
                sections.extend(
                    [
                        f"Item {index}: {finding['title']}",
                        "",
                        "What it found:",
                        finding["summary"],
                        "",
                        "Why this may be happening:",
                        json.dumps(finding.get("evidence", {}), indent=2),
                        "",
                        "What to do next:",
                        *[f"- {step}" for step in finding.get("recommended_next_steps", [])],
                        "",
                    ]
                )

        executable_backlog = self._maintenance_backlog_plans()
        if executable_backlog:
            sections.extend(
                [
                    "Ready for approval:",
                    (
                        "One or more maintenance backlog plans can execute now. "
                        "Use Review & Approve Next Fix to inspect the next plan and type APPROVE if it looks right."
                    ),
                    "",
                ]
            )
        response = self._show_action_dialog(
            "Maintenance Findings",
            "\n".join(sections).strip(),
            action_label="Review & Approve Next Fix" if executable_backlog else None,
        )
        if response == "__action__":
            self.on_review_next_backlog_fix(None)

    def on_review_selected_action(self, _button: Gtk.Button | None) -> None:
        plan = self._selected_queued_plan()
        if not plan:
            self._set_status("No queued plan is selected.")
            return
        contract = plan.get("action_contract", {})
        gate_reasons = contract.get("execution_gate", {}).get("reasons", [])
        body = "\n".join(
            [
                plan["title"],
                "",
                f"Risk: {plan['risk']}",
                f"Reversible: {plan['reversible']}",
                f"Requires privilege: {plan['requires_privilege']}",
                f"Execution mode: {contract.get('execution_mode', 'user')}",
                f"Execution enabled: {contract.get('execution_enabled', False)}",
                f"Fingerprint: {contract.get('fingerprint', 'not available')}",
                "",
                "Gate reasons:",
                *(f"- {reason}" for reason in gate_reasons),
                "",
                "Command preview:",
                *(f"- {command}" for command in contract.get("command_preview", [])),
            ]
        )
        self._show_action_dialog("Review Selected Plan", body)

    def on_execute_selected_action(self, _button: Gtk.Button | None) -> None:
        plan = self._selected_queued_plan()
        if not plan:
            self._set_status("Prepare a request plan or run diagnostics before reviewing execution.")
            self._show_action_dialog(
                "No Fix Selected",
                "No approval-required fix is queued yet. Use Request Desk to describe a specific request, or run maintenance diagnostics to populate the Approval Queue.",
            )
            return
        self._start_plan_execution_with_reasoning(plan)

    def on_execute_current_request(self, _button: Gtk.Button | None) -> None:
        if not self.current_request_plan:
            self._set_status("Prepare a recommendation before executing.")
            self._show_action_dialog(
                "No Recommendation Ready",
                "Request Desk has not prepared a current recommendation yet. Describe the issue first.",
            )
            return
        self._start_plan_execution(self.current_request_plan)

    def _start_plan_execution_with_reasoning(self, plan: dict) -> None:
        finding = self._finding_for_plan(plan)
        if not finding or plan.get("maintenance_reasoning"):
            self._start_plan_execution(plan)
            return
        self._show_approval_queue_page()
        self._show_pending_maintenance_reasoning(plan, finding)
        self._set_execution_buttons_sensitive(False)
        self._show_working_drama(
            "Thinking through the maintenance plan",
            "The local model is checking evidence, risk, rollback, and stop conditions before approval.",
        )
        self._set_status("Using the local reasoning brain to review the maintenance plan before approval...")
        threading.Thread(target=self._maintenance_reasoning_worker, args=(plan, finding), daemon=True).start()

    def _show_pending_maintenance_reasoning(self, plan: dict, finding: dict) -> None:
        if hasattr(self, "execution_gate_label"):
            self.execution_gate_label.set_text(
                "Review is in progress. The approval dialog will open after the reasoning pass finishes."
            )
        if not hasattr(self, "approval_selected_view"):
            return
        contract = plan.get("action_contract") or {}
        lines = [
            "Thinking through this maintenance plan before approval...",
            "",
            "Working problem:",
            finding.get("summary") or plan.get("title", "Maintenance finding needs review."),
            "",
            "What I am checking now:",
            "- Whether the finding matches the command preview",
            "- Whether there are safer explanations or narrower checks first",
            "- Whether the expected effect, rollback, and stop conditions are clear",
            "- Whether this should stay user-level or require stronger approval",
            "",
            "Selected command preview:",
            *(f"- {command}" for command in contract.get("command_preview", []) or ["No command preview is available."]),
            "",
            "Next step:",
            "The guarded approval dialog will open when this review finishes. Nothing is executing yet.",
        ]
        self._set_text(self.approval_selected_view, "\n".join(lines))

    def _maintenance_reasoning_worker(self, plan: dict, finding: dict) -> None:
        try:
            history = load_history(limit=25)
            reasoning = reason_about_maintenance_plan(
                plan,
                finding,
                maintenance_report=self.current_maintenance,
                learning_context=history.get("learning_notes", []) + history.get("known_good_lessons", []),
                changed_since_last=history.get("changed_since_last", []),
            )
        except Exception as exc:
            reasoning = {
                "ok": False,
                "source": "maintenance-reasoning-error",
                "model": None,
                "working_problem": finding.get("summary", plan.get("title", "")),
                "scenario_review": "The local reasoning pass failed before approval, so only the deterministic plan summary is available.",
                "hypotheses": [],
                "evidence_assessment": finding.get("summary", ""),
                "plan_fit": "Review the deterministic command preview carefully before approving.",
                "troubleshooting_path": plan.get("manual_steps", []),
                "recommended_next_step": self._maintenance_plan_action(
                    plan,
                    finding,
                    (plan.get("action_contract") or {}).get("execution_enabled", plan.get("execution_enabled", False)),
                    (plan.get("action_contract") or {}).get("execution_mode"),
                ),
                "approval_guidance": "Approve only if the exact command preview matches the evidence you want collected.",
                "stop_conditions": ["Do not approve if the command preview does not match the finding."],
                "model_error": str(exc),
            }
        GLib.idle_add(self._apply_maintenance_reasoning_and_execute, plan, reasoning)

    def _apply_maintenance_reasoning_and_execute(self, plan: dict, reasoning: dict) -> bool:
        plan["maintenance_reasoning"] = reasoning
        self._set_execution_buttons_sensitive(True)
        self._hide_working_drama()
        source = reasoning.get("source", "reasoning")
        model = reasoning.get("model")
        suffix = f" with {model}" if model else ""
        self._set_status(f"Maintenance reasoning complete via {source}{suffix}. Review before approving.")
        self._refresh_selected_plan_preview()
        self._start_plan_execution(plan)
        return False

    def _start_plan_execution(self, plan: dict) -> None:
        contract = plan.get("action_contract", {})
        confirmation_text = ""
        if contract.get("execution_enabled"):
            confirmation_text = self._show_execution_confirmation_dialog(plan)
            if confirmation_text is None:
                self._set_status("Execution canceled before approval.")
                return
            if confirmation_text.strip() != str(contract.get("confirmation_phrase", "")).strip():
                self._set_status("Execution canceled: confirmation phrase did not match.")
                self._show_action_dialog(
                    "Execution Not Confirmed",
                    "The confirmation phrase did not match the selected action. Nothing was executed.",
                )
                return
        if contract.get("execution_mode") == "elevated":
            prompt = (contract.get("elevation_prompt") or {}).get("message", "The operating system will ask for administrator approval.")
            self._set_status(f"Executing elevated recommendation. {prompt}")
        else:
            self._set_status("Executing the selected recommendation...")
        self._set_execution_buttons_sensitive(False)
        self._show_working_drama("Executing approved fix", "Running only the exact approved command preview.")
        threading.Thread(target=self._execute_plan_worker, args=(plan, confirmation_text), daemon=True).start()

    def _show_execution_confirmation_dialog(self, plan: dict) -> str | None:
        contract = plan.get("action_contract", {})
        phrase = str(contract.get("confirmation_phrase", ""))
        body = "\n".join(
            [
                self._plain_plan_summary(plan),
                "",
                "Approval confirmation:",
                f"Type this exact phrase to execute: {phrase}",
                "",
                "Execution will run only the exact command(s) shown above.",
            ]
        )

        dialog = Gtk.Dialog(title="Confirm Execution", transient_for=self, modal=True)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Execute", Gtk.ResponseType.OK)
        dialog.set_default_size(780, 560)
        content = dialog.get_content_area()
        content.set_border_width(12)

        text_view = self._make_text_view()
        self._set_text(text_view, body)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_hexpand(True)
        scroll.set_vexpand(True)
        scroll.add(text_view)
        content.pack_start(scroll, True, True, 0)

        entry = Gtk.Entry()
        entry.set_placeholder_text(phrase)
        content.pack_start(entry, False, False, 8)

        dialog.show_all()
        response = dialog.run()
        value = entry.get_text()
        dialog.destroy()
        if response != Gtk.ResponseType.OK:
            return None
        return value

    def _execute_plan_worker(self, plan: dict, confirmation_text: str) -> None:
        contract = plan.get("action_contract", {})
        analysis = None
        try:
            result = execute_guarded_action(contract, confirmation_text)
        except Exception as exc:
            result = self._execution_exception_result(contract, exc)
        try:
            record_action_result(result)
        except Exception as exc:
            result["history_error"] = str(exc)
        if result.get("status") == "completed":
            GLib.idle_add(
                self._show_working_drama,
                "Reading the aftermath",
                "Execution completed. The local model is analyzing the result and looking for the next concrete step.",
            )
            GLib.idle_add(self._set_status, "Execution completed. Analyzing result with the local model...")
            try:
                analysis = analyze_action_result(plan, result)
            except Exception as exc:
                analysis = {
                    "ok": False,
                    "model": None,
                    "analysis": f"Local model result analysis failed after execution completed: {exc}",
                }
        GLib.idle_add(self._apply_execution_result, plan, result, analysis)

    def _execution_exception_result(self, contract: dict, exc: Exception) -> dict:
        now = dt.datetime.now().isoformat(timespec="seconds")
        return {
            "action_id": contract.get("id"),
            "plan_id": contract.get("plan_id"),
            "server_plan_id": contract.get("server_plan_id"),
            "fingerprint": contract.get("fingerprint"),
            "status": "failed",
            "started_at": now,
            "finished_at": now,
            "execution_enabled": bool(contract.get("execution_enabled")),
            "exit_code": None,
            "commands": contract.get("command_preview", []),
            "output": "",
            "error": f"desktop execution worker failed before a command result was returned: {exc}",
            "post_check": contract.get("post_check", []),
            "rollback": contract.get("rollback", []),
        }

    def _apply_execution_result(self, plan: dict, result: dict, analysis: dict | None) -> bool:
        contract = plan.get("action_contract", {})
        followup_plan = None
        title = str(plan.get("title", "Selected recommendation"))
        status = "Execution finished."
        self._hide_working_drama()
        try:
            if str(plan.get("family", "")).startswith("pop-cosmic"):
                self.pop_cosmic_result = result
                self._append_text(
                    self.pop_cosmic_action_view,
                    "\n".join(
                        [
                            f"Action status: {result.get('status')}",
                            f"Action id: {result.get('action_id')}",
                            result.get("output") or result.get("error") or "No output.",
                        ]
                    ),
                )
            if result.get("status") == "completed":
                analysis = analysis or {}
                followup_plan = self._prepare_followup_plan_from_execution(plan, result, analysis)
                analysis_label = f"Local model analysis [{analysis.get('model')}]" if analysis.get("model") else "Local model analysis"
                body_lines = [
                    "Execution completed.",
                    "",
                    f"Selected plan: {title}",
                    f"Action id: {contract.get('id', 'unknown')}",
                    "",
                    f"{analysis_label}:",
                    analysis.get("analysis", "No analysis was returned."),
                ]
                if followup_plan:
                    body_lines.extend(
                        [
                            "",
                            "Next executable recommendation:",
                            self._plain_plan_summary(followup_plan),
                            "",
                            "I moved this fix into Request Desk. Press Execute Current Recommendation there to apply it, "
                            "or type a change in Request Desk to modify it.",
                        ]
                    )
                body_lines.extend(
                    [
                        "",
                        "Command output:",
                        result.get("output") or "No command output was returned.",
                        "",
                        "Post-check:",
                        *(f"- {item}" for item in result.get("post_check", [])),
                    ]
                )
                if result.get("history_error"):
                    body_lines.extend(["", f"History note: {result['history_error']}"])
                body = "\n".join(body_lines)
                status = (
                    "Investigation complete. A concrete fix is ready in Request Desk."
                    if followup_plan
                    else "Execution completed. The local model analyzed the output."
                )
                if plan is self.current_request_plan and not followup_plan:
                    self._set_text(
                        self.request_plan_view,
                        "\n".join(
                            [
                                self._plain_plan_summary(plan),
                                "",
                                "Execution Result:",
                                analysis.get("analysis", "No analysis was returned."),
                            ]
                        ),
                    )
            else:
                self._record_execution_learning(plan, result, analysis, None)
                gate_reasons = result.get("error") or "Execution is blocked by the current controls."
                body = "\n".join(
                    [
                        "Execution did not run.",
                        "",
                        f"Selected plan: {title}",
                        f"Action id: {contract.get('id', 'unknown')}",
                        f"Status: {result.get('status', 'unknown')}",
                        "",
                        "Reason:",
                        gate_reasons,
                        "",
                        (
                            "Only exact plans in the user-level or elevated guarded catalogs can execute. "
                            "Elevated plans also require the project elevated runner flag and OS administrator approval."
                        ),
                    ]
                )
                if result.get("history_error"):
                    body = f"{body}\n\nHistory note: {result['history_error']}"
                status = "Execution did not run. Review the gate reason."
        except Exception as exc:
            body = "\n".join(
                [
                    "Execution finished, but the desktop result view failed while updating.",
                    "",
                    f"Selected plan: {title}",
                    f"Action id: {contract.get('id', 'unknown')}",
                    f"Execution status: {result.get('status', 'unknown')}",
                    f"Display error: {exc}",
                    "",
                    "The action result was still returned to the desktop worker. Refresh History or restart the app to recover the view.",
                ]
            )
            status = "Execution finished, but the desktop result view hit an error."
        refresh_errors = []
        try:
            self._refresh_history_view()
        except Exception as exc:
            refresh_errors.append(f"history refresh failed: {exc}")
        try:
            self._refresh_approval_queue()
        except Exception as exc:
            refresh_errors.append(f"approval queue refresh failed: {exc}")
        self._set_execution_buttons_sensitive(True)
        if refresh_errors:
            status = f"{status} {'; '.join(refresh_errors)}"
        self._set_status(status)
        self._show_action_dialog("Execute Selected Fix", body)
        return False

    def _pop_cosmic_concern(self) -> str:
        buffer_ = self.pop_cosmic_concern_view.get_buffer()
        return buffer_.get_text(buffer_.get_start_iter(), buffer_.get_end_iter(), True).strip()

    def on_pop_cosmic_scan(self, _button: Gtk.Button | None) -> None:
        scope = self.pop_cosmic_scope.get_active_text() or "standard"
        self._show_working_drama("Scanning Pop!_OS and COSMIC", f"Collecting {scope} local evidence without changing settings.")
        self._set_status(f"Running Pop!_OS/COSMIC {scope} scan...")
        threading.Thread(target=self._pop_cosmic_scan_worker, args=(scope,), daemon=True).start()

    def _pop_cosmic_scan_worker(self, scope: str) -> None:
        try:
            scan = run_pop_cosmic_deep_scan(scope)
            GLib.idle_add(self._apply_pop_cosmic_scan, scan)
        except Exception as exc:
            GLib.idle_add(self._hide_working_drama)
            GLib.idle_add(self._set_status, f"Pop!_OS/COSMIC scan failed: {exc}")

    def _apply_pop_cosmic_scan(self, scan: dict) -> bool:
        self.pop_cosmic_scan = scan
        profile = scan.get("profile", {})
        lines = [
            f"Generated: {scan.get('generated_at')}",
            f"Scope: {scan.get('scope')}",
            f"Applicable: {scan.get('applicable')}",
            f"OS: {profile.get('pretty_name')}",
            f"Pop version: {profile.get('pop_version')}",
            f"COSMIC signal: {profile.get('has_cosmic_signal')}",
            f"Session: {json.dumps(profile.get('session', {}), indent=2)}",
            "",
            "Findings:",
            *[f"- {finding.get('severity')}: {finding.get('summary')}" for finding in scan.get("findings", [])],
        ]
        missing_cosmic_commands = [
            command
            for command, info in (profile.get("cosmic", {}).get("commands") or {}).items()
            if command in {"cosmic-randr", "cosmic-settings", "cosmic-store"} and not info.get("present")
        ]
        if missing_cosmic_commands:
            lines.extend(["", "Missing COSMIC commands:", *(f"- {command}" for command in missing_cosmic_commands)])
        self._set_text(self.pop_cosmic_profile_view, "\n".join(lines))
        self._hide_working_drama()
        self._set_status("Pop!_OS/COSMIC scan complete.")
        return False

    def on_pop_cosmic_research(self, _button: Gtk.Button | None) -> None:
        if not self.pop_cosmic_scan:
            self.on_pop_cosmic_scan(None)
            self._set_status("Started scan first; run research again after scan completes.")
            return
        symptom = self._pop_cosmic_concern()
        self._show_working_drama("Researching Pop!_OS and COSMIC", "Preparing source-aware research records for the local analysis.")
        self._set_status("Preparing source-aware Pop!_OS/COSMIC research records...")
        threading.Thread(target=self._pop_cosmic_research_worker, args=(symptom,), daemon=True).start()

    def _pop_cosmic_research_worker(self, symptom: str) -> None:
        try:
            profile = (self.pop_cosmic_scan or {}).get("profile", {})
            controls = load_pop_cosmic_controls()
            requested_live_web = bool(controls.get("web_research_enabled"))
            governance = {
                "source": controls.get("source"),
                "web_research_enabled": bool(controls.get("web_research_enabled")),
                "requested_live_web": requested_live_web,
                "effective_live_web": requested_live_web,
                "allowed_domains": controls.get("allowed_domains", []),
                "research_provider": controls.get("research_provider", "official"),
                "reason": (
                    "Desktop Pop/COSMIC research used the governed live provider."
                    if requested_live_web
                    else "Project controls keep live research disabled. Returning local/manual records and official source metadata only."
                ),
            }
            research = research_pop_cosmic_issue(
                symptom,
                profile,
                enabled=requested_live_web,
                include_github=requested_live_web,
                governance=governance,
                research_provider=str(controls.get("research_provider", "official")),
                allowed_domains=controls.get("allowed_domains", []),
                perplexity_config={
                    "api_key_env_var": controls.get("perplexity_api_key_env_var", "PERPLEXITY_API_KEY"),
                    "model_env_var": controls.get("perplexity_model_env_var", "PERPLEXITY_MODEL"),
                    "master_env_path": controls.get("master_env_path", ""),
                },
                max_results=int(controls.get("max_results_per_query", 8)),
            )
            save_research_records(research.get("records", []))
            if research.get("records"):
                record_learning_note(
                    {
                        "source": "pop-cosmic-research",
                        "summary": f"Saved {len(research.get('records', []))} Pop/COSMIC research records for future analysis.",
                        "query": research.get("query"),
                        "research_mode": research.get("research_mode"),
                        "provider": controls.get("research_provider", "official"),
                    }
                )
            GLib.idle_add(self._apply_pop_cosmic_research, research)
        except Exception as exc:
            GLib.idle_add(self._hide_working_drama)
            GLib.idle_add(self._set_status, f"Pop!_OS/COSMIC research failed: {exc}")

    def _apply_pop_cosmic_research(self, research: dict) -> bool:
        self.pop_cosmic_research = research
        records = research.get("records", [])
        lines = [
            f"Research enabled: {research.get('enabled')}",
            f"Research mode: {research.get('research_mode')}",
            f"Safe query: {research.get('query')}",
            f"Governance: {research.get('governance', {}).get('reason', '')}",
            research.get("privacy", ""),
            "",
            "Sources:",
            *[f"- [{record.get('trust_level')}] {record.get('title')} - {record.get('url')}" for record in records],
        ]
        self._append_text(self.pop_cosmic_analysis_view, "\n".join(lines))
        self._hide_working_drama()
        self._set_status("Pop!_OS/COSMIC research records prepared.")
        return False

    def on_pop_cosmic_analyze(self, _button: Gtk.Button | None) -> None:
        if not self.pop_cosmic_scan:
            self.on_pop_cosmic_scan(None)
            self._set_status("Started scan first; ask the model after scan completes.")
            return
        symptom = self._pop_cosmic_concern()
        self._show_working_drama("Asking the local model ladder", "Analyzing COSMIC evidence, lessons, and research notes.")
        self._set_status("Asking local model ladder to analyze Pop!_OS/COSMIC evidence...")
        threading.Thread(target=self._pop_cosmic_analyze_worker, args=(symptom,), daemon=True).start()

    def _pop_cosmic_analyze_worker(self, symptom: str) -> None:
        try:
            scan = self.pop_cosmic_scan or run_pop_cosmic_deep_scan("standard")
            profile = scan.get("profile", {})
            research = (self.pop_cosmic_research or {}).get("records") or load_relevant_research(symptom, profile)
            lessons = load_relevant_lessons(symptom, profile)
            analysis = analyze_pop_cosmic_issue(symptom, scan, research, lessons)
            GLib.idle_add(self._apply_pop_cosmic_analysis, analysis)
        except Exception as exc:
            GLib.idle_add(self._hide_working_drama)
            GLib.idle_add(self._set_status, f"Pop!_OS/COSMIC analysis failed: {exc}")

    def _apply_pop_cosmic_analysis(self, analysis: dict) -> bool:
        self.pop_cosmic_analysis = analysis
        lines = [
            f"Source: {analysis.get('source')} {analysis.get('model') or ''}".strip(),
            f"Working problem: {analysis.get('working_problem')}",
            f"Likely surface: {analysis.get('likely_surface')}",
            f"Confidence: {analysis.get('confidence')}",
            "",
            "Hypotheses:",
        ]
        if analysis.get("model_error"):
            lines.extend(["", f"Local model note: {analysis.get('model_error')}"])
        for hypothesis in analysis.get("hypotheses", []):
            lines.append(f"- {hypothesis.get('id', '?')}: {hypothesis.get('summary')}")
        lines.extend(["", "Ranked actions:"])
        for index, action in enumerate(analysis.get("ranked_actions", []), 1):
            lines.append(f"{index}. {action.get('action_key')} - {action.get('title')} [{action.get('risk')}]")
            if action.get("why"):
                lines.append(f"   why: {action.get('why')}")
        self._set_text(self.pop_cosmic_analysis_view, "\n".join(lines))
        self._hide_working_drama()
        self._set_status("Pop!_OS/COSMIC analysis complete.")
        return False

    def on_pop_cosmic_plan(self, _button: Gtk.Button | None) -> None:
        if not self.pop_cosmic_analysis:
            self.on_pop_cosmic_analyze(None)
            self._set_status("Started analysis first; build the fix plan after analysis completes.")
            return
        actions = self.pop_cosmic_analysis.get("ranked_actions", [])
        action_key = actions[0].get("action_key", "deep-scan-standard") if actions else "deep-scan-standard"
        plan = prepare_pop_cosmic_action(action_key, self.pop_cosmic_analysis, self.pop_cosmic_scan or {})
        self.pop_cosmic_plan = plan
        self.current_request_plan = plan
        record_request_plan(plan)
        self._set_text(self.pop_cosmic_action_view, self._plain_plan_summary(plan))
        self._refresh_approval_queue()
        self._set_status("Pop!_OS/COSMIC fix plan prepared. Review before execution.")

    def on_pop_cosmic_execute(self, _button: Gtk.Button | None) -> None:
        if not self.pop_cosmic_plan:
            self._set_status("Build a Pop!_OS/COSMIC fix plan before executing.")
            return
        self._start_plan_execution(self.pop_cosmic_plan)

    def on_pop_cosmic_verify(self, _button: Gtk.Button | None) -> None:
        if not self.pop_cosmic_result:
            self._set_status("No Pop!_OS/COSMIC action result is available to verify yet.")
            return
        self._show_working_drama("Verifying the fix", "Running a fresh post-action scan and saving the lesson.")
        self._set_status("Verifying Pop!_OS/COSMIC action with a fresh scan...")
        threading.Thread(target=self._pop_cosmic_verify_worker, daemon=True).start()

    def _pop_cosmic_verify_worker(self) -> None:
        try:
            post_scan = prepare_verification_plan(self.pop_cosmic_result or {}, self.pop_cosmic_scan or {})
            lesson = make_verification_lesson(
                symptom=self._pop_cosmic_concern(),
                action_result=self.pop_cosmic_result or {},
                post_scan=post_scan,
                user_confirmed=False,
            )
            save_lesson(lesson)
            GLib.idle_add(self._apply_pop_cosmic_verification, post_scan, lesson)
        except Exception as exc:
            GLib.idle_add(self._hide_working_drama)
            GLib.idle_add(self._set_status, f"Pop!_OS/COSMIC verification failed: {exc}")

    def _apply_pop_cosmic_verification(self, post_scan: dict, lesson: dict) -> bool:
        self.pop_cosmic_scan = post_scan
        self._append_text(
            self.pop_cosmic_action_view,
            "\n".join(
                [
                    "Verification scan complete.",
                    *[f"- {finding.get('summary')}" for finding in post_scan.get("findings", [])],
                    "",
                    f"Lesson saved: {lesson.get('result')}",
                ]
            ),
        )
        self._hide_working_drama()
        self._set_status("Pop!_OS/COSMIC verification complete and lesson saved.")
        return False

    def _prepare_followup_plan_from_execution(self, plan: dict, result: dict, analysis: dict | None) -> dict | None:
        followup = build_followup_request(plan, result, analysis)
        if not followup:
            self._record_execution_learning(plan, result, analysis, None)
            return None

        os_name, desktop_hint = self._request_environment_context()
        followup_plan = prepare_request_plan(
            followup["request_text"],
            os_name=os_name,
            distribution_hint=desktop_hint,
            family_override=followup["family"],
            reasoning=followup.get("reasoning"),
        )
        self.current_request_plan = followup_plan
        record_request_plan(followup_plan)
        self._set_text(
            self.request_plan_view,
            "\n".join(
                [
                    "Investigation complete. I prepared the next fix from the evidence.",
                    "",
                    self._plain_plan_summary(followup_plan),
                ]
            ),
        )
        self._show_request_page()
        self._append_request_message(
            "Request Desk",
            (
                "I used the executed evidence to prepare the next concrete fix.\n"
                f"{followup['summary']}\n"
                f"Can execute now: {'yes' if followup_plan['execution_enabled'] else 'no'}\n"
                "Press Execute Current Recommendation to apply it, or type what you want changed and I will revise the plan."
            ),
        )
        self._record_execution_learning(plan, result, analysis, followup_plan)
        return followup_plan

    def _record_execution_learning(
        self,
        plan: dict,
        result: dict,
        analysis: dict | None,
        followup_plan: dict | None,
    ) -> None:
        status = result.get("status", "unknown")
        family = plan.get("family", "unknown")
        if status == "completed" and followup_plan:
            lesson = (
                f"Evidence from {plan.get('title', family)} supported a next {followup_plan.get('family')} plan: "
                f"{followup_plan.get('title')}."
            )
        elif status == "completed":
            lesson = (
                f"{plan.get('title', family)} completed but did not produce a concrete follow-up fix; "
                "future runs should gather more specific evidence or ask for a narrower symptom."
            )
        else:
            lesson = f"{plan.get('title', family)} ended with status {status}: {result.get('error', 'no error text')}"
        if analysis and analysis.get("analysis"):
            lesson = f"{lesson} Analysis: {analysis['analysis'][:500]}"
        record_learning_note(
            {
                "family": family,
                "status": status,
                "plan_id": plan.get("id"),
                "plan_title": plan.get("title"),
                "lesson": lesson,
                "followup_family": followup_plan.get("family") if followup_plan else None,
                "action_id": result.get("action_id"),
                "commands": result.get("commands", []),
            }
        )

    def on_review_findings(self, _button: Gtk.Button | None) -> None:
        self._show_maintenance_findings_dialog()

    def on_refresh_history(self, _button: Gtk.Button | None) -> None:
        self._refresh_history_view()
        self._set_status("Local maintenance history refreshed.")

    def on_copy_summary(self, _button: Gtk.Button | None) -> None:
        if not self.current_report:
            self._set_status("Run a review before copying a share summary.")
            return

        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(build_share_text(self.current_report, self.current_map, self.current_maintenance), -1)
        self._set_status("Share summary copied to the clipboard.")

    def on_refresh_engine_clicked(self, _button: Gtk.Button | None) -> None:
        self._refresh_engine_status()
        self._set_status("Local AI engine status refreshed.")

    def on_prompt_clicked(self, _button: Gtk.Button | None, prompt: str) -> None:
        if any(
            word in prompt.lower()
            for word in ("cursor", "screen", "audio", "dns", "docker", "slow", "startup", "package", "update")
        ):
            self.request_entry.set_text(prompt)
            self.on_request_send(None)
            return
        self.coach_question_entry.set_text(prompt)
        self.on_ask_coach(None)

    def _append_request_message(self, speaker: str, text: str) -> None:
        self._append_text(self.request_thread_view, f"{speaker}: {text}")

    def _combined_request_context(self) -> str:
        return "\n".join(self.request_context).strip()

    def _request_environment_context(self) -> tuple[str | None, str | None]:
        environment = (self.current_report or {}).get("environment", {})
        maintenance_desktop = (self.current_maintenance or {}).get("metrics", {}).get("desktop", {})
        os_name = environment.get("os") or (self.current_maintenance or {}).get("metrics", {}).get("platform", {}).get("os")
        desktop_hint = environment.get("desktop") or maintenance_desktop.get("current_desktop")
        return os_name, desktop_hint

    def _start_request_brain(self, request_text: str, *, force_plan: bool = False) -> None:
        os_name, desktop_hint = self._request_environment_context()
        self.request_brain_sequence += 1
        token = self.request_brain_sequence
        self.active_request_brain_token = token
        self.request_send_button.set_sensitive(False)
        self.prepare_request_button.set_sensitive(False)
        self.execute_request_button.set_sensitive(False)
        self._show_working_drama("Request Desk is thinking", "The local engine is checking the request, evidence, and safe execution path.")
        self._set_status("The local model is thinking through the request...")
        GLib.timeout_add_seconds(
            self.REQUEST_BRAIN_TIMEOUT_SECONDS,
            self._request_brain_timeout,
            token,
            request_text,
            force_plan,
            desktop_hint,
        )
        threading.Thread(
            target=self._request_brain_worker,
            args=(token, request_text, os_name, desktop_hint, self.current_maintenance, force_plan),
            daemon=True,
        ).start()

    def _request_brain_worker(
        self,
        token: int,
        request_text: str,
        os_name: str | None,
        desktop_hint: str | None,
        maintenance_report: dict | None,
        force_plan: bool,
    ) -> None:
        evidence = {}
        try:
            evidence = collect_request_evidence(request_text, os_name=os_name, desktop_hint=desktop_hint)
            deterministic = review_request_intake(request_text, desktop_hint)
            if deterministic.get("ready"):
                reasoning = self._request_deterministic_reasoning(
                    deterministic,
                    evidence,
                    "Request Desk used deterministic routing because the request was already specific enough to plan safely.",
                )
                GLib.idle_add(self._apply_request_brain_result, token, request_text, reasoning, force_plan)
                return
            history = load_history(limit=20)
            reasoning = reason_about_request(
                request_text,
                os_name=os_name,
                desktop_hint=desktop_hint,
                maintenance_report=maintenance_report,
                request_evidence=evidence,
                learning_context=history.get("learning_notes", []) + history.get("known_good_lessons", []),
            )
            reasoning["request_evidence"] = evidence
            if not reasoning.get("ok"):
                reasoning = self._request_fallback_reasoning(
                    request_text,
                    evidence,
                    reasoning.get("acknowledgement", "Local model request analysis was unavailable."),
                    reasoning.get("reasoning_summary", ""),
                    desktop_hint,
                )
        except Exception as exc:
            reasoning = self._request_fallback_reasoning(
                request_text,
                evidence,
                f"Request Desk local reasoning failed before a plan was prepared: {exc}",
                "Request Desk worker failed and used deterministic fallback.",
                desktop_hint,
            )
        GLib.idle_add(self._apply_request_brain_result, token, request_text, reasoning, force_plan)

    def _request_brain_timeout(self, token: int, request_text: str, force_plan: bool, desktop_hint: str | None = None) -> bool:
        if self.active_request_brain_token != token:
            return False
        reasoning = self._request_fallback_reasoning(
            request_text,
            {},
            (
                f"The local model took longer than {self.REQUEST_BRAIN_TIMEOUT_SECONDS} seconds. "
                "I restored the Request Desk controls and used deterministic fallback instead."
            ),
            "Request Desk local model timed out and deterministic fallback was used.",
            desktop_hint,
        )
        self._hide_working_drama()
        self._apply_request_brain_result(token, request_text, reasoning, force_plan)
        return False

    def _request_fallback_reasoning(
        self,
        request_text: str,
        evidence: dict,
        model_error: str,
        reasoning_summary: str,
        desktop_hint: str | None = None,
    ) -> dict:
        fallback = review_request_intake(request_text, desktop_hint)
        fallback.update(
            {
                "ok": True,
                "source": "deterministic-fallback",
                "model": None,
                "confidence": None,
                "alternate_families": [],
                "evidence_assessment": "Deterministic fallback used the request wording and any collected read-only evidence.",
                "investigation_steps": fallback.get("questions", []),
                "permission_plan": "Prepare an approval-required plan before executing any change.",
                "reasoning_summary": reasoning_summary,
                "model_error": model_error,
                "request_evidence": evidence,
            }
        )
        return fallback

    def _request_deterministic_reasoning(self, intake: dict, evidence: dict, reasoning_summary: str) -> dict:
        reasoning = dict(intake)
        reasoning.update(
            {
                "ok": True,
                "source": "deterministic-fast-path",
                "model": None,
                "confidence": 0.8,
                "alternate_families": [],
                "evidence_assessment": "Deterministic routing used the request wording and collected read-only evidence.",
                "investigation_steps": intake.get("questions", []),
                "permission_plan": "Prepare an approval-required plan before executing any change.",
                "reasoning_summary": reasoning_summary,
                "request_evidence": evidence,
            }
        )
        return reasoning

    def _apply_request_brain_result(self, token: int, request_text: str, reasoning: dict, force_plan: bool) -> bool:
        if self.active_request_brain_token != token:
            return False
        self.active_request_brain_token = None
        self.latest_request_reasoning = reasoning
        self._hide_working_drama()
        self.request_send_button.set_sensitive(True)
        self.prepare_request_button.set_sensitive(True)
        self.execute_request_button.set_sensitive(self.current_request_plan is not None)

        source = reasoning.get("source", "deterministic")
        model = reasoning.get("model")
        brain_label = f"Local model [{model}]" if source == "local-model" and model else "Request Desk"

        if reasoning.get("model_error"):
            self._append_request_message("Request Desk", reasoning["model_error"])

        if reasoning.get("ready") or force_plan:
            self._append_request_message("Request Desk", f"{brain_label}: {reasoning['acknowledgement']}")
            try:
                self._prepare_request_plan(request_text, reasoning=reasoning)
            except Exception as exc:
                self._append_request_message("Request Desk", f"Plan preparation failed: {exc}")
                self._set_status("Request Desk could not prepare a plan. The controls have been restored.")
            return False

        response_lines = [f"{brain_label}: {reasoning['acknowledgement']}", "", "I need one or two details:"]
        response_lines.extend(f"- {question}" for question in reasoning.get("questions", []))
        self._append_request_message("Request Desk", "\n".join(response_lines))
        self._set_status("Request Desk needs more detail before preparing a plan.")
        return False

    def on_request_send(self, _widget: Gtk.Widget | None) -> None:
        request_text = self.request_entry.get_text().strip()
        if not request_text:
            self._set_status("Type a request or answer before sending.")
            return

        self.request_entry.set_text("")
        self.request_context.append(request_text)
        self._append_request_message("You", request_text)

        combined_text = self._combined_request_context()
        self._start_request_brain(combined_text)

    def on_prepare_request_plan(self, _widget: Gtk.Widget | None) -> None:
        request_text = self.request_entry.get_text().strip() or self._combined_request_context()
        if not request_text:
            self._set_status("Type a maintenance request before preparing a plan.")
            return
        if self.request_entry.get_text().strip():
            self.request_context.append(request_text)
            self._append_request_message("You", request_text)
            self.request_entry.set_text("")
        self._append_request_message("Request Desk", "I will ask the local model to prepare the best guarded path from the details available now.")
        self._start_request_brain(self._combined_request_context() or request_text, force_plan=True)

    def _prepare_request_plan(self, request_text: str, reasoning: dict | None = None) -> None:
        os_name, desktop_hint = self._request_environment_context()
        plan = prepare_request_plan(
            request_text,
            os_name=os_name,
            distribution_hint=desktop_hint,
            family_override=reasoning.get("family") if reasoning else None,
            reasoning=reasoning,
        )
        self.current_request_plan = plan
        self.execute_request_button.set_sensitive(True)
        record_request_plan(plan)
        formatted = format_request_plan(plan)
        self._set_text(self.request_plan_view, self._plain_plan_summary(plan))
        self._append_text(self.coach_view, f"You: {request_text}")
        self._append_text(self.coach_view, f"Plan [{plan['platform']}]:\n{formatted}")
        self._append_request_message(
            "Request Desk",
            (
                f"Plan ready: {plan['title']}\n"
                f"Can execute now: {'yes' if plan['execution_enabled'] else 'no'}\n"
                "Review the current recommendation. If this is an evidence step, Execute gathers facts first; the fix comes after those facts are reviewed."
            ),
        )
        self._set_status("Request plan prepared. Review it before execution.")
        self._refresh_history_view()
        self._refresh_approval_queue()

    def on_clear_request_conversation(self, _button: Gtk.Button | None) -> None:
        self.request_context = []
        self.request_entry.set_text("")
        self._set_text(self.request_thread_view, "")
        self._set_text(self.request_plan_view, "")
        self.current_request_plan = None
        self.latest_request_reasoning = None
        self.execute_request_button.set_sensitive(False)
        self._refresh_approval_queue()
        self._set_status("Request Desk conversation cleared.")

    def on_ask_coach(self, _widget: Gtk.Widget | None) -> None:
        question = self.coach_question_entry.get_text().strip()
        if not question:
            self._set_status("Type a question for the coach first.")
            return
        self.ask_button.set_sensitive(False)
        self._append_text(self.coach_view, f"You: {question}")
        self._show_working_drama("Coach is thinking", "Asking the local engine to explain the current system context.")
        self._set_status("Local AI is thinking...")
        threading.Thread(target=self._ask_coach_worker, args=(question,), daemon=True).start()

    def _ask_coach_worker(self, question: str) -> None:
        try:
            response = answer_question(
                question,
                self.current_report,
                self.current_map,
                self.current_maintenance,
                self.current_request_plan,
            )
        except Exception as exc:
            response = {
                "model": None,
                "answer": f"Coach response failed before an answer was returned: {exc}",
            }
        GLib.idle_add(self._apply_coach_answer, response)

    def _apply_coach_answer(self, response: dict) -> bool:
        model = response.get("model") or "local engine unavailable"
        self._append_text(self.coach_view, f"Coach [{model}]: {response['answer']}")
        self.ask_button.set_sensitive(True)
        self._refresh_engine_status()
        self._hide_working_drama()
        self._set_status("Coach answer ready.")
        return False


class SystemCoachDesktopApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="local.system.coach.maintenance.manager")

    def do_activate(self) -> None:  # noqa: N802
        window = self.props.active_window
        if not window:
            window = SystemCoachWindow(self)
        window.present()


def run_desktop() -> None:
    app = SystemCoachDesktopApp()
    app.run(None)
