import { useState, useEffect } from 'react'
import Login from './pages/Login'
import EditorPage from './pages/EditorPage'
import api from './api/client'
import { ThemeProvider } from './contexts/ThemeContext'

export default function App() {
  const [authed, setAuthed] = useState(null)

  useEffect(() => {
    api.get('/auth/verify')
      .then(() => setAuthed(true))
      .catch(() => setAuthed(false))
  }, [])

  if (authed === null) return null

  return (
    <ThemeProvider>
      {!authed ? <Login /> : <EditorPage />}
    </ThemeProvider>
  )
}
