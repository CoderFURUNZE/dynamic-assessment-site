<script setup lang="ts">
import {
  ArrowRight,
  ChatDotRound,
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
  { label: "学习路径", value: "2M+" },
  { label: "课程模块", value: "500+" },
];

const courses = [
  {
    icon: Collection,
    title: "Web 前端开发营",
    meta: "HTML · CSS · JavaScript",
    rating: "4.9",
    lessons: "72 节课",
  },
  {
    icon: Reading,
    title: "UI / UX 设计进阶",
    meta: "研究 · 线框图 · 原型",
    rating: "4.8",
    lessons: "48 节课",
  },
  {
    icon: DataAnalysis,
    title: "Python 数据分析",
    meta: "Pandas · 机器学习 · 可视化",
    rating: "4.9",
    lessons: "64 节课",
  },
  {
    icon: School,
    title: "移动应用开发",
    meta: "Vue · Vite · 产品交付",
    rating: "4.7",
    lessons: "52 节课",
  },
];

const features = [
  {
    icon: Reading,
    title: "按自己的节奏学习",
    desc: "课程、知识点与资源保持同一节奏，进入后直接知道下一步做什么。",
  },
  {
    icon: DataAnalysis,
    title: "集中查看进度",
    desc: "掌握度、阶段反馈和推荐动作集中展示，避免切页找信息。",
  },
  {
    icon: Collection,
    title: "结构化内容",
    desc: "把知识图谱、课程模块和任务列表整理成更清晰的卡片系统。",
  },
  {
    icon: ChatDotRound,
    title: "补足学习信号",
    desc: "通过问卷、画像和阶段记录补足系统自动看不到的学习信号。",
  },
];

const testimonials = [
  {
    name: "林墨",
    role: "前端学习者",
    text: "页面像真正的在线教育产品，重点很聚焦，进入后马上知道该学什么。",
  },
  {
    name: "周安",
    role: "课程导师",
    text: "课程、评价和学生分析终于在一套统一界面里，不再像多个系统拼在一起。",
  },
  {
    name: "顾言",
    role: "项目管理员",
    text: "这种风格更适合 Demo 和答辩展示，既轻松又有产品感。",
  },
];
</script>

