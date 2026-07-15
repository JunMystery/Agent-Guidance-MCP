"""Command-line entry point for the Agent Guidance MCP server."""


import argparse
import os
import sys

from . import __version__
from .catalog import find_standards_root
from .server import create_server, run_session_start
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
        choices=["auto", "manual", "ide"],
        default="auto",
        help="Setup mode: auto (all clients), manual (choose component groups), or ide (select individual IDEs). Default: auto.",
    )
    parser.add_argument(
        "--clients",
        default="",
        help="Comma-separated client indices for --mode=manual (non-interactive escape hatch).",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Download and update skill repositories from GitHub.",
    )
    parser.add_argument(
        "--auto-update",
        nargs="?",
        const="weekly",
        choices=["weekly", "monthly"],
        help=(
            "Enable scheduled automatic skill updates. Checks persisted state; "
            "runs update if the configured interval has elapsed. "
            "Default: weekly if no value given. "
            "Set AGENT_AUTO_UPDATE_INTERVAL env var to override."
        ),
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Run clean-up to remove server registrations, config rules, and databases.",
    )
    parser.add_argument(
        "--session-start",
        action="store_true",
        help=(
            "Session-start auto-activation: passes the priority gate and returns "
            "project context as a JSON payload for the session-start hook."
        ),
    )
    parser.add_argument(
        "--project-path",
        default=".",
        help="Project root path for --session-start (default: current dir).",
    )
    parser.add_argument(
        "--no-optimize",
        action="store_true",
        help="Disable token optimization and savings tracking for this server session.",
    )
    parser.add_argument(
        "--embed-daemon",
        action="store_true",
        help="Start embedding inference daemon as a standalone foreground process.",
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Start lightweight usage dashboard server (no ML model needed).",
    )
    parser.add_argument(
        "--client-name",
        help="Human-readable client/IDE name logged in usage sessions.",
    )
    parser.add_argument(
        "--session-label",
        help="Human-readable label for the current usage session.",
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

        if args.session_start:
            old_stdout = sys.stdout
            sys.stdout = sys.stderr
            try:
                result_json = run_session_start(
                    root=args.root,
                    project_path=args.project_path,
                )
            finally:
                sys.stdout = old_stdout
            print(result_json)
            sys.exit(0)

        if args.embed_daemon:
            from .embed_daemon import main as daemon_main
            daemon_main()
            sys.exit(0)

        if args.dashboard:
            from .dashboard_server import run_dashboard
            run_dashboard()
            sys.exit(0)

        # Compatibility check before server start
        from .updater import check_compatibility
        check_compatibility()

        # Auto-update (standalone command — runs check and exits)
        if args.auto_update:
            interval = os.environ.get("AGENT_AUTO_UPDATE_INTERVAL", args.auto_update).strip()
            if interval not in ("weekly", "monthly"):
                interval = args.auto_update
            from .updater import check_auto_update
            check_auto_update(interval=interval)
            sys.exit(0)

        # Runtime auto-update via environment variable (runs alongside server)
        auto_env = os.environ.get("AGENT_AUTO_UPDATE_INTERVAL", "").strip()
        if auto_env in ("weekly", "monthly"):
            from .updater import check_auto_update
            check_auto_update(interval=auto_env)

        root = find_standards_root(args.root)
        config = TokenOptimizationConfig.disabled() if args.no_optimize else None
        if args.client_name:
            os.environ["AGENT_CLIENT_NAME"] = args.client_name
        if args.session_label:
            os.environ["AGENT_SESSION_LABEL"] = args.session_label
        server = create_server(root, config=config)
        server.run()
    except KeyboardInterrupt:
        from .server import get_usage
        usage = get_usage()
        if usage is not None:
            usage.session_end()
            usage.close()
        sys.exit(0)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
