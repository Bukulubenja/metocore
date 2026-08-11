# SchoolOS — Brand Palette

Source: provided by product owner. Recorded here for use once template/UI work begins (Phase 3+ per the roadmap in `docs/architecture/phase-0-architecture-overview.md` §22) — no UI has been built yet, this is a reference for that point.

## Given colors

| Name | Hex | Contrast vs white (#FFFFFF) | Safe for body text on white? |
|---|---|---|---|
| Deep Navy | `#003272` | 12.4:1 | Yes — passes WCAG AA/AAA for any text size |
| Cobalt Blue | `#0065B3` | 6.0:1 | Yes — passes WCAG AA for normal text |
| Bright Cyan | `#009CD5` | 3.1:1 | No — only passes for large text (≥24px/bold ≥19px) or non-text UI (icons, borders). Too light for small body text or thin labels on white. |
| Forest Green | `#134C00` | 10.2:1 | Yes — passes WCAG AA/AAA for any text size |
| Leaf Green | `#4D9822` | 3.6:1 | No — same limitation as Bright Cyan: large text/UI only, not small body text |

(Contrast ratios computed against white; WCAG 2.2 AA requires ≥4.5:1 for normal text, ≥3:1 for large text/graphical objects — relevant since the spec commits to WCAG accessibility in §51.)

## Proposed semantic mapping

| Token | Color | Usage |
|---|---|---|
| `--color-brand-primary` | Deep Navy `#003272` | Headers, nav chrome, primary text on light backgrounds, dark-mode-style surfaces |
| `--color-brand-secondary` | Cobalt Blue `#0065B3` | Primary buttons/links, focus rings, interactive elements — safe for text too |
| `--color-brand-accent` | Bright Cyan `#009CD5` | Highlights, badges, chart accents, icons — not small text |
| `--color-positive-strong` | Forest Green `#134C00` | Confirmed/success text, "present"/"completed" states where text-weight color is needed |
| `--color-positive-accent` | Leaf Green `#4D9822` | Success badges, progress indicators, large success text — not small text |

## Gap to flag

This palette has **no warning/error/neutral colors** — but the product's core UI need (attendance states from §9/§21 of the architecture doc: `LATE`, `ABSENT`, `SUSPICIOUS`, `NOT_CHECKED_IN`) requires visually distinct alert colors that read as "needs attention" at a glance, separate from the green "all good" family. Reusing blue/green for those states would undermine the at-a-glance dashboard requirement in spec §28 ("do not overwhelm users" / clear status).

Also missing: a neutral/gray scale for body text, borders, disabled states, and backgrounds — five brand colors alone aren't enough to build a full UI.

**Needs your decision before Phase 3 template work starts:** do you have designated warning (amber/orange) and error (red) colors to pair with this palette, or should I propose a set that harmonizes with the given navy/blue/green? Neutrals I can propose without needing brand input (standard gray scale) unless you have a preference.

## CSS custom properties (draft, framework-agnostic)

```css
:root {
  --color-brand-primary: #003272;   /* Deep Navy */
  --color-brand-secondary: #0065B3; /* Cobalt Blue */
  --color-brand-accent: #009CD5;    /* Bright Cyan */
  --color-positive-strong: #134C00; /* Forest Green */
  --color-positive-accent: #4D9822; /* Leaf Green */
  /* --color-warning-*, --color-error-*, --color-neutral-* : pending decision above */
}
```