<template>
  <div class="edu-landing">
    <header class="edu-landing__nav">
      <div class="landing-brand" @click="router.push('/start')">
        <div class="landing-brand__mark">DA</div>
        <div class="landing-brand__copy">
          <strong>智学平台</strong>
          <span>动态评价学习平台</span>
        </div>
      </div>

      <nav class="landing-links">
        <a href="#courses">课程精选</a>
        <a href="#features">核心优势</a>
        <a href="#reviews">学生反馈</a>
        <a href="#start">开始使用</a>
      </nav>

      <div class="landing-nav__actions">
        <button class="landing-btn landing-btn--ghost" type="button" @click="router.push('/login/student')">学生登录</button>
        <button class="landing-btn landing-btn--primary" type="button" @click="router.push('/login/staff')">教师入口</button>
      </div>
    </header>

    <main class="landing-main">
      <section class="landing-hero">
        <div class="landing-hero__copy">
          <span class="landing-pill landing-pill--green">轻松上手的学习平台</span>
          <h1>
            让学习任务，
            <span>更清晰，</span>
            更好开始
          </h1>
          <p>
            把课程、评价与学习动作整理成更像教育 SaaS 的产品首页。你给的参考风格核心是轻松底色、粗边卡片、明确主 CTA，以及可爱但不幼稚的信息模块。
          </p>

          <div class="landing-hero__actions">
            <button class="landing-btn landing-btn--primary" type="button" @click="router.push('/login/student')">
              立即开始学习
              <el-icon><ArrowRight /></el-icon>
            </button>
            <button class="landing-btn landing-btn--secondary" type="button" @click="router.push('/login/staff')">进入教师 / 管理端</button>
          </div>

          <div class="landing-stats">
            <article v-for="item in stats" :key="item.label" class="landing-stats__item">
              <strong>{{ item.value }}</strong>
              <span>{{ item.label }}</span>
            </article>
          </div>
        </div>

        <div class="landing-hero__visual">
          <div class="hero-board">
            <div class="hero-board__top">
              <div class="hero-board__badge">
                <el-icon><User /></el-icon>
                <div>
                  <strong>Web 前端开发</strong>
                  <span>72 节课</span>
                </div>
              </div>
              <div class="hero-board__rating">
                <el-icon><StarFilled /></el-icon>
                <span>4.9</span>
              </div>
            </div>

            <div class="hero-board__progress">
              <div class="hero-board__progress-head">
                <span>课程进度</span>
                <strong>75%</strong>
              </div>
              <div class="hero-board__track">
                <div class="hero-board__fill"></div>
              </div>
            </div>

            <button class="hero-board__cta" type="button" @click="router.push('/login/student')">继续学习</button>
          </div>

          <span class="hero-float hero-float--pink"></span>
          <span class="hero-float hero-float--green"></span>
          <span class="hero-float hero-float--blue"></span>
        </div>
      </section>

      <section id="courses" class="landing-section">
        <div class="landing-section__head">
          <span class="landing-pill landing-pill--blue">热门课程</span>
          <h2>看看大家最常进入的课程</h2>
          <p>用粗边卡片和低饱和配色做信息分组，这是你给的参考图最强的识别点之一。</p>
        </div>

        <div class="course-grid">
          <article v-for="course in courses" :key="course.title" class="course-card">
            <div class="course-card__icon">
              <el-icon><component :is="course.icon" /></el-icon>
            </div>
            <div class="course-card__body">
              <div class="course-card__top">
                <h3>{{ course.title }}</h3>
                <span>{{ course.rating }}</span>
              </div>
              <p>{{ course.meta }}</p>
              <small>{{ course.lessons }}</small>
            </div>
          </article>
        </div>

        <div class="landing-section__cta">
          <button class="landing-btn landing-btn--secondary" type="button" @click="router.push('/login/student')">查看全部课程</button>
        </div>
      </section>

      <section id="features" class="landing-section landing-section--soft">
        <div class="landing-section__head">
          <span class="landing-pill landing-pill--pink">平台优势</span>
          <h2>把学习所需信息放在同一条路径里</h2>
        </div>

        <div class="feature-grid">
          <article v-for="feature in features" :key="feature.title" class="feature-card">
            <div class="feature-card__icon">
              <el-icon><component :is="feature.icon" /></el-icon>
            </div>
            <h3>{{ feature.title }}</h3>
            <p>{{ feature.desc }}</p>
          </article>
        </div>
      </section>

      <section id="reviews" class="landing-section">
        <div class="landing-section__head">
          <span class="landing-pill landing-pill--green">学生反馈</span>
          <h2>他们为什么更喜欢这套入口</h2>
        </div>

        <div class="review-grid">
          <article v-for="item in testimonials" :key="item.name" class="review-card">
            <div class="review-card__stars">
              <el-icon v-for="idx in 5" :key="idx"><StarFilled /></el-icon>
            </div>
            <p>{{ item.text }}</p>
            <div class="review-card__user">
              <div class="review-card__avatar">{{ item.name.slice(0, 1) }}</div>
              <div>
                <strong>{{ item.name }}</strong>
                <span>{{ item.role }}</span>
              </div>
            </div>
          </article>
        </div>
      </section>

      <section id="start" class="landing-cta">
        <div class="landing-cta__card">
          <h2>准备开始使用了吗？</h2>
          <p>如果你要的是这张图的产品气质，这里就该是一个非常明确、很轻松、很有行动感的 CTA 收口。</p>
          <div class="landing-cta__actions">
            <button class="landing-btn landing-btn--primary" type="button" @click="router.push('/login/student')">进入学生端</button>
            <button class="landing-btn landing-btn--secondary" type="button" @click="router.push('/login/staff')">进入教师 / 管理端</button>
          </div>
        </div>
      </section>
    </main>

    <footer class="landing-footer">
      <div>
        <strong>智学平台</strong>
        <p>一个更接近教育平台 Demo 气质的入口页设计。</p>
      </div>
      <div class="landing-footer__links">
        <a href="#courses">课程精选</a>
        <a href="#features">核心优势</a>
        <a href="#reviews">学生反馈</a>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.edu-landing {
  min-height: 100vh;
  padding: 20px;
  background:
    radial-gradient(circle at top left, rgba(180, 224, 255, 0.3), transparent 22%),
    radial-gradient(circle at bottom right, rgba(178, 232, 220, 0.24), transparent 20%),
    #f9f1e8;
  color: #1d2433;
}

