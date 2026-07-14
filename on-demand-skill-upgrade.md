Here’s a detailed, step-by-step implementation plan that an AI agent (or a developer) can follow to introduce **on‑demand skill injection** into your existing MCP server. The plan assumes you already have an MCP server with 200+ tools and want to drastically reduce token usage.

---

## Objective

Transform a static MCP server that exposes all tools at once into a dynamic one that:

- Initially exposes only a meta‑tool `search_skills`.
- Uses semantic search to find the most relevant skills for the user’s prompt.
- Injects only those skills into the LLM’s context for the actual execution.

**Token saving:** From ~20k tokens (200 tools) down to ~200 tokens for the initial call + ~1k tokens for the retrieved tools.

---

## Implementation Plan

### Phase 1 – Build the Skill Embedding Index

**Goal:** For every existing tool, create a searchable text description and a vector embedding.

#### 1.1 Collect Tool Descriptions

For each tool in your MCP server, extract:

- `name`
- `description`
- `inputSchema` (parameter names, types, descriptions)

Combine them into a single text document.  
Example document for a `send_email` tool:

```
Tool: send_email
Description: Send an email to one or more recipients.
Parameters:
- to (string, required): recipient email addresses, comma separated
- subject (string): email subject
- body (string): email body content
```

Store these documents in a list `tool_docs`.

#### 1.2 Choose an Embedding Model

Pick a lightweight, multilingual embedding model (since the question suggests Vietnamese prompts).  
Good choices:

- `intfloat/multilingual-e5-small` (multilingual, balanced)
- `BAAI/bge-small-en-v1.5` or `BAAI/bge-base-vi` for Vietnamese

You can also use an API like OpenAI’s `text-embedding-3-small` if you prefer remote.

#### 1.3 Compute and Store Embeddings

Use a local in‑memory vector store (simplest) or a persistent one like ChromaDB or FAISS.

**Example with in‑memory FAISS + sentence-transformers:**

```python
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

model = SentenceTransformer('BAAI/bge-base-vi')  # or your chosen model
tool_docs = [...]  # list of document strings
tool_names = [...]  # parallel list of tool names
tool_schemas = [...] # parallel list of full tool definitions (as dict)

embeddings = model.encode(tool_docs, normalize_embeddings=True)
dimension = embeddings.shape[1]
index = faiss.IndexFlatIP(dimension)  # inner product for cosine similarity
index.add(embeddings)

# Keep a mapping from FAISS index to tool info
id_to_tool = {i: {"name": tool_names[i], "schema": tool_schemas[i]} 
              for i in range(len(tool_names))}
```

**Tip:** Rebuild this index every time the server starts. If you add/remove tools dynamically, you can rebuild the index inside a `list_changed` hook (if your MCP library supports it) or periodically.

---

### Phase 2 – Create the `search_skills` Meta‑Tool

**Goal:** Expose a new tool that accepts a query string and returns the top‑k matching tool definitions.

#### 2.1 Define the Tool Schema

Add this tool definition to your MCP server’s tool list:

```json
{
  "name": "search_skills",
  "description": "Search for relevant skills based on a description of the task. Returns the full definitions of the most suitable skills to use.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "A natural language description of what needs to be done, e.g. 'send a thank-you email to the customer' or 'query sales data for last month'."
      }
    },
    "required": ["query"]
  }
}
```

#### 2.2 Implement the Tool Handler

In your MCP server code, implement the handler for `search_skills`:

```python
async def handle_search_skills(query: str) -> str:
    # 1. Embed the query
    query_emb = model.encode([query], normalize_embeddings=True)
    # 2. Search FAISS for top-k (k=5 recommended)
    k = 5
    scores, indices = index.search(query_emb, k)
    # 3. Retrieve corresponding tool schemas
    results = []
    for idx in indices[0]:
        if idx < 0:  # FAISS may return -1 if fewer than k results
            continue
        tool_info = id_to_tool[idx]
        results.append(tool_info["schema"])
    # 4. Return as JSON string (MCP tool call returns text)
    return json.dumps({"skills": results})
```

**Access control (optional):** If some tools are restricted by user, filter `results` based on the user’s permissions before returning.

#### 2.3 Register the Tool

In your MCP server initialization (e.g., using FastMCP):

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("My Dynamic Skills Server")

@mcp.tool()
async def search_skills(query: str) -> str:
    return await handle_search_skills(query)

# Keep all other tool registrations unchanged
@mcp.tool()
async def send_email(...): ...

@mcp.tool()
async def database_query(...): ...
# ... 200+ other tools
```

---

### Phase 3 – Modify `tools/list` to Be Minimal

**Goal:** When an AI agent first connects, it should only see `search_skills`, not all 200 tools.

If you’re using FastMCP, override the default `list_tools` behaviour. FastMCP by default returns all registered tools. To return only `search_skills`, you can create a custom server that filters the tool list.

**Example using `fastmcp` custom tool list:**

```python
from mcp.server.fastmcp import FastMCP
from mcp.types import Tool

class DynamicMCP(FastMCP):
    async def list_tools(self) -> list[Tool]:
        # Always return only the meta-tool
        return [
            Tool(
                name="search_skills",
                description="Search for relevant skills...",
                inputSchema={...}  # same as defined above
            )
        ]

