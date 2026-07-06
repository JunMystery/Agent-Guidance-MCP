# Image Prompts for Agent Guidance MCP GitHub README

Target model: DALL-E 3 (best text rendering). Midjourney v6 as fallback
(omit text labels — Midjourney cannot render readable text).
Resolution: 1792x1024 for hero/token-savings. 1024x1792 for pipeline. 1024x1024 for tool-surface.

---

## IMG 1: MCP Pipeline Architecture (Hero Banner)
**File**: `docs/images/hero-banner.png`
**Size**: 1792x1024 (16:9 landscape)

```
CRITICAL: This is an architectural diagram. It MUST contain readable text labels
in a clean sans-serif font (Inter or SF Pro Display). Labels in white bold on
dark background. Tool names at 10-11pt equivalent. Section headers at 14-16pt.
All text must be sharp, anti-aliased, and clearly legible at 1x zoom.

NO photorealism. NO 3D renders. NO faces. NO people. NO stock photography.
Flat vector architectural diagram. Think AWS reference architecture or system
design diagram.

BACKGROUND: Solid #0D1117.

═══════════════════════════════════════════════════════════════
OVERALL LAYOUT: Left-to-right pipeline with 4 horizontal zones
═══════════════════════════════════════════════════════════════

ZONE 1 — LEFT EDGE (15% width): "AI CODING AGENT" section
  - A rounded rectangle in purple #6C5CE7 at 30% fill, spanning the full zone height.
  - Inside, top: small icon of a gear/cog combined with a chat bubble (white outline).
  - Center: bold white text "AI CODING AGENT".
  - Below: smaller text "Claude · Cursor · Copilot · OpenCode" in #8B949E.
  - From the right edge of this block, a thick 3px cyan #00D2D3 arrow points
    rightward with the label "JSON-RPC via Stdio" in #8B949E small text above it.

ZONE 2 — CENTER-LEFT (20% width): "MCP SERVER" section
  - A larger rounded rectangle in solid purple #6C5CE7 (60% fill), center-aligned.
  - Inside, top: bold white text "MCP SERVER".
  - Below, in a smaller font: "Agent Guidance MCP" in cyan #00D2D3.
  - Below that, three small feature tags as pill badges in #0D1117 background
    with cyan borders: "168 Skills", "Token Optimizer", "CodeGraph".
  - From the right edge, six thin 1.5px cyan #00D2D3 arrows fan out to Zone 3
    (three going up at angles, three going down at angles) to connect to the
    six tool blocks.

ZONE 3 — CENTER-RIGHT (50% width): "MCP TOOLS" section
  Six rounded rectangle tool blocks arranged in two rows of three, connected
  to the MCP Server by the fan-out arrows from Zone 2.

  TOP ROW (left to right):
    Block A: Purple #6C5CE7 fill. Label "task_pipeline" in white bold.
      Sub-label "Call First — context prep" in #8B949E tiny text.
      Icon: rocket shape (white outline).
    Block B: Cyan #00D2D3 outline, 20% fill. Label "guidance" in white.
      Sub-label "Standards & Docs" in #8B949E.
      Icon: compass (circle + needle, white outline).
    Block C: Cyan #00D2D3 outline, 20% fill. Label "project_context" in white.
      Sub-label "Read · Search · Symbols" in #8B949E.
      Icon: folder tree (white outline).

  BOTTOM ROW (left to right):
    Block D: Teal #58A6FF outline, 20% fill. Label "ui_ux" in white.
      Sub-label "Design Guidance" in #8B949E.
      Icon: palette (circle + drops, white outline).
    Block E: Green #3FB950 outline, 20% fill. Label "session_continuity" in white.
      Sub-label "State Persistence" in #8B949E.
      Icon: save/disk shape (white outline).
    Block F: Gray #30363D outline, 20% fill. Label "health · diagnose · stats" in
      white. Sub-label "Operational" in #8B949E.
      Icon: heartbeat/pulse line (white outline).

  From the right edge of each tool block, a thin 1px arrow in #00D2D3 (30%
  opacity) points rightward toward Zone 4.

ZONE 4 — RIGHT EDGE (15% width): "RESPONSE" section
  - A rounded rectangle in green #3FB950 at 20% fill, spanning the full zone height.
  - Inside, top: bold white text "OPTIMIZED RESPONSE".
  - Below: "40-80% smaller" in #3FB950.
  - Below that, a vertical stack of three small labeled stages with arrow between
    each, in tiny #8B949E text:
    "Strip ANSI → Smart Truncate → Deduplicate"
  - At the bottom: a curved return arrow in #00D2D3 looping back toward Zone 1
    (the AI Agent), labeled "Context Window" in #8B949E tiny text.

═══════════════════════════════════════════════════════════════
STYLE: Clean flat vector architectural diagram. Think AWS
Architecture Diagrams or Google Cloud reference architectures.
Flat colors only. No gradients. No shadows. No glow effects.
All text must be readable. Solid #0D1117 background throughout.
Clear visual hierarchy with distinct color zones.
═══════════════════════════════════════════════════════════════
```

