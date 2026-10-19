#!/usr/bin/env python3
"""
GitHub Auditor & Relationship Tracker
Analyzes followers, following, mutuals, fans, and history deltas using GitHub REST API.
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv

# ---------------------------------------------------------
# Configuration & Authentication
# ---------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

def get_auth_headers() -> dict:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("❌ Error: GITHUB_TOKEN environment variable is not set!")
        print("   Add GITHUB_TOKEN=your_token to your .env file or environment.")
        sys.exit(1)
    
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

# ---------------------------------------------------------
# API Quota & Telemetry
# ---------------------------------------------------------
def get_rate_limit(headers: dict) -> dict:
    """Fetches real-time rate limit telemetry from GitHub."""
    url = "https://api.github.com/rate_limit"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        core = data["resources"]["core"]
        reset_time = datetime.fromtimestamp(core["reset"], tz=timezone.utc).astimezone()
        minutes_left = max(0, int((core["reset"] - time.time()) / 60))
        return {
            "limit": core["limit"],
            "remaining": core["remaining"],
            "used": core["used"],
            "reset_time": reset_time.strftime("%Y-%m-%d %H:%M:%S"),
            "minutes_left": minutes_left,
        }
    return {}

def print_quota_telemetry(quota: dict):
    """Prints a styled telemetry card for API quota."""
    if not quota:
        return
    pct = (quota["remaining"] / quota["limit"]) * 100 if quota["limit"] else 0
    print("\n⚡ [API Telemetry & Quota]")
    print(f"   Quota Available: {quota['remaining']} / {quota['limit']} ({pct:.1f}%)")
    print(f"   Requests Used:   {quota['used']}")
    print(f"   Window Resets:   {quota['reset_time']} (in ~{quota['minutes_left']} min)")

# ---------------------------------------------------------
# Data Fetching & Pagination
# ---------------------------------------------------------
def fetch_users(endpoint: str, headers: dict) -> set:
    """Fetches all usernames from a paginated GitHub endpoint."""
    users = set()
    page = 1

    while True:
        url = f"https://api.github.com/user/{endpoint}?per_page=100&page={page}"
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            print(f"❌ Error fetching {endpoint} (page {page}): {response.status_code}")
            break

        data = response.json()
        if not data:
            break

        for user in data:
            users.add(user["login"])

        print(f"  Fetching '{endpoint}'... Page {page} ({len(users)} accounts found)")
        page += 1

    return users

# ---------------------------------------------------------
# Whitelist Management
# ---------------------------------------------------------
def load_whitelist(filepath: str) -> set:
    """Loads a JSON list of usernames to ignore during unfollow audits."""
    if not os.path.exists(filepath):
        return set()

    with open(filepath, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            # Store normalized usernames
            return {u.strip().lower() for u in data if isinstance(u, str)}
        except json.JSONDecodeError:
            print(f"⚠️  Warning: {filepath} is empty or invalid JSON.")
            return set()

# ---------------------------------------------------------
# History & Snapshot Tracking
# ---------------------------------------------------------
def load_last_snapshot(filepath: str) -> dict:
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_snapshot(filepath: str, followers: set, following: set):
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    payload = {
        "timestamp": datetime.now().isoformat(),
        "followers": sorted(list(followers)),
        "following": sorted(list(following)),
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

def compute_history_diff(last_snap: dict, current_followers: set, current_following: set) -> dict:
    if not last_snap or "followers" not in last_snap:
        return {}

    old_followers = set(last_snap.get("followers", []))
    old_following = set(last_snap.get("following", []))

    return {
        "gained_followers": current_followers - old_followers,
        "lost_followers": old_followers - current_followers,
        "newly_following": current_following - old_following,
        "unfollowed": old_following - current_following,
        "previous_timestamp": last_snap.get("timestamp", "Unknown"),
    }

# ---------------------------------------------------------
# Markdown Report Generation
# ---------------------------------------------------------
def generate_markdown_report(filepath: str, stats: dict, not_following_back: set, fans: set, mutuals: set, diff: dict):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# 📊 GitHub Audience & Relationship Audit Report",
        f"\n*Generated on: `{now_str}`*\n",
        "## Summary Overview",
        "| Metric | Count | Description |",
        "| :--- | :---: | :--- |",
        f"| **Followers** | `{stats['followers']}` | Accounts following you |",
        f"| **Following** | `{stats['following']}` | Accounts you follow |",
        f"| **Mutual Connections** | `{stats['mutuals']}` | Reciprocal follows |",
        f"| **Fans (Follow You Only)** | `{stats['fans']}` | Follow you, not followed back |",
        f"| **Whitelisted Accounts** | `{stats['whitelisted']}` | Excluded from audit |",
        f"| **Not Following Back** | `{stats['not_following_back']}` | You follow, they don't follow back |",
    ]

    if diff:
        prev_time = diff.get("previous_timestamp", "")[:19].replace("T", " ")
        lines.extend([
            f"\n## 📈 Changes Since Last Snapshot (`{prev_time}`)",
            f"- 🟢 **New Followers:** {len(diff['gained_followers'])} " + (f"({', '.join(sorted(diff['gained_followers']))})" if diff['gained_followers'] else "*(none)*"),
            f"- 🔴 **Lost Followers (Unfollowed you):** {len(diff['lost_followers'])} " + (f"({', '.join(sorted(diff['lost_followers']))})" if diff['lost_followers'] else "*(none)*"),
            f"- ➕ **Newly Followed by You:** {len(diff['newly_following'])} " + (f"({', '.join(sorted(diff['newly_following']))})" if diff['newly_following'] else "*(none)*"),
            f"- ➖ **Unfollowed by You:** {len(diff['unfollowed'])} " + (f"({', '.join(sorted(diff['unfollowed']))})" if diff['unfollowed'] else "*(none)*"),
        ])

    lines.append("\n## 🔍 Accounts You Follow Who Do Not Follow Back")
    if not_following_back:
        lines.append("\n*(Excluding whitelisted accounts)*\n")
        lines.append("| # | Username | Profile Link |")
        lines.append("| :-: | :--- | :--- |")
        for i, user in enumerate(sorted(not_following_back), 1):
            lines.append(f"| {i} | `@{user}` | [View Profile](https://github.com/{user}) |")
    else:
        lines.append("\n✨ *None! All followed accounts either follow you back or are on your whitelist.*")

    lines.append("\n## ⭐ Fans (Followers You Don't Follow Back)")
    if fans:
        lines.append("\n| # | Username | Profile Link |")
        lines.append("| :-: | :--- | :--- |")
        for i, user in enumerate(sorted(fans), 1):
            lines.append(f"| {i} | `@{user}` | [View Profile](https://github.com/{user}) |")
    else:
        lines.append("\n*None! You follow all your followers back.*")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\n📄 Markdown report written to: {filepath}")

# ---------------------------------------------------------
# Main CLI Entrypoint
# ---------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="GitHub Auditor: Safe, read-only relationship and follower intelligence tool."
    )
    parser.add_argument(
        "-r", "--report",
        help="Generate a comprehensive Markdown report file (default: audit_report.md)",
        nargs="?",
        const=os.path.join(BASE_DIR, "audit_report.md"),
        default=None,
    )
    parser.add_argument(
        "-q", "--quota",
        action="store_true",
        help="Check and display GitHub API rate limit quota only",
    )
    parser.add_argument(
        "-w", "--whitelist",
        default=os.path.join(BASE_DIR, "whitelist.json"),
        help="Path to whitelist.json file (default: ./whitelist.json)",
    )
    parser.add_argument(
        "--no-history",
        action="store_true",
        help="Do not save or compare against snapshot history",
    )

    args = parser.parse_args()
    headers = get_auth_headers()

    # Quota check
    quota = get_rate_limit(headers)
    if args.quota:
        print_quota_telemetry(quota)
        return

    # Data collection
    print("\n🔍 Connecting to GitHub API...")
    followers = fetch_users("followers", headers)
    following = fetch_users("following", headers)
    raw_whitelist = load_whitelist(args.whitelist)

    # Set algebra (case-insensitive for safety)
    followers_lower = {u.lower(): u for u in followers}
    following_lower = {u.lower(): u for u in following}

    mutuals = {followers_lower[k] for k in followers_lower.keys() & following_lower.keys()}
    fans = {followers_lower[k] for k in followers_lower.keys() - following_lower.keys()}
    
    # Not following back = following - followers - whitelist
    unrequited_keys = (following_lower.keys() - followers_lower.keys()) - raw_whitelist
    not_following_back = {following_lower[k] for k in unrequited_keys}

    # History Diffing
    snapshot_path = os.path.join(BASE_DIR, "snapshots", "history.json")
    diff = {}
    if not args.no_history:
        last_snap = load_last_snapshot(snapshot_path)
        diff = compute_history_diff(last_snap, followers, following)
        save_snapshot(snapshot_path, followers, following)

    # Console Output
    print("\n" + "=" * 50)
    print(" 📊 GITHUB AUDIT & RELATIONSHIP REPORT")
    print("=" * 50)
    print(f" 👥 Total Followers:        {len(followers):>4}")
    print(f" ➡️  Total Following:        {len(following):>4}")
    print(f" 🤝 Mutual Connections:     {len(mutuals):>4}")
    print(f" ⭐ Fans (Follow you only): {len(fans):>4}")
    print(f" 🛡️  Whitelisted Accounts:   {len(raw_whitelist):>4}")
    print(f" ❓ Not Following Back:     {len(not_following_back):>4}")
    print("=" * 50)

    # Print history changes if any
    if diff:
        print("\n📈 [Historical Changes Since Last Run]")
        if diff["gained_followers"]:
            print(f"  🟢 Gained (+{len(diff['gained_followers'])}): {', '.join(sorted(diff['gained_followers']))}")
        if diff["lost_followers"]:
            print(f"  🔴 Unfollowed you (-{len(diff['lost_followers'])}): {', '.join(sorted(diff['lost_followers']))}")
        if diff["newly_following"]:
            print(f"  ➕ You started following (+{len(diff['newly_following'])}): {', '.join(sorted(diff['newly_following']))}")
        if diff["unfollowed"]:
            print(f"  ➖ You stopped following (-{len(diff['unfollowed'])}): {', '.join(sorted(diff['unfollowed']))}")
        if not (diff["gained_followers"] or diff["lost_followers"] or diff["newly_following"] or diff["unfollowed"]):
            print("  ✨ No follower or following changes since the last snapshot.")

    # Print list of not following back
    if not_following_back:
        print("\n🔍 Accounts you follow who do NOT follow back (excluding whitelist):")
        for idx, user in enumerate(sorted(not_following_back), 1):
            print(f"  {idx:2d}. https://github.com/{user}")
    else:
        print("\n✨ All accounts you follow either follow you back or are on your whitelist!")

    # Telemetry footer
    print_quota_telemetry(quota)

    # Markdown Report export
    if args.report:
        stats = {
            "followers": len(followers),
            "following": len(following),
            "mutuals": len(mutuals),
            "fans": len(fans),
            "whitelisted": len(raw_whitelist),
            "not_following_back": len(not_following_back),
        }
        generate_markdown_report(args.report, stats, not_following_back, fans, mutuals, diff)

if __name__ == "__main__":
    main()
