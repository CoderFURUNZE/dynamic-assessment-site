<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import AdminQuestionManager from "../components/AdminQuestionManager.vue";
import AdminEdgeManager from "../components/AdminEdgeManager.vue";
import AdminKpManager from "../components/AdminKpManager.vue";
import AdminPracticeReport from "../components/AdminPracticeReport.vue";
import AdminCourseManager from "../components/AdminCourseManager.vue";
import AdminPersonaManager from "../components/AdminPersonaManager.vue";
import AdminAnalyticsOverview from "../components/AdminAnalyticsOverview.vue";
import TeacherStudentDetail from "../components/TeacherStudentDetail.vue";
import TeacherStageManager from "../components/TeacherStageManager.vue";
import TeacherStageImport from "../components/TeacherStageImport.vue";
import TeacherIndicatorSelector from "../components/TeacherIndicatorSelector.vue";
import ExtensionPlaceholderCenter from "../components/ExtensionPlaceholderCenter.vue";
import { getRole } from "../token";

const role = ref(getRole());
const isTeacher = computed(() => role.value === "teacher");
const route = useRoute();
const router = useRouter();
const selectedStudentId = computed<number | null>(() => {
  const raw = route.query.user_id;
  const first = Array.isArray(raw) ? raw[0] : raw;
  const parsed = Number(first);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
});
const selectedCourseId = computed<number | null>(() => {
  const current = courses.value.find((item) => item.title === subject.value);
  return current?.id ?? null;
});

const subject = ref("");
const grade = ref("通用");
const courses = ref<Array<{ id: number; code: string; title: string }>>([]);
const kps = ref<Array<{ id: number; code: string; title: string }>>([]);
const selectedKpId = ref<number | null>(null);

const bilibili = ref({
  title: "",
  bvid: "BV1ct4y1t7pv",
  page: 1,
});
const localVideoTitle = ref("");
const localVideoUrl = ref("");
const localVideoFile = ref<File | null>(null);

const teacherTabs = [
  "courses",
  "stages",
  "imports",
  "indicators",
  "graph",
  "kps",
  "edges",
  "video",
  "questions",
  "analytics",
  "profiles",
  "students",
  "report",
  "extensions",
] as const;
const activeTab = computed<string>({
  get() {
    if (route.path === "/teacher/graph-workspace") return "graph";
    if (route.path.startsWith("/teacher/")) {
      const seg = route.path.split("/")[2];
      if ((teacherTabs as readonly string[]).includes(seg)) return seg;
    }
    return "courses";
  },
  set(value) {
    const safe = (teacherTabs as readonly string[]).includes(String(value)) ? String(value) : "courses";
    const target = `/teacher/${safe}`;
    if (route.path !== target) router.push(target);
  },
});

async function loadCourses() {
  try {
    const res = await api.get("/graph/courses");
    courses.value = res.data ?? [];
    if (!subject.value && courses.value.length) subject.value = courses.value[0].title;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载教师课程失败");
  }
}

async function loadKps() {
  if (!subject.value) return;
  try {
    const res = await api.get(`/graph/kps?subject=${encodeURIComponent(subject.value)}&grade=${encodeURIComponent(grade.value)}`);
    kps.value = res.data ?? [];
    if (!selectedKpId.value && kps.value.length) selectedKpId.value = kps.value[0].id;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载知识点失败");
  }
}

async function onSubjectChange() {
  selectedKpId.value = null;
  await loadKps();
}

function onLocalFileChange(file: any) {
  localVideoFile.value = file?.raw ?? null;
}

function openStudentDetail(userId: number) {
  router.push({
    path: "/teacher/students",
    query: { user_id: String(userId) },
  });
}

async function bindBilibili() {
  if (!selectedKpId.value) return ElMessage.warning("请选择知识点");
  if (!bilibili.value.bvid) return ElMessage.warning("请输入 bvid");
  try {
    const res = await api.put("/admin/kp-video/bilibili", {
      kp_id: selectedKpId.value,
      title: bilibili.value.title,
      bvid: bilibili.value.bvid,
      page: bilibili.value.page,
    });
    ElMessage.success(`已绑定：${res.data.url}`);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "绑定失败");
  }
}

