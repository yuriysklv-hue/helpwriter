import { useState, useEffect, useCallback, useRef } from 'react'
import Sidebar from '../components/Sidebar'
import Editor from '../components/Editor'
import api from '../api/client'
import './EditorPage.css'

// Convert plain text (old bot documents) to HTML paragraphs for TipTap
function normalizeContent(content) {
  if (!content) return '<p></p>'
  if (content.trim().startsWith('<')) return content  // already HTML
  return content.split(/\n\n+/)
    .filter(p => p.trim())
    .map(p => `<p>${p.trim().replace(/\n/g, '<br>')}</p>`)
    .join('') || '<p></p>'
}

export default function EditorPage() {
  const [documents, setDocuments] = useState([])
  const [activeDoc, setActiveDoc] = useState(null)
  const [saving, setSaving] = useState(false)
  const currentHtmlRef = useRef(null)  // latest unsaved HTML from editor

  useEffect(() => {
    api.get('/documents').then(async (res) => {
      const docs = res.data.items || res.data
      setDocuments(docs)
      if (docs.length > 0) {
        try {
          const full = await api.get(`/documents/${docs[0].id}`)
          setActiveDoc({ ...full.data, content: normalizeContent(full.data.content) })
        } catch (e) {
          // If full fetch fails, use list item data (preview only)
          setActiveDoc({ ...docs[0], content: normalizeContent(docs[0].preview || '') })
        }
      }
    }).catch(console.error)
  }, [])

  const handleSave = useCallback(async (html) => {
    if (!activeDoc) return
    setSaving(true)
    try {
      await api.put(`/documents/${activeDoc.id}`, { content: html })
      setDocuments((prev) =>
        prev.map((d) => (d.id === activeDoc.id ? { ...d, preview: html.slice(0, 200) } : d))
      )
      setActiveDoc((prev) => ({ ...prev, content: html }))
    } finally {
      setSaving(false)
    }
  }, [activeDoc])

  const handleChange = useCallback((html) => {
    currentHtmlRef.current = html
  }, [])

  const handleSelect = useCallback(async (doc) => {
    if (doc.id === activeDoc?.id) return
    // Save current doc before switching
    if (currentHtmlRef.current && activeDoc) {
      api.put(`/documents/${activeDoc.id}`, { content: currentHtmlRef.current }).catch(() => {})
      currentHtmlRef.current = null
    }
    try {
      const res = await api.get(`/documents/${doc.id}`)
      setActiveDoc({ ...res.data, content: normalizeContent(res.data.content) })
    } catch (e) {
      setActiveDoc({ ...doc, content: normalizeContent(doc.preview || '') })
    }
  }, [activeDoc])

  const handleLogout = async () => {
    await api.post('/auth/logout')
    window.location.href = '/login'
  }

  return (
    <div className="editor-page">
      <Sidebar
        documents={documents}
        activeId={activeDoc?.id}
        onSelect={handleSelect}
        onLogout={handleLogout}
      />
      <main className="editor-main">
        {activeDoc ? (
          <Editor
            key={activeDoc.id}
            content={activeDoc.content}
            onSave={handleSave}
            onChange={handleChange}
            saving={saving}
          />
        ) : (
          <div className="editor-empty">
            <p>Выберите документ или надиктуйте голосовое в боте</p>
          </div>
        )}
      </main>
    </div>
  )
}
