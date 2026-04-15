<script setup lang="ts">
type StudentRow = {
  user_id: number;
  username: string;
  full_name: string;
};

defineProps<{
  students: StudentRow[];
  selectedUserId: number | null;
}>();

const emit = defineEmits<{
  "update:selectedUserId": [value: number | null];
}>();
</script>

<template>
  <div class="detail-header">
    <div class="detail-header__main">
      <span class="detail-header__eyebrow">学生详情</span>
      <div class="detail-title">按学生切换查看画像、阶段变化和学习记录</div>
    </div>
    <div class="detail-actions">
      <div class="detail-actions__meta">共 {{ students.length }} 名学生</div>
      <el-select
        :model-value="selectedUserId"
        placeholder="请选择学生"
        style="width: 300px"
        filterable
        @update:model-value="(value) => emit('update:selectedUserId', value as number | null)"
      >
        <el-option
          v-for="student in students"
          :key="student.user_id"
          :label="`${student.username} ${student.full_name || ''}`"
          :value="student.user_id"
        />
      </el-select>
    </div>
  </div>
</template>

<style scoped>
.detail-header {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
  flex-wrap: wrap;
  padding: 20px 22px;
  border-radius: 28px;
  border: 3px solid #1f2937;
  background: radial-gradient(circle at top right, rgba(210, 238, 255, 0.72), transparent 42%), #fffdf6;
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
}

.detail-header__main {
  display: grid;
  gap: 6px;
}

.detail-header__eyebrow {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  min-height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  background: #d7f9a8;
  font-size: 12px;
  font-weight: 800;
  color: #17325c;
}

.detail-title {
  font-size: 28px;
  font-weight: 700;
  color: #17325c;
}

.detail-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.detail-actions__meta {
  padding: 0 12px;
  min-height: 42px;
  border-radius: 999px;
  border: 1px solid #c7daf6;
  background: linear-gradient(180deg, #f8fbff 0%, #eef5ff 100%);
  display: inline-flex;
  align-items: center;
  color: #47607f;
  font-size: 12px;
  font-weight: 700;
}

.detail-actions :deep(.el-select__wrapper) {
  min-height: 44px;
  border-radius: 18px !important;
  background: linear-gradient(180deg, #f9fbff 0%, #eef5ff 100%) !important;
  box-shadow: 0 0 0 1px #c7daf6 inset !important;
}
</style>
