<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import WorkspaceTopbar from "../components/WorkspaceTopbar.vue";
import TeacherStageImport from "../components/TeacherStageImport.vue";
import PageSectionCard from "../components/PageSectionCard.vue";
import HintButton from "../components/HintButton.vue";
import { buildTeacherSubjectQuery, resolveTeacherSubject, saveTeacherSubject } from "../utils/teacherCourse";

type Course = { id: number; code: string; title: string };
const route = useRoute(); const router = useRouter();
const subject = ref(""); const grade = ref("通用"); const courses = ref<Course[]>([]);
const selectedCourseId = computed<number | null>(() => courses.value.find((item) => item.title === subject.value)?.id ?? null);
async function loadCourses() { try { const res = await api.get("/graph/courses"); courses.value = res.data ?? []; subject.value = resolveTeacherSubject(String(route.query.subject || ""), subject.value, courses.value); } catch (e:any) { ElMessage.error(e?.response?.data?.detail ?? "加载教师课程失败"); } }
function syncQuery() { saveTeacherSubject(subject.value); router.replace({ path: "/teacher/imports", query: buildTeacherSubjectQuery(subject.value) }); }
watch(subject, () => syncQuery());
watch(() => route.query.subject, (value) => { const next = String(value || "").trim(); if (next && next !== subject.value) subject.value = next; });
onMounted(loadCourses);
</script>
<template>
  <div class="teacher-page">
    <WorkspaceTopbar v-model="subject" :courses="courses" badge="Teacher Imports" title="阶段数据导入" @change="syncQuery">
      <HintButton tip="回到阶段管理页，继续维护阶段结构。" @click="router.push({ path: '/teacher/stages', query: { subject: subject || undefined } })">返回阶段管理</HintButton>
      <HintButton tip="查看系统行为信号汇总和画像报表。" @click="router.push({ path: '/teacher/behavior-report', query: { subject: subject || undefined } })">行为画像报表</HintButton>
    </WorkspaceTopbar>
    <PageSectionCard eyebrow="Imports" title="全班阶段数据导入">
      <TeacherStageImport
        :course-id="selectedCourseId"
        :subject="subject"
        :grade="grade"
        @view-profiles="router.push({ path: '/teacher/profiles', query: { subject: subject || undefined } })"
      />
    </PageSectionCard>
  </div>
</template>
<style scoped>.teacher-page{display:grid;gap:20px}</style>
