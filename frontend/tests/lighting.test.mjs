import assert from 'node:assert/strict'
import test from 'node:test'
import { createRenderer, nextTick } from 'vue'
import { resolveBackendUrls } from '../app/utils/backendUrl.js'
import { useLighting } from '../app/composables/useLighting.js'

test('LAN URL uses the browser hostname, never visitor localhost', () => {
  assert.deepEqual(resolveBackendUrls({ backendUrl: '', backendPort: 8000 }, 'http://192.168.1.20:3000/'), {
    http: 'http://192.168.1.20:8000/', websocket: 'ws://192.168.1.20:8000/api/ws',
  })
})

test('separate server and proxy path apply to HTTP and WebSocket', () => {
  assert.deepEqual(resolveBackendUrls({ backendUrl: 'https://backend.example/lighting/' }, 'https://frontend.example/'), {
    http: 'https://backend.example/lighting/', websocket: 'wss://backend.example/lighting/api/ws',
  })
})

test('same-origin proxy and IPv6 are supported', () => {
  assert.equal(resolveBackendUrls({ backendUrl: '/' }, 'https://lights.example/').websocket,
    'wss://lights.example/api/ws')
  assert.equal(resolveBackendUrls({ backendPort: 8000 }, 'http://[::1]:3000/').http, 'http://[::1]:8000/')
})

test('mixed content and invalid protocols fail with a useful message', () => {
  assert.throws(() => resolveBackendUrls({ backendUrl: 'http://backend/' }, 'https://frontend/'), /HTTPS/)
  assert.throws(() => resolveBackendUrls({ backendUrl: 'file:///tmp/' }, 'http://frontend/'), /http/)
})

test('UI receives pushes, reconnects, sends commands and cleans up', async () => {
  const originals = Object.fromEntries(['window', 'WebSocket', 'fetch', '$fetch'].map(key => [key, globalThis[key]]))
  const sockets = []
  let configReads = 0
  const posts = []
  globalThis.window = { location: { href: 'http://192.168.1.20:3000/' } }
  globalThis.fetch = async () => {
    configReads++
    return { ok: true, json: async () => ({ backendPort: 8000 }) }
  }
  globalThis.$fetch = async (url, options) => { posts.push({ url, options }) }
  globalThis.WebSocket = class {
    constructor(url) { this.url = url; this.closed = false; sockets.push(this) }
    close() { this.closed = true; this.onclose?.() }
    push(message) { this.onmessage({ data: JSON.stringify(message) }) }
  }
  const renderer = createRenderer({
    createElement: () => ({}), createText: () => ({}), createComment: () => ({}),
    insert() {}, remove() {}, setElementText() {}, setText() {}, patchProp() {},
    parentNode: () => null, nextSibling: () => null,
  })
  let lighting
  const app = renderer.createApp({ setup() { lighting = useLighting(); return () => null } })
  try {
    app.mount({})
    await nextTick()
    await new Promise(resolve => setTimeout(resolve, 10))
    assert.equal(sockets.length, 1)
    assert.equal(sockets[0].url, 'ws://192.168.1.20:8000/api/ws')
    const state = { type: 'state', structure: { layout_name: 'Test' }, algorithms: ['disco'], algorithm_labels: { disco: 'Blikání (disco)' },
      hardware: { connected: true, error: null, module_errors: {}, pending_modules: [] } }
    sockets[0].push(state)
    assert.equal(lighting.connected.value, true)
    assert.equal(lighting.data.value.layout_name, 'Test')
    const originalTree = lighting.data.value
    sockets[0].push({ type: 'events', upcoming: { events: [{ id: 1, on: true, seconds: 20 }], unknown: [] } })
    assert.equal(lighting.upcoming.value.events[0].seconds, 20)
    assert.equal(lighting.data.value, originalTree)
    const modelClock = { source: 'hjop', time: '02:25:21', connected: true,
      available: true, used: true, running: true, speed: 9 }
    sockets[0].push({ type: 'clock', clock: modelClock })
    assert.equal(lighting.clockType.value, 'Modelový čas hJOP')
    assert.equal(lighting.clockSpeed.value, 'Zrychlení: 9×')
    assert.equal(lighting.clockStatus.value, 'Běží')
    assert.equal(lighting.data.value, originalTree)
    sockets[0].push({ type: 'clock', clock: { ...modelClock, running: false, speed: 2.5 } })
    assert.equal(lighting.clockStatus.value, 'Pozastaveno')
    assert.equal(lighting.clockSpeed.value, 'Zrychlení: 2,5×')
    sockets[0].push({ type: 'clock', clock: { source: 'system', time: '12:00:00', speed: 1 } })
    assert.equal(lighting.clockType.value, 'Reálný čas')
    assert.equal(lighting.clockSpeed.value, 'Rychlost: 1×')
    sockets[0].push({ type: 'clock', clock: { ...modelClock, connected: false } })
    assert.match(lighting.clockStatus.value, /odpojeno/)
    assert.equal(lighting.algorithmLabel('disco'), 'Blikání (disco)')
    assert.equal(lighting.algorithmLabel('new_mode'), 'new mode')
    await lighting.updateAlgorithm(3, 'disco')
    assert.equal(posts[0].url, 'http://192.168.1.20:8000/api/algorithm')
    assert.deepEqual(posts[0].options.body, { item_id: 3, new_algorithm: 'disco' })
    sockets[0].close()
    assert.equal(lighting.connected.value, false)
    await assert.rejects(lighting.updateAlgorithm(3, 'disco'), /připojený/)
    await new Promise(resolve => setTimeout(resolve, 550))
    assert.equal(sockets.length, 2)
    sockets[1].push(state)
    assert.equal(lighting.connected.value, true)
    assert.equal(configReads, 1) // No periodic HTTP fetch or refresh.
    app.unmount()
    assert.equal(sockets[1].closed, true)
    await new Promise(resolve => setTimeout(resolve, 550))
    assert.equal(sockets.length, 2)
  } finally {
    app.unmount()
    for (const [key, value] of Object.entries(originals)) {
      if (value === undefined) delete globalThis[key]
      else globalThis[key] = value
    }
  }
})
