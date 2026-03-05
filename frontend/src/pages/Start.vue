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
      <nav class="links">
        <button class="link">数据结构</button>
        <button class="link">计算机组成原理</button>
        <button class="link">操作系统</button>
        <button class="link">计算机网络</button>
        <button class="link ghost">学习资源</button>
        <button class="link ghost">联系我们</button>
      </nav>
      <div class="actions">
        <div class="search">
          <input placeholder="站内搜索" />
        </div>
        <button class="icon-btn">🔍</button>
      </div>
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
          <button class="secondary" @click="router.push('/login')">了解更多</button>
        </div>
        <div class="hint">点击“开始学习”进入登录/注册</div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.start-page {
  min-height: 100vh;
  background: radial-gradient(1200px 500px at 20% 10%, rgba(124, 205, 149, 0.16), transparent),
    radial-gradient(900px 450px at 80% 30%, rgba(94, 138, 213, 0.16), transparent),
    linear-gradient(160deg, var(--app-bg) 0%, var(--app-bg-alt) 40%, #0a0f0d 100%);
  color: var(--app-ink);
}

.start-nav {
  display: grid;
  grid-template-columns: 1.2fr 2.2fr 1.2fr;
  align-items: center;
  padding: 18px 32px;
  gap: 16px;
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
  background: color-mix(in srgb, var(--app-green) 25%, transparent);
  box-shadow: var(--app-shadow);
  font-weight: 700;
  letter-spacing: 0.5px;
}
.name .title {
  font-size: 18px;
  font-weight: 700;
}
.name .sub {
  font-size: 12px;
  color: var(--app-ink-soft);
}

.links {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
}
.link {
  border: none;
  background: transparent;
  color: var(--app-ink);
  font-size: 14px;
  padding: 6px 10px;
  border-radius: 8px;
  cursor: pointer;
}
.link:hover {
  background: color-mix(in srgb, var(--app-green) 15%, transparent);
}
.link.ghost {
  color: var(--app-green-dark);
}

.actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}
.search input {
  width: 160px;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid var(--app-border);
  background: color-mix(in srgb, var(--app-card) 85%, transparent);
  color: var(--app-ink);
  outline: none;
}
.icon-btn {
  border: none;
  background: color-mix(in srgb, var(--app-card) 80%, transparent);
  color: var(--app-ink);
  width: 36px;
  height: 36px;
  border-radius: 10px;
  cursor: pointer;
}

.hero {
  position: relative;
  padding: 80px 24px 120px;
  display: grid;
  place-items: center;
}
.hero-bg {
  position: absolute;
  inset: 80px 10%;
  border-radius: 28px;
  background: linear-gradient(140deg, color-mix(in srgb, var(--app-card) 85%, transparent), transparent);
  filter: blur(2px);
  border: 1px solid var(--app-border);
  box-shadow: var(--app-shadow);
}
.hero-content {
  position: relative;
  max-width: 760px;
  text-align: center;
  padding: 40px 24px;
}
.badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--app-green) 20%, transparent);
  color: var(--app-green-dark);
  font-size: 13px;
  margin-bottom: 18px;
}
h1 {
  font-size: 44px;
  margin: 0 0 14px;
  letter-spacing: 1px;
}
p {
  color: var(--app-ink-soft);
  font-size: 18px;
  line-height: 1.7;
  margin: 0 0 28px;
}
.hero-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
}
.primary {
  border: none;
  background: linear-gradient(135deg, var(--app-green), #5e8ad5);
  color: #fefefe;
  font-weight: 600;
  padding: 10px 26px;
  border-radius: 12px;
  cursor: pointer;
  box-shadow: 0 14px 30px color-mix(in srgb, var(--app-green) 35%, transparent);
}
.secondary {
  border: 1px solid var(--app-border);
  background: color-mix(in srgb, var(--app-card) 75%, transparent);
  color: var(--app-ink);
  padding: 10px 22px;
  border-radius: 12px;
  cursor: pointer;
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
  .actions {
    justify-content: flex-start;
  }
}
@media (max-width: 720px) {
  h1 {
    font-size: 32px;
  }
  .links {
    justify-content: flex-start;
  }
  .search input {
    width: 120px;
  }
}
</style>
