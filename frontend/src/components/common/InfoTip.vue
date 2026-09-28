<script setup lang="ts">
  import { computed } from 'vue';

  import { glossary, type GlossaryKey } from '@/content/glossary';

  const props = defineProps<{
    term: GlossaryKey;
  }>();

  const entry = computed(() => glossary[props.term]);
</script>

<template>
  <v-menu
    open-on-hover
    open-on-click
    :open-delay="100"
    :close-delay="150"
    location="top"
    max-width="300"
  >
    <template #activator="{ props: activatorProps }">
      <button
        v-bind="activatorProps"
        type="button"
        class="info-tip__button"
        :aria-label="`What does “${entry.title}” mean?`"
        @click.stop.prevent
      >
        <v-icon icon="mdi-information-outline" size="16" aria-hidden="true" />
      </button>
    </template>
    <div class="info-tip__card" role="tooltip">
      <strong>{{ entry.title }}</strong>
      <p>{{ entry.text }}</p>
    </div>
  </v-menu>
</template>

<style scoped>
  .info-tip__button {
    display: inline-grid;
    width: 24px;
    height: 24px;
    flex: none;
    place-items: center;
    margin-left: 2px;
    padding: 0;
    border: 0;
    border-radius: 50%;
    background: transparent;
    color: var(--color-muted);
    cursor: help;
    vertical-align: middle;
  }

  .info-tip__button:hover,
  .info-tip__button:focus-visible {
    background: var(--color-success-soft);
    color: var(--color-primary);
    outline: none;
  }

  .info-tip__card {
    padding: var(--space-sm) var(--space-md);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md, 12px);
    background: var(--color-surface, #fff);
    box-shadow: 0 8px 24px rgb(0 0 0 / 12%);
    color: var(--color-ink);
    font-size: 0.875rem;
    line-height: 1.5;
  }

  .info-tip__card strong {
    display: block;
    margin-bottom: 2px;
    color: var(--color-primary);
    font-size: 0.875rem;
  }

  .info-tip__card p {
    margin: 0;
    color: var(--color-ink-soft);
  }
</style>
