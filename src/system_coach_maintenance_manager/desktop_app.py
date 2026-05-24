"""Native GTK desktop shell for the system coach."""

from __future__ import annotations

import json
import threading

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")

from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from .agents import build_agents
from .ai_engine import analyze_action_result, answer_question, get_engine_status, reason_about_request
from .diagnostics import collect_diagnostics
from .exporting import build_share_text
from .followup_plans import build_followup_request
from .maintenance_actions import execute_guarded_action
from .maintenance_history import format_history, load_history, record_learning_note, record_maintenance_report, record_request_plan
from .maintenance_history import record_action_result
from .maintenance_reporting import generate_maintenance_report
from .pop_cosmic_actions import prepare_pop_cosmic_action, prepare_verification_plan
from .pop_cosmic_brain import analyze_pop_cosmic_issue
from .pop_cosmic_deep_scan import run_pop_cosmic_deep_scan
from .pop_cosmic_knowledge import load_relevant_lessons, load_relevant_research, make_lesson, save_lesson, save_research_records
from .pop_cosmic_research import research_pop_cosmic_issue
from .reporting import generate_report
from .request_evidence import collect_request_evidence
from .request_plans import format_request_plan, prepare_request_plan, review_request_intake
from .scanner import map_filesystem, suggest_roots


def build_report() -> dict:
    results = [agent.run() for agent in build_agents()]
    return generate_report(results)


def build_maintenance_report() -> dict:
    return generate_maintenance_report(collect_diagnostics())


