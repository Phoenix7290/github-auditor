# 🛡️ GitHub Relationship Auditor & Telemetry CLI

A safe, fast, and completely **read-only** CLI tool to inspect GitHub audience metrics, mutual follows, unrequited accounts, history deltas (new followers / unfollowers), and API rate limit quotas without risking account bans or triggering abuse detection mechanisms.

---

## ✨ Features

- **Safe & Read-Only:** Complies strictly with GitHub's Terms of Service and Abuse Policies. Zero automated write actions (`PUT`/`DELETE`).
- **Telemetry & Quota Monitoring:** Tracks GitHub API rate limits, requests used, and exact reset countdowns.
- **Snapshot & Delta Tracking:** Automatically compares results with previous runs to highlight new followers gained or lost.
- **Whitelist Protection:** Prevent respected developers or reference accounts from appearing as unfollow targets.
- **Markdown Export:** Generate formatted audit reports with markdown tables and direct profile links.
- **Case-Insensitive Set Operations:** Accurate set math for mutuals, fans, and unfollowers.

---

## 🚀 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd github-auditor
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure Authentication:**
   Create a `.env` file in the root directory:
   ```env
   GITHUB_TOKEN=your_personal_access_token_here
   ```
   *(Requires only `read:user` scope).*

---

## 💻 Usage

### Run standard audit:
```bash
./run.sh
# or
python main.py
```

### Export Markdown report:
```bash
./run.sh --report
```

### Check API Quota & Telemetry only:
```bash
./run.sh --quota
```

### Custom Whitelist:
Edit `whitelist.json` to add developers you admire:
```json
[
  "torvalds",
  "antirez"
]
```

---

## 🛠️ Global Execution

To run `github-auditor` from any directory in your terminal, link the runner script into `~/.local/bin`:

```bash
ln -s ~/code/github-auditor/run.sh ~/.local/bin/github-auditor
```
Now you can simply type:
```bash
github-auditor --report
```
