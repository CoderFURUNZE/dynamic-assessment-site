<script setup lang="ts">
import {
  ArrowRight,
  Collection,
  DataAnalysis,
  Reading,
  School,
  StarFilled,
  User,
} from "@element-plus/icons-vue";
import { useRouter } from "vue-router";

const router = useRouter();

const stats = [
  { label: "活跃学习者", value: "10K+" },
  { label: "学习记录", value: "2M+" },
  { label: "知识图谱节点", value: "500+" },
];

const courses = [
  {
    title: "Web 前端开发训练营",
    lessons: "18 节课程",
    rating: "4.9",
    icon: Reading,
  },
  {
    title: "UI / UX 设计实践课",
    lessons: "24 节课程",
    rating: "4.8",
    icon: Collection,
  },
  {
    title: "Python 数据分析基础",
    lessons: "16 节课程",
    rating: "4.9",
    icon: DataAnalysis,
  },
  {
    title: "移动应用开发工作坊",
    lessons: "21 节课程",
    rating: "4.7",
    icon: School,
  },
];

const features = [
  {
    title: "学习路径更清晰",
    desc: "课程、任务、图谱和反馈集中展示，减少切换成本。",
    icon: Reading,
    tone: "peach",
  },
  {
    title: "阶段反馈更及时",
    desc: "把学习行为和评价结果串起来，方便持续跟踪。",
    icon: DataAnalysis,
    tone: "blue",
  },
  {
    title: "成果展示更完整",
    desc: "不仅看课程进度，也能看到知识点掌握和成长变化。",
    icon: Collection,
    tone: "lavender",
  },
  {
    title: "师生协同更顺畅",
    desc: "学生关注学习，教师关注分析与干预，信息分层更明确。",
    icon: User,
    tone: "green",
  },
];

const testimonials = [
  {
    quote: "课程结构和反馈放在一起后，学生的成长路径更容易讲清楚。",
    name: "林老师",
    role: "课程设计教师",
  },
  {
    quote: "这版首页更像成熟产品，不再像临时拼接出来的演示页。",
    name: "吴同学",
    role: "答辩展示者",
  },
  {
    quote: "从知识图谱到动态评价的表达更顺了，系统价值更好理解。",
    name: "陈导师",
    role: "教学指导教师",
  },
];
</script>

