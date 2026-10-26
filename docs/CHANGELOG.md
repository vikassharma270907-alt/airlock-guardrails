# Changelog

All notable changes to the Airlock guardrail framework are documented here.

## [0.1.1] - 2026-10-26

### Security & Guardrail Hardening
- **Rename Evasion Defense (`policy_gate.py`)**: Added `--no-renames` to `git diff` invocations. Renaming a protected file (e.g., `.gitlab-ci.yml`) or a test file is now deterministically tracked as distinct delete and add events, preventing gate evasion.
- **Fail-Closed Security Gate (`sast_gate.py`)**: Defined `REQUIRED_REPORTS = ("gl-sast-report.json",)` and added `missing_reports()` verification. If security scanning is bypassed, fails to run, or produces no report artifact, `sast_gate.py` halts the pipeline with exit code 1.
- **Agent Self-Approval Prevention (`policy_gate.py`)**: Added `agent_usernames` policy key and integrated GitLab REST API check against `resource_label_events`. If an approval label (`control-plane-approved` or `size-approved`) was added by an agent account or if `AIRLOCK_API_TOKEN` is missing, the gate fails closed by ignoring the approval label.
- **Test Suite Expansion**: Added 10 new unit tests to `tests/test_gates.py` (total 26 unit tests), testing renamed files, missing report fail-closed, Medium severity ignore vs High failure, agent-applied labels, removed labels, and out-of-order label event streams.

### Documentation & Demonstration
- **Honest Metrics Audit**: Replaced unverified quantitative assertions with conservative phrasing, linked verified baseline CI Pipeline #2989126680, and marked unexecuted stages as "not yet".
- **Demo Runbook Reordering (`docs/DEMO.md`)**: Reordered demonstration sequence (Scenario 1: Injection Blocked -> Scenario 2: Control Plane Protected -> Scenario 3: SAST Fix Re-Verification) to prevent the seeded vulnerability from turning prior MRs red. Added pre-flight scanner checks and new pipeline re-run rule.
- **Setup Guide (`docs/SETUP.md`)**: Documented `AIRLOCK_API_TOKEN` (`read_api` scope) CI variable and `agent_usernames` configuration.
- **Flow Draft Configuration**: Added `docs/flows/airlock_triage.DRAFT.yaml` clearly marked as a draft export for Duo Flow Creator.

## [0.1.0] - 2026-10-26

### Initial Release
- Core deterministic gates: `policy_gate.py`, `sast_gate.py`, `fix_budget.py`, `ledger.py`, `scorecard.py`.
- Baseline GitLab CI pipeline with SAST, Secret Detection, package wheel build, staging deployment to Generic Package Registry, smoke test, and manual production gate.
- Dual-agent prompt injection isolation architecture (`airlock_triage`).
