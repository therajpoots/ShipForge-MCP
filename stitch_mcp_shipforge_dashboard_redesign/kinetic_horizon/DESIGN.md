---
name: Kinetic Horizon
colors:
  surface: '#0e1416'
  surface-dim: '#0e1416'
  surface-bright: '#343a3c'
  surface-container-lowest: '#090f11'
  surface-container-low: '#171d1e'
  surface-container: '#1b2122'
  surface-container-high: '#252b2d'
  surface-container-highest: '#303638'
  on-surface: '#dee3e6'
  on-surface-variant: '#bcc9cd'
  inverse-surface: '#dee3e6'
  inverse-on-surface: '#2b3133'
  outline: '#869397'
  outline-variant: '#3d494c'
  surface-tint: '#4cd7f6'
  primary: '#4cd7f6'
  on-primary: '#003640'
  primary-container: '#06b6d4'
  on-primary-container: '#00424f'
  inverse-primary: '#00687a'
  secondary: '#bcc7de'
  on-secondary: '#263143'
  secondary-container: '#3e495d'
  on-secondary-container: '#aeb9d0'
  tertiary: '#c6c6cc'
  on-tertiary: '#2f3035'
  tertiary-container: '#a5a6ac'
  on-tertiary-container: '#3a3c40'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#acedff'
  primary-fixed-dim: '#4cd7f6'
  on-primary-fixed: '#001f26'
  on-primary-fixed-variant: '#004e5c'
  secondary-fixed: '#d8e3fb'
  secondary-fixed-dim: '#bcc7de'
  on-secondary-fixed: '#111c2d'
  on-secondary-fixed-variant: '#3c475a'
  tertiary-fixed: '#e2e2e8'
  tertiary-fixed-dim: '#c6c6cc'
  on-tertiary-fixed: '#1a1c20'
  on-tertiary-fixed-variant: '#45474b'
  background: '#0e1416'
  on-background: '#dee3e6'
  surface-variant: '#303638'
typography:
  headline-xl:
    fontFamily: Outfit
    fontSize: 40px
    fontWeight: '600'
    lineHeight: 48px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Outfit
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Outfit
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 28px
  body-md:
    fontFamily: Outfit
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  metric-lg:
    fontFamily: JetBrains Mono
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
  metric-sm:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.1em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  container-padding: 2rem
  gutter: 1.5rem
  panel-gap: 1rem
  inner-padding: 1.25rem
---

## Brand & Style

The design system is engineered for high-performance naval architecture and Computational Fluid Dynamics (CFD). It targets engineers and maritime researchers who require an environment that balances intense data density with a premium, futuristic aesthetic.

The visual style is **Scientific Glassmorphism**. It evokes the feeling of a high-tech command deck or a deep-sea research laboratory. The interface prioritizes depth through layering, using semi-transparent surfaces and luminous accents to guide the eye toward critical simulation data. The emotional response is one of precision, advanced capability, and absolute reliability under technical complexity.

## Colors

This design system utilizes a "Deep Space" palette to maximize contrast for luminous data overlays.

- **Surface Primary:** #0A0C10 (Deep space dark) serves as the infinite background.
- **Surface Secondary:** #1E293B (Slate blue) is used for panel backgrounds and structural elements.
- **Accent Cyan:** #06B6D4 is the primary interactive color, representing active states, selection glows, and "flow" indicators.
- **Alert Red:** #EF4444 is reserved for critical hull stress points or simulation errors.
- **Success Emerald:** #10B981 marks completed computations and stable parameters.

All surfaces should utilize a semi-transparent alpha channel (e.g., `rgba(30, 41, 59, 0.7)`) to allow background blurs to penetrate the UI layers.

## Typography

The typography strategy separates the **interface (Outfit)** from the **engine (JetBrains Mono)**. 

- Use **Outfit** for all navigational elements, page titles, and explanatory text. It provides a clean, modern geometric feel that prevents the UI from feeling overly industrial.
- Use **JetBrains Mono** for all numerical readouts, CFD coordinates, terminal outputs, and status labels. This monospaced font ensures that rapidly changing metrics do not cause horizontal layout shifts (jitter) and reinforces the scientific nature of the tool.

## Layout & Spacing

The layout follows a **Fixed-Fluid Hybrid** model. The sidebar and inspector panels occupy fixed widths (300px and 350px respectively) to maintain the readability of technical controls, while the central viewport (the CFD Canvas) is fluid.

A 12-column grid is used within panels for organizing metrics. Spacing is tight (8px increments) to allow for high information density, but significant "outer" margins (32px) are maintained to create a sense of focused isolation for the ship model. Content reflow on smaller screens should collapse sidebars into slide-over "HUD" elements.

## Elevation & Depth

This design system rejects traditional shadows in favor of **Luminous Depth**.

- **Z-Axis Tiers:** Depth is established via `backdrop-filter: blur(12px)`.
- **Borders:** All panels must have a `1px` solid border with a `rgba(255, 255, 255, 0.1)` value. On the top and left edges, this can be slightly brighter (`0.2`) to simulate a subtle top-down light source.
- **Glows:** High-priority elements use an `outer-glow` (drop-shadow with the accent color) rather than a dark shadow. 
- **The "Glass" Effect:** Panels should have a subtle gradient background from `rgba(30, 41, 59, 0.8)` to `rgba(10, 12, 16, 0.9)`.

## Shapes

The shape language is **Technical & Precise**. We use "Soft" (0.25rem/4px) corner radii for standard UI elements like buttons and inputs to maintain a professional, rigid feel. 

Large containers and main dashboard panels use "Rounded-lg" (8px) to soften the overall viewport frame, but interior components must remain sharp and clinical.

## Components

### Glowing Buttons
Buttons are semi-transparent with a 1px Cyan border. On hover, the border-glow intensifies, and the background fill increases opacity from 10% to 25%. Active states include a 4px Cyan outer blur.

### Status Indicator Rings
Used for CFD progress and hull integrity. These are 2px thick concentric circles. The primary ring uses a dash-array stroke that rotates slowly. For alerts, the ring pulses between `#EF4444` and transparent.

### High-End Sliders
The slider track is a thin 2px slate line. The "thumb" is a vertical Cyan bar with a slight glow. Numerical values are displayed above the thumb in JetBrains Mono and update in real-time.

### Glass Cards
Cards for metric summaries do not have solid backgrounds. They rely on the `12px` backdrop blur to separate themselves from the 3D ship viewport behind them.

### Data Visualization
Charts should use "Neon" line styles—1.5px width with a subtle glow of the same color. Avoid solid fills in charts; use low-opacity gradients to fill areas under lines.