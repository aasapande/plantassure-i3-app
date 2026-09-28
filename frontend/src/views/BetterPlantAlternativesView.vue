<script setup lang="ts">
  import { storeToRefs } from 'pinia';
  import { computed, ref, watch } from 'vue';
  import { RouterLink, useRoute, useRouter } from 'vue-router';

  import AlternativePlantCard from '@/components/alternatives/AlternativePlantCard.vue';
  import AlternativesEmptyState from '@/components/alternatives/AlternativesEmptyState.vue';
  import CurrentPlantSummary from '@/components/alternatives/CurrentPlantSummary.vue';
  import TermCards from '@/components/common/TermCards.vue';
  import AppFooter from '@/components/layout/AppFooter.vue';
  import AppHeader from '@/components/layout/AppHeader.vue';
  import { usePlantAlternativesStore } from '@/stores/alternatives';

  const route = useRoute();
  const router = useRouter();
  const alternativesStore = usePlantAlternativesStore();
  const { alternatives, currentPlant, error, hasLoaded, isLoading, status } =
    storeToRefs(alternativesStore);
  const selectedPlantIds = ref<number[]>([]);

  const plantId = computed<number | null>(() => {
    const value = Number(route.params.plantId);

    return Number.isSafeInteger(value) && value > 0 ? value : null;
  });
  const selectedCount = computed(() => selectedPlantIds.value.length);
  // The original plant is always included, so users pick up to 2 alternatives.
  const MAX_SELECTED = 2;
  const originalName = computed(
    () => currentPlant.value?.commonName ?? currentPlant.value?.scientificName ?? 'your plant',
  );
  const selectedNames = computed(() =>
    selectedPlantIds.value
      .map((id) => alternatives.value.find((plant) => plant.plantId === id))
      .map((plant) => plant?.commonName ?? plant?.scientificName)
      .filter(Boolean)
      .join(' and '),
  );

  function loadAlternatives(id: number | null) {
    selectedPlantIds.value = [];

    if (id !== null) void alternativesStore.fetchAlternatives(id);
  }

  watch(plantId, loadAlternatives, { immediate: true });

  watch([alternatives, isLoading], ([plants, loading]) => {
    if (loading) return;

    const availablePlantIds = new Set(plants.map((plant) => plant.plantId));
    selectedPlantIds.value = selectedPlantIds.value.filter((id) => availablePlantIds.has(id));
  });

  function toggleCompare(id: number) {
    if (selectedPlantIds.value.includes(id)) {
      selectedPlantIds.value = selectedPlantIds.value.filter((plantId) => plantId !== id);
      return;
    }

    if (selectedPlantIds.value.length >= MAX_SELECTED) return;
    selectedPlantIds.value = [...selectedPlantIds.value, id];
  }

  function openComparison(alternativeIds: number[]) {
    if (plantId.value === null || !alternativeIds.length) return;

    void router.push({
      name: 'plant-comparison',
      query: {
        plants: [plantId.value, ...alternativeIds].join(','),
        fromPlantId: String(plantId.value),
      },
    });
  }

  function compareSelected() {
    openComparison(selectedPlantIds.value);
  }

  function compareOne(id: number) {
    openComparison([id]);
  }

  function retryAlternatives() {
    if (plantId.value !== null) void alternativesStore.fetchAlternatives(plantId.value);
  }

  function browsePlants() {
    void router.push({ name: 'plant-catalog' });
  }

  function goToSearch() {
    void router.push({ name: 'home', hash: '#plant-search-input' });
  }
</script>

