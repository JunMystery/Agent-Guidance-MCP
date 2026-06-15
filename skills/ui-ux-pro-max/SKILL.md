---
name: ui-ux-pro-max
description: UI/UX design intelligence for web, mobile, dashboards, landing pages, brand systems, banners, slides, design tokens, component styling, typography, color palettes, accessibility, responsive layout, interaction states, animation, shadcn/Tailwind UI, charts, and frontend quality review. Use when planning, building, reviewing, fixing, or improving interface structure, visual design, user experience, design systems, branded creative assets, or presentation-style UI.
---

# UI/UX Pro Max

Use this as the single entrypoint for UI/UX Pro Max guidance. Load only the
internal reference files needed for the task, then use the scripts when a
searchable recommendation or deterministic helper is more efficient than manual
lookup.

## When to Use

- Building or improving websites, apps, dashboards, landing pages, components, or mobile UI.
- Choosing style direction, color, typography, icons, layout, motion, or interaction states.
- Creating design systems, brand assets, banners, slides, logos, CIP mockups, or social images.
- Reviewing frontend work for UX quality, accessibility, responsive behavior, or visual consistency.

## Core Workflow

1. Identify the surface: landing page, dashboard, app screen, component,
   design system, brand asset, banner, slide deck, logo/CIP/icon, or review.
2. Search the embedded knowledge base for product, style, color, typography,
   UX, chart, stack, or slide recommendations.
3. Load the smallest relevant reference files from the map below.
4. Apply the repo's existing components, tokens, framework conventions, and
   accessibility requirements before introducing new patterns.
5. Verify visual quality across mobile and desktop, including text fit, touch
   targets, keyboard/focus behavior, contrast, reduced motion, and layout
   stability.

## Search Helpers

Run from the repository root:

```bash
python skills/ui-ux-pro-max/scripts/search.py "saas dashboard" --design-system --format markdown
python skills/ui-ux-pro-max/scripts/search.py "fintech trust palette" --domain color --json
python skills/ui-ux-pro-max/scripts/search.py "modal focus states" --domain ux
python skills/ui-ux-pro-max/scripts/search.py "navigation performance" --stack react
python skills/ui-ux-pro-max/scripts/search-slides.py "investor pitch" --json
```

Use `--domain` for `style`, `color`, `chart`, `landing`, `product`, `ux`,
`typography`, `icons`, `react`, `web`, or `google-fonts`. Use `--stack` for
framework-specific UI guidance such as `react`, `nextjs`, `vue`, `svelte`,
`astro`, `swiftui`, `react-native`, `flutter`, `nuxtjs`, `nuxt-ui`,
`html-tailwind`, `shadcn`, `jetpack-compose`, `threejs`, `angular`, or
`laravel`.

## Reference Map

- Product/style/color/typography/UX reasoning:
  `references/ui-ux-pro-max-guide.md`
- Banner and social/ad/hero banner design:
  `references/banner/overview.md`
- Brand voice, visual identity, messaging, assets, and approval:
  `references/brand/overview.md`
- Logo, CIP, icon, social photo, and multi-format design:
  `references/design/overview.md`
- Token architecture, component specs, Tailwind integration, and slide systems:
  `references/design-system/overview.md`
- Strategic HTML presentations and slide copy/layout patterns:
  `references/slides/overview.md`
- shadcn/ui, Tailwind, accessible components, canvas visuals, and UI styling:
  `references/ui-styling/overview.md`

## Implementation Priorities

- Accessibility first: contrast, semantic controls, keyboard support, visible
  focus, alt text, labels, and non-color-only status communication.
- Interaction quality: touch targets, loading/error/success feedback, hover and
  pressed states, and gesture alternatives.
- Responsive layout: mobile-first constraints, no horizontal overflow, stable
  fixed-format controls, and readable line lengths.
- Visual consistency: semantic tokens, consistent icon style, coherent
  typography scale, purposeful motion, and one clear primary action per screen.
- Performance: optimized/reserved media, route or component splitting where
  appropriate, transform/opacity animations, and reduced layout shift.

## Internal Assets

- Knowledge CSVs live in `data/`.
- Reusable helper scripts live in `scripts/`.
- Starter prompt/platform templates live in `templates/`.
- Font assets for canvas-oriented work live in `assets/ui-styling/`.

Do not create or call separate public skills for banner, brand, slides,
ui-styling, or imported design-system work. They are internal facets of this
single `ui-ux-pro-max` skill.
