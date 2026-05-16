"""Command line entry point."""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch the System Stack Review and Coach GUI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--browser", action="store_true", help="Launch the browser-hosted UI instead of the desktop shell.")
    args = parser.parse_args()
    if args.browser:
        from .server import serve

        serve(host=args.host, port=args.port or None, open_browser=not args.no_browser)
        return
    from .desktop_app import run_desktop

    run_desktop()


if __name__ == "__main__":
    main()
