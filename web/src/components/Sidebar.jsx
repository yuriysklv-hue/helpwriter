import { useState, useEffect, useMemo, useRef } from 'react'
import './Sidebar.css'

const MODE_LABELS = {
  transcription: '✏️',
  structure: '📋',
  ideas: '💡',
}
const MODE_KEYS = new Set(['transcription', 'structure', 'ideas'])

function getDisplayTitle(doc) {
  const titleOk = doc.title && !MODE_KEYS.has(doc.title)
  if (titleOk) return doc.title
  const fromPreview = stripHtml(doc.preview || '').trim().slice(0, 60)
  return fromPreview || '—'
}

function stripHtml(html) {
  return (html || '').replace(/<[^>]+>/g, '')
}

function formatDate(iso) {
  const d = new Date(iso)
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

function buildTree(folders) {
  const map = {}
  folders.forEach(f => { map[f.id] = { ...f, children: [] } })
  const roots = []
  folders.forEach(f => {
    if (f.parent_id && map[f.parent_id]) {
      map[f.parent_id].children.push(map[f.id])
    } else {
      roots.push(map[f.id])
    }
  })
  return roots
}

// Returns flat list of folders in tree order with depth, for the move menu
function getFoldersSorted(folders) {
  const map = {}
  folders.forEach(f => { map[f.id] = { ...f, children: [] } })
  const roots = []
  folders.forEach(f => {
    if (f.parent_id && map[f.parent_id]) {
      map[f.parent_id].children.push(map[f.id])
    } else {
      roots.push(map[f.id])
    }
  })
  const result = []
  const traverse = (node, depth) => {
    result.push({ ...node, depth })
    node.children.forEach(child => traverse(child, depth + 1))
  }
  roots.forEach(r => traverse(r, 0))
  return result
}

// ─── FolderNode ───────────────────────────────────────────────────────────────

function FolderNode({
  folder, level, selectedView, expandedFolders,
  renamingId, renameValue,
  onViewSelect, onToggle,
  onRenameChange, onRenameCommit, onRenameCancel,
  onMenuOpen,
}) {
  const isExpanded = expandedFolders.has(folder.id)
  const isActive = selectedView?.type === 'folder' && selectedView.id === folder.id
  const isRenaming = renamingId === folder.id
  const hasChildren = folder.children?.length > 0

  return (
    <div className="folder-node">
      <div
        className={`folder-item${isActive ? ' active' : ''}`}
        style={{ paddingLeft: `${12 + level * 16}px` }}
        onClick={() => {
          onViewSelect({ type: 'folder', id: folder.id })
          if (hasChildren) onToggle(folder.id)
        }}
      >
        <span
          className="folder-toggle"
          onClick={e => { e.stopPropagation(); if (hasChildren) onToggle(folder.id) }}
        >
          {hasChildren ? (isExpanded ? '▾' : '▸') : <span className="folder-toggle-spacer" />}
        </span>
        <span className="folder-icon-em">{isExpanded && hasChildren ? '📂' : '📁'}</span>
        {isRenaming ? (
          <input
            className="folder-name-input"
            autoFocus
            value={renameValue}
            onChange={e => onRenameChange(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter') onRenameCommit(folder.id)
              if (e.key === 'Escape') onRenameCancel()
            }}
            onBlur={() => onRenameCommit(folder.id)}
            onClick={e => e.stopPropagation()}
          />
        ) : (
          <span className="folder-name">{folder.name}</span>
        )}
        <button
          className="item-menu-btn"
          onClick={e => onMenuOpen(e, 'folder', folder.id)}
          title="Действия с папкой"
        >
          ···
        </button>
      </div>
      {isExpanded && hasChildren && (
        <div className="folder-children">
          {folder.children.map(child => (
            <FolderNode
              key={child.id}
              folder={child}
              level={level + 1}
              selectedView={selectedView}
              expandedFolders={expandedFolders}
              renamingId={renamingId}
              renameValue={renameValue}
              onViewSelect={onViewSelect}
              onToggle={onToggle}
              onRenameChange={onRenameChange}
              onRenameCommit={onRenameCommit}
              onRenameCancel={onRenameCancel}
              onMenuOpen={onMenuOpen}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

export default function Sidebar({
  documents,
  folders,
  activeId,
  selectedView,
  onSelect,
  onViewSelect,
  onFolderCreate,
  onFolderRename,
  onFolderDelete,
  onMoveDocument,
  onDeleteDocument,
  onLogout,
}) {
  const [expandedFolders, setExpandedFolders] = useState(new Set())
  const [creatingFolder, setCreatingFolder] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const [renamingId, setRenamingId] = useState(null)
  const [renameValue, setRenameValue] = useState('')
  const [menuState, setMenuState] = useState(null)
  // menuState: { type: 'doc'|'folder', id, x, y, step: 'main'|'move' }

  // Prevents blur from committing rename after Escape cancels it
  const skipBlurRef = useRef(false)

  const tree = useMemo(() => buildTree(folders), [folders])
  const foldersSorted = useMemo(() => getFoldersSorted(folders), [folders])

  // Close context menu on outside mousedown
  useEffect(() => {
    if (!menuState) return
    const handler = () => setMenuState(null)
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [menuState])

  const toggleFolder = (id) => {
    setExpandedFolders(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const openMenu = (e, type, id) => {
    e.stopPropagation()
    const rect = e.currentTarget.getBoundingClientRect()
    setMenuState({ type, id, x: rect.left, y: rect.bottom + 4, step: 'main' })
  }

  const startRename = (folder) => {
    skipBlurRef.current = false
    setRenamingId(folder.id)
    setRenameValue(folder.name)
  }

  const handleRenameCommit = (id) => {
    if (skipBlurRef.current) {
      skipBlurRef.current = false
      return
    }
    if (id && renameValue.trim()) {
      onFolderRename(id, renameValue.trim())
    }
    setRenamingId(null)
    setRenameValue('')
  }

  const handleRenameCancel = () => {
    skipBlurRef.current = true
    setRenamingId(null)
    setRenameValue('')
  }

  const handleNewFolderKeyDown = (e) => {
    if (e.key === 'Enter' && newFolderName.trim()) {
      onFolderCreate(newFolderName.trim())
      setNewFolderName('')
      setCreatingFolder(false)
    } else if (e.key === 'Escape') {
      setNewFolderName('')
      setCreatingFolder(false)
    }
  }

  return (
    <div className="sidebar">
      {/* ── Шапка ── */}
      <div className="sidebar-header">
        <h2>HelpWriter</h2>
        <button className="logout-btn" onClick={onLogout}>Выйти</button>
      </div>

      {/* ── Тело сайдбара (прокручивается целиком) ── */}
      <div className="sidebar-body">

      {/* ── Навигация ── */}
      <div className="sidebar-nav">
        {/* Новые (inbox) */}
        <div
          className={`sidebar-view-item${selectedView?.type === 'inbox' ? ' active' : ''}`}
          onClick={() => onViewSelect({ type: 'inbox' })}
        >
          <span className="view-icon">📥</span>
          <span className="view-name">Новые</span>
        </div>

        {/* Папки */}
        <div className="folders-section">
          <div className="folders-section-header">
            <span className="folders-label">Папки</span>
            <button
              className="add-folder-btn"
              title="Создать папку"
              onClick={e => { e.stopPropagation(); setCreatingFolder(true) }}
            >
              +
            </button>
          </div>

          {creatingFolder && (
            <div className="folder-create-row">
              <span className="folder-create-icon">📁</span>
              <input
                className="folder-name-input"
                autoFocus
                value={newFolderName}
                onChange={e => setNewFolderName(e.target.value)}
                onKeyDown={handleNewFolderKeyDown}
                onBlur={() => { setCreatingFolder(false); setNewFolderName('') }}
                placeholder="Название папки..."
              />
            </div>
          )}

          {tree.map(folder => (
            <FolderNode
              key={folder.id}
              folder={folder}
              level={0}
              selectedView={selectedView}
              expandedFolders={expandedFolders}
              renamingId={renamingId}
              renameValue={renameValue}
              onViewSelect={onViewSelect}
              onToggle={toggleFolder}
              onRenameChange={setRenameValue}
              onRenameCommit={handleRenameCommit}
              onRenameCancel={handleRenameCancel}
              onMenuOpen={openMenu}
            />
          ))}

          {folders.length === 0 && !creatingFolder && (
            <p className="empty-folders-hint">Нажмите + чтобы создать папку</p>
          )}
        </div>
      </div>{/* /sidebar-nav */}

      {/* ── Список документов текущего раздела ── */}
      <div className="doc-list">
        {documents.length === 0 && (
          <p className="empty-hint">
            {selectedView?.type === 'inbox'
              ? 'Новых документов нет.\nНадиктуйте голосовое в боте.'
              : 'Папка пуста.'}
          </p>
        )}
        {documents.map(doc => (
          <div
            key={doc.id}
            className={`doc-item${doc.id === activeId ? ' active' : ''}`}
            onClick={() => onSelect(doc)}
          >
            <div className="doc-title">
              <span className="doc-mode-icon">{MODE_LABELS[doc.mode] || '📄'}</span>
              <span className="doc-title-text">{getDisplayTitle(doc)}</span>
              <button
                className="item-menu-btn"
                onClick={e => openMenu(e, 'doc', doc.id)}
                title="Действия с документом"
              >
                ···
              </button>
            </div>
            <div className="doc-preview">{stripHtml(doc.preview || '').trim().slice(0, 80) || '(пустой документ)'}</div>
            <div className="doc-date">{formatDate(doc.created_at)}</div>
          </div>
        ))}
      </div>

      </div>{/* /sidebar-body */}

      {/* ── Контекстное меню (fixed overlay) ── */}
      {menuState && (
        <div
          className="context-menu"
          style={{ top: menuState.y, left: menuState.x }}
          onMouseDown={e => e.stopPropagation()}
        >
          {/* Документ — основное меню */}
          {menuState.type === 'doc' && menuState.step === 'main' && (
            <>
              <button
                className="menu-item"
                onClick={() => setMenuState(m => ({ ...m, step: 'move' }))}
              >
                Переместить в...
              </button>
              <div className="menu-divider" />
              <button
                className="menu-item menu-item-danger"
                onClick={() => { onDeleteDocument(menuState.id); setMenuState(null) }}
              >
                Удалить
              </button>
            </>
          )}

          {/* Документ — выбор папки */}
          {menuState.type === 'doc' && menuState.step === 'move' && (
            <>
              <button
                className="menu-item menu-item-back"
                onClick={() => setMenuState(m => ({ ...m, step: 'main' }))}
              >
                ← Назад
              </button>
              <div className="menu-divider" />
              <button
                className="menu-item"
                onClick={() => { onMoveDocument(menuState.id, null); setMenuState(null) }}
              >
                📥 Новые
              </button>
              {foldersSorted.map(f => (
                <button
                  key={f.id}
                  className="menu-item"
                  style={{ paddingLeft: `${12 + f.depth * 12}px` }}
                  onClick={() => { onMoveDocument(menuState.id, f.id); setMenuState(null) }}
                >
                  📁 {f.name}
                </button>
              ))}
              {folders.length === 0 && (
                <span className="menu-empty">Нет папок</span>
              )}
            </>
          )}

          {/* Папка — меню */}
          {menuState.type === 'folder' && (
            <>
              <button
                className="menu-item"
                onClick={() => {
                  const folder = folders.find(f => f.id === menuState.id)
                  if (folder) startRename(folder)
                  setMenuState(null)
                }}
              >
                Переименовать
              </button>
              <div className="menu-divider" />
              <button
                className="menu-item menu-item-danger"
                onClick={() => { onFolderDelete(menuState.id); setMenuState(null) }}
              >
                Удалить
              </button>
            </>
          )}
        </div>
      )}
    </div>
  )
}
