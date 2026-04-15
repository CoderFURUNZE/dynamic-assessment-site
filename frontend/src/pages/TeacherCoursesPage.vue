<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  CircleCheck,
  Histogram,
  Plus,
  Reading,
  Refresh,
  SwitchButton,
} from "@element-plus/icons-vue";
import { api } from "../api";
import AdminIntroHero from "../components/AdminIntroHero.vue";

type CourseRow = {
  id: number;
  code: string;
  title: string;
  description: string;
  target_class?: string | null;
  activated?: boolean;
  can_activate?: boolean;
  can_finish?: boolean;
  can_exit?: boolean;
  teaching_status?: string | null;
};

type PanelKey = "teaching" | "activatable" | "finished";

const loading = ref(false);
const actioningKey = ref("");
const catalogRows = ref<CourseRow[]>([]);
const activePanel = ref<PanelKey>("teaching");

function normalizeTeachingStatus(value?: string | null) {
  return String(value || "").trim().toLowerCase();
}

const teachingRows = computed(() =>
  catalogRows.value.filter((item) => item.activated && normalizeTeachingStatus(item.teaching_status) === "teaching"),
);
const activatableRows = computed(() =>
  catalogRows.value.filter((item) => !item.activated && item.can_activate),
);
const finishedRows = computed(() =>
  catalogRows.value.filter((item) => item.activated && normalizeTeachingStatus(item.teaching_status) === "finished"),
);

const currentPanelTitle = computed(() => {
  if (activePanel.value === "activatable") return "可激活课程";
  if (activePanel.value === "finished") return "已结课课程";
  return "授课中课程";
});

const currentPanelRows = computed(() => {
  if (activePanel.value === "activatable") return activatableRows.value;
  if (activePanel.value === "finished") return finishedRows.value;
  return teachingRows.value;
});

const currentEmptyText = computed(() => {
  if (activePanel.value === "activatable") return "当前没有可激活课程";
  if (activePanel.value === "finished") return "当前没有已结课课程";
  return "当前没有授课中课程";
});

function panelTagType(panel: PanelKey) {
  if (panel === "activatable") return "";
  if (panel === "finished") return "info";
  return "success";
}

function teachingStatusLabel(value?: string | null) {
  const normalized = normalizeTeachingStatus(value);
  if (normalized === "finished") return "已结课";
  if (normalized === "teaching") return "授课中";
  return "未激活";
}

function teachingStatusClass(value?: string | null) {
  const normalized = normalizeTeachingStatus(value);
  if (normalized === "finished") return "teacher-course-card__chip--warn";
  if (normalized === "teaching") return "teacher-course-card__chip--ok";
  return "";
}

async function loadCatalog() {
  loading.value = true;
  try {
    const res = await api.get("/graph/teacher/course-catalog");
    catalogRows.value = res.data?.items ?? [];
    if (activePanel.value === "teaching" && teachingRows.value.length === 0 && activatableRows.value.length > 0) {
      activePanel.value = "activatable";
    }
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "加载课程失败");
    catalogRows.value = [];
  } finally {
    loading.value = false;
  }
}

async function activateCourse(row: CourseRow) {
  const actionKey = `activate-${row.id}`;
  if (actioningKey.value) return;
  actioningKey.value = actionKey;
  try {
    await api.post(`/graph/teacher/courses/${row.id}/activate`);
    ElMessage.success("课程已激活，学生现在可以进入学习");
    activePanel.value = "teaching";
    await loadCatalog();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "激活课程失败");
  } finally {
    actioningKey.value = "";
  }
}

async function finishCourse(row: CourseRow) {
  if (actioningKey.value) return;
  try {
    await ElMessageBox.confirm(
      `结束后，学生将不能继续进入《${row.title}》学习。确认结束这门课程吗？`,
      "结束课程",
      {
        type: "warning",
        confirmButtonText: "确认结束",
        cancelButtonText: "取消",
      },
    );
  } catch {
    return;
  }
  const actionKey = `finish-${row.id}`;
  actioningKey.value = actionKey;
  try {
    await api.post(`/graph/teacher/courses/${row.id}/finish`);
    ElMessage.success("课程已结课");
    activePanel.value = "finished";
    await loadCatalog();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "结束课程失败");
  } finally {
    actioningKey.value = "";
  }
}

async function exitCourse(row: CourseRow) {
  if (actioningKey.value) return;
  try {
    await ElMessageBox.confirm(
      `退出后，《${row.title}》会从你的工作台移除，但不会影响历史记录。确认退出吗？`,
      "退出工作台",
      {
        type: "warning",
        confirmButtonText: "确认退出",
        cancelButtonText: "取消",
      },
    );
  } catch {
    return;
  }
  const actionKey = `exit-${row.id}`;
  actioningKey.value = actionKey;
  try {
    await api.delete(`/graph/teacher/courses/${row.id}/activation`);
    ElMessage.success("已退出课程工作台");
    activePanel.value = "activatable";
    await loadCatalog();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "退出工作台失败");
  } finally {
    actioningKey.value = "";
  }
}

