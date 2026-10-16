import { reactive } from 'vue'
export const state = reactive({ me: null, stats: null, topics: [], ready: false, error: '', toast: '' })
let toastTimer
export function notify(message) { state.toast = message; clearTimeout(toastTimer); toastTimer = setTimeout(() => state.toast = '', 3500) }
export async function api(path, options = {}) {
  let response
  try {
    response = await fetch(`/api${path}`, {credentials:'same-origin', ...options, headers:{'Content-Type':'application/json', ...options.headers}})
  } catch { throw new Error('Không kết nối được máy chủ. Kiểm tra backend rồi thử lại.') }
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Dữ liệu chưa hợp lệ. Vui lòng kiểm tra lại.')
  return data
}
export async function refresh() {
  const [stats,topics] = await Promise.all([api('/stats'), api('/topics')])
  state.stats=stats; state.topics=topics
}
export async function initialize() {
  state.error=''
  try { state.me=await api('/me'); await refresh(); state.ready=true }
  catch (e) { state.error=e.message }
}
export function speak(text,rate=.85) {
  if (!('speechSynthesis' in window)) { notify('Trình duyệt này chưa hỗ trợ đọc phát âm.'); return }
  const utterance=new SpeechSynthesisUtterance(text)
  utterance.lang='en-US'; utterance.rate=rate
  const voices=window.speechSynthesis.getVoices()
  utterance.voice=voices.find(v=>v.lang==='en-US') || voices.find(v=>v.lang.startsWith('en')) || null
  utterance.onerror=(event)=>{if(!['canceled','interrupted'].includes(event.error))notify('Không đọc được phát âm. Hãy kiểm tra giọng tiếng Anh trên thiết bị.')}
  window.speechSynthesis.cancel(); window.speechSynthesis.speak(utterance)
}
