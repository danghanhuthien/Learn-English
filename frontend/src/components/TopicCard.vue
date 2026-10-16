<script setup>
import Icon from './Icon.vue'
defineProps({topic:Object})
</script>
<template>
  <RouterLink :to="`/words?topic=${topic.id}`" class="topic-card" :style="{'--topic-color':topic.color}">
    <div class="topic-card-top"><span class="topic-icon"><Icon :name="topic.icon" :size="24"/></span><span class="level">{{ topic.level }}</span></div>
    <h3>{{ topic.name }}</h3><p>{{ topic.description }}</p>
    <div class="topic-card-meta"><span>{{ topic.word_count }} từ & cụm từ</span><Icon name="ArrowUpRight" :size="18"/></div>
    <div class="progress-track"><span :style="{width:`${topic.word_count ? topic.learned_count/topic.word_count*100 : 0}%`}"></span></div>
    <small>{{ topic.learned_count }}/{{ topic.word_count }} đã học</small>
  </RouterLink>
</template>
