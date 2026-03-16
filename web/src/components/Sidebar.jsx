import './Sidebar.css'

const MODE_LABELS = {
  transcription: '✏️',
  structure: '📋',
  ideas: '💡',
}

// These are raw mode keys — not real titles, should be ignored
const MODE_KEYS = new Set(['transcription', 'structure', 'ideas'])

function getDisplayTitle(doc) {
  const titleOk = doc.title && !MODE_KEYS.has(doc.title)
  if (titleOk) return doc.title
  const fromPreview = stripHtml(doc.preview || '').trim().slice(0, 60)
  return fromPreview || '—'
}

export default function Sidebar({ documents, activeId, onSelect, onLogout }) {
  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h2>HelpWriter</h2>
        <button className="logout-btn" onClick={onLogout}>Выйти</button>
      </div>
      <div className="doc-list">
        {documents.length === 0 && (
          <p className="empty-hint">Нет документов.<br />Надиктуйте голосовое в боте.</p>
        )}
        {documents.map((doc) => {
          const previewText = stripHtml(doc.preview || '').trim()
          return (
            <div
              key={doc.id}
              className={`doc-item ${doc.id === activeId ? 'active' : ''}`}
              onClick={() => onSelect(doc)}
            >
              <div className="doc-title">
                <span className="doc-mode-icon">{MODE_LABELS[doc.mode] || '📄'}</span>
                {getDisplayTitle(doc)}
              </div>
              <div className="doc-preview">{previewText.slice(0, 80) || '(пустой документ)'}</div>
              <div className="doc-date">{formatDate(doc.created_at)}</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function stripHtml(html) {
  return (html || '').replace(/<[^>]+>/g, '')
}

function formatDate(iso) {
  const d = new Date(iso)
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}