---

## IMG 2: Token Savings Comparison Chart
**File**: `docs/images/token-savings-chart.png`
**Size**: 1792x1024 (16:9 landscape)

```
CRITICAL: This image MUST contain readable text labels and numbers. All text must
be in a clean sans-serif font (Inter or SF Pro Display style), white or colored
as specified. Text must be sharp, anti-aliased, and clearly legible at 1x zoom.

A flat infographic comparison chart with two columns. NO photorealism. NO 3D.
NO faces. NO people. Vector illustration style with embedded text.

BACKGROUND: Solid #0D1117.

LAYOUT: Two equal-width columns separated by a thin vertical 1px #30363D line
down the center. A downward arrow between the columns at the top.

LEFT COLUMN — header in small uppercase text at top: "WITHOUT MCP" in #F85149 (red).
Below the header, four metric rows stacked vertically:
  Row 1: Large number "12-18" in white. Label below: "tool calls" in #8B949E small text.
  Row 2: Large number "45K" in white. Label below: "tokens used" in #8B949E.
  Row 3: Large number "8+" in white. Label below: "file reads" in #8B949E.
  Row 4: Large number "~4 min" in white. Label below: "time to fix" in #8B949E.
Left column has a subtle red tint overlay at 5% opacity. A thin red #F85149
border on the left edge of the column.

RIGHT COLUMN — header: "WITH MCP" in #3FB950 (green).
  Row 1: "4-6" in green #3FB950. Label: "tool calls" in #8B949E.
  Row 2: "12K" in green. Label: "tokens used".
  Row 3: "3" in green. Label: "capped reads".
  Row 4: "~45s" in green. Label: "time to fix".
Right column has subtle green tint at 5% opacity. Thin green #3FB950 right border.

CENTER: Between the two columns, a large bold percentage: "73%" in white, with
small text below: "fewer tokens" in #8B949E.

STYLE: Clean data dashboard aesthetic. Like a Grafana or Datadog widget.
Flat colors, no gradients, no shadows. All text must be in a clean sans-serif
font (Inter or SF Pro style). Numbers must be clearly readable.
```

---

## IMG 3: Token Optimization Pipeline
**File**: `docs/images/token-pipeline.png`
**Size**: 1024x1792 (9:16 portrait — vertical flow)

```
CRITICAL: This image MUST contain readable text labels at every stage. All text
must be rendered in a clean sans-serif font (Inter or SF Pro Display style).
Stage names in white bold 14-16pt equivalent. Descriptions in #8B949E at 10-11pt
equivalent. Text must be sharp and clearly legible against the dark background.

A vertical pipeline flow diagram. NO photorealism. NO 3D. NO faces. NO people.
Flat vector infographic style with embedded text labels.

BACKGROUND: Solid #0D1117.

TOP SECTION (first 15% of image height):
A wide rectangular block spanning 80% width, filled with a chaotic pattern of
small overlapping colorful rectangles and zigzag lines in various colors (red,
yellow, blue, green, orange). Above it, a label: "RAW RESPONSE" in white bold
text. Below it, a label: "Unfiltered MCP output" in #8B949E small text.

From this block, a thick cyan #00D2D3 arrow (4px width) points downward to the
first stage.

MIDDLE SECTION (stages, 70% of height):
Eight stages arranged vertically, each separated by a thin 2px arrow in #00D2D3.

Each stage is a horizontal pill-shaped rounded rectangle (width 70%, height 30px)
in purple #6C5CE7. Inside each pill:
  Left side: the stage number in a small white circle (20px diameter).
  Center: the stage name in white bold text.
  Right side: a small icon-like abstract shape in cyan:
    Stage 1 "ANSI STRIP": a crossed-out circle symbol.
    Stage 2 "REGEX REPLACE": a forward slash and asterisk pattern.
    Stage 3 "SHORT CIRCUIT": a small lightning bolt shape.
    Stage 4 "LINE FILTER": a simple funnel/triangle pointing down.
    Stage 5 "SMART TRUNCATION": a scalpel shape — thin vertical line with
      diagonal cross-line.
    Stage 6 "HEAD/TAIL KEEP": two horizontal brackets facing inward.
    Stage 7 "MAX LINES CAP": a horizontal ceiling bar with arrow pointing down.
    Stage 8 "EMPTY GUARD": a simple shield outline shape.

Below each pill, a brief one-line description in #8B949E small text:
  Stage 1: "Removes terminal color codes"
  Stage 2: "Collapses noise patterns"
  Stage 3: "Skips empty payloads"
  Stage 4: "Keeps only relevant output"
  Stage 5: "Preserves imports & signatures"
  Stage 6: "First + last N lines"
  Stage 7: "Absolute ceiling cutoff"
  Stage 8: "Fallback if empty"

BOTTOM SECTION (last 15%):
A compact clean rectangular block in green #3FB950, same width as the top block.
Inside: "OPTIMIZED RESPONSE" in dark navy #0D1117 bold text. Below: "40-80% smaller"
in #0D1117. The block has a subtle checkmark symbol in the right corner.

STYLE: Clean technical diagram. Think AWS architecture diagrams or system design
interview drawings. Flat colors. No gradients. No shadows. All text must be
readable sans-serif font.
```

