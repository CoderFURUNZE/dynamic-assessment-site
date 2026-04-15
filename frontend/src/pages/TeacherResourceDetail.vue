<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { Document, Link, Notebook, Reading, VideoPlay } from "@element-plus/icons-vue";
import { api } from "../api";

type ResourceDetail = {
  id: number;
  kp_id: number;
  subject: string;
  grade: string;
  type: string;
  title: string;
  url: string;
  category?: string;
  description?: string;
  tags?: string;
  original_file_name?: string;
  file_extension?: string;
  detected_mime_type?: string;
  detected_resource_type?: string;
  preview_type?: string;
  preview_status?: string;
  preview_error?: string;
  converted_preview_url?: string;
  original_file_url?: string;
  extension_mismatch?: boolean;
  source_kind?: string;
  kp_code: string;
  kp_title: string;
};

type DetailTab = "basic" | "preview" | "guide";

const route = useRoute();
const router = useRouter();

const loading = ref(false);
const saving = ref(false);
const activeTab = ref<DetailTab>("basic");
const detail = ref<ResourceDetail | null>(null);

const form = reactive({
  title: "",
  url: "",
  category: "learning",
  tags: "",
  description: "",
});

const resourceId = computed(() => {
  const raw = Number(route.params.resourceId);
  return Number.isFinite(raw) && raw > 0 ? raw : null;
});

const resourceTypeOptions = [
  { value: "video", label: "视频资源", icon: VideoPlay, desc: "适合讲解过程、演示操作和录播课程。" },
  { value: "note", label: "文档资料", icon: Notebook, desc: "适合讲义、PDF、课堂笔记和参考资料。" },
  { value: "doc", label: "补充资料", icon: Document, desc: "适合资料包、附件和实验文档。" },
  { value: "ppt", label: "课件", icon: Document, desc: "适合讲稿、课件和课堂展示材料。" },
  { value: "example", label: "案例示例", icon: Reading, desc: "适合案例解析、实验示例和代码样例。" },
  { value: "link", label: "外部链接", icon: Link, desc: "适合网页、外部平台和阅读链接。" },
  { value: "book", label: "推荐书籍", icon: Reading, desc: "适合课后阅读和拓展书单。" },
];

const selectedTypeMeta = computed(
  () => resourceTypeOptions.find((item) => item.value === (detail.value?.detected_resource_type || detail.value?.type || "")) ?? resourceTypeOptions[1]
);

const previewAvailable = computed(() => Boolean(form.url && form.url.trim()));

function fillForm() {
  if (!detail.value) return;
  form.title = detail.value.title || "";
  form.url = detail.value.original_file_url || detail.value.url || "";
  form.category = detail.value.category || "learning";
  form.tags = detail.value.tags || "";
  form.description = detail.value.description || "";
}

async function loadDetail() {
  if (!resourceId.value) return;
  loading.value = true;
  try {
    const res = await api.get(`/admin/kp-resources/${resourceId.value}/detail`);
    detail.value = res.data;
    fillForm();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载资源详情失败");
  } finally {
    loading.value = false;
  }
}

async function save() {
  if (!resourceId.value) return;
  saving.value = true;
  try {
    await api.put(`/admin/kp-resources/${resourceId.value}`, {
      title: form.title,
      url: detail.value?.source_kind === "external" ? form.url : undefined,
      category: form.category,
      tags: form.tags,
      description: form.description,
    });
    ElMessage.success("资源已保存");
    await loadDetail();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存资源失败");
  } finally {
    saving.value = false;
  }
}

async function removeResource() {
  if (!resourceId.value) return;
  try {
    await ElMessageBox.confirm("确定删除这个资源吗？删除后无法恢复。", "确认删除", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    });
    await api.delete(`/admin/kp-resources/${resourceId.value}`);
    ElMessage.success("资源已删除");
    backToWorkspace();
  } catch (e: any) {
    if (e === "cancel" || e === "close") return;
    ElMessage.error(e?.response?.data?.detail ?? "删除资源失败");
  }
}

function backToWorkspace() {
  const kpId = Number(detail.value?.kp_id || route.query.kp_id || 0);
  router.push({
    path: kpId > 0 ? `/teacher/kp-content/${kpId}` : "/teacher/content",
    query: {
      subject: detail.value?.subject || String(route.query.subject || "") || undefined,
      grade: detail.value?.grade || String(route.query.grade || "") || undefined,
    },
  });
}

function openPreview() {
  if (!previewAvailable.value) {
    ElMessage.warning("请先填写资源地址");
    return;
  }
  window.open(detail.value?.converted_preview_url || detail.value?.url || form.url, "_blank", "noopener,noreferrer");
}

