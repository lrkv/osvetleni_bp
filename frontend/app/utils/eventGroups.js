export function groupEvents(events) {
  const groups = new Map()
  for (const event of events) {
    // Do not merge independent timers merely because their rounded countdowns match.
    const key = [event.basis, event.at_key || `${event.day_offset}:${event.time}`, event.kind].join('|')
    if (!groups.has(key)) groups.set(key, { ...event, key, lights: [] })
    groups.get(key).lights.push(event)
  }
  return [...groups.values()]
}
