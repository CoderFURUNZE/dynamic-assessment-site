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
  min-height: 156px;
  padding: 28px;
  gap: 20px;
  flex-wrap: wrap;
  background:
    radial-gradient(circle at top right, rgba(201, 237, 255, 0.3), transparent 28%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
  border: 3px solid #1f2937;
  border-radius: 32px;
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
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
  letter-spacing: 0.08em;
  color: #1f2937;
  text-transform: uppercase;
  display: inline-flex;
  width: fit-content;
  padding: 6px 12px;
  border-radius: 999px;
  background: #d7f9a8;
}

.admin-intro-hero__title {
  margin: 0;
  font-size: clamp(28px, 3vw, 40px);
  line-height: 1.08;
  color: #1d2433;
  font-family: "Fredoka", "Nunito", sans-serif;
}

.admin-intro-hero__pill {
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  border: 1.5px solid #c6d8ef;
  background: #f6faff;
  color: #29476a;
  font-size: 12px;
  font-weight: 700;
  box-shadow: none;
}

.admin-intro-hero__description {
  margin: 0;
  max-width: 62ch;
  color: #636b7a;
  font-size: 15px;
  line-height: 1.8;
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
