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
  align-items: flex-start;
  gap: 18px;
  padding: 20px 22px;
  border-radius: 28px;
  border: 3px solid #1f2937;
  background: linear-gradient(180deg, #fff8ef 0%, #fffdf8 100%);
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
}

.student-content-page__left {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.student-content-page__back {
  border: 0;
  border-radius: 999px;
  background: #f8fbff;
  color: #355070;
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  border: 1.5px solid #c6d8ef;
  min-height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.student-content-page__title {
  margin: 0;
  font-size: 26px;
  font-weight: 800;
  color: #243449;
}

.student-content-page__chips {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 12px 16px;
  border-radius: 999px;
  background: #eef5ff;
  border: 1.5px solid #c6d8ef;
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

  .student-content-page__left {
    flex-direction: column;
  }
}
</style>
