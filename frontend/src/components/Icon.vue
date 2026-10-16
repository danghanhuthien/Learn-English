<script setup>
import { BookOpen, UserRound, UsersRound, Sun, Headphones, Heart, Utensils, House, ShoppingBag,
  HeartPulse, MapPin, MessagesSquare, CalendarDays, Plane, HandHelping, MessageCircleQuestion,
  BriefcaseBusiness, ContactRound, Presentation, Clock3, Handshake, BadgeCheck, GraduationCap,
  Laptop, CloudSun, Shirt, Dumbbell, Wallet, HeartHandshake, Siren, PartyPopper, ArrowUpRight,
  ArrowRight, Check, Volume2, MessageCircle, LayoutDashboard, Compass, Layers, Target, Sprout,
  Settings, Flame, WifiOff, LoaderCircle, Info, Search, SearchX, Bookmark, Plus, ChevronLeft,
  ChevronRight, X, RotateCw, CircleCheck, ListChecks, Keyboard, Award, CircleX, Database, Download } from '@lucide/vue'
const icons={ BookOpen, UserRound, UsersRound, Sun, Headphones, Heart, Utensils, House, ShoppingBag,
  HeartPulse, MapPin, MessagesSquare, CalendarDays, Plane, HandHelping, MessageCircleQuestion,
  BriefcaseBusiness, ContactRound, Presentation, Clock3, Handshake, BadgeCheck, GraduationCap,
  Laptop, CloudSun, Shirt, Dumbbell, Wallet, HeartHandshake, Siren, PartyPopper, ArrowUpRight,
  ArrowRight, Check, Volume2, MessageCircle, LayoutDashboard, Compass, Layers, Target, Sprout,
  Settings, Flame, WifiOff, LoaderCircle, Info, Search, SearchX, Bookmark, Plus, ChevronLeft,
  ChevronRight, X, RotateCw, CircleCheck, ListChecks, Keyboard, Award, CircleX, Database, Download }
defineProps({name:{type:String,default:'BookOpen'},size:{type:Number,default:20}})
</script>
<template><component :is="icons[name] || icons.BookOpen" :size="size" :stroke-width="1.8" aria-hidden="true" /></template>
