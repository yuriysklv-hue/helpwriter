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

  return (
    <div className="editor-wrapper">
      <div className="editor-toolbar">
        <button onClick={handleSave} disabled={saving} className="save-btn">
          {saving ? 'Сохранение...' : 'Сохранить'}
        </button>
        <span className="shortcut-hint">или Ctrl+S</span>
      </div>
      <EditorContent editor={editor} />
    </div>
  )
}
