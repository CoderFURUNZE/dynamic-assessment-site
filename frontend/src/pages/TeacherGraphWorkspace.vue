<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import { getRole } from "../token";
import TeacherGraphWorkbench from "../components/TeacherGraphWorkbench.vue";
import { buildTeacherSubjectQuery, resolveTeacherSubject, saveTeacherSubject } from "../utils/teacherCourse";

type Course = {
  id: number;
  code: string;
  title: string;
  lifecycle_status?: string;
  start_at?: string | null;
  end_at?: string | null;
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
const isStandaloneWorkspace = computed(() => Boolean(route.meta?.standaloneWorkspace));

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
const selectedLabel = computed(() => {
  if (workbenchState.value.selectedType === "category" && workbenchState.value.selectedCategory) {
    return workbenchState.value.selectedCategory;
  }
  if (workbenchState.value.selectedKpId) return `#${workbenchState.value.selectedKpId}`;
  return "未选择";
});

const summaryCards = computed(() => [
  { label: "知识点", value: String(workbenchState.value.kpCount) },
  { label: "分类", value: String(workbenchState.value.categoryCount) },
  { label: "当前选中", value: selectedLabel.value },
  { label: "状态", value: isReadonlyCourse.value ? "只读" : "可编辑" },
]);

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

function updateWorkbenchState(payload: WorkbenchState) {
  workbenchState.value = payload;
}

async function refreshWorkspace() {
  await loadCourses();
}

function goBack() {
  router.push({ path: "/teacher/workspace", query: buildTeacherSubjectQuery(subject.value) });
}

watch(
  () => route.query.subject,
  (value) => {
    const next = String(value || "");
    if (next && next !== subject.value) subject.value = next;
  },
);

watch(subject, () => {
  syncQuery();
});

onMounted(async () => {
  if (!isTeacher.value) {
    ElMessage.warning("仅教师可访问知识图谱");
    router.push("/login/student");
    return;
  }
  await loadCourses();
});
</script>

<template>
  <div v-if="isTeacher" class="graph-page">
    <section class="graph-page__toolbar">
      <div class="graph-page__toolbar-copy">
        <span class="graph-page__eyebrow">Teacher Workspace</span>
        <h1>知识图谱建设</h1>
        <p>{{ currentCourse?.title || "当前课程" }}</p>
      </div>

      <div class="graph-page__toolbar-actions">
        <el-select v-model="subject" class="graph-page__select" placeholder="选择课程">
          <el-option v-for="course in courses" :key="course.id" :label="course.title" :value="course.title" />
        </el-select>
        <button class="graph-page__ghost-btn" type="button" @click="refreshWorkspace">刷新</button>
      </div>
    </section>

    <section class="graph-page__workspace">
      <TeacherGraphWorkbench
        :subject="subject"
        :grade="grade"
        :fullscreen="true"
        :readonly="isReadonlyCourse"
        @state-change="updateWorkbenchState"
      />
    </section>
    <section class="graph-page__hero">
      <div class="graph-page__hero-copy">
        <span class="graph-page__eyebrow">Teacher Workspace</span>
        <h1>知识图谱建设</h1>
        <p>{{ currentCourse?.title || "当前课程" }}</p>
      </div>

      <div class="graph-page__hero-actions">
        <el-select v-model="subject" class="graph-page__select" placeholder="选择课程">
          <el-option v-for="course in courses" :key="course.id" :label="course.title" :value="course.title" />
        </el-select>
        <button class="graph-page__ghost-btn" type="button" @click="refreshWorkspace">刷新</button>
      </div>
    </section>

    <section class="graph-page__stats">
      <article v-for="item in summaryCards" :key="item.label" class="graph-page__stat-card">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </article>
    </section>

    <section class="graph-page__panel">
      <header class="graph-page__panel-head">
        <div>
          <h2>图谱编辑画布</h2>
          <span>{{ currentCourse?.code || "课程" }}</span>
        </div>
      </header>

      <div class="graph-page__panel-body">
        <TeacherGraphWorkbench
          :subject="subject"
          :grade="grade"
          :fullscreen="true"
          :readonly="isReadonlyCourse"
          @state-change="updateWorkbenchState"
        />
      </div>
    </section>
  </div>
</template>

<style scoped>
.graph-page {
  min-height: calc(100dvh - 96px);
  display: grid;
  gap: 12px;
}

.graph-page__toolbar,
.graph-page__workspace,
.graph-page__stat-card {
  border-radius: 24px;
  border: 1px solid color-mix(in srgb, var(--app-primary) 14%, var(--app-border));
  background: #ffffff;
  box-shadow: var(--app-shadow-soft);
}

.graph-page__hero,
.graph-page__stats,
.graph-page__panel {
  display: none;
}

.graph-page__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 18px;
  background: linear-gradient(135deg, #eef4ff 0%, #f5fbf7 52%, #ffffff 100%);
}

.graph-page__toolbar-copy {
  display: grid;
  gap: 6px;
  max-width: 60ch;
}

.graph-page__eyebrow {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #5a7db7;
}

.graph-page__toolbar-copy h1 {
  margin: 0;
  font-size: clamp(22px, 3vw, 30px);
  line-height: 1.1;
  color: #11284a;
}

.graph-page__toolbar-copy p {
  margin: 0;
  color: #60758f;
  font-size: 13px;
  line-height: 1.5;
}

.graph-page__toolbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.graph-page__select {
  width: 240px;
}

.graph-page__ghost-btn {
  min-height: 42px;
  padding: 0 16px;
  border-radius: 14px;
  border: 1px solid var(--app-border);
  background: rgba(255, 255, 255, 0.92);
  color: #31527f;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}

.graph-page__workspace {
  overflow: hidden;
  min-height: min(88vh, 1080px);
  padding: 8px;
  background: linear-gradient(180deg, #f8fbff 0%, #f3f7fc 100%);
}

@media (max-width: 1100px) {
  .graph-page__toolbar {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 768px) {
  .graph-page__toolbar-copy h1 {
    font-size: 28px;
  }

  .graph-page__select {
    width: 100%;
  }

  .graph-page__workspace {
    min-height: min(80vh, 940px);
  }
}
</style>
