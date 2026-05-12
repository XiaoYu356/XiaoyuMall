export const parseTime = (time) => {
  if (!time) return null
  return new Date(time.replace(/ /g, 'T'))
}

export const formatDate = (time) => {
  const d = parseTime(time)
  if (!d) return ''
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export const formatDateTime = (time) => {
  const d = parseTime(time)
  if (!d) return null
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}
