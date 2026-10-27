# Hackathon Submission Draft & Video Script

## Devpost Submission Text

### Project Title
Airlock: Deterministic CI Guardrails and Supervised Governance for AI Coding Agents

### Tagline
Autonomous agents that can ship, but cannot break the rules.

### The Problem
AI coding agents are gaining rapid access to software repositories and continuous delivery pipelines. However, empirical research reveals that prompt-based constraints consistently fail under prompt injection, agents frequently attempt to modify CI configurations or delete failing tests to pass pipelines, and passing unit tests alone does not validate that a vulnerability was properly remediated. Today, teams are forced between two extremes: slow manual reviews for every agent step, or risky unconstrained autonomy.

### The Solution: Airlock
Airlock introduces an explicit architectural boundary between the agent **data plane** (code changes, issue triage, implementation) and the human-controlled **control plane** (CI definitions, security gates, approval rules, production deployments). Instead of relying on prompt instructions alone, Airlock enforces deterministic gates inside the GitLab CI pipeline:
1. **Injection-Safe Triage**: Uses a dual-agent pattern. A read-only `reader` agent processes untrusted issue text and outputs strictly bounded JSON. A write-only `writer` agent formats and posts the triage note without ever seeing raw user text, stopping prompt injection before any active agent can be compromised.
2. **Deterministic Control-Plane Policy Gate**: Any Merge Request attempting to modify `.gitlab-ci.yml`, `.gitlab/*`, `tools/*`, `policy/*`, or delete test suites is blocked automatically unless a human explicitly applies the `control-plane-approved` label.
3. **Verify-Twice Security Gate**: Security fixes are evaluated directly against re-scanned SAST and secret detection reports (`gl-*report.json`), failing the pipeline if High or Critical findings persist, regardless of whether unit tests pass.
4. **Self-Healing CI with Bounded Retry**: Pipeline failures trigger the Fix CI/CD Pipeline flow, bounded by a 3-attempt ceiling to prevent credit exhaustion and runaway repair loops, followed by automated human escalation.
5. **State & Readiness Integrity Guardrail**: Enforces 100% verified checklist criteria before tasks transition to "Ready" or terminal milestones, immutably locks completed state against automated agent tampering, and enforces version-bound optimistic concurrency tokens.
6. **GitLab CI Pipeline Intelligence**: Employs `AST_ENABLE_MR_PIPELINES: 'true'` so security templates evaluate MR pipelines reliably, combined with redundant branch pipeline suppression (`$CI_COMMIT_BRANCH && $CI_OPEN_MERGE_REQUESTS: when: never`) to save compute.
7. **Continuous Governance Scorecard**: Every pipeline run records execution status into a per-job ledger artifact, compiling an auditable governance scorecard for compliance and visibility.

### DevSecOps Lifecycle Stages Touched
- **Plan**: Custom flow `airlock_triage` on issue mention trigger parses requirements and flags prompt injection.
- **Create**: Foundational Developer flow turns issues into bounded MRs under 10 files and 300 changed lines.
- **Verify**: Unit tests validate code logic; Fix Pipeline flow automatically remediates failures.
- **Package**: `build-wheel` packages Python distribution artifacts into `dist/`.
- **Secure**: GitLab SAST (`semgrep-sast`) and Secret Detection templates scan MRs, enforced by `sast_gate.py`.
- **Release**: Automated deployment to GitLab Generic Package Registry (staging) and manual gate for production.
- **Configure**: Policy gate blocks unauthorized modification of pipeline and environment configurations.
- **Monitor**: Automated post-deployment smoke test fetches, installs, and validates package execution.
- **Govern**: Deterministic policy enforcement, human approval labels, and automated scorecard artifact generation.

### GitLab Duo Agent Platform Features Used
- **Custom Flows**: Flow Registry v1 dual-agent flow (`airlock_triage`) separating read-only analysis from write-only actions, plus Time Machine regression flow (`airlock_historical_regression`).
- **Foundational Flows**: GitLab Duo Developer Flow, Fix CI/CD Pipeline Flow, and Code Review Flow.
- **Event-Driven Triggers**: Mention triggers on issue comments (`@airlock_triage`) and failure triggers on pipeline events.