---

## IMG 4: MCP Tool Surface Hexagon Diagram
**File**: `docs/images/tool-surface.png`
**Size**: 1024x1024 (1:1 square)

```
CRITICAL: This image MUST contain readable text labels inside each hexagon. All
text must be rendered in a clean sans-serif font (Inter or SF Pro Display style).
Tool names in white bold 13-15pt equivalent. Subtitles/descriptions in #8B949E
at 9-10pt equivalent. Text must be centered within each hexagon and clearly
legible against the dark background.

A hexagonal node diagram showing 6 interconnected tools. NO photorealism. NO 3D.
NO faces. NO people. Flat vector infographic with embedded text labels.

BACKGROUND: Solid #0D1117.

LAYOUT: Six hexagons arranged in a circular/flower pattern.
  - CENTER (largest, 1.5x size, solid purple #6C5CE7 fill):
    Inside: white bold text "task_pipeline". Below in smaller text: "Call First".
    A small rocket icon shape (simple triangle + fins, white outline only) above.
  - TOP-RIGHT (medium, cyan #00D2D3 outline, 15% fill):
    Inside: white text "guidance". Small compass icon (circle with pointed needle).
    Below: "Standards & Docs" in #8B949E small text.
  - MIDDLE-RIGHT (medium, teal #58A6FF outline, 15% fill):
    Inside: white text "project_context". Small folder-tree icon.
    Below: "Read & Search" in #8B949E.
  - BOTTOM (medium, blue #79C0FF outline, 15% fill):
    Inside: white text "ui_ux". Small palette icon (circle + paint drops).
    Below: "Design Guidance" in #8B949E.
  - MIDDLE-LEFT (medium, green #3FB950 outline, 15% fill):
    Inside: white text "session_continuity". Small save icon (floppy disk shape).
    Below: "State Persistence" in #8B949E.
  - TOP-LEFT (small, gray #30363D outline, 10% fill):
    Inside: white text "health / diagnose / stats". Below: "Operational" in #8B949E.

CONNECTIONS: Thin 1.5px lines in #00D2D3 with 50% opacity connecting the center
hexagon to all five outer hexagons. Lines have small dot markers at midpoint.

STYLE: Clean SaaS architecture diagram. Think Cloudflare or GitHub feature pages.
Flat colors, no gradients. All text readable in white sans-serif on dark background.
No overlapping elements. Clear spacing between hexagons.
```

---

## Tips for Best Results

1. **Use DALL-E 3** — it renders readable text and follows layout instructions.
   Prompts 2–4 include explicit font specs (Inter/SF Pro, specific pt sizes) and
   color-coded text. DALL-E 3 produces the most accurate text rendering.
2. **Midjourney fallback**: remove all text labels (Midjourney garbles text).
   Replace text content with abstract shapes and request "infographic diagram
   with placeholder boxes for text, no actual letters or words".
3. **Generate 2–4 variants per prompt**, pick the best.
4. **Crop/center** in an image editor after generation — AI sometimes misaligns.
5. If DALL-E adds unwanted text or artifacts to IMG 1 (the text-free banner),
   add: "NO text. NO letters. NO words. Abstract shapes ONLY." and regenerate.
6. **Text legibility check**: After generation, view the image at 50% zoom in
   your GitHub README preview. If labels are hard to read, request: "Make all
   text 20% larger and bolder" in a follow-up prompt.
7. **Consistency**: Generate all 4 images in the same DALL-E session — the model
   tends to maintain consistent color palette and style across a conversation.
