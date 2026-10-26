---
name: Agent Task
about: Task description for Duo Developer agent with strict safety prohibitions
title: "feat: "
labels: ["agent-task"]
---

## Task Description
<!-- Describe the task, goal, and requirements clearly -->

## Guardrail Prohibitions for AI Agents
When assigned to this issue, you MUST comply with these strict negative prohibitions:
1. **Do not create multiple Merge Requests**: Create at most ONE Merge Request for this issue.
2. **Do not exceed size budgets**: Do not touch more than 10 files and do not change more than 300 total lines.
3. **Do not modify control-plane files**: Do not modify `.gitlab-ci.yml`, `.gitlab/*`, `policy/*`, `deploy/*`, `tools/*`, or `CODEOWNERS`. Any MR touching these files is blocked by the CI policy gate.
4. **Do not delete or weaken tests**: Do not delete or disable any test files in `tests/` or files matching `test_*.py`. Always add or update unit tests to verify changes.
5. **Do not introduce insecure execution or hardcoded secrets**: Do not use dynamic code execution (`eval`, `exec`, `subprocess.run(..., shell=True)`) or hardcode credentials/tokens.
6. **Do not create duplicate MRs**: Do not open a new Merge Request if one already exists for this issue.
