"""Command-line entry point for the Agent Guidance MCP server."""


import argparse
import sys

from . import __version__
from .catalog import find_standards_root
from .server import create_server
from .token_config import TokenOptimizationConfig


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Agent Guidance MCP server.")
    parser.add_argument(
        "--root",
        help=(
            "Path to a standards corpus. Defaults to AGENT_GUIDANCE_ROOT, "
            "the bundled corpus, or --root."
        ),
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Run post-install setup to register server in IDE client configs.",
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "manual"],
        default="auto",
        help="Setup mode: auto (all clients) or manual (interactive menu). Default: auto.",
    )
    parser.add_argument(
        "--clients",
        default="",
        help="Comma-separated client indices for --mode=manual (non-interactive escape hatch).",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Download and update ECC skills and UI/UX data from GitHub.",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Run clean-up to remove server registrations, config rules, and databases.",
    )
    parser.add_argument(
        "--no-optimize",
        action="store_true",
        help="Disable token optimization and savings tracking for this server session.",
    )
    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"agent-guidance-mcp {__version__}",
        help="Show version information and exit.",
    )
    return parser.parse_args(argv)


def main() -> None:
    try:
        args = parse_args()
        if args.setup:
            from .setup import run_setup
            selected = None
            if args.clients:
                selected = {int(c.strip()) for c in args.clients.split(",") if c.strip().isdigit()}
            run_setup(mode=args.mode, selected=selected)
            sys.exit(0)
        if args.update:
            from .updater import run_update
            run_update()
            sys.exit(0)
        if args.uninstall:
            from .setup import run_uninstall
            run_uninstall()
            sys.exit(0)
        root = find_standards_root(args.root)
        config = TokenOptimizationConfig.disabled() if args.no_optimize else None
        server = create_server(root, config=config)
        server.run()
    except KeyboardInterrupt:
        sys.exit(0)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
