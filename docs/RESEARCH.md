# Research Foundation for Airlock Guardrails

Airlock translates empirical findings from software engineering and AI security research into deterministic CI/CD guardrails.

> Note: Citations were not independently verified in full; see each paper.

---

### 1. Control Plane vs. Data Plane Separation
- **Source**: Barnes, Ghaleb, Hassan, *"From Assistance to Agency: Rethinking Autonomy and Control in CI/CD Pipelines"* (arXiv 2605.07062).
- **Core Finding**: No documented agentic CI/CD deployment delegates control-plane authority (modifying pipelines, secret access, production release) without human verification. External governance carries the primary safety burden.
- **Airlock Implementation**: `tools/policy_gate.py` prevents agents from modifying `.gitlab-ci.yml`, `.gitlab/*`, `tools/*`, `policy/*`, `deploy/*`, `CODEOWNERS`, or deleting tests.

---

### 2. Untrusted Issue Content & Workflow Injection
- **Sources**: 
  - GitLab Security Documentation: *"Security threats in agentic systems"* (The Lethal Trifecta: untrusted input, privileged tools, external effects).
  - *GitInject* (arXiv 2606.09935) & *Agentic Workflow Injection* (arXiv 2605.07135).
- **Core Finding**: Issues, PR comments, and commit messages are untrusted entry points where indirect prompt injection can manipulate autonomous agents.
- **Airlock Implementation**: `airlock_triage` dual-agent architecture separates read-only analysis from write-only commenting. The reader agent lacks write tools and emits structured JSON; the writer agent never receives raw issue text.

---

### 3. Guardrails vs. Guidance: Negative Constraints Beat Positive Directives
- **Sources**:
  - *"Guardrails Beat Guidance: A Large-Scale Study of Rules, Skills, and Persistent Configuration for Coding Agents"* (arXiv 2604.11088).
  - *Progent* (arXiv 2504.11703) & *AgentGuard* (arXiv 2609.16287).
- **Core Finding**: Negative constraints (prohibitions such as *"do not modify CI"* or *"do not touch unrelated files"*) are uniquely beneficial and drive task success. In contrast, positive directives (broad behavioral advice) often degrade performance. Furthermore, AgentGuard (arXiv 2609.16287) documents that agents frequently modify unrelated files, rewrite tests improperly, or bypass validation checks unless constrained by execution guardrails.
- **Airlock Implementation**: Issue templates enforce strict negative prohibitions ("Do not modify CI", "Do not delete tests"), backed by deterministic CI exit codes in container jobs.

---

### 4. Patch Validation: Re-Scanning vs. Test Passing
- **Source**: Yu et al., *"Patch Validation in Automated Vulnerability Repair"* (arXiv 2603.06858).
- **Core Finding**: In evaluations across automated vulnerability repair (AVR) systems using PVBench (209 cases across 20 projects), over 40% of patches that passed traditional functional tests failed under stricter $\text{PoC}^+$ exploit tests, demonstrating that passing existing unit tests does not confirm that a vulnerability was properly remediated.
- **Airlock Implementation**: `tools/sast_gate.py` scans security reports (`gl-*report.json`) and blocks the MR if High or Critical findings remain, verifying remediation by re-scanning.

---

### 5. Bounded Repair Loops & Deterministic Rules First
- **Sources**:
  - *"Agentic RL for Real-World Code Repair"* (arXiv 2510.22075).
- **Core Finding**: Establishing bounded repair evaluations (capping repair attempts at 3 iterations) prevents runaway loops and maintains build stability before escalating to human maintainers.
- **Airlock Implementation**: The Fix CI/CD Pipeline flow applies a 3-attempt ceiling before triggering human escalation.

---

### 6. Empirical Characteristics of Agent Pull Requests
- **Source**: Ehsani et al., *"Where Do AI Coding Agents Fail? An Empirical Study of Failed Agentic Pull Requests in GitHub"* (arXiv 2601.15195).
- **Core Finding**: In an empirical analysis of 33,596 agent-generated PRs, rejected PRs were significantly larger, modified more files, and experienced higher rates of CI failure; duplicates and abandonment were common.
- **Airlock Implementation**: The policy gate enforces a size budget (maximum 10 files and 300 changed lines), requiring human authorization (`size-approved`) for larger MRs.

---

### 7. Historical Regression Memory & Deterministic Test Reproduction
- **Source**: Time Machine CI architectural pattern (GitLab Transcend Hackathon Showcase #43742192).
- **Core Finding**: Autonomous coding agents lack persistent organizational memory of past production outages and authorization flaws, frequently re-introducing vulnerabilities (e.g., Broken Object Level Authorization / BOLA) that the codebase previously survived. Relying on LLMs to synthesize arbitrary test code creates prompt injection risks and flaky execution.
- **Airlock Implementation**: `tools/regression_gate.py` couples incident memory (`policy/incidents.json`) with cryptographic assessment binding (`head_sha`, `context_sha256`) and reviewed immutable test templates. Only reproduced failure assertions fail the pipeline; clean fixes pass the exact same test, achieving deterministic regression protection.

