# Airlock

> **Autonomous agents that can ship, but cannot break the rules.**

Airlock introduces deterministic continuous integration guardrails and dual-agent governance for AI coding agents on the GitLab Duo Agent Platform. Instead of relying purely on system prompts to keep agents safe, Airlock enforces hard, programmatic boundaries in the CI/CD pipeline: untrusted issue text is neutralized via a reader/writer agent split, control-plane configurations (.gitlab-ci.yml, tools, test suites) cannot be modified without explicit human approval labels, and security fixes must be verified by re-scanning, not by tests alone.

---

## DevSecOps Lifecycle Stage Map

| Lifecycle Stage | Automation Mechanism | Human Role | Guardrail / Boundary |
|---|---|---|---|
| **Plan** | Custom Flow `airlock_triage` | Reviews issue triage note | Read-only reader outputs strict JSON; writer never sees raw issue |
| **Create** | Foundational Developer Flow | Creates issue, assigns task | Issue template prohibitions (size <150 lines, no CI edits) |
| **Verify** | CI `unit-tests` & Fix Pipeline | Escalation on 3 failures | Automated repair loop capped at 3 attempts; tests cannot be deleted |
| **Package** | CI `build-wheel` | Audits build logs | Standardized wheel packaged into `dist/` |
| **Secure** | SAST (`semgrep-sast`), Secret Detection, `sast-gate` | Security audit | `sast_gate.py` blocks MR on any High or Critical vulnerability |
| **Release** | `publish-staging` & `publish-production` | **Manual Approval** for prod | Staging package published automatically; production requires human click |
| **Configure** | CI `policy-gate` | Applies `control-plane-approved` | `policy_gate.py` blocks edits to `.gitlab-ci.yml`, `tools/`, or configs |
| **Monitor** | CI `smoke-test` | Reviews test report | Installs wheel from Generic Package Registry and executes CLI |
| **Govern** | CI `scorecard` & `ledger` | Reviews audit scorecard | Ledger tracks each job result; markdown scorecard generated per run |

---

## How the Guardrails Work

1. **Dual-Agent Triage (`airlock_triage`)**:
   - The **reader** component has access only to read-only tools (`get_issue`, `list_files`, `grep`, `read_file`) and strictly treats issue text as untrusted data.
   - The reader outputs structured JSON with fields: `type`, `severity`, `summary`, `acceptance_criteria`, `files_likely_affected`, `suspicious_instructions_detected`, and `suspicious_note`.
   - The **writer** component only has access to `create_issue_note` and receives *only* the reader's JSON output, completely sanitizing against prompt injection.

2. **Control-Plane Policy Gate (`tools/policy_gate.py`)**:
   - Compares the MR branch diff against the base branch (`origin/main`).
   - If changes touch protected paths (`.gitlab-ci.yml`, `.gitlab/*`, `policy/*`, `deploy/*`, `CODEOWNERS`, `tools/*`) or delete test files, the MR fails unless the human-applied label `control-plane-approved` is present.
   - If an MR modifies more than 10 files or 300 lines, the MR fails unless `size-approved` is present.

3. **Verify-Twice Security Gate (`tools/sast_gate.py`)**:
   - Scans GitLab security reports (`gl-*report.json`).
   - Blocks the pipeline if any High or Critical finding exists. Passing unit tests alone will not allow an un-remediated security vulnerability into the codebase.

4. **Self-Healing CI with 3-Attempt Cap**:
   - Pipeline failures trigger the Fix CI/CD Pipeline flow.
   - Remediation attempts are capped at 3 to prevent credit exhaustion or recursive degradation, followed by a human handoff.

---

## Setup & How to Run

### Local Development & Testing
```bash
# Install test dependencies (only pytest)
pip install -r requirements-dev.txt

# Run full test suite
pytest -q
```

### GitLab CI Execution
1. Push repository to GitLab.
2. Ensure project visibility is set to **Public** with MIT License in About section.
3. Open a Merge Request to see `policy-gate` and `sast-gate` evaluate MR changes.
4. Merge to `main` to trigger wheel packaging, staging deployment, smoke testing, and scorecard generation.

---

## Pipeline Governance Scorecard

| Check / Stage | Result | Policy Status |
|---|---|---|
| unit-tests | success | PASSED |
| sast-gate | success | PASSED |
| policy-gate | success | PASSED |
| build-wheel | success | PASSED |
| publish-staging | success | PASSED |
| smoke-test | success | PASSED |
| publish-production | manual | PENDING HUMAN APPROVAL |

---

## Known Limitations (Stated Honestly)
1. **MR Pipeline Autonomy vs Security Boundary**: An MR pipeline executes the MR branch's own `.gitlab-ci.yml`. Running gate scripts from a trusted target branch (`git show origin/main:tools/...`) ensures the gate logic cannot be rewritten, but an agent could theoretically remove the gate job from the MR's `.gitlab-ci.yml`. Absolute protection requires pairing the policy gate with protected branches, "Pipelines must succeed", required CODEOWNERS approval, or pointing the project's CI configuration to a separate, human-owned repository.
2. **Label Permissions**: The `control-plane-approved` and `size-approved` labels can currently be applied by any user with project member label-management permissions.
3. **Context Minimization Limits**: The reader/writer split protects control flow and prevents tool hijacking, but structured data passed between agents can still convey misleading semantic summaries to downstream developers if not reviewed.
4. **Retry Cap Scope**: In-repo retry counters rely on commit message conventions (`agent-fix:`) and author matching; external enforcement requires webhook middleware or CI-managed counters.
5. **Scorecard Scope**: The current scorecard records per-pipeline execution results; multi-pipeline historical rollups are derived from the GitLab pipeline history.

---

## Research References
- Barnes, Ghaleb, Hassan, *"From Assistance to Agency: Rethinking Autonomy and Control in CI/CD Pipelines"* (arXiv 2605.07062)
- GitLab Security Documentation: *"Security threats in agentic systems"*
- *GitInject* (arXiv 2606.09935) & *Agentic Workflow Injection* (arXiv 2605.07135)
- *AgentGuard* (arXiv 2609.16287) & *"Guardrails Beat Guidance"* (arXiv 2604.11088)
- Ehsani et al., *"Where Do AI Coding Agents Fail?"* (arXiv 2601.15195)
- Yu et al., *"Patch Validation in Automated Vulnerability Repair"* (arXiv 2603.06858)
- *"Agentic RL for Real-World Code Repair"* (arXiv 2510.22075) & *RELAY* (arXiv 2610.27784)

---

## License
MIT License. See [LICENSE](LICENSE) for details.