class SystemCoachWindow(Gtk.ApplicationWindow):
    DEFAULT_WINDOW_WIDTH = 1120
    DEFAULT_WINDOW_HEIGHT = 720
    MIN_VIEWPORT_WIDTH = 720
    MIN_VIEWPORT_HEIGHT = 420
    NARROW_LAYOUT_WIDTH = 1120

    def __init__(self, app: Gtk.Application):
        super().__init__(application=app, title="System Coach and Maintenance Manager")
        self.set_default_size(self.DEFAULT_WINDOW_WIDTH, self.DEFAULT_WINDOW_HEIGHT)
        self.set_resizable(True)
        self.set_border_width(16)

        self.current_report: dict | None = None
        self.current_map: dict | None = None
        self.current_maintenance: dict | None = None
        self.current_request_plan: dict | None = None
        self.current_history: dict | None = None
        self.engine_status: dict | None = None
        self.queued_plans: list[dict] = []
        self.request_context: list[str] = []
        self.latest_request_reasoning: dict | None = None
        self.pop_cosmic_scan: dict | None = None
        self.pop_cosmic_research: dict | None = None
        self.pop_cosmic_analysis: dict | None = None
        self.pop_cosmic_plan: dict | None = None
        self.pop_cosmic_result: dict | None = None

        outer_scroll = Gtk.ScrolledWindow()
        outer_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        outer_scroll.set_min_content_width(self.MIN_VIEWPORT_WIDTH)
        outer_scroll.set_min_content_height(self.MIN_VIEWPORT_HEIGHT)
        outer_scroll.set_hexpand(True)
        outer_scroll.set_vexpand(True)
        self.add(outer_scroll)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        root.set_hexpand(True)
        root.set_vexpand(True)
        outer_scroll.add(root)

        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        root.pack_start(header, False, False, 0)

        title = Gtk.Label()
        title.set_markup("<span size='24000' weight='bold'>System Coach and Maintenance Manager</span>")
        title.set_xalign(0)
        header.pack_start(title, False, False, 0)

        subtitle = Gtk.Label(
            label=(
                "A local teaching tool for understanding your environment, installed tools, "
                "and selected folders without sending data anywhere else."
            )
        )
        subtitle.set_xalign(0)
        subtitle.set_line_wrap(True)
        header.pack_start(subtitle, False, False, 0)

        action_row = self._make_wrapping_flow()
        root.pack_start(action_row, False, False, 0)

        self.review_button = Gtk.Button(label="Run Local Review")
        self.review_button.connect("clicked", self.on_run_review)
        action_row.add(self.review_button)

        self.map_button = Gtk.Button(label="Scan Selected Roots")
        self.map_button.connect("clicked", self.on_run_map)
        action_row.add(self.map_button)

        self.maintenance_button = Gtk.Button(label="Run Maintenance Diagnostics")
        self.maintenance_button.connect("clicked", self.on_run_maintenance)
        action_row.add(self.maintenance_button)

        self.share_button = Gtk.Button(label="Copy Share Summary")
        self.share_button.connect("clicked", self.on_copy_summary)
        action_row.add(self.share_button)

        nav_row = self._make_wrapping_flow()
        root.pack_start(nav_row, False, False, 0)

        for label, page_index in [
            ("Pop/COSMIC Agent", 4),
            ("Request Desk", 5),
            ("Approval Queue", 6),
            ("Ask The Coach", 8),
        ]:
            button = Gtk.Button(label=label)
            button.connect("clicked", self.on_nav_clicked, page_index)
            nav_row.add(button)

        self.execute_nav_button = Gtk.Button(label="Execute Fixes")
        self.execute_nav_button.set_tooltip_text("Open the Approval Queue and run the selected fix when its contract is enabled.")
        self.execute_nav_button.connect("clicked", self.on_execute_selected_action)
        nav_row.add(self.execute_nav_button)

        self.status_label = Gtk.Label(label="Ready. Run a review to learn the environment.")
        self.status_label.set_xalign(0)
        self.status_label.set_line_wrap(True)
        root.pack_start(self.status_label, False, False, 0)

        self.engine_label = Gtk.Label(label="Checking local AI engine...")
        self.engine_label.set_xalign(0)
        self.engine_label.set_line_wrap(True)
        root.pack_start(self.engine_label, False, False, 0)

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

        self.command_view = self._make_text_view()
        self.notebook.append_page(self._frame("Command Log", self.command_view), Gtk.Label(label="Command Log"))

        self._content_orientation: Gtk.Orientation | None = None
        self.connect("size-allocate", self._on_size_allocate)
        self.show_all()
        self._refresh_engine_status()
        self.on_run_review(None)
        self.on_run_maintenance(None)
        self.on_refresh_history(None)
        self._refresh_approval_queue()

    def _make_text_view(self) -> Gtk.TextView:
        view = Gtk.TextView()
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

    def _set_text(self, view: Gtk.TextView, text: str) -> None:
        buffer_ = view.get_buffer()
        buffer_.set_text(text)

    def _set_status(self, text: str) -> None:
        self.status_label.set_text(text)

    def _append_text(self, view: Gtk.TextView, text: str) -> None:
        buffer_ = view.get_buffer()
        existing = buffer_.get_text(buffer_.get_start_iter(), buffer_.get_end_iter(), True)
        buffer_.set_text(f"{existing}\n\n{text}".strip())

    def _refresh_engine_status(self) -> None:
        self.engine_status = get_engine_status()
        self.engine_label.set_text(f"Local AI engine: {self.engine_status['message']}")

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
        self._set_status("Running local review...")
        threading.Thread(target=self._run_review_worker, daemon=True).start()

    def _run_review_worker(self) -> None:
        try:
            report = build_report()
            GLib.idle_add(self._apply_report, report)
        except Exception as exc:
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
            "\n".join(f"{key.replace('_', ' ').title()}: {value}" for key, value in report["environment"].items()),
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
        self._set_status("Review complete. Explore the desktop app panels to learn the environment.")
        self.review_button.set_sensitive(True)
        return False

    def on_run_map(self, _button: Gtk.Button | None) -> None:
        roots = self._selected_roots()
        if not roots:
            self._set_status("Select at least one root before scanning.")
            return
        self.map_button.set_sensitive(False)
        self._set_status("Scanning the selected roots locally...")
        threading.Thread(target=self._run_map_worker, args=(roots,), daemon=True).start()

    def _run_map_worker(self, roots: list[str]) -> None:
        try:
            system_map = map_filesystem(roots)
            GLib.idle_add(self._apply_map, system_map)
        except Exception as exc:
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
        self._set_status("Filesystem map complete.")
        self.map_button.set_sensitive(True)
        return False

    def on_run_maintenance(self, _button: Gtk.Button | None) -> None:
        self.maintenance_button.set_sensitive(False)
        self.maintenance_page_button.set_sensitive(False)
        self._set_status("Running read-only maintenance diagnostics...")
        threading.Thread(target=self._run_maintenance_worker, daemon=True).start()

    def _run_maintenance_worker(self) -> None:
        try:
            maintenance_report = build_maintenance_report()
            GLib.idle_add(self._apply_maintenance_report, maintenance_report)
        except Exception as exc:
            GLib.idle_add(self._set_status, f"Maintenance diagnostics failed: {exc}")
            GLib.idle_add(self.maintenance_button.set_sensitive, True)
            GLib.idle_add(self.maintenance_page_button.set_sensitive, True)

    def _apply_maintenance_report(self, maintenance_report: dict) -> bool:
        self.current_maintenance = maintenance_report
        record_maintenance_report(maintenance_report)
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
        self._set_status("Maintenance diagnostics complete. No fixes were executed.")
        self.maintenance_button.set_sensitive(True)
        self.maintenance_page_button.set_sensitive(True)
        self._refresh_history_view()
        self._refresh_approval_queue()
        if maintenance_report["findings"]:
            self._show_maintenance_findings_dialog()
        return False

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
            self.execution_gate_label.set_text("Selected fix can execute. Press Execute Selected Fix to run it now.")
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
        if hasattr(self, "execute_nav_button"):
            self.execute_nav_button.set_sensitive(sensitive and bool(self.queued_plans))
        if hasattr(self, "execute_request_button"):
            self.execute_request_button.set_sensitive(sensitive and self.current_request_plan is not None)

    def _show_action_dialog(self, title: str, body: str, entry_text: str | None = None) -> str | None:
        dialog = Gtk.Dialog(title=title, transient_for=self, modal=True)
        dialog.add_button("Close", Gtk.ResponseType.CLOSE)
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
        dialog.run()
        value = entry.get_text() if entry else None
        dialog.destroy()
        return value

    def _finding_for_plan(self, plan: dict) -> dict | None:
        finding_id = plan.get("finding_id")
        if not finding_id or not self.current_maintenance:
            return None
        for finding in self.current_maintenance.get("findings", []):
            if finding.get("id") == finding_id:
                return finding
        return None

    def _plain_plan_summary(self, plan: dict) -> str:
        finding = self._finding_for_plan(plan)
        contract = plan.get("action_contract", {})
        gate_reasons = contract.get("execution_gate", {}).get("reasons", [])
        commands = contract.get("command_preview", plan.get("commands", []))
        executable = contract.get("execution_enabled", False)
        execution_mode = contract.get("execution_mode")
        changes_system = plan.get("family") in {
            "cursor-size",
            "display-brightness",
            "display-night-light",
            "display-refresh-rate",
            "display-scaling",
            "display-layout-fix",
            "audio-routing",
        }
        reasoning = plan.get("reasoning_brain", {})
        evidence_scopes = reasoning.get("evidence_scopes", [])
        evidence_count = reasoning.get("evidence_command_count", 0)

        if finding:
            problem = finding["summary"]
            evidence = json.dumps(finding.get("evidence", {}), indent=2)
            why = "The maintenance scan found this condition in the latest read-only diagnostics."
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
            alternates = reasoning.get("alternate_families", [])
            if alternates:
                why_parts.append(f"Alternates to keep in mind: {', '.join(alternates)}")
            steps = reasoning.get("investigation_steps", [])
            if steps:
                why_parts.append("Troubleshooting path:\n" + "\n".join(f"- {step}" for step in steps))
            if reasoning.get("permission_plan"):
                why_parts.append(f"Permission plan: {reasoning['permission_plan']}")
            why = "\n".join(why_parts) or plan.get("summary", "The request matched a known maintenance family.")

        if executable and execution_mode == "elevated":
            action = (
                "Execute will request administrator permission with the operating-system password prompt, "
                "then run the exact elevated command(s)."
            )
        elif executable and changes_system:
            action = "Execute will apply this low-risk current-user setting change."
        elif executable:
            action = "Execute will run these guarded command(s), capture the output, and ask the local model for the best next fix direction."
        else:
            action = "Execute will not run this plan yet because the guarded runner blocked it."

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
            "Recommended action:",
            action,
            "",
            "Can execute now:",
            "Yes" if executable else "No",
            "",
            "Commands:",
            *(f"- {command}" for command in commands),
        ]
        if elevation_prompt:
            lines.extend(["", "Elevation:", elevation_prompt.get("message", "This action needs administrator approval.")])
        if gate_reasons:
            lines.extend(["", "Why blocked:", *(f"- {reason}" for reason in gate_reasons)])
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

        self._show_action_dialog("Maintenance Findings", "\n".join(sections).strip())

    def on_nav_clicked(self, _button: Gtk.Button, page_index: int) -> None:
        self.notebook.set_current_page(page_index)

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
        self._start_plan_execution(plan)

    def on_execute_current_request(self, _button: Gtk.Button | None) -> None:
        if not self.current_request_plan:
            self._set_status("Prepare a recommendation before executing.")
            self._show_action_dialog(
                "No Recommendation Ready",
                "Request Desk has not prepared a current recommendation yet. Describe the issue first.",
            )
            return
        self._start_plan_execution(self.current_request_plan)

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
        result = execute_guarded_action(contract, confirmation_text)
        record_action_result(result)
        analysis = analyze_action_result(plan, result) if result["status"] == "completed" else None
        GLib.idle_add(self._apply_execution_result, plan, result, analysis)

    def _apply_execution_result(self, plan: dict, result: dict, analysis: dict | None) -> bool:
        contract = plan.get("action_contract", {})
        followup_plan = None
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
        if result["status"] == "completed":
            analysis = analysis or {}
            followup_plan = self._prepare_followup_plan_from_execution(plan, result, analysis)
            analysis_label = f"Local model analysis [{analysis.get('model')}]" if analysis.get("model") else "Local model analysis"
            body_lines = [
                "Execution completed.",
                "",
                f"Selected plan: {plan['title']}",
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
                        "Press Execute Current Recommendation to apply this fix, or type a change in Request Desk to modify it.",
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
                    f"Selected plan: {plan['title']}",
                    f"Action id: {contract.get('id', 'unknown')}",
                    f"Status: {result['status']}",
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
            status = "Execution did not run. Review the gate reason."
        self._show_action_dialog("Execute Selected Fix", body)
        self._refresh_history_view()
        self._refresh_approval_queue()
        self._set_execution_buttons_sensitive(True)
        self._set_status(status)
        return False

    def _pop_cosmic_concern(self) -> str:
        buffer_ = self.pop_cosmic_concern_view.get_buffer()
        return buffer_.get_text(buffer_.get_start_iter(), buffer_.get_end_iter(), True).strip()

    def on_pop_cosmic_scan(self, _button: Gtk.Button | None) -> None:
        scope = self.pop_cosmic_scope.get_active_text() or "standard"
        self._set_status(f"Running Pop!_OS/COSMIC {scope} scan...")
        threading.Thread(target=self._pop_cosmic_scan_worker, args=(scope,), daemon=True).start()

    def _pop_cosmic_scan_worker(self, scope: str) -> None:
        try:
            scan = run_pop_cosmic_deep_scan(scope)
            GLib.idle_add(self._apply_pop_cosmic_scan, scan)
        except Exception as exc:
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
        self._set_text(self.pop_cosmic_profile_view, "\n".join(lines))
        self._set_status("Pop!_OS/COSMIC scan complete.")
        return False

    def on_pop_cosmic_research(self, _button: Gtk.Button | None) -> None:
        if not self.pop_cosmic_scan:
            self.on_pop_cosmic_scan(None)
            self._set_status("Started scan first; run research again after scan completes.")
            return
        symptom = self._pop_cosmic_concern()
        self._set_status("Preparing source-aware Pop!_OS/COSMIC research records...")
        threading.Thread(target=self._pop_cosmic_research_worker, args=(symptom,), daemon=True).start()

    def _pop_cosmic_research_worker(self, symptom: str) -> None:
        try:
            profile = (self.pop_cosmic_scan or {}).get("profile", {})
            research = research_pop_cosmic_issue(symptom, profile, enabled=False)
            save_research_records(research.get("records", []))
            GLib.idle_add(self._apply_pop_cosmic_research, research)
        except Exception as exc:
            GLib.idle_add(self._set_status, f"Pop!_OS/COSMIC research failed: {exc}")

    def _apply_pop_cosmic_research(self, research: dict) -> bool:
        self.pop_cosmic_research = research
        records = research.get("records", [])
        lines = [
            f"Research enabled: {research.get('enabled')}",
            f"Safe query: {research.get('query')}",
            research.get("privacy", ""),
            "",
            "Sources:",
            *[f"- [{record.get('trust_level')}] {record.get('title')} - {record.get('url')}" for record in records],
        ]
        self._append_text(self.pop_cosmic_analysis_view, "\n".join(lines))
        self._set_status("Pop!_OS/COSMIC research records prepared.")
        return False

    def on_pop_cosmic_analyze(self, _button: Gtk.Button | None) -> None:
        if not self.pop_cosmic_scan:
            self.on_pop_cosmic_scan(None)
            self._set_status("Started scan first; ask the model after scan completes.")
            return
        symptom = self._pop_cosmic_concern()
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
        for hypothesis in analysis.get("hypotheses", []):
            lines.append(f"- {hypothesis.get('id', '?')}: {hypothesis.get('summary')}")
        lines.extend(["", "Ranked actions:"])
        for index, action in enumerate(analysis.get("ranked_actions", []), 1):
            lines.append(f"{index}. {action.get('action_key')} - {action.get('title')} [{action.get('risk')}]")
            if action.get("why"):
                lines.append(f"   why: {action.get('why')}")
        self._set_text(self.pop_cosmic_analysis_view, "\n".join(lines))
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
        self._set_status("Verifying Pop!_OS/COSMIC action with a fresh scan...")
        threading.Thread(target=self._pop_cosmic_verify_worker, daemon=True).start()

    def _pop_cosmic_verify_worker(self) -> None:
        try:
            post_scan = prepare_verification_plan(self.pop_cosmic_result or {}, self.pop_cosmic_scan or {})
            lesson = make_lesson(
                symptom=self._pop_cosmic_concern(),
                profile=post_scan.get("profile", {}),
                evidence_summary="; ".join(item.get("summary", "") for item in post_scan.get("findings", [])[:4]),
                action_taken=", ".join((self.pop_cosmic_result or {}).get("commands", [])),
                result="improved" if (self.pop_cosmic_result or {}).get("status") == "completed" else "unknown",
                verification="Post-scan collected after Pop/COSMIC action.",
            )
            save_lesson(lesson)
            GLib.idle_add(self._apply_pop_cosmic_verification, post_scan, lesson)
        except Exception as exc:
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
        self.request_send_button.set_sensitive(False)
        self.prepare_request_button.set_sensitive(False)
        self.execute_request_button.set_sensitive(False)
        self._set_status("The local model is thinking through the request...")
        threading.Thread(
            target=self._request_brain_worker,
            args=(request_text, os_name, desktop_hint, self.current_maintenance, force_plan),
            daemon=True,
        ).start()

    def _request_brain_worker(
        self,
        request_text: str,
        os_name: str | None,
        desktop_hint: str | None,
        maintenance_report: dict | None,
        force_plan: bool,
    ) -> None:
        evidence = collect_request_evidence(request_text, os_name=os_name, desktop_hint=desktop_hint)
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
            fallback = review_request_intake(request_text)
            fallback.update(
                {
                    "source": "deterministic-fallback",
                    "model": None,
                    "confidence": None,
                    "alternate_families": [],
                    "evidence_assessment": "Deterministic fallback used the request wording and collected read-only evidence only.",
                    "investigation_steps": fallback.get("questions", []),
                    "permission_plan": "Prepare an approval-required plan before executing any change.",
                    "reasoning_summary": reasoning.get("reasoning_summary", ""),
                    "model_error": reasoning.get("acknowledgement", "Local model request analysis was unavailable."),
                    "request_evidence": evidence,
                }
            )
            reasoning = fallback
        GLib.idle_add(self._apply_request_brain_result, request_text, reasoning, force_plan)

    def _apply_request_brain_result(self, request_text: str, reasoning: dict, force_plan: bool) -> bool:
        self.latest_request_reasoning = reasoning
        self.request_send_button.set_sensitive(True)
        self.prepare_request_button.set_sensitive(True)
        self.execute_request_button.set_sensitive(self.current_request_plan is not None)

        source = reasoning.get("source", "deterministic")
        model = reasoning.get("model")
        brain_label = f"Local model [{model}]" if source == "local-model" and model else source.replace("-", " ").title()

        if reasoning.get("model_error"):
            self._append_request_message("Request Desk", reasoning["model_error"])

        if reasoning.get("ready") or force_plan:
            self._append_request_message("Request Desk", f"{brain_label}: {reasoning['acknowledgement']}")
            self._prepare_request_plan(request_text, reasoning=reasoning)
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
                "Review the current recommendation, then press Execute when this is the selected fix."
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
        self._set_status("Local AI is thinking...")
        threading.Thread(target=self._ask_coach_worker, args=(question,), daemon=True).start()

    def _ask_coach_worker(self, question: str) -> None:
        response = answer_question(
            question,
            self.current_report,
            self.current_map,
            self.current_maintenance,
            self.current_request_plan,
        )
        GLib.idle_add(self._apply_coach_answer, response)

    def _apply_coach_answer(self, response: dict) -> bool:
        model = response.get("model") or "local engine unavailable"
        self._append_text(self.coach_view, f"Coach [{model}]: {response['answer']}")
        self.ask_button.set_sensitive(True)
        self._refresh_engine_status()
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
