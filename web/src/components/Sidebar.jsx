import './Sidebar.css'

const MODE_LABELS = {
  transcription: '✏️ Транскрибация',
  structure: '📋 Структура',
  ideas: '💡 Идеи',
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
        {documents.map((doc) => (
          <div
            key={doc.id}
            className={`doc-item ${doc.id === activeId ? 'active' : ''}`}
            onClick={() => onSelect(doc)}
          >
            <div className="doc-mode">{MODE_LABELS[doc.mode] || doc.mode}</div>
            <div className="doc-preview">{stripHtml(doc.content).slice(0, 80)}...</div>
            <div className="doc-date">{formatDate(doc.created_at)}</div>
          </div>
        ))}
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
