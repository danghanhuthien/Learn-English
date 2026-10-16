<script setup>
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { state, initialize } from './api'
import Icon from './components/Icon.vue'
const route=useRoute()
const nav=[['/','LayoutDashboard','Tổng quan'],['/topics','Compass','Khám phá chủ đề'],['/words','BookOpen','Kho từ vựng'],['/sentences','MessagesSquare','900 câu giao tiếp'],['/study','Layers','Học & ôn tập'],['/practice','Target','Luyện tập']]
onMounted(initialize)
</script>
<template>
  <div class="app-shell">
    <aside class="sidebar">
      <RouterLink to="/" class="brand"><span class="brand-mark">L<span></span></span><span>lingua<span class="brand-dot">.</span></span></RouterLink>
      <div class="sidebar-caption">MỖI NGÀY, MỘT CHÚT TIẾN BỘ</div>
      <nav aria-label="Điều hướng chính"><RouterLink v-for="[path,icon,label] in nav" :key="path" :to="path" :class="{active:path==='/sentences' ? route.path.startsWith(path) : route.path===path}"><Icon :name="icon"/><span>{{label}}</span><span v-if="path==='/study' && state.stats?.due" class="nav-badge">{{state.stats.due}}</span></RouterLink></nav>
      <div class="sidebar-tip"><span class="tip-icon"><Icon name="Sprout" :size="25"/></span><h4>Nhỏ thôi, nhưng đều đặn.</h4><p>15 phút hôm nay là một bước gần hơn đến cuộc trò chuyện tiếp theo.</p><RouterLink to="/study">Học một chút nhé <Icon name="ArrowRight" :size="16"/></RouterLink></div>
      <div class="sidebar-bottom"><RouterLink to="/settings" :class="{active:route.path==='/settings'}"><Icon name="Settings"/><span>Cài đặt</span></RouterLink><div class="profile"><span class="avatar">{{state.me?.name?.charAt(0).toUpperCase() || 'B'}}</span><div><strong>{{state.me?.name==='Bạn' ? 'Người học tiếng Anh' : state.me?.name || 'Đang kết nối…'}}</strong><small>Hành trình của bạn</small></div></div></div>
    </aside>
    <div class="main-shell">
      <header class="topbar"><span class="topbar-tag"><span class="status-dot"></span> TIẾNG ANH CHO CUỘC SỐNG</span><div class="topbar-right"><span class="streak-chip"><Icon name="Flame" :size="17"/> {{state.stats?.learning_streak ?? state.stats?.streak ?? 0}} ngày liên tiếp</span><RouterLink to="/settings" class="avatar small" aria-label="Hồ sơ của bạn">{{state.me?.name?.charAt(0).toUpperCase() || 'B'}}</RouterLink></div></header>
      <main v-if="state.ready"><RouterView/></main>
      <main v-else class="connection-state"><Icon :name="state.error ? 'WifiOff' : 'LoaderCircle'" :size="36"/><h2>{{state.error ? 'Chưa kết nối được' : 'Chuẩn bị hành trình của bạn…'}}</h2><p v-if="state.error" role="alert">{{state.error}}</p><button v-if="state.error" class="btn primary" @click="initialize">Thử lại</button></main>
      <footer>Học để nói. Nói để kết nối.<span>Lingua · Một chút mỗi ngày</span></footer>
    </div>
    <div v-if="state.toast" class="toast" role="status"><Icon name="Info" :size="18"/>{{state.toast}}</div>
  </div>
</template>