<template>
  <div class="alternatives-page">
    <AppHeader @check-plant="goToSearch" />

    <main class="alternatives-main">
      <div class="app-container">
        <RouterLink
          v-if="plantId !== null"
          class="alternatives-back-link"
          :to="{ name: 'plant-assessment', params: { plantId } }"
        >
          <v-icon icon="mdi-arrow-left" size="18" aria-hidden="true" />
          Back to assessment
        </RouterLink>

        <header class="alternatives-intro">
          <p class="alternatives-eyebrow">BETTER PLANT OPTIONS</p>
          <h1>Find a better plant</h1>
          <p>
            Similar plants that aren’t rated as weed risks. Some are rated Lower on Victoria’s weed
            list; others haven’t been rated yet, so check the rating on each card.
          </p>
        </header>

        <CurrentPlantSummary
          v-if="plantId !== null && currentPlant"
          :common-name="currentPlant.commonName"
          :scientific-name="currentPlant.scientificName"
          :image-url="currentPlant.imageUrl"
          :image-credit="currentPlant.imageCredit"
          :image-page-url="currentPlant.imagePageUrl"
          :environmental-concern="currentPlant.environmentalConcern"
          :growth-form="currentPlant.growthForm"
          :life-history="currentPlant.lifeHistory"
          :height="currentPlant.height"
        />

        <section class="alternatives-results" aria-labelledby="alternatives-title">
          <div class="alternatives-results__header">
            <div>
              <p class="alternatives-eyebrow">ALTERNATIVES</p>
              <h2 id="alternatives-title">Consider these options</h2>
            </div>
          </div>
          <p v-if="hasLoaded && alternatives.length" class="alternatives-compare-hint">
            <v-icon icon="mdi-compare-horizontal" size="20" aria-hidden="true" />
            <span>
              Tap <strong>Compare side by side</strong> to see a plant next to {{ originalName }},
              or tick <strong>Select to compare</strong> on two plants to compare all three.
            </span>
          </p>

          <v-alert v-if="plantId === null" type="warning" variant="tonal">
            We couldn’t find that plant.
          </v-alert>
          <div v-else-if="isLoading" class="alternatives-status" aria-live="polite">
            <v-progress-circular
              indeterminate
              color="primary"
              size="28"
              :width="3"
              aria-hidden="true"
            />
            <span>Loading alternative plants…</span>
          </div>
          <v-alert v-else-if="error" type="error" variant="tonal">
            {{ error }}
            <template #append>
              <v-btn color="primary" variant="outlined" size="small" @click="retryAlternatives">
                Try again
              </v-btn>
            </template>
          </v-alert>
          <div v-else-if="hasLoaded && alternatives.length" class="alternatives-grid">
            <AlternativePlantCard
              v-for="plant in alternatives"
              :key="plant.plantId"
              :plant-id="plant.plantId"
              :common-name="plant.commonName"
              :scientific-name="plant.scientificName"
              :image-url="plant.imageUrl"
              :image-credit="plant.imageCredit"
              :image-page-url="plant.imagePageUrl"
              :environmental-concern="plant.environmentalConcern"
              :origin-status="plant.originStatus"
              :legal-status="plant.legalStatus"
              :match-reasons="plant.matchReasons"
              :growth-form="plant.growthForm"
              :life-history="plant.lifeHistory"
              :height="plant.height"
              :selected="selectedPlantIds.includes(plant.plantId)"
              :compare-disabled="
                selectedCount >= MAX_SELECTED && !selectedPlantIds.includes(plant.plantId)
              "
              :original-name="originalName"
              @select="(id) => router.push({ name: 'plant-assessment', params: { plantId: id } })"
              @toggle-compare="toggleCompare"
              @compare-now="compareOne"
            />
          </div>
          <AlternativesEmptyState
            v-else-if="hasLoaded && currentPlant"
            :status="status"
            @browse="browsePlants"
          />
        </section>

        <div
          v-if="selectedCount"
          class="compare-bar"
          role="region"
          aria-label="Plants selected to compare"
        >
          <div class="compare-bar__inner">
            <p class="compare-bar__text">
              <v-icon icon="mdi-compare-horizontal" size="22" aria-hidden="true" />
              <span>
                Compare <strong>{{ originalName }}</strong> with
                <strong>{{ selectedNames }}</strong>
                <span v-if="selectedCount < MAX_SELECTED" class="compare-bar__more">
                  · you can add one more
                </span>
              </span>
            </p>
            <div class="compare-bar__actions">
              <v-btn variant="text" color="primary" type="button" @click="selectedPlantIds = []">
                Clear
              </v-btn>
              <v-btn
                color="primary"
                variant="flat"
                size="large"
                append-icon="mdi-arrow-right"
                type="button"
                @click="compareSelected"
              >
                Compare now
              </v-btn>
            </div>
          </div>
        </div>

        <TermCards
          heading="How we pick these plants"
          :terms="['whyItMatches', 'growthForm', 'lifeHistory', 'height']"
        />
      </div>
    </main>

    <AppFooter />
  </div>
