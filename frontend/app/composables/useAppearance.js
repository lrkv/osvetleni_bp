import { onMounted, ref, watch } from 'vue'

export function useAppearance(themes) {
  const darkMode = ref(false)
  const accent = ref('yellow')
  const showAddress = ref(false)
  const showId = ref(false)
  const showAlgorithm = ref(false)
  onMounted(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('lighting-appearance') || '{}')
      darkMode.value = typeof saved.darkMode === 'boolean' ? saved.darkMode : window.matchMedia('(prefers-color-scheme: dark)').matches
      if (themes.some(theme => theme.value === saved.accent)) accent.value = saved.accent
      showAddress.value = saved.showAddress === true
      showId.value = saved.showId === true
      showAlgorithm.value = saved.showAlgorithm === true
    } catch { /* Storage may be unavailable in private mode. */ }
    watch([darkMode, accent, showAddress, showId, showAlgorithm], () => {
      try {
        localStorage.setItem('lighting-appearance', JSON.stringify({
          darkMode: darkMode.value, accent: accent.value,
          showAddress: showAddress.value, showId: showId.value, showAlgorithm: showAlgorithm.value,
        }))
      } catch { /* Settings still work for the current page. */ }
    })
  })
  return { darkMode, accent, showAddress, showId, showAlgorithm }
}
