<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';
  import { useRouter } from 'vue-router';

  import { getInsights } from '@/api/passport';
  import AppFooter from '@/components/layout/AppFooter.vue';
  import AppHeader from '@/components/layout/AppHeader.vue';
  import type { InsightsResponse } from '@/types/passport';

  // Charts use numbers calculated in MySQL by the backend (GET /insights).
  const router = useRouter();
  const data = ref<InsightsResponse | null>(null);
  const loadError = ref(false);

  onMounted(async () => {
    try {
      data.value = await getInsights();
    } catch {
      loadError.value = true;
    }
  });

  const MONTHS = computed(() => data.value?.flowering.months ?? []);
  const MIN_GROUP_SIZE = computed(() => data.value?.minGroupSize ?? 30);

  const flowering = computed(() => {
    const counts = data.value?.flowering.counts ?? [];
    const max = Math.max(1, ...counts);
    return { counts, max, peak: counts.indexOf(Math.max(...counts)), total: data.value?.flowering.total ?? 0 };
  });

  const origin = computed(() => {
    const o = data.value?.origin ?? { introduced: 0, native: 0, total: 0 };
    return { ...o, introducedPct: Math.round((o.introduced / (o.total || 1)) * 100) };
  });

  const plantTypes = computed(() => data.value?.plantTypes ?? []);
</script>

<template>
  <div class="insights-page">
    <AppHeader @check-plant="router.push({ name: 'home', hash: '#plant-search-input' })" />

    <main class="app-container insights-main">
      <header>
        <p class="insights-eyebrow">DATA INSIGHTS</p>
        <h1>What the data tells Monash gardeners</h1>
      </header>

      <v-alert v-if="loadError" type="error" variant="tonal">
        We couldn’t load the data. Please refresh the page.
      </v-alert>

      <div v-else-if="data" class="insights-grid">
        <figure class="insight">
          <p class="insight__question">When should I act?</p>
          <h2>Risky plants in flower, by month</h2>
          <div
            class="month-bars"
            role="img"
            :aria-label="`Risky plants in flower each month; peak in ${MONTHS[flowering.peak]}`"
          >
            <div
              v-for="(count, index) in flowering.counts"
              :key="MONTHS[index]"
              class="month-bars__col"
            >
              <span class="month-bars__value">{{ count }}</span>
              <span
                class="month-bars__bar"
                :class="{ 'month-bars__bar--peak': index >= 8 && index <= 10 }"
                :style="{ height: `${(count / flowering.max) * 100}%` }"
              />
              <span class="month-bars__label">{{ MONTHS[index]?.charAt(0) }}</span>
            </div>
          </div>
          <figcaption>
            Most risky plants flower in spring (Sep–Nov): the time to cut off flowers before they
            seed. Based on {{ flowering.total }} risky plants with flowering records · AusTraits.
          </figcaption>
        </figure>

        <figure class="insight">
          <p class="insight__question">What kind of plants are risky?</p>
          <h2>Risky plants by origin</h2>
          <div
            class="split-bar"
            role="img"
            :aria-label="`${origin.introduced} introduced, ${origin.native} native`"
          >
            <span
              class="split-bar__part split-bar__part--introduced"
              :style="{ flexGrow: origin.introduced }"
            />
            <span
              class="split-bar__part split-bar__part--native"
              :style="{ flexGrow: origin.native }"
            />
          </div>
          <div class="split-legend">
            <span class="split-legend__introduced">Introduced · {{ origin.introduced }}</span>
            <span class="split-legend__native">Native · {{ origin.native }}</span>
          </div>
          <figcaption>
            {{ origin.introducedPct }}% of risky plants were brought to Victoria from elsewhere.
            Based on {{ origin.total }} risky plants · VicFlora, 2022 Advisory List.
          </figcaption>
        </figure>

        <figure class="insight">
          <p class="insight__question">Which plant types need most care?</p>
          <h2>Share of each plant type rated risky</h2>
          <div class="type-bars">
            <div v-for="group in plantTypes" :key="group.type" class="type-bars__row">
              <span>{{ group.type }}s</span>
              <span class="type-bars__track">
                <span
                  class="type-bars__fill"
                  :class="{ 'type-bars__fill--high': group.pct >= 50 }"
                  :style="{ width: `${group.pct}%` }"
                />
              </span>
              <span class="type-bars__pct">{{ group.pct }}%</span>
            </div>
          </div>
          <figcaption>
            Planting a tree? Check extra carefully. Groups under {{ MIN_GROUP_SIZE }} plants are
            left out · AusTraits, 2022 Advisory List.
          </figcaption>
        </figure>
      </div>
    </main>

    <AppFooter />
  </div>
