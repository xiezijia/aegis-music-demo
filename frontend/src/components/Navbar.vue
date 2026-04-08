<template>
  <header class="navbar">
    <div class="nav-brand">
      <span class="brand-icon">𝄞</span>
      <span class="brand-name">AEGIS</span>
      <span class="brand-sub">智慧音乐教室</span>
    </div>
    <nav class="nav-links">
      <template v-if="auth.role === 'student'">
        <RouterLink to="/studio" class="nav-link">作曲工坊</RouterLink>
        <RouterLink to="/history" class="nav-link">我的作品</RouterLink>
      </template>
      <template v-else>
        <RouterLink to="/teacher" class="nav-link">批改仪表盘</RouterLink>
      </template>
    </nav>
    <div class="nav-user">
      <span class="user-badge" :class="auth.role">{{ auth.role === 'teacher' ? '👩‍🏫' : '🎓' }}</span>
      <span class="user-name">{{ auth.displayName }}</span>
      <button class="btn btn-ghost btn-sm" @click="logout">退出</button>
    </div>
  </header>
</template>

<script setup>
import { useAuthStore } from '../stores/auth.js'
import { useRouter } from 'vue-router'
const auth   = useAuthStore()
const router = useRouter()
function logout() { auth.logout(); router.push('/login') }
</script>

<style scoped>
.navbar {
  position: fixed; top: 0; left: 0; right: 0; z-index: 100; height: 56px;
  background: rgba(6,15,30,0.95);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center;
  padding: 0 1.5rem; gap: 2rem;
  backdrop-filter: blur(8px);
}
.nav-brand { display: flex; align-items: center; gap: 0.5rem; flex-shrink: 0; }
.brand-icon { font-size: 1.4rem; color: var(--gold); }
.brand-name { font-size: 1rem; font-weight: 800; color: var(--gold); letter-spacing: 0.08em; }
.brand-sub  { font-size: 0.72rem; color: var(--text-muted); letter-spacing: 0.05em; }
.nav-links  { display: flex; gap: 0.3rem; flex: 1; }
.nav-link   { padding: 0.35rem 0.9rem; border-radius: 5px; font-size: 0.85rem; color: var(--text-secondary); text-decoration: none; transition: all 0.2s; }
.nav-link:hover, .nav-link.router-link-active { background: var(--gold-dim); color: var(--gold); }
.nav-user   { display: flex; align-items: center; gap: 0.6rem; flex-shrink: 0; }
.user-badge { font-size: 1rem; }
.user-name  { font-size: 0.84rem; color: var(--text-secondary); }
.btn-sm     { padding: 0.3rem 0.8rem; font-size: 0.75rem; }
</style>
