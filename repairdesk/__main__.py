import argparse
import json
import sys
from pathlib import Path
from .scenarios import SCENARIO_IDS, build_demo, replay
from .evaluation import evaluate
from .server import serve


def emit(data, destination=None):
    encoded = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if destination:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(encoded)
        print("Wrote " + str(path.resolve()))
    else:
        print(encoded, end="")


def main():
    parser = argparse.ArgumentParser(description="Replay a pinned metadata incident with inspectable evidence.")
    commands = parser.add_subparsers(dest="command", required=True)
    replay_parser = commands.add_parser("replay", help="Run one local scenario")
    replay_parser.add_argument("--scenario", required=True, choices=SCENARIO_IDS)
    replay_parser.add_argument("--output", help="Write the JSON receipt to this path")
    replay_parser.add_argument("--db", default=":memory:", help="Optional persistent SQLite store")
    build_parser = commands.add_parser("build", help="Build all scenarios and evaluations")
    build_parser.add_argument("--output", help="Write the complete JSON bundle to this path")
    evaluate_parser = commands.add_parser("evaluate", help="Run the behavioral fixture evaluation")
    evaluate_parser.add_argument("--output", help="Write the evaluation JSON to this path")
    serve_parser = commands.add_parser("serve", help="Serve the demo and local API on 127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    try:
        if args.command == "serve":
            serve(args.port)
            return 0
        if args.command == "replay":
            result = replay(args.scenario, args.db)
            emit(result, args.output)
            return 0 if result["regression"]["passed"] else 1
        if args.command == "build":
            result = build_demo()
            emit(result, args.output)
            return 0 if result["evaluation"]["all_passed"] else 1
        if args.command == "evaluate":
            result = evaluate()
            emit(result, args.output)
            return 0 if result["all_passed"] else 1
    except (OSError, ValueError) as exc:
        parser.exit(1, "error: " + str(exc) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
