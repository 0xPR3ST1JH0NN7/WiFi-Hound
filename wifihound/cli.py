"""Command-line entry point.

There is a single way to run WiFiHound:

    python -m wifihound            # or: python -m wifihound serve
    sudo python -m wifihound       # unlocks live radio capture + deauth

Offensive / live-radio features are enabled automatically when the process runs
as root, so just use ``sudo`` when you need them. No special flags.

By default the server runs quietly (no per-request logging). Pass ``--debug``
to see verbose request and framework logs.
"""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

from wifihound import __version__
from wifihound.operations.base import offensive_available

# ANSI colors, used only when writing to a real terminal.
_RED = "\033[91m"
_DIM = "\033[2m"
_RESET = "\033[0m"


def _paint(text: str, code: str) -> str:
    return f"{code}{text}{_RESET}" if sys.stdout.isatty() else text


def _banner() -> str:
    try:
        return (Path(__file__).parent / "banner.txt").read_text(encoding="utf-8")
    except OSError:
        return "WiFiHound\n"


def print_banner() -> None:
    sys.stdout.write(_paint(_banner(), _RED))
    sys.stdout.write(_paint(f"  WiFi recon, mapped.  v{__version__}\n\n", _DIM))


def _serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ImportError:
        print("[!] uvicorn is not installed. Run: pip install -r requirements.txt",
              file=sys.stderr)
        return 1

    print_banner()

    if offensive_available():
        print(_paint("[*] root: live radio capture and deauth are available.", _DIM))
        print(_paint("    Use only on networks you own or are authorized to test.", _DIM))
    else:
        print(_paint("[*] unprivileged: offline analysis and replay only "
                     "(use sudo for live capture).", _DIM))

    url = f"http://{args.host}:{args.port}"
    print(_paint(f"[*] listening on {url}", _DIM))
    if args.debug:
        print(_paint("[*] debug mode: verbose request logging enabled.", _DIM))

    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    # Quiet by default: hide per-request access logs and framework chatter.
    # --debug brings them all back.
    uvicorn.run(
        "wifihound.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="debug" if args.debug else "warning",
        access_log=args.debug,
    )
    return 0


def _add_serve_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--no-browser", action="store_true",
                   help="Do not auto-open the browser.")
    p.add_argument("--reload", action="store_true",
                   help="Auto-reload on code changes (development).")
    p.add_argument("--debug", action="store_true",
                   help="Verbose logging: framework and per-request logs.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wifihound",
        description="Interactive graph analysis for WiFi recon data.",
    )
    parser.add_argument("--version", action="version",
                        version=f"WiFiHound {__version__}")
    _add_serve_flags(parser)

    sub = parser.add_subparsers(dest="command")
    serve = sub.add_parser("serve", help="Start the local web app (default).")
    _add_serve_flags(serve)
    serve.set_defaults(func=_serve)

    parser.set_defaults(func=_serve)  # serve is the default action
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
