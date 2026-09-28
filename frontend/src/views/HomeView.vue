<script setup lang="ts">
  import { nextTick, onMounted, ref } from 'vue';
  import { useRoute, useRouter } from 'vue-router';

  import heroImageUrl from '@/assets/images/home-hero-botanical.png';
  import whyItMattersImageUrl from '@/assets/images/why-it-matters-garden.png';
  import InfoTip from '@/components/common/InfoTip.vue';
  import TermCards from '@/components/common/TermCards.vue';
  import AppFooter from '@/components/layout/AppFooter.vue';
  import AppHeader from '@/components/layout/AppHeader.vue';
  import CtaBanner from '@/components/layout/CtaBanner.vue';
  import PlantSearchInput from '@/components/search/PlantSearchInput.vue';

  const searchInput = ref<InstanceType<typeof PlantSearchInput> | null>(null);
  const route = useRoute();
  const router = useRouter();

  const processSteps = [
    { title: 'Find your plant', description: 'Search by name or browse the catalogue.' },
    { title: 'Check its rating', description: 'See if it can spread into local bushland.' },
    { title: 'Find an alternative', description: 'See similar plants not rated as weed risks.' },
  ];

  // Figures from the Iteration 2 dataset (output_i2.csv); update if the data changes.
  const highlights = [
    { value: '880', label: 'Monash plants you can search', icon: 'mdi-magnify' },
    { value: '325', label: 'rated on Victoria’s weed list', icon: 'mdi-clipboard-check-outline' },
    { value: '3', label: 'official data sources', icon: 'mdi-database-outline' },
  ];

  function focusSearch() {
    searchInput.value?.focusInput();
  }

  function browsePlants() {
    void router.push({ name: 'plant-catalog' });
  }

  function identifyFromPhoto() {
    void router.push({ name: 'plant-identification' });
  }

  onMounted(async () => {
    if (route.hash !== '#plant-search-input') return;
    await nextTick();
    focusSearch();
  });
</script>

<template>
  <div id="top" class="home-page">
    <AppHeader @check-plant="focusSearch" />

    <main>
      <section class="hero" aria-labelledby="home-title">
        <div class="app-container hero__inner">
          <div class="hero__content">
            <div class="hero__content-inner">
              <p class="eyebrow">CITY OF MONASH · PLANT ASSESSMENT TOOL</p>
              <h1 id="home-title">Check before<br />you plant</h1>
              <p class="hero__description">Find out if a plant is safe to grow in Monash.</p>
              <PlantSearchInput ref="searchInput" />
              <div class="hero__secondary-actions">
                <v-btn
                  class="plant-btn--secondary"
                  color="primary"
                  variant="outlined"
                  height="52"
                  block
                  prepend-icon="mdi-view-grid-outline"
                  @click="browsePlants"
                >
                  Browse plant catalogue
                </v-btn>
                <v-btn
                  class="plant-btn--secondary"
                  color="primary"
                  variant="outlined"
                  height="52"
                  block
                  prepend-icon="mdi-camera-outline"
                  @click="identifyFromPhoto"
                >
                  Identify from Photo
                </v-btn>
              </div>
              <p class="hero__helper">
                The catalogue shows plants rated on Victoria’s weed list. Search covers every plant.
              </p>
            </div>
          </div>
          <div class="hero__visual">
            <v-img
              class="hero__image"
              :src="heroImageUrl"
              alt=""
              aria-hidden="true"
              cover
              position="right center"
            />
            <section id="how-it-works" class="how-card" aria-labelledby="process-title">
              <h2 id="process-title">How it works</h2>
              <ol class="how-card__steps">
                <li v-for="(step, index) in processSteps" :key="step.title">
                  <span class="how-card__number" aria-hidden="true">{{ index + 1 }}</span>
                  <div>
                    <h3>{{ step.title }}</h3>
                    <p>{{ step.description }}</p>
                  </div>
                </li>
              </ol>
            </section>
          </div>
        </div>
      </section>

      <section class="highlights" aria-label="PlantAssure at a glance">
        <ul class="app-container highlights__list">
          <li v-for="item in highlights" :key="item.label" class="highlights__item">
            <v-icon :icon="item.icon" size="26" aria-hidden="true" />
            <strong>{{ item.value }}</strong>
            <span>{{ item.label }}</span>
          </li>
        </ul>
      </section>

      <section class="basics-section" aria-label="Plant basics">
        <div class="app-container">
          <TermCards
            heading="Plant basics"
            variant="feature"
            :terms="['native', 'introduced', 'naturalised', 'environmentalConcern']"
          />
        </div>
      </section>

      <section id="why-it-matters" class="why-section" aria-labelledby="why-title">
        <div class="app-container why-grid">
          <div class="why-image">
            <v-img
              :src="whyItMattersImageUrl"
              alt="Potted native and garden plants grouped together"
              cover
            />
          </div>
          <div class="why-content">
            <p class="why-eyebrow">WHY THIS MATTERS</p>
            <h2 id="why-title">Small planting choices can have wider impacts</h2>
            <ul class="why-list">
              <li>
                <v-icon icon="mdi-leaf" size="18" aria-hidden="true" />
                Some garden plants escape and spread into local bushland.
              </li>
              <li>
                <v-icon icon="mdi-leaf" size="18" aria-hidden="true" />
                We bring official plant data together in one place.
              </li>
            </ul>
            <div class="why-sources">
              <p class="why-sources__label">Where our data comes from</p>
              <ul>
                <li>
                  <v-icon icon="mdi-book-open-page-variant-outline" size="18" aria-hidden="true" />
                  <span>VicFlora</span>
                  <InfoTip term="vicflora" />
                </li>
                <li>
                  <v-icon icon="mdi-map-marker-radius-outline" size="18" aria-hidden="true" />
                  <span>Victorian Biodiversity Atlas</span>
                  <InfoTip term="vba" />
                </li>
                <li>
                  <v-icon icon="mdi-clipboard-list-outline" size="18" aria-hidden="true" />
                  <span>2022 Advisory List</span>
                  <InfoTip term="advisoryList" />
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      <section class="cta-section">
        <div class="app-container">
          <CtaBanner
            title="Thinking about planting something? Check it first."
            description="It takes a few seconds to search any plant in Monash."
            @action="focusSearch"
          />
        </div>
      </section>
    </main>
    <AppFooter />
  </div>
