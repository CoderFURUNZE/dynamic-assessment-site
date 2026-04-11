<script setup lang="ts">
import { useRouter } from "vue-router";

const router = useRouter();

const cards = [
  { title: "知识图谱", value: "清晰组织课程结构" },
  { title: "阶段评价", value: "持续反馈学习进度" },
  { title: "学习建议", value: "推荐下一步内容" },
];
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
      <div class="hero-grid">
        <section class="hero-main">
          <div class="badge">大学计算机 · 自适应学习</div>
          <h1>计算机课程自适应学习系统</h1>
          <p class="hero-lead">整合知识点、题库与学习资源，帮助你更直接地进入课程学习。</p>

          <div class="hero-actions">
            <button class="primary" @click="router.push('/login')">开始学习</button>
          </div>

          <div class="hint">首次使用时，先登录，再进入对应课程。</div>

          <div class="metrics">
            <article v-for="item in cards" :key="item.title" class="metric-card">
              <strong>{{ item.title }}</strong>
              <span>{{ item.value }}</span>
            </article>
          </div>
        </section>

        <aside class="hero-panel">
          <div class="panel-card">
            <div class="panel-eyebrow">平台特色</div>
            <div class="panel-title">把课程结构、学习反馈和下一步建议放到同一入口。</div>
            <div class="panel-text">页面保持简洁，信息只保留学习决策真正需要的部分。</div>
          </div>
        </aside>
      </div>
    </main>
  </div>
</template>

<style scoped>
.start-page {
  min-height: 100vh;
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--app-bg) 94%, white) 0%, var(--app-bg) 58%, color-mix(in srgb, var(--app-info) 5%, var(--app-bg)) 100%);
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
  backdrop-filter: blur(10px);
}

.brand {
  display: flex;
  align-items: center;
  gap: 14px;
}

.logo {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border-radius: 16px;
  background: linear-gradient(135deg, color-mix(in srgb, var(--app-primary) 18%, white), color-mix(in srgb, var(--app-primary) 6%, white));
  color: var(--app-primary-deep);
  font-weight: 800;
  font-size: 22px;
  border: 1px solid color-mix(in srgb, var(--app-primary) 22%, var(--app-border));
  box-shadow: var(--app-shadow-soft);
}

.name .title {
  font-size: var(--app-text-md);
  font-weight: 700;
}

.name .sub {
  font-size: var(--app-text-xs);
  color: var(--app-ink-soft);
}

.nav-note {
  color: var(--app-ink-soft);
  font-size: var(--app-text-sm);
  text-align: right;
}

.hero {
  position: relative;
  padding: 56px var(--app-space-6) 72px;
  overflow: hidden;
}

.hero-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 20% 80%, color-mix(in srgb, var(--app-info) 16%, transparent), transparent 30%),
    radial-gradient(circle at 76% 18%, color-mix(in srgb, var(--app-primary) 14%, transparent), transparent 26%);
  pointer-events: none;
}

.hero-grid {
  position: relative;
  z-index: 1;
  max-width: 1180px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(280px, 0.7fr);
  gap: 28px;
  align-items: center;
}

.hero-main {
  padding: 12px 0;
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 8px 16px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--app-card) 94%, white);
  color: var(--app-ink-soft);
  font-size: var(--app-text-sm);
  margin-bottom: 18px;
  border: 1px solid var(--app-border);
  box-shadow: var(--app-shadow-soft);
}

h1 {
  margin: 0 0 16px;
  font-size: clamp(34px, 4.5vw, 56px);
  line-height: 1.08;
  font-weight: 900;
  letter-spacing: -0.035em;
  color: var(--app-ink);
  max-width: 760px;
}

.hero-lead {
  max-width: 700px;
  color: color-mix(in srgb, var(--app-ink-soft) 94%, var(--app-ink));
  font-size: clamp(17px, 1.6vw, 20px);
  line-height: 1.8;
  margin: 0 0 24px;
}

.hero-actions {
  display: flex;
  justify-content: flex-start;
}

.primary {
  min-width: 152px;
  min-height: 48px;
  padding: 0 28px;
  border-radius: 16px;
  border: 1px solid color-mix(in srgb, var(--app-primary) 34%, var(--app-border-hover));
  background: linear-gradient(135deg, var(--app-primary), color-mix(in srgb, var(--app-primary) 72%, #7fb3ff));
  color: var(--app-card);
  font-weight: 800;
  font-size: var(--app-text-base);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 10px 26px color-mix(in srgb, var(--app-primary) 24%, transparent);
  transition:
    transform var(--app-duration) var(--app-ease-out),
    box-shadow var(--app-duration) var(--app-ease-out);
}

.primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 30px color-mix(in srgb, var(--app-primary) 28%, transparent);
}

.hint {
  margin-top: 14px;
  font-size: var(--app-text-sm);
  color: var(--app-ink-soft);
}

.metrics {
  margin-top: 28px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.metric-card {
  padding: 18px;
  border-radius: 18px;
  background: color-mix(in srgb, var(--app-card) 94%, white);
  border: 1px solid color-mix(in srgb, var(--app-border) 88%, white);
  box-shadow: var(--app-shadow-soft);
}

.metric-card strong {
  display: block;
  margin-bottom: 6px;
  font-size: var(--app-text-base);
  color: var(--app-ink);
}

.metric-card span {
  display: block;
  font-size: var(--app-text-sm);
  line-height: 1.7;
  color: var(--app-ink-soft);
}

.hero-panel {
  display: flex;
  justify-content: flex-end;
}

.panel-card {
  width: min(100%, 360px);
  padding: 24px;
  border-radius: 26px;
  background: color-mix(in srgb, var(--app-card) 94%, white);
  border: 1px solid color-mix(in srgb, var(--app-primary) 12%, var(--app-border));
  box-shadow: 0 16px 40px color-mix(in srgb, var(--app-info) 8%, transparent);
}

.panel-eyebrow {
  font-size: var(--app-text-xs);
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--app-primary);
  margin-bottom: 12px;
}

.panel-title {
  font-size: clamp(22px, 2vw, 30px);
  line-height: 1.5;
  font-weight: 800;
  color: var(--app-ink);
}

.panel-text {
  margin-top: 14px;
  font-size: var(--app-text-sm);
  line-height: 1.8;
  color: var(--app-ink-soft);
}

@media (max-width: 1100px) {
  .start-nav {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .hero-grid {
    grid-template-columns: 1fr;
  }

  .hero-panel {
    justify-content: flex-start;
  }
}

@media (max-width: 760px) {
  .hero {
    padding: 44px var(--app-space-4) 64px;
  }

  .hero-actions {
    justify-content: center;
  }

  .metrics {
    grid-template-columns: 1fr;
  }

  .nav-note {
    text-align: left;
  }
}
</style>