.edu-landing__nav,
.landing-cta__card,
.landing-footer,
.landing-pill,
.course-card,
.feature-card,
.review-card,
.hero-board {
  border: 2px solid #1d2433;
  box-shadow: 6px 6px 0 #1d2433;
}

.edu-landing__nav {
  position: sticky;
  top: 16px;
  z-index: 10;
  max-width: 1180px;
  margin: 0 auto;
  padding: 14px 18px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.landing-brand {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}

.landing-brand__mark {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: #ffe1d3;
  border: 1.5px solid #1d2433;
  font-weight: 800;
}

.landing-brand__copy {
  display: grid;
}

.landing-brand__copy strong {
  font-size: 15px;
}

.landing-brand__copy span {
  font-size: 11px;
  color: #6d7483;
}

.landing-links {
  display: flex;
  align-items: center;
  gap: 20px;
}

.landing-links a,
.landing-footer__links a {
  color: #3d4558;
  text-decoration: none;
  font-size: 13px;
  font-weight: 700;
}

.landing-nav__actions,
.landing-hero__actions,
.landing-cta__actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.landing-btn {
  min-height: 44px;
  padding: 0 18px;
  border-radius: 14px;
  border: 2px solid #1d2433;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.landing-btn:hover {
  transform: translate(-1px, -1px);
}

.landing-btn--primary {
  background: #32d25f;
  color: #10201a;
  box-shadow: 4px 4px 0 #1d2433;
}

.landing-btn--ghost,
.landing-btn--secondary {
  background: #d5efff;
  color: #1d2433;
  box-shadow: 4px 4px 0 #1d2433;
}

.landing-main {
  max-width: 1180px;
  margin: 28px auto 0;
  display: grid;
  gap: 72px;
}

.landing-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 440px);
  gap: 36px;
  align-items: center;
  padding: 24px 0 10px;
}

.landing-pill {
  width: fit-content;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  line-height: 1;
}

.landing-pill--green {
  background: #b9f7b0;
}

.landing-pill--blue {
  background: #c9edff;
}

.landing-pill--pink {
  background: #ffd3c8;
}

.landing-hero__copy h1 {
  margin: 18px 0 14px;
  font-size: clamp(44px, 6vw, 76px);
  line-height: 0.98;
  letter-spacing: -0.05em;
}

.landing-hero__copy h1 span {
  color: #32d25f;
}

.landing-hero__copy p {
  max-width: 58ch;
  margin: 0;
  color: #5f6777;
  font-size: 15px;
  line-height: 1.8;
}

.landing-stats {
  display: flex;
  gap: 26px;
  margin-top: 24px;
  flex-wrap: wrap;
}

.landing-stats__item strong {
  display: block;
  font-size: 20px;
}

.landing-stats__item span {
  font-size: 12px;
  color: #6d7483;
}

.landing-hero__visual {
  position: relative;
  min-height: 340px;
  display: grid;
  place-items: center;
}

.hero-board {
  width: min(100%, 390px);
  padding: 18px;
  border-radius: 24px;
  background: #ffffff;
  transform: rotate(-2deg);
}

.hero-board__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.hero-board__badge {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 16px;
  background: #eef8ff;
  border: 1.5px solid #1d2433;
}

.hero-board__badge strong,
.hero-board__progress-head strong {
  display: block;
}

.hero-board__badge span {
  font-size: 12px;
  color: #6d7483;
}

.hero-board__rating {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 10px 12px;
  border-radius: 14px;
  background: #ffd7e6;
  border: 1.5px solid #1d2433;
  font-weight: 800;
}

.hero-board__progress {
  margin-top: 20px;
}

.hero-board__progress-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  font-size: 13px;
}

.hero-board__track {
  height: 18px;
  border-radius: 999px;
  border: 1.5px solid #1d2433;
  background: #eef2f7;
  overflow: hidden;
}