</template>

<style scoped>
  .insights-page {
    display: flex;
    min-height: 100vh;
    flex-direction: column;
    background: var(--color-canvas);
  }

  .insights-main {
    flex: 1;
    padding-block: var(--space-xl) var(--space-3xl);
  }

  .insights-eyebrow {
    margin: 0 0 var(--space-xs);
    color: var(--color-accent);
    font-size: 0.75rem;
    font-weight: 800;
    letter-spacing: 0.12em;
  }

  .insights-main h1 {
    margin: 0 0 var(--space-lg);
    font-size: clamp(2rem, 4vw, 2.75rem);
  }

  .insights-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: var(--space-lg);
  }

  .insight {
    display: flex;
    flex-direction: column;
    margin: 0;
    padding: var(--space-lg);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    background: var(--color-surface);
  }

  .insight__question {
    margin: 0;
    color: var(--color-accent);
    font-size: 0.8125rem;
    font-weight: 700;
  }

  .insight h2 {
    margin: 2px 0 var(--space-md);
    font-family: var(--font-body);
    font-size: 1.0625rem;
    font-weight: 700;
  }

  .insight figcaption {
    margin-top: auto;
    padding-top: var(--space-md);
    color: var(--color-ink-soft);
    font-size: 0.8125rem;
    line-height: 1.5;
  }

  .month-bars {
    display: grid;
    grid-template-columns: repeat(12, minmax(0, 1fr));
    gap: 4px;
    height: 180px;
  }

  .month-bars__col {
    display: grid;
    grid-template-rows: auto 1fr auto;
    align-items: end;
    justify-items: center;
    min-width: 0;
  }

  .month-bars__value {
    color: var(--color-muted);
    font-size: 0.625rem;
  }

  .month-bars__bar {
    width: 100%;
    border-radius: 3px 3px 0 0;
    background: var(--color-border-strong);
  }

  .month-bars__bar--peak {
    background: var(--color-accent);
  }

  .month-bars__label {
    margin-top: 4px;
    color: var(--color-muted);
    font-size: 0.75rem;
  }

  .split-bar {
    display: flex;
    height: 36px;
    overflow: hidden;
    gap: 2px;
    border-radius: var(--radius-md);
  }

  .split-bar__part--introduced {
    background: var(--color-accent);
  }

  .split-bar__part--native {
    background: var(--color-primary);
  }

  .split-legend {
    display: flex;
    justify-content: space-between;
    margin-top: var(--space-xs);
    font-size: 0.875rem;
    font-weight: 700;
  }

  .split-legend__introduced {
    color: var(--color-accent);
  }

  .split-legend__native {
    color: var(--color-primary);
  }

  .type-bars {
    display: grid;
    gap: var(--space-sm);
  }

  .type-bars__row {
    display: grid;
    grid-template-columns: 70px minmax(0, 1fr) 40px;
    align-items: center;
    gap: var(--space-sm);
    font-size: 0.875rem;
  }

  .type-bars__track {
    height: 16px;
    overflow: hidden;
    border-radius: 4px;
    background: var(--color-surface-muted);
  }

  .type-bars__fill {
    display: block;
    height: 100%;
    background: #d9a441;
  }

  .type-bars__fill--high {
    background: #b5532e;
  }

  .type-bars__pct {
    color: var(--color-ink-soft);
    text-align: right;
  }
</style>
