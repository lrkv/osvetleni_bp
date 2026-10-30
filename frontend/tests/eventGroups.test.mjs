import assert from 'node:assert/strict'
import test from 'node:test'
import { groupEvents } from '../app/utils/eventGroups.js'

test('simultaneous lights share one countdown, keeping different actions', () => {
  const first = { id: 1, basis: 'model', at_key: '2000-01-02T19:00:00', kind: 'scheduled', seconds: 6, on: true }
  const groups = groupEvents([first, { ...first, id: 2, on: false }, { ...first, id: 3, at_key: '2000-01-02T19:01:00', seconds: 12 }])
  assert.equal(groups.length, 2)
  assert.deepEqual(groups[0].lights.map(light => light.id), [1, 2])
  assert.equal(groups[0].lights[1].on, false)
})
test('rounded countdowns, different days and deadline bounds are not merged', () => {
  const first = { id: 1, basis: 'real', at_key: '2026-10-30T19:00:00', kind: 'scheduled', seconds: 6 }
  assert.equal(groupEvents([first, { ...first, id: 2, kind: 'latest' }, { ...first, id: 3, at_key: '2026-10-31T19:00:00' }]).length, 3)
})
