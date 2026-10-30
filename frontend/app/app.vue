<template>
  <div class="lighting-app" :class="{ 'map-view': route.path === '/mapa' }" :data-theme="darkMode ? 'dark' : 'light'" :data-accent="accent" :style="themeStyle">
    <header class="topbar">
      <div class="topbar-inner">
        <div class="layout-heading">
          <div class="layout-title">{{ data?.layout_name || 'Osvětlení kolejiště' }}</div>
          <p v-if="data?.location" class="layout-location">{{ data.location }}</p>
          <p v-if="data?.note" class="layout-note" :title="data.note">{{ data.note }}</p>
        </div>
        <div class="clock-panel">
          <div class="clock-face">
            <span class="eyebrow">{{ clockType }}</span>
            <time>{{ clock?.time || '--:--:--' }}</time>
          </div>
          <div class="clock-meta">
            <strong>{{ clockSpeed || 'Čekám na čas' }}</strong>
            <span>{{ clockStatus }}</span>
          </div>
        </div>
        <button class="settings-button" @click="toggleSettings" :aria-expanded="settingsOpen" aria-controls="appearance-settings" aria-label="Nastavení vzhledu">⚙ <span>Vzhled</span></button>
      </div>
      <nav class="view-navigation" aria-label="Zobrazení kolejiště">
        <NuxtLink to="/" class="view-link" exact-active-class="is-active">Seznam</NuxtLink>
        <NuxtLink to="/mapa" class="view-link" exact-active-class="is-active">Mapa</NuxtLink>
        <NuxtLink to="/udalosti" class="view-link" exact-active-class="is-active">Budoucí události</NuxtLink>
      </nav>
    </header>

    <div class="page-content">
      <section v-if="settingsOpen" id="appearance-settings" class="settings-panel" aria-label="Nastavení vzhledu">
        <div class="section-title"><h2>Nastavení vzhledu</h2><button class="text-button" @click="settingsOpen = false">Zavřít</button></div>
        <div class="settings-options">
          <label class="check-option"><input type="checkbox" v-model="darkMode"> Tmavý režim</label>
          <label class="check-option"><input type="checkbox" v-model="showAddress"> Zobrazit adresy</label>
          <label class="check-option"><input type="checkbox" v-model="showId"> Zobrazit ID</label>
          <label class="check-option"><input type="checkbox" v-model="showAlgorithm"> Zobrazit algoritmy v mapě</label>
        </div>
        <fieldset class="theme-options"><legend>Barevný motiv</legend>
          <label v-for="theme in themes" :key="theme.value" class="theme-choice">
            <input type="radio" name="accent" :value="theme.value" v-model="accent">
            <span class="swatch" :style="{ background: theme.color }"></span>{{ theme.label }}
          </label>
        </fieldset>
        <p class="muted small">Nastavení se ukládá v tomto prohlížeči. Černý motiv používá černé pozadí a bílé doplňky. Žlutá vždy označuje rozsvícená světla.</p>
      </section>

      <section class="connection-status" aria-label="Stav připojení">
        <p v-if="pending">Načítám konfiguraci…</p>
        <p v-if="error" class="error-text" role="alert">{{ error }}</p>
        <p v-if="clock?.error" class="error-text">hJOP: {{ clock.error }}</p>
        <p v-if="hardware" role="status">{{ hardwareMessage }}</p>
        <div v-if="configurationErrors.length" class="error-box" role="alert">
          <strong>Nepodporované algoritmy – vyberte jiný režim:</strong>
          <p v-for="issue in configurationErrors" :key="issue.id">{{ issue.name }}: {{ issue.message }}</p>
        </div>
      </section>

      <NuxtPage />
    </div>
  </div>
</template>

<script setup>
import { provide, ref, nextTick, computed } from 'vue'
import './assets/lighting.css'
const route = useRoute()
const lighting = useLighting()
const { data, pending, error, hardware, hardwareMessage, configurationErrors, clock, clockType, clockSpeed, clockStatus } = lighting
// Barvy motivů se nastavují pouze zde. color = hlavní barva,
// ink = barva textu na ní. U černého motivu je color barva náhledu,
// accent je jeho bílá doplňková barva.
const themes = [
  { value: 'yellow', label: 'Žlutý', color: '#fffa4b', ink: '#363300' },
  { value: 'green', label: 'Zelený', color: '#36f608', ink: '#102900' },
  { value: 'blue', label: 'Modrý', color: '#0871f4', ink: '#ffffff' },
  { value: 'red', label: 'Červený', color: '#cd0f0f', ink: '#ffffff' },
  { value: 'cyan', label: 'Cyan', color: '#00e5ff', ink: '#00343b' },
  { value: 'black', label: 'Černý', color: '#111111', accent: '#ffffff', ink: '#111111' },
]
const appearance = useAppearance(themes)
const { darkMode, accent, showAddress, showId, showAlgorithm } = appearance
const themeStyle = computed(() => {
  const theme = themes.find(item => item.value === accent.value) || themes[0]
  return { '--accent': theme.accent || theme.color, '--accent-ink': theme.ink }
})
const settingsOpen = ref(false)
async function toggleSettings() {
  settingsOpen.value = !settingsOpen.value
  if (settingsOpen.value) {
    await nextTick()
    document.getElementById('appearance-settings')?.scrollIntoView({ block: 'start' })
  }
}

provide('lighting', lighting)
provide('appearance', appearance)
</script>
