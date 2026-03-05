<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import AdminQuestionManager from "../components/AdminQuestionManager.vue";
import AdminEdgeManager from "../components/AdminEdgeManager.vue";
import AdminUserManager from "../components/AdminUserManager.vue";
import AdminKpManager from "../components/AdminKpManager.vue";
import AdminPracticeReport from "../components/AdminPracticeReport.vue";
import AdminExpressionReport from "../components/AdminExpressionReport.vue";
import AdminCourseManager from "../components/AdminCourseManager.vue";
import AdminAuditLog from "../components/AdminAuditLog.vue";
import { getRole } from "../token";

const seeding = ref(false);
const loading = ref(false);
const subject = ref("");
const grade = ref("通用");
const role = ref(getRole());
const isPrivileged = computed(() => role.value === "admin" || role.value === "teacher");
const route = useRoute();
const router = useRouter();
const adminTabs = ["config", "video", "questions", "kps", "edges", "users", "report", "expression", "courses", "audit"];
const activeTab = computed<string>({
  get() {
    if (route.path.startsWith("/admin/")) {
      const seg = route.path.split("/")[2];
      if (adminTabs.includes(seg)) return seg;
    }
    return "config";
  },
  set(value) {
    const tab = String(value || "config");
    const safe = adminTabs.includes(tab) ? tab : "config";
    const target = `/admin/${safe}`;
    if (route.path !== target) router.push(target);
  },
});

type KP = { id: number; code: string; title: string };
type Course = { id: number; code: string; title: string };
const courses = ref<Course[]>([]);
const kps = ref<KP[]>([]);
const selectedKpId = ref<number | null>(null);
const bilibili = reactive({
  title: "",
  bvid: "BV1ct4y1t7pv",
  page: 1,
});
const localVideoTitle = ref("");
const localVideoUrl = ref("");
const localVideoFile = ref<File | null>(null);

const defaultWindow = {
  practice_attempts: 10,
  expressions: 20,
  practice_total: 10,
  difficulty_step: 0.1,
  expression_conf_threshold: 0.2,
  expression_influence: 1.0,
  video_complete_ratio: 0.8,
  video_min_ratio: 0.0,
  max_difficulty_jump: 0.2,
  stability_strength: 0.4,
};

const cfg = reactive({
  weights: {
    quiz_accuracy: 0.2,
    practice_accuracy: 0.7,
    expression_ease: 0.05,
    video_completion: 0.05,
    duration_penalty: 0.0,
  } as Record<string, number>,
  thresholds: { unlock_accuracy: 0.9, unlock_max_difficulty: 0.35 } as Record<string, number>,
  window: { ...defaultWindow } as Record<string, number>,
});

async function seed() {
  seeding.value = true;
  try {
    const res = await api.post("/admin/seed");
    ElMessage.success(`Seed 完成：${JSON.stringify(res.data)}`);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "Seed 失败（需 admin/teacher）");
  } finally {
    seeding.value = false;
  }
}

async function seedFull() {
  seeding.value = true;
  try {
    const res = await api.post("/admin/seed/full");
    ElMessage.success(`全科 Seed 完成：${JSON.stringify(res.data)}`);
    await loadConfig();
    await loadKps();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "全科 Seed 失败（需 admin/teacher）");
  } finally {
    seeding.value = false;
  }
}

async function loadCourses() {
  try {
    const res = await api.get("/graph/courses");
    courses.value = res.data ?? [];
    if (!subject.value && courses.value.length) {
      subject.value = courses.value[0].title;
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载课程失败");
  }
}

async function loadConfig() {
  if (!subject.value) return;
  loading.value = true;
  try {
    const res = await api.get(
      `/admin/config?subject=${encodeURIComponent(subject.value)}&grade=${encodeURIComponent(grade.value)}`
    );
    cfg.weights = res.data.weights;
    cfg.thresholds = res.data.thresholds;
    cfg.window = { ...defaultWindow, ...(res.data.window ?? {}) };
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "读取配置失败（需 admin/teacher）");
  } finally {
    loading.value = false;
  }
}

async function loadKps() {
  if (!subject.value) return;
  try {
    const res = await api.get(
      `/graph/kps?subject=${encodeURIComponent(subject.value)}&grade=${encodeURIComponent(grade.value)}`
    );
    kps.value = res.data;
    if (!selectedKpId.value && kps.value.length) selectedKpId.value = kps.value[0].id;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载知识点失败");
  }
}

