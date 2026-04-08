<template>
  <div class="teacher-page">
    <!-- 左：学生列表 -->
    <aside class="t-left">
      <div class="panel-title">🎓 学生列表</div>
      <div class="student-list">
        <div v-for="s in students" :key="s.id"
          :class="['student-item', { active: selected?.id === s.id }]"
          @click="selectStudent(s)">
          <span class="s-avatar">{{ s.display_name[0] }}</span>
          <div class="s-info">
            <span class="s-name">{{ s.display_name }}</span>
            <span class="s-stat">{{ s.submitted_count || 0 }} 件已提交 / {{ s.track_count || 0 }} 件总计</span>
          </div>
          <span v-if="s.submitted_count > 0" class="s-badge">{{ s.submitted_count }}</span>
        </div>
      </div>
    </aside>

    <!-- 中：提交作品列表 -->
    <main class="t-main">
      <div v-if="!selected" class="empty" style="margin-top:4rem">
        <div class="empty-icon">👈</div>
        <p>从左侧选择一个学生查看作品</p>
      </div>

      <template v-else>
        <div class="t-main-header">
          <h2 class="student-name-title">{{ selected.display_name }} 的作品</h2>
          <div class="header-tags">
            <span class="tag tag-blue">共 {{ studentTracks.length }} 个版本</span>
            <span class="tag tag-gold">{{ studentTracks.filter(t=>t.submitted).length }} 件已提交</span>
          </div>
        </div>

        <div v-if="studentTracks.length === 0" class="empty">
          <div class="empty-icon">🎵</div>
          <p>该学生还没有创作记录</p>
        </div>

        <div class="tracks-list">
          <div v-for="t in studentTracks" :key="t.id" class="track-with-fb">
            <TrackCard :track="t" />
            <!-- 评语区 -->
            <div class="feedback-area card">
              <div v-if="t.feedback" class="existing-feedback">
                <span class="fb-label">已有评语</span>
                <p class="fb-text">{{ t.feedback }}</p>
              </div>
              <div class="fb-input-area">
                <textarea class="input" v-model="fbInputs[t.id]" rows="2"
                  :placeholder="t.feedback ? '追加新评语…' : '写下评语（支持直接打分）…'"></textarea>
                <div class="fb-actions">
                  <input type="number" class="input score-input" v-model.number="scoreInputs[t.id]"
                    placeholder="分数" min="0" max="100" />
                  <button class="btn btn-primary" style="font-size:0.8rem"
                    :disabled="!fbInputs[t.id]"
                    @click="sendFeedback(t.id)">✓ 发送评语</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </main>

    <!-- 右：统计 -->
    <aside class="t-right">
      <div class="panel-title">📊 班级概况</div>
      <div class="stats-grid">
        <div class="stat-card card">
          <div class="stat-num">{{ students.length }}</div>
          <div class="stat-label">总学生数</div>
        </div>
        <div class="stat-card card">
          <div class="stat-num">{{ totalSubmitted }}</div>
          <div class="stat-label">待批改</div>
        </div>
        <div class="stat-card card">
          <div class="stat-num">{{ totalTracks }}</div>
          <div class="stat-label">总创作数</div>
        </div>
        <div class="stat-card card">
          <div class="stat-num">{{ feedbackGiven }}</div>
          <div class="stat-label">已批改</div>
        </div>
      </div>

      <div class="panel-title" style="margin-top:1.5rem">⚡ 所有提交</div>
      <div class="all-subs">
        <div v-for="t in allSubmissions.slice(0,8)" :key="t.id" class="sub-item"
          @click="quickSelect(t)">
          <span class="si-name">{{ t.display_name }}</span>
          <span class="si-title">{{ t.title }}</span>
          <span v-if="!t.feedback" class="tag tag-gold" style="font-size:0.65rem">待批</span>
          <span v-else class="tag tag-green" style="font-size:0.65rem">已批</span>
        </div>
      </div>
    </aside>
  </div>
</template>

<script setup>
import { ref, reactive, computed, inject, onMounted } from 'vue'
import axios from 'axios'
import TrackCard from '../components/TrackCard.vue'

const toast = inject('toast')
const students      = ref([])
const selected      = ref(null)
const studentTracks = ref([])
const allSubmissions = ref([])
const fbInputs  = reactive({})
const scoreInputs = reactive({})

const totalSubmitted = computed(() => students.value.reduce((s, x) => s + (x.submitted_count || 0), 0))
const totalTracks    = computed(() => students.value.reduce((s, x) => s + (x.track_count || 0), 0))
const feedbackGiven  = computed(() => allSubmissions.value.filter(t => t.feedback).length)

