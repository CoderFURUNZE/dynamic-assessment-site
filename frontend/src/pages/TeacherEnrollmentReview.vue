<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { CircleCheck, Clock, CloseBold, DocumentChecked } from "@element-plus/icons-vue";
import { api } from "../api";
import WorkspaceTopbar from "../components/WorkspaceTopbar.vue";
import HintButton from "../components/HintButton.vue";
import { buildTeacherSubjectQuery, resolveTeacherSubject, saveTeacherSubject } from "../utils/teacherCourse";

type CourseItem = { id: number; code: string; title: string };
type ReviewRow = {
  id: number;
  course_id: number;
  course_title: string;
  student_id: number;
  student_name: string;
  status: string;
  apply_reason: string;
  review_remark: string;
  reject_reason: string;
  created_at: string;
};

type StatusFilter = "pending" | "approved" | "rejected" | "all";

const route = useRoute();
const router = useRouter();
const grade = ref("通用");
const subject = ref("");
const courses = ref<CourseItem[]>([]);
const loading = ref(false);
const processingId = ref<number | null>(null);
const rows = ref<ReviewRow[]>([]);
const activeStatus = ref<StatusFilter>("pending");

const selectedCourseId = computed<number | null>(() => courses.value.find((item) => item.title === subject.value)?.id ?? null);

const activeStatusLabel = computed(() => {
  if (activeStatus.value === "pending") return "待审核";
  if (activeStatus.value === "approved") return "已通过";
  if (activeStatus.value === "rejected") return "已拒绝";
  return "全部申请";
});

const metaText = computed(() => `当前课程：${subject.value || "未选择"} · ${activeStatusLabel.value} ${rows.value.length} 条`);

const pendingCount = computed(() => rows.value.filter((item) => item.status === "pending").length);
const approvedCount = computed(() => rows.value.filter((item) => item.status === "approved").length);
const rejectedCount = computed(() => rows.value.filter((item) => item.status === "rejected").length);
const latestSubmittedAt = computed(() => {
  const latest = rows.value
    .map((item) => item.created_at)
    .filter(Boolean)
    .sort()
    .at(-1);
  return latest ? latest.replace("T", " ").slice(0, 16) : "暂无记录";
});

const summaryCards = computed(() => [
  { key: "pending", label: "待处理申请", value: pendingCount.value, tone: "warning", icon: Clock },
  { key: "approved", label: "已通过", value: approvedCount.value, tone: "success", icon: CircleCheck },
  { key: "rejected", label: "已拒绝", value: rejectedCount.value, tone: "danger", icon: CloseBold },
  { key: "latest", label: "最近提交", value: latestSubmittedAt.value, tone: "neutral", icon: DocumentChecked },
]);

const activeHelp = computed(() => {
  if (activeStatus.value === "pending") {
    return {
      title: "先处理待审核申请",
      text: "优先清空当前课程待审核队列，避免学生无法进入后续学习与评价流程。",
      action: "通过会创建选课关系；拒绝时需填写原因，系统会保留审核说明。",
    };
  }
  if (activeStatus.value === "approved") {
    return {
      title: "已通过记录用于复核",
      text: "这里保留已完成审核的申请，可核对学生进入课程后的最终名单。",
      action: "如需学期收口，请进入“最终评分确认”继续处理。",
    };
  }
  if (activeStatus.value === "rejected") {
    return {
      title: "拒绝记录用于说明与追踪",
      text: "查看历史拒绝原因，避免重复沟通，也便于后续重新提交时比对情况。",
      action: "若学生重新申请，需要重新提交报名理由并再次审核。",
    };
  }
  return {
    title: "查看该课程完整审核记录",
    text: "用于按课程复盘报名情况，快速定位高频原因、审核节奏和异常记录。",
    action: "建议先切回“待审核”处理，再用“全部申请”做阶段性复盘。",
  };
});

function statusLabel(status: string) {
  if (status === "pending") return "待审核";
  if (status === "approved") return "已通过";
  if (status === "rejected") return "已拒绝";
  return status;
}

function syncQuery() {
  saveTeacherSubject(subject.value);
  if (route.path === "/teacher/review" && String(route.query.subject || "") === subject.value && String(route.query.tab || "") === "enrollment") return;
  router.replace({ path: "/teacher/review", query: { ...buildTeacherSubjectQuery(subject.value), tab: "enrollment" } });
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

async function loadRows() {
  if (!selectedCourseId.value) {
    rows.value = [];
    return;
  }
  const statusPart = activeStatus.value !== "all" ? `&status=${encodeURIComponent(activeStatus.value)}` : "";
  loading.value = true;
  try {
    const res = await api.get(`/enrollment/teacher/applications?course_id=${selectedCourseId.value}${statusPart}`);
    rows.value = res.data?.items ?? [];
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载报名审核列表失败");
  } finally {
    loading.value = false;
  }
}

async function approve(row: ReviewRow) {
  processingId.value = row.id;
  try {
    await api.post(`/enrollment/teacher/applications/${row.id}/approve`, {
      review_remark: "审核通过，可进入课程学习",
    });
    ElMessage.success("已审核通过");
    await loadRows();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "审核通过失败");
  } finally {
    processingId.value = null;
  }
}

