<script setup lang="ts">
defineProps<{
  title: string;
  subtitle: string;
  hint: string;
  code?: string;
  kpTitle?: string;
  chapter?: string;
  masterySummary?: string;
}>();

const emit = defineEmits<{
  back: [];
}>();
</script>

<template>
  <div class="student-content-page__toolbar">
    <div class="student-content-page__left">
      <button class="student-content-page__back" @click="emit('back')">返回图谱</button>
      <div>
        <h1 class="student-content-page__title">{{ title }}</h1>
        <p class="student-content-page__subtitle">{{ subtitle }}</p>
        <div class="student-content-page__hint">{{ hint }}</div>
      </div>
    </div>
    <div v-if="kpTitle" class="student-content-page__chips">
      <span>{{ code }}</span>
      <strong>{{ kpTitle }}</strong>
      <small>{{ chapter || "未分章" }}</small>
      <el-tag v-if="masterySummary" size="small" type="info" effect="plain">{{ masterySummary }}</el-tag>
    </div>
  </div>
</template>

<style scoped>
.student-content-page__toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 18px;
  padding: 18px 20px;
  border-radius: 20px;
  border: 1px solid var(--app-border);
  background: #ffffff;
  box-shadow: var(--app-shadow-soft);
}

.student-content-page__left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.student-content-page__back {
  border: 0;
  border-radius: 999px;
  background: #f4f7fb;
  color: #39506d;
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  border: 1px solid var(--app-border);
  min-height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.student-content-page__title {
  margin: 0;
  font-size: 24px;
  font-weight: 800;
  color: #243449;
}

.student-content-page__subtitle {
  margin: 4px 0 0;
  color: #6e8097;
  font-size: 13px;
}

.student-content-page__hint {
  margin-top: 10px;
  max-width: 720px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--app-border);
  background: #f8fbff;
  color: #57708f;
  font-size: 12px;
  line-height: 1.6;
}

.student-content-page__chips {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 12px 16px;
  border-radius: 999px;
  background: #fafbfd;
  border: 1px solid var(--app-border);
  color: #314661;
}

.student-content-page__chips span {
  font-size: 12px;
  color: #6782a7;
  font-weight: 700;
}

.student-content-page__chips strong {
  font-size: 16px;
  color: #1f3249;
}

.student-content-page__chips small {
  font-size: 12px;
  color: #718097;
}

@media (max-width: 1080px) {
  .student-content-page__toolbar {
    grid-template-columns: 1fr;
    display: grid;
  }
}
</style>
