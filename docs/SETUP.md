# Airlock Setup & Configuration Guide

This guide details the setup across GitLab Duo Agent Platform, CI/CD, and repository governance.

---

## Section 1: Project & Repository Setup
1. **Repository Visibility**:
   - Navigate to **Settings > General > Visibility, project features, permissions**.
   - Set **Project visibility** to **Public**.
   - Verify that **Repository** and **CI/CD** are enabled and set to *Everyone with Access*.
2. **Branch Protection**:
   - Navigate to **Settings > Repository > Protected branches**.
   - Default branch: `main`.
   - Allowed to push: *No one* (forces all changes through Merge Requests).
   - Allowed to merge: *Maintainers* (or human developer).
3. **Package Registry**:
   - Verify Package Registry is enabled in **Settings > General > Visibility**.

---

## Section 2: Labels Configuration
Create the following scoped/standard labels under **Manage > Labels**:
1. `control-plane-approved` (Color: `#108548` / Green): Human authorization required to modify control plane files (`.gitlab-ci.yml`, `.gitlab/*`, `tools/*`, `CODEOWNERS`) or delete tests.
2. `size-approved` (Color: `#1F75CB` / Blue): Human authorization required to merge MRs exceeding 10 files or 300 changed lines.
3. `agent-task` (Color: `#6666c4` / Purple): Attached to issues designated for autonomous agent execution.

---

## Section 2b: Label Provenance Token & Agent Account Configuration
To prevent AI agents or automated bots from self-approving changes by attaching `control-plane-approved`:
1. **Create Access Token**:
   - Go to **Settings > Access Tokens** (Project or User Settings).
   - Create a token with **Role: Developer/Reporter** and **Scope: `read_api`**.
2. **Add CI/CD Variable**:
   - Go to **Settings > CI/CD > Variables**.
   - Key: `AIRLOCK_API_TOKEN`
   - Value: `<your-token>`
   - Flags: **Masked** (and expanded if needed).
3. **Configure Agent Accounts in Policy**:
   - In `policy/policy.json`, populate `agent_usernames` with known agent or bot usernames (e.g. `["gitlab-duo", "duo-developer"]`).
   - When set, `tools/policy_gate.py` calls the GitLab REST API `resource_label_events` and verifies that approval labels were applied by human maintainers, failing closed if the token is missing or if the label was applied by an agent account.

---

## Section 3: Duo Agent Platform Flows Setup
Navigate to **AI > Flows** in the left project sidebar:
1. **Custom Flow: `airlock_triage`**:
   - Import or paste the Flow Registry v1 YAML from `docs/flow_prompts.md`.
   - Component 1: `reader` (AgentComponent, read-only tools: `get_issue`, `list_files`, `grep`, `read_file`; no write tools, no command execution).
   - Component 2: `writer` (OneOffComponent, tool: `create_issue_note`).
   - Router: `reader` -> `writer` -> `end`.
2. **Foundational Flow: Developer Flow**:
   - Enable the foundational Developer / Software Development Flow for issue-to-MR generation.
   - Enforce prohibitions defined in `.gitlab/issue_templates/agent_task.md`.
3. **Foundational Flow: Fix CI/CD Pipeline Flow**:
   - Enable Fix Pipeline flow to diagnose and remediate broken CI/CD pipelines within a 3-attempt limit.
4. **Foundational Flow: Code Review Flow (Pre-Human Reviewer)**:
   - Enable the Code Review flow on Merge Requests to perform automated first-pass checks before human maintainer review.


---

## Section 4: Event Triggers Setup
Navigate to **AI > Triggers** (requires Maintainer/Owner role):
1. **Triage Mention Trigger**:
   - Event: `issue_comment`
   - Filter/Condition: Mentions `@airlock_triage`
   - Target Flow: `airlock_triage`
2. **Fix Pipeline Trigger**:
   - Event: `pipeline_event` (Pipeline Failure)
   - Target Flow: `Fix CI/CD Pipeline Flow` (or manual trigger from failed pipeline widget).
