<template>
  <div class="track-card card">
    <div class="tc-header">
      <div class="tc-meta">
        <span class="tc-version tag tag-gold">v{{ track.version }}</span>
        <span class="tc-title">{{ track.title }}</span>
        <span v-if="track.submitted" class="tag tag-blue" style="font-size:0.68rem">已提交</span>
      </div>
      <div class="tc-status">
        <span :class="['status-dot', `dot-${track.status}`]"></span>
        <span class="tc-status-text">{{ statusLabel }}</span>
        <span class="tc-time">{{ fmtDate(track.created_at) }}</span>
      </div>
    </div>

    <div class="tc-prompt">
      <span class="label">创作描述：</span>{{ track.prompt }}
      <span v-if="track.style" class="style-tags">
        <span v-for="s in track.style.split(' ')" :key="s" class="tag tag-muted" style="margin-left:4px;font-size:0.68rem">{{ s }}</span>
      </span>
    </div>

    <WavePlayer v-if="track.status === 'done' && track.audio_url" :url="track.audio_url" />
    <div v-else-if="track.status === 'generating'" class="generating-hint">
      <span class="spinner"></span>
      <span>AEGIS 正在创作中……</span>
    </div>

    <!-- 老师评语 -->
    <div v-if="track.feedback" class="tc-feedback">
      <span class="fb-label">👩‍🏫 老师评语</span>
      <p>{{ track.feedback }}</p>
    </div>

    <div class="tc-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup>
import WavePlayer from './WavePlayer.vue'
const props = defineProps({ track: Object })

const statusMap = { pending: '等待中', generating: '生成中', done: '已完成', error: '生成失败' }
const statusLabel = props.track ? statusMap[props.track.status] || props.track.status : ''

function fmtDate(s) {
  if (!s) return ''
  return new Date(s).toLocaleString('zh-CN', { month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit' })
}
</script>

<style scoped>
.track-card { padding: 1rem; display: flex; flex-direction: column; gap: 0.7rem; }
.tc-header  { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.5rem; }
.tc-meta    { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.tc-title   { font-size: 0.92rem; font-weight: 600; color: var(--text-primary); }
.tc-status  { display: flex; align-items: center; gap: 0.4rem; flex-shrink: 0; }
.tc-status-text { font-size: 0.72rem; color: var(--text-muted); }
.tc-time    { font-size: 0.7rem; color: var(--text-muted); }
.tc-prompt  { font-size: 0.82rem; color: var(--text-secondary); line-height: 1.5; }
.label      { color: var(--text-muted); }
.generating-hint { display: flex; align-items: center; gap: 0.6rem; font-size: 0.82rem; color: var(--gold); padding: 0.5rem 0; }
.tc-feedback {
  background: rgba(212,168,67,0.05);
  border-left: 2px solid var(--gold);
  padding: 0.6rem 0.8rem; border-radius: 0 4px 4px 0;
}
.fb-label { font-size: 0.72rem; color: var(--gold); display: block; margin-bottom: 0.3rem; }
.tc-feedback p { font-size: 0.82rem; color: var(--text-secondary); line-height: 1.6; }
.tc-actions { display: flex; gap: 0.5rem; flex-wrap: wrap; }
</style>
