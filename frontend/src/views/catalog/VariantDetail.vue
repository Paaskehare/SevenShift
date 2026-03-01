<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { catalogApi } from '@/api/catalog'
import { ArrowLeftIcon } from '@heroicons/vue/24/outline'

const route = useRoute()
const router = useRouter()
const variant = ref(null)
const generation = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const { data } = await catalogApi.getVariant(route.params.id)
    variant.value = data
    if (data.generation) {
      const { data: gen } = await catalogApi.getGeneration(data.generation)
      generation.value = gen
    }
  } finally {
    loading.value = false
  }
})

function specRow(label, value, unit = '') {
  if (!value && value !== 0) return null
  return { label, value: `${value}${unit}` }
}
</script>

<template>
  <div>
    <button @click="router.back()" class="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 mb-6 transition-colors">
      <ArrowLeftIcon class="h-4 w-4" />
      Back to Catalog
    </button>

    <div v-if="loading" class="text-center py-12 text-gray-400">Loading…</div>

    <template v-else-if="variant">
      <h1 class="text-2xl font-bold text-gray-900 mb-1">{{ variant.variant || '—' }}</h1>
      <p v-if="generation" class="text-gray-500 mb-6">
        {{ generation.name }}
        <span v-if="generation.production_start">
          · {{ generation.production_start }}{{ generation.production_end ? `–${generation.production_end}` : '–present' }}
        </span>
      </p>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <!-- Engine -->
        <div class="card p-5">
          <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">Engine & Drivetrain</h2>
          <dl class="space-y-3">
            <template v-for="row in [
              specRow('Fuel Type', variant.fuel_type),
              specRow('Displacement', variant.engine_displacement_cc, ' cc'),
              specRow('Cylinders', variant.engine_cylinders),
              specRow('Power', variant.power_hp, ' hp'),
              specRow('Torque', variant.torque_nm, ' Nm'),
              specRow('Transmission', variant.transmission),
              specRow('Gears', variant.number_of_gears),
              specRow('Drive', variant.drivetrain),
            ].filter(Boolean)" :key="row.label">
              <div class="flex justify-between text-sm">
                <dt class="text-gray-500">{{ row.label }}</dt>
                <dd class="text-gray-900 font-medium">{{ row.value }}</dd>
              </div>
            </template>
          </dl>
        </div>

        <!-- Performance -->
        <div class="card p-5">
          <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">Performance & Economy</h2>
          <dl class="space-y-3">
            <template v-for="row in [
              specRow('0–100 km/h', variant.acceleration_0_100, ' s'),
              specRow('Top Speed', variant.top_speed_kmh, ' km/h'),
              specRow('Fuel Consumption', variant.fuel_consumption_l100km, ' L/100km'),
              specRow('CO₂', variant.co2_g_km, ' g/km'),
              specRow('Electric Range', variant.all_electric_range, ' km'),
              specRow('Energy Consumption', variant.average_energy_consumption, ' kWh/100km'),
            ].filter(Boolean)" :key="row.label">
              <div class="flex justify-between text-sm">
                <dt class="text-gray-500">{{ row.label }}</dt>
                <dd class="text-gray-900 font-medium">{{ row.value }}</dd>
              </div>
            </template>
          </dl>
        </div>

        <!-- Dimensions -->
        <div class="card p-5">
          <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">Dimensions & Weight</h2>
          <dl class="space-y-3">
            <template v-for="row in [
              specRow('Length', variant.length_mm, ' mm'),
              specRow('Width', variant.width_mm, ' mm'),
              specRow('Height', variant.height_mm, ' mm'),
              specRow('Wheelbase', variant.wheelbase_mm, ' mm'),
              specRow('Curb Weight', variant.curb_weight_kg, ' kg'),
              specRow('Max Weight', variant.max_weight_kg, ' kg'),
              specRow('Trunk Volume', variant.trunk_volume_l, ' L'),
              specRow('Seats', variant.seats),
              specRow('Doors', variant.doors),
            ].filter(Boolean)" :key="row.label">
              <div class="flex justify-between text-sm">
                <dt class="text-gray-500">{{ row.label }}</dt>
                <dd class="text-gray-900 font-medium">{{ row.value }}</dd>
              </div>
            </template>
          </dl>
        </div>
      </div>
    </template>
  </div>
</template>
