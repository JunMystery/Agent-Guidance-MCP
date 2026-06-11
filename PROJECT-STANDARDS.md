# 🛠️ Project-Specific AI Agent Standards

This file contains standards, conventions, and rules specific to this project. AI Agents MUST adhere to the rules herein, in parallel with the core standards (like `GEMINI.md`, `CLAUDE.md`).

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

*(You can check the `PROJECT-STANDARDS-EXAMPLE.md` file in the same directory for available template examples and copy/paste them here to enforce them as hard rules for your project)*

<!-- ADD YOUR STANDARDS BELOW -->

### MCP Skill Auto-Discovery
- **Rule (Required):** Before starting any implementation, design, refactoring, or debugging task, the AI Agent MUST automatically invoke the `recommend_context(task)` tool from the `ai-agent-standards` MCP server. You must use the returned resources, principles, and skills to ground your work.
- **Reason (Required):** To ensure all coding activities comply with the 6 Core Principles and local project standards without needing explicit manual user prompts.
- **Do / Good Example:** Executing `recommend_context("implement rate limiting for Auth API")` at the beginning of the chat session.
- **Don't / Bad Example:** Coding immediately without consulting the MCP server's standards and context.
- **How to Test (Optional):** Ask the agent to list the standards/skills it loaded for the current task.

