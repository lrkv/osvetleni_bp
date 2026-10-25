import { computed, onMounted, onUnmounted, ref } from 'vue'
import { resolveBackendUrls } from '../utils/backendUrl.js'

export function useLighting() {
  const data = ref(null)
  const hardware = ref(null)
  const clock = ref(null)
  const configurationErrors = ref([])
  const availableAlgorithms = ref([])
  const connected = ref(false)
  const error = ref('')
  const pending = computed(() => !data.value && !error.value)
  let urls
  let socket
  let retryTimer
  let connectTimer
  let retryDelay = 500
  let disposed = false

  const scheduleReconnect = () => {
    if (disposed) return
    clearTimeout(retryTimer)
    retryTimer = setTimeout(connect, retryDelay)
    retryDelay = Math.min(retryDelay * 2, 10000)
  }

  async function connect() {
    try {
      if (!urls) {
        const response = await fetch('/backend-config.json', {
          cache: 'no-store', signal: AbortSignal.timeout(5000),
        })
        if (!response.ok) throw new Error('Nelze načíst backend-config.json.')
        urls = resolveBackendUrls(await response.json(), window.location.href)
      }
      if (disposed) return
      const current = new WebSocket(urls.websocket)
      socket = current
      connectTimer = setTimeout(() => current.close(), 10000)
      current.onmessage = (event) => {
        if (disposed || socket !== current) return
        try {
          const message = JSON.parse(event.data)
          if (message.clock) clock.value = message.clock
          if (message.type !== 'state') return
          data.value = message.structure
          hardware.value = message.hardware
          configurationErrors.value = message.configuration_errors || []
          availableAlgorithms.value = message.algorithms
          connected.value = true
          error.value = ''
          retryDelay = 500
          clearTimeout(connectTimer)
        } catch {
          error.value = 'Backend poslal neplatná data.'
          current.close()
        }
      }
      current.onerror = () => {
        error.value = 'Spojení s backendem selhalo. Připojení se automaticky obnoví.'
      }
      current.onclose = () => {
        if (disposed || socket !== current) return
        clearTimeout(connectTimer)
        connected.value = false
        error.value = 'Backend je odpojený. Zobrazený stav nemusí být aktuální.'
        scheduleReconnect()
      }
    } catch (cause) {
      if (disposed) return
      connected.value = false
      error.value = cause.message
      scheduleReconnect()
    }
  }

  async function updateAlgorithm(id, algorithm) {
    if (!connected.value) throw new Error('Backend není připojený.')
    await $fetch(new URL('api/algorithm', urls.http).href, {
      method: 'POST',
      body: { item_id: id, new_algorithm: algorithm },
      timeout: 5000,
      retry: 0,
    })
    // The WebSocket supplies authoritative state to every connected browser.
  }

  const clockType = computed(() => !clock.value ? 'Čas' :
    clock.value.source === 'system' ? 'Reálný čas' : 'Modelový čas hJOP')
  const clockSpeed = computed(() => {
    const value = clock.value
    if (!value) return ''
    if (value.source === 'system') return 'Rychlost: 1×'
    if (!value.time) return 'Zrychlení: čekám na synchronizaci'
    return 'Zrychlení: ' + new Intl.NumberFormat('cs-CZ').format(value.speed) + '×'
  })

  const clockStatus = computed(() => {
    if (!connected.value) return 'Backend odpojený – zobrazený čas není aktuální.'
    const value = clock.value
    if (!value) return 'Čekám na čas z hJOP…'
    if (value.source === 'system') return 'Systémový čas backendu'
    if (!value.connected) return 'hJOP odpojeno – čas je zastavený.'
    if (!value.available) return value.used ? 'Čekám na synchronizaci hJOP…' : 'Modelový čas není aktivní.'
    return value.running ? 'Běží' : 'Pozastaveno'
  })

  const hardwareMessage = computed(() => {
    const state = hardware.value
    if (!state) return ''
    if (!state.connected) return 'MTB démon je odpojený; změny čekají na připojení.'
    if (state.error) return state.error
    const errors = Object.entries(state.module_errors)
    if (errors.length) return errors.map(([id, text]) => 'Modul ' + id + ': ' + text).join(' · ')
    if (state.pending_modules.length) return 'Čeká se na potvrzení MTB démona.'
    return 'MTB démon potvrdil požadované nastavení.'
  })

  onMounted(connect)
  onUnmounted(() => {
    disposed = true
    clearTimeout(retryTimer)
    clearTimeout(connectTimer)
    socket?.close()
  })

  return { data, hardware, clock, clockType, clockSpeed, clockStatus, configurationErrors, availableAlgorithms, connected, error, pending,
    hardwareMessage, updateAlgorithm }
}