.hero-board__fill {
  width: 75%;
  height: 100%;
  background: linear-gradient(90deg, #32d25f 0%, #25b750 100%);
}

.hero-board__cta {
  width: 100%;
  min-height: 46px;
  margin-top: 18px;
  border-radius: 14px;
  border: 2px solid #1d2433;
  background: #32d25f;
  font: inherit;
  font-weight: 800;
  box-shadow: 4px 4px 0 #1d2433;
  cursor: pointer;
}

.hero-float {
  position: absolute;
  width: 22px;
  height: 22px;
  border-radius: 8px;
  border: 1.5px solid #1d2433;
  box-shadow: 4px 4px 0 #1d2433;
}

.hero-float--pink {
  right: 16px;
  top: 40px;
  background: #ffb9d4;
}

.hero-float--green {
  right: 4px;
  top: 160px;
  background: #b9f7b0;
  border-radius: 999px;
}

.hero-float--blue {
  left: 20px;
  bottom: 42px;
  background: #c9edff;
}

.landing-section {
  display: grid;
  gap: 26px;
}

.landing-section--soft {
  padding: 48px 0;
}

.landing-section__head {
  text-align: center;
  display: grid;
  justify-items: center;
  gap: 10px;
}

.landing-section__head h2 {
  margin: 0;
  font-size: clamp(28px, 3vw, 40px);
}

.landing-section__head p {
  max-width: 62ch;
  margin: 0;
  color: #6d7483;
  line-height: 1.7;
}

.course-grid,
.feature-grid,
.review-grid {
  display: grid;
  gap: 18px;
}

.course-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.feature-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.review-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.course-card,
.feature-card,
.review-card {
  border-radius: 22px;
  background: #ffffff;
  padding: 18px;
}

.course-card {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 14px;
  align-items: start;
}

.course-card__icon,
.feature-card__icon {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  border: 1.5px solid #1d2433;
}

.course-card__icon {
  background: #ffd8cf;
}

.feature-card:nth-child(1) .feature-card__icon {
  background: #ffd8cf;
}

.feature-card:nth-child(2) .feature-card__icon {
  background: #d6f0ff;
}

.feature-card:nth-child(3) .feature-card__icon {
  background: #ece4ff;
}

.feature-card:nth-child(4) .feature-card__icon {
  background: #c9ffb9;
}

.course-card__top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.course-card__top h3,
.feature-card h3 {
  margin: 0;
  font-size: 18px;
}

.course-card__top span {
  min-width: 48px;
  padding: 4px 8px;
  border-radius: 999px;
  text-align: center;
  background: #b9f7b0;
  border: 1.5px solid #1d2433;
  font-size: 12px;
  font-weight: 800;
}

.course-card p,
.feature-card p,
.review-card p {
  margin: 8px 0 0;
  color: #666f80;
  line-height: 1.7;
  font-size: 14px;
}

.course-card small {
  display: inline-block;
  margin-top: 10px;
  color: #6d7483;
}

.landing-section__cta {
  text-align: center;
}

.feature-card {
  text-align: center;
}

.review-card__stars {
  display: flex;
  gap: 4px;
  color: #ffbf3f;
}

.review-card__user {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 18px;
}

.review-card__avatar {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  background: #ffd8cf;
  border: 1.5px solid #1d2433;
  font-weight: 800;
}

.review-card__user span {
  display: block;
  color: #6d7483;
  font-size: 12px;
}

.landing-cta {
  padding: 24px 0 8px;
}

.landing-cta__card {
  max-width: 760px;
  margin: 0 auto;
  padding: 34px 28px;
  border-radius: 26px;
  text-align: center;
  background: #ffffff;
}

.landing-cta__card h2 {
  margin: 0;
  font-size: 34px;
}

.landing-cta__card p {
  max-width: 58ch;
  margin: 12px auto 0;
  color: #6d7483;
  line-height: 1.7;
}

.landing-cta__actions {
  justify-content: center;
  margin-top: 22px;
}

.landing-footer {
  max-width: 1180px;
  margin: 36px auto 0;
  padding: 22px 24px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.85);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.landing-footer p {
  margin: 6px 0 0;
  color: #6d7483;
  font-size: 14px;
}

.landing-footer__links {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

@media (max-width: 1100px) {
  .landing-hero,
  .course-grid,
  .feature-grid,
  .review-grid {
    grid-template-columns: 1fr;
  }

  .landing-links {
    display: none;
  }
}

@media (max-width: 760px) {
  .edu-landing {
    padding: 14px;
  }

  .edu-landing__nav,
  .landing-footer {
    flex-direction: column;
    align-items: flex-start;
  }

  .landing-main {
    gap: 52px;
  }

  .landing-hero__copy h1 {
    font-size: 48px;
  }

  .landing-stats {
    gap: 16px;
  }

  .course-card {
    grid-template-columns: 1fr;
  }
}
</style>
