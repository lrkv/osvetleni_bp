<template>
  <div class="min-h-screen bg-slate-50 font-sans p-4 sm:p-8">
    <div class="max-w-4xl mx-auto">

      <header class="mb-8">
        <h1 class="text-3xl font-extrabold text-slate-900 tracking-tight">Správa osvětlení kolejiště</h1>
        <p v-if="pending" class="text-slate-500 mt-2 animate-pulse">Načítám konfiguraci z backendu...</p>
        <p v-else-if="error" class="text-red-500 mt-2 font-medium">Chyba připojení k API: {{ error.message }}</p>
      </header>

      <main v-if="data" class="bg-white p-6 sm:p-8 rounded-2xl shadow-sm border border-slate-200">

        <div class="mb-8 pb-6 border-b border-slate-100">
          <h2 class="text-2xl font-bold text-slate-800">{{ data.layout_name }}</h2>
          <div class="text-sm text-slate-600 mt-2 flex gap-4">
            <span>Umístění: <strong>{{ data.location }}</strong></span>
            <span>Verze YAML: <strong>{{ data.version }}</strong></span>
          </div>
          <p class="text-slate-500 mt-3">{{ data.note }}</p>
        </div>

        <div class="space-y-6">
          <RailwayNode
            v-for="(group, index) in data.groups"
            :key="index"
            :node="group"
          />
        </div>

      </main>

    </div>
  </div>
</template>

<script setup>
const { data, pending, error } = await useFetch('http://127.0.0.1:8000/api/structure', {
  key: 'kolejiste'
})
</script>