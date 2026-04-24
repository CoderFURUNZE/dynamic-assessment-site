<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
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
</script>

<template>
  <div class="review-workspace">

    <component
      :is="currentComponent"
      :key="`${currentTab}-${String(route.query.subject || '')}-${String(route.query.user_id || '')}`"
    />
  </div>
</template>

<style scoped>
.review-workspace {
  display: grid;
  gap: 0;
}

:global(.student-shell--teacher:has(.review-workspace)) {
  max-width: 1540px;
}

</style>
