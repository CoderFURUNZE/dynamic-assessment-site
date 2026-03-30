<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";

type EnrollableCourse = {
  id: number;
  code: string;
  title: string;
  description: string;
  teacher_name?: string;
  max_students: number;
  enrolled_count: number;
  apply_deadline?: string | null;
  enroll_status: string;
  application_status?: string | null;
  enrollment_mode?: string;
  target_class?: string | null;
  lifecycle_status?: string;
  start_at?: string | null;
  end_at?: string | null;
};

type CourseApplication = {
  id: number;
  course_title: string;
  status: string;
  apply_reason: string;
  review_remark: string;
  reject_reason: string;
  created_at: string;
  reviewed_at?: string | null;
};

type Notice = {
  id: number;
  title: string;
  content: string;
  status: string;
  created_at: string;
};

const router = useRouter();
const route = useRoute();
const loading = ref(false);
const applying = ref<number | null>(null);
const courses = ref<EnrollableCourse[]>([]);
const applications = ref<CourseApplication[]>([]);
const notices = ref<Notice[]>([]);
const applyReasonMap = ref<Record<number, string>>({});
const joinCodeInput = ref("");
const joinByCodeLoading = ref(false);

function normalizeStatus(status?: string | null) {
  return String(status || "").trim().toLowerCase();
}

function statusLabel(status: string) {
  const value = normalizeStatus(status);
  if (value === "open") return "可报名";
  if (value === "full") return "已满";
  if (value === "closed") return "已关闭";
  if (value === "expired") return "已过期";
  return status;
}

function appStatusLabel(status?: string | null) {
  const value = normalizeStatus(status);
  if (!value) return "未报名";
  if (value === "pending") return "审核中";
  if (value === "approved") return "已通过";
  if (value === "linked") return "已自动关联";
  if (value === "rejected") return "已拒绝";
  return status;
}

function autoJoinHint(course: EnrollableCourse) {
  if (normalizeStatus(course.application_status) === "linked") return "系统已按班级自动关联，你可以直接进入课程学习。";
  if (normalizeStatus(course.application_status) === "approved") return "已进入课程";
  if (normalizeStatus(course.application_status) === "pending") return "等待老师确认";
  if (normalizeStatus(course.lifecycle_status) === "archived") return "课程已归档，当前只保留查看记录。";
  if (normalizeStatus(course.lifecycle_status) === "draft") return "课程还未正式开课，开课后会自动开放。";
    if (normalizeStatus(course.enrollment_mode) === "class_auto") return `系统会按班级 ${course.target_class || ""} 自动关联；也可使用课程代码加入。`;
  if (normalizeStatus(course.enroll_status) !== "open") return "当前不在开放加入时间";
  return "优先使用课程代码或与班级一致自动关联；「申请加入」仅为无法自动匹配时的备选。";
}

async function loadAll() {
  loading.value = true;
  try {
    const [courseRes, appRes, noticeRes] = await Promise.all([
      api.get("/enrollment/courses/enrollable"),
      api.get("/enrollment/my/applications"),
      api.get("/enrollment/my/notifications"),
    ]);
    courses.value = courseRes.data?.items ?? [];
    applications.value = appRes.data?.items ?? [];
    notices.value = noticeRes.data?.items ?? [];
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载报名数据失败");
  } finally {
    loading.value = false;
  }
}

async function joinByCourseCode() {
  const code = joinCodeInput.value.trim();
  if (!code) {
    ElMessage.warning("请输入管理员或教师公布的课程代码");
    return;
  }
  joinByCodeLoading.value = true;
  try {
    const res = await api.post("/enrollment/courses/join-by-code", { join_code: code });
    const title = res.data?.title || "";
    if (res.data?.already_enrolled) {
      ElMessage.success(title ? `你已在课程《${title}》中` : "你已在该课程中");
    } else {
      ElMessage.success(title ? `已加入《${title}》，可直接学习` : "加入成功");
    }
    joinCodeInput.value = "";
    await loadAll();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加入失败");
  } finally {
    joinByCodeLoading.value = false;
  }
}

async function applyCourse(course: EnrollableCourse) {
  if (course.application_status) {
    ElMessage.warning(`当前状态：${appStatusLabel(course.application_status)}`);
    return;
  }
  applying.value = course.id;
  try {
    await api.post(`/enrollment/courses/${course.id}/apply`, {
      apply_reason: applyReasonMap.value[course.id] || "",
    });
    ElMessage.success("报名已提交，等待老师审核");
    await loadAll();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "报名失败");
  } finally {
    applying.value = null;
  }
}

async function markRead(noticeId: number) {
  try {
    await api.post(`/enrollment/my/notifications/${noticeId}/read`);
    notices.value = notices.value.map((item) => (item.id === noticeId ? { ...item, status: "READ" } : item));
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "更新通知失败");
  }
}

function goBackStudy() {
  const preview = String(route.query.preview || "");
  router.push({
    path: "/student/overview",
    query: preview ? { preview } : undefined,
  });
}

onMounted(loadAll);
</script>