async function reject(row: ReviewRow) {
  try {
    const { value } = await ElMessageBox.prompt("请输入拒绝原因", "拒绝报名", {
      confirmButtonText: "提交",
      cancelButtonText: "取消",
      inputPlaceholder: "例如：建议先补完前置课程",
      inputValidator: (v) => (String(v || "").trim() ? true : "拒绝原因不能为空"),
    });
    processingId.value = row.id;
    await api.post(`/enrollment/teacher/applications/${row.id}/reject`, {
      reject_reason: String(value || "").trim(),
      review_remark: "本次报名未通过，请根据建议调整后再次申请",
    });
    ElMessage.success("已拒绝该报名申请");
    await loadRows();
  } catch (e: any) {
    if (e === "cancel") return;
    ElMessage.error(e?.response?.data?.detail ?? "审核拒绝失败");
  } finally {
    processingId.value = null;
  }
}

watch(selectedCourseId, () => loadRows());
watch(activeStatus, () => loadRows());
watch(subject, () => syncQuery());
watch(
  () => route.query.subject,
  (value) => {
    const next = String(value || "").trim();
    if (next && next !== subject.value) subject.value = next;
  }
);

onMounted(async () => {
  await loadCourses();
  await loadRows();
});
</script>

<template>
  <div class="review-page">
    <WorkspaceTopbar
      v-model="subject"
      :courses="courses"
      badge="Enrollment Review"
      title="报名审核与准入管理"
      subtitle="按课程统一处理学生报名申请，保持准入规则、审核记录和后续学习链路一致。"
      :meta-text="metaText"
    >
      <el-button @click="router.push({ path: '/teacher/workspace', query: buildTeacherSubjectQuery(subject) })">返回课程工作台</el-button>
      <HintButton tip="切换到学期收口页，继续处理最终评分确认。" @click="router.push({ path: '/teacher/review', query: { ...buildTeacherSubjectQuery(subject), tab: 'final' } })">
        最终评分确认
      </HintButton>
      <el-button type="primary" @click="loadRows">刷新列表</el-button>
    </WorkspaceTopbar>

    <section class="review-overview panel-card">
      <div class="review-overview__hero">
        <div>
          <span class="section-eyebrow">审核总览</span>
          <h2>让审核队列清晰、节奏稳定</h2>
          <p>{{ activeHelp.text }}</p>
        </div>
        <div class="review-overview__badges">
          <span>{{ subject || "未选择课程" }}</span>
          <span>{{ grade }}</span>
          <span>{{ activeStatusLabel }}</span>
        </div>
      </div>

      <div class="summary-grid">
        <article v-for="item in summaryCards" :key="item.key" class="summary-card" :class="`summary-card--${item.tone}`">
          <div class="summary-card__icon">
            <el-icon><component :is="item.icon" /></el-icon>
          </div>
          <div class="summary-card__body">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </article>
      </div>

      <div class="review-help">
        <strong>{{ activeHelp.title }}</strong>
        <span>{{ activeHelp.action }}</span>
      </div>
    </section>

    <el-card class="panel-card review-table-card" shadow="never">
      <template #header>
        <div class="review-toolbar">
          <div>
            <span class="section-eyebrow">审核列表</span>
            <h3>按状态筛选并处理申请</h3>
          </div>

          <div class="review-filter">
            <button
              v-for="item in [
                { label: '待审核', value: 'pending' },
                { label: '已通过', value: 'approved' },
                { label: '已拒绝', value: 'rejected' },
                { label: '全部申请', value: 'all' },
              ]"
              :key="item.value"
              type="button"
              class="filter-chip"
              :class="{ active: activeStatus === item.value }"
              @click="activeStatus = item.value as StatusFilter"
            >
              {{ item.label }}
            </button>
          </div>
        </div>
      </template>

      <el-table :data="rows" v-loading="loading" size="large" style="width: 100%">
        <el-table-column prop="student_name" label="学生" min-width="120" />
        <el-table-column prop="course_title" label="课程" min-width="160" />
        <el-table-column prop="status" label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.status === 'approved' ? 'success' : row.status === 'rejected' ? 'danger' : 'warning'" effect="light">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="apply_reason" label="报名理由" min-width="220" show-overflow-tooltip />
        <el-table-column prop="review_remark" label="审核备注" min-width="220" show-overflow-tooltip />
        <el-table-column prop="reject_reason" label="拒绝原因" min-width="220" show-overflow-tooltip />
        <el-table-column prop="created_at" label="提交时间" width="170">
          <template #default="{ row }">{{ row.created_at.replace("T", " ").slice(0, 16) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <div class="review-actions">
              <el-button size="small" type="success" :disabled="row.status !== 'pending'" :loading="processingId === row.id" @click="approve(row)">
                通过
              </el-button>
              <el-button size="small" plain type="danger" :disabled="row.status !== 'pending'" :loading="processingId === row.id" @click="reject(row)">
                拒绝
              </el-button>
              <el-button size="small" @click="router.push({ path: '/teacher/students', query: buildTeacherSubjectQuery(subject, { tab: 'detail', user_id: String(row.student_id) }) })">
                学生详情
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.review-page {
  display: grid;
  gap: 18px;
}

