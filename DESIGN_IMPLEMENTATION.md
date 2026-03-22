# HelpWriter Web — ТЗ на редизайн (для имплементации)

**Версия:** 2.0
**Дата:** 22 марта 2026

***

## 1. Цель

Обновить UI веб-редактора HelpWriter:

* Новая тёплая цветовая палитра (молочный фон, золотистый акцент)
* Шрифт Lora для редактора, Inter для UI
* Классический WYSIWYG редактор (НЕ блочный)
* Dark mode first-class

***

## 2. Цветовая палитра

### CSS переменные

```css
:root {
  /* Core palette */
  --ink: #1C1919;
  --accent: #D1AC88;
  --accent-light: #D5C1A9;
  --paper: #EBE7E3;
  --white: #FFFFFF;

  /* Semantic colors */
  --bg-primary: #EBE7E3;
  --bg-secondary: #F5F2EF;
  --bg-elevated: #FFFFFF;

  --text-primary: #1C1919;
  --text-secondary: #5C5856;
  --text-tertiary: #8A8785;

  --border-color: #D5C1A9;
  --border-light: #E5E0DB;

  --accent-hover: #C4A07B;
  --accent-active: #B7946E;

  /* Mode colors */
  --mode-transcription: #5B8C6A;
  --mode-structure: #6B8CAF;
  --mode-ideas: #C4976B;

  /* Shadows */
  --shadow-sm: 0 1px 3px rgba(28, 25, 25, 0.06);
  --shadow-md: 0 4px 12px rgba(28, 25, 25, 0.08);
  --shadow-lg: 0 8px 24px rgba(28, 25, 25, 0.12);

  /* Transitions */
  --transition-fast: 150ms ease;
  --transition-base: 200ms ease;
  --transition-slow: 300ms ease;

  /* Spacing */
  --sidebar-width: 300px;
  --editor-max-width: 680px;

  /* Radius */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
}

/* Dark mode */
[data-theme="dark"] {
  --bg-primary: #1A1816;
  --bg-secondary: #242220;
  --bg-elevated: #2A2826;

  --text-primary: #F5F2EF;
  --text-secondary: #A8A5A2;
  --text-tertiary: #6B6866;

  --border-color: #3A3836;
  --border-light: #2F2D2B;

  --accent: #D1AC88;
  --accent-hover: #DAB894;
  --accent-light: rgba(209, 172, 136, 0.15);

  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.2);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.3);
  --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.4);
}
```

***

## 3. Шрифты

### Подключение (index.html)

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
```

### CSS переменные

```css
:root {
  --font-editor: "Lora", "Georgia", "Times New Roman", serif;
  --font-ui: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --font-mono: "JetBrains Mono", "SF Mono", "Fira Code", monospace;
}
```

***

## 4. Файлы для изменения

### 4.1 index.css (глобальные стили)

**Путь:** `web/src/index.css`

**Задачи:**

* [ ] Заменить CSS переменные на новые (из секции 2)
* [ ] Добавить импорт шрифтов или подключить в index.html
* [ ] Добавить стили для dark mode (`[data-theme="dark"]`)
* [ ] Изменить `body` background на `var(--bg-primary)`

### 4.2 Sidebar.css

**Путь:** `web/src/components/Sidebar.css`

**Задачи:**

* [ ] Изменить фон sidebar на `var(--bg-secondary)`
* [ ] Изменить border на `var(--border-color)`
* [ ] Обновить стили document cards (см. секцию 5)
* [ ] Добавить группировку по дате (см. секцию 6)
* [ ] Обновить context menu стили
* [ ] Добавить staggered animation для карточек

### 4.3 Sidebar.jsx

**Путь:** `web/src/components/Sidebar.jsx`

**Задачи:**

* [ ] Добавить группировку документов по дате (Today, Yesterday, This Week, Older)
* [ ] Обновить структуру document card (preview text, footer с mode badge)
* [ ] Добавить search input в header
* [ ] Добавить theme toggle кнопку

### 4.4 Editor.css

**Путь:** `web/src/components/Editor.css`

**Задачи:**

* [ ] Изменить шрифт редактора на `var(--font-editor)` (Lora)
* [ ] Изменить фон на `var(--bg-primary)`
* [ ] Обновить стили для editor content wrapper (белая карточка с тенью)
* [ ] Упростить тулбар (см. секцию 7)
* [ ] Обновить типографику (размеры, отступы)
* [ ] Добавить bubble menu стили

### 4.5 Editor.jsx

**Путь:** `web/src/components/Editor.jsx`

**Задачи:**

* [ ] Заменить фиксированный тулбар на минимальный (back, mode badge, save status)
* [ ] Добавить bubble menu для форматирования (появляется при выделении текста)
* [ ] Убрать dropdown меню для heading/list — перенести в bubble menu
* [ ] Сохранить всю текущую функциональность (auto-save, Ctrl+S, форматирование)

### 4.6 EditorPage.css

**Путь:** `web/src/pages/EditorPage.css`

**Задачи:**

* [ ] Изменить layout (sidebar + editor)
* [ ] Изменить фон страницы на `var(--bg-primary)`
* [ ] Добавить responsive стили для mobile

### 4.7 Новый файл: ThemeContext.jsx

**Путь:** `web/src/contexts/ThemeContext.jsx`

**Задачи:**

* [ ] Создать React Context для темы
* [ ] Реализовать toggle (light/dark)
* [ ] Сохранять выбор в localStorage
* [ ] Применять `data-theme` атрибут к `document.documentElement`

### 4.8 index.html

**Путь:** `web/index.html`

**Задачи:**

* [ ] Добавить Google Fonts ссылку в `<head>`

***

## 5. Document Card (новый дизайн)

### Структура

```jsx
<div className="doc-card">
  <div className="doc-card-header">
    <span className="doc-mode-icon">💡</span>
    <span className="doc-title">Идеи для статьи</span>
    <span className="doc-time">10:30</span>
  </div>
  <div className="doc-preview">
    Первый вариант: написать про то, как экономить...
  </div>
  <div className="doc-card-footer">
    <span className="mode-badge mode-badge--ideas">💡 ideas</span>
    <span className="doc-duration">🎤 45 сек</span>
  </div>
