<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { vehiclesApi } from '@/api/vehicles'
import { MagnifyingGlassIcon, PlusIcon } from '@heroicons/vue/24/outline'

const router = useRouter()
const vehicles = ref([])
const count = ref(0)
const loading = ref(false)
const search = ref('')
const statusFilter = ref('')
const page = ref(1)
const pageSize = 25

const statusOptions = [
  { value: '', label: 'All statuses' },
  { value: 'available', label: 'Available' },
  { value: 'leased', label: 'Leased' },
  { value: 'in_service', label: 'In Service' },
  { value: 'reserved', label: 'Reserved' },
  { value: 'retired', label: 'Retired' },
]

const statusColors = {
  available: 'bg-green-100 text-green-700',
  leased: 'bg-blue-100 text-blue-700',
  in_service: 'bg-amber-100 text-amber-700',
  reserved: 'bg-purple-100 text-purple-700',
  retired: 'bg-gray-100 text-gray-500',
}

async function fetchVehicles() {
  loading.value = true
  try {
    const { data } = await vehiclesApi.list({
      search: search.value || undefined,
      status: statusFilter.value || undefined,
      page: page.value,
      page_size: pageSize,
    })
    vehicles.value = data.results
    count.value = data.count
  } finally {
    loading.value = false
  }
}

watch([search, statusFilter], () => { page.value = 1; fetchVehicles() })
watch(page, fetchVehicles)
onMounted(fetchVehicles)

const totalPages = () => Math.ceil(count.value / pageSize)
</script>

<template>
  <div>
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Vehicles</h1>
        <p class="text-sm text-gray-500 mt-0.5">{{ count }} vehicles in fleet</p>
      </div>
      <RouterLink to="/vehicles/new" class="btn-primary gap-2">
        <PlusIcon class="h-4 w-4" />
        Add Vehicle
      </RouterLink>
    </div>

    <!-- Filters -->
    <div class="card p-4 mb-4 flex flex-col sm:flex-row gap-3">
      <div class="relative flex-1">
        <MagnifyingGlassIcon class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <input
          v-model="search"
          type="text"
          placeholder="Search plate, VIN, make…"
          class="form-input pl-9"
        />
      </div>
      <select v-model="statusFilter" class="form-input sm:w-48">
        <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">
          {{ opt.label }}
        </option>
      </select>
    </div>

    <!-- Table -->
    <div class="card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 border-b border-gray-200">
            <tr>
              <th class="text-left px-4 py-3 font-medium text-gray-600">Vehicle</th>
              <th class="text-left px-4 py-3 font-medium text-gray-600">Plate</th>
              <th class="text-left px-4 py-3 font-medium text-gray-600">Year</th>
              <th class="text-left px-4 py-3 font-medium text-gray-600">Mileage</th>
              <th class="text-left px-4 py-3 font-medium text-gray-600">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-if="loading">
              <td colspan="5" class="px-4 py-8 text-center text-gray-400">Loading…</td>
            </tr>
            <tr v-else-if="!vehicles.length">
              <td colspan="5" class="px-4 py-8 text-center text-gray-400">No vehicles found.</td>
            </tr>
            <tr
              v-for="v in vehicles"
              :key="v.id"
              class="hover:bg-gray-50 cursor-pointer transition-colors"
              @click="router.push({ name: 'VehicleDetail', params: { id: v.id } })"
            >
              <td class="px-4 py-3 font-medium text-gray-900">{{ v.display_name }}</td>
              <td class="px-4 py-3 text-gray-600 font-mono">{{ v.plate_number }}</td>
              <td class="px-4 py-3 text-gray-600">{{ v.year }}</td>
              <td class="px-4 py-3 text-gray-600">{{ v.mileage_km.toLocaleString() }} km</td>
              <td class="px-4 py-3">
                <span :class="['badge capitalize', statusColors[v.status] || 'bg-gray-100 text-gray-600']">
                  {{ v.status.replace('_', ' ') }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div v-if="totalPages() > 1" class="flex items-center justify-between px-4 py-3 border-t border-gray-200">
        <p class="text-sm text-gray-500">Page {{ page }} of {{ totalPages() }}</p>
        <div class="flex gap-2">
          <button :disabled="page <= 1" @click="page--" class="btn-secondary !px-3 !py-1.5 !text-xs disabled:opacity-40">Prev</button>
          <button :disabled="page >= totalPages()" @click="page++" class="btn-secondary !px-3 !py-1.5 !text-xs disabled:opacity-40">Next</button>
        </div>
      </div>
    </div>
  </div>
</template>
