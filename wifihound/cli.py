"""Command-line entry point.

There is a single way to run WiFiHound:

    python -m wifihound            # or: python -m wifihound serve
    sudo python -m wifihound       # unlocks live radio capture + deauth

Offensive / live-radio features are enabled automatically when the process runs
as root, so just use ``sudo`` when you need them. No special flags.
"""

from __future__ import annotations

import argparse
import sys
import webbrowser

from wifihound import __version__
from wifihound.operations.base import offensive_available


def _serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ImportError:
        print("[!] uvicorn is not installed. Run: pip install -r requirements.txt",
              file=sys.stderr)
        return 1

    if offensive_available():
        print("[*] Running as root: live radio capture and deauth are available.")
        print("    Use only on networks you own or are authorized to test.")
    else:
        print("[*] Running unprivileged: offline analysis and replay only.")
        print("    Start with sudo to enable live radio capture and deauth.")

    url = f"http://{args.host}:{args.port}"
    print(f"[*] WiFiHound v{__version__} -> {url}")
    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    # Import string enables reload; the app is built in server.create_app().
    uvicorn.run("wifihound.server:app", host=args.host, port=args.port,
                reload=args.reload, log_level="info")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wifihound",
        description="Interactive graph analysis for WiFi recon data.",
    )
    parser.add_argument("--version", action="version",
                        version=f"WiFiHound {__version__}")
    # Plain serve flags; live radio / deauth are unlocked by running as root.
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true",
                        help="Do not auto-open the browser.")
    parser.add_argument("--reload", action="store_true",
                        help="Auto-reload on code changes (development).")

    sub = parser.add_subparsers(dest="command")
    serve = sub.add_parser("serve", help="Start the local web app (default).")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--no-browser", action="store_true")
    serve.add_argument("--reload", action="store_true")
    serve.set_defaults(func=_serve)

    parser.set_defaults(func=_serve)  # serve is the default action
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
