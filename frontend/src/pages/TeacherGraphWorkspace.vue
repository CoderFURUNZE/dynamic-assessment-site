<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import { getRole } from "../token";
import HoverTip from "../components/HoverTip.vue";
import TeacherGraphWorkbench from "../components/TeacherGraphWorkbench.vue";
import { buildTeacherSubjectQuery, resolveTeacherSubject, saveTeacherSubject } from "../utils/teacherCourse";

type Course = {
  id: number;
  code: string;
  title: string;
  lifecycle_status?: string;
  start_at?: string | null;
  end_at?: string | null;
  archived_at?: string | null;
};
type WorkbenchState = {
  kpCount: number;
  categoryCount: number;
  filteredCount: number;
  selectedType: "kp" | "category";
  selectedKpId: number | null;
  selectedCategory: string | null;
};

const route = useRoute();
const router = useRouter();
const isTeacher = computed(() => getRole() === "teacher");

const courses = ref<Course[]>([]);
const subject = ref("");
const grade = ref("通用");
const workbenchState = ref<WorkbenchState>({
  kpCount: 0,
  categoryCount: 0,
  filteredCount: 0,
  selectedType: "kp",
  selectedKpId: null,
  selectedCategory: null,
});
const currentCourse = computed(() => courses.value.find((item) => item.title === subject.value) ?? null);
const isStandaloneWorkspace = computed(() => Boolean(route.meta?.standaloneWorkspace));
const selectedKpChip = computed(() => {
  if (!workbenchState.value.selectedKpId) return "未选择知识点";
  return `已选知识点 #${workbenchState.value.selectedKpId}`;
});
const nextActionText = computed(() => {
  if (!currentCourse.value) return "先选择课程";
  if (workbenchState.value.kpCount <= 0) return "先创建知识点";
  if (workbenchState.value.selectedKpId) return "继续编辑当前知识点";
  return "选择一个知识点开始编辑";
});
const isReadonlyCourse = computed(() => {
  const course = currentCourse.value;
  if (!course) return false;
  if (String(course.lifecycle_status || "").toLowerCase() === "archived") return true;
  if (course.end_at) {
    const end = new Date(course.end_at).getTime();
    if (Number.isFinite(end) && end < Date.now()) return true;
  }
  return false;
});
const courseStatusText = computed(() => {
  const course = currentCourse.value;
  if (!course) return "";
  if (isReadonlyCourse.value) return "当前课程已归档，图谱只读";
  if (String(course.lifecycle_status || "").toLowerCase() === "draft") return "当前课程还未开课，建议先完善图谱";
  return "当前课程处于开课中，可继续维护图谱";
});

async function loadCourses() {
  try {
    const res = await api.get("/graph/courses");
    courses.value = res.data ?? [];
    subject.value = resolveTeacherSubject(String(route.query.subject || ""), subject.value, courses.value);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载教师课程失败");
  }
}

function syncQuery() {
  saveTeacherSubject(subject.value);
  router.replace({
    path: "/teacher/content",
    query: buildTeacherSubjectQuery(subject.value),
  });
}

watch(
  () => route.query.subject,
  (value) => {
    const next = String(value || "");
    if (next && next !== subject.value) subject.value = next;
  }
);

watch(subject, () => {
  syncQuery();
});

function updateWorkbenchState(payload: WorkbenchState) {
  workbenchState.value = payload;
}

function goWorkspaceHome() {
  router.push("/teacher/workspace");
}

function goEvaluation() {
  router.push({ path: "/teacher/evaluation", query: buildTeacherSubjectQuery(subject.value, { tab: "stages" }) });
}

function goStudents() {
  router.push({ path: "/teacher/students", query: buildTeacherSubjectQuery(subject.value, { tab: "class" }) });
}

function goCurrentKpContent() {
  if (!workbenchState.value.selectedKpId) return;
  router.push({
    path: `/teacher/kp-content/${workbenchState.value.selectedKpId}`,
    query: buildTeacherSubjectQuery(subject.value),
  });
}

onMounted(async () => {
  if (!isTeacher.value) {
    ElMessage.warning("仅教师可访问教师图谱工作区");
    router.push("/login/student");
    return;
  }
  await loadCourses();
});
</script>

