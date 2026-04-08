import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue') },
  { path: '/studio', name: 'Studio', component: () => import('../views/Studio.vue'), meta: { auth: true, role: 'student' } },
  { path: '/history', name: 'History', component: () => import('../views/History.vue'), meta: { auth: true, role: 'student' } },
  { path: '/teacher', name: 'Teacher', component: () => import('../views/Teacher.vue'), meta: { auth: true, role: 'teacher' } },
  { path: '/', redirect: '/login' },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.auth && !auth.token) return '/login'
  if (to.meta.role && auth.role !== to.meta.role) {
    return auth.role === 'teacher' ? '/teacher' : '/studio'
  }
})

export default router
