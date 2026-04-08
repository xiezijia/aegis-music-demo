import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'

export const useAuthStore = defineStore('auth', () => {
  const token       = ref(localStorage.getItem('aegis_token') || '')
  const role        = ref(localStorage.getItem('aegis_role') || '')
  const displayName = ref(localStorage.getItem('aegis_name') || '')
  const userId      = ref(Number(localStorage.getItem('aegis_uid')) || 0)

  if (token.value) {
    axios.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
  }

  async function login(username, password) {
    const { data } = await axios.post('/api/auth/login', { username, password })
    token.value       = data.access_token
    role.value        = data.role
    displayName.value = data.display_name
    userId.value      = data.user_id
    localStorage.setItem('aegis_token', data.access_token)
    localStorage.setItem('aegis_role',  data.role)
    localStorage.setItem('aegis_name',  data.display_name)
    localStorage.setItem('aegis_uid',   data.user_id)
    axios.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`
    return data.role
  }

  function logout() {
    token.value = role.value = displayName.value = ''
    userId.value = 0
    localStorage.clear()
    delete axios.defaults.headers.common['Authorization']
  }

  return { token, role, displayName, userId, login, logout }
})