async function clearVideo() {
  if (!selectedKpId.value) return;
  try {
    const res = await api.delete(`/admin/kp-video?kp_id=${selectedKpId.value}`);
    ElMessage.success(`已清除视频资源：${res.data.deleted}`);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "清除失败");
  }
}

async function uploadLocalVideo() {
  if (!selectedKpId.value) return ElMessage.warning("请选择知识点");
  if (!localVideoFile.value) return ElMessage.warning("请选择视频文件");
  const form = new FormData();
  form.append("kp_id", String(selectedKpId.value));
  if (localVideoTitle.value.trim()) form.append("title", localVideoTitle.value.trim());
  form.append("file", localVideoFile.value);
  try {
    const res = await api.post("/admin/kp-video/local", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    ElMessage.success(`已上传：${res.data.url}`);
    localVideoFile.value = null;
    localVideoTitle.value = "";
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "上传失败");
  }
}

async function bindLocalUrl() {
  if (!selectedKpId.value) return ElMessage.warning("请选择知识点");
  if (!localVideoUrl.value.trim()) return ElMessage.warning("请输入视频链接");
  try {
    const res = await api.put("/admin/kp-video/url", {
      kp_id: selectedKpId.value,
      title: localVideoTitle.value.trim(),
      url: localVideoUrl.value.trim(),
    });
    ElMessage.success(`已绑定：${res.data.url}`);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "绑定失败");
  }
}

onMounted(async () => {
  if (!isTeacher.value) {
    ElMessage.warning("仅教师可访问教师端");
    router.push("/login");
    return;
  }
  await loadCourses();
  await loadKps();
});
</script>

