<template>
  <div class="login-page">
    <!-- 背景波形 -->
    <div class="bg-bars">
      <div v-for="i in 60" :key="i" class="bg-bar" :style="barStyle(i)"></div>
    </div>

    <div class="login-card card">
      <div class="login-brand">
        <div class="logo-icon">𝄞</div>
        <div class="logo-name">AEGIS</div>
        <div class="logo-sub">智慧音乐教室</div>
      </div>

      <form @submit.prevent="submit" class="login-form">
        <div class="field">
          <label>账号</label>
          <input class="input" v-model="username" placeholder="输入账号" autocomplete="username" required />
        </div>
        <div class="field">
          <label>密码</label>
          <input class="input" type="password" v-model="password" placeholder="输入密码" autocomplete="current-password" required />
        </div>
        <div v-if="error" class="error-msg">{{ error }}</div>
        <button type="submit" class="btn btn-primary w-full" :disabled="loading">
          <span v-if="loading" class="spinner" style="width:16px;height:16px;border-width:2px;"></span>
          <span v-else>登 录</span>
        </button>
      </form>

      <div class="demo-hint">
        <span class="hint-label">Demo 账号</span>
        <div class="hint-row" @click="fillDemo('teacher01','aegis2026')">👩‍🏫 teacher01 / aegis2026 <span class="fill-hint">点击填入</span></div>
        <div class="hint-row" @click="fillDemo('stu01','student123')">🎓 stu01 / student123 <span class="fill-hint">点击填入</span></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const auth     = useAuthStore()
const router   = useRouter()
const username = ref('')
const password = ref('')
const loading  = ref(false)
const error    = ref('')

function fillDemo(u, p) { username.value = u; password.value = p }

function barStyle(i) {
  const h = 20 + Math.sin(i * 0.7) * 60 + Math.random() * 40
  const dur = 0.8 + Math.random() * 1.5
  const delay = Math.random() * 2
  return { '--h': h + 'px', '--dur': dur + 's', '--delay': delay + 's' }
}

async function submit() {
  error.value = ''; loading.value = true
  try {
    const role = await auth.login(username.value, password.value)
    router.push(role === 'teacher' ? '/teacher' : '/studio')
  } catch (e) {
    error.value = e.response?.data?.detail || '登录失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh; display: flex; align-items: center; justify-content: center;
  position: relative; overflow: hidden;
  background: radial-gradient(ellipse 80% 60% at 30% 30%, rgba(26,58,107,0.3) 0%, transparent 70%), var(--navy);
}
.bg-bars {
  position: absolute; bottom: 0; left: 0; right: 0; height: 180px;
  display: flex; align-items: flex-end; justify-content: center; gap: 4px;
  padding: 0 1rem; opacity: 0.5;
}
.bg-bar {
  width: 5px; border-radius: 2px 2px 0 0;
  background: linear-gradient(to top, var(--gold), transparent);
  animation: wavePulse var(--dur, 1s) ease-in-out infinite alternate;
  animation-delay: var(--delay, 0s);
  height: var(--h, 20px);
}
@keyframes wavePulse { from { height: 8px; opacity:0.2 } to { height: var(--h, 40px); opacity:0.7 } }

.login-card {
  width: 100%; max-width: 380px; padding: 2.5rem 2rem;
  position: relative; z-index: 1;
  background: rgba(6,15,30,0.92);
}
.login-brand { text-align: center; margin-bottom: 2rem; }
.logo-icon { font-size: 3rem; color: var(--gold); line-height: 1; }
.logo-name { font-size: 1.8rem; font-weight: 900; color: var(--gold); letter-spacing: 0.15em; }
.logo-sub  { font-size: 0.8rem; color: var(--text-muted); letter-spacing: 0.1em; margin-top: 0.2rem; }
.login-form { display: flex; flex-direction: column; gap: 1rem; }
.w-full { width: 100%; justify-content: center; padding: 0.7rem; font-size: 0.95rem; }
.error-msg { font-size: 0.8rem; color: #F87171; text-align: center; }
.demo-hint {
  margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid var(--border);
  font-size: 0.75rem;
}
.hint-label { color: var(--text-muted); display: block; margin-bottom: 0.4rem; letter-spacing: 0.05em; }
.hint-row {
  color: var(--text-secondary); padding: 0.3rem 0.5rem; border-radius: 4px;
  cursor: pointer; transition: background 0.15s; display: flex; align-items: center; gap: 0.5rem;
}
.hint-row:hover { background: var(--gold-dim); }
.fill-hint { margin-left: auto; font-size: 0.68rem; color: var(--gold); }
</style>
