<template>
  <div class="history-page">
    <div class="page-header">
      <h1 class="page-title">我的作品 <span class="cnt">{{ music.tracks.length }}</span></h1>
      <RouterLink to="/studio" class="btn btn-primary">+ 新建作品</RouterLink>
    </div>

    <div v-if="music.tracks.length === 0" class="empty">
      <div class="empty-icon">🎵</div>
      <p>还没有作品，去作曲工坊创作第一首吧</p>
    </div>

    <!-- 版本树视图 -->
    <div v-else class="version-tree">
      <div v-for="group in versionGroups" :key="group.rootId" class="track-group">
        <div class="group-header" @click="group.expanded = !group.expanded">
          <span class="g-arrow">{{ group.expanded ? '▼' : '▶' }}</span>
          <span class="g-title">{{ group.tracks[0].title.replace(/ v\d+.*/, '') }}</span>
          <span class="tag tag-muted">{{ group.tracks.length }} 个版本</span>
          <span v-if="group.tracks.some(t => t.feedback)" class="tag tag-gold" style="font-size:0.68rem">有老师评语</span>
        </div>
        <div v-if="group.expanded" class="group-tracks">
          <div v-for="(t, idx) in group.tracks" :key="t.id" class="version-item">
            <div class="version-line" v-if="idx < group.tracks.length - 1"></div>
            <TrackCard :track="t">
              <template #actions>
                <RouterLink to="/studio" class="btn btn-ghost" style="font-size:0.78rem"
                  @click="setBase(t)">🔄 在此基础上修改</RouterLink>
                <button v-if="!t.submitted && t.status === 'done'"
                  class="btn btn-outline" style="font-size:0.78rem" @click="submit(t)">📤 提交</button>
              </template>
            </TrackCard>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, inject, onMounted } from 'vue'
import TrackCard from '../components/TrackCard.vue'
import { useMusicStore } from '../stores/music.js'
import { useRouter } from 'vue-router'

const music  = useMusicStore()
const router = useRouter()
const toast  = inject('toast')

const versionGroups = computed(() => {
  const tracks = [...music.tracks].sort((a, b) => a.id - b.id)
  const map = new Map()
  tracks.forEach(t => {
    const root = findRoot(t, tracks)
    if (!map.has(root)) map.set(root, reactive({ rootId: root, expanded: true, tracks: [] }))
    map.get(root).tracks.push(t)
  })
  return [...map.values()].reverse()
})

function findRoot(t, all) {
  let cur = t
  while (cur.parent_id) { cur = all.find(x => x.id === cur.parent_id) || cur; break }
  return cur.id
}

async function submit(t) {
  await music.submitTrack(t.id)
  toast('已提交给老师', 'success')
}

function setBase(t) {
  sessionStorage.setItem('remix_base', JSON.stringify(t))
  router.push('/studio')
}

onMounted(() => music.fetchMyTracks())
</script>

<style scoped>
.history-page { padding: 1.5rem; max-width: 900px; margin: 0 auto; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem; }
.page-title  { font-size: 1.2rem; font-weight: 700; color: var(--text-primary); }
.cnt { font-size: 0.85rem; color: var(--text-muted); font-weight: 400; margin-left: 0.4rem; }

.version-tree { display: flex; flex-direction: column; gap: 1rem; }
.track-group { border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }
.group-header {
  display: flex; align-items: center; gap: 0.6rem;
  padding: 0.7rem 1rem; cursor: pointer;
  background: rgba(10,22,40,0.6);
  transition: background 0.15s;
}
.group-header:hover { background: rgba(212,168,67,0.05); }
.g-arrow { color: var(--text-muted); font-size: 0.7rem; }
.g-title { font-size: 0.9rem; font-weight: 600; color: var(--text-primary); flex: 1; }
.group-tracks { padding: 0.8rem; display: flex; flex-direction: column; gap: 0.6rem; }
.version-item { position: relative; }
.version-line {
  position: absolute; left: 1.2rem; bottom: -0.6rem; width: 1px; height: 0.6rem;
  background: var(--border);
}
</style>