</template>

<style scoped>
  .alternatives-compare-hint {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    margin: 0 0 var(--space-lg);
    padding: var(--space-sm) var(--space-md);
    border-radius: var(--radius-md);
    background: var(--color-success-soft);
    color: var(--color-ink);
    font-size: 0.9375rem;
  }

  .alternatives-compare-hint .v-icon {
    flex: none;
    color: var(--color-primary);
  }

  .compare-bar {
    position: sticky;
    bottom: var(--space-md);
    z-index: 5;
    margin-top: var(--space-lg);
  }

  .compare-bar__inner {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-sm) var(--space-md);
    padding: var(--space-md) var(--space-lg);
    border: 2px solid var(--color-primary);
    border-radius: var(--radius-lg);
    background: var(--color-surface);
    box-shadow: 0 12px 32px rgb(0 0 0 / 18%);
  }

  .compare-bar__text {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    margin: 0;
    color: var(--color-ink);
  }

  .compare-bar__text .v-icon {
    flex: none;
    color: var(--color-primary);
  }

  .compare-bar__more {
    color: var(--color-muted);
  }

  .compare-bar__actions {
    display: flex;
    align-items: center;
    gap: var(--space-xs);
  }
  .alternatives-page {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    background: var(--color-canvas);
  }

  .alternatives-main {
    flex: 1;
    padding-block: var(--space-xl) var(--space-4xl);
  }

  .alternatives-back-link {
    display: inline-flex;
    min-height: 44px;
    align-items: center;
    gap: var(--space-xs);
    color: var(--color-primary);
    font-size: 1rem;
    font-weight: 700;
    text-decoration: none;
  }

  .alternatives-back-link:hover {
    text-decoration: underline;
    text-underline-offset: 4px;
  }

  .alternatives-intro {
    max-width: 42rem;
    margin: var(--space-2xl) 0 var(--space-2xl);
  }

  .alternatives-eyebrow {
    margin: 0 0 var(--space-sm);
    color: var(--color-accent);
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.1em;
  }

  .alternatives-intro h1,
  .alternatives-results h2 {
    margin: 0;
    color: var(--color-primary);
  }

  .alternatives-intro h1 {
    font-size: clamp(2.75rem, 6vw, 4.5rem);
    line-height: 0.98;
  }

  .alternatives-intro > p:last-child {
    margin: var(--space-md) 0 0;
    color: var(--color-ink-soft);
    font-size: 1.0625rem;
  }

  .alternatives-results {
    margin-top: var(--space-3xl);
  }

  .alternatives-results__header {
    display: flex;
    align-items: end;
    justify-content: space-between;
    gap: var(--space-lg);
    margin-bottom: var(--space-lg);
  }

  .alternatives-results__header .alternatives-eyebrow {
    margin-bottom: var(--space-xs);
  }

  .alternatives-results h2 {
    font-size: 2rem;
    line-height: 1.1;
  }

  .alternatives-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: var(--space-lg);
  }

  .alternatives-status {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    padding-block: var(--space-md);
    color: var(--color-ink-soft);
    font-size: 0.875rem;
  }

  @media (max-width: 999px) {
    .alternatives-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 767px) {
    .alternatives-main {
      padding-block: var(--space-lg) var(--space-3xl);
    }

    .alternatives-intro {
      margin-block: var(--space-xl);
    }

    .alternatives-results {
      margin-top: var(--space-2xl);
    }

    .alternatives-results__header {
      align-items: start;
      flex-direction: column;
    }

    .alternatives-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
