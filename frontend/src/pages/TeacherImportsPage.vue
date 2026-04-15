<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import TeacherStageImport from "../components/TeacherStageImport.vue";
import TeacherIntroHero from "../components/TeacherIntroHero.vue";
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
    <TeacherIntroHero
      eyebrow="阶段评价"
      title="数据导入"
      pill="数据流转"
      description="按课程与阶段导入系统汇总、人工文件或行为信号，再进入结果页核对最新画像与阶段判断。"
    >
      <template #actions>
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
      </template>
    </TeacherIntroHero>

    <section class="imports-page__panel">
      <TeacherStageImport
        :course-id="selectedCourseId"
        :subject="subject"
        :grade="grade"
        @view-profiles="goResults"
      />
    </section>
  </div>
</template>

<style scoped>
.imports-page {
  display: grid;
  gap: 20px;
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
  color: #25645b;
}

.imports-page__select {
  width: 320px;
  max-width: 100%;
}

.imports-page__hero-actions :deep(.el-select__wrapper) {
  min-height: 44px;
  border-radius: 14px !important;
  background: linear-gradient(180deg, #fffdfa 0%, #fff7ef 100%) !important;
  box-shadow: 0 0 0 1px #dde3ef inset !important;
}

.imports-page__btn {
  min-height: 44px;
  padding: 0 18px;
  border-radius: 999px;
  border: 1px solid #dde3ef;
  background: linear-gradient(180deg, #fffdfa 0%, #fff7ef 100%);
  color: #315f56;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
}

.imports-page__btn--primary {
  border-color: #c7e38e;
  background: linear-gradient(180deg, #edf9cf 0%, #dff2b4 100%);
  color: #23421f;
}

.imports-page__panel {
  min-width: 0;
  padding: 18px;
  border-radius: 32px;
  border: 3px solid #1f2937;
  background:
    radial-gradient(circle at top left, rgba(201, 237, 255, 0.22), transparent 24%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
}

@media (max-width: 1024px) {
  .imports-page__hero-actions {
    align-items: stretch;
  }
}
</style>
