<template>
  <div class="ml-4 mt-3 border-l-2 border-slate-200 pl-4">

    <div v-if="node.items">
      <div class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 mb-2">

        <div
          @click="isOpen = !isOpen"
          class="flex-1 cursor-pointer group flex items-center gap-3"
        >
          <svg
            :class="{'rotate-90': isOpen}"
            class="w-5 h-5 text-slate-400 group-hover:text-indigo-500 transition-transform duration-200"
            fill="none" viewBox="0 0 24 24" stroke="currentColor"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>

          <div>
            <h3 class="text-lg font-semibold text-slate-800 group-hover:text-indigo-600 transition-colors">{{ node.name }}</h3>
            <p v-if="node.note" class="text-sm text-slate-500 italic">{{ node.note }}</p>
          </div>
        </div>

        <select
          @change="updateGroup($event)"
          class="w-56 border border-slate-300 rounded-lg px-3 py-2 bg-slate-50 text-slate-700 cursor-pointer hover:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100 transition-colors shadow-sm"
        >
          <option value="" disabled selected>Změnit vše na...</option>
          <option v-for="algo in availableAlgorithms" :key="algo" :value="algo">{{ algo }}</option>
        </select>
      </div>

      <div v-show="isOpen" class="mt-4">
        <RailwayNode
          v-for="(child, index) in node.items"
          :key="child.id || index"
          :node="child"
        />
      </div>
    </div>

    <div v-else class="bg-white p-4 rounded-xl shadow-sm border border-slate-100 my-2 flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 transition-all hover:shadow-md hover:border-indigo-100">
      <div>
        <h4 class="font-medium text-slate-900">{{ node.name }}</h4>
        <div class="text-xs text-slate-500 mt-1.5 flex gap-3">
          <span>Adresa: <strong class="font-mono bg-slate-100 px-1.5 py-0.5 rounded text-slate-700">{{ node.address }}</strong></span>
          <span>ID: {{ node.id }}</span>
        </div>
      </div>

      <select
        :value="node.algorithm"
        @change="updateSingle($event)"
        class="w-56 border border-slate-300 rounded-lg px-3 py-2 bg-slate-50 text-slate-700 cursor-pointer hover:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100 transition-colors shadow-sm"
      >
        <option v-for="algo in availableAlgorithms" :key="algo" :value="algo">{{ algo }}</option>
      </select>
    </div>

  </div>
</template>

<script setup>
import { ref } from 'vue'

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
      body: {
        item_id: id,
        new_algorithm: newAlgorithm
      }
    });

    await refreshNuxtData('kolejiste');

  } catch (error) {
    console.error("Chyba při změně algoritmu:", error);
    alert("Nepodařilo se změnit algoritmu. Běží backend?");
  }
}
</script>