import { useState, useEffect, useMemo, useRef } from 'react'
import {
  Search, Plus, Trash2, ChevronRight, ChevronDown,
  MoreHorizontal, LogOut, Sun, Moon, Folder, FolderOpen, Inbox
} from 'lucide-react'
import { useTheme } from '../contexts/ThemeContext'
import './Sidebar.css'

const MODE_LABELS = {
  transcription: '✏️',
  structure: '📋',
  ideas: '💡',
}

const MODE_DISPLAY_NAMES = {
  transcription: 'транскрипция',
  structure: 'структура',
  ideas: 'идеи',
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

function formatTime(iso) {
  const d = new Date(iso)
  return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
}

function groupDocumentsByDate(documents) {
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)
  const weekAgo = new Date(today)
  weekAgo.setDate(weekAgo.getDate() - 7)

  const groups = { today: [], yesterday: [], thisWeek: [], older: [] }

  documents.forEach(doc => {
    const docDate = new Date(doc.created_at)
    if (docDate >= today) {
      groups.today.push(doc)
    } else if (docDate >= yesterday) {
      groups.yesterday.push(doc)
    } else if (docDate >= weekAgo) {
      groups.thisWeek.push(doc)
    } else {
      groups.older.push(doc)
    }
  })

  return groups
}

