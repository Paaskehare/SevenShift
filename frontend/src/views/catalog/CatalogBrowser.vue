<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { catalogApi } from '@/api/catalog'
import { MagnifyingGlassIcon } from '@heroicons/vue/24/outline'

const router = useRouter()
const makes = ref([])
const selectedMake = ref(null)
const models = ref([])
const selectedModel = ref(null)
const generations = ref([])
const selectedGeneration = ref(null)
const variants = ref([])
const search = ref('')
const loading = ref({ makes: false, models: false, generations: false, variants: false })

async function fetchMakes() {
  loading.value.makes = true
  const { data } = await catalogApi.getMakes({ search: search.value || undefined, page_size: 100 })
  makes.value = data.results
  loading.value.makes = false
}

async function selectMake(make) {
  selectedMake.value = make
  selectedModel.value = null
  selectedGeneration.value = null
  generations.value = []
  variants.value = []
  loading.value.models = true
  const { data } = await catalogApi.getModels({ make: make.id, page_size: 100 })
  models.value = data.results
  loading.value.models = false
}

async function selectModel(model) {
  selectedModel.value = model
  selectedGeneration.value = null
  variants.value = []
  loading.value.generations = true
  const { data } = await catalogApi.getGenerations({ car_model: model.id, page_size: 100 })
  generations.value = data.results
  loading.value.generations = false
}

async function selectGeneration(generation) {
  selectedGeneration.value = generation
  loading.value.variants = true
  const { data } = await catalogApi.getVariants({ generation: generation.id, page_size: 100 })
  variants.value = data.results
  loading.value.variants = false
}

watch(search, fetchMakes)
onMounted(fetchMakes)
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900">Car Catalog</h1>
    </div>

    <!-- Search -->
    <div class="card p-4 mb-4">
      <div class="relative">
        <MagnifyingGlassIcon class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <input
          v-model="search"
          type="text"
          placeholder="Search makes…"
          class="form-input pl-9"
        />
      </div>
    </div>

    <!-- Four-column drill-down -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- Makes -->
      <div class="card overflow-hidden">
        <div class="px-4 py-3 bg-gray-50 border-b border-gray-200">
          <h2 class="text-sm font-semibold text-gray-700">Makes</h2>
        </div>
        <div class="divide-y divide-gray-100 max-h-[60vh] overflow-y-auto">
          <div v-if="loading.makes" class="px-4 py-6 text-center text-sm text-gray-400">Loading…</div>
          <button
            v-for="make in makes"
            :key="make.id"
            @click="selectMake(make)"
            class="w-full text-left px-4 py-3 text-sm transition-colors hover:bg-gray-50"
            :class="selectedMake?.id === make.id ? 'bg-brand-50 text-brand-700 font-medium' : 'text-gray-700'"
          >
            {{ make.name }}
            <span v-if="make.country" class="text-xs text-gray-400 ml-1">({{ make.country }})</span>
          </button>
          <div v-if="!loading.makes && !makes.length" class="px-4 py-6 text-center text-sm text-gray-400">
            No makes found.
          </div>
        </div>
      </div>

      <!-- Models -->
      <div class="card overflow-hidden">
        <div class="px-4 py-3 bg-gray-50 border-b border-gray-200">
          <h2 class="text-sm font-semibold text-gray-700">
            {{ selectedMake ? `${selectedMake.name} Models` : 'Models' }}
          </h2>
        </div>
        <div class="divide-y divide-gray-100 max-h-[60vh] overflow-y-auto">
          <div v-if="!selectedMake" class="px-4 py-6 text-center text-sm text-gray-400">Select a make</div>
          <div v-else-if="loading.models" class="px-4 py-6 text-center text-sm text-gray-400">Loading…</div>
          <button
            v-for="model in models"
            :key="model.id"
            @click="selectModel(model)"
            class="w-full text-left px-4 py-3 text-sm transition-colors hover:bg-gray-50"
            :class="selectedModel?.id === model.id ? 'bg-brand-50 text-brand-700 font-medium' : 'text-gray-700'"
          >
            {{ model.name }}
          </button>
          <div v-if="selectedMake && !loading.models && !models.length" class="px-4 py-6 text-center text-sm text-gray-400">
            No models found.
          </div>
        </div>
      </div>

      <!-- Generations -->
      <div class="card overflow-hidden">
        <div class="px-4 py-3 bg-gray-50 border-b border-gray-200">
          <h2 class="text-sm font-semibold text-gray-700">
            {{ selectedModel ? `${selectedModel.name} Generations` : 'Generations' }}
          </h2>
        </div>
        <div class="divide-y divide-gray-100 max-h-[60vh] overflow-y-auto">
          <div v-if="!selectedModel" class="px-4 py-6 text-center text-sm text-gray-400">Select a model</div>
          <div v-else-if="loading.generations" class="px-4 py-6 text-center text-sm text-gray-400">Loading…</div>
          <button
            v-for="generation in generations"
            :key="generation.id"
            @click="selectGeneration(generation)"
            class="w-full text-left px-4 py-3 text-sm transition-colors hover:bg-gray-50"
            :class="selectedGeneration?.id === generation.id ? 'bg-brand-50 text-brand-700 font-medium' : 'text-gray-700'"
          >
            <div>{{ generation.name || '—' }}</div>
            <div class="text-xs text-gray-400">
              {{ generation.production_start }}{{ generation.production_end ? `–${generation.production_end}` : generation.production_start ? '–present' : '' }}
            </div>
          </button>
          <div v-if="selectedModel && !loading.generations && !generations.length" class="px-4 py-6 text-center text-sm text-gray-400">
            No generations found.
          </div>
        </div>
      </div>

      <!-- Variants -->
      <div class="card overflow-hidden">
        <div class="px-4 py-3 bg-gray-50 border-b border-gray-200">
          <h2 class="text-sm font-semibold text-gray-700">
            {{ selectedGeneration ? `${selectedGeneration.name || selectedModel?.name} Variants` : 'Variants' }}
          </h2>
        </div>
        <div class="divide-y divide-gray-100 max-h-[60vh] overflow-y-auto">
          <div v-if="!selectedGeneration" class="px-4 py-6 text-center text-sm text-gray-400">Select a generation</div>
          <div v-else-if="loading.variants" class="px-4 py-6 text-center text-sm text-gray-400">Loading…</div>
          <button
            v-for="variant in variants"
            :key="variant.id"
            @click="router.push({ name: 'VariantDetail', params: { id: variant.id } })"
            class="w-full text-left px-4 py-3 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
          >
            <div class="font-medium">{{ variant.variant || '—' }}</div>
            <div class="text-xs text-gray-400 flex gap-2 mt-0.5">
              <span v-if="variant.fuel_type">{{ variant.fuel_type }}</span>
              <span v-if="variant.power_hp">{{ variant.power_hp }} hp</span>
              <span v-if="variant.transmission">{{ variant.transmission }}</span>
            </div>
          </button>
          <div v-if="selectedGeneration && !loading.variants && !variants.length" class="px-4 py-6 text-center text-sm text-gray-400">
            No variants found.
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
