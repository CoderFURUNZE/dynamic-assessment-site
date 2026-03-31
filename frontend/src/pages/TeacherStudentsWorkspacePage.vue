<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import TeacherAnalyticsPage from "./TeacherAnalyticsPage.vue";
import TeacherStudentsPage from "./TeacherStudentsPage.vue";
import TeacherProfilesPage from "./TeacherProfilesPage.vue";

type StudentsTab = "class" | "detail" | "rules";

const route = useRoute();
const router = useRouter();

const tabs: Array<{ key: StudentsTab; label: string; desc: string }> = [
  { key: "class", label: "班级总览", desc: "先看整体，再看个体" },
  { key: "detail", label: "学生详情", desc: "查看单个学生的阶段变化" },
  { key: "rules", label: "规则参考", desc: "理解画像结果的配置依据" },
];

const currentTab = computed<StudentsTab>(() => {
  const raw = String(route.query.tab || "class");
  if (raw === "detail" || raw === "rules") return raw;
  return "class";
});

const currentComponent = computed(() => {
  if (currentTab.value === "detail") return TeacherStudentsPage;
  if (currentTab.value === "rules") return TeacherProfilesPage;
  return TeacherAnalyticsPage;
});

const currentTaskText = computed(() => {
  if (currentTab.value === "class") return "先看班级整体情况";
  if (currentTab.value === "detail") return "定位具体学生并看阶段变化";
  return "对照规则理解画像结果";
});

function switchTab(tab: StudentsTab) {
  router.replace({
    path: "/teacher/students",
    query: {
      ...route.query,
      tab,
    },
  });
}
</script>

<template>
  <div class="workspace-hub">
    <section class="workspace-hub__hero workspace-hub__hero--three">
      <div>
        <span class="workspace-hub__eyebrow">学生分析</span>
        <h1>先看班级，再看个人，最后回到规则解释结果</h1>
        <p>这个页面负责串起班级总览、学生详情和规则参考，避免在多个分析页之间来回切换。</p>
      </div>
      <article class="workspace-hub__focus-card">
        <span>当前最重要的事</span>
        <strong>{{ currentTaskText }}</strong>
        <p>{{ tabs.find((item) => item.key === currentTab)?.desc }}</p>
      </article>
    </section>

    <section class="workspace-hub__tabs workspace-hub__tabs--three">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="workspace-hub__tab"
        :class="{ active: currentTab === tab.key }"
        @click="switchTab(tab.key)"
      >
        <strong>{{ tab.label }}</strong>
        <span>{{ tab.desc }}</span>
      </button>
    </section>

    <component :is="currentComponent" />
  </div>
</template>

<style scoped>
.workspace-hub {
  display: grid;
  gap: 18px;
}

.workspace-hub__hero {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(280px, 0.8fr);
  gap: 16px;
  padding: 24px 26px;
  border-radius: 24px;
  border: 1px solid #e3ebf5;
  background: linear-gradient(135deg, #ffffff 0%, #f4f8ff 100%);
  box-shadow: 0 18px 38px rgba(15, 23, 42, 0.05);
}

.workspace-hub__eyebrow,
.workspace-hub__focus-card span {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--app-primary-deep);
}

.workspace-hub__hero h1,
.workspace-hub__focus-card strong {
  margin: 8px 0 0;
  font-size: 28px;
  color: var(--app-text-main);
}

.workspace-hub__hero p,
.workspace-hub__focus-card p {
  margin: 10px 0 0;
  line-height: 1.7;
  color: var(--app-text-soft);
}

.workspace-hub__focus-card {
  display: grid;
  gap: 8px;
  padding: 18px 20px;
  border-radius: 18px;
  border: 1px solid #dbe7f6;
  background: linear-gradient(145deg, #fdfefe 0%, #eef6ff 100%);
}

.workspace-hub__tabs {
  display: grid;
  gap: 12px;
}

.workspace-hub__tabs--three {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.workspace-hub__tab {
  display: grid;
  gap: 6px;
  padding: 14px 16px;
  text-align: left;
  border-radius: 18px;
  border: 1px solid #dfe7f1;
  background: #fff;
  cursor: pointer;
}

.workspace-hub__tab strong {
  font-size: 15px;
  color: var(--app-text-main);
}

.workspace-hub__tab span {
  font-size: 12px;
  color: var(--app-text-soft);
}

.workspace-hub__tab.active {
  border-color: color-mix(in srgb, var(--app-primary) 35%, var(--app-border));
  background: var(--app-primary-tint);
}

@media (max-width: 1100px) {
  .workspace-hub__hero,
  .workspace-hub__tabs--three {
    grid-template-columns: 1fr;
  }
}
</style>
