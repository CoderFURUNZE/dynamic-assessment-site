<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import WorkspaceTopbar from "../components/WorkspaceTopbar.vue";
import HintButton from "../components/HintButton.vue";
import PortraitRadarChart from "../components/PortraitRadarChart.vue";
import { buildTeacherSubjectQuery, resolveTeacherSubject, saveTeacherSubject } from "../utils/teacherCourse";

type CourseItem = { id: number; code: string; title: string };
type StudentItem = {
  user_id: number;
  username: string;
  full_name: string;
  student_no: string;
  class_name: string;
  persona_label: string;
  dynamic_score: number;
  course_mastery: number;
  risk_level: string;
  suggested_score: number;
  confirmed_score?: number | null;
  confirmed_level?: string;
  confirmed_at?: string | null;
};

const router = useRouter();
const route = useRoute();
const grade = ref("通用");
const subject = ref("");
const courses = ref<CourseItem[]>([]);
const students = ref<StudentItem[]>([]);
const selectedUserId = ref<number | null>(null);
const detailLoading = ref(false);
const listLoading = ref(false);
const saving = ref(false);
const detail = ref<any | null>(null);
const form = reactive({
  confirmedScorePercent: 0,
  confirmedLevel: "",
  recommendationSummary: "",
  comment: "",
});

const levelOptions = ["优秀", "良好", "中等", "需关注"];
const selectedCourseId = computed<number | null>(() => courses.value.find((item) => item.title === subject.value)?.id ?? null);
const stageHistory = computed(() => detail.value?.stage_history ?? []);
const finalDimensions = computed(() => detail.value?.profile?.final_portrait_dimensions ?? []);
const termSummary = computed(() => detail.value?.profile?.term_summary ?? {});
const recommendationClosure = computed(() => detail.value?.recommendation_closure ?? {});
const selectedStudent = computed(() => students.value.find((item) => item.user_id === selectedUserId.value) ?? null);
const canConfirmFinalScore = computed(() => Number(termSummary.value?.stage_count || 0) > 0);

function toPercent(value?: number | null) {
  return Math.round(Number(value || 0) * 100);
}

function syncFormFromDetail() {
  const confirmation = detail.value?.final_score_confirmation;
  form.confirmedScorePercent = confirmation ? toPercent(confirmation.confirmed_score) : toPercent(termSummary.value?.final_score_reference);
  form.confirmedLevel = confirmation?.confirmed_level || "";
  form.recommendationSummary = confirmation?.recommendation_summary || recommendationClosure.value?.final_summary || "";
  form.comment = confirmation?.comment || termSummary.value?.final_reason_summary || "";
}

async function loadCourses() {
  try {
    const res = await api.get("/graph/courses");
    courses.value = res.data ?? [];
    subject.value = resolveTeacherSubject(String(route.query.subject || ""), subject.value, courses.value);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载课程失败");
  }
}

function syncQuery() {
  saveTeacherSubject(subject.value);
  const routeUserId = String(route.query.user_id || "").trim();
  router.replace({
    path: "/teacher/review",
    query: {
      ...buildTeacherSubjectQuery(subject.value, {
        user_id: selectedUserId.value ? String(selectedUserId.value) : routeUserId || undefined,
      }),
      tab: "final",
    },
  });
}

