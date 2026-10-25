<template>
  <div class="lighting-app" :data-theme="darkMode ? 'dark' : 'light'" :data-accent="accent">
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
    </header>

    <div class="page-content">
      <section v-if="settingsOpen" id="appearance-settings" class="settings-panel" aria-label="Nastavení vzhledu">
        <div class="section-title"><h2>Nastavení vzhledu</h2><button class="text-button" @click="settingsOpen = false">Zavřít</button></div>
        <div class="settings-options">
          <label class="check-option"><input type="checkbox" v-model="darkMode"> Tmavý režim</label>
          <label class="check-option"><input type="checkbox" v-model="showAddress"> Zobrazit adresy</label>
          <label class="check-option"><input type="checkbox" v-model="showId"> Zobrazit ID</label>
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

      <main v-if="data" class="layout-content">
        <div class="section-title"><h1>Osvětlení</h1><span class="muted small">{{ data.version ? 'Verze ' + data.version : '' }}</span></div>
        <div class="legend" aria-label="Stavy skupin">
          <span><i class="status-dot all"></i>Vše svítí</span>
          <span><i class="status-dot some"></i>Část svítí</span>
          <span><i class="status-dot none"></i>Vypnuto</span>
        </div>
        <p class="muted small legend-note">Barvy ukazují požadovaný stav podle algoritmu.</p>
        <RailwayNode v-for="group in data.groups" :key="group.id" :node="group" />
      </main>
    </div>
  </div>
</template>

<script setup>
import { provide, ref, nextTick } from 'vue'
import './assets/lighting.css'
const lighting = useLighting()
const { data, pending, error, hardware, hardwareMessage, configurationErrors, clock, clockType, clockSpeed, clockStatus } = lighting
const appearance = useAppearance()
const { darkMode, accent, showAddress, showId } = appearance
const settingsOpen = ref(false)
async function toggleSettings() {
  settingsOpen.value = !settingsOpen.value
  if (settingsOpen.value) {
    await nextTick()
    document.getElementById('appearance-settings')?.scrollIntoView({ block: 'start' })
  }
}
const themes = [
  { value: 'yellow', label: 'Žlutý', color: '#fffa4b' },
  { value: 'green', label: 'Zelený', color: '#36f608' },
  { value: 'blue', label: 'Modrý', color: '#0871f4' },
  { value: 'red', label: 'Červený', color: '#cd0f0f' },
  { value: 'black', label: 'Černý', color: '#111111' },
  { value: 'cyan', label: 'Cyan', color: '#00FFFF' },
]
provide('lighting', lighting)
provide('appearance', appearance)
</script>
