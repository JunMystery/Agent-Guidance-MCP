---
name: humanizer
description: Transforms AI-generated text into more natural, human-like language by adjusting tone, varying sentence structure, and removing common AI patterns. Use for refining content for readability and authenticity.
---

# Humanizer

Transforms AI-generated text into more natural, human-like language by adjusting tone, varying sentence structure, and removing common AI patterns.

## How It Works

1. **Analysis**: Identify dry, repetitive, or overly formal AI markers in the input.
2. **Transformation**: Apply humanizing heuristics (e.g., varied sentence lengths, colloquialisms where appropriate, nuanced transitions).
3. **Review**: Provide the refined text alongside a summary of changes made.

## Usage (Optional)

```bash
bash /mnt/skills/user/humanizer/scripts/humanize.sh [text]
```

**Arguments:**
- `text` - The AI-generated text to humanize.

## Output

The humanized version of the provided text.

## Present Results to User

Present the original text followed by the humanized version, highlighting the key improvements made.

## Troubleshooting

- Ensure the input is not extremely long, as it may exceed LLM context limits.
- If the output is still too formal, try specifying a target audience in the input.
