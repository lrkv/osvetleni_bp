<template>
  <main class="events-page">
    <div class="section-title"><h1>Budoucí události</h1><span class="muted small">Od nejbližší změny</span></div>
    <p class="muted small legend-note">Denní rozvrhy na příštích 24 hodin, dvě nejbližší změny algoritmu Minuta a naplánované náhodné změny. Odpočet je ve skutečném čase, se započtením zrychlení hJOP. Přepnutí může nastat při následujícím sekundovém přepočtu.</p>
    <p v-if="!connected" class="error-box" role="status">Backend je odpojený. Události a odpočty nejsou aktuální.</p>
    <p v-else-if="!upcoming" class="muted">Čekám na plán událostí. Pokud se nezobrazí, restartujte aktualizovaný backend.</p>
    <template v-if="upcoming">
      <p v-if="upcoming.model_paused" class="muted small legend-note">Modelový čas neběží. Změny podle něj čekají; skutečné časovače chodby a domácností pokračují.</p>
      <p v-if="!upcoming.events.length" class="events-empty">Žádné změny se známým časem. Trvale zapnutá a vypnutá světla nemají automatickou událost.</p>
      <ol class="event-list">
        <li v-for="group in groupedEvents" :key="group.key" class="event-card">
          <div class="event-timing">
            <strong>{{ connected ? countdown(group.seconds) : 'Neaktuální' }}</strong>
            <span v-if="group.kind === 'latest'" class="muted small">Nejpozději</span>
            <template v-if="group.model_time">
              <span class="event-model-time">hJOP {{ group.model_time }}{{ daySuffix(group.model_day_offset) }}</span>
              <small class="muted">{{ group.basis === 'model' ? 'Modelový čas změny' : 'Odhad při aktuálním zrychlení' }}</small>
            </template>
            <small v-else-if="clock?.source === 'hjop'" class="muted">Čas hJOP nelze určit, dokud neběží.</small>
            <span v-if="group.basis === 'real'" class="muted small">Reálně {{ group.time }}{{ daySuffix(group.day_offset) }}</span>
            <span v-if="group.seconds === null && group.basis === 'model'" class="muted small">Čeká na spuštění modelového času</span>
          </div>
          <div class="event-lights">
            <article v-for="event in group.lights" :key="event.id" class="event-description" :class="{ 'event-on': event.on }">
              <span class="event-action"><i class="status-dot" :class="event.on ? 'all' : 'none'"></i>{{ event.on ? 'Rozsvítí se' : 'Zhasne' }}</span>
              <h2>{{ event.name }}</h2><p class="muted small">{{ event.path }}</p>
              <p class="muted small">{{ algorithmLabel(event.algorithm) }}<span v-if="showAddress"> · Adresa {{ event.address }}</span><span v-if="showId"> · ID {{ event.id }}</span></p>
              <p v-if="event.kind === 'latest'" class="muted small">Při snížení požadovaného podílu může zhasnout dříve.</p>
            </article>
          </div>
        </li>
      </ol>
      <details v-if="upcoming.unknown.length" class="events-unknown"><summary>Čas dalšího rozsvícení zatím není určený ({{ upcoming.unknown.length }})</summary><p class="muted small">Budoucí náhodné volby se nepočítají dopředu. Událost se objeví, jakmile ji algoritmus naplánuje.</p><ul><li v-for="item in upcoming.unknown" :key="item.id"><strong>{{ item.name }}</strong><span class="muted small"> — {{ item.reason }}</span></li></ul></details>
    </template>
  </main>
</template>
<script setup>
import { computed, inject } from 'vue'
import { groupEvents } from '../utils/eventGroups.js'
const { upcoming, connected, algorithmLabel, clock } = inject('lighting')
const { showAddress, showId } = inject('appearance')
const groupedEvents = computed(() => groupEvents(upcoming.value?.events || []))
const daySuffix = days => days > 0 ? ` (+${days} den)` : ''
useHead({ title: 'Budoucí události – Osvětlení kolejiště' })
function countdown(seconds) {
  if (seconds === null) return 'Čeká na běh času'
  if (seconds <= 0) return 'Při nejbližším přepočtu'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor(seconds % 3600 / 60)
  return 'Za ' + (hours ? `${hours} h ` : '') + (minutes ? `${minutes} min ` : '') + `${seconds % 60} s`
}
</script>
