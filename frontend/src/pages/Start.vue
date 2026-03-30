<script setup lang="ts">
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
  padding: var(--app-space-4) var(--app-space-6);
  gap: var(--app-space-4);
  border-bottom: 1px solid var(--app-border);
  background: color-mix(in srgb, var(--app-card) 92%, transparent);
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
  border-radius: var(--app-radius-sm);
  background: var(--app-primary-tint);
  color: var(--app-primary-deep);
  font-weight: 700;
  border: 1px solid var(--app-border);
}
.name .title {
  font-size: var(--app-text-md);
  font-weight: 600;
}
.name .sub {
  font-size: var(--app-text-xs);
  color: var(--app-ink-soft);
}

.nav-note {
  color: var(--app-ink-soft);
  font-size: var(--app-text-base);
  text-align: right;
}

.hero {
  position: relative;
  padding: var(--app-space-8) var(--app-space-5) 120px;
  display: grid;
  place-items: center;
  overflow: hidden;
}

.hero-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 80% 50% at 50% -20%, color-mix(in srgb, var(--app-primary) 18%, transparent), transparent 60%),
    radial-gradient(ellipse 60% 40% at 100% 50%, color-mix(in srgb, var(--app-info) 12%, transparent), transparent 55%),
    radial-gradient(ellipse 50% 35% at 0% 80%, color-mix(in srgb, var(--app-success) 10%, transparent), transparent 55%);
  pointer-events: none;
  z-index: 0;
}
.hero-content {
  position: relative;
  z-index: 1;
  max-width: 720px;
  text-align: center;
  padding: var(--app-space-5) var(--app-space-3);
}
.badge {
  display: inline-flex;
  align-items: center;
  gap: var(--app-space-2);
  padding: 6px 14px;
  border-radius: 999px;
  background: var(--app-card);
  color: var(--app-ink-soft);
  font-size: var(--app-text-sm);
  margin-bottom: 18px;
  border: 1px solid var(--app-border);
  box-shadow: var(--app-shadow-soft);
}
h1 {
  font-size: 42px;
  margin: 0 0 14px;
  font-weight: 800;
  line-height: 1.15;
  color: var(--app-ink);
  letter-spacing: -0.02em;
}
p {
  color: var(--app-ink-soft);
  font-size: var(--app-text-md);
  line-height: 1.8;
  margin: 0 0 28px;
}
.hero-actions {
  display: flex;
  justify-content: center;
  gap: var(--app-space-4);
  flex-wrap: wrap;
}
.primary {
  border: 1px solid color-mix(in srgb, var(--app-primary) 35%, var(--app-border-hover));
  background: var(--app-primary);
  color: var(--app-card);
  font-weight: 700;
  padding: 0 28px;
  min-height: 44px;
  border-radius: var(--app-radius-sm);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  box-shadow: 0 4px 14px color-mix(in srgb, var(--app-primary) 35%, transparent);
  transition: transform var(--app-duration) var(--app-ease-out),
    box-shadow var(--app-duration) var(--app-ease-out),
    background var(--app-duration) var(--app-ease-out);
}
.primary:hover {
  background: var(--app-primary-deep);
  transform: translateY(-1px);
  box-shadow: 0 6px 20px color-mix(in srgb, var(--app-primary) 42%, transparent);
}
.secondary {
  border: 1px solid var(--app-border);
  background: var(--app-card);
  color: var(--app-ink);
  padding: 0 var(--app-space-5);
  min-height: 44px;
  border-radius: var(--app-radius-sm);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  transition: border-color var(--app-duration) var(--app-ease-out),
    background var(--app-duration) var(--app-ease-out),
    color var(--app-duration) var(--app-ease-out);
}
.secondary:hover {
  border-color: var(--app-primary);
  color: var(--app-primary);
  background: var(--app-primary-soft);
}
.hint {
  margin-top: 18px;
  font-size: var(--app-text-xs);
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
