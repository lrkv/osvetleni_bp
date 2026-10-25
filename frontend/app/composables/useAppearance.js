import { onMounted, ref, watch } from 'vue'

export function useAppearance() {
  const darkMode = ref(false)
  const accent = ref('yellow')
  const showAddress = ref(false)
  const showId = ref(false)
  onMounted(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('lighting-appearance') || '{}')
      darkMode.value = typeof saved.darkMode === 'boolean' ? saved.darkMode : window.matchMedia('(prefers-color-scheme: dark)').matches
      if (['yellow', 'green', 'blue', 'red', 'black'].includes(saved.accent)) accent.value = saved.accent
      showAddress.value = saved.showAddress === true
      showId.value = saved.showId === true
    } catch { /* Storage may be unavailable in private mode. */ }
    watch([darkMode, accent, showAddress, showId], () => {
      try {
        localStorage.setItem('lighting-appearance', JSON.stringify({
          darkMode: darkMode.value, accent: accent.value,
          showAddress: showAddress.value, showId: showId.value,
        }))
      } catch { /* Settings still work for the current page. */ }
    })
  })
  return { darkMode, accent, showAddress, showId }
}
