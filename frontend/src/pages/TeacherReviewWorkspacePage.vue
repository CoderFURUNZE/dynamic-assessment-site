<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import TeacherEnrollmentReviewPage from "./TeacherEnrollmentReview.vue";
import TeacherFinalScoreReviewPage from "./TeacherFinalScoreReview.vue";
import TeacherIntroHero from "../components/TeacherIntroHero.vue";

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
    <TeacherIntroHero eyebrow="教师工作台" title="审核与评分" :pill="currentTabMeta.label" description="把课程收尾动作放到一个地方处理。先审核报名，再复核最终成绩，避免老师在多个页面之间来回切换。" />

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

.review-focus {
  display: grid;
  gap: 18px;
  padding: 22px 24px;
  border: 3px solid #1f2937;
  border-radius: 32px;
  background:
    radial-gradient(circle at top left, rgba(201, 237, 255, 0.22), transparent 24%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
}

.review-focus > div:first-child {
  display: grid;
  gap: 8px;
}

.review-focus__label {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--app-eyebrow);
}

.review-focus__title {
  margin: 0;
  font-size: 28px;
  line-height: 1.2;
  color: var(--app-ink);
}

.review-focus__desc {
  margin: 0;
  max-width: 760px;
  font-size: 13px;
  line-height: 1.8;
  color: var(--app-ink-soft);
}

.review-focus__actions {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.review-tab-card {
  border: 1.5px solid #c6d8ef;
  border-radius: 22px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  padding: 14px 16px;
  display: grid;
  gap: 4px;
  text-align: left;
  cursor: pointer;
  transition: 0.2s ease;
}

.review-tab-card:hover {
  transform: translateY(-1px);
  border-color: #8fd8c1;
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
  border-color: #1f2937;
  background: radial-gradient(circle at top left, rgba(215, 249, 168, 0.38), transparent 58%), #fffdf6;
  box-shadow: 0 10px 0 rgba(31, 41, 55, 0.08);
}

@media (max-width: 960px) {
  .review-focus__actions {
    grid-template-columns: 1fr;
  }
}
</style>
