import { useEditor, EditorContent, BubbleMenu } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import TextAlign from '@tiptap/extension-text-align'
import Highlight from '@tiptap/extension-highlight'
import Link from '@tiptap/extension-link'
import Superscript from '@tiptap/extension-superscript'
import Subscript from '@tiptap/extension-subscript'
import { useEffect, useCallback, useRef, useState } from 'react'
import {
  ArrowLeft, Bold, Italic, Underline as UnderlineIcon, Strikethrough,
  Code, Link2, Highlighter, Quote, Check, Loader2,
  AlignLeft, AlignCenter, AlignRight
} from 'lucide-react'
import './Editor.css'

const MODE_ICONS = { transcription: '✏️', structure: '📋', ideas: '💡' }
const MODE_DISPLAY_NAMES = {
  transcription: 'транскрипция',
  structure: 'структура',
  ideas: 'идеи',
}

function BubbleBtn({ onClick, active, title, children }) {
  return (
    <button
      onMouseDown={e => { e.preventDefault(); onClick() }}
      className={`bubble-btn${active ? ' active' : ''}`}
      title={title}
    >
      {children}
    </button>
  )
}

function BubbleSep() {
  return <div className="bubble-sep" />
}

function SaveStatus({ saving, savedRecently }) {
  if (saving) {
    return (
      <span className="save-status saving">
        <Loader2 size={13} />
        Сохранение...
      </span>
    )
  }
  if (savedRecently) {
    return (
      <span className="save-status saved">
        <Check size={13} />
        Сохранено
      </span>
    )
  }
  return null
}

export default function Editor({ content, onSave, onChange, saving, mode, onBack, viewTitle }) {
  const autoSaveTimer = useRef(null)
  const prevSavingRef = useRef(false)
  const savedTimerRef = useRef(null)
  const [savedRecently, setSavedRecently] = useState(false)

  // Track saving → saved transition
  useEffect(() => {
    if (prevSavingRef.current && !saving) {
      setSavedRecently(true)
      clearTimeout(savedTimerRef.current)
      savedTimerRef.current = setTimeout(() => setSavedRecently(false), 2000)
    }
    prevSavingRef.current = saving
  }, [saving])

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
      attributes: { class: 'tiptap' },
    },
    onUpdate({ editor }) {
      const html = editor.getHTML()
      if (onChange) onChange(html)
      clearTimeout(autoSaveTimer.current)
      autoSaveTimer.current = setTimeout(() => onSave(html), 2000)
    },
  })

  useEffect(() => {
    return () => {
      clearTimeout(autoSaveTimer.current)
      clearTimeout(savedTimerRef.current)
    }
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

  // Ctrl+S
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

  if (!editor) return null

  return (
    <div className="editor-wrapper">
      {/* ── Minimal toolbar ── */}
      <div className="editor-toolbar">
        <button className="back-btn" onClick={onBack} title="Назад">
          <ArrowLeft size={16} />
          <span>{viewTitle || 'Назад'}</span>
        </button>

        <div className="toolbar-center">
          {mode && (
            <span className={`mode-badge mode-badge--${mode}`}>
              {MODE_ICONS[mode]} {MODE_DISPLAY_NAMES[mode] || mode}
            </span>
          )}
        </div>

        <div className="toolbar-right">
          <SaveStatus saving={saving} savedRecently={savedRecently} />
        </div>
      </div>

      {/* ── Editor scroll area ── */}
      <div className="editor-scroll">
        <div className="editor-content-wrapper">

          {/* ── Bubble menu ── */}
          <BubbleMenu editor={editor} tippyOptions={{ duration: 150, placement: 'top' }}>
            <div className="bubble-menu">
              <BubbleBtn
                onClick={() => editor.chain().focus().toggleBold().run()}
                active={editor.isActive('bold')}
                title="Жирный (Ctrl+B)"
              >
                <Bold size={14} />
              </BubbleBtn>
              <BubbleBtn
                onClick={() => editor.chain().focus().toggleItalic().run()}
                active={editor.isActive('italic')}
                title="Курсив (Ctrl+I)"
              >
                <Italic size={14} />
              </BubbleBtn>
              <BubbleBtn
                onClick={() => editor.chain().focus().toggleUnderline().run()}
                active={editor.isActive('underline')}
                title="Подчёркнутый (Ctrl+U)"
              >
                <UnderlineIcon size={14} />
              </BubbleBtn>
              <BubbleBtn
                onClick={() => editor.chain().focus().toggleStrike().run()}
                active={editor.isActive('strike')}
                title="Зачёркнутый"
              >
                <Strikethrough size={14} />
              </BubbleBtn>
              <BubbleBtn
                onClick={() => editor.chain().focus().toggleCode().run()}
                active={editor.isActive('code')}
                title="Код"
              >
                <Code size={14} />
              </BubbleBtn>

              <BubbleSep />

              <BubbleBtn
                onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
                active={editor.isActive('heading', { level: 1 })}
                title="Заголовок 1"
              >
                <span className="bubble-btn-text">H1</span>
              </BubbleBtn>
              <BubbleBtn
                onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
                active={editor.isActive('heading', { level: 2 })}
                title="Заголовок 2"
              >
                <span className="bubble-btn-text">H2</span>
              </BubbleBtn>
              <BubbleBtn
                onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
                active={editor.isActive('heading', { level: 3 })}
                title="Заголовок 3"
              >
                <span className="bubble-btn-text">H3</span>
              </BubbleBtn>

              <BubbleSep />

              <BubbleBtn
                onClick={handleLink}
                active={editor.isActive('link')}
                title="Ссылка"
              >
                <Link2 size={14} />
              </BubbleBtn>
              <BubbleBtn
                onClick={() => editor.chain().focus().toggleHighlight().run()}
                active={editor.isActive('highlight')}
                title="Выделение"
              >
                <Highlighter size={14} />
              </BubbleBtn>
              <BubbleBtn
                onClick={() => editor.chain().focus().toggleBlockquote().run()}
                active={editor.isActive('blockquote')}
                title="Цитата"
              >
                <Quote size={14} />
              </BubbleBtn>

              <BubbleSep />

              <BubbleBtn
                onClick={() => editor.chain().focus().setTextAlign('left').run()}
                active={editor.isActive({ textAlign: 'left' })}
                title="По левому краю"
              >
                <AlignLeft size={14} />
              </BubbleBtn>
              <BubbleBtn
                onClick={() => editor.chain().focus().setTextAlign('center').run()}
                active={editor.isActive({ textAlign: 'center' })}
                title="По центру"
              >
                <AlignCenter size={14} />
              </BubbleBtn>
              <BubbleBtn
                onClick={() => editor.chain().focus().setTextAlign('right').run()}
                active={editor.isActive({ textAlign: 'right' })}
                title="По правому краю"
              >
                <AlignRight size={14} />
              </BubbleBtn>
            </div>
          </BubbleMenu>

          <EditorContent editor={editor} />
        </div>
      </div>
    </div>
  )
}
