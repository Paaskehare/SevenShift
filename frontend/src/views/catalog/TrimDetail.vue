<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { catalogApi } from '@/api/catalog'
import { ArrowLeftIcon } from '@heroicons/vue/24/outline'

const route = useRoute()
const router = useRouter()
const trim = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const { data } = await catalogApi.getTrim(route.params.id)
    trim.value = data
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

    <template v-else-if="trim">
      <h1 class="text-2xl font-bold text-gray-900 mb-1">{{ trim.name }}</h1>
      <p class="text-gray-500 mb-6">
        {{ trim.car_model }} ·
        <span v-if="trim.year_from">{{ trim.year_from }}{{ trim.year_to ? `–${trim.year_to}` : '–present' }}</span>
      </p>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <!-- Engine -->
        <div class="card p-5">
          <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">Engine & Drivetrain</h2>
          <dl class="space-y-3">
            <template v-for="row in [
              specRow('Fuel Type', trim.fuel_type),
              specRow('Displacement', trim.engine_displacement_cc, ' cc'),
              specRow('Cylinders', trim.engine_cylinders),
              specRow('Power', trim.power_hp, ' hp'),
              specRow('Torque', trim.torque_nm, ' Nm'),
              specRow('Transmission', trim.transmission),
              specRow('Drive', trim.drivetrain),
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
              specRow('0–100 km/h', trim.acceleration_0_100, ' s'),
              specRow('Top Speed', trim.top_speed_kmh, ' km/h'),
              specRow('Fuel Consumption', trim.fuel_consumption_l100km, ' L/100km'),
              specRow('CO₂', trim.co2_g_km, ' g/km'),
              specRow('Electric Range', trim.electric_range_km, ' km'),
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
              specRow('Length', trim.length_mm, ' mm'),
              specRow('Width', trim.width_mm, ' mm'),
              specRow('Height', trim.height_mm, ' mm'),
              specRow('Wheelbase', trim.wheelbase_mm, ' mm'),
              specRow('Curb Weight', trim.curb_weight_kg, ' kg'),
              specRow('Trunk Volume', trim.trunk_volume_l, ' L'),
              specRow('Seats', trim.seats),
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