</div>
```

### CSS

```css
.doc-card {
  background: var(--bg-elevated);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  padding: 12px 14px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all var(--transition-base);
}

.doc-card:hover {
  box-shadow: var(--shadow-md);
  border-color: var(--border-color);
}

.doc-card.active {
  border-left: 3px solid var(--accent);
  background: rgba(209, 172, 136, 0.08);
}

.doc-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.doc-title {
  flex: 1;
  font-family: var(--font-ui);
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.doc-time {
  font-size: 12px;
  color: var(--text-tertiary);
}

.doc-preview {
  font-family: var(--font-ui);
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 8px;
}

.doc-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 8px;
  border-top: 1px solid var(--border-light);
}

.doc-duration {
  font-size: 12px;
  color: var(--text-tertiary);
}
```

***

## 6. Группировка по дате

### Логика

```javascript
function groupDocumentsByDate(documents) {
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)
  const weekAgo = new Date(today)
  weekAgo.setDate(weekAgo.getDate() - 7)

  const groups = {
    today: [],
    yesterday: [],
    thisWeek: [],
    older: []
  }

  documents.forEach(doc => {
    const docDate = new Date(doc.created_at)
    if (docDate >= today) {
      groups.today.push(doc)
    } else if (docDate >= yesterday) {
      groups.yesterday.push(doc)
    } else if (docDate >= weekAgo) {
      groups.thisWeek.push(doc)
    } else {
      groups.older.push(doc)
    }
  })

  return groups
}

const DATE_LABELS = {
  today: 'Сегодня',
  yesterday: 'Вчера',
  thisWeek: 'На этой неделе',
  older: 'Ранее'
}
```

### CSS

```css
.date-group {
  margin-bottom: 16px;
}

.date-group-title {
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 500;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 8px 4px;
  margin-bottom: 4px;
}
```

***

## 7. Редактор (изменения)

### Минимальный тулбар

Вместо текущего громоздкого тулбара сделать:

```jsx
<div className="editor-toolbar">
  <button className="back-btn" onClick={onBack}>
    <ArrowLeft size={16} />
    <span>{viewTitle}</span>
  </button>

  <div className="toolbar-center">
    <span className={`mode-badge mode-badge--${doc.mode}`}>
      {MODE_ICONS[doc.mode]} {doc.mode}
    </span>
  </div>

  <div className="toolbar-right">
    <SaveStatus status={saveStatus} />
  </div>
</div>
```

### Bubble Menu

Добавить всплывающее меню при выделении текста:

```jsx
{editor && (
  <BubbleMenu editor={editor} tippyOptions={{ duration: 150 }}>
    <div className="bubble-menu">
      <button
        onClick={() => editor.chain().focus().toggleBold().run()}
        className={editor.isActive('bold') ? 'active' : ''}
      >
        <Bold size={16} />
      </button>
      <button
        onClick={() => editor.chain().focus().toggleItalic().run()}
        className={editor.isActive('italic') ? 'active' : ''}
      >
        <Italic size={16} />
      </button>
      {/* ... other formatting buttons */}
    </div>
  </BubbleMenu>
)}
```

### CSS для редактора

```css
.editor-page {
  flex: 1;
  background: var(--bg-primary);
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  position: sticky;
  top: 0;
  z-index: 10;
}

.editor-container {
  flex: 1;
  padding: 32px 24px;
  overflow-y: auto;
}

.editor-content-wrapper {
  max-width: var(--editor-max-width);
  margin: 0 auto;
  background: var(--bg-elevated);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  padding: 48px 56px;
  min-height: 500px;
}

