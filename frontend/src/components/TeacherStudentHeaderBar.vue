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
      <div class="detail-title">按学生切换查看画像、阶段和学习记录</div>
    </div>
    <div class="detail-actions">
      <div class="detail-actions__meta">共 {{ students.length }} 名学生</div>
      <el-select
        :model-value="selectedUserId"
        placeholder=""
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
}
.detail-header__main { display: grid; gap: 6px; }
.detail-header__eyebrow {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: .08em;
  text-transform: uppercase;
  color: var(--app-primary-deep);
}
.detail-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--app-ink);
}
.detail-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.detail-actions__meta {
  padding: 0 12px;
  min-height: 38px;
  border-radius: 999px;
  border: 1px solid var(--app-border);
  display: inline-flex;
  align-items: center;
  color: var(--app-ink-soft);
  font-size: 12px;
  font-weight: 700;
}
</style>
