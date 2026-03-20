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
  const [folders, setFolders] = useState([])
  const [selectedView, setSelectedView] = useState({ type: 'inbox' })
  const [activeDoc, setActiveDoc] = useState(null)
  const [saving, setSaving] = useState(false)
  const currentHtmlRef = useRef(null)  // latest unsaved HTML from editor

  // Load folders once on mount
  useEffect(() => {
    api.get('/folders').then(res => setFolders(res.data)).catch(console.error)
  }, [])

  // Load documents whenever selected view changes
  useEffect(() => {
    const params = {}
    if (selectedView.type === 'inbox') {
      params.view = 'inbox'
    } else if (selectedView.type === 'folder') {
      params.folder_id = selectedView.id
    }

    api.get('/documents', { params }).then(async res => {
      const docs = res.data.items || res.data
      setDocuments(docs)
      setActiveDoc(null)
      currentHtmlRef.current = null
      if (docs.length > 0) {
        try {
          const full = await api.get(`/documents/${docs[0].id}`)
          setActiveDoc({ ...full.data, content: normalizeContent(full.data.content) })
        } catch {
          setActiveDoc({ ...docs[0], content: normalizeContent(docs[0].preview || '') })
        }
      }
    }).catch(console.error)
  }, [selectedView])

  const handleSave = useCallback(async (html) => {
    if (!activeDoc) return
    setSaving(true)
    try {
      await api.put(`/documents/${activeDoc.id}`, { content: html })
      setDocuments(prev =>
        prev.map(d => d.id === activeDoc.id ? { ...d, preview: html.slice(0, 200) } : d)
      )
      setActiveDoc(prev => ({ ...prev, content: html }))
    } finally {
      setSaving(false)
    }
  }, [activeDoc])

  const handleChange = useCallback((html) => {
    currentHtmlRef.current = html
  }, [])

  const handleSelect = useCallback(async (doc) => {
    if (doc.id === activeDoc?.id) return
    // Auto-save current doc before switching
    if (currentHtmlRef.current && activeDoc) {
      api.put(`/documents/${activeDoc.id}`, { content: currentHtmlRef.current }).catch(() => {})
      currentHtmlRef.current = null
    }
    try {
      const res = await api.get(`/documents/${doc.id}`)
      setActiveDoc({ ...res.data, content: normalizeContent(res.data.content) })
    } catch {
      setActiveDoc({ ...doc, content: normalizeContent(doc.preview || '') })
    }
  }, [activeDoc])

  // ── Folder handlers ──────────────────────────────────────────────────────

  const handleFolderCreate = useCallback(async (name) => {
    try {
      await api.post('/folders', { name })
      // Reload to get server-sorted list
      const res = await api.get('/folders')
      setFolders(res.data)
    } catch (e) {
      console.error('Failed to create folder', e)
    }
  }, [])

  const handleFolderRename = useCallback(async (id, name) => {
    try {
      await api.put(`/folders/${id}`, { name })
      // Reload to get correctly sorted list after rename
      const res = await api.get('/folders')
      setFolders(res.data)
    } catch (e) {
      console.error('Failed to rename folder', e)
    }
  }, [])

  const handleFolderDelete = useCallback(async (id) => {
    try {
      await api.delete(`/folders/${id}`)
      // Reload all folders — cascade on server may have deleted children too
      const res = await api.get('/folders')
      setFolders(res.data)
      // If current view is a folder that no longer exists, go to inbox
      if (selectedView.type === 'folder' && !res.data.find(f => f.id === selectedView.id)) {
        setSelectedView({ type: 'inbox' })
      }
    } catch (e) {
      console.error('Failed to delete folder', e)
    }
  }, [selectedView])

  const handleMoveDocument = useCallback(async (docId, folderId) => {
    try {
      await api.put(`/documents/${docId}/move`, { folder_id: folderId })
      // Remove doc from current view (it moved elsewhere)
      setDocuments(prev => prev.filter(d => d.id !== docId))
      if (activeDoc?.id === docId) {
        setActiveDoc(null)
        currentHtmlRef.current = null
      }
    } catch (e) {
      console.error('Failed to move document', e)
    }
  }, [activeDoc])

  const handleDeleteDocument = useCallback(async (docId) => {
    try {
      await api.delete(`/documents/${docId}`)
      setDocuments(prev => prev.filter(d => d.id !== docId))
      if (activeDoc?.id === docId) {
        setActiveDoc(null)
        currentHtmlRef.current = null
      }
    } catch (e) {
      console.error('Failed to delete document', e)
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
        folders={folders}
        activeId={activeDoc?.id}
        selectedView={selectedView}
        onSelect={handleSelect}
        onViewSelect={setSelectedView}
        onFolderCreate={handleFolderCreate}
        onFolderRename={handleFolderRename}
        onFolderDelete={handleFolderDelete}
        onMoveDocument={handleMoveDocument}
        onDeleteDocument={handleDeleteDocument}
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