async function bindBilibili() {
  if (!selectedKpId.value) {
    ElMessage.warning("请选择知识点");
    return;
  }
  if (!bilibili.bvid) {
    ElMessage.warning("请输入 bvid");
    return;
  }
  try {
    const res = await api.put("/admin/kp-video/bilibili", {
      kp_id: selectedKpId.value,
      title: bilibili.title,
      bvid: bilibili.bvid,
      page: bilibili.page,
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

function onLocalFileChange(file: any) {
  localVideoFile.value = file?.raw ?? null;
}

async function uploadLocalVideo() {
  if (!selectedKpId.value) {
    ElMessage.warning("请选择知识点");
    return;
  }
  if (!localVideoFile.value) {
    ElMessage.warning("请选择视频文件");
    return;
  }
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
  if (!selectedKpId.value) {
    ElMessage.warning("请选择知识点");
    return;
  }
  if (!localVideoUrl.value.trim()) {
    ElMessage.warning("请输入视频链接");
    return;
  }
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

async function saveConfig() {
  try {
    await api.put(`/admin/config?subject=${encodeURIComponent(subject.value)}&grade=${encodeURIComponent(grade.value)}`, cfg);
    ElMessage.success("已保存");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存失败");
  }
}

onMounted(async () => {
  if (!isPrivileged.value) {
    ElMessage.warning("仅管理员/教师可访问管理端");
    router.push("/student/resource");
    return;
  }
  await loadCourses();
  await loadConfig();
  await loadKps();
});
</script>

<template>
  <div v-if="isPrivileged" class="admin-shell">
    <el-card class="panel-card" shadow="never">
      <div class="topbar">
        <div class="topbar-left">
          <el-select v-model="subject" size="small" style="width: 200px" @change="() => { loadConfig(); loadKps(); }">
            <el-option v-for="c in courses" :key="c.id" :label="c.title" :value="c.title" />
          </el-select>
          <el-button size="small" type="primary" :loading="seeding" @click="seed">Seed 数据结构 Demo</el-button>
          <el-button size="small" type="success" :loading="seeding" @click="seedFull">Seed 全科数据</el-button>
        </div>
        <el-text type="info">admin/admin123; student1/student123</el-text>
      </div>
    </el-card>

    <div class="space" />

    <el-tabs v-model="activeTab" type="border-card" class="dify-tabs">
      <el-tab-pane label="评价配置" name="config">
        <el-card class="panel-card" shadow="never">
          <template #header>动态评价配置</template>
          <el-skeleton v-if="loading" :rows="6" animated />
          <div v-else class="config-grid">
            <el-form label-width="180px" size="small">
              <el-form-item label="小测正确率权重">
                <el-input-number v-model="cfg.weights.quiz_accuracy" :min="0" :max="1" :step="0.05" />
              </el-form-item>
              <el-form-item label="练习正确率权重">
                <el-input-number v-model="cfg.weights.practice_accuracy" :min="0" :max="1" :step="0.05" />
              </el-form-item>
              <el-form-item label="表情轻松度权重">
                <el-input-number v-model="cfg.weights.expression_ease" :min="0" :max="1" :step="0.05" />
              </el-form-item>
              <el-form-item label="视频完成度权重">
                <el-input-number v-model="cfg.weights.video_completion" :min="0" :max="1" :step="0.05" />
              </el-form-item>
              <el-form-item label="耗时惩罚权重">
                <el-input-number v-model="cfg.weights.duration_penalty" :min="0" :max="1" :step="0.05" />
              </el-form-item>

              <el-form-item label="解锁练习正确率阈值">
                <el-input-number v-model="cfg.thresholds.unlock_accuracy" :min="0" :max="1" :step="0.01" />
              </el-form-item>
              <el-form-item label="解锁最大困难度阈值">
                <el-input-number v-model="cfg.thresholds.unlock_max_difficulty" :min="0" :max="1" :step="0.01" />
              </el-form-item>

              <el-form-item label="练习统计窗口(题数)">
                <el-input-number v-model="cfg.window.practice_attempts" :min="1" :max="200" :step="1" />
              </el-form-item>
              <el-form-item label="表情统计窗口(次数)">
                <el-input-number v-model="cfg.window.expressions" :min="1" :max="200" :step="1" />
              </el-form-item>
              <el-form-item label="练习题总量(自动推荐)">
                <el-input-number v-model="cfg.window.practice_total" :min="1" :max="200" :step="1" />
              </el-form-item>
              <el-form-item label="难度区间步长">
                <el-input-number v-model="cfg.window.difficulty_step" :min="0.05" :max="0.5" :step="0.05" />
              </el-form-item>
              <el-form-item label="表情置信度阈值">
                <el-input-number v-model="cfg.window.expression_conf_threshold" :min="0" :max="1" :step="0.01" />
              </el-form-item>
              <el-form-item label="表情影响系数">
                <el-input-number v-model="cfg.window.expression_influence" :min="0" :max="2" :step="0.1" />
              </el-form-item>
              <el-form-item label="视频完成阈值">
                <el-input-number v-model="cfg.window.video_complete_ratio" :min="0" :max="1" :step="0.05" />
              </el-form-item>
              <el-form-item label="视频起始计入比例">
                <el-input-number v-model="cfg.window.video_min_ratio" :min="0" :max="1" :step="0.05" />
              </el-form-item>
              <el-form-item label="最大难度跳升">
                <el-input-number v-model="cfg.window.max_difficulty_jump" :min="0" :max="0.5" :step="0.05" />
              </el-form-item>
              <el-form-item label="稳定区强度">
                <el-input-number v-model="cfg.window.stability_strength" :min="0" :max="1" :step="0.05" />
              </el-form-item>
            </el-form>

            <div class="action-row">
              <el-button size="small" type="success" @click="saveConfig">保存</el-button>
              <el-button size="small" @click="loadConfig">重新加载</el-button>
            </div>
          </div>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="视频绑定" name="video">
        <el-card class="panel-card" shadow="never">
          <template #header>知识点绑定 B 站选集</template>
          <el-form label-width="120px" size="small">
            <el-form-item label="知识点">
              <el-select v-model="selectedKpId" style="width: 100%" filterable @visible-change="loadKps">
                <el-option v-for="kp in kps" :key="kp.id" :label="`${kp.code} ${kp.title}`" :value="kp.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="bvid">
              <el-input v-model="bilibili.bvid" placeholder="例如 BV1ct4y1t7pv" />
            </el-form-item>
            <el-form-item label="选集(page)">
              <el-input-number v-model="bilibili.page" :min="1" :max="200" :step="1" />
            </el-form-item>
            <el-form-item label="标题(可选)">
              <el-input v-model="bilibili.title" placeholder="留空将自动生成" />
            </el-form-item>
            <el-form-item>
              <el-button size="small" type="success" @click="bindBilibili">绑定</el-button>
              <el-button size="small" type="danger" @click="clearVideo">清除</el-button>
              <el-button size="small" @click="loadKps">刷新</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <div class="space" />

        <el-card class="panel-card" shadow="never">
          <template #header>本地/自托管视频</template>
          <el-form label-width="120px" size="small">
            <el-form-item label="知识点">
              <el-select v-model="selectedKpId" style="width: 100%" filterable @visible-change="loadKps">
                <el-option v-for="kp in kps" :key="kp.id" :label="`${kp.code} ${kp.title}`" :value="kp.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="标题(可选)">
              <el-input v-model="localVideoTitle" placeholder="留空将自动生成" />
            </el-form-item>
            <el-form-item label="上传 MP4">
              <el-upload :auto-upload="false" :show-file-list="true" :limit="1" @change="onLocalFileChange">
                <el-button size="small">选择文件</el-button>
              </el-upload>
              <el-button size="small" type="success" style="margin-left: 8px" @click="uploadLocalVideo">
                上传并绑定
              </el-button>
            </el-form-item>
            <el-form-item label="自托管链接">
              <el-input v-model="localVideoUrl" placeholder="可填 mp4 或 m3u8 地址" />
            </el-form-item>
            <el-form-item>
              <el-button size="small" type="primary" @click="bindLocalUrl">绑定链接</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="题库" name="questions">
        <AdminQuestionManager :subject="subject" :grade="grade" />
      </el-tab-pane>

      <el-tab-pane label="课程" name="courses">
        <AdminCourseManager />
      </el-tab-pane>

      <el-tab-pane label="知识点" name="kps">
        <AdminKpManager :subject="subject" :grade="grade" />
      </el-tab-pane>

      <el-tab-pane label="先修边" name="edges">
        <AdminEdgeManager :subject="subject" :grade="grade" />
      </el-tab-pane>

      <el-tab-pane label="用户" name="users">
        <AdminUserManager />
      </el-tab-pane>

      <el-tab-pane label="练习报表" name="report">
        <AdminPracticeReport />
      </el-tab-pane>

    <el-tab-pane label="表情报表" name="expression">
      <AdminExpressionReport />
    </el-tab-pane>

    <el-tab-pane label="操作日志" name="audit">
      <AdminAuditLog />
    </el-tab-pane>
  </el-tabs>
  </div>
</template>

<style scoped>
.admin-shell {
  display: grid;
  gap: 16px;
}

.topbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
}

.topbar-left {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.space {
  height: 12px;
}

.config-grid {
  display: grid;
  gap: 8px;
}

.action-row {
  display: flex;
  gap: 8px;
}

.dify-tabs :deep(.el-tabs__header) {
  margin-bottom: 12px;
}

.dify-tabs :deep(.el-tabs__nav-wrap::after) {
  background: var(--app-border);
}
</style>
