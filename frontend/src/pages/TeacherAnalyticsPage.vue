<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import WorkspaceTopbar from "../components/WorkspaceTopbar.vue";
import AdminAnalyticsOverview from "../components/AdminAnalyticsOverview.vue";
import PageSectionCard from "../components/PageSectionCard.vue";
import { buildTeacherSubjectQuery, resolveTeacherSubject, saveTeacherSubject } from "../utils/teacherCourse";

type Course = { id: number; code: string; title: string };
const route = useRoute(); const router = useRouter();
const subject = ref(""); const grade = ref("通用"); const courses = ref<Course[]>([]);
async function loadCourses() { try { const res = await api.get("/graph/courses"); courses.value = res.data ?? []; subject.value = resolveTeacherSubject(String(route.query.subject || ""), subject.value, courses.value); } catch (e:any) { ElMessage.error(e?.response?.data?.detail ?? "加载教师课程失败"); } }
function syncQuery() { saveTeacherSubject(subject.value); router.replace({ path: "/teacher/analytics", query: buildTeacherSubjectQuery(subject.value) }); }
watch(subject, () => syncQuery());
watch(() => route.query.subject, (value) => { const next = String(value || "").trim(); if (next && next !== subject.value) subject.value = next; });
onMounted(loadCourses);
</script>
<template>
  <div class="teacher-page">
    <WorkspaceTopbar v-model="subject" :courses="courses" badge="Teacher Analytics" title="课程分析" @change="syncQuery">
      <el-button @click="router.push({ path: '/teacher/students', query: { subject: subject || undefined } })">看学生详情</el-button>
    </WorkspaceTopbar>
    <PageSectionCard eyebrow="Analytics" title="课程分析">
      <AdminAnalyticsOverview :subject="subject" :grade="grade" :show-student-detail-action="true" @view-student="(id:number)=>router.push({ path: '/teacher/students', query: { user_id: String(id), subject: subject || undefined } })" />
    </PageSectionCard>
  </div>
</template>
<style scoped>.teacher-page{display:grid;gap:20px}</style>
