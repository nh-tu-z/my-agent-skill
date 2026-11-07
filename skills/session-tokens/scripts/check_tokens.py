#!/usr/bin/env python3
"""
Antigravity Session Token Analyzer (`check_tokens.py`)
Calculates Token In (`input_tokens`), Token Out (`output_tokens`), and
Token Cache (`cache_read_tokens`) for one or all Antigravity sessions,
including per-turn breakdown, per-step context window tracking, cache hit rate,
and optional standalone HTML report generation.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


UUID_RE = re.compile(
    r"\b([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\b"
)
USER_REQ_RE = re.compile(r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>", re.DOTALL)
MODEL_CHANGE_RE = re.compile(r"changed setting `Model Selection` from .*? to ([^\.\n]+)")


def get_default_brain_dir() -> Path:
    home = Path.home()
    return home / ".gemini" / "antigravity" / "brain"


def extract_user_prompt(content: str) -> str:
    if not content:
        return ""
    m = USER_REQ_RE.search(content)
    text = m.group(1).strip() if m else content.strip()
    single_line = " ".join(text.split())
    return single_line[:120] + ("..." if len(single_line) > 120 else "")


def extract_model_name(content: str) -> str | None:
    if not content:
        return None
    m = MODEL_CHANGE_RE.search(content)
    if m:
        return m.group(1).strip()
    return None


def resolve_transcript_path(target: str, brain_dir: Path) -> Path:
    p = Path(target)
    if p.exists():
        if p.is_file():
            return p
        candidate = p / ".system_generated" / "logs" / "transcript.jsonl"
        if candidate.exists():
            return candidate

    if not brain_dir.exists():
        raise FileNotFoundError(f"Brain directory not found at: {brain_dir}")

    if target.lower() in ("latest", "current", ""):
        candidates = list(brain_dir.glob("*/.system_generated/logs/transcript.jsonl"))
        if not candidates:
            raise FileNotFoundError(f"No session transcripts found in {brain_dir}")
        candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return candidates[0]

    # Exact or prefix match on conversation ID folder under brain_dir
    exact = brain_dir / target / ".system_generated" / "logs" / "transcript.jsonl"
    if exact.exists():
        return exact

    matches = [
        d / ".system_generated" / "logs" / "transcript.jsonl"
        for d in brain_dir.iterdir()
        if d.is_dir() and d.name.lower().startswith(target.lower())
    ]
    matches = [m for m in matches if m.exists()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        matches.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return matches[0]

    raise FileNotFoundError(f"Could not resolve session transcript for '{target}' in {brain_dir}")


def parse_session_transcript(
    transcript_path: Path,
    brain_dir: Path | None = None,
    include_subagents: bool = True,
    visited: set[str] | None = None,
) -> dict[str, Any]:
    if visited is None:
        visited = set()

    # Conversation ID is 3 levels above transcript.jsonl: <id>/.system_generated/logs/transcript.jsonl
    try:
        conv_id = transcript_path.parents[2].name
    except IndexError:
        conv_id = transcript_path.stem

    visited.add(conv_id)

    steps_data: list[dict[str, Any]] = []
    turns_data: list[dict[str, Any]] = []
    current_turn: dict[str, Any] | None = None

    total_in = 0
    total_out = 0
    total_cache = 0
    peak_context = 0
    current_context = 0
    started_at = None
    updated_at = None
    detected_model = None
    subagent_ids: list[str] = []
    pending_subagent_check = False

    with transcript_path.open("r", encoding="utf-8", errors="replace") as fp:
        for raw_line in fp:
            line = raw_line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            created_at = obj.get("created_at")
            if created_at:
                if started_at is None:
                    started_at = created_at
                updated_at = created_at

            step_type = obj.get("type")
            content_str = obj.get("content", "") if isinstance(obj.get("content"), str) else ""

            if step_type == "USER_INPUT":
                m_name = extract_model_name(content_str)
                if m_name:
                    detected_model = m_name
                prompt_preview = extract_user_prompt(content_str)
                current_turn = {
                    "turn_index": len(turns_data) + 1,
                    "step_index": obj.get("step_index", 0),
                    "created_at": created_at,
                    "user_prompt_preview": prompt_preview,
                    "llm_steps": 0,
                    "input_tokens": 0,
                    "cache_read_tokens": 0,
                    "output_tokens": 0,
                    "total_prompt_tokens": 0,
                    "total_tokens": 0,
                    "cache_hit_rate_pct": 0.0,
                }
                turns_data.append(current_turn)

            # Check for subagent invocations
            tool_calls = obj.get("tool_calls") or []
            tool_names: list[str] = []
            for tc in tool_calls:
                if isinstance(tc, dict):
                    tname = tc.get("name", "")
                    if tname:
                        tool_names.append(tname)
                    if tname == "invoke_subagent":
                        pending_subagent_check = True

            if pending_subagent_check and step_type == "GENERIC" and content_str:
                for match_uuid in UUID_RE.findall(content_str):
                    if match_uuid != conv_id and match_uuid not in subagent_ids:
                        subagent_ids.append(match_uuid)
                pending_subagent_check = False

            # Check if step carries token usage (typically PLANNER_RESPONSE)
            has_tokens = any(
                k in obj for k in ("input_tokens", "output_tokens", "cache_read_tokens")
            )
            if has_tokens or step_type == "PLANNER_RESPONSE":
                in_tok = int(obj.get("input_tokens") or 0)
                cache_tok = int(obj.get("cache_read_tokens") or 0)
                out_tok = int(obj.get("output_tokens") or 0)
                prompt_ctx = in_tok + cache_tok
                step_total = prompt_ctx + out_tok
                hit_rate = (cache_tok / prompt_ctx * 100.0) if prompt_ctx > 0 else 0.0

                total_in += in_tok
                total_cache += cache_tok
                total_out += out_tok
                current_context = prompt_ctx
                if prompt_ctx > peak_context:
                    peak_context = prompt_ctx

                step_record = {
                    "step_index": obj.get("step_index"),
                    "created_at": created_at,
                    "input_tokens": in_tok,
                    "cache_read_tokens": cache_tok,
                    "prompt_context_tokens": prompt_ctx,
                    "output_tokens": out_tok,
                    "step_total_tokens": step_total,
                    "cache_hit_rate_pct": round(hit_rate, 2),
                    "tools": tool_names,
                }
                steps_data.append(step_record)

                if current_turn is None:
                    current_turn = {
                        "turn_index": len(turns_data) + 1,
                        "step_index": obj.get("step_index", 0),
                        "created_at": created_at,
                        "user_prompt_preview": "(Initial / System Step)",
                        "llm_steps": 0,
                        "input_tokens": 0,
                        "cache_read_tokens": 0,
                        "output_tokens": 0,
                        "total_prompt_tokens": 0,
                        "total_tokens": 0,
                        "cache_hit_rate_pct": 0.0,
                    }
                    turns_data.append(current_turn)

                current_turn["llm_steps"] += 1
                current_turn["input_tokens"] += in_tok
                current_turn["cache_read_tokens"] += cache_tok
                current_turn["output_tokens"] += out_tok
                current_turn["total_prompt_tokens"] += prompt_ctx
                current_turn["total_tokens"] += step_total
                t_prompt = current_turn["total_prompt_tokens"]
                current_turn["cache_hit_rate_pct"] = (
                    round(current_turn["cache_read_tokens"] / t_prompt * 100.0, 2)
                    if t_prompt > 0
                    else 0.0
                )

    total_prompt = total_in + total_cache
    grand_total = total_prompt + total_out
    cache_hit_pct = round((total_cache / total_prompt * 100.0), 2) if total_prompt > 0 else 0.0
    uncached_share_pct = round(100.0 - cache_hit_pct, 2) if total_prompt > 0 else 0.0
    llm_steps = len(steps_data)

    totals = {
        "llm_steps": llm_steps,
        "user_turns": len(turns_data),
        "input_tokens": total_in,
        "cache_read_tokens": total_cache,
        "total_prompt_tokens": total_prompt,
        "output_tokens": total_out,
        "total_tokens": grand_total,
        "cache_hit_rate_pct": cache_hit_pct,
        "uncached_input_share_pct": uncached_share_pct,
        "current_context_tokens": current_context,
        "peak_context_tokens": peak_context,
        "avg_input_tokens_per_step": round(total_in / llm_steps) if llm_steps > 0 else 0,
        "avg_cache_tokens_per_step": round(total_cache / llm_steps) if llm_steps > 0 else 0,
        "avg_output_tokens_per_step": round(total_out / llm_steps) if llm_steps > 0 else 0,
    }

    # Resolve subagent transcripts if present
    subagent_reports: list[dict[str, Any]] = []
    if include_subagents and brain_dir and subagent_ids:
        for sub_id in subagent_ids:
            if sub_id in visited:
                continue
            sub_tx = brain_dir / sub_id / ".system_generated" / "logs" / "transcript.jsonl"
            if sub_tx.exists():
                sub_rep = parse_session_transcript(
                    sub_tx, brain_dir=brain_dir, include_subagents=True, visited=visited
                )
                subagent_reports.append(sub_rep)

    return {
        "conversation_id": conv_id,
        "transcript_path": str(transcript_path.resolve()),
        "model": detected_model or "Default",
        "started_at": started_at,
        "updated_at": updated_at,
        "totals": totals,
        "turns": turns_data,
        "steps": steps_data,
        "subagents": subagent_reports,
    }


def format_markdown_single(report: dict[str, Any]) -> str:
    t = report["totals"]
    lines = []
    lines.append(f"## Session Token Summary (`{report['conversation_id']}`)")
    lines.append("")
    lines.append(f"- **Transcript**: `{report['transcript_path']}`")
    lines.append(f"- **Model**: `{report['model']}`")
    lines.append(f"- **Time Range (UTC)**: `{report['started_at'] or 'N/A'}` -> `{report['updated_at'] or 'N/A'}`")
    lines.append(f"- **LLM Steps**: `{t['llm_steps']}` across `{t['user_turns']}` user turn(s)")
    lines.append("")
    lines.append("### Core Token Metrics")
    lines.append("")
    lines.append("| Metric | Field / Formula | Token Count | Share / Notes |")
    lines.append("| :--- | :--- | ---: | :--- |")
    lines.append(
        f"| **Token In (Uncached)** | `input_tokens` | **{t['input_tokens']:,}** | `{t['uncached_input_share_pct']:.1f}%` of prompt context (avg `{t['avg_input_tokens_per_step']:,}`/step) |"
    )
    lines.append(
        f"| **Token Cache (Read)** | `cache_read_tokens` | **{t['cache_read_tokens']:,}** | **{t['cache_hit_rate_pct']:.1f}% Cache Hit Rate** (avg `{t['avg_cache_tokens_per_step']:,}`/step) |"
    )
    lines.append(
        f"| **Total Prompt Context** | `In + Cache` | **{t['total_prompt_tokens']:,}** | Cumulative prompt tokens sent across `{t['llm_steps']}` steps |"
    )
    lines.append(
        f"| **Token Out (Generated)** | `output_tokens` | **{t['output_tokens']:,}** | Thinking + responses + tool calls (avg `{t['avg_output_tokens_per_step']:,}`/step) |"
    )
    lines.append(
        f"| **Grand Total Tokens** | `In + Cache + Out` | **{t['total_tokens']:,}** | Total tokens processed in session |"
    )
    lines.append(
        f"| **Current Context Window** | Latest `In + Cache` | **{t['current_context_tokens']:,}** | Active context window at latest step |"
    )
    lines.append(
        f"| **Peak Context Window** | Max `In + Cache` | **{t['peak_context_tokens']:,}** | Maximum context window reached in session |"
    )
    lines.append("")

    if report.get("turns"):
        lines.append("### Per-Turn Breakdown")
        lines.append("")
        lines.append("| Turn | Prompt Preview | LLM Steps | Token In | Token Cache | Token Out | Cache Hit % |")
        lines.append("| :--- | :--- | ---: | ---: | ---: | ---: | ---: |")
        for tr in report["turns"]:
            preview = (tr.get("user_prompt_preview") or "").replace("|", "\\|")
            if len(preview) > 65:
                preview = preview[:62] + "..."
            lines.append(
                f"| #{tr['turn_index']} | {preview} | {tr['llm_steps']} | {tr['input_tokens']:,} | {tr['cache_read_tokens']:,} | {tr['output_tokens']:,} | {tr['cache_hit_rate_pct']:.1f}% |"
            )
        lines.append("")

    if report.get("steps"):
        lines.append("### Step-by-Step LLM Token Log")
        lines.append("")
        lines.append("| Step | Timestamp (UTC) | Token In | Token Cache | Prompt Context (`In+Cache`) | Token Out | Cache Hit % | Tools Called |")
        lines.append("| :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- |")
        for st in report["steps"]:
            tools_str = ", ".join(f"`{tl}`" for tl in st.get("tools", [])) if st.get("tools") else "—"
            ts = (st.get("created_at") or "").replace("T", " ").replace("Z", "")
            lines.append(
                f"| #{st['step_index']} | `{ts}` | {st['input_tokens']:,} | {st['cache_read_tokens']:,} | **{st['prompt_context_tokens']:,}** | {st['output_tokens']:,} | {st['cache_hit_rate_pct']:.1f}% | {tools_str} |"
            )
        lines.append("")

    if report.get("subagents"):
        lines.append("### Subagent Sessions Invoked")
        lines.append("")
        lines.append("| Subagent ID | LLM Steps | Token In | Token Cache | Token Out | Cache Hit % |")
        lines.append("| :--- | ---: | ---: | ---: | ---: | ---: |")
        for sub in report["subagents"]:
            st_tot = sub["totals"]
            lines.append(
                f"| `{sub['conversation_id']}` | {st_tot['llm_steps']} | {st_tot['input_tokens']:,} | {st_tot['cache_read_tokens']:,} | {st_tot['output_tokens']:,} | {st_tot['cache_hit_rate_pct']:.1f}% |"
            )
        lines.append("")

    return "\n".join(lines)


def format_markdown_multi(reports: list[dict[str, Any]]) -> str:
    lines = []
    lines.append("## Multi-Session Token Usage Summary")
    lines.append("")
    lines.append("| Session ID | Updated (UTC) | Steps | Token In (Uncached) | Token Cache (Read) | Token Out | Peak Window | Cache Hit % |")
    lines.append("| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |")

    grand_in = grand_cache = grand_out = grand_steps = 0
    for r in reports:
        t = r["totals"]
        grand_in += t["input_tokens"]
        grand_cache += t["cache_read_tokens"]
        grand_out += t["output_tokens"]
        grand_steps += t["llm_steps"]
        ts = (r.get("updated_at") or "N/A").replace("T", " ").replace("Z", "")
        lines.append(
            f"| `{r['conversation_id']}` | `{ts}` | {t['llm_steps']} | {t['input_tokens']:,} | {t['cache_read_tokens']:,} | {t['output_tokens']:,} | {t['peak_context_tokens']:,} | {t['cache_hit_rate_pct']:.1f}% |"
        )

    grand_prompt = grand_in + grand_cache
    grand_hit = (grand_cache / grand_prompt * 100.0) if grand_prompt > 0 else 0.0
    lines.append(
        f"| **TOTAL ({len(reports)} sessions)** | — | **{grand_steps}** | **{grand_in:,}** | **{grand_cache:,}** | **{grand_out:,}** | — | **{grand_hit:.1f}%** |"
    )
    lines.append("")
    return "\n".join(lines)


def generate_html_report(payload: dict[str, Any], output_html_path: Path, template_path: Path) -> None:
    if not template_path.exists():
        raise FileNotFoundError(f"HTML template not found at {template_path}")

    template_str = template_path.read_text(encoding="utf-8")
    sessions = payload.get("sessions", [payload])
    if len(sessions) == 1:
        title = f"Session {sessions[0]['conversation_id'][:8]}"
    else:
        title = f"{len(sessions)} Sessions Overview"

    safe_json = json.dumps(payload, indent=2, ensure_ascii=False).replace("</", "<\\/")
    rendered = template_str.replace("{{REPORT_TITLE}}", title).replace("{{TOKEN_DATA_JSON}}", safe_json)

    output_html_path.parent.mkdir(parents=True, exist_ok=True)
    output_html_path.write_text(rendered, encoding="utf-8")


def main() -> int:
    # Ensure UTF-8 stdout on Windows
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Check Token In, Token Out, and Token Cache for Antigravity session(s)."
    )
    parser.add_argument(
        "--session",
        "-s",
        default="latest",
        help="Conversation ID (full or prefix), path to transcript.jsonl, or 'latest' (default).",
    )
    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Analyze all sessions found in the Antigravity brain directory.",
    )
    parser.add_argument(
        "--brain-dir",
        default=None,
        help="Override path to Antigravity brain directory (defaults to ~/.gemini/antigravity/brain).",
    )
    parser.add_argument(
        "--no-subagents",
        action="store_true",
        help="Disable automatic subagent transcript resolution.",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["markdown", "json"],
        default="markdown",
        help="Console output format: 'markdown' (default) or 'json'.",
    )
    parser.add_argument(
        "--json-out",
        default=None,
        help="Optional file path to save the structured JSON report.",
    )
    parser.add_argument(
        "--html-out",
        default=None,
        help="Optional file path to generate a standalone interactive HTML dashboard.",
    )

    args = parser.parse_args()
    brain_dir = Path(args.brain_dir) if args.brain_dir else get_default_brain_dir()
    script_dir = Path(__file__).resolve().parent
    default_template = script_dir.parent / "resources" / "token_report_template.html"

    try:
        if args.all:
            if not brain_dir.exists():
                raise FileNotFoundError(f"Brain directory not found: {brain_dir}")
            tx_files = list(brain_dir.glob("*/.system_generated/logs/transcript.jsonl"))
            tx_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            reports = [
                parse_session_transcript(
                    tx, brain_dir=brain_dir, include_subagents=not args.no_subagents
                )
                for tx in tx_files
            ]
            payload: dict[str, Any] = {"sessions": reports}
            if args.format == "json":
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            else:
                print(format_markdown_multi(reports))
        else:
            tx_path = resolve_transcript_path(args.session, brain_dir)
            report = parse_session_transcript(
                tx_path, brain_dir=brain_dir, include_subagents=not args.no_subagents
            )
            payload = report
            if args.format == "json":
                print(json.dumps(report, indent=2, ensure_ascii=False))
            else:
                print(format_markdown_single(report))

        if args.json_out:
            json_out_path = Path(args.json_out)
            json_out_path.parent.mkdir(parents=True, exist_ok=True)
            json_out_path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
            )

        if args.html_out:
            html_out_path = Path(args.html_out)
            generate_html_report(payload, html_out_path, default_template)

        return 0
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

