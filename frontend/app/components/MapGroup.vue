<template>
  <div class="map-contents">
    <div v-if="lights.length" class="map-lights" :style="columnWidths(lights.length)" :class="{ 'has-details': showAddress || showId || showAlgorithm }">
      <article v-for="light in lights" :key="light.id" class="map-light" :class="{ 'is-on': light.is_on }" :aria-label="light.name + (light.is_on ? ' – svítí' : ' – vypnuto')">
        <span class="map-light-status"><i class="status-dot" :class="light.is_on ? 'all' : 'none'" aria-hidden="true"></i>{{ light.is_on ? 'Svítí' : 'Vypnuto' }}</span>
        <h3>{{ light.name }}</h3>
        <dl v-if="showAddress || showId || showAlgorithm" class="map-light-details">
          <div v-if="showAddress"><dt>Adresa</dt><dd>{{ light.address }}</dd></div>
          <div v-if="showId"><dt>ID</dt><dd>{{ light.id }}</dd></div>
          <div v-if="showAlgorithm"><dt>Algoritmus</dt><dd>{{ algorithmLabel(light.algorithm) }}</dd></div>
        </dl>
      </article>
    </div>
    <section v-for="group in groups" :key="group.id" class="map-group" :style="columnWidths(groupWidth(group), 2)" :aria-label="group.name">
      <header class="map-group-heading">
        <div><h3>{{ group.name }}</h3><p v-if="group.note" class="muted small">{{ group.note }}</p></div>
        <span class="map-group-state" :title="stateLabel(group)">
          <span>{{ totals(group).on }}/{{ totals(group).total }}</span>
          <i class="status-dot" :class="state(group)" :aria-label="stateLabel(group)" role="img"></i>
        </span>
      </header>
      <MapGroup :nodes="group.items || []" />
      <p v-if="!group.items?.length" class="muted small">Prázdná skupina</p>
    </section>
  </div>
</template>

<script setup>
import { computed, inject } from 'vue'
const props = defineProps({ nodes: { type: Array, required: true } })
const { showAddress, showId, showAlgorithm } = inject('appearance')
const { algorithmLabel } = inject('lighting')
const lights = computed(() => props.nodes.filter(node => node.address !== undefined))
const groups = computed(() => props.nodes.filter(node => node.items !== undefined))
function columnWidths(count, minimum = 1) {
  return Object.fromEntries([2, 4, 6, 8].map(columns => [
    `--width-${columns}`, Math.min(columns, Math.max(minimum, count)),
  ]))
}
function groupWidth(node) {
  const children = node.items || []
  const width = children.reduce((sum, child) => sum + (
    child.items !== undefined ? groupWidth(child) : child.address !== undefined ? 1 : 0
  ), 0)
  return Math.min(8, Math.max(2, width))
}
function totals(node) {
  let total = node.address !== undefined ? 1 : 0
  let on = total && node.is_on ? 1 : 0
  for (const child of node.items || []) {
    const nested = totals(child)
    total += nested.total
    on += nested.on
  }
  return { total, on }
}
function state(node) {
  const { total, on } = totals(node)
  return on === 0 ? 'none' : on === total ? 'all' : 'some'
}
function stateLabel(node) {
  const { total, on } = totals(node)
  return `Svítí ${on} z ${total} světel`
}
</script>
