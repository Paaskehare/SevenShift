import apiClient from './client'

export const leasingApi = {
  listOffers: (params) => apiClient.get('/leasing/offers/', { params }),
  getOffer: (id) => apiClient.get(`/leasing/offers/${id}/`),
  createOffer: (data) => apiClient.post('/leasing/offers/', data),
  updateOffer: (id, data) => apiClient.patch(`/leasing/offers/${id}/`, data),
  removeOffer: (id) => apiClient.delete(`/leasing/offers/${id}/`),

  listContracts: (params) => apiClient.get('/leasing/contracts/', { params }),
  getContract: (id) => apiClient.get(`/leasing/contracts/${id}/`),
  createContract: (data) => apiClient.post('/leasing/contracts/', data),
  updateContract: (id, data) => apiClient.patch(`/leasing/contracts/${id}/`, data),
}
