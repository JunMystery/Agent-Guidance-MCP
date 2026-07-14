# Project-Specific Agent Guidance

This file contains standards, conventions, and rules specific to this project. AI Agents MUST follow the 8 core standards for every single action, in parallel with the rules herein.

> **💡 Instructions:**
> - **Independent operation:** Simply create/edit this file, and the AI Agent will automatically detect it.
> - **Fully customizable:** You can add new fields (e.g., "Reviewer", "Effective Date") if necessary. Just keep it in a bulleted list format.
> - Use this file to define: project architecture, preferred libraries, naming conventions, error handling flows, etc.

---

## 🏗️ Template

*(Copy the block below to add a new standard. You can add/remove any fields according to your needs)*

### [Standard Name / Category]
- **Rule (Required):** [Clear description of the rule the AI must follow]
- **Reason (Required):** [Brief explanation of why this rule exists]
- **Do / Good Example (Optional):** [Example of correct code/behavior]
- **Don't / Bad Example (Optional):** [Example of incorrect code/behavior]
- **Scope (Optional):** [e.g.: Only applies to Frontend code, or only .ts files]
- **Reference (Optional):** [Link or path to documentation, design file, issue...]
- **Exceptions (Optional):** [Cases where this rule does not apply]
- **Terminal Command (Optional):** [Commands to run, e.g.: npm run lint]
- **How to Test (Optional):** [How to know this rule has been followed?]

---

## 📋 Project Standards List (Customize below)

> [!IMPORTANT]
> **GLOBAL ENFORCEMENT**: All 8 rules herein MUST be evaluated and followed for every single coding action, repository lookup, refactoring, or planning phase without exception.

<!-- ADD YOUR STANDARDS BELOW -->

### MCP Context Grounding & Planning
- **Rule (Required):** At the start of any task, the AI Agent MUST invoke `task_pipeline(task, project_path, ...)` to retrieve task-context-aware standards, directory structure, and UI guidance in a single efficient call. Alternatively, the agent can call `project_context(operation="tree")` to view the directory tree, and `guidance(operation="recommend", query)` to identify applicable standards. Before inspecting or modifying any file, the agent MUST use `project_context(operation="read", relative_path)` to retrieve optimized file contents instead of manual file reads. Avoid manual file search commands when `project_context(operation="search", query)` can be utilized. Most importantly, even if the user prompt does not mention specific files/code directly, or references a function name without its location, AI Agents MUST NOT guess anything; they must find the exact related files/functions/symbols first, and formulate a plan before proposing changes.
- **Reason (Required):** Enforces a token-efficient workflow, prevents blind guessing, guarantees implementation alignment with coding standards, and ensures correct context loading without redundant filesystem traversals.
- **Do / Good Example:** Start a session by calling `task_pipeline(task="add search endpoints to book API", project_path=".")` to load the codebase state, then inspect target files using `project_context(operation="read", relative_path="src/api.py")` and formulate an implementation plan before writing any code.
- **Don't / Bad Example:** Directly editing files, guessing function/file locations unverified, or running custom commands without checking workspace context, or doing generic text-based reads when optimized `project_context(operation="read")` is available.
- **How to Test (Optional):** Ensure that the agent's first steps call either `task_pipeline` or the respective `project_context` and `guidance` tools to verify locations and propose a plan before performing any codebase edits.

### File Size and Focus Limits (Rule 6)
- **Rule (Required):** Keep code files focused and split them when they exceed 300 lines of code (LOC). Avoid monolithic files and dumping grounds.
- **Reason (Required):** Focused files simplify unit testing, reduce cognitive overhead during code reviews, minimize git merge conflicts, and prevent exceeding AI token/context budgets.
- **Do / Good Example:** Splitting a large module into helper scripts, separate controllers, or separate components where each module does one logical thing.
- **Don't / Bad Example:** Appending unrelated helper methods, model definitions, and API routes to a single monolithic controller file that grows to 500+ lines.
- **How to Test (Optional):** Verify the line count of modified or created files using system utilities or checks to ensure they do not exceed 300 LOC.