<template>
  <div class="start-page">
    <header class="start-nav">
      <button type="button" class="start-brand" aria-label="返回首页" @click="router.push('/start')">
        <span class="start-brand__logo">学</span>
        <span class="start-brand__copy">
          <strong>学研空间</strong>
          <small>学习画像与知识图谱平台</small>
        </span>
      </button>

      <nav class="start-nav__links" aria-label="页面导航">
        <a href="#courses">精选课程</a>
        <a href="#features">核心能力</a>
        <a href="#reviews">用户反馈</a>
        <a href="#start">开始使用</a>
      </nav>

      <button type="button" class="start-btn start-btn--primary start-btn--compact" @click="router.push('/login/staff')">
        教师入口
      </button>
    </header>

    <main class="start-main">
      <section class="hero-section">
        <div class="hero-copy">
          <span class="hero-copy__eyebrow">学习平台 / 动态评价</span>
          <h1>
            让学习过程
            <span>更清晰</span>
            也更好展示
          </h1>
          

          <div class="hero-actions">
            <button type="button" class="start-btn start-btn--primary" @click="router.push('/login/student')">
              进入学生端
              <el-icon><ArrowRight /></el-icon>
            </button>
            <button type="button" class="start-btn start-btn--secondary" @click="router.push('/login/staff')">
              查看教师端
            </button>
          </div>

          <div class="hero-stats">
            <article v-for="item in stats" :key="item.label" class="hero-stat">
              <strong>{{ item.value }}</strong>
              <span>{{ item.label }}</span>
            </article>
          </div>
        </div>

        <aside class="hero-visual">
          <div class="hero-dashboard">
            <div class="hero-dashboard__badge hero-dashboard__badge--top">
              <span class="hero-dashboard__badge-icon">★</span>
              <span>推荐学习路径</span>
            </div>

            <div class="hero-dashboard__window">
              <div class="hero-dashboard__window-head">
                <div class="hero-dashboard__avatar">学</div>
                <div>
                  <strong>前端开发课程</strong>
                  <small>已完成 42 个学习任务</small>
                </div>
              </div>

              <div class="hero-dashboard__metrics">
                <div>
                  <span>当前进度</span>
                  <strong>85%</strong>
                </div>
                <div>
                  <span>课程评分</span>
                  <strong>4.9</strong>
                </div>
              </div>

              <div class="hero-dashboard__progress">
                <span class="hero-dashboard__progress-fill" />
              </div>

              <button type="button" class="hero-dashboard__cta" @click="router.push('/login/student')">
                继续学习
              </button>
            </div>
          </div>
        </aside>
      </section>

      <section id="courses" class="content-section">
        <div class="section-heading section-heading--with-action">
          <div>
            <span class="section-heading__eyebrow section-heading__eyebrow--blue">课程推荐</span>
            <h2>探索热门课程</h2>
            <p>用清晰的课程卡片展示课程方向、数量和评分，便于快速浏览。</p>
          </div>
          <button type="button" class="start-btn start-btn--secondary" @click="router.push('/login/student')">
            查看全部课程
          </button>
        </div>

        <div class="course-grid">
          <article v-for="item in courses" :key="item.title" class="course-card">
            <div class="course-card__icon">
              <el-icon><component :is="item.icon" /></el-icon>
            </div>
            <div class="course-card__content">
              <h3>{{ item.title }}</h3>
              <p>{{ item.lessons }}</p>
            </div>
            <div class="course-card__rating">
              <el-icon><StarFilled /></el-icon>
              <span>{{ item.rating }}</span>
            </div>
          </article>
        </div>
      </section>

      <section id="features" class="content-section content-section--soft">
        <div class="section-heading">
          <span class="section-heading__eyebrow section-heading__eyebrow--pink">平台特点</span>
          <h2>把学习平台该有的体验做完整</h2>
          <p>统一卡片、按钮和信息层级后，学生端、教师端和管理端会更像同一套产品。</p>
        </div>

        <div class="feature-grid">
          <article v-for="item in features" :key="item.title" class="feature-card" :data-tone="item.tone">
            <div class="feature-card__icon">
              <el-icon><component :is="item.icon" /></el-icon>
            </div>
            <h3>{{ item.title }}</h3>
            <p>{{ item.desc }}</p>
          </article>
        </div>
      </section>

      <section id="reviews" class="content-section">
        <div class="section-heading">
          <span class="section-heading__eyebrow">用户反馈</span>
          <h2>他们如何评价这套界面</h2>
        </div>

        <div class="testimonial-grid">
          <article v-for="item in testimonials" :key="item.name" class="testimonial-card">
            <div class="testimonial-card__stars">
              <el-icon v-for="star in 5" :key="star"><StarFilled /></el-icon>
            </div>
            <p>{{ item.quote }}</p>
            <div class="testimonial-card__author">
              <span class="testimonial-card__avatar">{{ item.name.slice(0, 1) }}</span>
              <div>
                <strong>{{ item.name }}</strong>
                <small>{{ item.role }}</small>
              </div>
            </div>
          </article>
        </div>
      </section>
    </main>

    <footer class="start-footer">
      <div class="start-footer__brand">
        <span class="start-brand__logo">学</span>
        <div>
          <strong>学研空间</strong>
          <p>适用于学习平台展示、课程系统演示和教育产品原型表达。</p>
        </div>
      </div>

      <div class="start-footer__links">
        <a href="#courses">课程</a>
        <a href="#features">能力</a>
        <a href="#reviews">反馈</a>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.start-page {
  min-height: 100vh;
  padding: 22px 20px 36px;
  background:
    radial-gradient(circle at top left, rgba(191, 221, 254, 0.36), transparent 19%),
    radial-gradient(circle at 88% 9%, rgba(254, 226, 226, 0.34), transparent 14%),
    linear-gradient(180deg, #f8fafc 0%, #f8fafc 48%, #f5f7fb 100%);
  color: #0f172a;
}

.start-nav,
.hero-section,
.content-section,
.start-footer {
  width: 100%;
  max-width: 1180px;
  margin: 0 auto;
}

.start-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 14px 16px 14px 18px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
  backdrop-filter: blur(14px);
}

.start-brand {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  border: 0;
  padding: 0;
  background: transparent;
  cursor: pointer;
  text-align: left;
  font: inherit;
  color: inherit;
}

