<template>
  <div class="ml-4 mt-3 border-l-2 border-slate-200 pl-4">

    <!-- VYKRESLENÍ SKUPINY -->
    <div v-if="node.items">
      <div class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 mb-2">

        <div
          @click="isOpen = !isOpen"
          class="flex-1 cursor-pointer group flex items-center gap-3"
        >
          <svg :class="{'rotate-90': isOpen}" class="w-5 h-5 text-slate-400 group-hover:text-indigo-500 transition-transform duration-200" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>

          <div>
            <h3 class="text-lg font-semibold text-slate-800 group-hover:text-indigo-600 transition-colors flex items-center gap-2">
              {{ node.name }}

              <!-- NOVÉ: Dynamické tečky podle vypočítaného stavu skupiny -->
              <span v-if="groupStatus === 'all'" class="inline-block w-3 h-3 rounded-full bg-amber-400 shadow-sm" title="Vše svítí"></span>
              <span v-else-if="groupStatus === 'some'" class="inline-block w-3 h-3 rounded-full bg-amber-200 shadow-sm" title="Něco svítí"></span>
              <span v-else-if="groupStatus === 'none'" class="inline-block w-3 h-3 rounded-full bg-slate-300 shadow-inner" title="Nic nesvítí"></span>
            </h3>
            <p v-if="node.note" class="text-sm text-slate-500 italic">{{ node.note }}</p>
          </div>
        </div>

        <select @change="updateGroup($event)" class="w-56 border border-slate-300 rounded-lg px-3 py-2 bg-slate-50 text-slate-700 cursor-pointer hover:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100 transition-colors shadow-sm">
          <option value="" disabled selected>Změnit vše na...</option>
          <option v-for="algo in availableAlgorithms" :key="algo" :value="algo">{{ algo }}</option>
        </select>
      </div>

      <div v-show="isOpen" class="mt-4">
        <RailwayNode v-for="(child, index) in node.items" :key="child.id || index" :node="child" />
      </div>
    </div>

    <!-- VYKRESLENÍ KONKRÉTNÍHO SVĚTLA -->
    <div v-else :class="[
      'p-4 rounded-xl shadow-sm border my-2 flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 transition-all hover:shadow-md',
      node.is_on ? 'bg-amber-50 border-amber-300' : 'bg-white border-slate-100 hover:border-indigo-100'
    ]">
      <div>
        <h4 class="font-medium text-slate-900 flex items-center gap-2">
          {{ node.name }}
          <span v-if="node.is_on" class="relative flex h-2.5 w-2.5" title="Svítí">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500"></span>
          </span>
        </h4>
        <div class="text-xs text-slate-500 mt-1.5 flex gap-3">
          <span>Adresa: <strong class="font-mono bg-slate-100 px-1.5 py-0.5 rounded text-slate-700">{{ node.address }}</strong></span>
          <span>ID: {{ node.id }}</span>
        </div>
      </div>

      <select :value="node.algorithm" @change="updateSingle($event)" class="w-56 border border-slate-300 rounded-lg px-3 py-2 bg-white text-slate-700 cursor-pointer hover:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100 transition-colors shadow-sm">
        <option v-for="algo in availableAlgorithms" :key="algo" :value="algo">{{ algo }}</option>
      </select>
    </div>

  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  node: {
    type: Object,
    required: true
  }
})

const isOpen = ref(false)

const availableAlgorithms = [
  "trvale_zapnuto",
  "trvale_vypnuto",
  "domacnost",
  "poulicni_lampa",
  "drazni_osvetleni",
  "disco"
]

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
  const newAlgorithm = event.target.value;
  if (!newAlgorithm) return;
  await sendToBackend(props.node.id, newAlgorithm);
  event.target.value = "";
}

async function updateSingle(event) {
  const newAlgorithm = event.target.value;
  if (!newAlgorithm) return;
  await sendToBackend(props.node.id, newAlgorithm);
}

async function sendToBackend(id, newAlgorithm) {
  try {
    await $fetch('http://127.0.0.1:8000/api/algorithm', {
      method: 'POST',
      body: { item_id: id, new_algorithm: newAlgorithm }
    });
    await refreshNuxtData('kolejiste');
  } catch (error) {
    console.error("Chyba při změně algoritmu:", error);
    alert("Nepodařilo se změnit algoritmus. Běží backend?");
  }
}
</script>