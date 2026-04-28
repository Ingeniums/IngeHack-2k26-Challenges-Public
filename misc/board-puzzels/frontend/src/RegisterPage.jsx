import { useEffect, useMemo, useState } from 'react'
import { apiRequest, getStoredToken, setStoredToken } from './api'
import { statusClass } from './ui'

function redirectToLevels() {
  window.location.replace('/levels.html')
}

function RegisterPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isBusy, setIsBusy] = useState(false)
  const [status, setStatus] = useState({ message: '', tone: 'neutral' })

  const queryMessage = useMemo(() => {
    const params = new URLSearchParams(window.location.search)
    return params.get('msg') ?? ''
  }, [])

  const shownStatus =
    status.message.length > 0
      ? status
      : queryMessage
        ? { message: queryMessage, tone: 'error' }
        : { message: '', tone: 'neutral' }

  useEffect(() => {
    if (getStoredToken()) {
      redirectToLevels()
    }
  }, [])

  const authenticate = async (mode) => {
    if (!email.trim() || !password) {
      setStatus({ message: 'Email and password are required.', tone: 'error' })
      return
    }

    setIsBusy(true)
    setStatus({
      message: mode === 'register' ? 'Creating account...' : 'Signing in...',
      tone: 'neutral',
    })

    try {
      const endpoint = mode === 'register' ? '/api/auth/register' : '/api/auth/login'
      const payload = await apiRequest(endpoint, {
        method: 'POST',
        requiresAuth: false,
        body: {
          email: email.trim(),
          password,
        },
      })

      setStoredToken(payload.access_token)
      setStatus({ message: 'Success. Redirecting...', tone: 'success' })
      redirectToLevels()
    } catch (error) {
      setStatus({ message: error.message, tone: 'error' })
    } finally {
      setIsBusy(false)
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-label="Register or login">
        <h1>Board Puzzles</h1>
        <p className="subtitle">Create an account or log in.</p>

        <form
          className="auth-form"
          onSubmit={(event) => {
            event.preventDefault()
            void authenticate('register')
          }}
          noValidate
        >
          <label htmlFor="email-input">Email</label>
          <input
            id="email-input"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />

          <label htmlFor="password-input">Password</label>
          <input
            id="password-input"
            type="password"
            autoComplete="current-password"
            placeholder="At least 8 characters"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />

          <div className="button-row">
            <button type="submit" disabled={isBusy}>
              Register
            </button>
            <button
              type="button"
              className="secondary"
              disabled={isBusy}
              onClick={() => {
                void authenticate('login')
              }}
            >
              Login
            </button>
          </div>
        </form>

        <p className={statusClass(shownStatus.tone)} role="status" aria-live="polite">
          {shownStatus.message}
        </p>
      </section>
    </main>
  )
}

export default RegisterPage