async function loadStudents() {
  if (!subject.value) return;
  listLoading.value = true;
  try {
    const res = await api.get(`/admin/final-score/students?subject=${encodeURIComponent(subject.value)}&grade=${encodeURIComponent(grade.value)}`);
    students.value = res.data?.items ?? [];
    const queryUserId = Number(route.query.user_id);
    if (Number.isFinite(queryUserId) && students.value.some((item) => item.user_id === queryUserId)) {
      selectedUserId.value = queryUserId;
    } else if (!selectedUserId.value && students.value.length) {
      selectedUserId.value = students.value[0].user_id;
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载最终评分列表失败");
  } finally {
    listLoading.value = false;
  }
}

async function loadDetail() {
  if (!selectedUserId.value || !subject.value) {
    detail.value = null;
    return;
  }
  detailLoading.value = true;
  try {
    const res = await api.get(
      `/admin/final-score/detail?user_id=${selectedUserId.value}&subject=${encodeURIComponent(subject.value)}&grade=${encodeURIComponent(grade.value)}`
    );
    detail.value = res.data;
    syncFormFromDetail();
  } catch (e: any) {
    detail.value = null;
    ElMessage.error(e?.response?.data?.detail ?? "加载评分确认详情失败");
  } finally {
    detailLoading.value = false;
  }
}

async function saveConfirmation() {
  if (!selectedUserId.value || !subject.value) {
    ElMessage.warning("请先选择课程和学生");
    return;
  }
  saving.value = true;
  try {
    await api.put("/admin/final-score/confirm", {
      user_id: selectedUserId.value,
      subject: subject.value,
      grade: grade.value,
      confirmed_score: Math.max(0, Math.min(100, Number(form.confirmedScorePercent || 0))) / 100,
      confirmed_level: form.confirmedLevel,
      recommendation_summary: form.recommendationSummary,
      comment: form.comment,
    });
    ElMessage.success("最终评分已确认并归档");
    await loadStudents();
    await loadDetail();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存最终评分失败");
  } finally {
    saving.value = false;
  }
}

watch(selectedCourseId, async () => {
  await loadStudents();
  await loadDetail();
});

watch(subject, () => {
  syncQuery();
});

watch(
  () => route.query.subject,
  (value) => {
    const next = String(value || "").trim();
    if (next && next !== subject.value) subject.value = next;
  }
);

watch(selectedUserId, async (value) => {
  syncQuery();
  await loadDetail();
});

onMounted(async () => {
  await loadCourses();
  await loadStudents();
  await loadDetail();
});
</script>

<template>
  <div class="final-review-page">
    <WorkspaceTopbar
      v-model="subject"
      :courses="courses"
      badge="Teacher Final Review"
      title="老师最终评分确认页"
      subtitle="按学期阶段趋势、期末雷达图和推荐收口情况，给出老师最终确认分。"
      :meta-text="`当前课程：${subject || '未选择'}，已确认 ${students.filter((item) => item.confirmed_score != null).length}/${students.length}`"
    >
      <el-button @click="router.push({ path: '/teacher/workspace', query: buildTeacherSubjectQuery(subject) })">返回课程工作台</el-button>
      <HintButton tip="单独处理课程报名审核。" @click="router.push({ path: '/teacher/review', query: { ...buildTeacherSubjectQuery(subject), tab: 'enrollment' } })">
        去报名审核页
      </HintButton>
      <el-button type="primary" @click="loadDetail">刷新详情</el-button>
    </WorkspaceTopbar>

    <div class="final-review-layout">
      <aside class="final-review-sidebar panel-card" v-loading="listLoading">
        <div class="sidebar-head">
          <div>
            <div class="sidebar-head__eyebrow">Student List</div>
            <div class="sidebar-head__title">学生名单</div>
            <div class="sidebar-head__subtitle">先选学生，再确认期末成绩。</div>
          </div>
        </div>
        <div class="student-list">
          <button
            v-for="item in students"
            :key="item.user_id"
            class="student-item"
            :class="{ active: item.user_id === selectedUserId }"
            @click="selectedUserId = item.user_id"
          >
            <div class="student-item__main">
              <strong>{{ item.full_name || item.username }}</strong>
              <span>{{ item.persona_label }} · {{ item.risk_level }}</span>
            </div>
            <div class="student-item__meta">
              <span>建议 {{ toPercent(item.suggested_score) }}%</span>
              <span v-if="item.confirmed_score != null">已确认 {{ toPercent(item.confirmed_score) }}%</span>
            </div>
          </button>
        </div>
      </aside>

      <main class="final-review-main" v-loading="detailLoading">
        <template v-if="detail">
          <section class="detail-grid">
            <el-card class="panel-card" shadow="never">
              <template #header>期末画像雷达图</template>
              <PortraitRadarChart
                :items="finalDimensions"
                title="学期最终五维结果"
                subtitle="系统根据各阶段快照汇总得到的期末结果"
                accent="#2f7a6d"
              />
            </el-card>

            <el-card class="panel-card" shadow="never">
              <template #header>最终评分确认</template>
              <div class="confirm-form">
                <div class="confirm-form__row">
                  <label>学生</label>
                  <div>{{ detail.student?.full_name || detail.student?.username }}</div>
                </div>
                <div class="confirm-form__row">
                  <label>确认分</label>
                  <el-input-number v-model="form.confirmedScorePercent" :min="0" :max="100" :step="1" />
                </div>
                <div class="confirm-form__row">
                  <label>等级</label>
                  <el-select v-model="form.confirmedLevel" placeholder="选择等级">
                    <el-option v-for="item in levelOptions" :key="item" :label="item" :value="item" />
                  </el-select>
                </div>
                <div class="confirm-form__row confirm-form__row--stack">
                  <label>推荐链路收口说明</label>
                  <el-input v-model="form.recommendationSummary" type="textarea" :rows="3" placeholder="总结推荐链路最后收口情况" />
                </div>
                <div class="confirm-form__row confirm-form__row--stack">
                  <label>老师确认说明</label>
                  <el-input v-model="form.comment" type="textarea" :rows="4" placeholder="填写最终评分依据、教学观察或补充说明" />
                </div>
                <div class="confirm-form__actions">
                  <el-button type="primary" :loading="saving" :disabled="!canConfirmFinalScore" @click="saveConfirmation">确认并归档</el-button>
                  <el-button @click="router.push({ path: '/teacher/students', query: buildTeacherSubjectQuery(subject, { tab: 'detail', user_id: String(selectedUserId || '') || undefined }) })">
                    打开学生详情
                  </el-button>
                </div>
                <div v-if="!canConfirmFinalScore" class="empty-text">该学生还没有阶段评价数据，暂时不能确认期末成绩。</div>
              </div>
            </el-card>
          </section>

          <section class="detail-grid">
            <el-card class="panel-card" shadow="never">
              <template #header>阶段变化趋势</template>
              <div v-if="stageHistory.length === 0" class="empty-text">暂无阶段数据</div>
              <div v-else class="timeline-list">
                <div v-for="item in stageHistory" :key="item.stage_id" class="timeline-item">
                  <div class="timeline-item__title">{{ item.stage_order }}. {{ item.stage_title }}</div>
                  <div class="timeline-item__meta">
                    动态评分 {{ toPercent(item.dynamic_score) }}% · 掌握度 {{ toPercent(item.course_mastery) }}% · {{ item.trend_label }}
                  </div>
                  <div class="timeline-item__desc">{{ item.reason_summary }}</div>
                </div>
              </div>
            </el-card>

            <el-card class="panel-card" shadow="never">
              <template #header>推荐链路最后收口</template>
              <div class="closure-panel">
                <div class="closure-panel__item">
                  <span>最后一次推荐时间</span>
                  <strong>{{ recommendationClosure.latest_created_at ? recommendationClosure.latest_created_at.replace("T", " ").slice(0, 16) : "暂无" }}</strong>
                </div>
                <div class="closure-panel__item">
                  <span>最后推荐目标</span>
                  <strong>{{ recommendationClosure.latest_target_kp_id || "暂无" }}</strong>
                </div>
                <div class="closure-panel__item closure-panel__item--wide">
                  <span>系统推荐结论</span>
                  <strong>{{ recommendationClosure.latest_reason_summary || "暂无推荐结果" }}</strong>
                </div>
                <div class="closure-panel__item closure-panel__item--wide">
                  <span>当前收口摘要</span>
                  <strong>{{ recommendationClosure.final_summary || "尚未填写收口摘要" }}</strong>
                </div>
              </div>
            </el-card>
          </section>
        </template>

        <el-card v-else class="panel-card empty-card" shadow="never">
          <div></div>
        </el-card>
      </main>
    </div>
  </div>
</template>

<style scoped>
.final-review-page {
  display: grid;
  gap: 16px;
}

.panel-card {
  border: 3px solid #1f2937;
  border-radius: 32px;
  background:
    radial-gradient(circle at top left, rgba(201, 237, 255, 0.22), transparent 24%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
}

.final-review-layout {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 16px;
}

.final-review-sidebar {
  padding: 18px;
  border: 3px solid #1f2937;
  background:
    radial-gradient(circle at top left, rgba(201, 237, 255, 0.22), transparent 24%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
}

.sidebar-head__eyebrow {
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 800;
  color: #5d8666;
}

.sidebar-head__title {
  margin-top: 8px;
  font-size: 22px;
  font-weight: 800;
  color: #1f5130;
}

.sidebar-head__subtitle {
  display: none;
}

.student-list {
  margin-top: 14px;
  display: grid;
  gap: 10px;
}

.student-item {
  border: 1.5px solid #c6d8ef;
  border-radius: 22px;
  padding: 14px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  display: grid;
  gap: 8px;
  text-align: left;
  cursor: pointer;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
}

.student-item.active {
  border-color: rgba(78, 138, 96, 0.48);
  background: linear-gradient(180deg, rgba(223, 243, 227, 0.98), rgba(243, 250, 245, 0.98));
  box-shadow: 0 14px 30px rgba(42, 109, 61, 0.12);
}

.student-item__main,
.student-item__meta {
  display: grid;
  gap: 4px;
}

.student-item strong {
  color: #1f5130;
}

.student-item span {
  color: #5b715e;
  font-size: 13px;
}

.final-review-main {
  display: grid;
  gap: 16px;
}

.detail-grid {
  display: grid;
  gap: 16px;
}

.detail-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.confirm-form {
  display: grid;
  gap: 14px;
}

.confirm-form__row {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr);
  align-items: center;
  gap: 12px;
}

.confirm-form__row--stack {
  grid-template-columns: 1fr;
}

.confirm-form__row label {
  font-size: 13px;
  color: #5b715e;
  font-weight: 700;
}

.confirm-form__actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.timeline-list {
  display: grid;
  gap: 12px;
}

.timeline-item {
  border: 1.5px solid #c6d8ef;
  border-radius: 22px;
  padding: 14px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
}

.timeline-item__title {
  font-weight: 700;
  color: #1f5130;
}

.timeline-item__meta,
.timeline-item__desc {
  margin-top: 6px;
  color: #5b715e;
  font-size: 13px;
  line-height: 1.6;
}

.closure-panel {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.closure-panel__item {
  border: 1.5px solid #c6d8ef;
  border-radius: 22px;
  padding: 14px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  display: grid;
  gap: 8px;
}

.closure-panel__item--wide {
  grid-column: 1 / -1;
}

.closure-panel__item span {
  color: #5b715e;
  font-size: 13px;
}

.closure-panel__item strong {
  color: #1f5130;
  line-height: 1.7;
}

.empty-card,
.empty-text {
  color: #5b715e;
}

.final-review-page :deep(.el-card__header) {
  padding: 24px 24px 0;
  border-bottom: none;
  color: #1f5130;
  font-weight: 800;
}

.final-review-page :deep(.el-card__body) {
  padding: 20px 24px 24px;
}

.final-review-page :deep(.el-select__wrapper),
.final-review-page :deep(.el-textarea__inner),
.final-review-page :deep(.el-input__wrapper),
.final-review-page :deep(.el-input-number),
.final-review-page :deep(.el-input-number .el-input__wrapper) {
  border-radius: 18px;
  box-shadow: 0 0 0 1px rgba(140, 173, 149, 0.3) inset;
  background: rgba(245, 250, 246, 0.96);
}

.final-review-page :deep(.el-button--primary) {
  border-color: rgba(51, 122, 71, 0.8);
  background: linear-gradient(135deg, #2f7a45, #2aa887);
}

.final-review-page :deep(.el-button:not(.el-button--primary)) {
  border-radius: 999px;
}

@media (max-width: 1100px) {
  .final-review-layout,
  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
