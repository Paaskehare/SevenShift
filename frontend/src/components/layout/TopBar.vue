<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ArrowRightOnRectangleIcon, UserCircleIcon } from '@heroicons/vue/24/outline'

const auth = useAuthStore()
const router = useRouter()

function handleLogout() {
  auth.logout()
  router.push({ name: 'Login' })
}
</script>

<template>
  <header class="flex items-center justify-between h-16 px-6 bg-white border-b border-gray-200 flex-shrink-0">
    <div>
      <!-- Page title slot or breadcrumb could go here -->
    </div>
    <div class="flex items-center gap-4">
      <div class="flex items-center gap-2 text-sm text-gray-600">
        <UserCircleIcon class="h-5 w-5 text-gray-400" />
        <span class="font-medium">{{ auth.user?.username || '—' }}</span>
        <span
          v-if="auth.user?.role"
          class="badge bg-brand-50 text-brand-700 capitalize"
        >{{ auth.user.role }}</span>
      </div>
      <button
        @click="handleLogout"
        class="btn-secondary !px-3 !py-1.5 !text-xs gap-1.5"
      >
        <ArrowRightOnRectangleIcon class="h-4 w-4" />
        Logout
      </button>
    </div>
  </header>
</template>
