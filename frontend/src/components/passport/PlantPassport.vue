<script setup lang="ts">
  import { computed } from 'vue';

  import InfoTip from '@/components/common/InfoTip.vue';
  import type { PassportPlant } from '@/types/passport';
  import {
    containmentFacts,
    GENERAL_CONTAINMENT_STEPS,
    generalGuidance,
    growingFacts,
    isRisky,
    showsGrowingGuide,
    whatWeDontKnow,
    whatWeKnow,
  } from '@/utils/passportPresentation';

  const props = defineProps<{
    plant: PassportPlant;
  }>();

  const known = computed(() => whatWeKnow(props.plant));
  const unknown = computed(() => whatWeDontKnow(props.plant));
  const risky = computed(() => isRisky(props.plant));
  const growing = computed(() => (showsGrowingGuide(props.plant) ? growingFacts(props.plant) : []));
  const guidance = computed(() =>
    showsGrowingGuide(props.plant) ? generalGuidance(props.plant) : null,
  );
  const containment = computed(() => (risky.value ? containmentFacts(props.plant) : []));
  const strengthTone = computed(
    () =>
      ({ Strong: 'strong', Moderate: 'moderate', Limited: 'limited' })[
        props.plant.evidence.strength
      ],
  );
</script>

<template>
  <section class="passport" aria-labelledby="passport-heading">
    <header class="passport__header">
      <div>
        <p class="passport__eyebrow">PLANT PASSPORT</p>
        <h2 id="passport-heading">Everything we know about this plant</h2>
      </div>
      <span class="passport__strength" :class="`passport__strength--${strengthTone}`">
        <v-icon icon="mdi-shield-check-outline" size="18" aria-hidden="true" />
        {{ plant.evidence.strength }} evidence
        <InfoTip term="evidenceStrength" />
      </span>
    </header>

    <div class="passport__grid">
      <article class="passport__card">
        <h3>
          <v-icon icon="mdi-check-circle-outline" size="20" aria-hidden="true" /> What we know
        </h3>
        <ul>
          <li v-for="line in known" :key="line">{{ line }}</li>
        </ul>
      </article>
      <article v-if="unknown.length" class="passport__card passport__card--muted">
        <h3>
          <v-icon icon="mdi-help-circle-outline" size="20" aria-hidden="true" /> What we don’t know
          yet
        </h3>
        <ul>
          <li v-for="line in unknown" :key="line">{{ line }}</li>
        </ul>
      </article>
    </div>

    <article v-if="risky" class="passport__card passport__card--caution">
      <h3>
        <v-icon icon="mdi-fence" size="20" aria-hidden="true" /> Already have it? Keep it in your
        garden
      </h3>
      <ul v-if="containment.length">
        <li v-for="line in containment" :key="line">{{ line }}</li>
      </ul>
      <p class="passport__label">General steps for any risky plant</p>
      <ul>
        <li v-for="step in GENERAL_CONTAINMENT_STEPS" :key="step">{{ step }}</li>
      </ul>
    </article>

    <article v-else-if="growing.length || guidance" class="passport__card passport__card--grow">
      <h3><v-icon icon="mdi-shovel" size="20" aria-hidden="true" /> Growing it</h3>
      <ul v-if="growing.length">
        <li v-for="line in growing" :key="line">{{ line }}</li>
      </ul>
      <template v-if="guidance">
        <p class="passport__label">General guidance</p>
        <p class="passport__guidance">{{ guidance }}</p>
      </template>
      <p class="passport__label">For watering and soil advice, ask a local indigenous nursery.</p>
    </article>

    <footer class="passport__footer">
      <a v-if="plant.vicflora_url" :href="plant.vicflora_url" target="_blank" rel="noopener">
        Full description on VicFlora
        <v-icon icon="mdi-open-in-new" size="16" aria-hidden="true" />
      </a>
      <span>Sources: VicFlora, 2022 Advisory List, VBA, ALA, AusTraits</span>
    </footer>
  </section>
</template>

<style scoped>
  .passport {
    margin-top: var(--space-xl);
    padding: var(--space-lg);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    background: var(--color-surface);
  }

  .passport__header {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--space-md);
    margin-bottom: var(--space-md);
  }

  .passport__eyebrow {
    margin: 0 0 var(--space-xs);
    color: var(--color-accent);
    font-size: 0.75rem;
    font-weight: 800;
    letter-spacing: 0.12em;
  }

  .passport__header h2 {
    margin: 0;
    font-size: clamp(1.5rem, 3vw, 2rem);
  }

  .passport__strength {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border-radius: var(--radius-pill);
    font-size: 0.875rem;
    font-weight: 700;
  }

  .passport__strength--strong {
    background: var(--color-success-soft);
    color: var(--color-primary);
  }

  .passport__strength--moderate {
    background: var(--color-surface-muted);
    color: var(--color-ink);
  }

  .passport__strength--limited {
    background: var(--color-accent-soft);
    color: var(--color-accent);
  }

  .passport__grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: var(--space-md);
  }

  .passport__card {
    padding: var(--space-md) var(--space-lg);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-canvas);
  }

  .passport__card + .passport__card,
  .passport__grid + .passport__card {
    margin-top: var(--space-md);
  }

  .passport__grid .passport__card {
    margin-top: 0;
  }

  .passport__card--muted {
    background: var(--color-surface-muted);
  }

  .passport__card--caution {
    border-color: color-mix(in srgb, var(--color-accent) 40%, var(--color-border));
    background: var(--color-accent-soft);
  }

  .passport__card--grow {
    border-color: color-mix(in srgb, var(--color-primary) 30%, var(--color-border));
    background: var(--color-success-soft);
  }

  .passport__card h3 {
    display: flex;
    align-items: center;
    gap: var(--space-xs);
    margin: 0 0 var(--space-sm);
    color: var(--color-primary);
    font-family: var(--font-body);
    font-size: 1rem;
    font-weight: 700;
  }

  .passport__card--caution h3 {
    color: var(--color-accent);
  }

  .passport__card ul {
    display: grid;
    gap: 6px;
    margin: 0;
    padding-left: 1.2rem;
    color: var(--color-ink-soft);
    line-height: 1.5;
  }

  .passport__label {
    margin: var(--space-md) 0 var(--space-xs);
    color: var(--color-muted);
    font-size: 0.8125rem;
    font-weight: 700;
  }

  .passport__guidance {
    margin: 0;
    color: var(--color-ink-soft);
    line-height: 1.5;
  }

  .passport__footer {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-sm);
    margin-top: var(--space-md);
    color: var(--color-muted);
    font-size: 0.8125rem;
  }

  .passport__footer a {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    color: var(--color-primary);
    font-weight: 700;
  }
</style>
