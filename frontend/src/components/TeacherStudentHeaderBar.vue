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
        @update:model-value="(value: string | number | boolean | null | undefined) => emit('update:selectedUserId', value == null ? null : Number(value))"
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
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  padding: 12px 16px;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background:
    radial-gradient(circle at top left, rgba(191, 219, 254, 0.18), transparent 28%),
    radial-gradient(circle at right center, rgba(187, 247, 208, 0.16), transparent 22%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow:
    0 10px 22px rgba(15, 23, 42, 0.04),
    inset 0 1px 0 rgba(255, 255, 255, 0.88);
}

.detail-header__main {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.detail-header__eyebrow {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  min-height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(187, 247, 208, 0.42);
  font-size: 12px;
  font-weight: 800;
  color: #166534;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.detail-title {
  font-size: clamp(18px, 2vw, 22px);
  font-weight: 800;
  line-height: 1.2;
  letter-spacing: -0.04em;
  color: #0f172a;
}

.detail-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.detail-actions__meta {
  padding: 0 12px;
  min-height: 36px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  display: inline-flex;
  align-items: center;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
}

.detail-actions :deep(.el-select__wrapper) {
  min-height: 38px;
  border-radius: 14px !important;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%) !important;
  box-shadow: 0 0 0 1px rgba(148, 163, 184, 0.2) inset !important;
}
</style>
