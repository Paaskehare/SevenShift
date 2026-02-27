import apiClient from './client'

export const catalogApi = {
  getMakes: (params) => apiClient.get('/catalog/makes/', { params }),
  getMake: (id) => apiClient.get(`/catalog/makes/${id}/`),
  getModels: (params) => apiClient.get('/catalog/models/', { params }),
  getModel: (id) => apiClient.get(`/catalog/models/${id}/`),
  getGenerations: (params) => apiClient.get('/catalog/generations/', { params }),
  getGeneration: (id) => apiClient.get(`/catalog/generations/${id}/`),
  getVariants: (params) => apiClient.get('/catalog/variants/', { params }),
  getVariant: (id) => apiClient.get(`/catalog/variants/${id}/`),
}
