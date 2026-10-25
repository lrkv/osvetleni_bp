<template>
  <div class="railway-node">
    <section v-if="node.items" class="node-group">
      <div class="group-header">
        <button class="group-toggle" @click="isOpen = !isOpen" :aria-expanded="isOpen">
          <svg class="chevron" :class="{ expanded: isOpen }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="m9 5 7 7-7 7" /></svg>
          <span class="group-name">{{ node.name }}<small v-if="node.note">{{ node.note }}</small></span>

        </button>
        <span class="node-state" :title="statusLabels[groupStatus]" :aria-label="statusLabels[groupStatus]" role="img"><i class="status-dot" :class="groupStatus"></i></span>
        <select :disabled="saving || !connected" @change="updateGroup" :aria-label="'Změnit algoritmus celé skupiny ' + node.name">
          <option value="" disabled selected>Změnit vše na…</option>
          <option v-for="algo in availableAlgorithms" :key="algo" :value="algo">{{ algo }}</option>
        </select>
      </div>
      <div v-show="isOpen" class="group-children">
        <RailwayNode v-for="child in node.items" :key="child.id" :node="child" />
      </div>
    </section>
    <article v-else class="light-card" :class="{ 'is-on': node.is_on }">
      <span class="node-state" :title="node.is_on ? 'Svítí' : 'Vypnuto'" :aria-label="node.is_on ? 'Svítí' : 'Vypnuto'" role="img"><i class="status-dot" :class="node.is_on ? 'all' : 'none'"></i></span>
      <div class="light-description">
        <div class="light-heading"><h3>{{ node.name }}</h3></div>
        <p v-if="node.note" class="muted small">{{ node.note }}</p>
        <div v-if="showAddress || showId" class="light-details">
          <span v-if="showAddress">Adresa: <strong>{{ node.address }}</strong></span>
          <span v-if="showId">ID: {{ node.id }}</span>
        </div>
      </div>
      <select :disabled="saving || !connected" :value="node.algorithm" @change="updateSingle" :aria-label="'Algoritmus světla ' + node.name">
        <option v-if="!availableAlgorithms.includes(node.algorithm)" :value="node.algorithm" disabled>{{ node.algorithm || 'Chybějící algoritmus' }} (nepodporováno)</option>
        <option v-for="algo in availableAlgorithms" :key="algo" :value="algo">{{ algo }}</option>
      </select>
    </article>
  </div>
</template>

<script setup>
import { ref, computed, inject } from 'vue'

const props = defineProps({
  node: {
    type: Object,
    required: true
  }
})

const isOpen = ref(false)
const { showAddress, showId } = inject('appearance')
const statusLabels = { all: 'Vše svítí', some: 'Část svítí', none: 'Vypnuto' }

const { availableAlgorithms, connected, updateAlgorithm } = inject('lighting')
const saving = ref(false)

// NOVÉ: Chytrý výpočet stavu pro celou skupinu
const groupStatus = computed(() => {
  if (!props.node.items) return null;

  let total = 0;
  let onCount = 0;

  // Interní rekurzivní funkce, která se zanoří klidně až na dno struktury
  const countStates = (items) => {
    for (const child of items) {
      if (child.address !== undefined) {
        total++;
        if (child.is_on) onCount++;
      }
      if (child.items) {
        countStates(child.items); // Zanoření do dalších podskupin
      }
    }
  }

  countStates(props.node.items);

  if (total === 0) return 'none'; // Ve skupině nejsou žádná světla
  if (onCount === total) return 'all'; // Svítí naprosto všechno
  if (onCount > 0) return 'some'; // Svítí alespoň jedno
  return 'none'; // Nesvítí nic
})

async function updateGroup(event) {
  const select = event.target
  await sendToBackend(props.node.id, select.value)
  select.value = ''
}

async function updateSingle(event) {
  const select = event.target
  const success = await sendToBackend(props.node.id, select.value)
  if (!success) select.value = props.node.algorithm
}

async function sendToBackend(id, newAlgorithm) {
  if (!newAlgorithm || saving.value) return false
  saving.value = true
  try {
    await updateAlgorithm(id, newAlgorithm)
    return true
  } catch (error) {
    alert(error.data?.detail || error.message || 'Nepodařilo se změnit algoritmus.')
    return false
  } finally {
    saving.value = false
  }
}
</script>
