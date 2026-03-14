import { useEffect } from 'react'
import './Login.css'

export default function Login() {
  useEffect(() => {
    window.TelegramLoginWidget = {
      dataOnauth: (user) => {
        fetch('/api/auth/telegram', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(user),
        }).then((res) => {
          if (res.ok) window.location.href = '/'
        })
      },
    }

    const script = document.createElement('script')
    script.src = 'https://telegram.org/js/telegram-widget.js?22'
    script.setAttribute('data-telegram-login', import.meta.env.VITE_BOT_USERNAME)
    script.setAttribute('data-size', 'large')
    script.setAttribute('data-onauth', 'TelegramLoginWidget.dataOnauth(user)')
    script.setAttribute('data-request-access', 'write')
    script.async = true
    document.getElementById('telegram-widget').appendChild(script)
  }, [])

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>HelpWriter</h1>
        <p>Войдите через Telegram для доступа к редактору</p>
        <div id="telegram-widget" />
      </div>
    </div>
  )
}
