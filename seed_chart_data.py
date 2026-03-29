"""
seed_chart_data.py
Run this ONCE from your project root (where the logs/ folder is).
It takes your existing audit_logs.json entries, duplicates and spreads
them across the past 30 days with realistic risk score variation,
so the Risk Score Trend chart shows a proper line graph.

Usage:
    python seed_chart_data.py
"""

import json
import random
import copy
from pathlib import Path
from datetime import datetime, timedelta, timezone

AUDIT_LOG_PATH = Path("logs/audit_logs.json")

def load_logs():
    if not AUDIT_LOG_PATH.exists():
        print(f"ERROR: {AUDIT_LOG_PATH} not found. Make sure you run this from your project root.")
        return []
    with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_logs(logs):
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2, default=str)

def vary_risk(base_score, day_offset):
    """Add realistic day-to-day variation to risk scores."""
    # Use day_offset as seed for consistent but varied results
    random.seed(day_offset * 7)
    variation = random.uniform(-18, 22)
    score = base_score + variation
    return round(max(10, min(95, score)), 1)

def risk_to_level(score):
    if score >= 65: return "HIGH"
    if score >= 40: return "MEDIUM"
    return "LOW"

def main():
    existing_logs = load_logs()
    if not existing_logs:
        print("No existing logs found.")
        return

    print(f"Found {len(existing_logs)} existing log entries.")

    # Keep all original logs untouched
    seeded_logs = list(existing_logs)

    # Use the existing logs as templates to seed the past 30 days
    # Skip the last 2 days (Mar 28-29) since real data already exists there
    today = datetime.now(timezone.utc).date()
    
    # Check which days already have data
    days_with_data = set()
    for log in existing_logs:
        try:
            d = datetime.fromisoformat(log["timestamp"].replace("Z", "+00:00"))
            days_with_data.add(d.date())
        except:
            pass

    print(f"Days with existing data: {sorted(days_with_data)}")

    # Templates to cycle through for variety
    templates = existing_logs[:8] if len(existing_logs) >= 8 else existing_logs

    added = 0
    for day_offset in range(29, 1, -1):  # 29 days ago to 2 days ago
        target_date = today - timedelta(days=day_offset)
        
        if target_date in days_with_data:
            continue  # Don't touch days that already have real data

        # Add 1-4 entries per day for realistic variation
        random.seed(day_offset)
        entries_per_day = random.randint(1, 4)

        for entry_idx in range(entries_per_day):
            template = templates[(day_offset + entry_idx) % len(templates)]
            new_entry = copy.deepcopy(template)

            # Assign new timestamp on this day
            hour = random.randint(8, 20)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            new_ts = datetime(
                target_date.year, target_date.month, target_date.day,
                hour, minute, second, tzinfo=timezone.utc
            )

            new_score = vary_risk(template["risk_score"], day_offset * 10 + entry_idx)
            new_level = risk_to_level(new_score)

            new_entry["trace_id"] = f"SC-SEED{day_offset:02d}{entry_idx:02d}-HIST"
            new_entry["timestamp"] = new_ts.isoformat().replace("+00:00", "Z")
            new_entry["completed_at"] = new_ts.isoformat().replace("+00:00", "Z")
            new_entry["risk_score"] = new_score
            new_entry["risk_level"] = new_level
            # Keep decision as PROCEED for low/medium, REROUTE for high
            new_entry["decision"] = "REROUTE" if new_score >= 65 else "PROCEED"
            # Strip pipeline_steps to keep file size small
            new_entry["pipeline_steps"] = []
            new_entry["total_steps"] = 0

            seeded_logs.append(new_entry)
            added += 1

    # Sort by timestamp
    seeded_logs.sort(key=lambda x: x.get("timestamp", ""))

    save_logs(seeded_logs)
    print(f"Done! Added {added} historical entries across 28 days.")
    print(f"Total log entries now: {len(seeded_logs)}")
    print(f"Reload your dashboard — the chart should now show a proper trend line.")

if __name__ == "__main__":
    main()
