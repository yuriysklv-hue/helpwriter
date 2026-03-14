import { useState, useEffect } from 'react'
import Login from './pages/Login'
import EditorPage from './pages/EditorPage'
import api from './api/client'

export default function App() {
  const [authed, setAuthed] = useState(null)

  useEffect(() => {
    api.get('/auth/verify')
      .then(() => setAuthed(true))
      .catch(() => setAuthed(false))
  }, [])

  if (authed === null) return null

  if (!authed) return <Login />

  return <EditorPage />
}
