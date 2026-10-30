export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: false },
  app: {
    head: {
      link: [
        { rel: 'icon', type: 'image/x-icon', href: '/favicon-lighting.ico' },
        { rel: 'icon', type: 'image/png', sizes: '32x32', href: '/lighting-icon-32.png' },
        { rel: 'apple-touch-icon', sizes: '180x180', href: '/lighting-apple-touch-icon.png' },
      ],
    },
  },
  devServer: { host: '0.0.0.0', port: 3000 },
  modules: ['@nuxtjs/tailwindcss']
})
