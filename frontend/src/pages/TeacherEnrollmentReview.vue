<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
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

const route = useRoute();
const router = useRouter();
const grade = ref("通用");
const subject = ref("");
const courses = ref<CourseItem[]>([]);
const loading = ref(false);
const processingId = ref<number | null>(null);
const rows = ref<ReviewRow[]>([]);
const activeStatus = ref<"pending" | "approved" | "rejected" | "all">("pending");

const selectedCourseId = computed<number | null>(() => courses.value.find((item) => item.title === subject.value)?.id ?? null);

const activeStatusLabel = computed(() => {
  if (activeStatus.value === "pending") return "待审核";
  if (activeStatus.value === "approved") return "已通过";
  if (activeStatus.value === "rejected") return "已拒绝";
  return "全部";
});

const metaText = computed(() => `当前课程：${subject.value || "未选择"}，${activeStatusLabel.value} ${rows.value.length} 条`);

const activeHelp = computed(() => {
  if (activeStatus.value === "pending") {
    return { title: "功能范围", text: "查看当前课程所有待审核报名申请，并对每条执行“通过/拒绝”。通过将创建 `Enrollment` 并推送通知；拒绝需要输入拒绝原因并推送通知。", action: "优先从列表顶部处理待审核项。" };
  }
  if (activeStatus.value === "approved") {
    return { title: "功能范围", text: "查看已通过的报名申请记录（只做审核结果回顾）。", action: "如需继续处理期末收口，请使用顶部按钮前往最终评分确认。" };
  }
  if (activeStatus.value === "rejected") {
    return { title: "功能范围", text: "查看已拒绝的报名申请记录（只做审核结果回顾）。", action: "如果学生后续再次申请，需要重新提交报名理由并等待本页审核。" };
  }
  return { title: "功能范围", text: "查看该课程报名申请的全量记录（包含待审核/已通过/已拒绝），用于复盘与排查。", action: "通过状态筛选可以更快定位需要处理的记录。" };
});
function statusLabel(status: string) {
  if (status === "pending") return "待审核";
  if (status === "approved") return "已通过";
  if (status === "rejected") return "已拒绝";
  return status;
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
  router.replace({ path: "/teacher/review", query: { ...buildTeacherSubjectQuery(subject.value), tab: "enrollment" } });
}

async function loadRows() {
  if (!selectedCourseId.value) {
    rows.value = [];
    return;
  }
  const statusPart = activeStatus.value && activeStatus.value !== "all" ? `&status=${encodeURIComponent(activeStatus.value)}` : "";
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
      inputPlaceholder: "例如：建议先修完前置课程",
      inputValidator: (v) => (String(v || "").trim() ? true : "拒绝原因不能为空"),
    });
    processingId.value = row.id;
    await api.post(`/enrollment/teacher/applications/${row.id}/reject`, {
      reject_reason: String(value || "").trim(),
      review_remark: "本次未通过，请根据建议调整后再报名",
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
watch(() => route.query.subject, (value) => {
  const next = String(value || "").trim();
  if (next && next !== subject.value) subject.value = next;
});

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
      badge="Teacher Review"
      title="老师报名审核独立页"
      subtitle="这里单独处理课程报名，不再挤在课程管理弹窗里。"
      :meta-text="metaText"
    >
      <el-button @click="router.push({ path: '/teacher/workspace', query: buildTeacherSubjectQuery(subject) })">返回课程工作台</el-button>
      <HintButton tip="切到最终评分确认页，完成学期末收口。" @click="router.push({ path: '/teacher/review', query: { ...buildTeacherSubjectQuery(subject), tab: 'final' } })">
        去最终评分确认
      </HintButton>
      <el-button type="primary" @click="loadRows">刷新</el-button>
    </WorkspaceTopbar>

    <el-card class="panel-card" shadow="never">
      <template #header>
        <div class="review-head">
          <div>
            <div class="review-head__eyebrow">Enrollment Queue</div>
            <div class="review-head__title">报名申请列表</div>
          </div>
        </div>

        <div class="review-tabs-wrap">
          <el-tabs v-model="activeStatus" class="review-tabs">
            <el-tab-pane label="待审核" name="pending" />
            <el-tab-pane label="已通过" name="approved" />
            <el-tab-pane label="已拒绝" name="rejected" />
            <el-tab-pane label="全部" name="all" />
          </el-tabs>
        </div>

        <div class="review-help">
          <div class="review-help__title">{{ activeHelp.title }}</div>
          <div class="review-help__text">{{ activeHelp.text }}</div>
          <div class="review-help__action">{{ activeHelp.action }}</div>
        </div>
      </template>

      <el-table :data="rows" v-loading="loading" size="small">
        <el-table-column prop="student_name" label="学生" min-width="120" />
        <el-table-column prop="course_title" label="课程" min-width="160" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'approved' ? 'success' : row.status === 'rejected' ? 'danger' : 'warning'">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="apply_reason" label="报名理由" min-width="220" />
        <el-table-column prop="review_remark" label="审核备注" min-width="180" />
        <el-table-column prop="reject_reason" label="拒绝原因" min-width="180" />
        <el-table-column prop="created_at" label="提交时间" width="170">
          <template #default="{ row }">{{ row.created_at.replace("T", " ").slice(0, 16) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <div class="review-actions">
              <el-button
                size="small"
                type="success"
                :disabled="row.status !== 'pending'"
                :loading="processingId === row.id"
                @click="approve(row)"
              >
                通过
              </el-button>
              <el-button
                size="small"
                type="danger"
                plain
                :disabled="row.status !== 'pending'"
                :loading="processingId === row.id"
                @click="reject(row)"
              >
                拒绝
              </el-button>
              <el-button size="small" @click="router.push({ path: '/teacher/students', query: buildTeacherSubjectQuery(subject, { tab: 'detail', user_id: String(row.student_id) }) })">
                看学生详情
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
  gap: 16px;
}

.panel-card {
  border-radius: 20px;
}

.review-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.review-head__eyebrow {
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 800;
  color: #6c86ab;
}

.review-head__title {
  margin-top: 8px;
  font-size: 22px;
  font-weight: 800;
  color: #253d58;
}

.review-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.review-tabs-wrap {
  margin-top: 10px;
}

.review-tabs :deep(.el-tabs__nav) {
  margin: 0;
}

.review-help {
  margin-top: 12px;
  padding: 12px 14px;
  border: 1px solid var(--app-border);
  border-radius: 16px;
  background: #fafbfd;
  display: grid;
  gap: 6px;
}

.review-help__title {
  font-size: 13px;
  font-weight: 900;
  color: #24374f;
}

.review-help__text {
  font-size: 13px;
  color: #5a6f86;
  line-height: 1.6;
}

.review-help__action {
  font-size: 13px;
  color: #6a82a0;
  font-weight: 700;
}
</style>
