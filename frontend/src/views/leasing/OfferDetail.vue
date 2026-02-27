<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { leasingApi } from '@/api/leasing'
import { ArrowLeftIcon } from '@heroicons/vue/24/outline'

const route = useRoute()
const router = useRouter()
const offer = ref(null)
const loading = ref(true)

const statusColors = {
  draft: 'bg-gray-100 text-gray-600',
  active: 'bg-green-100 text-green-700',
  expired: 'bg-red-100 text-red-600',
  archived: 'bg-gray-100 text-gray-400',
}

onMounted(async () => {
  try {
    const { data } = await leasingApi.getOffer(route.params.id)
    offer.value = data
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <button @click="router.back()" class="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 mb-6 transition-colors">
      <ArrowLeftIcon class="h-4 w-4" />
      Back to Offers
    </button>

    <div v-if="loading" class="text-center py-12 text-gray-400">Loading…</div>

    <template v-else-if="offer">
      <div class="flex items-start justify-between mb-6">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">Leasing Offer #{{ offer.id }}</h1>
          <p class="text-gray-500 mt-1">
            Created {{ new Date(offer.created_at).toLocaleDateString() }}
          </p>
        </div>
        <span :class="['badge capitalize text-sm px-3 py-1', statusColors[offer.status] || 'bg-gray-100']">
          {{ offer.status }}
        </span>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <!-- Pricing terms -->
        <div class="card p-5">
          <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">Pricing Terms</h2>
          <dl class="space-y-3">
            <div class="flex justify-between text-sm">
              <dt class="text-gray-500">Monthly Rate</dt>
              <dd class="text-gray-900 font-bold text-base">€{{ Number(offer.monthly_rate).toLocaleString() }}</dd>
            </div>
            <div class="flex justify-between text-sm">
              <dt class="text-gray-500">Down Payment</dt>
              <dd class="text-gray-900 font-medium">€{{ Number(offer.down_payment).toLocaleString() }}</dd>
            </div>
            <div class="flex justify-between text-sm">
              <dt class="text-gray-500">Duration</dt>
              <dd class="text-gray-900 font-medium">{{ offer.duration_months }} months</dd>
            </div>
            <div class="flex justify-between text-sm">
              <dt class="text-gray-500">KM Limit/Year</dt>
              <dd class="text-gray-900 font-medium">{{ offer.km_limit_per_year.toLocaleString() }} km</dd>
            </div>
            <div v-if="offer.residual_value" class="flex justify-between text-sm">
              <dt class="text-gray-500">Residual Value</dt>
              <dd class="text-gray-900 font-medium">€{{ Number(offer.residual_value).toLocaleString() }}</dd>
            </div>
            <div v-if="offer.excess_km_rate" class="flex justify-between text-sm">
              <dt class="text-gray-500">Excess KM Rate</dt>
              <dd class="text-gray-900 font-medium">€{{ offer.excess_km_rate }}/km</dd>
            </div>
          </dl>
        </div>

        <!-- Linked vehicle/trim -->
        <div class="card p-5">
          <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">Linked To</h2>
          <dl class="space-y-3">
            <div v-if="offer.vehicle" class="flex justify-between text-sm">
              <dt class="text-gray-500">Vehicle</dt>
              <dd>
                <RouterLink :to="`/vehicles/${offer.vehicle}`" class="text-brand-600 hover:text-brand-700 font-medium">
                  Vehicle #{{ offer.vehicle }}
                </RouterLink>
              </dd>
            </div>
            <div v-if="offer.variant" class="flex justify-between text-sm">
              <dt class="text-gray-500">Catalog Variant</dt>
              <dd>
                <RouterLink :to="`/catalog/variants/${offer.variant}`" class="text-brand-600 hover:text-brand-700 font-medium">
                  Variant #{{ offer.variant }}
                </RouterLink>
              </dd>
            </div>
            <div v-if="offer.valid_from || offer.valid_until" class="flex justify-between text-sm">
              <dt class="text-gray-500">Validity</dt>
              <dd class="text-gray-900">{{ offer.valid_from || '—' }} → {{ offer.valid_until || '—' }}</dd>
            </div>
          </dl>
        </div>

        <div v-if="offer.notes" class="card p-5 lg:col-span-2">
          <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-2">Notes</h2>
          <p class="text-sm text-gray-700 whitespace-pre-line">{{ offer.notes }}</p>
        </div>
      </div>
    </template>
  </div>
</template>
