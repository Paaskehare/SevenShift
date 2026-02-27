import apiClient from './client'

export const authApi = {
  login: (username, password) =>
    apiClient.post('/auth/token/', { username, password }),
  refresh: (refresh) =>
    apiClient.post('/auth/token/refresh/', { refresh }),
  me: () =>
    apiClient.get('/auth/me/'),
}
