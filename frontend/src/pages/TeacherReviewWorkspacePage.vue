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

    <component
      :is="currentComponent"
      :key="`${currentTab}-${String(route.query.subject || '')}-${String(route.query.user_id || '')}`"
    />
  </div>
</template>

<style scoped>
.review-workspace {
  display: grid;
  gap: 18px;
}

.review-focus {
  display: grid;
  gap: 16px;
  padding: 20px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 20px;
  background:
    radial-gradient(circle at top left, rgba(239, 220, 179, 0.22), transparent 26%),
    radial-gradient(circle at top right, rgba(191, 221, 254, 0.18), transparent 24%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: 0 12px 26px rgba(15, 23, 42, 0.07);
}

.review-focus > div:first-child {
  display: grid;
  gap: 8px;
}

.review-focus__label {
  display: inline-flex;
  width: fit-content;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  background: linear-gradient(180deg, #eef6dc 0%, #fff2db 100%);
  color: #586537;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.review-focus__title {
  margin: 0;
  font-size: 28px;
  line-height: 1.2;
  color: #1f2937;
}

.review-focus__desc {
  margin: 0;
  max-width: 760px;
  font-size: 14px;
  line-height: 1.8;
  color: #6a7280;
}

.review-focus__actions {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.review-tab-card {
  border: 1px solid rgba(191, 167, 132, 0.24);
  border-radius: 22px;
  background: linear-gradient(180deg, rgba(255, 252, 247, 0.96), rgba(255, 244, 229, 0.92));
  padding: 14px 16px;
  display: grid;
  gap: 4px;
  text-align: left;
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.review-tab-card:hover {
  transform: translateY(-1px);
  border-color: rgba(34, 197, 94, 0.22);
}

.review-tab-card strong {
  font-size: 15px;
  color: #1f2937;
}

.review-tab-card span {
  font-size: 13px;
  line-height: 1.7;
  color: #6a7280;
}

.review-tab-card.active {
  border-color: rgba(34, 197, 94, 0.28);
  background:
    radial-gradient(circle at top right, rgba(215, 249, 168, 0.22), transparent 28%),
    linear-gradient(180deg, #ffffff 0%, #eef8ff 100%);
  box-shadow: 0 16px 28px rgba(15, 23, 42, 0.08);
}

@media (max-width: 960px) {
  .review-focus__actions {
    grid-template-columns: 1fr;
  }
}
</style>
