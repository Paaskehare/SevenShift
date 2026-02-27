import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: () => import('@/components/layout/AppShell.vue'),
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/DashboardView.vue'),
      },
      // Vehicles
      {
        path: 'vehicles',
        name: 'VehicleList',
        component: () => import('@/views/vehicles/VehicleList.vue'),
      },
      {
        path: 'vehicles/:id',
        name: 'VehicleDetail',
        component: () => import('@/views/vehicles/VehicleDetail.vue'),
      },
      // Catalog
      {
        path: 'catalog',
        name: 'CatalogBrowser',
        component: () => import('@/views/catalog/CatalogBrowser.vue'),
      },
      {
        path: 'catalog/variants/:id',
        name: 'VariantDetail',
        component: () => import('@/views/catalog/VariantDetail.vue'),
      },
      // Leasing
      {
        path: 'leasing/offers',
        name: 'OfferList',
        component: () => import('@/views/leasing/OfferList.vue'),
      },
      {
        path: 'leasing/offers/:id',
        name: 'OfferDetail',
        component: () => import('@/views/leasing/OfferDetail.vue'),
      },
      {
        path: 'leasing/contracts',
        name: 'ContractList',
        component: () => import('@/views/leasing/ContractList.vue'),
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: 'Login' }
  }
  if (auth.isAuthenticated && !auth.user) {
    try {
      await auth.fetchMe()
    } catch {
      auth.logout()
      return { name: 'Login' }
    }
  }
})

export default router
