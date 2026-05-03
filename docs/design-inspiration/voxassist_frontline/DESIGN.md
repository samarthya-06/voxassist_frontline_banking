---
name: VoxAssist Frontline
colors:
  surface: '#faf9fe'
  surface-dim: '#dad9df'
  surface-bright: '#faf9fe'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f4f3f8'
  surface-container: '#eeedf2'
  surface-container-high: '#e8e7ed'
  surface-container-highest: '#e3e2e7'
  on-surface: '#1a1b1f'
  on-surface-variant: '#43474f'
  inverse-surface: '#2f3034'
  inverse-on-surface: '#f1f0f5'
  outline: '#747781'
  outline-variant: '#c4c6d1'
  surface-tint: '#3e5e95'
  primary: '#00193c'
  on-primary: '#ffffff'
  primary-container: '#002d62'
  on-primary-container: '#7796d1'
  inverse-primary: '#abc7ff'
  secondary: '#505f76'
  on-secondary: '#ffffff'
  secondary-container: '#d0e1fb'
  on-secondary-container: '#54647a'
  tertiary: '#330e00'
  on-tertiary: '#ffffff'
  tertiary-container: '#541d02'
  on-tertiary-container: '#d4815d'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d7e2ff'
  primary-fixed-dim: '#abc7ff'
  on-primary-fixed: '#001b3f'
  on-primary-fixed-variant: '#24467c'
  secondary-fixed: '#d3e4fe'
  secondary-fixed-dim: '#b7c8e1'
  on-secondary-fixed: '#0b1c30'
  on-secondary-fixed-variant: '#38485d'
  tertiary-fixed: '#ffdbcd'
  tertiary-fixed-dim: '#ffb597'
  on-tertiary-fixed: '#360f00'
  on-tertiary-fixed-variant: '#743417'
  background: '#faf9fe'
  on-background: '#1a1b1f'
  surface-variant: '#e3e2e7'
typography:
  h1:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  h2:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  h3:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: -0.01em
  body-base:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
    letterSpacing: '0'
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: '0'
  label-caps:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.05em
  tabular-nums:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  container-padding: 24px
  gutter: 16px
  component-gap-xs: 4px
  component-gap-sm: 8px
  component-gap-md: 12px
  section-margin: 24px
---

## Brand & Style
The design system is engineered for high-stakes enterprise banking environments where speed of information processing and absolute clarity are paramount. The brand personality is institutional, authoritative, and precise, aiming to evoke a sense of reliability and calm efficiency for power users.

The visual style follows a **Corporate / Modern** aesthetic, prioritizing functional density over decorative elements. It utilizes a high-contrast interface to reduce cognitive load during long shifts, ensuring that primary actions are unmistakable and data visualization remains the focal point.

## Colors
The palette is anchored by a deep navy blue, reserved strictly for primary actions, navigation anchors, and active states to maintain a strong visual hierarchy. 

- **Primary:** Deep Navy (#002D62) provides a stable, institutional foundation.
- **Surface & Background:** A clean distinction is made between the application shell (#F8F9FA) and workspace cards (#FFFFFF) to create subtle depth without relying on heavy shadows.
- **Accents:** Success and Destructive colors are calibrated for high legibility against white backgrounds, meeting WCAG AA standards for accessibility.
- **Neutrals:** A range of slate grays is used for borders, secondary text, and disabled states to keep the interface feeling crisp and organized.

## Typography
The design system utilizes **Inter** for its exceptional legibility in data-heavy environments. The scale is intentionally compact to facilitate information density.

A key feature is the use of `tabular-nums` for all financial figures and data tables, ensuring that columns of numbers align perfectly for rapid scanning. Headlines are kept modest in size to preserve vertical space, while labels use a slightly heavier weight or uppercase styling to differentiate them from interactive data points.

## Layout & Spacing
The layout employs a **Fluid Grid** logic with a 4px base unit. This tight spacing rhythm is designed to maximize "above the fold" information without sacrificing hit targets.

Margins and gutters are kept lean (16px–24px) to allow for multi-column data views and side-by-side comparisons of banking records. Padding within components (like table cells or input fields) is minimized to the smallest comfortable standard to ensure the interface remains efficient for expert users who navigate the system daily.

## Elevation & Depth
Depth is communicated through **Low-contrast outlines** rather than expansive shadows. This keeps the interface feeling "flat" and professional, preventing a cluttered look when many windows or cards are open simultaneously.

- **Level 0 (Background):** #F8F9FA.
- **Level 1 (Cards/Workspaces):** #FFFFFF with a 1px border (#E2E8F0).
- **Level 2 (Popovers/Modals):** #FFFFFF with a 1px border and a very tight, subtle shadow (0 4px 6px -1px rgb(0 0 0 / 0.1)) to lift it slightly from the workspace.
- **Active States:** Elements are highlighted using the primary navy color or a subtle 2px inset border to indicate focus without shifting layout.

## Shapes
The shape language is conservative and architectural. A subtle **4px (Soft)** corner radius is applied to buttons, input fields, and cards. This slight rounding softens the "industrial" feel just enough to appear modern while maintaining the serious tone of an internal financial tool.

Secondary elements like tags or "chips" may use slightly more rounding (6px) to distinguish them from primary action buttons, but pill-shaped elements are avoided to maintain the system's structured, grid-aligned integrity.

## Components
Components are built upon the Shadcn UI framework, customized for high-density banking workflows.

- **Buttons:** Primary buttons use the Deep Navy (#002D62) with white text. Ghost and Outline variants use #64748B for secondary actions. Sizing is compact (32px height for standard).
- **Data Tables:** The core of the system. Uses 13px text, thin borders, and a subtle zebra-striping on hover. Headers are #F8F9FA with 11px uppercase labels.
- **Input Fields:** Sharp 1px borders (#E2E8F0) that turn Primary Navy on focus. Labels are positioned above the input to save horizontal space.
- **Cards:** Crisp white containers with no visible shadow, defined by 1px borders. Card headers use a light gray bottom border to separate metadata from content.
- **Status Badges:** Small, rectangular badges with subtle background tints and high-contrast text for "Pending," "Settled," or "Flagged" states.
- **Sidebar:** A collapsed or slim navigation system utilizing the primary navy for icons to maximize horizontal workspace for data entry.