"""Usage: python3 -m sourcecheck audit W123 --output report.json --evidence-dir evidence"""
import argparse
import json
import sys
from pathlib import Path
from .audit import audit


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only OpenAlex/DOI-registry title audit; no corrections or identity decisions.")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("audit", help="Compare one OpenAlex work with at most six public DOI registry records")
    command.add_argument("identifier", help="W-number, DOI, or plain HTTPS OpenAlex/doi.org URL")
    command.add_argument("--output", required=True, help="Write the JSON report")
    command.add_argument("--evidence-dir", required=True, help="Save content-addressed raw HTTP bodies here")
    args = parser.parse_args(argv)
    try:
        report = audit(args.identifier, args.evidence_dir)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError) as exc:
        parser.exit(2, "error: {}\n".format(exc))
    print("{}: {}".format(report["status"], report["summary"]))
    print("Report: {}".format(output.resolve()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
