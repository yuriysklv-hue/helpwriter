import { useState, useEffect, useCallback, useRef } from 'react'
import Sidebar from '../components/Sidebar'
import Editor from '../components/Editor'
import api from '../api/client'
import './EditorPage.css'

function normalizeContent(content) {
  if (!content) return '<p></p>'
  if (content.trim().startsWith('<')) return content
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
  const currentHtmlRef = useRef(null)

  useEffect(() => {
    api.get('/folders').then(res => setFolders(res.data)).catch(console.error)
  }, [])

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

  const handleBack = useCallback(() => {
    if (currentHtmlRef.current && activeDoc) {
      api.put(`/documents/${activeDoc.id}`, { content: currentHtmlRef.current }).catch(() => {})
      currentHtmlRef.current = null
    }
    setActiveDoc(null)
  }, [activeDoc])

  // ── Folder handlers ───────────────────────────────────────────

  const handleFolderCreate = useCallback(async (name) => {
    try {
      await api.post('/folders', { name })
      const res = await api.get('/folders')
      setFolders(res.data)
    } catch (e) {
      console.error('Failed to create folder', e)
    }
  }, [])

  const handleFolderRename = useCallback(async (id, name) => {
    try {
      await api.put(`/folders/${id}`, { name })
      const res = await api.get('/folders')
      setFolders(res.data)
    } catch (e) {
      console.error('Failed to rename folder', e)
    }
  }, [])

  const handleFolderDelete = useCallback(async (id) => {
    try {
      await api.delete(`/folders/${id}`)
      const res = await api.get('/folders')
      setFolders(res.data)
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

  const handleDocumentCreate = useCallback(async (title) => {
    // Auto-save current doc before switching
    if (currentHtmlRef.current && activeDoc) {
      api.put(`/documents/${activeDoc.id}`, { content: currentHtmlRef.current }).catch(() => {})
      currentHtmlRef.current = null
    }
    try {
      const folderId = selectedView.type === 'folder' ? selectedView.id : null
      const res = await api.post('/documents', {
        title: title || null,
        content: '',
        mode: 'transcription',
        folder_id: folderId,
      })
      const newDoc = { ...res.data, content: normalizeContent(res.data.content) }
      setDocuments(prev => [
        { id: newDoc.id, title: newDoc.title, preview: '', mode: newDoc.mode, source: newDoc.source, created_at: newDoc.created_at, updated_at: newDoc.updated_at, folder_id: newDoc.folder_id },
        ...prev,
      ])
      setActiveDoc(newDoc)
    } catch (e) {
      console.error('Failed to create document', e)
    }
  }, [activeDoc, selectedView])

  const handleLogout = async () => {
    await api.post('/auth/logout')
    window.location.href = '/login'
  }

  // Compute viewTitle for the editor back button
  const viewTitle = selectedView?.type === 'inbox'
    ? 'Новые'
    : folders.find(f => f.id === selectedView?.id)?.name || 'Папка'

  return (
    <div className={`editor-page${activeDoc ? ' has-doc' : ''}`}>
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
        onDocumentCreate={handleDocumentCreate}
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
            mode={activeDoc.mode}
            onBack={handleBack}
            viewTitle={viewTitle}
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