watch(resourceId, loadDetail, { immediate: true });
</script>

<template>
  <div class="teacher-resource-page" v-loading="loading">
    <div class="teacher-resource-page__inner">
      <header class="resource-hero">
        <div class="resource-hero__left">
          <button class="back-button" @click="backToWorkspace">返回图谱</button>
          <div class="hero-copy">
            <div class="hero-eyebrow">教师资源配置</div>
            <h1>资源详情与配置</h1>
            <p>在这里维护知识点下的资源标题、分类、说明和预览入口。</p>
          </div>
        </div>

        <div v-if="detail" class="hero-kp-card">
          <span>{{ detail.subject }}</span>
          <strong>{{ detail.kp_code }} {{ detail.kp_title }}</strong>
          <small>资源 ID：{{ detail.id }}</small>
        </div>
      </header>

      <el-empty v-if="!detail" description="资源不存在或已删除" />

      <template v-else>
        <section class="resource-overview">
          <div class="overview-card">
            <span>资源标题</span>
            <strong>{{ form.title || "未命名资源" }}</strong>
          </div>
          <div class="overview-card">
            <span>资源类型</span>
            <strong>{{ selectedTypeMeta.label }}</strong>
          </div>
          <div class="overview-card">
            <span>所属知识点</span>
            <strong>{{ detail.kp_title }}</strong>
          </div>
          <div class="overview-card">
            <span>预览状态</span>
            <strong>{{ previewAvailable ? "已配置" : "未填写地址" }}</strong>
          </div>
        </section>

        <section class="resource-layout">
          <aside class="resource-side">
            <button class="side-tab" :class="{ active: activeTab === 'basic' }" @click="activeTab = 'basic'">
              <strong>基础信息</strong>
              <small>改标题、分类、标签和地址</small>
            </button>
            <button class="side-tab" :class="{ active: activeTab === 'preview' }" @click="activeTab = 'preview'">
              <strong>资源预览</strong>
              <small>快速检查链接和打开效果</small>
            </button>
            <button class="side-tab" :class="{ active: activeTab === 'guide' }" @click="activeTab = 'guide'">
              <strong>使用说明</strong>
              <small>帮助老师明确资源该怎么配</small>
            </button>
          </aside>

          <main class="resource-main">
            <section v-if="activeTab === 'basic'" class="panel-card">
              <div class="panel-head">
                <div>
                  <h3>基础信息</h3>
                  <p>系统自动识别资源类型，老师只需要维护标题、分类、标签和说明。</p>
                </div>
                <div class="panel-actions">
                  <el-button @click="openPreview" :disabled="!previewAvailable">预览资源</el-button>
                  <el-button type="primary" :loading="saving" @click="save">保存修改</el-button>
                </div>
              </div>

              <div class="type-grid">
                <button
                  v-for="item in resourceTypeOptions"
                  :key="item.value"
                  class="type-card"
                  :class="{ active: (detail?.detected_resource_type || detail?.type) === item.value }"
                  disabled
                >
                  <component :is="item.icon" class="type-card__icon" />
                  <strong>{{ item.label }}</strong>
                  <small>{{ item.desc }}</small>
                </button>
              </div>

              <div class="resource-meta-card">
                <div><span>系统识别类型</span><strong>{{ selectedTypeMeta.label }}</strong></div>
                <div><span>学生预览方式</span><strong>{{ detail.preview_type || "download" }}</strong></div>
                <div><span>原始文件</span><strong>{{ detail.original_file_name || "外部链接" }}</strong></div>
                <div><span>MIME 类型</span><strong>{{ detail.detected_mime_type || "外部链接" }}</strong></div>
              </div>

              <el-form label-position="top" class="resource-form">
                <el-form-item label="资源标题">
                  <el-input v-model="form.title" placeholder="例如：操作系统历史讲解视频" />
                </el-form-item>
                <el-form-item label="所属分类">
                  <el-radio-group v-model="form.category">
                    <el-radio label="learning">学习内容</el-radio>
                    <el-radio label="recommend">推荐资源</el-radio>
                  </el-radio-group>
                </el-form-item>
                <el-form-item v-if="detail.source_kind === 'external'" label="资源 URL / 外部地址">
                  <el-input v-model="form.url" placeholder="可填写视频地址、文档地址、网页链接或网盘地址" />
                </el-form-item>
                <el-form-item label="标签">
                  <el-input v-model="form.tags" placeholder="例如：阶段一、重点、补充阅读" />
                </el-form-item>
                <el-form-item label="描述">
                  <el-input v-model="form.description" type="textarea" :rows="3" placeholder="告诉学生怎么使用这份资源" />
                </el-form-item>
              </el-form>
            </section>

            <section v-else-if="activeTab === 'preview'" class="panel-card">
              <div class="panel-head">
                <div>
                  <h3>资源预览</h3>
                  <p>这里不做复杂播放器，只提供老师快速检查链接和跳转。</p>
                </div>
              </div>

              <div class="preview-box" :class="{ empty: !previewAvailable }">
                <template v-if="previewAvailable">
                  <div class="preview-meta">
                    <span>{{ selectedTypeMeta.label }}</span>
                    <strong>{{ form.title || "未命名资源" }}</strong>
                    <small>{{ form.url }}</small>
                  </div>
                  <div class="preview-actions">
                    <el-button type="primary" @click="openPreview">打开资源地址</el-button>
                    <el-button @click="activeTab = 'basic'">返回修改</el-button>
                  </div>
                </template>
                <template v-else>
                  <strong>还没有可预览的资源地址</strong>
                  <span>先去“基础信息”里填写资源 URL，再回来预览。</span>
                </template>
              </div>
            </section>

            <section v-else class="panel-card">
              <div class="panel-head">
                <div>
                  <h3>老师使用说明</h3>
                  <p>把资源配置页的用途说明清楚，后续答辩和交接都更方便。</p>
                </div>
              </div>

              <div class="guide-list">
                <div class="guide-item">
                  <strong>1. 视频资源</strong>
                  <p>适合放讲解视频、实验演示和录播课程，学生点击学习时优先进入这里。</p>
                </div>
                <div class="guide-item">
                  <strong>2. 文档资料</strong>
                  <p>适合 PDF、讲义、课件、笔记和学习说明文档。</p>
                </div>
                <div class="guide-item">
                  <strong>3. 外部链接</strong>
                  <p>适合超星页面、外部网页、慕课地址和在线阅读页面。</p>
                </div>
                <div class="guide-item danger">
                  <strong>4. 删除资源</strong>
                  <p>删除后学生端将无法再看到这个资源入口，请确认不再使用再删除。</p>
                </div>
              </div>

              <div class="danger-zone">
                <div>
                  <strong>危险操作</strong>
                  <p>删除资源不会影响知识点本身，但会移除这个资源入口。</p>
                </div>
                <el-button type="danger" plain @click="removeResource">删除资源</el-button>
              </div>
            </section>
          </main>
        </section>
      </template>
    </div>
  </div>
