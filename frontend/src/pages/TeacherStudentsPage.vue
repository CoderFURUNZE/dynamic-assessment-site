<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import WorkspaceTopbar from "../components/WorkspaceTopbar.vue";
import TeacherStudentDetail from "../components/TeacherStudentDetail.vue";
import PageSectionCard from "../components/PageSectionCard.vue";
import { buildTeacherSubjectQuery, resolveTeacherSubject, saveTeacherSubject } from "../utils/teacherCourse";

type Course = { id: number; code: string; title: string };
const route = useRoute(); const router = useRouter();
const subject = ref(""); const grade = ref("通用"); const courses = ref<Course[]>([]);
const selectedStudentId = computed<number | null>(() => {
  const raw = route.query.user_id;
  const value = Array.isArray(raw) ? raw[0] : raw;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
});
async function loadCourses() { try { const res = await api.get("/graph/courses"); courses.value = res.data ?? []; subject.value = resolveTeacherSubject(String(route.query.subject || ""), subject.value, courses.value); } catch (e:any) { ElMessage.error(e?.response?.data?.detail ?? "加载教师课程失败"); } }
function syncQuery() { saveTeacherSubject(subject.value); router.replace({ path: "/teacher/students", query: buildTeacherSubjectQuery(subject.value, { tab: "detail", user_id: selectedStudentId.value ? String(selectedStudentId.value) : undefined }) }); }
watch(subject, () => syncQuery());
watch(() => route.query.subject, (value) => { const next = String(value || "").trim(); if (next && next !== subject.value) subject.value = next; });
onMounted(loadCourses);
</script>
<template>
  <div class="teacher-page">
    <WorkspaceTopbar v-model="subject" :courses="courses" badge="Teacher Students" title="学生详情" @change="syncQuery">
      <el-button @click="router.push({ path: '/teacher/students', query: { subject: subject || undefined, tab: 'class' } })">返回班级总览</el-button>
    </WorkspaceTopbar>
    <PageSectionCard eyebrow="Students" title="学生详情">
      <TeacherStudentDetail :subject="subject" :grade="grade" :initial-user-id="selectedStudentId" />
    </PageSectionCard>
  </div>
</template>
<style scoped>.teacher-page{display:grid;gap:20px}</style>
