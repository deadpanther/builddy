"""
Pre-built Tailwind component reference library.

These patterns are injected into code generation prompts so the AI COMPOSES
from proven, polished patterns rather than inventing everything from scratch.
Each pattern is minimal but demonstrates the quality bar: dark mode, animations,
proper spacing, accessibility, and visual polish.
"""

COMPONENT_LIBRARY = """
## COMPONENT REFERENCE LIBRARY
Use these as building blocks. Adapt colors/content to the specific app. Every component
supports dark mode and includes animations.

### 1. App Shell (Header + Content)
```html
<div class="min-h-screen bg-slate-50 dark:bg-slate-950 transition-colors">
  <header class="sticky top-0 z-40 border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md">
    <div class="mx-auto max-w-5xl flex items-center justify-between px-4 h-14">
      <div class="flex items-center gap-3">
        <span class="text-lg font-bold tracking-tight text-slate-900 dark:text-white">AppName</span>
        <nav class="hidden sm:flex items-center gap-1 ml-6">
          <a href="#" class="px-3 py-1.5 text-sm font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">Dashboard</a>
          <a href="#" class="px-3 py-1.5 text-sm font-medium text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-950 rounded-md">Active</a>
        </nav>
      </div>
      <div class="flex items-center gap-2">
        <button onclick="toggleDark()" class="p-2 rounded-lg text-slate-500 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
          <svg class="w-5 h-5 hidden dark:block" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/></svg>
          <svg class="w-5 h-5 dark:hidden" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/></svg>
        </button>
      </div>
    </div>
  </header>
  <main class="mx-auto max-w-5xl px-4 py-8">
    <!-- Page content -->
  </main>
</div>
```

### 2. Stat Cards Row
```html
<div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
  <div class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 shadow-sm hover:shadow-md transition-shadow">
    <p class="text-sm font-medium text-slate-500 dark:text-slate-400">Total Items</p>
    <p class="text-2xl font-bold text-slate-900 dark:text-white mt-1">128</p>
    <p class="text-xs text-emerald-600 dark:text-emerald-400 mt-1 flex items-center gap-1">
      <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18"/></svg>
      +12% from last week
    </p>
  </div>
</div>
```

### 3. Data Card with Actions
```html
<div class="group bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm hover:shadow-md hover:border-primary-300 dark:hover:border-primary-700 transition-all duration-200 animate-fade-in">
  <div class="flex items-start justify-between">
    <div class="flex-1 min-w-0">
      <h3 class="font-semibold text-slate-900 dark:text-white truncate">Card Title</h3>
      <p class="text-sm text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">Description text that may be long and should be truncated after two lines.</p>
    </div>
    <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
      <button class="p-1.5 rounded-lg text-slate-400 hover:text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-950 transition-colors">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
      </button>
      <button class="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950 transition-colors">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
      </button>
    </div>
  </div>
  <div class="flex items-center gap-2 mt-3">
    <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300">Tag</span>
    <span class="text-xs text-slate-400">2 hours ago</span>
  </div>
</div>
```

### 4. Empty State
```html
<div class="flex flex-col items-center justify-center py-16 px-4 animate-fade-in">
  <div class="w-16 h-16 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center mb-4">
    <svg class="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"/></svg>
  </div>
  <h3 class="text-lg font-semibold text-slate-900 dark:text-white">No items yet</h3>
  <p class="text-sm text-slate-500 dark:text-slate-400 mt-1 text-center max-w-sm">Get started by creating your first item. It only takes a few seconds.</p>
  <button class="mt-4 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg shadow-sm hover:shadow transition-all active:scale-95">
    Create your first item
  </button>
</div>
```

### 5. Form Input with Validation
```html
<div class="space-y-1.5">
  <label class="block text-sm font-medium text-slate-700 dark:text-slate-300">Label</label>
  <input type="text" placeholder="Enter value..." class="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-shadow" />
  <p class="text-xs text-red-500 hidden" id="error-msg">This field is required</p>
</div>
```

### 6. Modal Dialog
```html
<div id="modal" class="fixed inset-0 z-50 hidden">
  <div class="fixed inset-0 bg-black/50 backdrop-blur-sm" onclick="closeModal()"></div>
  <div class="fixed inset-0 flex items-center justify-center p-4">
    <div class="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 w-full max-w-md p-6 animate-scale-in">
      <h2 class="text-lg font-bold text-slate-900 dark:text-white">Modal Title</h2>
      <p class="text-sm text-slate-500 mt-2">Modal description text.</p>
      <div class="flex justify-end gap-2 mt-6">
        <button onclick="closeModal()" class="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors">Cancel</button>
        <button class="px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg shadow-sm transition-all active:scale-95">Confirm</button>
      </div>
    </div>
  </div>
</div>
```

### 7. Toast Notification
```html
<div id="toast" class="fixed bottom-4 right-4 z-50 hidden">
  <div class="flex items-center gap-3 px-4 py-3 rounded-xl bg-slate-900 dark:bg-white text-white dark:text-slate-900 shadow-lg animate-slide-up">
    <svg class="w-5 h-5 text-emerald-400 dark:text-emerald-600 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
    <span class="text-sm font-medium" id="toast-msg">Action completed</span>
  </div>
</div>
```

### 8. Search + Filter Bar
```html
<div class="flex flex-col sm:flex-row gap-3 mb-6">
  <div class="relative flex-1">
    <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
    <input type="text" placeholder="Search..." class="w-full pl-10 pr-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-shadow" />
  </div>
  <select class="px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500">
    <option>All</option>
    <option>Active</option>
    <option>Completed</option>
  </select>
</div>
```

### 9. CSS Animations (add to <style>)
```css
@keyframes fade-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
@keyframes scale-in { from { opacity: 0; transform: scale(0.95); } to { opacity: 1; transform: scale(1); } }
@keyframes slide-up { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }
@keyframes shimmer { 0% { background-position: -200% 0; } 100% { background-position: 200% 0; } }
.animate-fade-in { animation: fade-in 0.4s ease-out forwards; }
.animate-scale-in { animation: scale-in 0.2s ease-out forwards; }
.animate-slide-up { animation: slide-up 0.3s ease-out forwards; }
.animate-shimmer { background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.1) 50%, transparent 100%); background-size: 200% 100%; animation: shimmer 1.5s infinite; }
.stagger-1 { animation-delay: 0.05s; opacity: 0; }
.stagger-2 { animation-delay: 0.1s; opacity: 0; }
.stagger-3 { animation-delay: 0.15s; opacity: 0; }
.stagger-4 { animation-delay: 0.2s; opacity: 0; }
.stagger-5 { animation-delay: 0.25s; opacity: 0; }
```

### 10. Dark Mode Toggle Script
```js
function toggleDark() {
  document.documentElement.classList.toggle('dark');
  localStorage.setItem('theme', document.documentElement.classList.contains('dark') ? 'dark' : 'light');
}
// Restore on load
if (localStorage.getItem('theme') === 'dark' || (!localStorage.getItem('theme') && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
  document.documentElement.classList.add('dark');
}
```

### 11. Toast Helper Script
```js
function showToast(message, type = 'success') {
  const toast = document.getElementById('toast');
  const msg = document.getElementById('toast-msg');
  msg.textContent = message;
  toast.classList.remove('hidden');
  setTimeout(() => toast.classList.add('hidden'), 3000);
}
```

### 12. Loading Skeleton
```html
<div class="space-y-4 animate-pulse">
  <div class="h-4 bg-slate-200 dark:bg-slate-800 rounded w-3/4"></div>
  <div class="h-4 bg-slate-200 dark:bg-slate-800 rounded w-1/2"></div>
  <div class="h-32 bg-slate-200 dark:bg-slate-800 rounded-xl"></div>
</div>
```
"""
