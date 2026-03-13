import { useState, useEffect, useCallback } from 'react'
import Sidebar from '../components/Sidebar'
import Editor from '../components/Editor'
import api from '../api/client'
import './EditorPage.css'

export default function EditorPage() {
  const [documents, setDocuments] = useState([])
  const [activeDoc, setActiveDoc] = useState(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api.get('/documents').then((res) => {
      const docs = res.data.items || res.data
      setDocuments(docs)
      if (docs.length > 0) setActiveDoc(docs[0])
    })
  }, [])

  const handleSave = useCallback(async (html) => {
    if (!activeDoc) return
    setSaving(true)
    try {
      await api.put(`/documents/${activeDoc.id}`, { content: html })
      setDocuments((prev) =>
        prev.map((d) => (d.id === activeDoc.id ? { ...d, content: html } : d))
      )
      setActiveDoc((prev) => ({ ...prev, content: html }))
    } finally {
      setSaving(false)
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
        onSelect={setActiveDoc}
        onLogout={handleLogout}
      />
      <main className="editor-main">
        {activeDoc ? (
          <Editor
            key={activeDoc.id}
            content={activeDoc.content}
            onSave={handleSave}
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
