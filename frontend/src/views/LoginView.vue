<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    router.push({ name: 'Dashboard' })
  } catch {
    error.value = 'Invalid credentials. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-brand-950 flex items-center justify-center px-4">
    <div class="w-full max-w-sm">
      <!-- Logo -->
      <div class="text-center mb-10">
        <h1 class="text-4xl font-bold text-white tracking-tight">
          Seven<span class="text-brand-400">Shift</span>
        </h1>
        <p class="mt-2 text-brand-300 text-sm">Fleet Management Platform</p>
      </div>

      <!-- Card -->
      <div class="card p-8">
        <h2 class="text-lg font-semibold text-gray-900 mb-6">Sign in to your account</h2>

        <form @submit.prevent="handleLogin" class="space-y-4">
          <div>
            <label for="username" class="form-label">Username</label>
            <input
              id="username"
              v-model="username"
              type="text"
              autocomplete="username"
              required
              class="form-input"
              placeholder="Enter your username"
            />
          </div>

          <div>
            <label for="password" class="form-label">Password</label>
            <input
              id="password"
              v-model="password"
              type="password"
              autocomplete="current-password"
              required
              class="form-input"
              placeholder="Enter your password"
            />
          </div>

          <div
            v-if="error"
            class="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3"
          >
            {{ error }}
          </div>

          <button type="submit" :disabled="loading" class="btn-primary w-full mt-2">
            <span v-if="loading">Signing in…</span>
            <span v-else>Sign in</span>
          </button>
        </form>
      </div>
    </div>
  </div>
</template>
