<template>
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
</template>

<script setup>
import { inject } from 'vue'
const { data } = inject('lighting')
useHead({ title: 'Osvětlení kolejiště' })
</script>
