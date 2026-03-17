﻿<script setup lang="ts">
import { useRouter } from "vue-router";

const router = useRouter();
</script>

<template>
  <div class="start-page">
    <header class="start-nav">
      <div class="brand">
        <div class="logo">CS</div>
        <div class="name">
          <div class="title">计算机课程学习平台</div>
          <div class="sub">知识图谱 · 动态评价 · 个性化路径</div>
        </div>
      </div>
      <div class="nav-note">打开后先登录，再选择课程开始学习。</div>
    </header>

    <main class="hero">
      <div class="hero-bg" />
      <div class="hero-content">
        <div class="badge">大学计算机 · 自适应学习</div>
        <h1>计算机课程自适应学习系统</h1>
        <p>
          汇集知识点、题库与学习资源，结合学习行为与状态信号，
          为你提供更贴合的学习路径与练习推荐。
        </p>
        <div class="hero-actions">
          <button class="primary" @click="router.push('/login')">开始学习</button>
          <button class="secondary" @click="router.push('/login')">进入系统</button>
        </div>
        <div class="hint">第一次使用时，先用老师或学生账号登录。</div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.start-page {
  min-height: 100vh;
  background: var(--app-bg);
  color: var(--app-ink);
}

.start-nav {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  padding: 18px 32px;
  gap: 16px;
  border-bottom: 1px solid var(--app-border);
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(8px);
}

.brand {
  display: flex;
  align-items: center;
  gap: 14px;
}
.logo {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: #f4f7fb;
  color: var(--app-ink);
  font-weight: 700;
}
.name .title {
  font-size: 16px;
  font-weight: 600;
}
.name .sub {
  font-size: 12px;
  color: var(--app-ink-soft);
}

.nav-note {
  color: var(--app-ink-soft);
  font-size: 14px;
  text-align: right;
}

.hero {
  padding: 96px 24px 120px;
  display: grid;
  place-items: center;
}
.hero-content {
  max-width: 720px;
  text-align: center;
  padding: 24px 12px;
}
.badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 999px;
  background: #ffffff;
  color: var(--app-ink-soft);
  font-size: 13px;
  margin-bottom: 18px;
  border: 1px solid var(--app-border);
}
h1 {
  font-size: 42px;
  margin: 0 0 14px;
  font-weight: 800;
  line-height: 1.15;
}
p {
  color: var(--app-ink-soft);
  font-size: 16px;
  line-height: 1.8;
  margin: 0 0 28px;
}
.hero-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
}
.primary {
  border: 1px solid #c9d9ec;
  background: #2f6fed;
  color: #fff;
  font-weight: 700;
  padding: 0 28px;
  min-height: 42px;
  border-radius: 12px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}
.secondary {
  border: 1px solid var(--app-border);
  background: #fafbfd;
  color: var(--app-ink);
  padding: 0 24px;
  min-height: 42px;
  border-radius: 12px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}
.hint {
  margin-top: 18px;
  font-size: 12px;
  color: var(--app-ink-soft);
}

@media (max-width: 1100px) {
  .start-nav {
    grid-template-columns: 1fr;
    gap: 12px;
  }
}
@media (max-width: 720px) {
  h1 {
    font-size: 30px;
  }
  .nav-note {
    text-align: left;
  }
}
</style>
