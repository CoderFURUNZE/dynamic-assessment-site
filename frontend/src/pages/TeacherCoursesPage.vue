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
.teacher-courses-page__stat-card {
  border-radius: 28px;
  border: 1px solid #e3ebf5;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: var(--app-shadow);
}

.teacher-courses-page__refresh-btn,
.teacher-course-card__activate-btn {
  --el-button-text-color: #ffffff;
  --el-button-bg-color: #5c8fff;
  --el-button-border-color: #5c8fff;
  --el-button-hover-text-color: #ffffff;
  --el-button-hover-bg-color: #4d82f5;
  --el-button-hover-border-color: #4d82f5;
  --el-button-active-bg-color: #4577e6;
  --el-button-active-border-color: #4577e6;
  min-width: 108px;
  padding-inline: 18px;
  box-shadow: 0 10px 22px rgba(92, 143, 255, 0.22);
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
}

.teacher-courses-page__stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.teacher-courses-page__stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.08);
}

.teacher-courses-page__stat-card.is-active {
  border-color: #8eb7f7;
  box-shadow: var(--app-shadow-lg);
}

.teacher-courses-page__stat-icon {
  width: 46px;
  height: 46px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  color: #fff;
}

.teacher-courses-page__stat-icon--on { background: linear-gradient(145deg, #3b82f6 0%, #10b981 100%); }
.teacher-courses-page__stat-icon--pending { background: linear-gradient(145deg, #6366f1 0%, #4f8cff 100%); }
.teacher-courses-page__stat-icon--hold { background: linear-gradient(145deg, #94a3b8 0%, #cbd5e1 100%); }

.teacher-courses-page__stat-card span {
  display: block;
  font-size: 12px;
  color: var(--app-text-soft);
}

.teacher-courses-page__stat-card strong {
  font-size: 26px;
  color: var(--app-text-main);
}

.teacher-courses-page__panel {
  overflow: hidden;
}

.teacher-courses-page__panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 22px 24px;
  border-bottom: 1px solid #edf2f7;
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
}

.teacher-course-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 22px;
  border-radius: 24px;
  border: 1px solid #e6edf5;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: var(--app-shadow-sm);
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
  background: var(--app-primary-soft);
  color: var(--app-primary-deep);
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
  background: #f1f5f9;
  color: #475569;
  border: 1px solid #e2e8f0;
}

.teacher-course-card__chip--muted {
  color: #64748b;
}

.teacher-course-card__chip--ok {
  background: rgba(16, 185, 129, 0.1);
  color: #047857;
  border-color: rgba(16, 185, 129, 0.28);
}

.teacher-course-card__chip--warn {
  background: rgba(245, 158, 11, 0.12);
  color: #b45309;
  border-color: rgba(245, 158, 11, 0.35);
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
