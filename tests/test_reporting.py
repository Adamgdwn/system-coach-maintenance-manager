import unittest

from stack_review_coach.reporting import generate_report


class ReportingTests(unittest.TestCase):
    def test_generate_report_builds_user_facing_summary(self):
        report = generate_report(
            [
                {
                    "id": "environment",
                    "findings": {
                        "os": "Linux",
                        "release": "Ubuntu",
                        "machine": "x86_64",
                        "python_runtime": "3.12.3",
                        "shell": "/bin/bash",
                        "desktop": "GNOME",
                        "session_type": "x11",
                    },
                    "commands": [],
                },
                {
                    "id": "languages",
                    "findings": [
                        {
                            "installed": True,
                            "command": "python3",
                            "path": "/usr/bin/python3",
                            "version": "3.12.3",
                            "details": [],
                        },
                        {
                            "installed": True,
                            "command": "node",
                            "path": "/usr/bin/node",
                            "version": "22.0.0",
                            "details": [],
                        },
                    ],
                    "commands": [],
                },
                {
                    "id": "package-managers",
                    "findings": [
                        {
                            "installed": True,
                            "command": "npm",
                            "path": "/usr/bin/npm",
                            "version": "10.0.0",
                            "details": [],
                        }
                    ],
                    "commands": [],
                },
            ]
        )

        self.assertEqual(report["summary"]["installed_component_count"], 3)
        self.assertTrue(
            any(item["title"] == "Python App Stack" for item in report["summary"]["primary_stack_matches"])
        )
        self.assertTrue(any(component["label"] == "Python" for component in report["components"]))

    def test_generate_report_surfaces_creative_toolkit(self):
        report = generate_report(
            [
                {
                    "id": "environment",
                    "findings": {
                        "os": "Linux",
                        "release": "Ubuntu",
                        "machine": "x86_64",
                        "python_runtime": "3.12.3",
                        "shell": "/bin/bash",
                        "desktop": "GNOME",
                        "session_type": "x11",
                    },
                    "commands": [],
                },
                {
                    "id": "creative-tools",
                    "findings": [
                        {
                            "installed": True,
                            "command": "inkscape",
                            "path": "/usr/bin/inkscape",
                            "version": "1.2.2",
                            "details": [],
                        },
                        {
                            "installed": True,
                            "command": "gimp",
                            "path": "flatpak:org.gimp.GIMP",
                            "version": "3.2.2",
                            "details": [],
                        },
                        {
                            "installed": True,
                            "command": "chromium",
                            "path": "/snap/bin/chromium",
                            "version": "147.0.7727.55",
                            "details": [],
                        },
                        {
                            "installed": True,
                            "command": "playwright",
                            "path": "/home/tester/.nvm/versions/node/v24/bin/playwright",
                            "version": "1.59.1",
                            "details": [],
                        },
                    ],
                    "commands": [],
                },
            ]
        )

        self.assertTrue(
            any(
                item["title"] == "Creative And Presentation Toolkit"
                for item in report["summary"]["primary_stack_matches"]
            )
        )
        self.assertTrue(any(component["label"] == "Inkscape" for component in report["components"]))
        self.assertTrue(
            any("creative production toolkit" in recommendation.lower() for recommendation in report["recommendations"])
        )


if __name__ == "__main__":
    unittest.main()
