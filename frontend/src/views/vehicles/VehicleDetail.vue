<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { vehiclesApi } from '@/api/vehicles'
import { ArrowLeftIcon } from '@heroicons/vue/24/outline'

const route = useRoute()
const router = useRouter()
const vehicle = ref(null)
const loading = ref(true)

const statusColors = {
  available: 'bg-green-100 text-green-700',
  leased: 'bg-blue-100 text-blue-700',
  in_service: 'bg-amber-100 text-amber-700',
  reserved: 'bg-purple-100 text-purple-700',
  retired: 'bg-gray-100 text-gray-500',
}

onMounted(async () => {
  try {
    const { data } = await vehiclesApi.get(route.params.id)
    vehicle.value = data
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <button @click="router.back()" class="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 mb-6 transition-colors">
      <ArrowLeftIcon class="h-4 w-4" />
      Back to Vehicles
    </button>

    <div v-if="loading" class="text-center py-12 text-gray-400">Loading…</div>

    <template v-else-if="vehicle">
      <!-- Title row -->
      <div class="flex items-start justify-between mb-6">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">{{ vehicle.display_name }}</h1>
          <p class="text-gray-500 font-mono mt-1">{{ vehicle.plate_number }}</p>
        </div>
        <span :class="['badge capitalize text-sm px-3 py-1', statusColors[vehicle.status] || 'bg-gray-100 text-gray-600']">
          {{ vehicle.status.replace('_', ' ') }}
        </span>
      </div>

      <!-- Detail grid -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <!-- Identification -->
        <div class="card p-5">
          <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">Identification</h2>
          <dl class="space-y-3">
            <div class="flex justify-between text-sm">
              <dt class="text-gray-500">VIN</dt>
              <dd class="font-mono text-gray-900">{{ vehicle.vin || '—' }}</dd>
            </div>
            <div class="flex justify-between text-sm">
              <dt class="text-gray-500">Year</dt>
              <dd class="text-gray-900">{{ vehicle.year }}</dd>
            </div>
            <div class="flex justify-between text-sm">
              <dt class="text-gray-500">Color</dt>
              <dd class="text-gray-900">{{ vehicle.color || '—' }} <span v-if="vehicle.color_code" class="text-gray-400">({{ vehicle.color_code }})</span></dd>
            </div>
          </dl>
        </div>

        <!-- Operations -->
        <div class="card p-5">
          <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">Operations</h2>
          <dl class="space-y-3">
            <div class="flex justify-between text-sm">
              <dt class="text-gray-500">Mileage</dt>
              <dd class="text-gray-900">{{ vehicle.mileage_km.toLocaleString() }} km</dd>
            </div>
            <div class="flex justify-between text-sm">
              <dt class="text-gray-500">Purchase Date</dt>
              <dd class="text-gray-900">{{ vehicle.purchase_date || '—' }}</dd>
            </div>
            <div class="flex justify-between text-sm">
              <dt class="text-gray-500">Purchase Price</dt>
              <dd class="text-gray-900">{{ vehicle.purchase_price ? `€${Number(vehicle.purchase_price).toLocaleString()}` : '—' }}</dd>
            </div>
          </dl>
        </div>

        <!-- Catalog specs -->
        <div v-if="vehicle.variant_detail" class="card p-5 lg:col-span-2">
          <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">Catalog Specs</h2>
          <dl class="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div v-if="vehicle.variant_detail.fuel_type" class="text-sm">
              <dt class="text-gray-500">Fuel</dt>
              <dd class="text-gray-900 font-medium">{{ vehicle.variant_detail.fuel_type }}</dd>
            </div>
            <div v-if="vehicle.variant_detail.power_hp" class="text-sm">
              <dt class="text-gray-500">Power</dt>
              <dd class="text-gray-900 font-medium">{{ vehicle.variant_detail.power_hp }} hp</dd>
            </div>
            <div v-if="vehicle.variant_detail.transmission" class="text-sm">
              <dt class="text-gray-500">Transmission</dt>
              <dd class="text-gray-900 font-medium">{{ vehicle.variant_detail.transmission }}</dd>
            </div>
            <div v-if="vehicle.variant_detail.drive" class="text-sm">
              <dt class="text-gray-500">Drive</dt>
              <dd class="text-gray-900 font-medium">{{ vehicle.variant_detail.drive }}</dd>
            </div>
          </dl>
          <RouterLink
            :to="`/catalog/variants/${vehicle.variant}`"
            class="inline-flex items-center text-sm text-brand-600 hover:text-brand-700 mt-4"
          >
            View full catalog entry →
          </RouterLink>
        </div>

        <!-- Notes -->
        <div v-if="vehicle.notes" class="card p-5 lg:col-span-2">
          <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-2">Notes</h2>
          <p class="text-sm text-gray-700 whitespace-pre-line">{{ vehicle.notes }}</p>
        </div>
      </div>
    </template>
  </div>
</template>