onMounted(loadCatalog);
</script>

<template>
  <div class="teacher-courses-page" v-loading="loading">
    <AdminIntroHero
      eyebrow="教师工作台"
      title="课程工作台"
      pill="课程运行"
      description="管理员决定课程是否在平台开放，教师负责激活课程、结课课程和退出工作台。"
    >
    </AdminIntroHero>

    <section class="teacher-courses-page__stats">
      <article
        class="teacher-courses-page__stat-card"
        :class="{ 'is-active': activePanel === 'teaching' }"
        @click="activePanel = 'teaching'"
      >
        <div class="teacher-courses-page__stat-icon teacher-courses-page__stat-icon--on">
          <el-icon><Reading /></el-icon>
        </div>
        <div>
          <span>授课中</span>
          <strong>{{ teachingRows.length }}</strong>
        </div>
      </article>
      <article
        class="teacher-courses-page__stat-card"
        :class="{ 'is-active': activePanel === 'activatable' }"
        @click="activePanel = 'activatable'"
      >
        <div class="teacher-courses-page__stat-icon teacher-courses-page__stat-icon--pending">
          <el-icon><Plus /></el-icon>
        </div>
        <div>
          <span>可激活</span>
          <strong>{{ activatableRows.length }}</strong>
        </div>
      </article>
      <article
        class="teacher-courses-page__stat-card"
        :class="{ 'is-active': activePanel === 'finished' }"
        @click="activePanel = 'finished'"
      >
        <div class="teacher-courses-page__stat-icon teacher-courses-page__stat-icon--hold">
          <el-icon><Histogram /></el-icon>
        </div>
        <div>
          <span>已结课</span>
          <strong>{{ finishedRows.length }}</strong>
        </div>
      </article>
    </section>

    <section class="teacher-courses-page__panel">
      <header class="teacher-courses-page__panel-head">
        <h2>{{ currentPanelTitle }}</h2>
        <div class="teacher-courses-page__panel-actions">
          <el-button
            class="teacher-courses-page__refresh-btn"
            type="primary"
            round
            :loading="loading"
            @click="loadCatalog"
          >
            <el-icon class="el-icon--left"><Refresh /></el-icon>
            刷新课程
          </el-button>
          <el-tag round :type="panelTagType(activePanel)">{{ currentPanelRows.length }}</el-tag>
        </div>
      </header>

      <div v-if="currentPanelRows.length" class="teacher-courses-page__card-grid">
        <article
          v-for="row in currentPanelRows"
          :key="`${activePanel}-${row.id}`"
          class="teacher-course-card"
        >
          <div class="teacher-course-card__top">
            <span class="teacher-course-card__code">{{ row.code }}</span>
            <h3>{{ row.title }}</h3>
          </div>
          <p>{{ row.description || "管理员暂未填写课程简介。" }}</p>
          <div class="teacher-course-card__chips">
            <span
              class="teacher-course-card__chip"
              :class="activePanel === 'activatable' ? 'teacher-course-card__chip--ok' : teachingStatusClass(row.teaching_status)"
            >
              {{ activePanel === 'activatable' ? "待教师激活" : teachingStatusLabel(row.teaching_status) }}
            </span>
            <span class="teacher-course-card__chip teacher-course-card__chip--muted">
              {{ row.target_class || "班级未设置" }}
            </span>
          </div>
          <div class="teacher-course-card__actions">
            <el-button
              v-if="activePanel === 'activatable'"
              class="teacher-course-card__activate-btn"
              type="primary"
              round
              :loading="actioningKey === `activate-${row.id}`"
              @click="activateCourse(row)"
            >
              激活课程
            </el-button>
            <el-button
              v-if="activePanel === 'teaching' && row.can_finish"
              class="teacher-course-card__finish-btn"
              type="warning"
              round
              :loading="actioningKey === `finish-${row.id}`"
              @click="finishCourse(row)"
            >
              <el-icon class="el-icon--left"><CircleCheck /></el-icon>
              结束课程
            </el-button>
            <el-button
              v-if="activePanel === 'finished' && row.can_exit"
              class="teacher-course-card__exit-btn"
              round
              :loading="actioningKey === `exit-${row.id}`"
              @click="exitCourse(row)"
            >
              <el-icon class="el-icon--left"><SwitchButton /></el-icon>
              退出工作台
            </el-button>
          </div>
        </article>
      </div>

      <el-empty v-else :description="currentEmptyText" />
    </section>
  </div>
</template>

<style scoped>
.teacher-courses-page {
  display: grid;
  gap: 18px;
}

