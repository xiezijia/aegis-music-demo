import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'

export const useMusicStore = defineStore('music', () => {
  const tracks  = ref([])
  const loading = ref(false)

  async function fetchMyTracks() {
    const { data } = await axios.get('/api/music/my-tracks')
    tracks.value = data
  }

  async function generate(payload) {
    const { data } = await axios.post('/api/music/generate', payload)
    return data  // { track_id, status }
  }

  async function pollStatus(trackId) {
    for (let i = 0; i < 60; i++) {
      await new Promise(r => setTimeout(r, 3000))
      const { data } = await axios.get(`/api/music/status/${trackId}`)
      if (data.status === 'done') return data
      if (data.status === 'error') throw new Error('生成失败')
    }
    throw new Error('生成超时')
  }

  async function submitTrack(trackId) {
    await axios.post(`/api/music/submit/${trackId}`)
    await fetchMyTracks()
  }

  return { tracks, loading, fetchMyTracks, generate, pollStatus, submitTrack }
})
