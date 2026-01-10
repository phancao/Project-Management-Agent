# Galaxy AI Design System

A comprehensive UI style guide for the Project Management Agent application.

---

## Color System

### Configurable Accent Colors
The primary accent color is user-configurable via **Settings → Appearance**.

| Theme | Primary Gradient | Shadow | Usage |
|-------|-----------------|--------|-------|
| **Indigo** (default) | `from-indigo-500 to-violet-600` | `shadow-indigo-500/30` | Primary actions, headers |
| **Blue** | `from-blue-500 to-cyan-600` | `shadow-blue-500/30` | Alternative primary |
| **Purple** | `from-purple-500 to-pink-600` | `shadow-purple-500/30` | Creative contexts |
| **Emerald** | `from-emerald-500 to-teal-600` | `shadow-emerald-500/30` | Success, growth |
| **Amber** | `from-amber-500 to-orange-600` | `shadow-amber-500/30` | Warm, attention |
| **Rose** | `from-rose-500 to-pink-600` | `shadow-rose-500/30` | Soft, feminine |

### Semantic Colors
```css
/* Success */
bg-emerald-500, text-emerald-600 dark:text-emerald-400

/* Warning */
bg-amber-500, text-amber-600 dark:text-amber-400

/* Error/Danger */
bg-red-500, text-red-600 dark:text-red-400

/* Info */
bg-blue-500, text-blue-600 dark:text-blue-400
```

### Theme Support
All components must support both light and dark themes:
```tsx
// Light theme
className="bg-white text-gray-900"

// Dark theme additions
className="dark:bg-slate-900 dark:text-white"
```

---

## Typography

### Font Stack
```css
font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
```

### Scale
| Size | Class | Usage |
|------|-------|-------|
| 2XL | `text-2xl font-bold` | Page titles |
| XL | `text-xl font-semibold` | Section headers |
| LG | `text-lg font-medium` | Card titles |
| Base | `text-base` | Body text |
| SM | `text-sm` | Descriptions, metadata |
| XS | `text-xs` | Labels, badges |

---

## Components

### Cards
Premium cards use glassmorphism with subtle shadows:

```tsx
// Standard Card
<div className="bg-white dark:bg-slate-900 rounded-xl border border-gray-200 dark:border-slate-700/50 shadow-sm">

// Premium Card (featured content)
<div className="bg-white dark:bg-gradient-to-br dark:from-slate-900 dark:to-slate-800 rounded-2xl shadow-xl dark:shadow-2xl p-6">

// Glassmorphic Card
<div className="bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm rounded-xl border border-gray-200/50 dark:border-slate-700/50">
```

### Buttons

```tsx
// Primary Button (uses accent color)
<Button className="bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-600 hover:to-violet-700 text-white shadow-lg shadow-indigo-500/30">

// Secondary Button
<Button variant="outline" className="border-gray-200 dark:border-slate-700">

// Ghost Button
<Button variant="ghost">

// Danger Button
<Button className="bg-red-500 hover:bg-red-600 text-white">
```

### Badges

```tsx
// Default Badge
<Badge className="bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-slate-300">

// Accent Badge
<Badge className="bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-lg shadow-indigo-500/30">

// Status Badges
<Badge className="bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">  // Success
<Badge className="bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">      // Warning
<Badge className="bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">              // Error
```

### Avatars

```tsx
// User Avatar with gradient fallback
<div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white font-bold shadow-lg shadow-indigo-500/25">
  {initials}
</div>
```

### Loading States

Use `WorkspaceLoading` component for consistent loading UI:
```tsx
import { WorkspaceLoading, InlineLoading } from "~/components/ui/workspace-loading";

// Full loading state
<WorkspaceLoading
  title="Loading..."
  subtitle="Please wait..."
  items={[
    { label: "Data", isLoading: true },
  ]}
/>

// Inline loading
<InlineLoading message="Loading..." />
```

---

## Effects

### Shadows
```css
/* Standard */
shadow-sm, shadow-md, shadow-lg

/* Colored shadows (use accent color) */
shadow-lg shadow-indigo-500/30

/* Dark mode enhanced */
dark:shadow-2xl dark:shadow-indigo-500/10
```

### Gradients
```css
/* Header/accent gradient */
bg-gradient-to-r from-indigo-500 to-violet-600

/* Background gradient */
bg-gradient-to-br from-slate-50 via-white to-indigo-50/30
dark:bg-gradient-to-br dark:from-slate-900 dark:to-slate-800

/* Text gradient */
bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent
```

### Animations
```css
/* Hover scale */
transition-transform hover:scale-105

/* Fade in */
animate-in fade-in duration-300

/* Slide in */
animate-in slide-in-from-bottom-4 duration-300

/* Pulse (for attention) */
animate-pulse
```

---

## Layout

### Spacing Scale
- `gap-1` / `p-1`: 4px - Tight spacing
- `gap-2` / `p-2`: 8px - Compact
- `gap-3` / `p-3`: 12px - Default
- `gap-4` / `p-4`: 16px - Comfortable
- `gap-6` / `p-6`: 24px - Relaxed
- `gap-8` / `p-8`: 32px - Section spacing

### Container Widths
```css
max-w-sm   /* 384px - Dialogs, loading cards */
max-w-md   /* 448px - Small modals */
max-w-lg   /* 512px - Medium content */
max-w-xl   /* 576px - Large content */
max-w-2xl  /* 672px - Wide content */
max-w-7xl  /* 1280px - Page container */
```

### Responsive Patterns
```tsx
// Mobile-first responsive grid
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">

// Responsive flex
<div className="flex flex-col md:flex-row gap-4">
```

---

## Best Practices

### DO ✅
- Use `cn()` for conditional class merging
- Always include `dark:` variants for theme support
- Use semantic color names (emerald for success, red for error)
- Apply consistent border radius (`rounded-xl` for cards, `rounded-lg` for buttons)
- Use gradient buttons for primary actions
- Add colored shadows to accent elements

### DON'T ❌
- Hardcode hex colors (use Tailwind classes)
- Forget dark mode variants
- Use flat colors for primary actions (use gradients)
- Mix border radius sizes inconsistently
- Skip loading states

---

## Implementation Checklist

When creating new UI components:
1. [ ] Supports light and dark themes
2. [ ] Uses configurable accent color from settings
3. [ ] Includes proper loading states
4. [ ] Has consistent spacing and typography
5. [ ] Uses gradient buttons for primary actions
6. [ ] Has colored shadows on accent elements
7. [ ] Is responsive (mobile-first)