.start-brand__logo {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  background: linear-gradient(180deg, #fee2e2 0%, #fecdd3 100%);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.06);
  font-weight: 800;
}

.start-brand__copy {
  display: grid;
  gap: 2px;
}

.start-brand__copy strong {
  font-size: 15px;
  line-height: 1;
}

.start-brand__copy small {
  color: #64748b;
  font-size: 11px;
}

.start-nav__links,
.hero-actions,
.start-footer__links {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.start-nav__links a,
.start-footer__links a {
  color: #475569;
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
}

.start-main {
  display: grid;
  gap: 42px;
  padding-top: 26px;
}

.hero-section {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: center;
  gap: 42px;
  width: 100%;
  padding: 30px 16px 18px;
}

.hero-copy,
.hero-visual,
.section-heading,
.feature-card,
.testimonial-card,
.start-footer__brand {
  display: grid;
  gap: 14px;
}

.hero-copy__eyebrow,
.section-heading__eyebrow {
  display: inline-flex;
  width: fit-content;
  align-items: center;
  min-height: 30px;
  padding: 0 14px;
  border: 1px solid rgba(34, 197, 94, 0.18);
  border-radius: 999px;
  background: #eefbf3;
  color: #166534;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
}

.section-heading__eyebrow--blue {
  background: #eef6ff;
  border-color: rgba(59, 130, 246, 0.18);
  color: #1d4ed8;
}

.section-heading__eyebrow--pink {
  background: #fdf2f8;
  border-color: rgba(244, 114, 182, 0.18);
  color: #be185d;
}

.hero-copy h1,
.section-heading h2 {
  margin: 0;
  color: #0f172a;
  line-height: 1.13;
  letter-spacing: -0.035em;
}

.hero-copy h1 {
  max-width: 100%;
  font-size: clamp(48px, 6.2vw, 76px);
}

.hero-copy h1 span {
  color: #22c55e;
}

.hero-copy .hero-actions {
  margin-top: 8px;
}

.hero-copy p,
.section-heading p,
.feature-card p,
.testimonial-card p,
.start-footer__brand p {
  margin: 0;
  color: #64748b;
  font-size: 15px;
  line-height: 1.75;
}

.hero-stats {
  display: flex;
  gap: 28px;
  flex-wrap: wrap;
  padding-top: 6px;
}

.hero-stat {
  display: grid;
  gap: 4px;
}

.hero-stat strong {
  font-size: 24px;
  line-height: 1;
}

.hero-stat span {
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
}

.hero-dashboard {
  position: relative;
  min-height: 360px;
  width: 100%;
  display: grid;
  place-items: center;
}

.hero-dashboard__window {
  width: 100%;
  padding: 22px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 22px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.08);
}

.hero-dashboard__window-head,
.hero-dashboard__metrics,
.course-card,
.testimonial-card__author,
.start-footer {
  display: flex;
}

.hero-dashboard__window-head,
.hero-dashboard__metrics,
.testimonial-card__author,
.start-footer {
  align-items: center;
  justify-content: space-between;
}

.hero-dashboard__window-head {
  gap: 14px;
}

.hero-dashboard__avatar,
.testimonial-card__avatar {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 16px;
  background: linear-gradient(180deg, #dbeafe 0%, #bfdbfe 100%);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.06);
  font-weight: 800;
}

.hero-dashboard__window-head strong,
.hero-dashboard__metrics strong,
.course-card h3,
.feature-card h3,
.testimonial-card strong,
.start-footer__brand strong {
  font-size: 20px;
  line-height: 1.15;
}

.hero-dashboard__window-head small,
.hero-dashboard__metrics span,
.course-card p,
.testimonial-card small {
  color: #64748b;
  font-size: 13px;
}

.hero-dashboard__metrics {
  margin-top: 20px;
  gap: 16px;
}

.hero-dashboard__metrics > div {
  flex: 1;
  display: grid;
  gap: 4px;
}

.hero-dashboard__progress {
  margin-top: 18px;
  height: 12px;
  padding: 2px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 999px;
  background: #eff6ff;
  overflow: hidden;
}

.hero-dashboard__progress-fill {
  display: block;
  width: 85%;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #22c55e 0%, #16a34a 100%);
}

.hero-dashboard__cta {
  width: 100%;
  margin-top: 16px;
  min-height: 42px;
  border: 1px solid rgba(34, 197, 94, 0.22);
  border-radius: 14px;
  background: linear-gradient(180deg, #22c55e 0%, #16a34a 100%);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
  color: #ffffff;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.hero-dashboard__badge {
  position: absolute;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-width: 46px;
  min-height: 40px;
  padding: 0 14px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 14px;
  box-shadow: 0 10px 20px rgba(15, 23, 42, 0.06);
  font-size: 13px;
  font-weight: 700;
}

.hero-dashboard__badge--top {
  top: 0;
  left: 8px;
  background: #eef6ff;
  color: #1d4ed8;
}

.hero-dashboard__badge-icon {
  color: #f59e0b;
}

.content-section {
  display: grid;
  gap: 26px;
  padding: 38px 34px 34px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 28px;
  background:
    radial-gradient(circle at top right, rgba(191, 219, 254, 0.14), transparent 28%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.84) 0%, rgba(248, 250, 252, 0.96) 100%);
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.04);
}

.content-section--soft {
  background:
    radial-gradient(circle at top right, rgba(244, 114, 182, 0.08), transparent 26%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.86) 0%, rgba(248, 250, 252, 0.96) 100%);
}

