<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import TeacherStagesPage from "./TeacherStagesPage.vue";
import TeacherIndicatorsPage from "./TeacherIndicatorsPage.vue";
import TeacherImportsPage from "./TeacherImportsPage.vue";
import TeacherBehaviorReportPage from "./TeacherBehaviorReportPage.vue";

type EvaluationTab = "stages" | "indicators" | "imports" | "behavior";

const route = useRoute();
const router = useRouter();

const tabs: Array<{ key: EvaluationTab; label: string; desc: string }> = [
  { key: "stages", label: "阶段设置", desc: "维护课程阶段与时间窗口" },
  { key: "indicators", label: "指标配置", desc: "配置画像和评价指标" },
  { key: "imports", label: "数据导入", desc: "导入系统汇总与教师补录" },
  { key: "behavior", label: "结果查看", desc: "查看行为与阶段结果" },
];

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

function switchTab(tab: EvaluationTab) {
  router.replace({
    path: "/teacher/evaluation",
    query: {
      ...route.query,
      tab,
    },
  });
}
</script>

<template>
  <div class="workspace-hub">
    <section class="workspace-hub__hero">
      <div>
        <span class="workspace-hub__eyebrow">教师评价工作台</span>
        <h1>阶段评价工作台</h1>
        <p>把阶段设置、指标配置、数据导入和结果查看统一放在一条工作链路里，老师可以按阶段自然推进，不再在多个零散页面之间来回跳转。</p>
      </div>
    </section>

    <section class="workspace-hub__tabs">
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
  padding: 26px 28px;
  border-radius: 24px;
  border: 1px solid #e3ebf5;
  background: linear-gradient(135deg, #ffffff 0%, #edf4ff 100%);
  box-shadow: 0 18px 38px rgba(15, 23, 42, 0.05);
}

.workspace-hub__eyebrow {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #4a73b8;
}

.workspace-hub__hero h1 {
  margin: 8px 0 0;
  font-size: 30px;
  color: var(--app-text-main);
}

.workspace-hub__hero p {
  margin: 10px 0 0;
  max-width: 780px;
  color: #61758f;
  line-height: 1.75;
}

.workspace-hub__tabs {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.workspace-hub__tab {
  display: grid;
  gap: 6px;
  padding: 16px 18px;
  text-align: left;
  border-radius: 18px;
  border: 1px solid #dfe7f1;
  background: #fff;
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.workspace-hub__tab strong {
  font-size: 15px;
  color: var(--app-text-main);
}

.workspace-hub__tab span {
  color: #6b7e97;
  font-size: 12px;
  line-height: 1.6;
}

.workspace-hub__tab:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 24px rgba(31, 51, 84, 0.07);
}

.workspace-hub__tab.active {
  border-color: color-mix(in srgb, var(--app-primary) 35%, var(--app-border));
  background: var(--app-primary-tint);
}

@media (max-width: 1100px) {
  .workspace-hub__tabs {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 720px) {
  .workspace-hub__tabs {
    grid-template-columns: 1fr;
  }
}
</style>
