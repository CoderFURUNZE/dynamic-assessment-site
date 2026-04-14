<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import HoverTip from "./HoverTip.vue";

type Resource = {
  id: number;
  kp_id: number;
  type: string;
  title: string;
  url: string;
  category?: string;
  description?: string;
  tags?: string;
  preview_type?: string;
  preview_status?: string;
  preview_error?: string;
  converted_preview_url?: string;
  original_file_url?: string;
  detected_resource_type?: string;
  original_file_name?: string;
};

const props = defineProps<{ kpId: number | null }>();
const emit = defineEmits<{ (e: "progress-updated"): void }>();

const resources = ref<Resource[]>([]);
const currentResourceId = ref<number | null>(null);
const videoRef = ref<HTMLVideoElement | null>(null);
const iframeRef = ref<HTMLIFrameElement | null>(null);
const lastTick = ref<number>(Date.now());

const progressById = ref<Record<number, { watched_seconds: number; duration_seconds: number; completed: boolean }>>({});

const currentResource = computed(() => resources.value.find((r) => r.id === currentResourceId.value) ?? null);
const learningResources = computed(() => resources.value.filter((r) => !["book", "recommend_book"].includes(r.type)));
const resourceTab = ref("all");

const learningResourceGroups = computed(() => {
  const groups = [
    { key: "video", title: "视频", description: "录播视频、讲解视频", items: [] as Resource[] },
    { key: "document", title: "文档 / 课件", description: "PDF、PPT、讲义、Word", items: [] as Resource[] },
    { key: "image", title: "图片", description: "图表、示意图、截图", items: [] as Resource[] },
    { key: "link", title: "外部链接", description: "B 站、课程网站、在线资料", items: [] as Resource[] },
    { key: "other", title: "其他资源", description: "暂未归类的资源", items: [] as Resource[] },
  ];
  const bucket = new Map(groups.map((item) => [item.key, item]));
  for (const resource of learningResources.value) {
    const key = resourceGroupKey(resource);
    bucket.get(key)?.items.push(resource);
  }
  return groups.filter((group) => group.items.length > 0);
});

const allLearningSorted = computed(() =>
  [...learningResources.value].sort((a, b) => a.title.localeCompare(b.title, "zh-Hans-CN")),
);
const videoResources = computed(() => learningResources.value.filter((r) => r.preview_type === "video_inline"));
const isBilibiliEmbed = computed(() => {
  const url = currentResource.value?.url ?? "";
  return url.includes("player.bilibili.com/player.html");
});
const apiBase = (api.defaults.baseURL || "").replace(/\/api\/?$/, "");
const resolvedVideoUrl = computed(() => {
  const raw = currentResource.value?.converted_preview_url || currentResource.value?.url || "";
  if (!raw) return "";
  if (raw.startsWith("http://") || raw.startsWith("https://") || raw.startsWith("//")) return raw;
  if (raw.startsWith("/")) return `${apiBase}${raw}`;
  return raw;
});
const isHls = computed(() => resolvedVideoUrl.value.includes(".m3u8"));
const videoSrc = computed(() => (isHls.value ? "" : resolvedVideoUrl.value));
const currentProgress = computed(() => {
  const id = currentResourceId.value;
  if (!id) return null;
  return progressById.value[id] ?? null;
});
const canInlinePdfPreview = computed(
  () =>
    Boolean(
      resolvedVideoUrl.value &&
      currentResource.value &&
      currentResource.value.preview_status === "ready" &&
      ["pdf_inline", "pdf_after_convert"].includes(currentResource.value.preview_type || ""),
    ),
);
const currentPreviewLabel = computed(() => {
  const previewType = currentResource.value?.preview_type || "";
  if (previewType === "pdf_after_convert") return "预览版 PDF，原文件为 Office 文档";
  if (previewType === "pdf_inline") return "PDF 在线预览";
  if (previewType === "video_inline") return "视频在线播放";
  if (previewType === "image_inline") return "图片在线预览";
  return "资源访问";
});

