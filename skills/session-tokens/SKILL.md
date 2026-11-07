---
name: session-tokens
description: >-
  Checks and analyzes token usage—Token In (input_tokens), Token Out (output_tokens),
  and Token Cache (cache_read_tokens)—for the current Antigravity session, a specific
  conversation ID, or across all sessions. Computes cumulative totals, cache hit rate (%),
  current and peak context window sizes, per-turn breakdowns, subagent token usage, and
  optional interactive HTML reports. Use this skill whenever the user invokes `/session-tokens`
  or asks to check token in, token out, token cache, context window usage, or token statistics
  for a session.
---

# Session Token Usage Analyzer (`/session-tokens`)

When the user asks to check **Token In**, **Token Out**, **Token Cache**, cache efficiency, or context window size for the current session (or any other session), follow this deterministic workflow.

---

## Workflow Steps

### Step 1: Identify the Target Session
1. **Current Active Session (Default)**:
   - Use the current `<conversation-id>` from your `<user_information>` block (or pass `--session latest`).
2. **Specific Session ID or Path**:
   - If the user provides a conversation ID (full UUID or prefix) or a path to a `transcript.jsonl` file, pass `--session "<id_or_path>"`.
3. **All Sessions Overview**:
   - If the user asks to compare or sum token usage across all sessions on the machine, pass `--all`.

---

### Step 2: Run the Token Analyzer Script
Execute [check_tokens.py](./scripts/check_tokens.py) from the workspace root (or via its full path if invoked as a global skill):

```powershell
# Check the current session and generate both Markdown summary and an HTML dashboard
python skills/session-tokens/scripts/check_tokens.py --session "<conversation-id>" --html-out "./reports/token_usage_<short_id>.html" --json-out "./reports/token_usage_<short_id>.json"
```

*Tip: If running from outside this repository when installed globally, use `~/.gemini/config/skills/session-tokens/scripts/check_tokens.py`.*

**Available CLI Flags**:
- `--session, -s <id|latest|path>`: Target conversation ID (supports prefix matching), `latest` (default), or direct path to `transcript.jsonl`.
- `--all, -a`: Aggregate and rank all sessions in `<appDataDir>/brain/`.
- `--no-subagents`: Skip automatic subagent token resolution.
- `--format, -f <markdown|json>`: Output format to stdout (`markdown` default).
- `--html-out <path>`: Generate a standalone dark/light mode interactive HTML report using [token_report_template.html](./resources/token_report_template.html).
- `--json-out <path>`: Export structured JSON metrics to disk.

---

### Step 3: Present the Results Clearly
Present the results to the user in a concise, easy-to-scan response:
1. **Core Summary Table**:
   - **Token In (`input_tokens`)**: Uncached input tokens processed across all steps.
   - **Token Cache (`cache_read_tokens`)**: Cached context tokens read from the prompt cache, alongside the **Cache Hit Rate (%)**.
   - **Total Prompt Context (`In + Cache`)**: Cumulative prompt context sent across all LLM steps.
   - **Token Out (`output_tokens`)**: Generated tokens (thinking, responses, and tool calls).
   - **Current / Peak Context Window**: The prompt context size (`input_tokens + cache_read_tokens`) at the latest step vs. the maximum step in the session.
2. **Per-Turn / Per-Step Highlights**:
   - Show the per-turn or per-step breakdown table output by `check_tokens.py` (or highlight the most token-intensive steps and subagents if any were invoked).
3. **Clickable Report Links**:
   - If `--html-out` or `--json-out` was generated, include clickable file links (`[token_usage_report.html](file:///...)`).
   - For deeper metric definitions, refer to [token_metrics_guide.md](./references/token_metrics_guide.md).

