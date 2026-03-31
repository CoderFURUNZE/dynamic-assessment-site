<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import TeacherEnrollmentReviewPage from "./TeacherEnrollmentReview.vue";
import TeacherFinalScoreReviewPage from "./TeacherFinalScoreReview.vue";

type ReviewTab = "enrollment" | "final";

type ReviewTabItem = {
  key: ReviewTab;
  label: string;
  desc: string;
  summary: string;
};

const route = useRoute();
const router = useRouter();

const tabs: ReviewTabItem[] = [
  {
    key: "enrollment",
    label: "报名审核",
    desc: "处理学生申请、查看状态、确认是否加入课程。",
    summary: "适合先处理还没入班的学生。",
  },
  {
    key: "final",
    label: "最终评分",
    desc: "核对阶段结果、确认最终成绩，完成课程收口。",
    summary: "适合课程末尾统一复核。",
  },
];

const currentTab = computed<ReviewTab>(() => (String(route.query.tab || "enrollment") === "final" ? "final" : "enrollment"));

const currentComponent = computed(() => (currentTab.value === "final" ? TeacherFinalScoreReviewPage : TeacherEnrollmentReviewPage));

const currentTabMeta = computed(() => tabs.find((item) => item.key === currentTab.value) ?? tabs[0]);

function switchTab(tab: ReviewTab) {
  router.replace({
    path: "/teacher/review",
    query: {
      ...route.query,
      tab,
    },
  });
}
</script>

<template>
  <div class="review-workspace">
    <section class="review-hero panel-card">
      <div class="review-hero__copy">
        <div class="review-hero__eyebrow">Teacher Review</div>
        <h1 class="review-hero__title">审核与评分</h1>
        <p class="review-hero__desc">
          把课程收尾动作放到一个地方处理。先审核报名，再复核最终成绩，避免老师在多个页面之间来回切换。
        </p>
      </div>
      <div class="review-hero__cards">
        <article class="review-kpi">
          <span>当前模块</span>
          <strong>{{ currentTabMeta.label }}</strong>
          <small>{{ currentTabMeta.summary }}</small>
        </article>
        <article class="review-kpi">
          <span>处理顺序</span>
          <strong>先审核，再评分</strong>
          <small>先确认学生进入课程，再做课程末尾复核。</small>
        </article>
      </div>
    </section>

    <section class="review-focus panel-card">
      <div>
        <div class="review-focus__label">当前最重要的事</div>
        <h2 class="review-focus__title">{{ currentTabMeta.label }}</h2>
        <p class="review-focus__desc">{{ currentTabMeta.desc }}</p>
      </div>
      <div class="review-focus__actions">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="review-tab-card"
          :class="{ active: currentTab === tab.key }"
          @click="switchTab(tab.key)"
        >
          <strong>{{ tab.label }}</strong>
          <span>{{ tab.desc }}</span>
        </button>
      </div>
    </section>

    <component :is="currentComponent" />
  </div>
</template>

<style scoped>
.review-workspace {
  display: grid;
  gap: 18px;
}

.review-hero,
.review-focus {
  display: grid;
  gap: 18px;
  padding: 22px 24px;
}

.review-hero__copy,
.review-focus > div:first-child {
  display: grid;
  gap: 8px;
}

.review-hero__eyebrow,
.review-focus__label {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--app-eyebrow);
}

.review-hero__title,
.review-focus__title {
  margin: 0;
  font-size: 28px;
  line-height: 1.2;
  color: var(--app-ink);
}

.review-hero__desc,
.review-focus__desc {
  margin: 0;
  max-width: 760px;
  font-size: 13px;
  line-height: 1.8;
  color: var(--app-ink-soft);
}

.review-hero__cards {
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.review-kpi {
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid var(--app-border);
  background: linear-gradient(180deg, #fbfdff 0%, #f5f9ff 100%);
  display: grid;
  gap: 6px;
}

.review-kpi span {
  font-size: 12px;
  color: #66809a;
}

.review-kpi strong {
  font-size: 22px;
  font-weight: 800;
  color: var(--app-ink);
}

.review-kpi small {
  font-size: 12px;
  line-height: 1.6;
  color: var(--app-ink-soft);
}

.review-focus__actions {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.review-tab-card {
  border: 1px solid var(--app-border);
  border-radius: 16px;
  background: #fff;
  padding: 14px 16px;
  display: grid;
  gap: 4px;
  text-align: left;
  cursor: pointer;
  transition: 0.2s ease;
}

.review-tab-card:hover {
  transform: translateY(-1px);
  border-color: color-mix(in srgb, var(--app-primary) 28%, var(--app-border));
}

.review-tab-card strong {
  font-size: 15px;
  color: var(--app-ink);
}

.review-tab-card span {
  font-size: 12px;
  line-height: 1.7;
  color: var(--app-ink-soft);
}

.review-tab-card.active {
  border-color: color-mix(in srgb, var(--app-primary) 38%, var(--app-border));
  background: var(--app-primary-tint);
  box-shadow: 0 18px 40px rgba(47, 109, 246, 0.12);
}

@media (max-width: 960px) {
  .review-hero__cards,
  .review-focus__actions {
    grid-template-columns: 1fr;
  }
}
</style>