</template>

<style scoped>
  .eyebrow {
    margin: 0 0 var(--space-sm);
    color: var(--color-accent);
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.1em;
  }
  .hero {
    position: relative;
  }
  .hero::before,
  .hero::after {
    content: '';
    position: absolute;
    right: 0;
    left: 0;
    z-index: 3;
    height: 1px;
    background: color-mix(in srgb, var(--color-border) 60%, transparent);
    pointer-events: none;
  }
  .hero::before {
    top: -1px;
  }
  .hero::after {
    bottom: 0;
  }
  .hero__inner {
    --hero-grid-gutter: max(var(--space-xl), calc((100vw - var(--content-max-width)) / 2));

    width: 100%;
    max-width: none;
    min-height: 600px;
    display: grid;
    grid-template-columns:
      minmax(0, calc(56vw - var(--hero-grid-gutter)))
      minmax(0, 44vw);
    align-items: center;
    padding-left: var(--hero-grid-gutter);
  }
  .hero__content {
    width: 100%;
    display: flex;
    align-items: center;
    padding: var(--space-3xl) var(--space-2xl) var(--space-3xl) 0;
  }
  .hero__content-inner {
    width: 100%;
    max-width: 560px;
  }
  .hero h1 {
    max-width: 9ch;
    margin: 0;
    font-size: 3.25rem;
    line-height: 1.05;
    letter-spacing: -0.025em;
  }
  .hero__description {
    max-width: 520px;
    margin: var(--space-md) 0 var(--space-lg);
    color: var(--color-ink-soft);
    font-size: 1.0625rem;
    line-height: 1.6;
  }
  .hero__secondary-actions {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--space-md);
    margin-top: var(--space-md);
  }
  .hero__helper {
    display: flex;
    align-items: center;
    max-width: 460px;
    margin: var(--space-sm) 0 0;
    color: var(--color-muted);
    font-size: 0.8125rem;
    line-height: 1.55;
  }
  @media (max-width: 1199px) {
    .hero__inner {
      width: min(100% - 48px, var(--hero-max-width));
      max-width: var(--hero-max-width);
      min-height: 470px;
      grid-template-columns: minmax(0, 60fr) minmax(0, 40fr);
      padding-left: 0;
    }
    .hero__content {
      padding: var(--space-2xl) var(--space-xl) var(--space-2xl) 0;
    }
  }
  @media (max-width: 899px) {
    .hero__inner {
      min-height: auto;
      grid-template-columns: 1fr;
    }
    .hero__content {
      width: 100%;
      padding: var(--space-2xl) 0 var(--space-xl);
    }
  }
  @media (max-width: 767px) {
    .hero__inner {
      width: calc(100% - 32px);
    }
    .hero h1 {
      font-size: 2.75rem;
    }
    .hero__description {
      font-size: 1rem;
    }
    .hero__secondary-actions {
      grid-template-columns: 1fr;
    }
  }

  .hero__visual {
    position: relative;
    display: flex;
    min-height: 100%;
    align-items: flex-end;
    padding: var(--space-2xl) var(--space-xl) var(--space-2xl) 0;
  }
  .hero__visual :deep(.hero__image) {
    position: absolute;
    inset: 0;
    -webkit-mask-image: linear-gradient(90deg, transparent 0%, #000 28%);
    mask-image: linear-gradient(90deg, transparent 0%, #000 28%);
  }
  .how-card {
    position: relative;
    z-index: 1;
    width: 100%;
    max-width: 380px;
    padding: var(--space-lg);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    background: color-mix(in srgb, var(--color-surface) 88%, transparent);
    backdrop-filter: blur(8px);
    box-shadow: 0 16px 40px rgb(0 0 0 / 12%);
    scroll-margin-top: 96px;
  }
  .how-card h2 {
    margin: 0 0 var(--space-md);
    font-size: 1.5rem;
    line-height: 1.1;
  }
  .how-card__steps {
    display: grid;
    gap: var(--space-md);
    margin: 0;
    padding: 0;
    list-style: none;
  }
  .how-card__steps li {
    display: flex;
    align-items: flex-start;
    gap: var(--space-sm);
  }
  .how-card__number {
    width: 36px;
    height: 36px;
    display: grid;
    flex: none;
    place-items: center;
    background: var(--color-success-soft);
    border-radius: var(--radius-pill);
    color: var(--color-primary);
    font-weight: 700;
  }
  .how-card__steps li:nth-child(2) .how-card__number {
    background: var(--color-accent-soft);
    color: var(--color-accent);
  }
  .how-card h3 {
    margin: 0;
    font-family: var(--font-body);
    font-size: 1rem;
    font-weight: 700;
  }
  .how-card p {
    margin: 2px 0 0;
    color: var(--color-ink-soft);
    font-size: 0.9375rem;
    line-height: 1.45;
  }
  .highlights {
    border-block: 1px solid var(--color-border);
    background: var(--color-surface);
  }
  .highlights__list {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin-block: 0;
    padding-block: var(--space-lg);
    list-style: none;
  }
  .highlights__item {
    display: grid;
    grid-template-columns: auto 1fr;
    grid-template-rows: auto auto;
    column-gap: var(--space-sm);
    align-items: center;
    justify-content: center;
    padding-inline: var(--space-md);
  }
  .highlights__item + .highlights__item {
    border-left: 1px solid var(--color-border);
  }
  .highlights__item .v-icon {
    grid-row: 1 / span 2;
    color: var(--color-accent);
  }
  .highlights__item strong {
    color: var(--color-primary);
    font-family: var(--font-display);
    font-size: 2rem;
    font-weight: 400;
    line-height: 1;
  }
  .highlights__item span {
    color: var(--color-ink-soft);
    font-size: 0.875rem;
  }
  .basics-section {
    padding-block: var(--space-xl) var(--space-2xl);
  }
  .why-section {
    padding-block: var(--space-2xl) clamp(var(--space-2xl), 5vw, var(--space-3xl));
    scroll-margin-top: 96px;
  }
  .why-grid {
    display: grid;
    grid-template-columns: minmax(0, 42fr) minmax(0, 58fr);
    align-items: center;
    gap: clamp(var(--space-xl), 5vw, var(--space-3xl));
  }
  .why-image {
    aspect-ratio: 4 / 3;
    overflow: hidden;
    border-radius: var(--radius-lg);
    background: var(--color-surface-muted);
  }
  .why-image :deep(.v-img) {
    height: 100%;
  }
  .why-eyebrow {
    margin: 0 0 var(--space-sm);
    color: var(--color-accent);
    font-size: 0.75rem;
    font-weight: 800;
    letter-spacing: 0.12em;
  }
  .why-content h2 {
    max-width: 20ch;
    margin: 0 0 var(--space-lg);
    font-size: clamp(1.75rem, 3.5vw, 2.25rem);
    line-height: 1.15;
  }
  .why-list {
    display: grid;
    gap: var(--space-sm);
    margin: 0 0 var(--space-lg);
    padding: 0;
    list-style: none;
  }
  .why-list li {
    display: flex;
    align-items: flex-start;
    gap: var(--space-sm);
    color: var(--color-ink-soft);
    line-height: 1.5;
  }
  .why-list .v-icon {
    flex: 0 0 auto;
    margin-top: 3px;
    color: var(--color-primary);
  }
  .why-sources {
    padding: var(--space-md) var(--space-lg);
    border-radius: var(--radius-md);
    background: var(--color-surface-muted);
  }
  .why-sources__label {
    margin: 0 0 var(--space-sm);
    color: var(--color-ink);
    font-size: 0.875rem;
    font-weight: 700;
  }
  .why-sources ul {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-xs) var(--space-lg);
    margin: 0;
    padding: 0;
    list-style: none;
  }
  .why-sources li {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: var(--color-ink-soft);
    font-size: 0.875rem;
  }
  .why-sources .v-icon {
    color: var(--color-primary);
  }
  .cta-section {
    padding-block: 0 clamp(var(--space-2xl), 5vw, var(--space-3xl));
  }
  @media (max-width: 899px) {
    .hero__visual {
      flex-direction: column;
      align-items: stretch;
      padding: 0 0 var(--space-xl);
    }
    .hero__visual :deep(.hero__image) {
      display: none;
    }
    .how-card {
      max-width: none;
    }
    .why-grid {
      grid-template-columns: 1fr;
    }
    .why-image {
      aspect-ratio: 16 / 9;
    }
  }
  @media (max-width: 767px) {
    .highlights__list {
      grid-template-columns: 1fr;
      gap: var(--space-sm);
    }
    .highlights__item {
      justify-content: start;
    }
    .highlights__item + .highlights__item {
      border-left: 0;
    }
  }
</style>
