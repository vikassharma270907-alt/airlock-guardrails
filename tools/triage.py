"""Airlock Dual-Agent Issue Triage and Prompt Injection Defense Engine.

Implements the read-only Reader agent parser and write-only Writer agent formatter
that isolates untrusted user inputs from privileged coding tools.

Owner: Vikas Sharma <beyondnothing01@gmail.com>
"""

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


@dataclass
class TriageAssessment:
    type: str  # 'feature' | 'bug' | 'security' | 'chore'
    severity: str  # 'critical' | 'high' | 'medium' | 'low'
    summary: str
    acceptance_criteria: List[str]
    files_likely_affected: List[str]
    suspicious_instructions_detected: bool
    suspicious_note: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


SUSPICIOUS_PATTERNS = [
    (r"<!--[\s\S]*?(?:system\s+override|ignore\s+previous|exfiltrate|token|curl|wget|api_key|rm\s+-rf|chmod)[\s\S]*?-->",
     "Hidden HTML comment attempting prompt override or sensitive execution"),
    (r"(?:ignore\s+(?:all\s+)?previous\s+(?:instructions|guidelines|rules))",
     "Prompt injection attempting instruction override"),
    (r"(?:exfiltrate|leak|send|upload|dump|print|post)[\s\S]*?(?:token|secret|key|ci_job_token|credentials|password)",
     "Attempted credential or CI secret exfiltration"),
    (r"(?:remove|delete|bypass|skip)[\s\S]*?(?:unit[\s_-]?tests?|sast|security|pipeline|\.gitlab-ci\.yml)",
     "Attempted control-plane CI or test deletion"),
]


class DualAgentTriageEngine:
    """Simulates the dual-agent Reader and Writer architecture of airlock_triage."""

    def reader_agent(self, raw_issue_text: str) -> TriageAssessment:
        """Reader Agent: strictly read-only tools, parses text as untrusted data."""
        text = raw_issue_text.strip()
        suspicious_detected = False
        suspicious_notes = []

        # 1. Prompt Injection & Malicious Instruction Detection
        for pattern, note in SUSPICIOUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                suspicious_detected = True
                suspicious_notes.append(note)

        # 2. Extract Title / Summary (first markdown heading or line)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        first_line = lines[0] if lines else "Untitled Issue"
        summary = re.sub(r"^[#\s*_-]+", "", first_line)

        # 3. Classify issue type and severity
        lower_text = text.lower()
        if any(w in lower_text for w in ("vulnerability", "cwe-", "cve-", "exploit", "security")):
            issue_type = "security"
            severity = "high"
        elif any(w in lower_text for w in ("bug", "fix", "error", "crash", "fails", "broken")):
            issue_type = "bug"
            severity = "medium"
        elif any(w in lower_text for w in ("feat", "add", "feature", "new", "implement", "support")):
            issue_type = "feature"
            severity = "medium"
        else:
            issue_type = "chore"
            severity = "low"

        # 4. Extract likely affected files (look for paths or code mentions)
        file_matches = re.findall(r"[a-zA-Z0-9_./\\-]+\.[a-zA-Z0-9]+", text)
        files = list(dict.fromkeys(
            f for f in file_matches
            if not f.startswith("http") and ("/" in f or "." in f)
        ))
        if not files:
            files = ["airlock_demo/textkit.py"]

        # 5. Extract acceptance criteria
        criteria = []
        for line in lines:
            if line.startswith(("- [ ]", "- ", "* ", "1.", "2.")):
                clean_item = re.sub(r"^[-*0-9.\s\[\]]+", "", line).strip()
                if clean_item and len(clean_item) > 5 and not clean_item.startswith("<"):
                    criteria.append(clean_item)
        if not criteria:
            criteria = [f"Implement requested changes for '{summary}' and verify with unit tests."]

        return TriageAssessment(
            type=issue_type,
            severity=severity,
            summary=summary,
            acceptance_criteria=criteria[:5],
            files_likely_affected=files[:5],
            suspicious_instructions_detected=suspicious_detected,
            suspicious_note="; ".join(suspicious_notes) if suspicious_notes else None,
        )

    def writer_agent(self, assessment: TriageAssessment) -> str:
        """Writer Agent: receives ONLY the sanitized JSON from the reader agent."""
        output_lines = [
            "### Airlock Triage Summary",
            f"- **Type**: `{assessment.type}` | **Severity**: `{assessment.severity}`",
            f"- **Summary**: {assessment.summary}",
            "- **Likely Files Affected**: " + (", ".join(f"`{f}`" for f in assessment.files_likely_affected) if assessment.files_likely_affected else "None identified"),
            "- **Acceptance Criteria**:"
        ]
        for c in assessment.acceptance_criteria:
            output_lines.append(f"  - [ ] {c}")

        if assessment.suspicious_instructions_detected:
            output_lines.append("")
            output_lines.append("> ⚠️ **Security Warning**: Suspicious instructions detected in issue payload:")
            output_lines.append(f"> *{assessment.suspicious_note}*")
            output_lines.append("> Active coding tools have been protected. Maintainer review required.")

        return "\n".join(output_lines)

    def process(self, raw_issue_text: str) -> Dict[str, Any]:
        """Execute full dual-agent pipeline."""
        reader_output = self.reader_agent(raw_issue_text)
        writer_output = self.writer_agent(reader_output)
        return {
            "reader_json": reader_output.to_dict(),
            "writer_note": writer_output,
            "suspicious_detected": reader_output.suspicious_instructions_detected,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Airlock Dual-Agent Issue Triage CLI")
    parser.add_argument("file", nargs="?", help="Path to markdown issue file to triage")
    parser.add_argument("--text", type=str, help="Raw issue text to triage")
    parser.add_argument("--json", action="store_true", help="Output pure JSON")
    args = parser.parse_args()

    content = ""
    if args.text:
        content = args.text
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading file '{args.file}': {e}", file=sys.stderr)
            return 1
    else:
        # Read from stdin if interactive or piped
        if not sys.stdin.isatty():
            content = sys.stdin.read()
        else:
            print("Enter issue description (Ctrl+Z or Ctrl+D on empty line to finish):")
            content = sys.stdin.read()

    engine = DualAgentTriageEngine()
    result = engine.process(content)

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print("=" * 60)
    print("  [1] READER AGENT STRUCTURED JSON OUTPUT")
    print("=" * 60)
    print(json.dumps(result["reader_json"], indent=2))
    print("\n" + "=" * 60)
    print("  [2] WRITER AGENT SANITIZED COMMENT")
    print("=" * 60)
    print(result["writer_note"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
