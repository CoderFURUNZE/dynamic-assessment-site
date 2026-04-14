<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import TeacherStageImport from "../components/TeacherStageImport.vue";
import { buildTeacherSubjectQuery, resolveTeacherSubject, saveTeacherSubject } from "../utils/teacherCourse";

type Course = { id: number; code: string; title: string };

const route = useRoute();
const router = useRouter();

const subject = ref("");
const grade = ref("通用");
const courses = ref<Course[]>([]);

const selectedCourseId = computed<number | null>(() => courses.value.find((item) => item.title === subject.value)?.id ?? null);

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
    path: "/teacher/evaluation",
    query: { ...buildTeacherSubjectQuery(subject.value), tab: "imports" },
  });
}

function goResults() {
  router.push({
    path: "/teacher/evaluation",
    query: { subject: subject.value || undefined, tab: "results" },
  });
}

function goHistory() {
  router.push({
    path: "/teacher/evaluation",
    query: { subject: subject.value || undefined, tab: "imports", section: "history" },
  });
}

watch(subject, () => syncQuery());
watch(
  () => route.query.subject,
  (value) => {
    const next = resolveTeacherSubject(String(value || ""), subject.value, courses.value);
    if (next && next !== subject.value) subject.value = next;
  },
);

onMounted(loadCourses);
</script>

<template>
  <div class="imports-page">
    <section class="imports-page__hero">
      <div class="imports-page__hero-copy">
        <span class="imports-page__eyebrow">阶段评价</span>
        <h1>数据导入</h1>
        <p>按课程选择阶段后导入系统汇总、手工文件或行为信号，系统会自动重算阶段画像。</p>
      </div>

      <div class="imports-page__hero-actions">
        <div class="imports-page__field">
          <label>当前课程</label>
          <el-select v-model="subject" size="large" placeholder="请选择课程" class="imports-page__select">
            <el-option v-for="course in courses" :key="course.id" :label="course.title" :value="course.title" />
          </el-select>
        </div>
        <button class="imports-page__btn" type="button" @click="goHistory">导入历史</button>
        <button class="imports-page__btn imports-page__btn--primary" type="button" @click="goResults">去看结果</button>
      </div>
    </section>

    <TeacherStageImport
      :course-id="selectedCourseId"
      :subject="subject"
      :grade="grade"
      @view-profiles="goResults"
    />
  </div>
</template>

<style scoped>
.imports-page {
  display: grid;
  gap: 20px;
}

.imports-page__hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 24px 26px;
  border-radius: 24px;
  border: 1px solid #dfe7f4;
  background: linear-gradient(180deg, #f7fbff 0%, #ffffff 100%);
  box-shadow: 0 10px 28px rgba(31, 61, 120, 0.05);
}

.imports-page__hero-copy {
  display: grid;
  gap: 8px;
  max-width: 60ch;
}

.imports-page__eyebrow {
  display: inline-flex;
  width: fit-content;
  padding: 6px 12px;
  border-radius: 999px;
  background: #eef4ff;
  color: #4f7fff;
  font-size: 12px;
  font-weight: 800;
}

.imports-page__hero-copy h1 {
  margin: 0;
  color: #1f2a44;
  font-size: clamp(28px, 3vw, 34px);
  line-height: 1.1;
}

.imports-page__hero-copy p {
  margin: 0;
  color: #70819a;
  font-size: 14px;
  line-height: 1.7;
}

.imports-page__hero-actions {
  display: flex;
  align-items: end;
  gap: 12px;
  flex-wrap: wrap;
}

.imports-page__field {
  display: grid;
  gap: 8px;
}

.imports-page__field label {
  font-size: 13px;
  font-weight: 700;
  color: #405a7f;
}

.imports-page__select {
  width: 320px;
  max-width: 100%;
}

.imports-page__hero-actions :deep(.el-select__wrapper) {
  min-height: 44px;
  border-radius: 14px !important;
}

.imports-page__btn {
  min-height: 44px;
  padding: 0 18px;
  border-radius: 999px;
  border: 1px solid #dce6f2;
  background: #ffffff;
  color: #314661;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}

.imports-page__btn--primary {
  border-color: #4f7fff;
  background: linear-gradient(135deg, #5b7cfa 0%, #59b7ff 100%);
  color: #ffffff;
}

@media (max-width: 1024px) {
  .imports-page__hero {
    display: grid;
    grid-template-columns: 1fr;
  }

  .imports-page__hero-actions {
    align-items: stretch;
  }
}
</style>
