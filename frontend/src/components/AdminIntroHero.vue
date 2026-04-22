<script setup lang="ts">
defineProps<{
  eyebrow?: string;
  title: string;
  description?: string;
  pill?: string;
}>();
</script>

<template>
  <section class="admin-intro-hero panel-card">
    <div class="admin-intro-hero__main">
      <p v-if="eyebrow" class="admin-intro-hero__eyebrow">{{ eyebrow }}</p>
      <div class="admin-intro-hero__row">
        <h1 class="admin-intro-hero__title">{{ title }}</h1>
        <span v-if="pill" class="admin-intro-hero__pill">{{ pill }}</span>
      </div>
      <p v-if="description" class="admin-intro-hero__description">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="admin-intro-hero__actions">
      <slot name="actions" />
    </div>
  </section>
</template>

<style scoped>
.admin-intro-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  min-height: 140px;
  padding: 28px;
  gap: 20px;
  flex-wrap: wrap;
  background:
    radial-gradient(circle at top right, rgba(56, 189, 248, 0.1), transparent 28%),
    radial-gradient(circle at top left, rgba(34, 197, 94, 0.08), transparent 24%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 20px;
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.08);
}

.admin-intro-hero__main {
  display: grid;
  gap: 10px;
  max-width: 760px;
}

.admin-intro-hero__row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.admin-intro-hero__eyebrow {
  margin: 0;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.04em;
  color: #166534;
  display: inline-flex;
  width: fit-content;
  padding: 5px 10px;
  border-radius: 999px;
  background: #eefbf3;
  border: 1px solid rgba(34, 197, 94, 0.16);
}

.admin-intro-hero__title {
  margin: 0;
  font-size: clamp(28px, 3vw, 36px);
  line-height: 1.08;
  color: #0f172a;
  font-family: var(--el-font-family);
  font-weight: 800;
}

.admin-intro-hero__pill {
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: #f8fafc;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
}

.admin-intro-hero__description {
  margin: 0;
  max-width: 62ch;
  color: #64748b;
  font-size: 15px;
  line-height: 1.75;
}

.admin-intro-hero__actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
  margin-left: auto;
}

@media (max-width: 960px) {
  .admin-intro-hero {
    padding: 22px 20px;
  }

  .admin-intro-hero__actions {
    margin-left: 0;
    width: 100%;
  }
}
</style>