<template>
  <div v-if="isTeacher" class="workspace-page" :class="{ 'workspace-page--standalone': isStandaloneWorkspace }">
    <div class="workspace-page__toolbar">
      <div class="workspace-page__left">
        <button class="workspace-page__back" @click="goWorkspaceHome">返回课程工作台</button>
        <div>
          <div class="workspace-page__eyebrow">课程结构</div>
          <div class="workspace-page__title">知识图谱建设</div>
          <div class="workspace-page__subtitle">
            {{ workbenchState.selectedKpId ? `当前任务：${nextActionText}` : "先选课程，再搭结构或补知识点内容。" }}
          </div>
        </div>
      </div>

      <div class="workspace-page__right">
        <el-select v-model="subject" placeholder="选择课程" style="width: min(280px, 100%)">
          <el-option v-for="course in courses" :key="course.id" :label="course.title" :value="course.title" />
        </el-select>
        <button type="button" class="workspace-page__minor-btn" @click="loadCourses">刷新</button>
        <button type="button" class="workspace-page__minor-btn" @click="goStudents">看学生结果</button>
        <div class="workspace-page__chip">{{ selectedKpChip }}</div>
      </div>
    </div>

    <section class="workspace-context-bar">
      <div class="workspace-context-bar__item">
        <span>知识点数</span>
        <strong>{{ workbenchState.kpCount }}</strong>
      </div>
      <div class="workspace-context-bar__item">
        <span>分类数</span>
        <strong>{{ workbenchState.categoryCount }}</strong>
      </div>
      <div class="workspace-context-bar__item">
        <span>当前状态</span>
        <strong>{{ isReadonlyCourse ? "只读" : "可编辑" }}</strong>
      </div>
      <div class="workspace-context-bar__summary">
        <span>{{ nextActionText }}。{{ courseStatusText || "维护知识点、关系和章节布局后，学生端图谱会同步更新。" }}</span>
        <HoverTip content="在知识点上配置能力和素养标签后，学生端图谱与学习报告会按掌握度、练习和小测证据展示达成情况。" />
      </div>
    </section>

    <TeacherGraphWorkbench :subject="subject" :grade="grade" :fullscreen="true" :readonly="isReadonlyCourse" @state-change="updateWorkbenchState" />
  </div>
</template>

<style scoped>
.workspace-page {
  height: calc(100dvh - 96px - 4px);
  max-height: calc(100dvh - 96px - 4px);
  padding: 6px 10px 8px;
  box-sizing: border-box;
  background: var(--app-bg);
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow-x: hidden;
  overflow-y: auto;
  min-height: 0;
}

.workspace-page--standalone {
  height: 100dvh;
  max-height: 100dvh;
  padding: 10px 12px 12px;
}

.workspace-page > :last-child {
  flex: 1;
  min-height: 0;
}

.workspace-page__toolbar {
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border-radius: var(--app-radius);
  background: var(--app-card);
  border: 1px solid var(--app-border);
  box-shadow: var(--app-shadow-soft);
}

.workspace-page__left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.workspace-page__left > div:last-child {
  display: grid;
  gap: 4px;
}

.workspace-page__back {
  border: 1px solid var(--app-border);
  border-radius: 999px;
  padding: 0 18px;
  background: linear-gradient(180deg, #ffffff 0%, #f4f7fb 100%);
  color: #39506d;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  min-height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  box-shadow: var(--app-shadow-soft);
}

.workspace-page__eyebrow {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #6c86ab;
}

.workspace-page__title {
  font-size: 18px;
  font-weight: 800;
  color: #243449;
  line-height: 1.25;
}

.workspace-page__subtitle {
  color: #718097;
  font-size: 12px;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}

.workspace-page__right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.workspace-page__minor-btn {
  border: 1px solid var(--app-border);
  background: linear-gradient(180deg, #ffffff 0%, #f4f7fb 100%);
  color: #39506d;
  border-radius: 999px;
  padding: 0 16px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  min-height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--app-shadow-soft);
}

.workspace-page__primary-btn {
  border: 1px solid var(--app-green);
  background: linear-gradient(180deg, #3f7af0 0%, var(--app-green) 100%);
  color: #ffffff;
  border-radius: 999px;
  padding: 0 16px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 10px 22px rgba(47, 111, 237, 0.18);
  min-height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.workspace-page__chip {
  min-height: 42px;
  padding: 0 18px;
  border-radius: 999px;
  background: #fafbfd;
  border: 1px solid var(--app-border);
  color: #314661;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
}

.workspace-context-bar {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 160px)) 1fr;
  gap: 10px;
}

.workspace-context-bar__item,
.workspace-context-bar__summary,
.workspace-next-bar__card,
.workspace-next-bar__actions {
  padding: 10px 12px;
  border-radius: var(--app-radius-sm);
  background: var(--app-card);
  border: 1px solid var(--app-border);
  box-shadow: var(--app-shadow-soft);
}

.workspace-context-bar__item {
  display: grid;
  gap: 6px;
}

.workspace-context-bar__item span,
.workspace-context-bar__summary span {
  font-size: 12px;
  color: var(--app-ink-soft);
}

.workspace-context-bar__item strong {
  font-size: 16px;
  color: var(--app-ink);
}

.workspace-context-bar__summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

@media (max-width: 900px) {
  .workspace-context-bar {
    grid-template-columns: 1fr;
  }

  .workspace-page__toolbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .workspace-page__left {
    width: 100%;
    flex-wrap: wrap;
  }

  .workspace-page__right {
    width: 100%;
    flex-wrap: wrap;
  }
}
</style>
