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
  { key: "stages", label: "阶段设置", desc: "先建阶段，再导入数据" },
  { key: "indicators", label: "指标配置", desc: "选择这门课真正要看的指标" },
  { key: "imports", label: "数据导入", desc: "导入阶段数据并生成汇总" },
  { key: "behavior", label: "结果查看", desc: "查看行为画像和阶段结果" },
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

const currentTaskText = computed(() => {
  if (currentTab.value === "stages") return "先把阶段建出来";
  if (currentTab.value === "indicators") return "确认这门课真正要看的指标";
  if (currentTab.value === "imports") return "导入阶段数据并生成汇总";
  return "查看结果，确认是否需要回调前面步骤";
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
        <span class="workspace-hub__eyebrow">阶段评价</span>
        <h1>按固定流程完成评价配置和结果查看</h1>
        <p>这个页面只负责串起阶段设置、指标配置、数据导入和结果查看，不再把说明文字堆得过长。</p>
      </div>
      <article class="workspace-hub__focus-card">
        <span>当前最重要的事</span>
        <strong>{{ currentTaskText }}</strong>
        <p>{{ tabs.find((item) => item.key === currentTab)?.desc }}</p>
      </article>
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
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
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
  .workspace-hub__tabs {
    grid-template-columns: 1fr;
  }
}
</style>
