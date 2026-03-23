import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Process from '../views/MainView.vue'
import SimulationView from '../views/SimulationView.vue'
import SimulationRunView from '../views/SimulationRunView.vue'
import ReportView from '../views/ReportView.vue'
import InteractionView from '../views/InteractionView.vue'
import AuthView from '../views/AuthView.vue'
import { authClient } from '../lib/auth-client'

const routes = [
  {
    path: '/auth',
    name: 'Auth',
    component: AuthView,
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'Home',
    component: Home,
    meta: { requiresAuth: false }
  },
  {
    path: '/process/:projectId',
    name: 'Process',
    component: Process,
    props: true,
    meta: { requiresAuth: true }
  },
  {
    path: '/simulation/:simulationId',
    name: 'Simulation',
    component: SimulationView,
    props: true,
    meta: { requiresAuth: true }
  },
  {
    path: '/simulation/:simulationId/start',
    name: 'SimulationRun',
    component: SimulationRunView,
    props: true,
    meta: { requiresAuth: true }
  },
  {
    path: '/report/:reportId',
    name: 'Report',
    component: ReportView,
    props: true,
    meta: { requiresAuth: true }
  },
  {
    path: '/interaction/:reportId',
    name: 'Interaction',
    component: InteractionView,
    props: true,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to) => {
  const requiresAuth = to.meta.requiresAuth !== false
  let data = null

  try {
    const session = await authClient.getSession()
    data = session.data
  } catch (error) {
    console.warn('Session lookup failed during navigation guard:', error)
  }

  if (!requiresAuth && data && to.name === 'Auth') {
    return { name: 'Home' }
  }

  if (requiresAuth && !data) {
    return {
      name: 'Auth',
      query: { redirect: to.fullPath }
    }
  }

  return true
})

export default router
