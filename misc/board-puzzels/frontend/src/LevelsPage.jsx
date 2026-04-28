import { useCallback, useEffect, useMemo, useState } from 'react'
import { apiRequest, clearStoredToken, getStoredToken } from './api'
import { statusClass } from './ui'

const LEVEL_COUNT = 2
const DEFAULT_LEVEL_CARDS_GAP = 'clamp(10px, 1.2vw, 16px)'

function resolveCardsGap(levelData) {
  const rawGap = levelData?.cards_gap
  if (typeof rawGap !== 'string') {
    return DEFAULT_LEVEL_CARDS_GAP
  }

  const normalized = rawGap.trim()
  return normalized.length > 0 ? normalized : DEFAULT_LEVEL_CARDS_GAP
}

function goToRegister(message = '') {
  clearStoredToken()
  const target = new URL('/register.html', window.location.origin)
  if (message) {
    target.searchParams.set('msg', message)
  }
  window.location.replace(target.toString())
}

function goToPuzzle(level) {
  const target = new URL('/puzzle.html', window.location.origin)
  target.searchParams.set('levelId', String(level))
  window.location.assign(target.toString())
}

function LevelsPage() {
  const token = getStoredToken()

  const [userEmail, setUserEmail] = useState('')
  const [currentLevelId, setCurrentLevelId] = useState(null)
  const [completedLevelIds, setCompletedLevelIds] = useState([])
  const [levelsCardsGap, setLevelsCardsGap] = useState(DEFAULT_LEVEL_CARDS_GAP)
  const [status, setStatus] = useState({ message: 'Loading levels...', tone: 'neutral' })
  const [isLoading, setIsLoading] = useState(true)

  const queryMessage = useMemo(() => {
    const params = new URLSearchParams(window.location.search)
    return params.get('msg') ?? ''
  }, [])

  const shownStatus =
    status.message.length > 0
      ? status
      : queryMessage
        ? { message: queryMessage, tone: 'neutral' }
        : { message: '', tone: 'neutral' }

  const subtitle = useMemo(() => {
    if (!userEmail) {
      return 'Loading account...'
    }

    if (currentLevelId === null) {
      return `Signed in as ${userEmail}`
    }

    return `Signed in as ${userEmail} · Current level: ${currentLevelId}`
  }, [currentLevelId, userEmail])

  const fetchDashboard = useCallback(
    async () =>
      Promise.all([apiRequest('/api/auth/me', { token }), apiRequest('/api/levels', { token })]),
    [token],
  )

  const loadDashboard = useCallback(async () => {
    setIsLoading(true)
    setStatus({ message: 'Loading levels...', tone: 'neutral' })

    try {
      const [me, levelData] = await fetchDashboard()
      const levelId = Number.isInteger(levelData?.level_id) ? levelData.level_id : null
      if (levelId === null) {
        throw new Error('Server did not return a current level.')
      }
      setUserEmail(me.email)
      setCurrentLevelId(levelId)
      setCompletedLevelIds(
        Array.isArray(levelData?.completed_level_ids)
          ? levelData.completed_level_ids.filter((value) => Number.isInteger(value))
          : [],
      )
      setLevelsCardsGap(resolveCardsGap(levelData))
      setStatus({ message: 'Current level loaded.', tone: 'neutral' })
    } catch (error) {
      if (error?.status === 401) {
        goToRegister('Session expired. Please login again.')
        return
      }

      setStatus({ message: error.message, tone: 'error' })
    } finally {
      setIsLoading(false)
    }
  }, [fetchDashboard])

  useEffect(() => {
    if (!token) {
      goToRegister('Please login first.')
      return
    }

    let cancelled = false

    const bootstrap = async () => {
      try {
        const [me, levelData] = await fetchDashboard()
        const levelId = Number.isInteger(levelData?.level_id) ? levelData.level_id : null
        if (levelId === null) {
          throw new Error('Server did not return a current level.')
        }
        if (cancelled) {
          return
        }

        setUserEmail(me.email)
        setCurrentLevelId(levelId)
        setCompletedLevelIds(
          Array.isArray(levelData?.completed_level_ids)
            ? levelData.completed_level_ids.filter((value) => Number.isInteger(value))
            : [],
        )
        setLevelsCardsGap(resolveCardsGap(levelData))
        setStatus({ message: 'Current level loaded.', tone: 'neutral' })
      } catch (error) {
        if (cancelled) {
          return
        }

        if (error?.status === 401) {
          goToRegister('Session expired. Please login again.')
          return
        }

        setStatus({ message: error.message, tone: 'error' })
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    void bootstrap()

    return () => {
      cancelled = true
    }
  }, [fetchDashboard, token])

  return (
    <main className="levels-page">
      <header className="levels-header">
        <p className="subtitle">{subtitle}</p>
      </header>

      <section className="levels-center" aria-label="Level selection cards">
        <div className="levels-grid" style={{ '--levels-cards-gap': levelsCardsGap }}>
          {Array.from({ length: LEVEL_COUNT }, (_, index) => {
            const levelId = index + 1
            const isCurrent = currentLevelId === levelId
            const isCompleted = completedLevelIds.includes(levelId)
            const isLocked = !isCurrent && !isCompleted

            const cardClassName = [
              'levels-card',
              isCurrent ? 'unlocked' : isLocked ? 'locked' : '',
              isCompleted ? 'completed' : '',
            ]
              .filter(Boolean)
              .join(' ')

            return (
              <button
                key={levelId}
                type="button"
                className={cardClassName}
                disabled={isLoading || !isCurrent}
                onClick={() => {
                  if (isCurrent) {
                    goToPuzzle(levelId)
                  }
                }}
              >
                <span className="levels-card-title">{`Level ${levelId}`}</span>
                <span className="levels-card-state">
                  {isCompleted ? 'Completed' : isCurrent ? 'Current' : 'Locked'}
                </span>
              </button>
            )
          })}
        </div>
      </section>

      <footer className="levels-footer">
        <p className={statusClass(shownStatus.tone)} role="status" aria-live="polite">
          {shownStatus.message}
        </p>
        <div className="button-row">
          <button
            type="button"
            className="secondary"
            disabled={isLoading}
            onClick={() => {
              void loadDashboard()
            }}
          >
            Refresh
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() => {
              goToRegister('Logged out.')
            }}
          >
            Log Out
          </button>
        </div>
      </footer>
    </main>
  )
}

export default LevelsPage
