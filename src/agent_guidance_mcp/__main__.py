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