.teacher-courses-page__panel,
.teacher-courses-page__stats {
  border-radius: 32px;
  border: 3px solid #1f2937;
  background:
    radial-gradient(circle at top right, rgba(201, 237, 255, 0.32), transparent 28%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
}

.teacher-courses-page__refresh-btn,
.teacher-course-card__activate-btn {
  --el-button-text-color: #ffffff;
  --el-button-bg-color: #059669;
  --el-button-border-color: #059669;
  --el-button-hover-text-color: #ffffff;
  --el-button-hover-bg-color: #047857;
  --el-button-hover-border-color: #047857;
  --el-button-active-bg-color: #065f46;
  --el-button-active-border-color: #065f46;
  min-width: 108px;
  padding-inline: 18px;
  box-shadow: 0 10px 22px rgba(5, 150, 105, 0.2);
}

.teacher-course-card__actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.teacher-course-card__finish-btn,
.teacher-course-card__exit-btn {
  min-width: 118px;
  padding-inline: 18px;
}

.teacher-courses-page__stats {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  padding: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
}

.teacher-courses-page__stat-card {
  border-radius: 34px;
  border: 3px solid #1f2937 !important;
  background: linear-gradient(180deg, #fffaf3 0%, #fffdf8 100%) !important;
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12) !important;
  display: grid;
  gap: 10px;
  align-content: start;
  padding: 26px 28px;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  min-height: 132px;
}

.teacher-courses-page__stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 0 rgba(31, 41, 55, 0.14) !important;
}

.teacher-courses-page__stat-card.is-active {
  border-color: #1f2937 !important;
  background: linear-gradient(180deg, #fffaf3 0%, #fffdf8 100%) !important;
  box-shadow: 0 14px 0 rgba(31, 41, 55, 0.14) !important;
}

.teacher-courses-page__stat-icon {
  display: none;
}

.teacher-courses-page__stat-icon--on { background: linear-gradient(145deg, #059669 0%, #10b981 100%); }
.teacher-courses-page__stat-icon--pending { background: linear-gradient(145deg, #0891b2 0%, #22d3ee 100%); }
.teacher-courses-page__stat-icon--hold { background: linear-gradient(145deg, #64748b 0%, #94a3b8 100%); }

.teacher-courses-page__stat-card span {
  display: block;
  font-size: 13px;
  font-weight: 700;
  color: #506176;
  letter-spacing: 0;
  text-transform: none;
}

.teacher-courses-page__stat-card strong {
  display: block;
  margin-top: 8px;
  font-size: 48px;
  line-height: 1;
  color: var(--app-text-main);
}

.teacher-courses-page__panel {
  overflow: hidden;
  padding: 0;
  box-shadow: 0 14px 0 rgba(31, 41, 55, 0.12);
}

.teacher-courses-page__panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 22px 24px;
  border-bottom: 1.5px solid #c6d8ef;
  background:
    radial-gradient(circle at top right, rgba(201, 237, 255, 0.18), transparent 28%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
}

.teacher-courses-page__panel-head h2 {
  margin: 0;
  font-size: 18px;
  color: var(--app-text-main);
}

.teacher-courses-page__panel-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}

.teacher-courses-page__card-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  padding: 22px 24px 24px;
  background:
    radial-gradient(circle at top left, rgba(201, 237, 255, 0.14), transparent 24%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
}

.teacher-course-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 22px;
  border-radius: 24px;
  border: 2px solid #1f2937;
  background:
    radial-gradient(circle at top left, rgba(201, 237, 255, 0.18), transparent 24%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
  box-shadow: 0 10px 0 rgba(31, 41, 55, 0.08);
  min-width: 0;
}

.teacher-course-card__top {
  display: grid;
  gap: 8px;
}

.teacher-course-card__code {
  width: fit-content;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  background: rgba(5, 150, 105, 0.1);
  color: #047857;
}

.teacher-course-card h3 {
  margin: 0;
  font-size: 18px;
  color: var(--app-text-main);
}

.teacher-course-card p {
  margin: 0;
  color: var(--app-text-soft);
  line-height: 1.7;
  overflow-wrap: anywhere;
}

.teacher-course-card__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.teacher-course-card__chip {
  padding: 5px 10px;
  border-radius: 999px;
  font-size: 12px;
  background: linear-gradient(180deg, #f4f9ff 0%, #edf6ff 100%);
  color: #4b635a;
  border: 1.5px solid #c6d8ef;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.teacher-course-card__chip--muted {
  color: #64748b;
}

.teacher-course-card__chip--ok {
  background: linear-gradient(180deg, #f4fff8 0%, #effcf4 100%);
  color: #047857;
  border-color: rgba(16, 185, 129, 0.34);
}

.teacher-course-card__chip--warn {
  background: linear-gradient(180deg, #f4fbff 0%, #edf8ff 100%);
  color: #0e7490;
  border-color: rgba(8, 145, 178, 0.34);
}

@media (max-width: 1100px) {
  .teacher-courses-page__stats,
  .teacher-courses-page__card-grid {
    grid-template-columns: 1fr;
  }

  .teacher-courses-page__panel-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .teacher-courses-page__panel-actions {
    width: 100%;
    justify-content: space-between;
  }
}
</style>