.tiptap {
  font-family: var(--font-editor);
  font-size: 18px;
  line-height: 1.8;
  color: var(--text-primary);
  outline: none;
}

.tiptap h1 {
  font-family: var(--font-editor);
  font-size: 2.25rem;
  font-weight: 700;
  margin: 1.5em 0 0.5em;
  letter-spacing: -0.015em;
  line-height: 1.25;
}

.tiptap h2 {
  font-family: var(--font-editor);
  font-size: 1.625rem;
  font-weight: 600;
  margin: 1.25em 0 0.5em;
}

.tiptap h3 {
  font-family: var(--font-editor);
  font-size: 1.25rem;
  font-weight: 600;
  margin: 1em 0 0.5em;
}

.tiptap blockquote {
  border-left: 3px solid var(--accent);
  padding-left: 1.25em;
  margin: 1.25em 0;
  color: var(--text-secondary);
  font-style: italic;
}

.tiptap code {
  font-family: var(--font-mono);
  font-size: 0.9em;
  background: var(--bg-secondary);
  padding: 0.2em 0.4em;
  border-radius: 4px;
  color: #B85450;
}

.tiptap mark {
  background: rgba(209, 172, 136, 0.35);
  padding: 0.1em 0.2em;
  border-radius: 3px;
}

.tiptap a {
  color: var(--accent);
  text-decoration: underline;
  text-underline-offset: 2px;
}
```

***

## 8. Mode Badges

```css
.mode-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 4px;
  font-family: var(--font-ui);
  font-size: 11px;
  font-weight: 500;
  text-transform: lowercase;
}

.mode-badge--transcription {
  background: rgba(91, 140, 106, 0.12);
  color: var(--mode-transcription);
}

.mode-badge--structure {
  background: rgba(107, 140, 175, 0.12);
  color: var(--mode-structure);
}

.mode-badge--ideas {
  background: rgba(196, 151, 107, 0.15);
  color: var(--mode-ideas);
}
```

***

## 9. Анимации

```css
/* Staggered card reveal */
@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.doc-card {
  animation: slideUp 0.35s ease-out;
  animation-fill-mode: both;
}

.doc-card:nth-child(1) { animation-delay: 0ms; }
.doc-card:nth-child(2) { animation-delay: 40ms; }
.doc-card:nth-child(3) { animation-delay: 80ms; }
.doc-card:nth-child(4) { animation-delay: 120ms; }
.doc-card:nth-child(5) { animation-delay: 160ms; }
.doc-card:nth-child(6) { animation-delay: 200ms; }
```

***

## 10. Responsive (Mobile)

```css
@media (max-width: 767px) {
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    z-index: 100;
    transform: translateX(-100%);
    transition: transform var(--transition-slow);
  }

  .sidebar.open {
    transform: translateX(0);
  }

  .editor-content-wrapper {
    padding: 24px 20px;
    border-radius: 0;
    box-shadow: none;
    background: var(--bg-primary);
  }
}
```

***

## 11. План имплементации

### Фаза 1: Foundation (приоритет: высокий)

* [ ] Обновить CSS переменные в `index.css`
* [ ] Добавить Google Fonts в `index.html`
* [ ] Создать `ThemeContext.jsx` для dark mode
* [ ] Обновить базовые цвета во всех компонентах

### Фаза 2: Sidebar (приоритет: высокий)

* [ ] Обновить `Sidebar.css` с новыми цветами
* [ ] Добавить группировку документов по дате в `Sidebar.jsx`
* [ ] Обновить document card дизайн
* [ ] Добавить search input
* [ ] Добавить theme toggle

### Фаза 3: Editor (приоритет: высокий)

* [ ] Обновить `Editor.css` — шрифт Lora, новые цвета
* [ ] Упростить тулбар (минимальный)
* [ ] Добавить bubble menu
* [ ] Обновить editor content wrapper (белая карточка)

### Фаза 4: Polish (приоритет: средний)

* [ ] Добавить анимации (staggered reveal)
* [ ] Responsive стили для mobile
* [ ] Empty states
* [ ] Финальная проверка dark mode

***

## 12. Важно сохранить

* Auto-save через 2 секунды после изменений
* Ctrl+S для ручного сохранения
* Все TipTap расширения (Bold, Italic, Heading, Lists, etc.)
* Folder CRUD (создание, переименование, удаление)
* Перемещение документов между папками
* Удаление документов (soft delete)
* Поиск по документам
* Классический WYSIWYG (НЕ блочный редактор!)

***

## 13. Иконки

Использовать **Lucide React**:

```bash
npm install lucide-react
```

```jsx
import {
  Search, Plus, Trash2, FolderOpen, ChevronRight, ChevronDown,
  MoreHorizontal, ArrowLeft, LogOut, Sun, Moon,
  Bold, Italic, Underline, Strikethrough, Code,
  List, ListOrdered, Quote, Link2, Highlighter,
  Check, Loader2, Mic
} from 'lucide-react'
```

***

*ТЗ готово для имплементации в Claude Code*