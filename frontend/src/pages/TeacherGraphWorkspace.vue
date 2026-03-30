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
    path: "/teacher/graph-workspace",
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

onMounted(async () => {
  if (!isTeacher.value) {
    ElMessage.warning("仅教师可访问教师图谱工作区");
    router.push("/login");
    return;
  }
  await loadCourses();
});
</script>

<template>
  <div v-if="isTeacher" class="workspace-page">
    <div class="workspace-page__toolbar">
      <div class="workspace-page__left">
        <div class="workspace-page__title">知识图谱工作台（教学视图）</div>
        <div class="workspace-page__subtitle">与学生端同源课程数据；节点三色环一致——内绿知识、中黄能力、外紫素养。</div>
      </div>

      <div class="workspace-page__right">
        <el-select v-model="subject" style="width: 240px">
          <el-option v-for="course in courses" :key="course.id" :label="course.title" :value="course.title" />
        </el-select>
        <button class="workspace-page__minor-btn" @click="loadCourses">刷新</button>
      </div>
    </div>

    <section class="workspace-simple-note">
      <strong>当前状态</strong>
      <span>分类 {{ workbenchState.categoryCount }} 个，已选知识点 {{ workbenchState.selectedKpId ? 1 : 0 }} 个。</span>
      <span v-if="courseStatusText">{{ courseStatusText }}</span>
      <HoverTip content="在知识点上配置能力标签与素养标签后，学生端图谱与报告会按掌握度、练习与小测证据汇总能力达成情况。" />
    </section>

    <TeacherGraphWorkbench :subject="subject" :grade="grade" :fullscreen="true" :readonly="isReadonlyCourse" @state-change="updateWorkbenchState" />
  </div>
</template>

<style scoped>
.workspace-page {
  /* 与学生端一致，减少外层高度扣减，避免内部画布被截断 */
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
  display: grid;
  gap: 4px;
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

.workspace-simple-note {
  flex-shrink: 0;
  padding: 6px 10px;
  border-radius: var(--app-radius-sm);
  background: var(--app-card);
  border: 1px solid var(--app-border);
  color: var(--app-ink-soft);
  font-size: 12px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
  box-shadow: var(--app-shadow-soft);
}

@media (max-width: 900px) {
  .workspace-page__toolbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .workspace-page__right {
    width: 100%;
    flex-wrap: wrap;
  }
}
</style>
