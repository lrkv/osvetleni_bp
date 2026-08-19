<template>
  <div class="ml-4 mt-3 border-l-2 border-slate-200 pl-4">

    <!-- Vykreslení nadřazené skupiny -->
    <div v-if="node.polozky">
      <div class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 mb-2">
        <div>
          <h3 class="text-lg font-semibold text-slate-800">{{ node.nazev }}</h3>
          <p v-if="node.poznamka" class="text-sm text-slate-500 italic">{{ node.poznamka }}</p>
        </div>

        <!-- Hromadná změna (volá funkci updateGroup) -->
        <select
          @change="updateGroup($event)"
          class="text-sm border border-slate-300 rounded-lg px-3 py-1.5 bg-slate-50 text-slate-700 cursor-pointer hover:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
        >
          <option value="" disabled selected>Změnit vše na...</option>
          <option v-for="algo in availableAlgorithms" :key="algo" :value="algo">{{ algo }}</option>
        </select>
      </div>

      <RailwayNode
        v-for="(child, index) in node.polozky"
        :key="child.id || index"
        :node="child"
      />
    </div>

    <!-- Vykreslení konkrétního koncového světla -->
    <div v-else class="bg-white p-4 rounded-xl shadow-sm border border-slate-100 my-2 flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 transition-all hover:shadow-md">
      <div>
        <h4 class="font-medium text-slate-900">{{ node.nazev }}</h4>
        <div class="text-xs text-slate-500 mt-1.5 flex gap-3">
          <span>Adresa: <strong class="font-mono bg-slate-100 px-1.5 py-0.5 rounded text-slate-700">{{ node.adresa }}</strong></span>
          <span>ID: {{ node.id }}</span>
        </div>
      </div>

      <!-- Jednosměrná vazba :value místo zakázaného v-model (prop nesmíme upravovat lokálně) -->
      <select
        :value="node.algoritmus"
        @change="updateSingle($event)"
        class="text-sm border font-semibold border-indigo-200 rounded-full px-3 py-1 bg-indigo-50 text-indigo-700 cursor-pointer hover:bg-indigo-100 focus:outline-none"
      >
        <option v-for="algo in availableAlgorithms" :key="algo" :value="algo">{{ algo }}</option>
      </select>
    </div>

  </div>
</template>

<script setup>
const props = defineProps({
  node: {
    type: Object,
    required: true
  }
})

const availableAlgorithms = [
  "trvale_zapnuto",
  "trvale_vypnuto",
  "domacnost",
  "poulicni_lampa",
  "drazni_osvetleni",
  "disco"
]

// 1. Ošetření akce pro celou skupinu
async function updateGroup(event) {
  const newAlgorithm = event.target.value;
  if (!newAlgorithm) return;

  await sendToBackend(props.node.id, newAlgorithm);

  // Po odeslání roletku vizuálně vrátíme do neutrálního stavu
  event.target.value = "";
}

// 2. Ošetření akce pro jedno světlo
async function updateSingle(event) {
  const newAlgorithm = event.target.value;
  if (!newAlgorithm) return;

  await sendToBackend(props.node.id, newAlgorithm);
}

// 3. Společná komunikace s Pythonem
async function sendToBackend(id, newAlgorithm) {
  try {
    await $fetch('http://127.0.0.1:8000/api/algorithm', {
      method: 'POST',
      body: {
        item_id: id,
        new_algorithm: newAlgorithm
      }
    });

    // Klíčový příkaz: Vyvolá opětovné stažení dat z backendu a okamžitě překreslí komponenty
    await refreshNuxtData('kolejiste');

  } catch (error) {
    console.error("Chyba při změně algoritmu:", error);
    alert("Nepodařilo se změnit algoritmus. Běží backend?");
  }
}
</script>