function resourceGroupKey(resource: Resource) {
  const type = String(resource.detected_resource_type || resource.type || "").toLowerCase();
  const previewType = String(resource.preview_type || "").toLowerCase();
  if (type === "video" || previewType === "video_inline") return "video";
  if (type === "image" || previewType === "image_inline") return "image";
  if (type === "link" || previewType === "external_link") return "link";
  if (["pdf", "ppt", "pptx", "doc", "docx", "note"].includes(type) || previewType.includes("pdf")) return "document";
  return "other";
}

function resourceTypeLabel(resource: Resource) {
  const type = String(resource.detected_resource_type || resource.type || "").toLowerCase();
  const map: Record<string, string> = {
    video: "视频",
    pdf: "PDF",
    ppt: "PPT",
    pptx: "PPT",
    doc: "Word",
    docx: "Word",
    note: "文档",
    image: "图片",
    link: "外链",
  };
  return map[type] || "资源";
}

function previewStatusLabel(resource: Resource) {
  const map: Record<string, string> = {
    ready: "可预览",
    processing: "处理中",
    failed: "转换失败",
  };
  return map[String(resource.preview_status || "ready")] || "可访问";
}

async function trackResource(resource: Resource, action: "visit" | "download" = "visit") {
  try {
    await api.post("/content/resource/visit", {
      kp_id: resource.kp_id,
      resource_id: resource.id,
      action,
    });
  } catch {
    // ignore tracking failure
  }
}

async function loadProgress() {
  if (!props.kpId) return;
  try {
    const res = await api.get(`/content/video/progress?kp_id=${props.kpId}`);
    const map: Record<number, { watched_seconds: number; duration_seconds: number; completed: boolean }> = {};
    for (const row of res.data ?? []) {
      map[row.resource_id] = {
        watched_seconds: Number(row.watched_seconds ?? 0),
        duration_seconds: Number(row.duration_seconds ?? 0),
        completed: Boolean(row.completed),
      };
    }
    progressById.value = map;
  } catch {
    // ignore
  }
}

async function load() {
  if (!props.kpId) return;
  try {
    const res = await api.get(`/content/resources?kp_id=${props.kpId}`);
    resources.value = res.data;
    currentResourceId.value = learningResources.value[0]?.id ?? null;
    await loadProgress();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载资源失败");
  }
}

async function openSupportResource(resource: Resource, action: "visit" | "download" = "visit") {
  await trackResource(resource, action);
  window.open(resource.original_file_url || resource.url, "_blank", "noopener,noreferrer");
  emit("progress-updated");
}

async function postProgress(payload: any) {
  const res = await api.post("/content/video/progress", payload);
  const rid = Number(res.data.resource_id);
  progressById.value[rid] = {
    watched_seconds: Number(res.data.watched_seconds ?? 0),
    duration_seconds: Number(res.data.duration_seconds ?? 0),
    completed: Boolean(res.data.completed),
  };
  emit("progress-updated");
}

async function tickMp4() {
  const v = videoRef.value;
  const r = currentResource.value;
  if (!v || !r || !props.kpId) return;
  if (v.paused || v.ended) return;
  if (document.hidden) return;

  const now = Date.now();
  const delta = Math.max(0, (now - lastTick.value) / 1000);
  lastTick.value = now;

  try {
    await postProgress({
      kp_id: props.kpId,
      resource_id: r.id,
      position_seconds: v.currentTime,
      duration_seconds: Number.isFinite(v.duration) ? v.duration : 0,
      watched_delta_seconds: delta,
      playback_rate: v.playbackRate,
    });
  } catch {
    // ignore
  }
}

