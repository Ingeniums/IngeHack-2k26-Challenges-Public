import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { apiRequest, clearStoredToken, getStoredToken } from './api'
import { formatDuration, statusClass } from './ui'

function goToRegister(message = '') {
  clearStoredToken()
  const target = new URL('/register.html', window.location.origin)
  if (message) {
    target.searchParams.set('msg', message)
  }
  window.location.replace(target.toString())
}

function goToLevels(message = '') {
  const target = new URL('/levels.html', window.location.origin)
  if (message) {
    target.searchParams.set('msg', message)
  }
  window.location.replace(target.toString())
}

function readLevelSelection() {
  const params = new URLSearchParams(window.location.search)
  const rawLevelId = params.get('levelId')
  const parsedLevelId = Number.parseInt(rawLevelId ?? '', 10)

  return {
    levelId: Number.isInteger(parsedLevelId) && parsedLevelId > 0 ? parsedLevelId : null,
    levelName: params.get('levelName') ?? '',
  }
}

function PuzzlePage() {
  const token = getStoredToken()
  const selectedLevel = useMemo(() => readLevelSelection(), [])

  const [userEmail, setUserEmail] = useState('')
  const [status, setStatus] = useState({ message: '', tone: 'neutral' })
  const [activeLevelId, setActiveLevelId] = useState(null)
  const [activeLevelName, setActiveLevelName] = useState('')
  const [activeLevelRunId, setActiveLevelRunId] = useState(null)
  const [currentPuzzle, setCurrentPuzzle] = useState(null)
  const [tileRotations, setTileRotations] = useState([])
  const [solvedPuzzles, setSolvedPuzzles] = useState(0)
  const [totalPuzzles, setTotalPuzzles] = useState(0)
  const [expiresAtIso, setExpiresAtIso] = useState(null)
  const [secondsRemaining, setSecondsRemaining] = useState(null)
  const [isTimeUp, setIsTimeUp] = useState(false)
  const [isStarting, setIsStarting] = useState(false)
  const [isChecking, setIsChecking] = useState(false)
  const [boardSize, setBoardSize] = useState({ width: 0, height: 0 })
  const [flagPopup, setFlagPopup] = useState(null)

  const boardShellRef = useRef(null)
  const timeoutResetInFlightRef = useRef(false)
  const timeoutPayloadRef = useRef({
    levelRunId: null,
    puzzleId: null,
    rotations: [],
  })

  const hasPuzzle = Boolean(currentPuzzle && activeLevelRunId)
  const timerText = useMemo(() => formatDuration(secondsRemaining), [secondsRemaining])
  const subtitle = useMemo(() => {
    if (activeLevelId !== null && totalPuzzles > 0) {
      const levelText = activeLevelName || `Level ${activeLevelId}`
      return `${levelText} · ${solvedPuzzles}/${totalPuzzles} puzzles`
    }

    if (selectedLevel.levelId !== null) {
      const selectedText = selectedLevel.levelName || `Level ${selectedLevel.levelId}`
      if (userEmail) {
        return `Signed in as ${userEmail} · ${selectedText}`
      }
      return `${selectedText} selected`
    }

    if (userEmail) {
      return `Signed in as ${userEmail}.`
    }

    return 'Loading account...'
  }, [
    activeLevelId,
    activeLevelName,
    selectedLevel.levelId,
    selectedLevel.levelName,
    solvedPuzzles,
    totalPuzzles,
    userEmail,
  ])

  useEffect(() => {
    if (!token) {
      goToRegister('Please login first.')
    }
  }, [token])

  const fitBoard = useCallback(() => {
    if (!boardShellRef.current || !currentPuzzle) {
      return
    }

    const maxWidth = boardShellRef.current.clientWidth
    const maxHeight = boardShellRef.current.clientHeight
    if (!maxWidth || !maxHeight) {
      return
    }

    const boardAspectRatio = currentPuzzle.image_width / currentPuzzle.image_height

    let width = maxWidth
    let height = width / boardAspectRatio

    if (height > maxHeight) {
      height = maxHeight
      width = height * boardAspectRatio
    }

    setBoardSize({ width: Math.floor(width), height: Math.floor(height) })
  }, [currentPuzzle])

  useEffect(() => {
    const handleResize = () => {
      fitBoard()
    }

    window.addEventListener('resize', handleResize)
    const frameId = window.requestAnimationFrame(handleResize)

    return () => {
      window.cancelAnimationFrame(frameId)
      window.removeEventListener('resize', handleResize)
    }
  }, [fitBoard])

  const startCountdown = useCallback((nextExpiresAtIso) => {
    if (!nextExpiresAtIso) {
      setExpiresAtIso(null)
      setSecondsRemaining(null)
      return
    }

    const initialRemaining = Math.max(0, Math.ceil((Date.parse(nextExpiresAtIso) - Date.now()) / 1000))
    setExpiresAtIso(nextExpiresAtIso)
    setSecondsRemaining(initialRemaining)
    setIsTimeUp(initialRemaining <= 0)
  }, [])

  const stopCountdown = useCallback((finalSeconds = null) => {
    setExpiresAtIso(null)
    setSecondsRemaining(finalSeconds)
  }, [])

  useEffect(() => {
    timeoutPayloadRef.current = {
      levelRunId: activeLevelRunId,
      puzzleId: currentPuzzle?.puzzle_id ?? null,
      rotations: tileRotations,
    }
  }, [activeLevelRunId, currentPuzzle, tileRotations])

  const applyPuzzle = useCallback((puzzle) => {
    setCurrentPuzzle(puzzle)
    setTileRotations(Array(puzzle.tiles.length).fill(0))
    setStatus((previous) => {
      if (previous.tone === 'error') {
        return previous
      }
      return { message: '', tone: 'neutral' }
    })
  }, [])

  const resetAfterTimeout = useCallback(async () => {
    const { levelRunId, puzzleId, rotations } = timeoutPayloadRef.current
    if (!levelRunId || !puzzleId) {
      timeoutResetInFlightRef.current = false
      return
    }

    setIsChecking(true)

    try {
      const result = await apiRequest('/api/levels/check', {
        method: 'POST',
        token,
        body: {
          level_run_id: levelRunId,
          puzzle_id: puzzleId,
          rotations,
        },
      })

      if (!result.next_puzzle || result.level_completed) {
        throw new Error('Failed to refresh puzzle after timeout.')
      }

      setSolvedPuzzles(Math.max(0, result.puzzle_number - 1))
      setTotalPuzzles(result.total_puzzles)
      applyPuzzle(result.next_puzzle)
      startCountdown(result.expires_at)
      setIsTimeUp(false)
      setStatus({ message: 'Time is up.', tone: 'error' })
    } catch (error) {
      if (error?.status === 401) {
        goToRegister('Session expired. Please login again.')
        return
      }

      if (error?.status === 404) {
        goToLevels('Level session expired. Start the level again.')
        return
      }

      setStatus({ message: error.message, tone: 'error' })
    } finally {
      timeoutResetInFlightRef.current = false
      setIsChecking(false)
    }
  }, [applyPuzzle, startCountdown, token])

  useEffect(() => {
    if (!expiresAtIso) {
      return undefined
    }

    const intervalId = window.setInterval(() => {
      const remaining = Math.max(0, Math.ceil((Date.parse(expiresAtIso) - Date.now()) / 1000))
      setSecondsRemaining(remaining)

      if (remaining <= 0) {
        setIsTimeUp(true)
        setExpiresAtIso(null)
        setStatus({ message: 'Time is up. Resetting progress...', tone: 'error' })
        if (!timeoutResetInFlightRef.current) {
          timeoutResetInFlightRef.current = true
          void resetAfterTimeout()
        }
      }
    }, 500)

    return () => {
      window.clearInterval(intervalId)
    }
  }, [expiresAtIso, resetAfterTimeout])

  const startLevel = useCallback(
    async (levelIdToStart, levelNameHint = '', forceRestart = false) => {
      if (!levelIdToStart) {
        setStatus({ message: 'Select a valid level first.', tone: 'error' })
        return
      }

      setIsStarting(true)
      const levelText = levelNameHint || `Level ${levelIdToStart}`
      setStatus({ message: `Starting ${levelText}...`, tone: 'neutral' })

      try {
        const response = await apiRequest(`/api/levels/${levelIdToStart}/start`, {
          method: 'POST',
          token,
          body: forceRestart ? { force_restart: true } : undefined,
        })

        setIsTimeUp(false)
        timeoutResetInFlightRef.current = false
        setActiveLevelId(response.level_id)
        setActiveLevelName(response.level_name)
        setActiveLevelRunId(response.level_run_id)
        setSolvedPuzzles(Math.max(0, response.puzzle_number - 1))
        setTotalPuzzles(response.total_puzzles)

        applyPuzzle(response.puzzle)
        startCountdown(response.expires_at)
        setStatus({
          message: `${response.level_name} started. Rotate tiles and press Check.`,
          tone: 'neutral',
        })
      } catch (error) {
        if (error?.status === 401) {
          goToRegister('Session expired. Please login again.')
          return
        }

        setStatus({ message: error.message, tone: 'error' })
      } finally {
        setIsStarting(false)
      }
    },
    [applyPuzzle, startCountdown, token],
  )

  useEffect(() => {
    if (!token) {
      return
    }

    if (selectedLevel.levelId === null) {
      goToLevels('Select a level first.')
      return
    }

    let cancelled = false

    const bootstrap = async () => {
      try {
        const me = await apiRequest('/api/auth/me', { token })
        if (cancelled) {
          return
        }

        setUserEmail(me.email)
        await startLevel(selectedLevel.levelId, selectedLevel.levelName)
      } catch (error) {
        if (cancelled) {
          return
        }

        if (error?.status === 401) {
          goToRegister('Session expired. Please login again.')
          return
        }

        setStatus({ message: error.message, tone: 'error' })
      }
    }

    void bootstrap()

    return () => {
      cancelled = true
    }
  }, [selectedLevel.levelId, selectedLevel.levelName, startLevel, token])

  const checkPuzzle = useCallback(async () => {
    if (!activeLevelRunId || !currentPuzzle) {
      return
    }

    setIsChecking(true)
    setStatus({ message: 'Checking...', tone: 'neutral' })

    try {
      const result = await apiRequest('/api/levels/check', {
        method: 'POST',
        token,
        body: {
          level_run_id: activeLevelRunId,
          puzzle_id: currentPuzzle.puzzle_id,
          rotations: tileRotations,
        },
      })

      if (result.expires_at) {
        startCountdown(result.expires_at)
      }

      if (!result.solved) {
        if (result.next_puzzle) {
          setSolvedPuzzles(Math.max(0, result.puzzle_number - 1))
          setTotalPuzzles(result.total_puzzles)
          applyPuzzle(result.next_puzzle)
          startCountdown(result.expires_at)
          setIsTimeUp(false)
          timeoutResetInFlightRef.current = false
          setStatus({ message: 'Time is up.', tone: 'error' })
          return
        }

        setStatus({ message: 'Wrong answer. 10 seconds penalty applied.', tone: 'error' })
        return
      }

      if (result.level_completed) {
        stopCountdown(0)
        setSolvedPuzzles(result.total_puzzles)
        setTotalPuzzles(result.total_puzzles)
        const completedLevelName = activeLevelName || `Level ${activeLevelId}`
        setStatus({
          message: `${completedLevelName} cleared. Choose another level.`,
          tone: 'success',
        })
        setFlagPopup({
          levelName: completedLevelName,
          flag: result.flag ?? null,
        })
        setActiveLevelRunId(null)
        setCurrentPuzzle(null)
        setTileRotations([])
        return
      }

      if (!result.next_puzzle) {
        throw new Error('Server did not return the next puzzle.')
      }

      setSolvedPuzzles(Math.max(0, result.puzzle_number - 1))
      setTotalPuzzles(result.total_puzzles)
      applyPuzzle(result.next_puzzle)
      setStatus({
        message: `Correct. Puzzle ${result.puzzle_number}/${result.total_puzzles}.`,
        tone: 'success',
      })
    } catch (error) {
      if (error?.status === 401) {
        goToRegister('Session expired. Please login again.')
        return
      }

      if (/time is up/i.test(error.message)) {
        setIsTimeUp(true)
        setStatus({ message: 'Time is up. Resetting progress...', tone: 'error' })
        if (!timeoutResetInFlightRef.current) {
          timeoutResetInFlightRef.current = true
          void resetAfterTimeout()
          return
        }
      }

      setStatus({ message: error.message, tone: 'error' })
    } finally {
      setIsChecking(false)
    }
  }, [
    activeLevelId,
    activeLevelName,
    activeLevelRunId,
    applyPuzzle,
    currentPuzzle,
    startCountdown,
    stopCountdown,
    resetAfterTimeout,
    tileRotations,
    token,
  ])

  const checkDisabled = !hasPuzzle || isChecking || isStarting || isTimeUp
  const restartDisabled = activeLevelId === null || isChecking || isStarting

  return (
    <main className="page">
      <section className="challenge" aria-label="Board Puzzles platform">
        <header className="topbar">
          <div>
            <h1>Board Puzzles</h1>
            <p className="subtitle">{subtitle}</p>
          </div>
          <div className="timer-wrap">
            <span className="timer-label">Time Left</span>
            <strong className="timer" aria-live="polite">
              {timerText}
            </strong>
          </div>
        </header>

        <div className="board-shell" ref={boardShellRef}>
          {currentPuzzle ? (
            <div
              className="tile-board"
              style={{
                width: boardSize.width ? `${boardSize.width}px` : undefined,
                height: boardSize.height ? `${boardSize.height}px` : undefined,
                gridTemplateColumns: `repeat(${currentPuzzle.cols}, minmax(0, 1fr))`,
                gridTemplateRows: `repeat(${currentPuzzle.rows}, minmax(0, 1fr))`,
              }}
              aria-live="polite"
            >
              {currentPuzzle.tiles.map((tileSrc, index) => (
                <button
                  key={`${currentPuzzle.puzzle_id}-${index}`}
                  type="button"
                  className="tile"
                  onClick={() => {
                    setTileRotations((previous) => {
                      const next = [...previous]
                      next[index] = (next[index] ?? 0) + currentPuzzle.rotation_step
                      return next
                    })
                    setStatus({ message: '', tone: 'neutral' })
                  }}
                >
                  <img
                    src={tileSrc}
                    alt={`Puzzle tile ${index + 1}`}
                    loading="lazy"
                    style={{
                      transform: `rotate(${tileRotations[index] ?? 0}deg)`,
                    }}
                  />
                </button>
              ))}
            </div>
          ) : (
            <p className="status">Preparing puzzle...</p>
          )}
        </div>

        <footer className="controls">
          <p className={statusClass(status.tone)} role="status" aria-live="polite">
            {status.message}
          </p>
          <div className="button-row">
            <button
              type="button"
              disabled={checkDisabled}
              onClick={() => {
                void checkPuzzle()
              }}
            >
              Check
            </button>
            <button
              type="button"
              className="secondary"
              disabled={restartDisabled}
              onClick={() => {
                if (activeLevelId === null) {
                  setStatus({ message: 'Select a level first.', tone: 'error' })
                  return
                }

                void startLevel(activeLevelId, activeLevelName, true)
              }}
            >
              Restart Level
            </button>
            <button
              type="button"
              className="secondary"
              disabled={isStarting || isChecking}
              onClick={() => {
                goToLevels('Select a level to continue.')
              }}
            >
              Back to Levels
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
      </section>

      {flagPopup ? (
        <div
          className="flag-modal-backdrop"
          role="dialog"
          aria-modal="true"
          aria-labelledby="completion-title"
        >
          <section className="flag-modal">
            <h2 id="completion-title">Congrats!</h2>
            <p className="subtitle">{`${flagPopup.levelName} cleared.`}</p>
            {flagPopup.flag ? <code className="flag-value">{flagPopup.flag}</code> : null}
            <div className="button-row">
              <button
                type="button"
                onClick={() => {
                  setFlagPopup(null)
                  goToLevels('Level cleared.')
                }}
              >
                Continue
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </main>
  )
}

export default PuzzlePage
