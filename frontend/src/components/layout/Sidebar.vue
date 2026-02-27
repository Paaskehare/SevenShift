<script setup>
import { RouterLink, useRoute } from 'vue-router'
import {
  HomeIcon,
  TruckIcon,
  BookOpenIcon,
  DocumentTextIcon,
  ClipboardDocumentListIcon,
} from '@heroicons/vue/24/outline'

const route = useRoute()

const nav = [
  { name: 'Dashboard', to: '/', icon: HomeIcon },
  { name: 'Vehicles', to: '/vehicles', icon: TruckIcon },
  { name: 'Catalog', to: '/catalog', icon: BookOpenIcon },
  { name: 'Leasing Offers', to: '/leasing/offers', icon: DocumentTextIcon },
  { name: 'Contracts', to: '/leasing/contracts', icon: ClipboardDocumentListIcon },
]

function isActive(item) {
  if (item.to === '/') return route.path === '/'
  return route.path.startsWith(item.to)
}
</script>

<template>
  <div class="flex flex-col w-64 bg-brand-950 text-white flex-shrink-0">
    <!-- Logo -->
    <div class="flex items-center h-16 px-6 border-b border-brand-800">
      <span class="text-xl font-bold tracking-tight text-white">Seven<span class="text-brand-400">Shift</span></span>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
      <RouterLink
        v-for="item in nav"
        :key="item.name"
        :to="item.to"
        class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors"
        :class="isActive(item)
          ? 'bg-brand-700 text-white'
          : 'text-brand-200 hover:bg-brand-800 hover:text-white'"
      >
        <component :is="item.icon" class="h-5 w-5 flex-shrink-0" />
        {{ item.name }}
      </RouterLink>
    </nav>

    <!-- Bottom user badge -->
    <div class="p-4 border-t border-brand-800">
      <div class="text-xs text-brand-400 uppercase tracking-wider mb-1">Fleet Management</div>
      <div class="text-xs text-brand-300">SevenShift v1.0</div>
    </div>
  </div>
</template>