.panel-card {
  border-radius: 20px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background:
    radial-gradient(circle at top right, rgba(191, 221, 254, 0.18), transparent 24%),
    radial-gradient(circle at top left, rgba(245, 158, 11, 0.08), transparent 22%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: 0 12px 26px rgba(15, 23, 42, 0.07);
}

.review-overview {
  display: grid;
  gap: 16px;
  padding: 20px;
}

.review-overview__hero,
.review-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.review-overview__hero h2,
.review-toolbar h3 {
  margin: 6px 0 0;
  color: #1f2937;
  font-size: 24px;
  line-height: 1.15;
}

.review-overview__hero p {
  margin: 8px 0 0;
  max-width: 60ch;
  color: #6a7280;
  line-height: 1.6;
}

.review-overview__badges,
.review-filter {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.review-overview__badges span,
.filter-chip,
.section-eyebrow {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
}

.review-overview__badges span {
  border: 1px solid rgba(191, 167, 132, 0.34);
  background: linear-gradient(180deg, #f8fbff 0%, #eef6ff 100%);
  color: #8a6740;
}

.section-eyebrow {
  width: fit-content;
  background: linear-gradient(180deg, #eef6dc 0%, #fff2db 100%);
  color: #586537;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.summary-card {
  display: flex;
  gap: 12px;
  padding: 16px;
  border-radius: 18px;
  border: 1px solid rgba(191, 167, 132, 0.24);
  background: linear-gradient(180deg, rgba(255, 252, 247, 0.96), rgba(255, 244, 229, 0.92));
}

.summary-card__icon {
  width: 40px;
  height: 40px;
  flex: 0 0 40px;
  display: grid;
  place-items: center;
  border-radius: 16px;
  background: #ffffff;
}

.summary-card__icon :deep(svg) {
  width: 20px;
  height: 20px;
}

.summary-card__body {
  display: grid;
  gap: 6px;
}

.summary-card__body span {
  color: #6a7280;
  font-size: 13px;
}

.summary-card__body strong {
  color: #1f2937;
  font-size: 22px;
  line-height: 1.1;
}

.summary-card--warning .summary-card__icon {
  color: #b45309;
  background: rgba(251, 191, 36, 0.16);
}

.summary-card--success .summary-card__icon {
  color: #15803d;
  background: rgba(134, 239, 172, 0.2);
}

.summary-card--danger .summary-card__icon {
  color: #b91c1c;
  background: rgba(252, 165, 165, 0.2);
}

.summary-card--neutral .summary-card__icon {
  color: #334155;
  background: rgba(191, 227, 245, 0.45);
}

.review-help {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
  padding: 16px 18px;
  border-radius: 22px;
  border: 1px solid rgba(191, 167, 132, 0.24);
  background: rgba(255, 252, 247, 0.82);
}

.review-help strong {
  color: #1f2937;
  font-size: 15px;
}

.review-help span {
  color: #6a7280;
  line-height: 1.7;
}

.review-table-card :deep(.el-card__header) {
  padding: 24px 24px 0;
  border-bottom: 0;
}

.review-table-card :deep(.el-card__body) {
  padding: 18px 24px 24px;
}

.filter-chip {
  border: 1px solid rgba(191, 167, 132, 0.3);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  color: #7c5e3d;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.filter-chip.active {
  color: #ffffff;
  border-color: rgba(31, 41, 55, 0.14);
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
  box-shadow: 0 10px 18px rgba(15, 23, 42, 0.08);
}

.review-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.review-table-card :deep(.el-table) {
  --el-table-header-bg-color: rgba(250, 243, 232, 0.94);
  --el-table-row-hover-bg-color: rgba(239, 246, 255, 0.72);
  border-radius: 20px;
  overflow: hidden;
}

.review-table-card :deep(.el-button--success) {
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
  border-color: #16a34a;
}

.review-table-card :deep(.el-button:not(.el-button--success):not(.el-button--danger)) {
  border-color: rgba(191, 167, 132, 0.3);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  color: #7c5e3d;
}

@media (max-width: 1080px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .review-overview,
  .review-table-card :deep(.el-card__body) {
    padding: 18px;
  }

  .review-table-card :deep(.el-card__header) {
    padding: 18px 18px 0;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .review-overview__hero h2,
  .review-toolbar h3 {
    font-size: 22px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .filter-chip {
    transition: none;
  }
}
</style>
