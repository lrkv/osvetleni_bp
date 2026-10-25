export function resolveBackendUrls(config, pageUrl) {
  const page = new URL(pageUrl)
  let base
  if (config.backendUrl) {
    base = new URL(config.backendUrl, page)
  } else {
    base = new URL(page.origin)
    base.port = String(config.backendPort ?? 8000)
  }
  if (!['http:', 'https:'].includes(base.protocol)) {
    throw new Error('Adresa backendu musí začínat http:// nebo https://.')
  }
  if (page.protocol === 'https:' && base.protocol !== 'https:') {
    throw new Error('Pro stránku přes HTTPS nastavte také HTTPS adresu backendu.')
  }
  base.pathname = base.pathname.replace(/\/+$/, '') + '/'
  base.search = ''
  base.hash = ''
  const websocket = new URL('api/ws', base)
  websocket.protocol = base.protocol === 'https:' ? 'wss:' : 'ws:'
  return { http: base.href, websocket: websocket.href }
}