</template>

<style scoped>
.teacher-resource-page {
  padding: 24px;
  background: var(--app-bg);
  min-height: 100vh;
}

.teacher-resource-page__inner {
  max-width: 1440px;
  margin: 0 auto;
  display: grid;
  gap: 18px;
}

.resource-hero,
.resource-overview,
.resource-layout {
  background:
    radial-gradient(circle at top right, rgba(210, 238, 255, 0.72), transparent 42%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
  border: 3px solid #1f2937;
  border-radius: 30px;
  box-shadow:
    0 12px 0 rgba(31, 41, 55, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.78);
}

.resource-hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;
  padding: 28px;
}

.resource-hero__left {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.back-button {
  width: fit-content;
  border: 1.5px solid #c6d8ef;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  color: #35557f;
  border-radius: 999px;
  height: 42px;
  padding: 0 18px;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.hero-eyebrow {
  color: #587394;
  font-size: 13px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.hero-copy h1 {
  margin: 8px 0 10px;
  font-size: 34px;
  line-height: 1.1;
  color: #17325c;
}

.hero-copy p {
  margin: 0;
  max-width: 640px;
  font-size: 16px;
  line-height: 1.7;
  color: #587394;
}

.hero-kp-card {
  min-width: 260px;
  padding: 18px 20px;
  border-radius: 22px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  border: 1.5px solid #c6d8ef;
  display: grid;
  gap: 8px;
}

.hero-kp-card span,
.hero-kp-card small {
  color: #587394;
}

.hero-kp-card strong {
  color: #17325c;
  font-size: 19px;
}

.resource-overview {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  padding: 20px;
}

.overview-card {
  padding: 18px;
  border: 1.5px solid #c6d8ef;
  border-radius: 22px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  display: grid;
  gap: 8px;
}

.overview-card span {
  color: #587394;
  font-size: 13px;
  font-weight: 700;
}

.overview-card strong {
  color: #17325c;
  font-size: 24px;
  line-height: 1.25;
}

.resource-layout {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 18px;
  padding: 20px;
}

.resource-side {
  display: grid;
  gap: 12px;
  align-content: start;
}

.side-tab {
  border: 1.5px solid #c6d8ef;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  border-radius: 22px;
  padding: 16px 18px;
  text-align: left;
  cursor: pointer;
  display: grid;
  gap: 4px;
}

.side-tab strong {
  font-size: 18px;
  color: #17325c;
}

.side-tab small {
  color: #587394;
  font-size: 13px;
}

.side-tab.active {
  background: radial-gradient(circle at top left, rgba(215, 249, 168, 0.42), transparent 58%), #fffdf6;
  border-color: #1f2937;
  box-shadow: 0 10px 24px rgba(31, 41, 55, 0.1);
}

.resource-main {
  min-width: 0;
}

.panel-card {
  border: 1.5px solid #c6d8ef;
  border-radius: 24px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  padding: 22px;
  display: grid;
  gap: 20px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
}

.panel-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.panel-head h3 {
  margin: 0 0 6px;
  font-size: 26px;
  color: #17325c;
}

.panel-head p {
  margin: 0;
  color: #587394;
  line-height: 1.7;
}

.panel-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.type-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.type-card {
  border: 1.5px solid #c6d8ef;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  border-radius: 20px;
  padding: 18px;
  text-align: left;
  display: grid;
  gap: 8px;
  cursor: pointer;
}

.type-card.active {
  border-color: #1f2937;
  background: radial-gradient(circle at top left, rgba(215, 249, 168, 0.42), transparent 58%), #fffdf6;
  box-shadow: 0 10px 24px rgba(31, 41, 55, 0.1);
}

.type-card__icon {
  width: 22px;
  height: 22px;
  color: #4f7fff;
}

.type-card strong {
  color: #17325c;
  font-size: 18px;
}

.type-card small {
  color: #587394;
  line-height: 1.6;
}

.resource-form {
  max-width: 820px;
}

.resource-meta-card {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  padding: 14px 16px;
  border: 1.5px solid #c6d8ef;
  border-radius: 20px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
}

.resource-meta-card div {
  display: grid;
  gap: 4px;
}

.resource-meta-card span {
  font-size: 12px;
  color: #587394;
}

.resource-meta-card strong {
  color: #17325c;
  word-break: break-all;
}

.preview-box {
  min-height: 320px;
  border: 1.5px solid #c6d8ef;
  border-radius: 24px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  padding: 24px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 18px;
}

.preview-box.empty {
  align-items: center;
  justify-content: center;
  text-align: center;
}

.preview-box strong {
  color: #17325c;
  font-size: 22px;
}

.preview-box span,
.preview-box small {
  color: #587394;
}

.preview-meta {
  display: grid;
  gap: 10px;
}

.preview-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.guide-list {
  display: grid;
  gap: 12px;
}

.guide-item {
  border: 1.5px solid #c6d8ef;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  border-radius: 20px;
  padding: 18px;
  display: grid;
  gap: 6px;
}

.guide-item strong {
  color: #17325c;
  font-size: 18px;
}

.guide-item p {
  margin: 0;
  color: #587394;
  line-height: 1.75;
}

.guide-item.danger {
  background: #fff8f7;
  border-color: #f1c6be;
}

.danger-zone {
  border: 1.5px solid #f1c6be;
  background: #fff9f8;
  border-radius: 24px;
  padding: 18px 20px;
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  flex-wrap: wrap;
}

.danger-zone strong {
  color: #8a3e36;
}

.danger-zone p {
  margin: 6px 0 0;
  color: #9f6b65;
}

.teacher-resource-page :deep(.el-input__wrapper),
.teacher-resource-page :deep(.el-textarea__inner),
.teacher-resource-page :deep(.el-button) {
  border-radius: 16px;
}

.teacher-resource-page :deep(.el-input__wrapper),
.teacher-resource-page :deep(.el-textarea__inner) {
  box-shadow: 0 0 0 1px #c6d8ef inset;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
}

.teacher-resource-page :deep(.el-button--primary) {
  border-color: rgba(51, 122, 71, 0.8);
  background: linear-gradient(135deg, #2f7a45, #2aa887);
}

@media (max-width: 1100px) {
  .resource-overview {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .resource-layout {
    grid-template-columns: 1fr;
  }

  .type-grid {
    grid-template-columns: 1fr;
  }

  .resource-meta-card {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .teacher-resource-page {
    padding: 14px;
  }

  .resource-hero {
    padding: 20px;
  }

  .hero-copy h1 {
    font-size: 28px;
  }

  .hero-copy p {
    font-size: 15px;
  }

  .resource-overview {
    grid-template-columns: 1fr;
  }
}
</style>