<template>
  <div class="enroll-page" v-loading="loading">
    <header class="enroll-header panel-card">
      <div>
        <div class="enroll-kicker">课程关联</div>
        <h1>课程加入与通知</h1>
        <p class="enroll-lead">
          校内教学默认由<strong>管理员导入师生信息</strong>；同班学生可按「目标班级」自动关联课程。也可使用管理员公布的<strong>课程代码</strong>自助加入，无需教师逐人审核。
        </p>
      </div>
      <div class="enroll-header__actions">
        <el-button @click="goBackStudy">返回学习中心</el-button>
        <el-button type="primary" @click="loadAll">刷新</el-button>
      </div>
    </header>

    <section class="panel-card block join-code-block">
      <div class="block__head">
        <h3>通过课程代码加入</h3>
        <span class="block__hint">代码与管理员在「课程」里设置的课程编码一致；仅限开课中且在周期内的课程。</span>
      </div>
      <div class="join-code-row">
        <el-input v-model="joinCodeInput" placeholder="例如课程编码 CS101-2025" clearable style="max-width: 320px" />
        <el-button type="primary" :loading="joinByCodeLoading" @click="joinByCourseCode">加入课程</el-button>
      </div>
    </section>

    <section class="panel-card block">
      <div class="block__head">
        <h3>课程关联结果</h3>
      </div>
      <div class="enroll-list">
        <div v-for="course in courses" :key="course.id" class="enroll-item">
          <div class="enroll-item__main">
            <strong>{{ course.title }}</strong>
            <span>{{ course.code }} · {{ course.teacher_name || "未分配老师" }}</span>
            <span>名额 {{ course.enrolled_count }}/{{ course.max_students }} · {{ statusLabel(course.enroll_status) }}</span>
            <span v-if="course.apply_deadline">截止：{{ course.apply_deadline.replace("T", " ").slice(0, 16) }}</span>
            <span>教学状态：{{ course.lifecycle_status === "active" ? "开课中" : course.lifecycle_status === "archived" ? "已归档" : "待开课" }}</span>
            <span v-if="course.target_class">目标班级：{{ course.target_class }}</span>
            <span v-if="course.start_at || course.end_at">开课周期：{{ course.start_at ? course.start_at.replace("T", " ").slice(0, 16) : "未设置" }} ~ {{ course.end_at ? course.end_at.replace("T", " ").slice(0, 16) : "未设置" }}</span>
            <span>当前报名状态：{{ appStatusLabel(course.application_status) }}</span>
            <span>{{ autoJoinHint(course) }}</span>
          </div>
          <div class="enroll-item__actions">
            <el-input
              v-model="applyReasonMap[course.id]"
              placeholder="可填写报名理由（选填）"
              style="width: 260px"
              :disabled="!!course.application_status || normalizeStatus(course.enrollment_mode) === 'class_auto'"
            />
            <el-button
              type="primary"
              plain
              :loading="applying === course.id"
              :disabled="!!course.application_status || normalizeStatus(course.enroll_status) !== 'open' || normalizeStatus(course.enrollment_mode) === 'class_auto'"
              @click="applyCourse(course)"
            >
              {{ normalizeStatus(course.enrollment_mode) === "class_auto" ? "自动关联课程" : "申请加入（备选）" }}
            </el-button>
          </div>
        </div>
      </div>
    </section>

    <section class="panel-card block">
      <div class="block__head">
        <h3>我的报名记录</h3>
      </div>
      <el-table :data="applications" size="small">
        <el-table-column prop="course_title" label="课程" min-width="180" />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column prop="apply_reason" label="报名理由" min-width="180" />
        <el-table-column prop="review_remark" label="审核备注" min-width="160" />
        <el-table-column prop="reject_reason" label="拒绝原因" min-width="180" />
        <el-table-column prop="created_at" label="提交时间" width="170">
          <template #default="{ row }">{{ row.created_at.replace("T", " ").slice(0, 16) }}</template>
        </el-table-column>
      </el-table>
    </section>

    <section class="panel-card block">
      <div class="block__head">
        <h3>站内通知</h3>
      </div>
      <div v-if="notices.length === 0" class="empty">暂无通知</div>
      <div v-else class="notice-list">
        <div v-for="notice in notices" :key="notice.id" class="notice-item">
          <div>
            <strong>{{ notice.title }}</strong>
            <p>{{ notice.content }}</p>
            <small>{{ notice.created_at.replace("T", " ").slice(0, 16) }}</small>
          </div>
          <el-button size="small" :disabled="normalizeStatus(notice.status) === 'read'" @click="markRead(notice.id)">
            {{ normalizeStatus(notice.status) === "read" ? "已读" : "标记已读" }}
          </el-button>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.enroll-page { display: grid; gap: 18px; padding: 18px; }
.panel-card {
  border-radius: var(--app-radius-lg);
  padding: 20px;
}
.enroll-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
}
.enroll-kicker { font-size: 12px; letter-spacing: .08em; text-transform: uppercase; color: #6d87ab; font-weight: 800; }
.enroll-header h1 { margin: 8px 0; font-size: 30px; line-height: 1.15; color: #24374f; }
.enroll-lead { margin: 0; max-width: 720px; font-size: 14px; line-height: 1.65; color: #5a6f86; }
.join-code-block .block__head {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
}
.block__hint { font-size: 13px; color: #6f829b; font-weight: 500; }
.join-code-row { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
.enroll-header__actions { display: flex; gap: 8px; flex-wrap: wrap; }
.block { display: grid; gap: 14px; }
.block__head h3 { margin: 0; color: #24374f; font-size: 18px; }
.enroll-list, .notice-list { display: grid; gap: 12px; }
.enroll-item, .notice-item {
  border: 1px solid var(--app-border);
  border-radius: 16px;
  padding: 16px;
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: center;
  background: #fcfdff;
}
.enroll-item__main { display: grid; gap: 6px; }
.enroll-item__main strong { color: #253d58; font-size: 16px; }
.enroll-item__main span, .notice-item p, .notice-item small { color: #6f829b; margin: 0; line-height: 1.6; }
.enroll-item__actions { display: flex; gap: 8px; align-items: center; }
.empty { color: #7c8da2; padding: 4px 0; }
@media (max-width: 980px) {
  .enroll-header, .enroll-item, .notice-item { flex-direction: column; align-items: flex-start; }
  .enroll-item__actions { width: 100%; flex-direction: column; align-items: stretch; }
}
</style>
