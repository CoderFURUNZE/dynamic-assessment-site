<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import TeacherAnalyticsPage from "./TeacherAnalyticsPage.vue";
import TeacherBehaviorReportPage from "./TeacherBehaviorReportPage.vue";
import TeacherStudentsPage from "./TeacherStudentsPage.vue";
import TeacherProfilesPage from "./TeacherProfilesPage.vue";

type StudentsTab = "class" | "detail" | "behavior" | "results";

const route = useRoute();

const currentTab = computed<StudentsTab>(() => {
  const raw = String(route.query.tab || "class");
  if (raw === "detail" || raw === "behavior" || raw === "results") return raw;
  return "class";
});

const currentComponent = computed(() => {
  if (currentTab.value === "detail") return TeacherStudentsPage;
  if (currentTab.value === "behavior") return TeacherBehaviorReportPage;
  if (currentTab.value === "results") return TeacherProfilesPage;
  return TeacherAnalyticsPage;
});
</script>

<template>
  <div class="teacher-students-workspace">
    <component
      :is="currentComponent"
      :key="`${currentTab}-${String(route.query.subject || '')}-${String(route.query.user_id || '')}`"
    />
  </div>
</template>

<style scoped>
.teacher-students-workspace {
  display: grid;
}
</style>
