import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Dashboard from './views/Dashboard.vue'
import Topics from './views/Topics.vue'
import Library from './views/Library.vue'
import Study from './views/Study.vue'
import Practice from './views/Practice.vue'
import Settings from './views/Settings.vue'
import Sentences from './views/Sentences.vue'
import SentenceStudy from './views/SentenceStudy.vue'
import './style.css'
const router = createRouter({ history: createWebHistory(), scrollBehavior:(_to,_from,saved)=>saved || {top:0}, routes: [
  {path:'/', component:Dashboard}, {path:'/topics',component:Topics},
  {path:'/words',component:Library}, {path:'/study',component:Study},
  {path:'/practice',component:Practice}, {path:'/settings',component:Settings},
  {path:'/sentences',component:Sentences}, {path:'/sentences/learn',component:SentenceStudy},
  {path:'/:pathMatch(.*)*',redirect:'/'},
]})
createApp(App).use(router).mount('#app')
