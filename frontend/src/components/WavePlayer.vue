<template>
  <div class="wave-player">
    <div class="wave-wrap" ref="waveRef"></div>
    <div class="player-controls">
      <button class="play-btn" @click="togglePlay" :disabled="!ready">
        <span v-if="!playing">▶</span>
        <span v-else>⏸</span>
      </button>
      <div class="time-info">
        <span class="time-cur">{{ fmtTime(currentTime) }}</span>
        <span class="time-sep">/</span>
        <span class="time-dur">{{ fmtTime(duration) }}</span>
      </div>
      <div class="vol-wrap">
        <span>🔊</span>
        <input type="range" min="0" max="1" step="0.05" v-model.number="volume" @input="setVol" class="vol-slider" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import WaveSurfer from 'wavesurfer.js'

const props = defineProps({ url: String })
const waveRef    = ref(null)
const playing    = ref(false)
const ready      = ref(false)
const currentTime = ref(0)
const duration    = ref(0)
const volume      = ref(0.8)
let ws = null

function build() {
  if (ws) { ws.destroy(); ws = null }
  if (!props.url) return
  ready.value = false; playing.value = false
  ws = WaveSurfer.create({
    container: waveRef.value,
    waveColor: 'rgba(212,168,67,0.35)',
    progressColor: '#D4A843',
    cursorColor: '#F0C85A',
    height: 56,
    barWidth: 2,
    barGap: 1,
    barRadius: 2,
    normalize: true,
    url: props.url,
  })
  ws.on('ready', d => { ready.value = true; duration.value = d })
  ws.on('timeupdate', t => { currentTime.value = t })
  ws.on('finish', () => { playing.value = false })
  ws.setVolume(volume.value)
}

function togglePlay() { if (!ws) return; ws.playPause(); playing.value = ws.isPlaying() }
function setVol()      { ws?.setVolume(volume.value) }
function fmtTime(s)    { const m = Math.floor(s/60); return `${m}:${String(Math.floor(s%60)).padStart(2,'0')}` }

watch(() => props.url, build)
onMounted(build)
onBeforeUnmount(() => ws?.destroy())
</script>

<style scoped>
.wave-player {
  background: rgba(6,15,30,0.8);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 0.8rem 1rem;
}
.wave-wrap { margin-bottom: 0.6rem; min-height: 56px; }
.player-controls { display: flex; align-items: center; gap: 0.8rem; }
.play-btn {
  width: 34px; height: 34px; border-radius: 50%;
  background: linear-gradient(135deg, var(--gold), var(--amber));
  border: none; cursor: pointer; color: #020810; font-size: 0.85rem;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; transition: transform 0.15s;
}
.play-btn:hover:not(:disabled) { transform: scale(1.08); }
.play-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.time-info { font-size: 0.75rem; color: var(--text-muted); font-variant-numeric: tabular-nums; }
.time-cur { color: var(--gold); }
.time-sep { margin: 0 0.2rem; }
.vol-wrap { display: flex; align-items: center; gap: 0.4rem; margin-left: auto; font-size: 0.85rem; }
.vol-slider { width: 70px; accent-color: var(--gold); }
</style>
