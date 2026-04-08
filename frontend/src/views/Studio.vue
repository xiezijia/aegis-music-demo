<template>
  <div class="studio-page">
    <!-- 左：输入表单 -->
    <aside class="studio-left">
      <div class="panel-title">
        <span class="panel-icon">✦</span> 创作描述
      </div>

      <form @submit.prevent="generate" class="studio-form">
        <div class="field">
          <label>作品标题</label>
          <input class="input" v-model="form.title" placeholder="给这首曲子起个名字" required />
        </div>

        <div class="field">
          <label>情绪 / 场景描述 <span class="hint-text">（中文描述，越具体越好）</span></label>
          <textarea class="input" v-model="form.prompt" rows="4"
            placeholder="例：忧郁的秋天傍晚，古筝和箫的意境，思念远方的故人，节奏缓慢，有留白感" required></textarea>
        </div>

        <div class="field">
          <label>风格标签 <span class="hint-text">（空格分隔）</span></label>
          <div class="style-presets">
            <span v-for="tag in styleTags" :key="tag"
              :class="['style-tag', { active: form.style.includes(tag) }]"
              @click="toggleTag(tag)">{{ tag }}</span>
          </div>
          <input class="input" v-model="form.style" placeholder="古风 民族 忧郁…" style="margin-top:0.4rem" />
        </div>

        <div class="field">
          <label>歌词 <span class="hint-text">（选填，留空则纯音乐）</span></label>
          <textarea class="input" v-model="form.lyrics" rows="3" placeholder="在此输入歌词，或留空生成纯音乐…"></textarea>
        </div>

        <div v-if="lastTrack" class="base-on-hint">
          <span class="tag tag-gold">基于 v{{ lastTrack.version }}</span>
          <span class="bo-text">在上一版本基础上修改</span>
          <button type="button" class="btn-clear" @click="clearBase">✕ 清除</button>
        </div>

        <button type="submit" class="btn btn-primary generate-btn" :disabled="generating">
          <span v-if="generating" class="spinner" style="width:16px;height:16px;border-width:2px;"></span>
          <span v-else>🎵 AEGIS 开始创作</span>
        </button>
      </form>

      <div v-if="generating" class="generating-overlay">
        <div class="gen-anim">
          <div v-for="i in 12" :key="i" class="gen-bar" :style="genBarStyle(i)"></div>
        </div>
        <p class="gen-text">AEGIS 音乐大模型正在创作<span class="dots"></span></p>
        <p class="gen-sub">通常需要 20—40 秒</p>
      </div>
    </aside>

    <!-- 右：最新生成结果 + 最近历史 -->
    <main class="studio-right">
      <div class="result-section">
        <div class="panel-title">
          <span class="panel-icon">🎵</span> 最新作品
        </div>
        <div v-if="currentTrack" class="current-result">
          <TrackCard :track="currentTrack">
            <template #actions>
              <button class="btn btn-outline" @click="remixThis">🔄 在此基础上修改</button>
              <button v-if="!currentTrack.submitted && currentTrack.status === 'done'"
                class="btn btn-primary" @click="submitIt">📤 提交给老师</button>
              <span v-if="currentTrack.submitted" class="tag tag-green">✓ 已提交</span>
            </template>
          </TrackCard>
        </div>
        <div v-else class="empty">
          <div class="empty-icon">🎼</div>
          <p>填写左侧表单，让 AEGIS 为你创作第一首曲子</p>
        </div>
      </div>

      <div v-if="recentTracks.length > 0" class="history-preview">
        <div class="panel-title" style="margin-bottom:0.8rem">
          <span class="panel-icon">📂</span> 创作历史
          <RouterLink to="/history" class="view-all">查看全部 →</RouterLink>
        </div>
        <div class="tracks-list">
          <TrackCard v-for="t in recentTracks" :key="t.id" :track="t">
            <template #actions>
              <button class="btn btn-ghost" style="font-size:0.78rem" @click="remixTrack(t)">🔄 基于此修改</button>
            </template>
          </TrackCard>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, inject, onMounted } from 'vue'
import TrackCard from '../components/TrackCard.vue'
import { useMusicStore } from '../stores/music.js'

const music   = useMusicStore()
const toast   = inject('toast')

const form = ref({ title: '', prompt: '', style: '', lyrics: '' })
const generating  = ref(false)
const currentTrack = ref(null)
const lastTrack    = ref(null)

const styleTags = ['古风', '民族', '现代', '流行', '电子', '古典', '爵士', '忧郁', '欢快', '激昂', '古筝', '二胡', '琵琶']

const recentTracks = computed(() =>
  music.tracks.filter(t => t.id !== currentTrack.value?.id).slice(0, 4)
)

function toggleTag(tag) {
  const tags = form.value.style.split(' ').filter(Boolean)
  const idx = tags.indexOf(tag)
  idx >= 0 ? tags.splice(idx, 1) : tags.push(tag)
  form.value.style = tags.join(' ')
}

