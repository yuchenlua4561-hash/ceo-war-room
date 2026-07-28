"""Hourly data collector stub.

Replace `collect()` with licensed API calls. Keep API keys in repository secrets.
The sample deliberately preserves the existing JSON when no provider is configured.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dashboard.json"


def validate(data: dict) -> None:
    required = {
        "ceo_summary", "risk", "markets", "liquid_cooling_pumps",
        "competitors", "news", "supply_chain",
    }
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Missing dashboard fields: {sorted(missing)}")
    required_markets = {
        "usd_twd", "jpy_twd", "eur_twd", "gold_twd",
        "brent", "copper_3m", "aluminium_3m",
    }
    missing_markets = required_markets - data["markets"].keys()
    if missing_markets:
        raise ValueError(f"Missing market fields: {sorted(missing_markets)}")


def collect(previous: dict) -> dict | None:
    if not os.getenv("MARKET_API_KEY"):
        print("MARKET_API_KEY not configured; sample data was validated but not refreshed.")
        return None
    # Integrate licensed providers here. Normalize every quote to the schema in
    # dashboard.json and calculate change against the previous trading day.
    raise NotImplementedError("Configure licensed market/news providers first.")


def main() -> None:
    previous = json.loads(OUTPUT.read_text(encoding="utf-8"))
    data = collect(previous)
    if data is None:
        validate(previous)
        return
    data["updated_at"] = datetime.now(ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds")
    validate(data)
    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
