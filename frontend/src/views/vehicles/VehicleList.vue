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
const makeFilter = ref('')
const page = ref(1)
const pageSize = 25
const makes = ref([])

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

const priceRatingColors = {
  GOOD_PRICE: 'bg-green-100 text-green-700',
  FAIR_PRICE: 'bg-amber-100 text-amber-700',
  HIGH_PRICE: 'bg-red-100 text-red-700',
}

async function fetchVehicles() {
  loading.value = true
  try {
    const { data } = await vehiclesApi.list({
      search: search.value || undefined,
      status: statusFilter.value || undefined,
      make: makeFilter.value || undefined,
      page: page.value,
      page_size: pageSize,
    })
    vehicles.value = data.results
    count.value = data.count
  } finally {
    loading.value = false
  }
}

watch([search, statusFilter, makeFilter], () => { page.value = 1; fetchVehicles() })
watch(page, fetchVehicles)

onMounted(async () => {
  fetchVehicles()
  const { data } = await vehiclesApi.getMakes()
  makes.value = data
})

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
      <select v-model="makeFilter" class="form-input sm:w-44">
        <option value="">All makes</option>
        <option v-for="m in makes" :key="m.id" :value="m.id">{{ m.name }}</option>
      </select>
      <select v-model="statusFilter" class="form-input sm:w-44">
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
              <th class="w-16 px-3 py-3"></th>
              <th class="text-left px-4 py-3 font-medium text-gray-600">Vehicle</th>
              <th class="text-left px-4 py-3 font-medium text-gray-600">Year</th>
              <th class="text-left px-4 py-3 font-medium text-gray-600">Mileage</th>
              <th class="text-left px-4 py-3 font-medium text-gray-600">Price</th>
              <th class="text-left px-4 py-3 font-medium text-gray-600">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-if="loading">
              <td colspan="6" class="px-4 py-8 text-center text-gray-400">Loading…</td>
            </tr>
            <tr v-else-if="!vehicles.length">
              <td colspan="6" class="px-4 py-8 text-center text-gray-400">No vehicles found.</td>
            </tr>
            <tr
              v-for="v in vehicles"
              :key="v.id"
              class="hover:bg-gray-50 cursor-pointer transition-colors"
              @click="router.push({ name: 'VehicleDetail', params: { id: v.id } })"
            >
              <td class="px-3 py-2">
                <img
                  v-if="v.thumbnail_url"
                  :src="v.thumbnail_url"
                  class="h-10 w-14 object-cover rounded"
                  loading="lazy"
                />
                <div v-else class="h-10 w-14 bg-gray-100 rounded" />
              </td>
              <td class="px-4 py-3">
                <p class="font-medium text-gray-900">{{ v.display_name }}</p>
                <p v-if="v.plate_number" class="text-xs text-gray-400 font-mono">{{ v.plate_number }}</p>
              </td>
              <td class="px-4 py-3 text-gray-600">{{ v.year ?? '—' }}</td>
              <td class="px-4 py-3 text-gray-600">
                {{ v.mileage_km != null ? v.mileage_km.toLocaleString() + ' km' : '—' }}
              </td>
              <td class="px-4 py-3">
                <template v-if="v.price">
                  <p class="text-gray-900 font-medium">€{{ Number(v.price).toLocaleString() }}</p>
                  <span
                    v-if="v.price_rating"
                    :class="['text-xs px-1.5 py-0.5 rounded font-medium', priceRatingColors[v.price_rating] || 'bg-gray-100 text-gray-500']"
                  >{{ v.price_rating.replace(/_/g, ' ') }}</span>
                </template>
                <span v-else class="text-gray-400">—</span>
              </td>
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