<template>
  <div v-if="isTeacher" class="teacher-shell">
    <el-card class="panel-card" shadow="never">
      <div class="teacher-topbar">
        <div class="teacher-topbar__left">
          <el-select v-model="subject" size="small" style="width: 220px" @change="onSubjectChange">
            <el-option v-for="c in courses" :key="c.id" :label="c.title" :value="c.title" />
          </el-select>
          <el-tag type="success">教师端</el-tag>
        </div>
        <el-button size="small" @click="router.push('/student/overview')">查看学生端效果</el-button>
      </div>
    </el-card>

    <el-tabs v-model="activeTab" type="border-card" class="dify-tabs">
      <el-tab-pane label="课程建设" name="courses">
        <AdminCourseManager />
      </el-tab-pane>

      <el-tab-pane label="阶段管理" name="stages">
        <TeacherStageManager :course-id="selectedCourseId" :subject="subject" :grade="grade" />
      </el-tab-pane>

      <el-tab-pane label="阶段数据导入" name="imports">
        <TeacherStageImport :course-id="selectedCourseId" :subject="subject" :grade="grade" />
      </el-tab-pane>

      <el-tab-pane label="画像指标选择" name="indicators">
        <TeacherIndicatorSelector :course-id="selectedCourseId" :subject="subject" />
      </el-tab-pane>

      <el-tab-pane label="图谱工作台" name="graph">
        <el-card class="panel-card teacher-graph-entry" shadow="never">
          <div class="teacher-graph-entry__hero">
            <div>
              <div class="teacher-graph-entry__kicker">Teacher Graph Workspace</div>
              <div class="teacher-graph-entry__title">进入教师知识图谱工作区</div>
              <div class="teacher-graph-entry__subtitle">
                参考学生端的独立图谱页，把知识点、关系、资源绑定放到全屏工作区里维护，不再挤在教师主页 tab 中间。
              </div>
            </div>
            <div class="teacher-graph-entry__actions">
              <div class="teacher-graph-entry__chip">当前课程：{{ subject || "未选择课程" }}</div>
              <el-button
                type="primary"
                size="large"
                @click="router.push({ path: '/teacher/graph-workspace', query: { subject: subject || undefined } })"
              >
                进入全屏图谱工作区
              </el-button>
            </div>
          </div>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="知识点管理" name="kps">
        <AdminKpManager :subject="subject" :grade="grade" />
      </el-tab-pane>

      <el-tab-pane label="知识图谱关系" name="edges">
        <AdminEdgeManager :subject="subject" :grade="grade" />
      </el-tab-pane>

      <el-tab-pane label="资源绑定" name="video">
        <el-card class="panel-card" shadow="never">
          <template #header>知识点视频资源</template>
          <el-form label-width="120px" size="small">
            <el-form-item label="知识点">
              <el-select v-model="selectedKpId" style="width: 100%" filterable @visible-change="loadKps">
                <el-option v-for="kp in kps" :key="kp.id" :label="`${kp.code} ${kp.title}`" :value="kp.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="B站 bvid">
              <el-input v-model="bilibili.title" placeholder="可选标题" style="width: 220px; margin-right: 8px" />
              <el-input v-model="bilibili.bvid" placeholder="例如 BV1ct4y1t7pv" style="width: 220px; margin-right: 8px" />
              <el-input-number v-model="bilibili.page" :min="1" :max="200" />
            </el-form-item>
            <el-form-item>
              <el-button type="success" @click="bindBilibili">绑定 B 站视频</el-button>
              <el-button type="danger" @click="clearVideo">清除视频</el-button>
            </el-form-item>
            <el-divider />
            <el-form-item label="本地上传">
              <el-upload :auto-upload="false" :show-file-list="true" :limit="1" @change="onLocalFileChange">
                <el-button>选择文件</el-button>
              </el-upload>
              <el-button type="success" style="margin-left: 8px" @click="uploadLocalVideo">上传并绑定</el-button>
            </el-form-item>
            <el-form-item label="标题(可选)">
              <el-input v-model="localVideoTitle" placeholder="本地视频标题" style="width: 320px" />
            </el-form-item>
            <el-form-item label="链接绑定">
              <el-input v-model="localVideoUrl" placeholder="可填 mp4 或 m3u8 地址" style="width: 320px" />
              <el-button type="primary" style="margin-left: 8px" @click="bindLocalUrl">绑定链接</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="题库与小测" name="questions">
        <AdminQuestionManager :subject="subject" :grade="grade" />
      </el-tab-pane>

      <el-tab-pane label="学习分析" name="analytics">
        <AdminAnalyticsOverview
          :subject="subject"
          :grade="grade"
          :show-student-detail-action="true"
          @view-student="openStudentDetail"
        />
      </el-tab-pane>

      <el-tab-pane label="画像查看" name="profiles">
        <AdminPersonaManager
          :subject="subject"
          :grade="grade"
          :show-student-detail-action="true"
          @view-student="openStudentDetail"
        />
      </el-tab-pane>

      <el-tab-pane label="单学生详情" name="students">
        <TeacherStudentDetail :subject="subject" :grade="grade" :initial-user-id="selectedStudentId" />
      </el-tab-pane>

      <el-tab-pane label="练习评价" name="report">
        <AdminPracticeReport />
      </el-tab-pane>

      <el-tab-pane label="扩展与答辩" name="extensions">
        <ExtensionPlaceholderCenter />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.teacher-shell {
  display: grid;
  gap: 16px;
}

.teacher-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.teacher-topbar__left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.teacher-graph-entry__hero {
  min-height: 280px;
  border-radius: 28px;
  padding: 28px;
  background: linear-gradient(135deg, #0f3a7f, #1d56a7 58%, #2c6fbe 100%);
  color: #f8fbff;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
}

.teacher-graph-entry__kicker {
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  opacity: 0.75;
  font-weight: 800;
}

.teacher-graph-entry__title {
  margin-top: 10px;
  font-size: 40px;
  line-height: 1.15;
  font-weight: 800;
}

.teacher-graph-entry__subtitle {
  margin-top: 14px;
  max-width: 700px;
  line-height: 1.8;
  font-size: 15px;
  color: rgba(240, 246, 255, 0.84);
}

.teacher-graph-entry__actions {
  display: grid;
  gap: 14px;
  justify-items: end;
}

.teacher-graph-entry__chip {
  padding: 12px 18px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.1);
  font-weight: 700;
}

.dify-tabs :deep(.el-tabs__header) {
  margin-bottom: 12px;
}

.dify-tabs :deep(.el-tabs__nav-wrap::after) {
  background: var(--app-border);
}

@media (max-width: 980px) {
  .teacher-graph-entry__hero {
    flex-direction: column;
  }

  .teacher-graph-entry__actions {
    justify-items: start;
  }
}
</style>