async function loadStudents() {
  const { data } = await axios.get('/api/teacher/students')
  students.value = data
}
async function loadSubmissions() {
  const { data } = await axios.get('/api/teacher/submissions')
  allSubmissions.value = data
}
async function selectStudent(s) {
  selected.value = s
  const { data } = await axios.get(`/api/teacher/student/${s.id}/tracks`)
  studentTracks.value = data
}
function quickSelect(t) {
  const s = students.value.find(x => x.display_name === t.display_name)
  if (s) selectStudent(s)
}
async function sendFeedback(trackId) {
  await axios.post('/api/teacher/feedback', {
    track_id: trackId,
    comment: fbInputs[trackId],
    score: scoreInputs[trackId] || null
  })
  toast('评语已发送', 'success')
  fbInputs[trackId] = ''
  scoreInputs[trackId] = null
  if (selected.value) await selectStudent(selected.value)
  await loadSubmissions()
}

onMounted(() => { loadStudents(); loadSubmissions() })
</script>

<style scoped>
.teacher-page { display: flex; height: 100%; }

.t-left {
  width: 200px; flex-shrink: 0;
  border-right: 1px solid var(--border);
  padding: 1.2rem 0.8rem; overflow-y: auto;
  background: rgba(6,15,30,0.4);
}
.t-main  { flex: 1; padding: 1.2rem; overflow-y: auto; }
.t-right { width: 220px; flex-shrink: 0; border-left: 1px solid var(--border); padding: 1.2rem 0.8rem; overflow-y: auto; }

.panel-title {
  font-size: 0.72rem; font-weight: 700; color: var(--gold);
  letter-spacing: 0.1em; margin-bottom: 0.8rem;
}

.student-list { display: flex; flex-direction: column; gap: 0.3rem; }
.student-item {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.5rem 0.6rem; border-radius: 5px; cursor: pointer;
  transition: background 0.15s;
}
.student-item:hover { background: var(--gold-dim); }
.student-item.active { background: var(--gold-dim); border: 1px solid var(--border-bright); }
.s-avatar {
  width: 28px; height: 28px; border-radius: 50%; flex-shrink: 0;
  background: linear-gradient(135deg, var(--gold), var(--amber));
  color: #020810; font-size: 0.75rem; font-weight: 800;
  display: flex; align-items: center; justify-content: center;
}
.s-info { flex: 1; min-width: 0; }
.s-name { font-size: 0.82rem; color: var(--text-primary); display: block; }
.s-stat { font-size: 0.65rem; color: var(--text-muted); }
.s-badge {
  background: var(--amber); color: #020810;
  font-size: 0.65rem; font-weight: 700; padding: 0.1rem 0.35rem;
  border-radius: 10px; flex-shrink: 0;
}

.t-main-header { display: flex; align-items: center; gap: 0.8rem; margin-bottom: 1.2rem; }
.student-name-title { font-size: 1rem; font-weight: 700; }
.header-tags { display: flex; gap: 0.4rem; }

.tracks-list { display: flex; flex-direction: column; gap: 1rem; }
.track-with-fb { display: flex; flex-direction: column; gap: 0.4rem; }
.feedback-area { padding: 0.8rem; }
.existing-feedback { margin-bottom: 0.6rem; }
.fb-label { font-size: 0.68rem; color: var(--gold); display: block; margin-bottom: 0.3rem; }
.fb-text { font-size: 0.8rem; color: var(--text-secondary); line-height: 1.6; }
.fb-input-area { display: flex; flex-direction: column; gap: 0.5rem; }
.fb-actions { display: flex; gap: 0.5rem; align-items: center; }
.score-input { width: 80px; flex-shrink: 0; padding: 0.5rem; text-align: center; }

.stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; }
.stat-card { padding: 0.7rem 0.5rem; text-align: center; }
.stat-num { font-size: 1.4rem; font-weight: 900; color: var(--gold); }
.stat-label { font-size: 0.65rem; color: var(--text-muted); }

.all-subs { display: flex; flex-direction: column; gap: 0.3rem; }
.sub-item {
  display: flex; align-items: center; gap: 0.4rem;
  padding: 0.4rem 0.5rem; border-radius: 4px; cursor: pointer;
  transition: background 0.15s; font-size: 0.75rem;
}
.sub-item:hover { background: var(--gold-dim); }
.si-name { color: var(--gold); flex-shrink: 0; min-width: 40px; }
.si-title { color: var(--text-muted); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
