<script setup lang="ts">
  import { computed } from 'vue';

  import { glossary, type GlossaryEntry, type GlossaryKey } from '@/content/glossary';

  const props = withDefaults(
    defineProps<{
      terms: Array<GlossaryKey | null | undefined>;
      heading?: string;
      /** 'feature' shows larger cards with an icon, for landing sections. */
      variant?: 'compact' | 'feature';
    }>(),
    { heading: 'Terms explained', variant: 'compact' },
  );

  const entries = computed(() =>
    [...new Set(props.terms.filter((term): term is GlossaryKey => Boolean(term)))].map(
      (term): GlossaryEntry & { key: GlossaryKey } => ({ key: term, ...glossary[term] }),
    ),
  );
</script>

<template>
  <section
    v-if="entries.length"
    class="term-cards"
    :class="`term-cards--${variant}`"
    :aria-label="heading"
  >
    <h2 class="term-cards__heading">
      <v-icon icon="mdi-book-open-variant" size="20" aria-hidden="true" />
      {{ heading }}
    </h2>
    <ul class="term-cards__grid">
      <li v-for="entry in entries" :key="entry.key" class="term-cards__card">
        <span
          v-if="variant === 'feature' && entry.icon"
          class="term-cards__icon"
          aria-hidden="true"
        >
          <v-icon :icon="entry.icon" size="22" />
        </span>
        <strong>{{ entry.title }}</strong>
        <p>{{ entry.text }}</p>
      </li>
    </ul>
  </section>
</template>

<style scoped>
  .term-cards {
    margin-top: var(--space-xl);
  }

  .term-cards__heading {
    display: flex;
    align-items: center;
    gap: var(--space-xs);
    margin: 0 0 var(--space-md);
    color: var(--color-primary);
    font-family: var(--font-body);
    font-size: 1.125rem;
    font-weight: 700;
  }

  .term-cards__grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: var(--space-md);
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .term-cards__card {
    padding: var(--space-md);
    border: 1px solid var(--color-border);
    border-left: 4px solid var(--color-primary);
    border-radius: var(--radius-md);
    background: var(--color-surface);
  }

  .term-cards__card strong {
    display: block;
    margin-bottom: var(--space-xs);
    color: var(--color-ink);
    font-size: 0.9375rem;
  }

  .term-cards__card p {
    margin: 0;
    color: var(--color-ink-soft);
    font-size: 0.875rem;
    line-height: 1.5;
  }

  .term-cards--feature .term-cards__heading {
    font-family: var(--font-display);
    font-size: clamp(1.5rem, 3vw, 2rem);
    font-weight: 400;
  }

  .term-cards--feature .term-cards__grid {
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  }

  .term-cards--feature .term-cards__card {
    padding: var(--space-lg);
    border-left-width: 1px;
    border-radius: var(--radius-lg);
    transition:
      transform 160ms ease,
      box-shadow 160ms ease;
  }

  .term-cards--feature .term-cards__card:hover {
    box-shadow: 0 10px 28px rgb(0 0 0 / 7%);
    transform: translateY(-2px);
  }

  .term-cards__icon {
    display: grid;
    width: 44px;
    height: 44px;
    place-items: center;
    margin-bottom: var(--space-sm);
    border-radius: var(--radius-pill);
    background: var(--color-success-soft);
    color: var(--color-primary);
  }

  .term-cards__card:nth-child(even) .term-cards__icon {
    background: var(--color-accent-soft);
    color: var(--color-accent);
  }

  @media (prefers-reduced-motion: reduce) {
    .term-cards--feature .term-cards__card {
      transition: none;
    }
  }
</style>
