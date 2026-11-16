---
name: Elite Performance Minimalist
colors:
  surface: '#fbf8ff'
  surface-dim: '#dad9e2'
  surface-bright: '#fbf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f4f2fc'
  surface-container: '#efedf6'
  surface-container-high: '#e9e7f1'
  surface-container-highest: '#e3e1eb'
  on-surface: '#1a1b22'
  on-surface-variant: '#5a4136'
  inverse-surface: '#2f3037'
  inverse-on-surface: '#f1eff9'
  outline: '#8e7164'
  outline-variant: '#e2bfb0'
  surface-tint: '#a04100'
  primary: '#a04100'
  on-primary: '#ffffff'
  primary-container: '#ff6b00'
  on-primary-container: '#572000'
  inverse-primary: '#ffb693'
  secondary: '#5f5e60'
  on-secondary: '#ffffff'
  secondary-container: '#e5e1e4'
  on-secondary-container: '#656466'
  tertiary: '#0062a1'
  on-tertiary: '#ffffff'
  tertiary-container: '#059eff'
  on-tertiary-container: '#003357'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdbcc'
  primary-fixed-dim: '#ffb693'
  on-primary-fixed: '#351000'
  on-primary-fixed-variant: '#7a3000'
  secondary-fixed: '#e5e1e4'
  secondary-fixed-dim: '#c8c6c8'
  on-secondary-fixed: '#1b1b1d'
  on-secondary-fixed-variant: '#474649'
  tertiary-fixed: '#d0e4ff'
  tertiary-fixed-dim: '#9ccaff'
  on-tertiary-fixed: '#001d35'
  on-tertiary-fixed-variant: '#00497b'
  background: '#fbf8ff'
  on-background: '#1a1b22'
  surface-variant: '#e3e1eb'
typography:
  display-metric:
    fontFamily: lexend
    fontSize: 48px
    fontWeight: '900'
    lineHeight: 52px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: lexend
    fontSize: 34px
    fontWeight: '800'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: lexend
    fontSize: 28px
    fontWeight: '800'
    lineHeight: 34px
  section-title:
    fontFamily: manrope
    fontSize: 20px
    fontWeight: '700'
    lineHeight: 28px
  body-main:
    fontFamily: manrope
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-secondary:
    fontFamily: manrope
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  caption-pill:
    fontFamily: manrope
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.02em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  margin-page: 24px
  gutter-grid: 16px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 32px
  section-gap: 48px
---

## Brand & Style
The brand personality of this design system is "Premium Minimal Sport." It is engineered to feel expensive, high-performance, and precise. It draws from **Minimalism** and **Modern Corporate** aesthetics, prioritizing immense whitespace and ultra-clean typography to create a sense of calm focus—essential for a high-end fitness experience.

The emotional response should be one of "effortless discipline." By removing visual noise and using a palette of sophisticated neutrals with surgical strikes of high-visibility orange, the UI feels like a professional-grade athletic tool rather than a casual social app.

## Colors
The color strategy utilizes a "Gallery White" base (`#F8F8FA`) to allow content and photography to breathe. The primary action color is a high-energy `accentOrange`, reserved strictly for key CTAs and active progress states. 

Supporting accents like `accentBlue` and `accentGreen` are used sparingly for data differentiation (e.g., hydration vs. recovery). A "Dark Mode" logic is applied contextually to specific "Hero" or "Workout" cards (`darkCard`) to create a high-contrast, immersive focus during active exercise sessions. Text hierarchy is strictly enforced through three tiers of grayscale to maintain legibility without sacrificing the minimal aesthetic.

## Typography
This design system utilizes **Lexend** for headlines and metrics to evoke an athletic, modern, and highly readable feel. **Manrope** is used for body copy and UI labels to provide a refined, technical balance.

Metrics are treated as primary visual elements; they use a "Black" weight and tight letter spacing to emphasize achievement. Large headers should always use the "bold/black" weight to anchor the page. For mobile-specific screens, headlines scale down to 28px to ensure no awkward line breaks while maintaining visual impact.

## Layout & Spacing
The layout follows a **fluid grid** model optimized for Android viewports. A standard 4-column mobile grid is used with 24px outer margins to create a "premium" sense of padding and 16px gutters between internal card elements.

Spacing follows an 8px rhythmic scale. Vertically, components are grouped into logical blocks with 32px or 48px gaps to prevent the UI from feeling cluttered. Content density should remain low to medium; if a screen feels crowded, increase the `section-gap` to emphasize the minimal aesthetic.

## Elevation & Depth
This design system avoids traditional heavy shadows in favor of **Tonal Layers** and **Low-Contrast Outlines**. 

- **Level 0 (Background):** `#F8F8FA` - The canvas.
- **Level 1 (Cards):** `#FFFFFF` with a 1px solid border of `#E8E8EC`. No shadow.
- **Level 2 (Active/Floating):** Use a very subtle, diffused ambient shadow (Opacity 4%, Blur 20px, Y-Offset 4px) only for floating action elements or high-priority modals.
- **Depth through Overlay:** Photography uses a linear gradient overlay (Top: Transparent to Bottom: `darkCard` at 80% opacity) to ensure text legibility while creating a sense of physical depth.

## Shapes
The shape language is defined by oversized, friendly radii that contrast against the technical typography. 

Standard cards utilize a 24px radius, while primary "Hero" sections (such as daily progress or featured workouts) use a more aggressive 32px radius to command attention. Buttons and interactive chips are strictly **Pill-shaped**, reinforcing the "Sport" aesthetic. This consistent curvature creates a tactile, premium feel that distinguishes the app from more rigid, utility-focused fitness trackers.

## Components
- **Buttons:** Primary CTAs are pill-shaped with `#FF6B00` fill and white text. Secondary buttons use the `accentOrangeSoft` background with orange text. 
- **Bottom Navigation:** Features a clean `#FFFFFF` surface. Active states use a 4px horizontal indicator pill in `#FF6B00` located above the icon, with an `accentOrangeSoft` circular highlight behind the active icon.
- **Cards:** White surface with 24px radius and 1px border. Inside, metrics are displayed in `textPrimary` with `textSecondary` labels.
- **Chips:** Full pill-shaped, using `surface_soft` for inactive states and `primary` for selected states.
- **Charts:**
    - *Activity (Bar):* Thin 8px bars with rounded caps.
    - *Calories (Area):* Smooth Bézier curves with a subtle gradient fill.
    - *Progress (Ring):* 12px stroke width with rounded ends.
- **Icons:** 24px line icons with a 1.5pt stroke weight. Do not use solid fills unless the icon is in an active state.
- **Interactions:** Every touch target must include a `0.98` scale down on press. Use staggered fade-in animations (50ms offset) for list items to enhance the "expensive" feel.