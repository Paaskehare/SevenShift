<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { leasingApi } from '@/api/leasing'
import { PlusIcon } from '@heroicons/vue/24/outline'

const router = useRouter()
const offers = ref([])
const count = ref(0)
const loading = ref(false)
const statusFilter = ref('')
const page = ref(1)
const pageSize = 25

const statusOptions = [
  { value: '', label: 'All statuses' },
  { value: 'draft', label: 'Draft' },
  { value: 'active', label: 'Active' },
  { value: 'expired', label: 'Expired' },
  { value: 'archived', label: 'Archived' },
]

const statusColors = {
  draft: 'bg-gray-100 text-gray-600',
  active: 'bg-green-100 text-green-700',
  expired: 'bg-red-100 text-red-600',
  archived: 'bg-gray-100 text-gray-400',
}

async function fetchOffers() {
  loading.value = true
  try {
    const { data } = await leasingApi.listOffers({
      status: statusFilter.value || undefined,
      page: page.value,
      page_size: pageSize,
    })
    offers.value = data.results
    count.value = data.count
  } finally {
    loading.value = false
  }
}

watch(statusFilter, () => { page.value = 1; fetchOffers() })
watch(page, fetchOffers)
onMounted(fetchOffers)

const totalPages = () => Math.ceil(count.value / pageSize)
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Leasing Offers</h1>
        <p class="text-sm text-gray-500 mt-0.5">{{ count }} offers total</p>
      </div>
      <RouterLink to="/leasing/offers/new" class="btn-primary gap-2">
        <PlusIcon class="h-4 w-4" />
        New Offer
      </RouterLink>
    </div>

    <!-- Filter -->
    <div class="card p-4 mb-4 flex gap-3">
      <select v-model="statusFilter" class="form-input w-48">
        <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
      </select>
    </div>

    <!-- Table -->
    <div class="card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 border-b border-gray-200">
            <tr>
              <th class="text-left px-4 py-3 font-medium text-gray-600">#</th>
              <th class="text-left px-4 py-3 font-medium text-gray-600">Vehicle / Trim</th>
              <th class="text-left px-4 py-3 font-medium text-gray-600">Monthly Rate</th>
              <th class="text-left px-4 py-3 font-medium text-gray-600">Duration</th>
              <th class="text-left px-4 py-3 font-medium text-gray-600">KM/Year</th>
              <th class="text-left px-4 py-3 font-medium text-gray-600">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-if="loading"><td colspan="6" class="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            <tr v-else-if="!offers.length"><td colspan="6" class="px-4 py-8 text-center text-gray-400">No offers found.</td></tr>
            <tr
              v-for="offer in offers"
              :key="offer.id"
              class="hover:bg-gray-50 cursor-pointer transition-colors"
              @click="router.push({ name: 'OfferDetail', params: { id: offer.id } })"
            >
              <td class="px-4 py-3 text-gray-400 text-xs">#{{ offer.id }}</td>
              <td class="px-4 py-3 font-medium text-gray-900">
                {{ offer.vehicle ? `Vehicle #${offer.vehicle}` : offer.trim ? `Trim #${offer.trim}` : '—' }}
              </td>
              <td class="px-4 py-3 text-gray-900 font-semibold">€{{ Number(offer.monthly_rate).toLocaleString() }}/mo</td>
              <td class="px-4 py-3 text-gray-600">{{ offer.duration_months }} months</td>
              <td class="px-4 py-3 text-gray-600">{{ offer.km_limit_per_year.toLocaleString() }} km</td>
              <td class="px-4 py-3">
                <span :class="['badge capitalize', statusColors[offer.status] || 'bg-gray-100 text-gray-600']">
                  {{ offer.status }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
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
