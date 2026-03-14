import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import TextAlign from '@tiptap/extension-text-align'
import Highlight from '@tiptap/extension-highlight'
import Link from '@tiptap/extension-link'
import Superscript from '@tiptap/extension-superscript'
import Subscript from '@tiptap/extension-subscript'
import { useEffect, useCallback, useRef, useState } from 'react'
import './Editor.css'

function Btn({ onClick, active, title, children }) {
  return (
    <button
      onMouseDown={(e) => { e.preventDefault(); onClick() }}
      className={`fmt-btn${active ? ' active' : ''}`}
      title={title}
    >{children}</button>
  )
}

function Sep() {
  return <div className="toolbar-sep" />
}

function Dropdown({ label, open, setOpen, children, btnRef }) {
  return (
    <div className="toolbar-dropdown" ref={btnRef}>
      <button
        className="fmt-btn dropdown-toggle"
        onMouseDown={(e) => { e.preventDefault(); setOpen(o => !o) }}
      >
        {label} <span className="dropdown-arrow">▾</span>
      </button>
      {open && <div className="dropdown-menu">{children}</div>}
    </div>
  )
}

export default function Editor({ content, onSave, onChange, saving }) {
  const [headingOpen, setHeadingOpen] = useState(false)
  const [listOpen, setListOpen] = useState(false)
  const headingRef = useRef(null)
  const listRef = useRef(null)
  const autoSaveTimer = useRef(null)

  const editor = useEditor({
    extensions: [
      StarterKit,
      Underline,
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      Highlight.configure({ multicolor: false }),
      Link.configure({ openOnClick: false }),
      Superscript,
      Subscript,
    ],
    content,
    editorProps: {
      attributes: { class: 'editor-content' },
    },
    onUpdate({ editor }) {
      const html = editor.getHTML()
      if (onChange) onChange(html)
      // Debounced auto-save: 2s after last keystroke
      clearTimeout(autoSaveTimer.current)
      autoSaveTimer.current = setTimeout(() => {
        onSave(html)
      }, 2000)
    },
  })

  // Cleanup timer on unmount
  useEffect(() => {
    return () => clearTimeout(autoSaveTimer.current)
  }, [])

  useEffect(() => {
    if (editor && content !== editor.getHTML()) {
      editor.commands.setContent(content)
    }
  }, [content])

  const handleSave = useCallback(() => {
    if (editor) {
      clearTimeout(autoSaveTimer.current)
      onSave(editor.getHTML())
    }
  }, [editor, onSave])

  useEffect(() => {
    const handler = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        handleSave()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [handleSave])

  // Close dropdowns on outside click
  useEffect(() => {
    const handler = (e) => {
      if (headingRef.current && !headingRef.current.contains(e.target)) setHeadingOpen(false)
      if (listRef.current && !listRef.current.contains(e.target)) setListOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleLink = useCallback(() => {
    if (!editor) return
    const prev = editor.getAttributes('link').href
    const url = window.prompt('URL ссылки:', prev || 'https://')
    if (url === null) return
    if (url === '') {
      editor.chain().focus().unsetLink().run()
    } else {
      editor.chain().focus().setLink({ href: url }).run()
    }
  }, [editor])

  const headingLabel = () => {
    if (!editor) return 'H'
    if (editor.isActive('heading', { level: 1 })) return 'H1'
    if (editor.isActive('heading', { level: 2 })) return 'H2'
    if (editor.isActive('heading', { level: 3 })) return 'H3'
    return 'P'
  }

  if (!editor) return null

  return (
    <div className="editor-wrapper">
      <div className="editor-toolbar">
        <div className="format-btns">

          {/* Undo / Redo */}
          <Btn onClick={() => editor.chain().focus().undo().run()} title="Отменить (Ctrl+Z)">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 7v6h6"/><path d="M3 13a9 9 0 1 0 2.83-6.36L3 9"/></svg>
          </Btn>
          <Btn onClick={() => editor.chain().focus().redo().run()} title="Повторить (Ctrl+Y)">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 7v6h-6"/><path d="M21 13a9 9 0 1 1-2.83-6.36L21 9"/></svg>
          </Btn>

          <Sep />

          {/* Heading dropdown */}
          <Dropdown
            label={headingLabel()}
            open={headingOpen}
            setOpen={setHeadingOpen}
            btnRef={headingRef}
          >
            <button className="dropdown-item" onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().setParagraph().run(); setHeadingOpen(false) }}>
              <span className="di-p">Текст</span>
            </button>
            <button className="dropdown-item" onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().toggleHeading({ level: 1 }).run(); setHeadingOpen(false) }}>
              <span className="di-h1">Заголовок 1</span>
            </button>
            <button className="dropdown-item" onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().toggleHeading({ level: 2 }).run(); setHeadingOpen(false) }}>
              <span className="di-h2">Заголовок 2</span>
            </button>
            <button className="dropdown-item" onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().toggleHeading({ level: 3 }).run(); setHeadingOpen(false) }}>
              <span className="di-h3">Заголовок 3</span>
            </button>
          </Dropdown>

          {/* List dropdown */}
          <Dropdown
            label={
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="9" y1="6" x2="20" y2="6"/><line x1="9" y1="12" x2="20" y2="12"/><line x1="9" y1="18" x2="20" y2="18"/><circle cx="4" cy="6" r="1.5" fill="currentColor" stroke="none"/><circle cx="4" cy="12" r="1.5" fill="currentColor" stroke="none"/><circle cx="4" cy="18" r="1.5" fill="currentColor" stroke="none"/></svg>
            }
            open={listOpen}
            setOpen={setListOpen}
            btnRef={listRef}
          >
            <button className="dropdown-item" onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().toggleBulletList().run(); setListOpen(false) }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="4" cy="7" r="1.5" fill="currentColor" stroke="none"/><circle cx="4" cy="12" r="1.5" fill="currentColor" stroke="none"/><circle cx="4" cy="17" r="1.5" fill="currentColor" stroke="none"/><line x1="8" y1="7" x2="20" y2="7"/><line x1="8" y1="12" x2="20" y2="12"/><line x1="8" y1="17" x2="20" y2="17"/></svg>
              &nbsp; Маркированный
            </button>
            <button className="dropdown-item" onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().toggleOrderedList().run(); setListOpen(false) }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><text x="2" y="9" fontSize="8" fill="currentColor" stroke="none">1.</text><text x="2" y="15" fontSize="8" fill="currentColor" stroke="none">2.</text><text x="2" y="21" fontSize="8" fill="currentColor" stroke="none">3.</text><line x1="10" y1="7" x2="21" y2="7"/><line x1="10" y1="13" x2="21" y2="13"/><line x1="10" y1="19" x2="21" y2="19"/></svg>
              &nbsp; Нумерованный
            </button>
          </Dropdown>

          {/* Outdent / Indent */}
          <Btn onClick={() => editor.chain().focus().liftListItem('listItem').run()} title="Уменьшить отступ">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="21" y1="6" x2="3" y2="6"/><line x1="21" y1="12" x2="9" y2="12"/><line x1="21" y1="18" x2="3" y2="18"/><polyline points="5 9 2 12 5 15"/></svg>
          </Btn>
          <Btn onClick={() => editor.chain().focus().sinkListItem('listItem').run()} title="Увеличить отступ">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="21" y1="6" x2="3" y2="6"/><line x1="21" y1="12" x2="9" y2="12"/><line x1="21" y1="18" x2="3" y2="18"/><polyline points="7 9 10 12 7 15"/></svg>
          </Btn>

          <Sep />

          {/* Text formatting */}
          <Btn onClick={() => editor.chain().focus().toggleBold().run()} active={editor.isActive('bold')} title="Жирный (Ctrl+B)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M6 4h8a4 4 0 0 1 4 4 4 4 0 0 1-4 4H6z"/><path d="M6 12h9a4 4 0 0 1 4 4 4 4 0 0 1-4 4H6z"/></svg>
          </Btn>
          <Btn onClick={() => editor.chain().focus().toggleItalic().run()} active={editor.isActive('italic')} title="Курсив (Ctrl+I)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><line x1="19" y1="4" x2="10" y2="4"/><line x1="14" y1="20" x2="5" y2="20"/><line x1="15" y1="4" x2="9" y2="20"/></svg>
          </Btn>
          <Btn onClick={() => editor.chain().focus().toggleStrike().run()} active={editor.isActive('strike')} title="Зачёркнутый">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.3 4.9c-2.3-.6-4.4-1-6.2-.9-2.7 0-5.3.7-5.3 3.6 0 1.5 1.8 3.3 5 3.8h1.2"/><path d="M21 12H3"/><path d="M7 19.4c2.3.6 4.4 1 6.2.9 2.7 0 5.3-.7 5.3-3.6 0-1.5-1.8-3.3-5-3.8h-1.2"/></svg>
          </Btn>
          <Btn onClick={() => editor.chain().focus().toggleCode().run()} active={editor.isActive('code')} title="Код">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
          </Btn>
          <Btn onClick={() => editor.chain().focus().toggleUnderline().run()} active={editor.isActive('underline')} title="Подчёркнутый (Ctrl+U)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 3v7a6 6 0 0 0 6 6 6 6 0 0 0 6-6V3"/><line x1="4" y1="21" x2="20" y2="21"/></svg>
          </Btn>
          <Btn onClick={() => editor.chain().focus().toggleHighlight().run()} active={editor.isActive('highlight')} title="Выделение цветом">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m9 11-6 6v3h9l3-3"/><path d="m22 12-4.6 4.6a2 2 0 0 1-2.8 0l-5.2-5.2a2 2 0 0 1 0-2.8L14 4"/></svg>
          </Btn>
          <Btn onClick={handleLink} active={editor.isActive('link')} title="Ссылка">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
          </Btn>

          <Sep />

          {/* Superscript / Subscript */}
          <Btn onClick={() => editor.chain().focus().toggleSuperscript().run()} active={editor.isActive('superscript')} title="Верхний индекс">
            x<sup style={{fontSize:'0.65em'}}>2</sup>
          </Btn>
          <Btn onClick={() => editor.chain().focus().toggleSubscript().run()} active={editor.isActive('subscript')} title="Нижний индекс">
            x<sub style={{fontSize:'0.65em'}}>2</sub>
          </Btn>

          <Sep />

          {/* Text alignment */}
          <Btn onClick={() => editor.chain().focus().setTextAlign('left').run()} active={editor.isActive({ textAlign: 'left' })} title="По левому краю">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="15" y2="12"/><line x1="3" y1="18" x2="18" y2="18"/></svg>
          </Btn>
          <Btn onClick={() => editor.chain().focus().setTextAlign('center').run()} active={editor.isActive({ textAlign: 'center' })} title="По центру">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="6" y1="12" x2="18" y2="12"/><line x1="4" y1="18" x2="20" y2="18"/></svg>
          </Btn>
          <Btn onClick={() => editor.chain().focus().setTextAlign('right').run()} active={editor.isActive({ textAlign: 'right' })} title="По правому краю">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="9" y1="12" x2="21" y2="12"/><line x1="6" y1="18" x2="21" y2="18"/></svg>
          </Btn>
          <Btn onClick={() => editor.chain().focus().setTextAlign('justify').run()} active={editor.isActive({ textAlign: 'justify' })} title="По ширине">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
          </Btn>

          <Sep />

          {/* Blockquote */}
          <Btn onClick={() => editor.chain().focus().toggleBlockquote().run()} active={editor.isActive('blockquote')} title="Цитата">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2H4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V20c0 1 0 1 1 1z"/><path d="M15 21c3 0 7-1 7-8V5c0-1.25-.757-2.017-2-2h-4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2h.75c0 2.25.25 4-2.75 4v3c0 1 0 1 1 1z"/></svg>
          </Btn>
        </div>

        <div className="toolbar-right">
          <button onClick={handleSave} disabled={saving} className="save-btn">
            {saving ? 'Сохранение...' : 'Сохранить'}
          </button>
          <span className="shortcut-hint">Ctrl+S</span>
        </div>
      </div>
      <EditorContent editor={editor} />
    </div>
  )
}
