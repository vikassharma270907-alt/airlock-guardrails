# Research Foundation for Airlock Guardrails

Airlock translates empirical findings from recent software engineering and AI security research into deterministic CI/CD guardrails.

---

### 1. Control Plane vs. Data Plane Separation
- **Source**: Barnes, Ghaleb, Hassan, *"From Assistance to Agency: Rethinking Autonomy and Control in CI/CD Pipelines"* (arXiv 2605.07062).
- **Core Finding**: No documented agentic CI/CD deployment delegates control-plane authority (modifying pipelines, secret access, production release) without human verification. The safety burden falls on external governance rather than agent self-restraint.
- **Airlock Implementation**: `policy_gate.py` prevents agents from touching `.gitlab-ci.yml`, `.gitlab/*`, `tools/*`, `deploy/*`, `CODEOWNERS`, or deleting tests.

---

### 2. Untrusted Issue Content & Workflow Injection
- **Sources**: 
  - GitLab Security Documentation: *"Security threats in agentic systems"* (Lethal Trifecta: untrusted input, privileged tools, external effects).
  - *GitInject* (arXiv 2606.09935) & *Agentic Workflow Injection* (arXiv 2605.07135).
- **Core Finding**: Issues, PR comments, and commit messages are untrusted entry points where indirect prompt injection can hijack autonomous agents.
- **Airlock Implementation**: `airlock_triage` dual-agent architecture separates read-only analysis from write-only commenting. The reader agent lacks write tools and emits structured JSON; the writer agent never receives raw issue text.

---

### 3. Deterministic Guardrails vs. Prompt Guidance
- **Sources**:
  - *"Guardrails Beat Guidance"* (arXiv 2604.11088).
  - *Progent* (arXiv 2504.11703) & *AgentGuard* (arXiv 2609.16287).
- **Core Finding**: Negative prompt instructions ("do not modify CI") suffer from semantic drift and jailbreaks. Hard programmatic gates in the runtime or CI pipeline provide guaranteed policy enforcement.
- **Airlock Implementation**: Hard exit codes in Python CI scripts executed in isolated container jobs.

---

### 4. Patch Validation: Re-Scanning vs. Test Passing
- **Sources**:
  - Yu et al., *"Patch Validation in Automated Vulnerability Repair"* (arXiv 2603.06858).
  - *PatchBench* (arXiv 2609.04075).
- **Core Finding**: Over 40% of automated patches that pass test suites fail under stricter exploit validation or leave underlying vulnerabilities intact.
- **Airlock Implementation**: `sast_gate.py` requires SAST scans (`gl-*report.json`) to return zero High or Critical findings before allowing MR merges.

---

### 5. Bounded Retries & Toil Reduction
- **Sources**:
  - *"Agentic RL for Real-World Code Repair"* (arXiv 2510.22075).
  - *RELAY* (arXiv 2610.27784).
- **Core Finding**: Unbounded fix loops result in recursive degradation and resource exhaustion. Cap repair loops at 3 iterations and escalate to human review.
- **Airlock Implementation**: Fix Pipeline execution policy capped at three iterations with human escalation.