mcp = DynamicMCP("Dynamic Server")
# ... register all tools normally
```

Make sure that when `tools/call` is invoked with any of the 200 tools, the server still executes them correctly. The handler functions are still registered internally; only the `list_tools` result is trimmed.

If you use another MCP library or a custom server, apply the same principle: intercept the `tools/list` request and return only the `search_skills` tool definition.

---

### Phase 4 – Update the Client / AI Agent Integration

**Goal:** The agent (e.g., a LangChain agent, or a custom loop) must use a two‑step process: first call `search_skills`, then call the actual skill.

#### 4.1 Initial Agent Setup

When the agent connects to the MCP server, it fetches the tool list via `tools/list` – it will now get only `search_skills`.

The agent should be configured with this single tool and a system prompt instructing it to **always search for skills first** before answering. Example system message:

> You have access to a tool `search_skills` that finds the right skills for any task.  
> Whenever the user asks you to perform an action, call `search_skills` with a short description of the task.  
> After you receive the list of available skills, use the most appropriate one to complete the task.

#### 4.2 Two‑Step Execution Loop

A simple loop (pseudo‑code) using the OpenAI API directly:

```python
import openai, json

client = openai.OpenAI()
mcp_client = MCPClient()  # your MCP client

messages = [
    {"role": "system", "content": "You are a helpful assistant. Always use search_skills first."},
    {"role": "user", "content": user_prompt}
]

# Step 1: First LLM call with only search_skills
tools_basic = [search_skills_openai_format]  # Only search_skills
response1 = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    tools=tools_basic,
    tool_choice="auto"
)
msg1 = response1.choices[0].message

# Check if LLM wants to call search_skills
if msg1.tool_calls:
    # We expect exactly one call to search_skills
    tool_call = msg1.tool_calls[0]
    if tool_call.function.name == "search_skills":
        # Extract query
        args = json.loads(tool_call.function.arguments)
        query = args["query"]
        
        # Call MCP search_skills
        result_json = mcp_client.call_tool("search_skills", {"query": query})
        skills = json.loads(result_json)["skills"]  # list of tool definitions
        
        # Convert MCP tool schemas into OpenAI function definitions
        new_openai_tools = [convert_to_openai_tool(s) for s in skills]
        # Keep search_skills too, in case agent needs to search again
        new_openai_tools.append(search_skills_openai_format)
        
        # Append messages to conversation
        messages.append(msg1)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": f"Found skills: {', '.join(s['name'] for s in skills)}"
        })
        
        # Step 2: Second LLM call with dynamically injected tools
        response2 = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=new_openai_tools,
            tool_choice="auto"
        )
        # Now process response2 – it may call a real skill, or ask for more info
        # Continue the loop if it makes another tool call
```

**Helper to convert MCP tool schema to OpenAI format:**

```python
def convert_to_openai_tool(mcp_tool: dict) -> dict:
    return {
        "type": "function",
        "function": {
            "name": mcp_tool["name"],
            "description": mcp_tool["description"],
            "parameters": mcp_tool["inputSchema"]
        }
    }
```

#### 4.3 Handling Subsequent Tool Calls

If `response2` contains a tool call to one of the injected skills, execute it via `mcp_client.call_tool(...)` and continue the conversation until the LLM returns a final text answer.

This two‑step loop is easy to implement inside any agent framework (LangChain, CrewAI, etc.) by overriding the tool selection step.

---

### Phase 5 – Testing, Fallbacks, and Optimizations

#### 5.1 Testing

- Test with a variety of prompts and verify that `search_skills` returns the correct tools.
- Check token consumption: initial call should be minimal; second call contains only 5–10 tools.
- Ensure that the agent never sees all 200 tools in any call.

#### 5.2 Fallback for Poor Matches

If `search_skills` returns skills with low similarity scores, you can either:

- Return a default set of the most common tools.
- Return an error message that makes the LLM ask the user for clarification.

**Implementation:** In `handle_search_skills`, check the highest score; if it’s below a threshold (e.g., 0.5 for cosine similarity), return an empty list and let the agent handle it gracefully.

#### 5.3 Caching

- Cache query embeddings and results for repeated or similar requests (use an LRU cache).
- Pre‑warm the embedding model to reduce latency.

#### 5.4 Index Updates

If your tool list changes at runtime, you can rebuild the FAISS index automatically. In `FastMCP`, you can listen for tool registration changes (if available) or rebuild periodically. A simpler approach: restart the server after modifications.

---

## Summary of Changes to Your Existing MCP Server

1. **No changes** to your 200+ tool handler functions – they remain exactly as they are.
2. **Add** an embedding index (Phase 1) and a `search_skills` handler (Phase 2).
3. **Modify** `tools/list` to return only `search_skills` (Phase 3).
4. **On the client/agent side**, implement the two‑step loop (Phase 4).

That’s it. Your server continues to serve all tools on demand, but the initial tool list is tiny, saving massive amounts of tokens.

---

## Next Steps

If you are using a specific MCP library (e.g., `fastmcp`, `mcp-python-sdk`, or a custom server), adapt the code snippets accordingly. The core logic remains identical.

Once implemented, monitor the token usage and adjust `k` (the number of retrieved skills) based on actual prompt complexity – 5 is a safe default.

This plan provides all necessary details for an AI agent (or a human developer) to carry out the implementation successfully.