async function tickEmbed() {
  const r = currentResource.value;
  if (!r || !props.kpId) return;
  if (document.hidden) return;

  const now = Date.now();
  const delta = Math.max(0, (now - lastTick.value) / 1000);
  lastTick.value = now;

  try {
    await postProgress({
      kp_id: props.kpId,
      resource_id: r.id,
      position_seconds: 0,
      duration_seconds: 0,
      watched_delta_seconds: delta,
      playback_rate: 1.0,
    });
  } catch {
    // ignore
  }
}

let timer: number | null = null;
let hls: any = null;

async function attachHls(url: string) {
  const v = videoRef.value;
  if (!v) return;
  if (hls?.destroy) {
    hls.destroy();
    hls = null;
  }
  try {
    const mod: any = await import(
      /* @vite-ignore */ "https://cdn.jsdelivr.net/npm/hls.js@1.5.15/dist/hls.min.js"
    );
    const HlsCtor = mod?.default ?? mod;
    if (HlsCtor && HlsCtor.isSupported && HlsCtor.isSupported()) {
      hls = new HlsCtor();
      hls.loadSource(url);
      hls.attachMedia(v);
      return;
    }
  } catch {
    // fall back to direct src
  }
  v.src = url;
}

function startTimer() {
  stopTimer();
  lastTick.value = Date.now();
  timer = window.setInterval(() => {
    if (isBilibiliEmbed.value) return tickEmbed();
    return tickMp4();
  }, 5000);
}

function stopTimer() {
  if (timer) window.clearInterval(timer);
  timer = null;
}

function onPlay() {
  lastTick.value = Date.now();
}

function onEmbedVisible() {
  lastTick.value = Date.now();
}

watch(
  () => currentResource.value?.id,
  async (id, prevId) => {
    if (!id || id === prevId || currentResource.value?.preview_type === "video_inline") return;
    await trackResource(currentResource.value);
    emit("progress-updated");
  }
);

watch(
  () => props.kpId,
  () => load(),
  { immediate: true }
);

watch(
  () => currentResourceId.value,
  () => {
    lastTick.value = Date.now();
  }
);

watch(
  () => resolvedVideoUrl.value,
  (url) => {
    if (!url || isBilibiliEmbed.value) return;
    if (isHls.value) {
      attachHls(url);
    } else if (videoRef.value) {
      if (hls?.destroy) {
        hls.destroy();
        hls = null;
      }
      videoRef.value.src = url;
    }
  }
);

onMounted(() => {
  startTimer();
});

onBeforeUnmount(() => {
  stopTimer();
  if (hls?.destroy) hls.destroy();
});
</script>