function genBarStyle(i) {
  const h = 10 + Math.sin(i) * 30 + Math.random() * 20
  return { '--h': h + 'px', '--dur': (0.5 + Math.random()) + 's', '--delay': (i * 0.08) + 's' }
}

function remixThis()     { if (currentTrack.value) remixTrack(currentTrack.value) }
function remixTrack(t)   { lastTrack.value = t; form.value.parent_id = t.id; toast('已选择 v' + t.version + ' 作为基础版本', 'info') }
function clearBase()     { lastTrack.value = null; form.value.parent_id = null }

async function generate() {
  generating.value = true
  try {
    const payload = { ...form.value, parent_id: lastTrack.value?.id || null }
    const { track_id } = await music.generate(payload)
    currentTrack.value = { id: track_id, status: 'generating', title: form.value.title, prompt: form.value.prompt, style: form.value.style, lyrics: form.value.lyrics, version: (lastTrack.value?.version || 0) + 1, created_at: new Date().toISOString() }
    const result = await music.pollStatus(track_id)
    currentTrack.value = { ...currentTrack.value, ...result }
    await music.fetchMyTracks()
    toast('✓ 创作完成！', 'success')
  } catch (e) {
    toast('生成失败：' + e.message, 'error')
    if (currentTrack.value) currentTrack.value.status = 'error'
  } finally {
    generating.value = false
  }
}

async function submitIt() {
  await music.submitTrack(currentTrack.value.id)
  currentTrack.value.submitted = 1
  toast('已提交给老师', 'success')
}

onMounted(() => music.fetchMyTracks())
</script>

<style scoped>
.studio-page { display: flex; height: 100%; }
.studio-left {
  width: 380px; flex-shrink: 0;
  border-right: 1px solid var(--border);
  padding: 1.5rem; overflow-y: auto;
  position: relative;
  background: rgba(6,15,30,0.4);
}
.studio-right { flex: 1; padding: 1.5rem; overflow-y: auto; display: flex; flex-direction: column; gap: 1.5rem; }

.panel-title {
  font-size: 0.78rem; font-weight: 700; color: var(--gold);
  letter-spacing: 0.1em; text-transform: uppercase;
  display: flex; align-items: center; gap: 0.4rem;
  margin-bottom: 1.2rem;
}
.panel-icon { font-size: 0.9rem; }
.view-all { margin-left: auto; font-size: 0.72rem; color: var(--text-muted); text-decoration: none; }
.view-all:hover { color: var(--gold); }

.studio-form { display: flex; flex-direction: column; gap: 1rem; }
.hint-text { font-size: 0.68rem; color: var(--text-muted); font-weight: 400; }

.style-presets { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-bottom: 0; }
.style-tag {
  padding: 0.22rem 0.55rem; border-radius: 3px; font-size: 0.72rem; cursor: pointer;
  background: rgba(90,104,128,0.15); border: 1px solid var(--border); color: var(--text-muted);
  transition: all 0.15s;
}
.style-tag:hover { border-color: var(--border-bright); color: var(--text-secondary); }
.style-tag.active { background: var(--gold-dim); border-color: var(--border-bright); color: var(--gold); }

.base-on-hint { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8rem; }
.bo-text { color: var(--text-muted); }
.btn-clear { background: none; border: none; color: var(--text-muted); cursor: pointer; font-size: 0.8rem; margin-left: auto; }
.btn-clear:hover { color: #F87171; }

.generate-btn { width: 100%; justify-content: center; padding: 0.75rem; font-size: 0.95rem; margin-top: 0.5rem; }

.generating-overlay {
  position: absolute; inset: 0; background: rgba(6,15,30,0.92);
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1rem;
  z-index: 10;
}
.gen-anim { display: flex; align-items: flex-end; gap: 4px; height: 60px; }
.gen-bar {
  width: 6px; border-radius: 3px 3px 0 0;
  background: linear-gradient(to top, var(--gold), var(--amber));
  animation: wavePulse var(--dur, 1s) ease-in-out infinite alternate;
  animation-delay: var(--delay, 0s); height: var(--h, 20px);
}
@keyframes wavePulse { from{height:4px;opacity:0.3} to{height:var(--h,30px);opacity:1} }
.gen-text { color: var(--gold); font-size: 0.9rem; font-weight: 600; }
.gen-sub  { color: var(--text-muted); font-size: 0.78rem; }
.dots::after { content: '...'; animation: dotAnim 1.5s infinite; }
@keyframes dotAnim { 0%{content:'.'} 33%{content:'..'} 66%{content:'...'} }

.result-section, .history-preview { display: flex; flex-direction: column; }
.tracks-list { display: flex; flex-direction: column; gap: 0.8rem; }
</style>
