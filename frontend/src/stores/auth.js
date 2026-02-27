import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const accessToken = ref(localStorage.getItem('access_token'))

  const isAuthenticated = computed(() => !!accessToken.value)

  async function login(username, password) {
    const { data } = await authApi.login(username, password)
    accessToken.value = data.access
    localStorage.setItem('access_token', data.access)
    localStorage.setItem('refresh_token', data.refresh)
    await fetchMe()
  }

  async function fetchMe() {
    const { data } = await authApi.me()
    user.value = data
  }

  function logout() {
    user.value = null
    accessToken.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  return { user, isAuthenticated, login, logout, fetchMe }
})