const DATE_LABELS = {
  today: 'Сегодня',
  yesterday: 'Вчера',
  thisWeek: 'На этой неделе',
  older: 'Ранее',
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
          {hasChildren
            ? (isExpanded
                ? <ChevronDown size={12} />
                : <ChevronRight size={12} />)
            : <span className="folder-toggle-spacer" />}
        </span>
        <span className="folder-icon-em">
          {isExpanded && hasChildren
            ? <FolderOpen size={14} />
            : <Folder size={14} />}
        </span>
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
          <MoreHorizontal size={14} />
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
  onDocumentCreate,
  onFolderCreate,
  onFolderRename,
  onFolderDelete,
  onMoveDocument,
  onDeleteDocument,
  onLogout,
}) {
  const { theme, toggleTheme } = useTheme()
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedFolders, setExpandedFolders] = useState(new Set())
  const [creatingFolder, setCreatingFolder] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const [renamingId, setRenamingId] = useState(null)
  const [renameValue, setRenameValue] = useState('')
  const [menuState, setMenuState] = useState(null)
  const [creatingDoc, setCreatingDoc] = useState(false)
  const [newDocTitle, setNewDocTitle] = useState('')

  const skipBlurRef = useRef(false)
  const tree = useMemo(() => buildTree(folders), [folders])
  const foldersSorted = useMemo(() => getFoldersSorted(folders), [folders])

  // Filter documents by search query
  const filteredDocs = useMemo(() => {
    if (!searchQuery.trim()) return documents
    const q = searchQuery.toLowerCase()
    return documents.filter(doc =>
      getDisplayTitle(doc).toLowerCase().includes(q) ||
      stripHtml(doc.preview || '').toLowerCase().includes(q)
    )
  }, [documents, searchQuery])

  // Group filtered docs by date
  const groupedDocs = useMemo(() => groupDocumentsByDate(filteredDocs), [filteredDocs])
  const hasAnyDocs = filteredDocs.length > 0

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
    if (skipBlurRef.current) { skipBlurRef.current = false; return }
    if (id && renameValue.trim()) onFolderRename(id, renameValue.trim())
    setRenamingId(null)
    setRenameValue('')
  }

  const handleRenameCancel = () => {
    skipBlurRef.current = true
    setRenamingId(null)
    setRenameValue('')
  }

  const handleNewDocKeyDown = (e) => {
    if (e.key === 'Enter') {
      onDocumentCreate(newDocTitle.trim())
      setNewDocTitle('')
      setCreatingDoc(false)
    } else if (e.key === 'Escape') {
      setNewDocTitle('')
      setCreatingDoc(false)
    }
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
        <div className="sidebar-header-top">
          <h2>HelpWriter</h2>
          <div className="sidebar-header-actions">
            <button className="icon-btn" onClick={toggleTheme} title={theme === 'light' ? 'Тёмная тема' : 'Светлая тема'}>
              {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
            </button>
            <button className="icon-btn" onClick={onLogout} title="Выйти">
              <LogOut size={16} />
            </button>
          </div>
        </div>
        <div className="sidebar-search">
          <Search size={14} className="sidebar-search-icon" />
          <input
            className="sidebar-search-input"
            type="text"
            placeholder="Поиск документов..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* ── Тело сайдбара ── */}
      <div className="sidebar-body">

        {/* ── Навигация ── */}
        <div className="sidebar-nav">
          <div
            className={`sidebar-view-item${selectedView?.type === 'inbox' ? ' active' : ''}`}
            onClick={() => onViewSelect({ type: 'inbox' })}
          >
            <Inbox size={15} className="view-icon" />
            <span className="view-name">Новые</span>
          </div>

          <div className="folders-section">
            <div className="folders-section-header">
              <span className="folders-label">Папки</span>
              <button
                className="add-folder-btn"
                title="Создать папку"
                onClick={e => { e.stopPropagation(); setCreatingFolder(true) }}
              >
                <Plus size={14} />
              </button>
            </div>

            {creatingFolder && (
              <div className="folder-create-row">
                <Folder size={14} className="folder-create-icon" />
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
        </div>

        {/* ── Список документов ── */}
        <div className="doc-list">
          {creatingDoc && (
            <div className="doc-create-row">
              <span className="doc-create-icon">📄</span>
              <input
                className="doc-create-input"
                autoFocus
                value={newDocTitle}
                onChange={e => setNewDocTitle(e.target.value)}
                onKeyDown={handleNewDocKeyDown}
                onBlur={() => { setCreatingDoc(false); setNewDocTitle('') }}
                placeholder="Название документа..."
              />
            </div>
          )}

          {!hasAnyDocs && !creatingDoc && (
            <p className="empty-hint">
              {searchQuery.trim()
                ? 'Ничего не найдено'
                : selectedView?.type === 'inbox'
                  ? 'Новых документов нет.\nНадиктуйте голосовое в боте.'
                  : 'Папка пуста.'}
            </p>
          )}

          {hasAnyDocs && Object.entries(groupedDocs).map(([key, docs]) => {
            if (docs.length === 0) return null
            return (
              <div key={key} className="date-group">
                <div className="date-group-title">{DATE_LABELS[key]}</div>
                {docs.map(doc => (
                  <div
                    key={doc.id}
                    className={`doc-card${doc.id === activeId ? ' active' : ''}`}
                    onClick={() => onSelect(doc)}
                  >
                    <div className="doc-card-header">
                      <span className="doc-mode-icon">{MODE_LABELS[doc.mode] || '📄'}</span>
                      <span className="doc-title">{getDisplayTitle(doc)}</span>
                      <span className="doc-time">{formatTime(doc.created_at)}</span>
                      <button
                        className="item-menu-btn"
                        onClick={e => openMenu(e, 'doc', doc.id)}
                        title="Действия с документом"
                      >
                        <MoreHorizontal size={14} />
                      </button>
                    </div>
                    <div className="doc-preview">
                      {stripHtml(doc.preview || '').trim().slice(0, 100) || '(пустой документ)'}
                    </div>
                    <div className="doc-card-footer">
                      <span className={`mode-badge mode-badge--${doc.mode || 'transcription'}`}>
                        {MODE_LABELS[doc.mode] || '📄'} {MODE_DISPLAY_NAMES[doc.mode] || doc.mode}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )
          })}
        </div>

      </div>

      {/* ── FAB: создать документ ── */}
      <button
        className="fab-create-doc"
        title="Создать документ"
        onClick={() => { setCreatingDoc(true); setNewDocTitle('') }}
      >
        <Plus size={20} />
      </button>

      {/* ── Контекстное меню ── */}
      {menuState && (
        <div
          className="context-menu"
          style={{ top: menuState.y, left: menuState.x }}
          onMouseDown={e => e.stopPropagation()}
        >
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
                <Trash2 size={14} /> Удалить
              </button>
            </>
          )}

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
                <Inbox size={14} /> Новые
              </button>
              {foldersSorted.map(f => (
                <button
                  key={f.id}
                  className="menu-item"
                  style={{ paddingLeft: `${12 + f.depth * 12}px` }}
                  onClick={() => { onMoveDocument(menuState.id, f.id); setMenuState(null) }}
                >
                  <Folder size={14} /> {f.name}
                </button>
              ))}
              {folders.length === 0 && <span className="menu-empty">Нет папок</span>}
            </>
          )}

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
                <Trash2 size={14} /> Удалить
              </button>
            </>
          )}
        </div>
      )}
    </div>
  )
}
