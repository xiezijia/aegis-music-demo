<template>
  <div class="app-shell">
    <Navbar v-if="auth.token" />
    <main class="app-main" :class="{ 'with-nav': auth.token }">
      <RouterView />
    </main>
    <!-- Toast 通知 -->
    <div class="toast-wrap">
      <div v-for="t in toasts" :key="t.id" :class="['toast', `toast-${t.type}`]">
        {{ t.msg }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { provide, ref } from 'vue'
import { useAuthStore } from './stores/auth.js'
import Navbar from './components/Navbar.vue'

const auth   = useAuthStore()
const toasts = ref([])

function showToast(msg, type = 'info', duration = 3000) {
  const id = Date.now()
  toasts.value.push({ id, msg, type })
  setTimeout(() => { toasts.value = toasts.value.filter(t => t.id !== id) }, duration)
}

provide('toast', showToast)
</script>

<style scoped>
.app-shell { display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
.app-main  { flex: 1; overflow-y: auto; }
.app-main.with-nav { margin-top: 56px; }
</style>
