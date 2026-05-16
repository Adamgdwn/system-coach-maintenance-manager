"""Native GTK desktop shell for the stack coach."""

from __future__ import annotations

import json
import threading

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")

from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from .agents import build_agents
from .ai_engine import answer_question, get_engine_status
from .diagnostics import collect_diagnostics
from .exporting import build_share_text
from .maintenance_reporting import generate_maintenance_report
from .reporting import generate_report
from .request_plans import format_request_plan, prepare_request_plan
from .scanner import map_filesystem, suggest_roots


def build_report() -> dict:
    results = [agent.run() for agent in build_agents()]
    return generate_report(results)


def build_maintenance_report() -> dict:
    return generate_maintenance_report(collect_diagnostics())


class StackCoachWindow(Gtk.ApplicationWindow):
    NARROW_LAYOUT_WIDTH = 1120

    def __init__(self, app: Gtk.Application):
        super().__init__(application=app, title="System Stack Review and Coach")
        self.set_default_size(1220, 840)
        self.set_border_width(16)

        self.current_report: dict | None = None
        self.current_map: dict | None = None
        self.current_maintenance: dict | None = None
        self.current_request_plan: dict | None = None
        self.engine_status: dict | None = None

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.add(root)

        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        root.pack_start(header, False, False, 0)

        title = Gtk.Label()
        title.set_markup("<span size='24000' weight='bold'>System Stack Review and Coach</span>")
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

        notebook = Gtk.Notebook()
        notebook.set_scrollable(True)
        right.pack_start(notebook, True, True, 0)

        self.components_view = self._make_text_view()
        notebook.append_page(self._frame("Detected Components", self.components_view), Gtk.Label(label="Components"))

        self.stacks_view = self._make_text_view()
        notebook.append_page(self._frame("Stack Patterns And Tips", self.stacks_view), Gtk.Label(label="Stacks"))

        self.scan_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.scan_page.set_border_width(6)
        notebook.append_page(self.scan_page, Gtk.Label(label="Find And Map"))
        self._build_scan_page()

        self.maintenance_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.maintenance_page.set_border_width(6)
        notebook.append_page(self.maintenance_page, Gtk.Label(label="Maintenance"))
        self._build_maintenance_page()

        self.coach_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.coach_page.set_border_width(6)
        notebook.append_page(self.coach_page, Gtk.Label(label="Ask The Coach"))
        self._build_coach_page()

        self.command_view = self._make_text_view()
        notebook.append_page(self._frame("Command Log", self.command_view), Gtk.Label(label="Command Log"))

        self.connect("size-allocate", self._on_size_allocate)
        self.show_all()
        self._refresh_engine_status()
        self.on_run_review(None)
        self.on_run_maintenance(None)

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

    def _build_coach_page(self) -> None:
        intro = Gtk.Label(
            label=(
                "Ask questions about your stack and the app will answer using the local AI engine when available. "
                "This keeps the coaching flow interactive without sending your environment data away."
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
            "My cursor size seems odd. Make it smaller.",
        ]:
            button = Gtk.Button(label=prompt)
            button.connect("clicked", self.on_prompt_clicked, prompt)
            prompts_row.add(button)

        self.question_entry = Gtk.Entry()
        self.question_entry.set_placeholder_text("Ask a question about your environment, tools, or selected roots...")
        self.question_entry.connect("activate", self.on_ask_coach)
        self.coach_page.pack_start(self.question_entry, False, False, 0)

        coach_actions = self._make_wrapping_flow()
        self.coach_page.pack_start(coach_actions, False, False, 0)
        self.ask_button = Gtk.Button(label="Ask Local AI")
        self.ask_button.connect("clicked", self.on_ask_coach)
        coach_actions.add(self.ask_button)

        self.prepare_request_button = Gtk.Button(label="Prepare Approval Plan")
        self.prepare_request_button.connect("clicked", self.on_prepare_request_plan)
        coach_actions.add(self.prepare_request_button)

        self.refresh_engine_button = Gtk.Button(label="Refresh AI Status")
        self.refresh_engine_button.connect("clicked", self.on_refresh_engine_clicked)
        coach_actions.add(self.refresh_engine_button)

        self.coach_view = self._make_text_view()
        self.coach_page.pack_start(self._frame("Coach Conversation", self.coach_view), True, True, 0)

        self.request_plan_view = self._make_text_view()
        self.coach_page.pack_start(self._frame("Latest Approval Plan", self.request_plan_view), True, True, 0)

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
            if self.content_paned.get_orientation() != Gtk.Orientation.VERTICAL:
                self.content_paned.set_orientation(Gtk.Orientation.VERTICAL)
            self.content_paned.set_position(int(allocation.height * 0.44))
            return

        if self.content_paned.get_orientation() != Gtk.Orientation.HORIZONTAL:
            self.content_paned.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.content_paned.set_position(int(allocation.width * 0.46))

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
                plan_sections.extend(
                    [
                        f"{plan['title']}",
                        f"Risk: {plan['risk']}",
                        f"Requires privilege: {plan['requires_privilege']}",
                        f"Reversible: {plan['reversible']}",
                        f"Execution enabled: {plan['execution_enabled']}",
                        "Commands:",
                        *[f"- {command}" for command in plan["commands"]],
                        f"Expected effect: {plan['expected_effect']}",
                        f"Approval gate: {plan['approval_prompt']}",
                        "",
                    ]
                )
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
        return False

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
        self.question_entry.set_text(prompt)
        if "cursor" in prompt.lower():
            self.on_prepare_request_plan(None)
            return
        self.on_ask_coach(None)

    def on_prepare_request_plan(self, _widget: Gtk.Widget | None) -> None:
        request_text = self.question_entry.get_text().strip()
        if not request_text:
            self._set_status("Type a maintenance request before preparing a plan.")
            return

        environment = (self.current_report or {}).get("environment", {})
        maintenance_desktop = (self.current_maintenance or {}).get("metrics", {}).get("desktop", {})
        desktop_hint = environment.get("desktop") or maintenance_desktop.get("current_desktop")
        plan = prepare_request_plan(
            request_text,
            os_name=environment.get("os") or (self.current_maintenance or {}).get("metrics", {}).get("platform", {}).get("os"),
            distribution_hint=desktop_hint,
        )
        self.current_request_plan = plan
        formatted = format_request_plan(plan)
        self._set_text(self.request_plan_view, formatted)
        self._append_text(self.coach_view, f"You: {request_text}")
        self._append_text(self.coach_view, f"Plan [{plan['platform']}]:\n{formatted}")
        self._set_status("Approval-required plan prepared. No change was executed.")

    def on_ask_coach(self, _widget: Gtk.Widget | None) -> None:
        question = self.question_entry.get_text().strip()
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


class StackCoachDesktopApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="local.stack.review.coach")

    def do_activate(self) -> None:  # noqa: N802
        window = self.props.active_window
        if not window:
            window = StackCoachWindow(self)
        window.present()


def run_desktop() -> None:
    app = StackCoachDesktopApp()
    app.run(None)