### Visible Pipeline History & Live Deployment
- Official YouTube Demo Video (2:42): https://www.youtube.com/watch?v=jFqkEme0DG8
- Public Repository: https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43727879/showcase
- GitHub Public Mirror: https://github.com/vikassharma270907-alt/airlock-guardrails
- Live Interactive Web Playground: https://airlock-guardrails.vercel.app
- Staging Package Registry: https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43727879/showcase/-/packages
- CI/CD Pipeline History: https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43727879/showcase/-/pipelines
- Baseline Clean Main Pipeline: https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43727879/showcase/-/pipelines/2993995494 (and #2989694028)
- Baseline Clean MR Pipeline (MR !1): https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43727879/showcase/-/pipelines/2989715383
- Control-Plane Protection MR Pipeline (MR !2, Blocked): https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43727879/showcase/-/pipelines/2989716535
- Rename-Evasion Defense MR Pipeline (MR !3, Blocked): https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43727879/showcase/-/pipelines/2989719601
- SAST Vulnerability Defense MR Pipeline (MR !4, Blocked): https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43727879/showcase/-/pipelines/2992681172

### Real Results & Metrics
- Total Unit Tests: 53 automated unit tests passing in 0.10s across 5 test suites (`test_gates.py`, `test_regression_gate.py`, `test_state_guard.py`, `test_textkit.py`, `test_triage.py`).
- Total Scenarios Demonstrated: 5 (Prompt injection neutralized, control plane tampering blocked, rename evasion blocked, historical regression detected, state readiness tamper-proofing enforced).
- Control Plane Violations Blocked: 2 (MR !2 unauthorized CI edit; MR !3 test deletion evasion).
- Live Interactive Interfaces: 2 (Terminal CLI console via `interactive.py` / `python main.py --cli` and Live Web Playground at `https://airlock-guardrails.vercel.app/#playground`).
- Human Approvals Required: 2 (`control-plane-approved` label and manual production release gate).

### Known Limitations (Stated Honestly)
1. **Guardrail vs Security Boundary**: The policy gate is a programmatic guardrail, not an absolute security boundary. The gate runs inside the MR pipeline using the branch's code. Comprehensive protection requires pairing this gate with protected branches, "Pipelines must succeed", and human-owned CODEOWNERS.
2. **Context Minimization Limits**: The reader/writer split protects control flow and prevents tool hijacking, but data passed between the reader and writer agents can still be manipulated semantically to convey misleading summaries if not reviewed by a human maintainer.
3. **Retry Cap Scope**: The retry cap is by instruction unless code enforces it. While `tools/fix_budget.py` provides deterministic in-repo enforcement by counting commits matching `agent-fix:` or configured agent author patterns, full platform-level enforcement requires webhook middleware or CI-managed counters.
4. **Label Permissions & Token Scope**: Verification of human label provenance relies on `AIRLOCK_API_TOKEN` (`read_api` scope) calling GitLab REST APIs. If the token is missing or invalid, the gate fails closed by ignoring approval labels. The label-provenance check has not yet been exercised on a live merge request.
5. **Scorecard Scope**: The current scorecard records per-pipeline execution results; multi-pipeline historical rollups are derived from the GitLab pipeline history.

---

## 3-Minute Demo Video Script

| Timestamp | Visual Screen Action | Voiceover Narration |
|---|---|---|
| **0:00 - 0:20** | Title card and GitLab architecture diagram showing data plane vs control plane. | "AI coding agents are accelerating development, but giving them direct access to CI/CD without hard boundaries creates severe security risks. Welcome to Airlock: agents that can ship, but cannot break the rules." |
| **0:20 - 0:55** | Open issue with hidden HTML prompt injection. Trigger `@airlock_triage`. Show reader JSON output and resulting issue comment with security warning. | "Scenario 1: An attacker files an issue with a hidden prompt injection inside an HTML comment attempting to delete CI tests. Our custom triage flow uses a dual-agent design: a read-only reader parses the input as data, detects the injection, and outputs strict JSON. The write-only writer receives only the sanitized JSON, posting a security alert without ever exposing active tools to the exploit." |
| **0:55 - 1:35** | Open security issue on legacy runner. Developer agent creates MR. Pipeline runs: SAST gate fails red on eval(). Agent applies safe fix, pipeline re-runs, SAST gate turns green. | "Scenario 2: An issue asks to fix an insecure eval. The Developer flow opens an MR. The SAST gate runs and blocks the MR because High findings persist. The agent updates the patch to safe parsing. In the re-scan, SAST confirms zero High or Critical findings, and the gate turns green. We verify the security fix by re-scanning, not by tests alone." |
| **1:35 - 2:10** | Issue asks to speed up CI by removing tests. Agent creates MR editing `.gitlab-ci.yml`. Pipeline runs `policy-gate` and immediately fails with POLICY VIOLATION. | "Scenario 3: An agent is prompted to speed up CI and removes the test job. When the pipeline runs, the deterministic policy gate detects changes to protected control-plane files without human approval. The MR is stopped dead in its tracks. Only an authorized human can apply the 'control-plane-approved' label." |
| **2:10 - 2:40** | Merge approved MR into `main`. Show staging wheel build, upload to generic package registry, smoke test passing, and scorecard artifact. Point to manual `publish-production` button. | "On main, the pipeline packages the wheel, publishes it to the GitLab Generic Package Registry, runs an end-to-end smoke test, and compiles a governance scorecard. Production deployment remains paused waiting for human authorization: true Supervised autonomy." |
| **2:40 - 2:55** | Display 9-stage lifecycle coverage table, research references, and conclusion. | "Airlock covers all nine DevSecOps stages with deterministic guardrails grounded in published research. Safe agents, verified fixes, and humans in control." |
