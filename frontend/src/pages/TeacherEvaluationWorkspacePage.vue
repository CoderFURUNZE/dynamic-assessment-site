<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import TeacherStagesPage from "./TeacherStagesPage.vue";
import TeacherIndicatorsPage from "./TeacherIndicatorsPage.vue";
import TeacherImportsPage from "./TeacherImportsPage.vue";
import TeacherBehaviorReportPage from "./TeacherBehaviorReportPage.vue";

type EvaluationTab = "stages" | "indicators" | "imports" | "behavior";

const route = useRoute();

const currentTab = computed<EvaluationTab>(() => {
  const raw = String(route.query.tab || "stages");
  if (raw === "indicators" || raw === "imports" || raw === "behavior") return raw;
  return "stages";
});

const currentComponent = computed(() => {
  if (currentTab.value === "indicators") return TeacherIndicatorsPage;
  if (currentTab.value === "imports") return TeacherImportsPage;
  if (currentTab.value === "behavior") return TeacherBehaviorReportPage;
  return TeacherStagesPage;
});
</script>

<template>
  <div class="teacher-evaluation-workspace">
    <component
      :is="currentComponent"
      :key="`${currentTab}-${String(route.query.subject || '')}-${String(route.query.stage_id || '')}`"
    />
  </div>
</template>

<style scoped>
.teacher-evaluation-workspace {
  display: grid;
}
</style>
