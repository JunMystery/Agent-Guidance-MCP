# Image Prompts for Agent Guidance MCP GitHub README

Target model: DALL-E 3 via ChatGPT (best text rendering for diagrams).
Resolution: 1792x1024 (16:9) for hero/token-savings, 1024x1792 (9:16) for pipeline, 1024x1024 for tool-surface.

---

## IMG 1: Hero Banner
**File**: `docs/images/hero-banner.png`
**Size**: 1792x1024 (16:9 landscape)

```
A dark-themed tech hero banner with text overlay for a GitHub project README.
CRITICAL: This image MUST contain readable text — a title and short description.
All text must be in a clean sans-serif font (Inter or SF Pro Display), white,
anti-aliased, and sharp at 1x zoom. NO photorealism. NO 3D. NO faces. NO people.
NO stock photography.

BACKGROUND: Deep navy #0D1117 with subtle noise texture (1-2% opacity).

LAYOUT: Split composition — text on the left 45%, abstract art on the right 55%.

───────────────────────────────────────────────────────────────
LEFT SIDE (45%): TEXT OVERLAY
───────────────────────────────────────────────────────────────

A semi-transparent dark card (rounded rectangle, #161B22 at 60% fill, 8px
border radius) centered vertically. Inside the card, stacked text:

  TOP: A small uppercase label "MCP SERVER" in cyan #00D2D3 at 10pt, with
     a thin cyan horizontal line (40px wide) directly below it.

  MIDDLE: Large bold title "Agent Guidance" on line 1, then "MCP" on line 2.
     Both in white, 28-32pt equivalent, tight line spacing (1.1). The word
     "Guidance" has a subtle purple #6C5CE7 underline accent (3px thick,
     60% width of the word).

  BELOW TITLE: A short description in #8B949E at 13-14pt:
     "168-skill catalog · Token optimization engine ·"
     (line break)
     "Bounded project context tools · Stdio transport"

  BOTTOM OF CARD: Three small feature pill badges in a row:
     Pill 1 (purple #6C5CE7 fill): "40-80% fewer tokens" in white tiny text.
     Pill 2 (cyan #00D2D3 outline, 20% fill): "9 IDE support" in white.
     Pill 3 (green #3FB950 outline, 20% fill): "Auto-configured" in white.

───────────────────────────────────────────────────────────────
RIGHT SIDE (55%): ABSTRACT ART
───────────────────────────────────────────────────────────────

PRIMARY — Center-right: A large glowing translucent sphere/orb in cyan #00D2D3
at 15% opacity with soft gaussian blur (200px radius). Inside the orb, dozens
of tiny bright cyan dots (2-3px each) arranged in curved sweeping arcs like
orbital paths. Dots have subtle glow — some at 80% opacity, most at 20-40%.

SECONDARY — Far right: Five thin vertical glowing lines in purple #6C5CE7 at
30% opacity, varying heights (shortest 15%, tallest 60%), like audio spectrum
bars. At the base of each line, a tiny bright purple dot. Tops fade to
transparent.

TERTIARY — Bottom edge (full width): A thin horizontal gradient line from
cyan #00D2D3 (left, 40% opacity) fading through purple (center, 20%) to
transparent (right). Above it, scattered tiny diamonds, circles, and plus marks
floating upward like particles in #8B949E at 10% opacity.

ATMOSPHERE:
- Subtle vignette (darker edges, lighter center) — barely perceptible
- Premium SaaS feel: Vercel / Linear / Stripe hero aesthetic
- Matte finish, not glossy

COLOR PALETTE: #0D1117 bg, #00D2D3 cyan, #6C5CE7 purple, #8B949E gray, #161B22 card, #3FB950 green. NO other colors.
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
   Prompts 2-4 include explicit font specs (Inter/SF Pro, specific pt sizes).
2. **IMG 1 only**: NO text. DALL-E sometimes adds hallucinated words to images.
   If text appears, add "Absolutely NO text, NO letters, NO words" and regenerate.
3. **Midjourney fallback** (for IMG 2-4): remove all text labels. Midjourney
   garbles text. Replace with "placeholder boxes for text labels, no letters".
4. **Generate 2-4 variants per prompt**, pick the best.
5. **Crop/center** in an image editor — AI sometimes misaligns.
6. **Text legibility**: view at 50% zoom. If labels are hard to read, request
   "Make all text 20% larger and bolder" in a follow-up.
7. **Consistency**: generate all 4 in the same DALL-E session for matching style.
