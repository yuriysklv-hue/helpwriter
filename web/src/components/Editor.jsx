import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import { useEffect, useCallback } from 'react'
import './Editor.css'

export default function Editor({ content, onSave, saving }) {
  const editor = useEditor({
    extensions: [StarterKit],
    content,
    editorProps: {
      attributes: {
        class: 'editor-content',
      },
    },
  })

  useEffect(() => {
    if (editor && content !== editor.getHTML()) {
      editor.commands.setContent(content)
    }
  }, [content])

  const handleSave = useCallback(() => {
    if (editor) {
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

  if (!editor) return null

  return (
    <div className="editor-wrapper">
      <div className="editor-toolbar">
        <div className="format-btns">
          <button
            onClick={() => editor.chain().focus().toggleBold().run()}
            className={`fmt-btn ${editor.isActive('bold') ? 'active' : ''}`}
            title="Жирный (Ctrl+B)"
          ><b>Ж</b></button>
          <button
            onClick={() => editor.chain().focus().toggleItalic().run()}
            className={`fmt-btn ${editor.isActive('italic') ? 'active' : ''}`}
            title="Курсив (Ctrl+I)"
          ><i>К</i></button>
          <button
            onClick={() => editor.chain().focus().toggleStrike().run()}
            className={`fmt-btn ${editor.isActive('strike') ? 'active' : ''}`}
            title="Зачёркнутый"
          ><s>З</s></button>
          <div className="toolbar-sep" />
          <button
            onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
            className={`fmt-btn ${editor.isActive('heading', { level: 1 }) ? 'active' : ''}`}
            title="Заголовок 1"
          >H1</button>
          <button
            onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
            className={`fmt-btn ${editor.isActive('heading', { level: 2 }) ? 'active' : ''}`}
            title="Заголовок 2"
          >H2</button>
          <div className="toolbar-sep" />
          <button
            onClick={() => editor.chain().focus().toggleBulletList().run()}
            className={`fmt-btn ${editor.isActive('bulletList') ? 'active' : ''}`}
            title="Список"
          >• —</button>
          <button
            onClick={() => editor.chain().focus().toggleOrderedList().run()}
            className={`fmt-btn ${editor.isActive('orderedList') ? 'active' : ''}`}
            title="Нумерованный список"
          >1.</button>
          <div className="toolbar-sep" />
          <button
            onClick={() => editor.chain().focus().toggleBlockquote().run()}
            className={`fmt-btn ${editor.isActive('blockquote') ? 'active' : ''}`}
            title="Цитата"
          >❝</button>
        </div>
        <div className="toolbar-right">
          <button onClick={handleSave} disabled={saving} className="save-btn">
            {saving ? 'Сохранение...' : 'Сохранить'}
          </button>
          <span className="shortcut-hint">или Ctrl+S</span>
        </div>
      </div>
      <EditorContent editor={editor} />
    </div>
  )
}
