<script setup>
import { ref, onMounted, watch } from 'vue'
import { leasingApi } from '@/api/leasing'

const contracts = ref([])
const count = ref(0)
const loading = ref(false)
const statusFilter = ref('')
const page = ref(1)
const pageSize = 25

const statusOptions = [
  { value: '', label: 'All statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'active', label: 'Active' },
  { value: 'completed', label: 'Completed' },
  { value: 'terminated', label: 'Terminated' },
]

const statusColors = {
  pending: 'bg-amber-100 text-amber-700',
  active: 'bg-green-100 text-green-700',
  completed: 'bg-blue-100 text-blue-700',
  terminated: 'bg-red-100 text-red-600',
}

async function fetchContracts() {
  loading.value = true
  try {
    const { data } = await leasingApi.listContracts({
      status: statusFilter.value || undefined,
      page: page.value,
      page_size: pageSize,
    })
    contracts.value = data.results
    count.value = data.count
  } finally {
    loading.value = false
  }
}

watch(statusFilter, () => { page.value = 1; fetchContracts() })
watch(page, fetchContracts)
onMounted(fetchContracts)

const totalPages = () => Math.ceil(count.value / pageSize)
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Leasing Contracts</h1>
        <p class="text-sm text-gray-500 mt-0.5">{{ count }} contracts total</p>
      </div>
    </div>

    <!-- Filter -->
    <div class="card p-4 mb-4 flex gap-3">
      <select v-model="statusFilter" class="form-input w-48">
        <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
      </select>
    </div>

    <div class="card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 border-b border-gray-200">
            <tr>
              <th class="text-left px-4 py-3 font-medium text-gray-600">#</th>
              <th class="text-left px-4 py-3 font-medium text-gray-600">Vehicle</th>
              <th class="text-left px-4 py-3 font-medium text-gray-600">Monthly</th>
              <th class="text-left px-4 py-3 font-medium text-gray-600">Start</th>
              <th class="text-left px-4 py-3 font-medium text-gray-600">End</th>
              <th class="text-left px-4 py-3 font-medium text-gray-600">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-if="loading"><td colspan="6" class="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            <tr v-else-if="!contracts.length"><td colspan="6" class="px-4 py-8 text-center text-gray-400">No contracts found.</td></tr>
            <tr v-for="c in contracts" :key="c.id" class="hover:bg-gray-50 transition-colors">
              <td class="px-4 py-3 text-gray-400 text-xs">#{{ c.id }}</td>
              <td class="px-4 py-3 font-medium text-gray-900">
                <RouterLink :to="`/vehicles/${c.vehicle}`" class="text-brand-600 hover:underline">
                  Vehicle #{{ c.vehicle }}
                </RouterLink>
              </td>
              <td class="px-4 py-3 text-gray-900 font-semibold">€{{ Number(c.monthly_rate).toLocaleString() }}/mo</td>
              <td class="px-4 py-3 text-gray-600">{{ c.start_date }}</td>
              <td class="px-4 py-3 text-gray-600">{{ c.end_date }}</td>
              <td class="px-4 py-3">
                <span :class="['badge capitalize', statusColors[c.status] || 'bg-gray-100 text-gray-600']">
                  {{ c.status }}
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
