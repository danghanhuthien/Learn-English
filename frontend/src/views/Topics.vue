<script setup>
import { ref,computed } from 'vue'
import { state } from '../api'
import Icon from '../components/Icon.vue'
import TopicCard from '../components/TopicCard.vue'
const search=ref(''),category=ref('Tất cả')
const categories=computed(()=>['Tất cả',...new Set(state.topics.map(t=>t.category))])
const filtered=computed(()=>state.topics.filter(t=>(category.value==='Tất cả'||t.category===category.value)&&`${t.name} ${t.description}`.toLocaleLowerCase('vi').includes(search.value.toLocaleLowerCase('vi'))))
</script>
<template><div class="page"><div class="page-heading"><div><div class="eyebrow">TỪ VỰNG THEO NGỮ CẢNH</div><h1>Thế giới quanh bạn</h1><p>{{state.topics.length}} chủ đề. Những từ bạn cần cho những cuộc trò chuyện thật.</p></div><span class="count-pill">{{state.stats.total_words}} từ & cụm từ</span></div><div class="toolbar"><div class="tabs"><button v-for="item in categories" :key="item" :class="{selected:category===item}" @click="category=item">{{item}}</button></div><label class="search-field"><Icon name="Search" :size="18"/><input v-model="search" placeholder="Tìm chủ đề…" aria-label="Tìm chủ đề"/></label></div><div class="topic-grid all-topics"><TopicCard v-for="topic in filtered" :key="topic.id" :topic="topic"/></div><div v-if="!filtered.length" class="empty-state"><Icon name="SearchX" :size="36"/><h3>Chưa tìm thấy chủ đề</h3><p>Thử tìm bằng một từ khác nhé.</p><button class="btn outline" @click="search='';category='Tất cả'">Xóa bộ lọc</button></div></div></template>
