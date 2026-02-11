---
name: modern-web-design
description: Create modern, responsive websites with light/dark themes and premium UX. Use this skill when the user asks for web design, UI/UX, or frontend development tasks that require a high-quality, modern aesthetic.
---

# Modern Web Design Skill

This skill guides the creation of modern, responsive, and aesthetically pleasing websites.

## Core Principles

1.  **Aesthetic Excellence**: Do not create "basic" or "MVP" looking sites. Aim for a premium, polished look (Glassmorphism, subtle gradients, clean typography).
2.  **Mobile-First Responsiveness**: All designs must be fully responsive, using CSS Grid and Flexbox.
3.  **User Experience (UX)**: Prioritize smooth interactions, micro-animations, and intuitive navigation.
4.  **Theming**: **MANDATORY** Light/Dark mode toggle in every design.

## Technical Requirements

### 1. File Structure
Unless a framework is requested, use a clean structure:
- `index.html`: Semantic HTML5.
- `styles.css`: Vanilla CSS (or Tailwind if requested).
- `script.js`: Logic for themes and interactions.

### 2. Theming (Light/Dark Mode)
- **CSS Variables**: Use CSS variables for all colors.
  ```css
  :root {
      --bg-color: #ffffff;
      --text-color: #1a1a1a;
      --primary-color: #3b82f6;
      /* ... other variables */
  }
  
  [data-theme="dark"] {
      --bg-color: #0f172a;
      --text-color: #f8fafc;
      /* ... dark mode overrides */
  }
  ```
- **JS Toggle**: Include a toggle button that switches the `data-theme` attribute on `<html>` or `<body>` and saves the preference to `localStorage`.

### 3. Typography
- Use modern sans-serif fonts (e.g., Inter, Roboto, Outfit, Plus Jakarta Sans) via Google Fonts.
- Ensure readable line heights (1.5 for body text) and adequate contrast.

### 4. Layout & Spacing
- Use a consistent spacing system (e.g., 4px, 8px, 16px, 24px, etc.).
- Use constraints (max-width containers) to prevent content from stretching too wide on large screens.

### 5. Micro-Interactions
- Add `:hover` states to all interactive elements.
- Use `transition: all 0.3s ease;` for smooth state changes.
- Consider subtle entrance animations for main content.

## Checklist for Every Output
- [ ] Is the design responsive?
- [ ] Does it have a working Light/Dark toggle?
- [ ] Are colors and fonts modern and accessible?
- [ ] Is the code clean and semantic?
