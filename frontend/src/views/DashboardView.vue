<script setup>
import { ref, onMounted } from 'vue'
import { vehiclesApi } from '@/api/vehicles'
import { leasingApi } from '@/api/leasing'
import { catalogApi } from '@/api/catalog'
import { TruckIcon, DocumentTextIcon, BookOpenIcon, ClipboardDocumentListIcon } from '@heroicons/vue/24/outline'

const stats = ref([
  { label: 'Total Vehicles', value: '—', icon: TruckIcon, color: 'bg-brand-50 text-brand-600' },
  { label: 'Active Leases', value: '—', icon: DocumentTextIcon, color: 'bg-green-50 text-green-600' },
  { label: 'Catalog Models', value: '—', icon: BookOpenIcon, color: 'bg-purple-50 text-purple-600' },
  { label: 'Open Offers', value: '—', icon: ClipboardDocumentListIcon, color: 'bg-amber-50 text-amber-600' },
])

onMounted(async () => {
  const [vehicles, contracts, makes, offers] = await Promise.allSettled([
    vehiclesApi.list({ page_size: 1 }),
    leasingApi.listContracts({ status: 'active', page_size: 1 }),
    catalogApi.getMakes({ page_size: 1 }),
    leasingApi.listOffers({ status: 'active', page_size: 1 }),
  ])

  if (vehicles.status === 'fulfilled') stats.value[0].value = vehicles.value.data.count
  if (contracts.status === 'fulfilled') stats.value[1].value = contracts.value.data.count
  if (makes.status === 'fulfilled') stats.value[2].value = makes.value.data.count
  if (offers.status === 'fulfilled') stats.value[3].value = offers.value.data.count
})
</script>

<template>
  <div>
    <h1 class="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>

    <!-- Stats grid -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <div v-for="stat in stats" :key="stat.label" class="card p-5 flex items-center gap-4">
        <div :class="['rounded-xl p-3', stat.color]">
          <component :is="stat.icon" class="h-6 w-6" />
        </div>
        <div>
          <div class="text-2xl font-bold text-gray-900">{{ stat.value }}</div>
          <div class="text-sm text-gray-500">{{ stat.label }}</div>
        </div>
      </div>
    </div>

    <!-- Quick links -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <RouterLink to="/vehicles" class="card p-5 hover:border-brand-300 hover:shadow-md transition-all group">
        <div class="flex items-center gap-3 mb-2">
          <TruckIcon class="h-5 w-5 text-brand-500" />
          <h3 class="font-semibold text-gray-900">Vehicle Fleet</h3>
        </div>
        <p class="text-sm text-gray-500">View and manage all vehicles in the fleet.</p>
      </RouterLink>
      <RouterLink to="/leasing/offers" class="card p-5 hover:border-brand-300 hover:shadow-md transition-all group">
        <div class="flex items-center gap-3 mb-2">
          <DocumentTextIcon class="h-5 w-5 text-brand-500" />
          <h3 class="font-semibold text-gray-900">Leasing Offers</h3>
        </div>
        <p class="text-sm text-gray-500">Create and manage leasing offers for vehicles.</p>
      </RouterLink>
      <RouterLink to="/catalog" class="card p-5 hover:border-brand-300 hover:shadow-md transition-all group">
        <div class="flex items-center gap-3 mb-2">
          <BookOpenIcon class="h-5 w-5 text-brand-500" />
          <h3 class="font-semibold text-gray-900">Car Catalog</h3>
        </div>
        <p class="text-sm text-gray-500">Browse the full car specification database.</p>
      </RouterLink>
      <RouterLink to="/leasing/contracts" class="card p-5 hover:border-brand-300 hover:shadow-md transition-all group">
        <div class="flex items-center gap-3 mb-2">
          <ClipboardDocumentListIcon class="h-5 w-5 text-brand-500" />
          <h3 class="font-semibold text-gray-900">Contracts</h3>
        </div>
        <p class="text-sm text-gray-500">Track active and historical leasing contracts.</p>
      </RouterLink>
    </div>
  </div>
</template>
