export function formatDuration(totalSeconds) {
  if (totalSeconds === null || totalSeconds === undefined) {
    return '--:--'
  }

  const safeSeconds = Math.max(0, totalSeconds)
  const minutes = String(Math.floor(safeSeconds / 60)).padStart(2, '0')
  const seconds = String(safeSeconds % 60).padStart(2, '0')
  return `${minutes}:${seconds}`
}

export function statusClass(tone) {
  if (tone === 'success') {
    return 'status tone-success'
  }

  if (tone === 'error') {
    return 'status tone-error'
  }

  return 'status'
}
