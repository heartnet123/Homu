# AGENTS.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them instead of choosing silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop, name the confusion, and ask.

## 2. Simplicity First

**Write the minimum code that solves the problem. Nothing speculative.**

- Do not add features beyond what was requested.
- Do not introduce abstractions for single-use code.
- Do not add flexibility or configurability unless requested.
- Do not add error handling for impossible scenarios.
- If a solution is overly long for the problem, simplify it.

Ask: "Would a senior engineer consider this overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Change only what is necessary. Clean up only what your change affects.**

When editing existing code:
- Do not improve adjacent code, comments, or formatting unless required.
- Do not refactor code that is not part of the task.
- Match the existing code style, even if you would prefer a different style.
- If you notice unrelated dead code, mention it, but do not remove it unless asked.

When your changes create orphans:
- Remove imports, variables, or functions made unused by your change.
- Do not remove pre-existing unused code unless asked.

The test: every changed line should trace directly to the request.

## 4. Goal-Driven Execution

**Define success criteria. Verify each step.**

Turn tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

```text
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]