<template>
  <el-card class="resource-shell" shadow="never">
    <template #header>学习资源</template>
    <div v-if="!kpId">
      <el-text type="info">请选择知识点</el-text>
    </div>
    <div v-else>
      <div v-if="learningResources.length > 0" class="resource-pane">
        <el-tabs v-model="resourceTab" class="resource-pane__tabs">
          <el-tab-pane :label="`全部 (${learningResources.length})`" name="all">
            <div class="resource-pane__group-list resource-pane__group-list--flat">
              <button
                v-for="resource in allLearningSorted"
                :key="resource.id"
                class="resource-pane__resource"
                :class="{ active: resource.id === currentResourceId }"
                @click="currentResourceId = resource.id"
              >
                <div class="resource-pane__resource-meta">
                  <span>{{ resourceTypeLabel(resource) }}</span>
                  <small>{{ previewStatusLabel(resource) }}</small>
                </div>
                <strong>{{ resource.title }}</strong>
                <p>{{ resource.description || "打开后可查看该资源的预览、下载和学习进度。" }}</p>
              </button>
            </div>
          </el-tab-pane>
          <el-tab-pane
            v-for="group in learningResourceGroups"
            :key="group.key"
            :label="`${group.title} (${group.items.length})`"
            :name="group.key"
          >
            <div class="resource-pane__group-head resource-pane__group-head--tab">
              <div>
                <strong>{{ group.title }}</strong>
                <span>{{ group.description }}</span>
              </div>
            </div>
            <div class="resource-pane__group-list">
              <button
                v-for="resource in group.items"
                :key="resource.id"
                class="resource-pane__resource"
                :class="{ active: resource.id === currentResourceId }"
                @click="currentResourceId = resource.id"
              >
                <div class="resource-pane__resource-meta">
                  <span>{{ resourceTypeLabel(resource) }}</span>
                  <small>{{ previewStatusLabel(resource) }}</small>
                </div>
                <strong>{{ resource.title }}</strong>
                <p>{{ resource.description || "打开后可查看该资源的预览、下载和学习进度。" }}</p>
              </button>
            </div>
          </el-tab-pane>
        </el-tabs>

        <div v-if="currentResource" class="resource-pane__preview">
          <el-alert
            v-if="currentResource.preview_status === 'processing'"
            type="warning"
            :title="`${currentResource.title} 还在处理中`"
            description="Office 文档会先转换成 PDF，稍后刷新即可在线预览。"
            show-icon
            style="margin-bottom: 12px"
          />
          <el-alert
            v-else-if="currentResource.preview_status === 'failed'"
            type="error"
            :title="`${currentResource.title} 预览转换失败`"
            :description="currentResource.preview_error || '当前资源暂时只能下载查看'"
            show-icon
            style="margin-bottom: 12px"
          />
          <div>
            <iframe
              v-if="isBilibiliEmbed"
              ref="iframeRef"
              :src="currentResource.url"
              style="width: 100%; height: 520px; border: 0; border-radius: 8px; background: #000"
              @load="onEmbedVisible"
            />
            <iframe
              v-else-if="canInlinePdfPreview"
              ref="iframeRef"
              :src="resolvedVideoUrl"
              style="width: 100%; height: 620px; border: 1px solid var(--app-border); border-radius: 12px; background: #fff"
            />
            <img
              v-else-if="currentResource.preview_type === 'image_inline' && resolvedVideoUrl"
              :src="resolvedVideoUrl"
              :alt="currentResource.title"
              style="max-width: 100%; max-height: 620px; border-radius: 12px; border: 1px solid var(--app-border); background: #fff; object-fit: contain"
            />
            <video
              v-else-if="currentResource.preview_type === 'video_inline'"
              ref="videoRef"
              :src="videoSrc"
              controls
              style="width: 100%; border-radius: 8px; background: #000"
              @play="onPlay"
            />
            <div
              v-else
              style="display: grid; gap: 12px; padding: 18px; border: 1px dashed var(--app-border); border-radius: 12px; background: #fafbfd"
            >
              <strong style="color: var(--app-ink)">{{ currentResource.title }}</strong>
              <el-text type="info">当前资源不支持直接内嵌，点击按钮查看或下载。</el-text>
              <div style="display: flex; gap: 10px; flex-wrap: wrap">
                <el-button type="primary" @click="openSupportResource(currentResource, 'visit')">打开资源</el-button>
                <el-button v-if="currentResource.original_file_url" @click="openSupportResource({ ...currentResource, url: currentResource.original_file_url }, 'download')">下载原文件</el-button>
              </div>
            </div>
          </div>
          <div class="resource-tip-inline">
            <span>{{ currentPreviewLabel }}</span>
            <HoverTip
              :content="currentResource.preview_type === 'video_inline'
                ? '系统只保存观看进度，不保存视频画面。B 站 iframe 只能记录停留时长。'
                : ['pdf_inline', 'pdf_after_convert'].includes(currentResource.preview_type || '')
                  ? currentResource.preview_type === 'pdf_after_convert'
                    ? '当前展示的是系统自动转换后的 PDF 预览版，学生无需先下载。需要原文件时可单独下载。'
                    : '当前资源展示的是在线 PDF 预览版，学生无需先下载。'
                  : currentResource.preview_type === 'image_inline'
                    ? '当前资源以图片方式直接在线预览。'
                    : '当前资源通过外部地址或原文件打开。'"
            />
          </div>

          <el-text v-if="currentResource.preview_type === 'video_inline' && currentProgress" type="info" style="display: inline-block; margin-top: 8px">
            已记录：{{ Math.round(currentProgress.watched_seconds) }} 秒
            <span v-if="currentProgress.duration_seconds > 0">
              （约 {{ Math.round((currentProgress.watched_seconds / currentProgress.duration_seconds) * 100) }}%）
            </span>
          </el-text>
        </div>
      </div>

      <div v-else>
        <el-text type="warning">当前知识点未配置学习资源</el-text>
      </div>
    </div>
  </el-card>
