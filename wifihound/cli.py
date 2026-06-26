"""Command-line entry point: ``python -m wifihound serve``."""

from __future__ import annotations

import argparse
import sys
import webbrowser

from wifihound import __version__
from wifihound.operations.base import set_offensive_enabled


def _serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ImportError:
        print("[!] uvicorn is not installed. Run: pip install -r requirements.txt",
              file=sys.stderr)
        return 1

    set_offensive_enabled(args.enable_offensive)
    if args.enable_offensive:
        print("[!] OFFENSIVE OPERATIONS ENABLED — use only on authorized networks.")

    url = f"http://{args.host}:{args.port}"
    print(f"[*] WiFi-Hound v{__version__} → {url}")
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
        description="BloodHound-style interactive graph analysis for Wi-Fi recon data.",
    )
    parser.add_argument("--version", action="version",
                        version=f"WiFi-Hound {__version__}")
    sub = parser.add_subparsers(dest="command")

    serve = sub.add_parser("serve", help="Start the local web app.")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--no-browser", action="store_true",
                       help="Do not auto-open the browser.")
    serve.add_argument("--reload", action="store_true",
                       help="Auto-reload on code changes (development).")
    serve.add_argument("--enable-offensive", action="store_true",
                       help="Enable offensive operations (authorized testing only).")
    serve.set_defaults(func=_serve)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
