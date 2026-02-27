import apiClient from './client'

export const vehiclesApi = {
  list: (params) => apiClient.get('/vehicles/', { params }),
  get: (id) => apiClient.get(`/vehicles/${id}/`),
  create: (data) => apiClient.post('/vehicles/', data),
  update: (id, data) => apiClient.patch(`/vehicles/${id}/`, data),
  remove: (id) => apiClient.delete(`/vehicles/${id}/`),
}