.section-heading--with-action {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.section-heading--with-action > div {
  display: grid;
  gap: 14px;
  min-width: 0;
}

.section-heading--with-action .start-btn {
  flex: 0 0 auto;
  margin-top: 6px;
}

.course-grid,
.feature-grid,
.testimonial-grid {
  display: grid;
  gap: 18px;
}

.course-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.course-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 18px 20px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 18px;
  background: #ffffff;
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.05);
}

.course-card__icon,
.feature-card__icon {
  width: 50px;
  height: 50px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 16px;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.05);
  font-size: 20px;
}

.course-card__icon {
  background: linear-gradient(180deg, #fee2e2 0%, #fecaca 100%);
}

.course-card__content {
  flex: 1;
  display: grid;
  gap: 4px;
  min-width: 0;
}

.course-card__rating {
  display: inline-flex;
  align-items: center;
  flex: 0 0 auto;
  gap: 6px;
  padding: 8px 12px;
  border: 1px solid rgba(34, 197, 94, 0.18);
  border-radius: 999px;
  background: #eefbf3;
  color: #166534;
  font-weight: 700;
}

.course-card__rating :deep(.el-icon),
.testimonial-card__stars :deep(.el-icon) {
  color: #f59e0b;
}

.feature-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.feature-card {
  padding: 24px 20px;
  border-radius: 20px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  background: #ffffff;
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.05);
}

.feature-card[data-tone="peach"] .feature-card__icon {
  background: linear-gradient(180deg, #ffedd5 0%, #fed7aa 100%);
}

.feature-card[data-tone="blue"] .feature-card__icon {
  background: linear-gradient(180deg, #e0f2fe 0%, #bae6fd 100%);
}

.feature-card[data-tone="lavender"] .feature-card__icon {
  background: linear-gradient(180deg, #ede9fe 0%, #ddd6fe 100%);
}

.feature-card[data-tone="green"] .feature-card__icon {
  background: linear-gradient(180deg, #dcfce7 0%, #bbf7d0 100%);
}

.testimonial-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  width: 100%;
}

.testimonial-card {
  padding: 24px 20px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 20px;
  background: #ffffff;
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.05);
}

.testimonial-card__stars {
  display: inline-flex;
  gap: 4px;
}


.start-footer {
  padding: 42px 0 12px;
  gap: 24px;
  border-top: 1px solid rgba(148, 163, 184, 0.16);
}

.start-footer__brand {
  grid-auto-flow: column;
  align-items: start;
  justify-content: start;
  gap: 14px;
}

.start-btn {
  min-height: 42px;
  padding: 0 18px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 14px;
  background: #ffffff;
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.05);
  color: #334155;
  cursor: pointer;
  font: inherit;
  font-weight: 700;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.start-btn--compact {
  min-height: 40px;
  padding: 0 16px;
}

.start-btn--primary {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  background: linear-gradient(180deg, #22c55e 0%, #16a34a 100%);
  border-color: rgba(34, 197, 94, 0.24);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
  color: #ffffff;
}

.start-btn--secondary {
  background: #ffffff;
}

.start-btn:hover,
.hero-dashboard__cta:hover {
  transform: translateY(-1px);
}

.start-btn:focus-visible,
.hero-dashboard__cta:focus-visible,
.start-brand:focus-visible,
.start-nav__links a:focus-visible,
.start-footer__links a:focus-visible {
  outline: 3px solid rgba(34, 197, 94, 0.18);
  outline-offset: 4px;
}

@media (max-width: 1080px) {
  .hero-section,
  .feature-grid,
  .testimonial-grid,
  .course-grid {
    grid-template-columns: 1fr;
  }

  .feature-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .course-grid,
  .testimonial-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .start-page {
    padding: 16px 14px 28px;
  }

  .start-nav,
  .start-footer,
  .hero-section {
    grid-template-columns: 1fr;
  }

  .start-nav,
  .start-footer,
  .hero-section,
  .course-grid,
  .feature-grid,
  .testimonial-grid {
    display: grid;
  }

  .start-nav {
    justify-items: start;
  }

  .hero-section,
  .content-section {
    padding-left: 18px;
    padding-right: 18px;
  }

  .hero-copy h1 {
    font-size: clamp(40px, 13vw, 56px);
    max-width: 8.5ch;
  }

  .hero-stats,
  .hero-actions {
    gap: 12px;
  }

  .hero-actions,
  .start-nav__links,
  .start-footer__links {
    flex-direction: column;
    align-items: stretch;
  }

  .section-heading--with-action {
    display: grid;
  }

  .section-heading--with-action .start-btn {
    width: fit-content;
    margin-top: 0;
  }

  .course-grid,
  .feature-grid,
  .testimonial-grid {
    grid-template-columns: 1fr;
  }

  .course-card {
    align-items: flex-start;
  }

  .course-card__rating {
    margin-left: auto;
  }

  .hero-dashboard__badge--top {
    position: static;
  }
}
</style>
