---
name: Agent Task
about: Task description for Duo Developer agent with strict safety prohibitions
title: "feat: "
labels: ["agent-task"]
---

## Task Description
<!-- Describe the task, goal, and requirements clearly -->

## Guardrail Prohibitions for AI Agents
When assigned to this issue, you MUST comply with these strict boundaries:
1. **Scope Limit**: Create exactly ONE Merge Request per issue. Keep total changes under 150 lines and under 10 files.
2. **Control-Plane Prohibition**: DO NOT modify `.gitlab-ci.yml`, `.gitlab/*`, `policy/*`, `deploy/*`, `tools/*`, or `CODEOWNERS`. Any MR modifying these files will be automatically blocked by the policy gate.
3. **Preserve & Add Tests**: DO NOT delete or weaken existing tests in `tests/`. Always add or update unit tests to verify your fix or feature.
4. **Duplicate Prevention**: Before creating a new Merge Request, check for any open MR linked to this issue.
5. **No Secrets or Insecure Executions**: DO NOT introduce hardcoded credentials or dynamic code execution (`eval`, `exec`, `subprocess.run(..., shell=True)`).
