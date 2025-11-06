# PM Module Debug Engine

A centralized, categorized debug logging system for the PM module that can be enabled/disabled for performance testing.

## Features

- **Zero overhead when disabled**: All debug calls are no-ops when disabled
- **Categorized logging**: Different categories for different types of logs (time, api, filter, state, render, dnd, storage, project, task, column)
- **Performance timing**: Built-in timing utilities for measuring performance
- **Configurable**: Enable/disable via localStorage or programmatically
- **Browser console access**: Exposed via `window.pmDebug` for easy access

## Usage

### Basic Usage

```typescript
import { debug } from '~/app/pm/utils/debug';

// Time logs
debug.time('Component rendered');
debug.timeStart('fetch-tasks');
// ... do work ...
debug.timeEnd('fetch-tasks', 'Tasks fetched');

// API logs
debug.api('Fetching tasks', { projectId: '123' });

// Filter logs
debug.filter('Filtering tasks', { count: tasks.length });

// State logs
debug.state('State updated', { newState });

// Render logs
debug.render('Component rendered');

// DnD logs
debug.dnd('Drag started', { taskId });

// Storage logs
debug.storage('Saved to localStorage', { key, value });

// Project logs
debug.project('Project changed', { projectId });

// Task logs
debug.task('Task updated', { taskId, status });

// Column logs
debug.column('Column reordered', { columnId });

// Warnings and errors (always shown if debug is enabled)
debug.warn('Warning message', { data });
debug.error('Error message', { error });
```

## Categories

- `time` - Performance timing logs
- `api` - API request/response logs
- `filter` - Data filtering operations
- `state` - State management logs
- `render` - Component rendering logs
- `dnd` - Drag and drop operations
- `storage` - LocalStorage operations
- `project` - Project switching and logic
- `task` - Task-related operations
- `column` - Column/status operations
- `all` - All categories (default)

## Enabling/Disabling Debug

### Via Browser Console

```javascript
// Enable all categories
window.pmDebug.enable();

// Enable specific categories
window.pmDebug.enable(['time', 'api', 'filter']);

// Disable
window.pmDebug.disable();

// Set specific categories
window.pmDebug.setCategories(['time', 'api']);

// Add categories
window.pmDebug.addCategories(['filter']);

// Remove categories
window.pmDebug.removeCategories(['time']);

// Get current config
window.pmDebug.getConfig();

// Reload config from localStorage
window.pmDebug.reload();
```

### Via localStorage

```javascript
// Enable debug
localStorage.setItem('pm:debug:enabled', 'true');

// Set categories (JSON array)
localStorage.setItem('pm:debug:categories', '["time","api","filter"]');

// Disable timestamps
localStorage.setItem('pm:debug:timestamp', 'false');

// Disable performance timing
localStorage.setItem('pm:debug:performance', 'false');

// Disable debug
localStorage.setItem('pm:debug:enabled', 'false');
```

### Programmatically

```typescript
import { enableDebug, disableDebug, debug } from '~/app/pm/utils/debug';

// Enable all categories
enableDebug();

// Enable specific categories
enableDebug(['time', 'api', 'filter']);

// Disable
disableDebug();

// Set categories
debug.setCategories(['time', 'api']);

// Add categories
debug.addCategories(['filter']);

// Remove categories
debug.removeCategories(['time']);
```

## Performance

When debug is disabled, all debug calls are no-ops with zero overhead. The `isEnabled()` check is fast and happens before any string formatting or data processing.

## Development Mode

In development mode, the debug engine automatically reloads configuration from localStorage every 2 seconds, allowing you to toggle debug on/off without refreshing the page.

## Examples

### Enable only API and time logs

```javascript
window.pmDebug.enable(['api', 'time']);
```

### Enable all logs except render

```javascript
window.pmDebug.enable();
window.pmDebug.removeCategories(['render']);
```

### Measure performance

```typescript
debug.timeStart('task-filtering');
// ... filter tasks ...
debug.timeEnd('task-filtering', 'Tasks filtered');
// Output: ⏱️ [TIME] Tasks filtered (took 12.34ms)
```

## Default Behavior

- Debug is **disabled by default** for performance
- When enabled, all categories are enabled by default
- Timestamps are enabled by default
- Performance timing is enabled by default

