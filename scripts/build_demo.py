#!/usr/bin/env python3
"""Regenerate the browser's pinned, deterministic evidence bundle."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from repairdesk.scenarios import build_demo

if __name__ == "__main__":
    result = build_demo()
    destination = ROOT / "data/demo.json"
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print("Wrote {}: {} / {} evaluation cases passed".format(destination, result["evaluation"]["passed"], result["evaluation"]["total"]))
    sys.exit(0 if result["evaluation"]["all_passed"] else 1)
