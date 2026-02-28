<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { vehiclesApi } from '@/api/vehicles'
import { ArrowLeftIcon, ArrowTopRightOnSquareIcon } from '@heroicons/vue/24/outline'

const route = useRoute()
const router = useRouter()
const vehicle = ref(null)
const loading = ref(true)
const activeImage = ref(0)

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

const imageUrl = (img) => img.image || img.url

const activeImageUrl = computed(() => {
  if (!vehicle.value?.images?.length) return vehicle.value?.thumbnail_url || null
  return imageUrl(vehicle.value.images[activeImage.value])
})

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
      <div class="flex items-start justify-between mb-5">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">{{ vehicle.display_name }}</h1>
          <p v-if="vehicle.trim" class="text-gray-500 mt-0.5">{{ vehicle.trim }}</p>
        </div>
        <span :class="['badge capitalize text-sm px-3 py-1', statusColors[vehicle.status] || 'bg-gray-100 text-gray-600']">
          {{ vehicle.status.replace('_', ' ') }}
        </span>
      </div>

      <!-- Image gallery -->
      <div v-if="activeImageUrl" class="mb-6">
        <div class="rounded-xl overflow-hidden bg-gray-100 aspect-video max-h-96">
          <img :src="activeImageUrl" class="w-full h-full object-cover" />
        </div>
        <div v-if="vehicle.images?.length > 1" class="flex gap-2 mt-2 overflow-x-auto pb-1">
          <button
            v-for="(img, i) in vehicle.images"
            :key="img.id"
            @click="activeImage = i"
            :class="['flex-shrink-0 rounded-lg overflow-hidden border-2 transition-colors', i === activeImage ? 'border-brand-500' : 'border-transparent']"
          >
            <img :src="imageUrl(img)" class="h-16 w-24 object-cover" loading="lazy" />
          </button>
        </div>
      </div>

      <!-- Detail grid -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">

        <!-- Pricing (only if price is set) -->
        <div v-if="vehicle.price" class="card p-5">
          <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">Pricing</h2>
          <dl class="space-y-3">
            <div class="flex justify-between text-sm items-center">
              <dt class="text-gray-500">Price</dt>
              <dd class="text-gray-900 font-semibold text-base">€{{ Number(vehicle.price).toLocaleString() }}</dd>
            </div>
            <div v-if="vehicle.price_rating" class="flex justify-between text-sm items-center">
              <dt class="text-gray-500">Rating</dt>
              <dd>
                <span :class="['px-2 py-0.5 rounded text-xs font-medium', priceRatingColors[vehicle.price_rating] || 'bg-gray-100 text-gray-500']">
                  {{ vehicle.price_rating.replace(/_/g, ' ') }}
                </span>
              </dd>
            </div>
            <div class="flex justify-between text-sm">
              <dt class="text-gray-500">VAT included</dt>
              <dd class="text-gray-900">{{ vehicle.price_vat ? 'Yes' : 'No' }}</dd>
            </div>
            <div v-if="vehicle.seller_type" class="flex justify-between text-sm">
              <dt class="text-gray-500">Seller</dt>
              <dd class="text-gray-900 capitalize">{{ vehicle.seller_type.toLowerCase() }}</dd>
            </div>
            <div v-if="vehicle.country" class="flex justify-between text-sm">
              <dt class="text-gray-500">Country</dt>
              <dd class="text-gray-900">{{ vehicle.country }}</dd>
            </div>
          </dl>
        </div>

        <!-- Identification -->
        <div class="card p-5">
          <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">Identification</h2>
          <dl class="space-y-3">
            <div v-if="vehicle.plate_number" class="flex justify-between text-sm">
              <dt class="text-gray-500">Plate</dt>
              <dd class="font-mono text-gray-900">{{ vehicle.plate_number }}</dd>
            </div>
            <div v-if="vehicle.vin" class="flex justify-between text-sm">
              <dt class="text-gray-500">VIN</dt>
              <dd class="font-mono text-gray-900 text-xs">{{ vehicle.vin }}</dd>
            </div>
            <div v-if="vehicle.first_registration" class="flex justify-between text-sm">
              <dt class="text-gray-500">First reg.</dt>
              <dd class="text-gray-900">{{ vehicle.first_registration }}</dd>
            </div>
            <div v-if="vehicle.body_type" class="flex justify-between text-sm">
              <dt class="text-gray-500">Body</dt>
              <dd class="text-gray-900">{{ vehicle.body_type }}</dd>
            </div>
            <div v-if="vehicle.color" class="flex justify-between text-sm">
              <dt class="text-gray-500">Colour</dt>
              <dd class="text-gray-900">{{ vehicle.color }}<span v-if="vehicle.color_code" class="text-gray-400 ml-1">({{ vehicle.color_code }})</span></dd>
            </div>
            <div v-if="vehicle.interior_color" class="flex justify-between text-sm">
              <dt class="text-gray-500">Interior</dt>
              <dd class="text-gray-900">{{ vehicle.interior_color }}</dd>
            </div>
          </dl>
        </div>

        <!-- Specs -->
        <div class="card p-5">
          <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">Specs</h2>
          <dl class="space-y-3">
            <div v-if="vehicle.fuel_type" class="flex justify-between text-sm">
              <dt class="text-gray-500">Fuel</dt>
              <dd class="text-gray-900">{{ vehicle.fuel_type }}</dd>
            </div>
            <div v-if="vehicle.power_hp" class="flex justify-between text-sm">
              <dt class="text-gray-500">Power</dt>
              <dd class="text-gray-900">{{ vehicle.power_hp }} hp</dd>
            </div>
            <div v-if="vehicle.battery_capacity_kwh" class="flex justify-between text-sm">
              <dt class="text-gray-500">Battery</dt>
              <dd class="text-gray-900">{{ vehicle.battery_capacity_kwh }} kWh</dd>
            </div>
            <div class="flex justify-between text-sm">
              <dt class="text-gray-500">Mileage</dt>
              <dd class="text-gray-900">{{ vehicle.mileage_km != null ? vehicle.mileage_km.toLocaleString() + ' km' : '—' }}</dd>
            </div>
          </dl>
        </div>

        <!-- Fleet / purchase info (only if any fleet data present) -->
        <div v-if="vehicle.purchase_date || vehicle.purchase_price || vehicle.notes" class="card p-5">
          <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">Fleet</h2>
          <dl class="space-y-3">
            <div v-if="vehicle.purchase_date" class="flex justify-between text-sm">
              <dt class="text-gray-500">Purchase Date</dt>
              <dd class="text-gray-900">{{ vehicle.purchase_date }}</dd>
            </div>
            <div v-if="vehicle.purchase_price" class="flex justify-between text-sm">
              <dt class="text-gray-500">Purchase Price</dt>
              <dd class="text-gray-900">€{{ Number(vehicle.purchase_price).toLocaleString() }}</dd>
            </div>
            <div v-if="vehicle.notes" class="text-sm">
              <dt class="text-gray-500 mb-1">Notes</dt>
              <dd class="text-gray-700 whitespace-pre-line">{{ vehicle.notes }}</dd>
            </div>
          </dl>
        </div>

        <!-- Catalog specs -->
        <div v-if="vehicle.variant_detail" class="card p-5 lg:col-span-2">
          <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">Catalog Specs</h2>
          <dl class="grid grid-cols-2 sm:grid-cols-4 gap-3">
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

        <!-- Equipment -->
        <div v-if="vehicle.equipment?.length" class="card p-5 lg:col-span-2">
          <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-3">Equipment</h2>
          <ul class="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-1.5">
            <li v-for="item in vehicle.equipment" :key="item" class="text-sm text-gray-700 flex items-start gap-1.5">
              <span class="text-gray-300 mt-0.5">•</span>{{ item }}
            </li>
          </ul>
        </div>

      </div>

      <!-- Source listing link -->
      <div v-if="vehicle.source_url" class="mt-4 text-center">
        <a
          :href="vehicle.source_url"
          target="_blank"
          rel="noopener noreferrer"
          class="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
        >
          View original listing on mobile.de
          <ArrowTopRightOnSquareIcon class="h-4 w-4" />
        </a>
      </div>

    </template>
  </div>
</template>
