# Project-Specific Agent Guidance

This file contains standards, conventions, and rules specific to this project. AI Agents MUST follow the 6 core standards for every single action, in parallel with the rules herein.

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

<!-- ADD YOUR STANDARDS BELOW -->

### MCP Context Grounding
- **Rule (Required):** At the start of any task, the AI Agent MUST invoke `task_pipeline(task, project_path, ...)` to retrieve task-context-aware standards, directory structure, and UI guidance in a single efficient call. Alternatively, the agent can call `project_context(operation="tree")` to view the directory tree, and `guidance(operation="recommend", query)` to identify applicable standards. Before inspecting or modifying any file, the agent MUST use `project_context(operation="read", relative_path)` to retrieve optimized file contents instead of manual file reads. Avoid manual file search commands when `project_context(operation="search", query)` can be utilized.
- **Reason (Required):** Enforces a token-efficient workflow, guarantees implementation alignment with coding standards, and ensures correct context loading without redundant filesystem traversals.
- **Do / Good Example:** Start a session by calling `task_pipeline(task="add search endpoints to book API", project_path=".")` to load the codebase state, then inspect target files using `project_context(operation="read", relative_path="src/api.py")`.
- **Don't / Bad Example:** Directly editing files or running custom commands without checking workspace context, or doing generic text-based reads when optimized `project_context(operation="read")` is available.
- **How to Test (Optional):** Ensure that the agent's first steps call either `task_pipeline` or the respective `project_context` and `guidance` tools before performing any codebase edits.
