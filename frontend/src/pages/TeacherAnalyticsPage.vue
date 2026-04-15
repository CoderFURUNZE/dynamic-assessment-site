<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import AdminAnalyticsOverview from "../components/AdminAnalyticsOverview.vue";
import HintButton from "../components/HintButton.vue";
import { buildTeacherSubjectQuery, resolveTeacherSubject, saveTeacherSubject } from "../utils/teacherCourse";

type Course = { id: number; code: string; title: string };

const route = useRoute();
const router = useRouter();
const subject = ref("");
const grade = ref("通用");
const courses = ref<Course[]>([]);

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
    path: "/teacher/students",
    query: { ...buildTeacherSubjectQuery(subject.value), tab: "class" },
  });
}

watch(subject, () => syncQuery());
watch(
  () => route.query.subject,
  (value) => {
    const next = String(value || "").trim();
    if (next && next !== subject.value) subject.value = next;
  }
);

onMounted(loadCourses);
</script>

<template>
  <div class="teacher-page">
    <section class="analytics-toolbar">
      <div class="analytics-toolbar__main">
        <div class="analytics-title">
          <span class="analytics-title__eyebrow">学生分析</span>
          <h1>班级总览</h1>
          <p>{{ subject || "未选择课程" }} · {{ grade }}</p>
        </div>
        <div class="analytics-toolbar__course">
          <span>当前课程</span>
          <el-select v-model="subject" placeholder="请选择课程" size="large" style="width: 240px">
            <el-option v-for="course in courses" :key="course.id" :label="course.title" :value="course.title" />
          </el-select>
        </div>
      </div>
      <div class="analytics-toolbar__actions">
        <HintButton size="small" tip="刷新当前班级分析数据" @click="loadCourses">刷新</HintButton>
        <HintButton
          size="small"
          tip="切换到学生详情视图"
          @click="router.push({ path: '/teacher/students', query: { ...buildTeacherSubjectQuery(subject), tab: 'detail' } })"
        >
          切换视图
        </HintButton>
      </div>
    </section>

    <section class="edu-panel">
      <AdminAnalyticsOverview
        :subject="subject"
        :grade="grade"
        :show-student-detail-action="true"
        @view-student="(id:number) => router.push({ path: '/teacher/students', query: { user_id: String(id), subject: subject || undefined, tab: 'detail' } })"
      />
    </section>
  </div>
</template>

<style scoped>
.teacher-page {
  display: grid;
  gap: 24px;
}

.analytics-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding: 24px 22px;
  border: 3px solid #1f2937;
  border-radius: 32px;
  background:
    radial-gradient(circle at top right, rgba(201, 237, 255, 0.32), transparent 28%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
}

.analytics-toolbar__main,
.analytics-toolbar__actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.analytics-toolbar__course {
  display: grid;
  gap: 6px;
  padding: 0 0 0 4px;
}

.analytics-toolbar__course span {
  font-size: 12px;
  font-weight: 700;
  color: #25645b;
}

.analytics-title {
  display: grid;
  gap: 4px;
}

.analytics-title__eyebrow {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #0f766e;
}

.analytics-title h1 {
  margin: 0;
  font-size: 20px;
  line-height: 1.1;
  font-weight: 800;
  color: #0f172a;
}

.analytics-title p {
  margin: 0;
  font-size: 12px;
  color: #5d746c;
}

:deep(.analytics-toolbar .el-select__wrapper) {
  min-height: 40px;
  border-radius: 18px;
  box-shadow: 0 0 0 1px #c7daf6 inset;
  background: linear-gradient(180deg, #f9fbff 0%, #eef5ff 100%);
}

:deep(.analytics-toolbar .el-select__placeholder),
:deep(.analytics-toolbar .el-select__selected-item) {
  color: #355070;
}

:deep(.teacher-page .edu-panel) {
  padding: 0;
  border: 3px solid #1f2937;
  border-radius: 32px;
  background:
    radial-gradient(circle at top right, rgba(201, 237, 255, 0.32), transparent 28%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
}

@media (max-width: 768px) {
  .analytics-toolbar {
    align-items: stretch;
    padding: 20px 18px;
  }

  .analytics-toolbar__course {
    width: 100%;
    padding-left: 0;
  }
}
</style>
