<template>
  <main v-if="data" class="map-page">
    <div class="section-title"><h1>Mapa</h1><span class="muted small">Přehled osvětlení</span></div>
    <div class="legend" aria-label="Stavy skupin">
      <span><i class="status-dot all"></i>Vše svítí</span>
      <span><i class="status-dot some"></i>Část svítí</span>
      <span><i class="status-dot none"></i>Vypnuto</span>
    </div>
    <p class="muted small legend-note">Žluté obdélníky označují rozsvícená světla. Barvy ukazují požadovaný stav podle algoritmu.</p>
    <section class="map-layout" :aria-label="data.layout_name || 'Kolejiště'">
      <h2 class="map-layout-title">{{ data.layout_name || 'Kolejiště' }}</h2>
      <MapGroup :nodes="data.groups || []" />
      <p v-if="!data.groups?.length" class="muted small">V této konfiguraci nejsou žádné skupiny ani světla.</p>
    </section>
  </main>
</template>

<script setup>
import { inject } from 'vue'
const { data } = inject('lighting')
useHead({ title: 'Mapa – Osvětlení kolejiště' })
</script>