</template>

<style scoped>
.resource-pane {
  display: grid;
  gap: 16px;
}

.resource-shell {
  overflow: hidden;
  border-radius: 28px;
  border: 2px solid #1f2937;
  background: linear-gradient(180deg, #f5f9ff 0%, #ffffff 100%);
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.08), 0 20px 32px rgba(31, 41, 55, 0.08);
}

.resource-shell :deep(.el-card__header) {
  padding: 16px 20px 12px;
  border-bottom: 1px solid #cfe0f5;
  background: linear-gradient(180deg, #f5f9ff 0%, #f8fbff 100%);
  font-weight: 800;
  color: #16355c;
}

.resource-shell :deep(.el-card__body) {
  padding: 16px;
}

.resource-pane__tabs {
  margin-bottom: 4px;
}

.resource-pane__tabs :deep(.el-tabs__header) {
  margin-bottom: 12px;
}

.resource-pane__tabs :deep(.el-tabs__nav-wrap)::after,
.resource-pane__tabs :deep(.el-tabs__active-bar) {
  display: none;
}

.resource-pane__tabs :deep(.el-tabs__item) {
  min-height: 42px;
  border-radius: 999px;
  border: 1.5px solid #c6d8ef;
  background: #f8fbff;
  color: #4c6787;
  padding: 6px 16px;
  margin-right: 8px;
  transition: all 0.2s ease;
}

.resource-pane__tabs :deep(.el-tabs__item.is-active) {
  background: #e8f1ff;
  border-color: #96b6e2;
  color: #1f3a5c;
  box-shadow: 0 8px 14px rgba(31, 41, 55, 0.08);
}

.resource-pane__group-list--flat {
  max-height: 420px;
  overflow-y: auto;
}

.resource-pane__group-head--tab {
  margin-bottom: 10px;
}

.resource-pane__groups {
  display: grid;
  gap: 14px;
}

.resource-pane__group {
  border: 1px solid var(--app-border);
  border-radius: 16px;
  padding: 14px;
  background: #fafcff;
  display: grid;
  gap: 12px;
}

.resource-pane__group-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.resource-pane__group-head strong {
  display: block;
  color: #27415f;
  font-size: 15px;
}

.resource-pane__group-head span,
.resource-pane__group-head small {
  color: #6d819b;
  font-size: 12px;
}

.resource-pane__group-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
}

.resource-pane__resource {
  border: 1.5px solid #c6d8ef;
  border-radius: 18px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  padding: 14px;
  display: grid;
  gap: 8px;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
  min-width: 0;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.resource-pane__resource.active {
  border-color: #96b6e2;
  background: #eef5ff;
  box-shadow: 0 10px 18px rgba(31, 41, 55, 0.08);
  transform: translateY(-1px);
}

.resource-pane__resource-meta {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  color: #6b80a0;
  font-size: 12px;
  font-weight: 700;
}

.resource-pane__resource strong {
  color: #223654;
  font-size: 15px;
  overflow-wrap: anywhere;
}

.resource-pane__resource p {
  margin: 0;
  color: #72839b;
  font-size: 12px;
  line-height: 1.6;
}

.resource-pane__preview {
  border: 1.5px solid #c6d8ef;
  border-radius: 22px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  padding: 16px;
  min-width: 0;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.resource-tip-inline {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  color: #637995;
  font-size: 13px;
  font-weight: 700;
}
</style>
