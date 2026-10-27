# Airlock Demo Video: Production Script, Shot List & Assets

**Project:** Airlock — Deterministic CI Guardrails and Supervised Governance for AI Coding Agents  
**Tagline:** *Autonomous agents that can ship, but cannot break the rules.*  
**Target Duration:** 2:42 (162 seconds) | **Word Count:** 358 words (~133 words per minute)  
**Voice Engine:** ElevenLabs (Recommended voice: *Adam* or *Rachel*, Stability: 55%, Clarity/Similarity: 75%, Style: 0.00)

---

## 1. Shot-by-Shot Table

| Timestamp | Screen Footage & URL / Action | Voiceover Narration (Word-for-Word) | On-Screen Caption / Callout | Transition |
|---|---|---|---|---|
| **0:00 – 0:18** | **Page:** `https://airlock-guardrails.vercel.app`<br>**Action:** Start at top hero. Scroll smoothly to the Control Plane vs Data Plane architecture diagram. | "AI coding agents are accelerating software delivery on GitLab. But prompt constraints alone fail under prompt injection, and agents under pressure will edit CI pipelines or delete failing tests to force builds green. Welcome to Airlock: deterministic CI guardrails for supervised agent autonomy." | **AIRLOCK**<br>`Supervised Autonomy for GitLab Duo` | Cut |
| **0:18 – 0:52** | **Page:** `https://airlock-guardrails.vercel.app/#playground`<br>**Action:** Tab 1 (Dual-Agent Triage). Click *'Prompt Injection Attack'*. Highlight the hidden HTML comment overriding instructions. Click *'Run Dual-Agent Triage'*. Zoom into Reader JSON and Sanitized Comment badge (`INJECTION BLOCKED`). | "Scenario one: untrusted issue triage. An attacker embeds an instruction override inside an HTML comment attempting to delete CI tests. Airlock uses a dual-agent split. The read-only reader parses the input strictly as data, recognizes the exploit, and outputs rigid JSON. The write-only writer receives only this sanitized JSON, posting a security warning without ever exposing active tools to prompt injection." | **GATE 1: DUAL-AGENT TRIAGE**<br>`Reader/Writer Context Separation` | Smooth Scroll / Zoom |
| **0:52 – 1:32** | **Page:** `MR !4` & `Pipeline #2992681172`<br>**Action:** Open MR !4 diff showing `eval(user_input)`. Open pipeline job `sast-gate` log showing exit code 1 and blocked High finding. Show safe fix to `ast.literal_eval`. | "Scenario two: verifying security fixes twice. An issue asks to fix an insecure eval. In Merge Request four, unit tests pass, but our SAST gate inspects the scanner report and blocks the pipeline because a High-severity finding persists. Automated fixes must be validated by security re-scanning, not by tests alone. When remediated safely, the re-scan confirms zero findings and the gate passes." | **GATE 2: VERIFY-TWICE SAST**<br>`Eliminating the 'Illusion of Fix'` | Cut |
| **1:32 – 2:05** | **Page:** `MR !2` (Pipeline #2989716535) & `MR !3` (Pipeline #2989719601)<br>**Action:** Open job log for `policy-gate` in MR !2 showing `.gitlab-ci.yml` tampering halted with `POLICY VIOLATION`. Switch to MR !3 job log showing test deletion detected via `--no-renames`. | "Scenario three: control-plane protection. In Merge Request two, an agent attempts to edit dot-gitlab-ci-dot-yml to speed up builds. The policy gate halts the pipeline immediately with exit code one. In Merge Request three, an agent renames a test file to bypass deletion checks. Using git diff with no-renames, Airlock catches the evasion and blocks merge without verified human approval." | **GATE 3: POLICY GATE**<br>`Control Plane & Test Evasion Defense` | Cut |
| **2:05 – 2:42** | **Page:** `Pipeline #2993995494`<br>**Action:** Show default branch pipeline: `build-wheel`, `unit-tests` (53 passed), `publish-staging`, `smoke-test`, `scorecard`. Hover over manual `publish-production` button. Scroll to End Card on website. | "On main, Pipeline 2993995494 builds the wheel, passes 53 unit tests, publishes to the GitLab Generic Package Registry, executes an end-to-end smoke test, and compiles an auditable governance scorecard. Production deployment stays locked waiting for a human maintainer click. As a limitation, these gates run inside CI, so complete isolation requires human CODEOWNERS and protected branches. Airlock: safe agents, verified fixes, humans in control." | **PIPELINE #2993995494**<br>`All 9 DevSecOps Stages Covered`<br>`Supervised Production Release` | Fade to End Card |

---

## 2. Full Spoken Narration Script

**Word Count:** 358 words  
**Estimated Spoken Duration:** 2 minutes 40 seconds (at 134 WPM)  
*Clean text ready to paste directly into ElevenLabs:*

> AI coding agents are accelerating software delivery on GitLab. But prompt constraints alone fail under prompt injection, and agents under pressure will edit CI pipelines or delete failing tests to force builds green. Welcome to Airlock: deterministic CI guardrails for supervised agent autonomy.
> 
> Scenario one: untrusted issue triage. An attacker embeds an instruction override inside an HTML comment attempting to delete CI tests. Airlock uses a dual-agent split. The read-only reader parses the input strictly as data, recognizes the exploit, and outputs rigid JSON. The write-only writer receives only this sanitized JSON, posting a security warning without ever exposing active tools to prompt injection.
> 
> Scenario two: verifying security fixes twice. An issue asks to fix an insecure eval. In Merge Request four, unit tests pass, but our SAST gate inspects the scanner report and blocks the pipeline because a High-severity finding persists. Automated fixes must be validated by security re-scanning, not by tests alone. When remediated safely, the re-scan confirms zero findings and the gate passes.
> 
> Scenario three: control-plane protection. In Merge Request two, an agent attempts to edit dot-gitlab-ci-dot-yml to speed up builds. The policy gate halts the pipeline immediately with exit code one. In Merge Request three, an agent renames a test file to bypass deletion checks. Using git diff with no-renames, Airlock catches the evasion and blocks merge without verified human approval.
> 
> On main, Pipeline 2993995494 builds the wheel, passes 53 unit tests, publishes to the GitLab Generic Package Registry, executes an end-to-end smoke test, and compiles an auditable governance scorecard. Production deployment stays locked waiting for a human maintainer click. As a limitation, these gates run inside CI, so complete isolation requires human CODEOWNERS and protected branches. Airlock: safe agents, verified fixes, humans in control.

---

## 3. Subtitle File (SRT)

See `docs/airlock_demo.srt`.

---

## 4. Metadata

- **Published YouTube Video**: https://www.youtube.com/watch?v=jFqkEme0DG8
- **YouTube Title**: Airlock: Deterministic CI Guardrails for AI Coding Agents (GitLab Transcend Hackathon)
- **Tagline**: Autonomous agents that can ship, but cannot break the rules.
- **Track**: Path A (Start Fresh) | Autonomy: Supervised
- **Showcase**: https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43727879/showcase
- **Mirror**: https://github.com/vikassharma270907-alt/airlock-guardrails
- **Live Demo**: https://airlock-guardrails.vercel.app
