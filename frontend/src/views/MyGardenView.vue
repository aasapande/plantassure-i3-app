<script setup lang="ts">
  import { storeToRefs } from 'pinia';
  import { computed, onMounted, ref, watch } from 'vue';
  import { RouterLink, useRoute, useRouter } from 'vue-router';

  import { getPassports } from '@/api/passport';
  import { getAlternatives } from '@/api/plants';
  import AppFooter from '@/components/layout/AppFooter.vue';
  import AppHeader from '@/components/layout/AppHeader.vue';
  import { useGardenStore } from '@/stores/garden';
  import type { PassportPlant } from '@/types/passport';
  import {
    containmentFacts,
    GENERAL_CONTAINMENT_STEPS,
    generalGuidance,
    growingFacts,
    isRisky,
    showsGrowingGuide,
  } from '@/utils/passportPresentation';

  const route = useRoute();
  const router = useRouter();
  const garden = useGardenStore();
  const { plants, gardenId, linkStatus, shareUrl, editUrl, viewing } = storeToRefs(garden);
  const passportData = ref<Record<number, PassportPlant>>({});
  const loadError = ref(false);
  const openingShared = ref(false);
  const sharedMissing = ref(false);
  const copied = ref<'share' | 'edit' | null>(null);
  const confirmingDelete = ref(false);
  const confirmingClear = ref(false);
  /** Swap names for risky plants, used in the printout. null = none found. */
  const swapIdeas = ref<Record<number, string[] | null>>({});

  /** True when showing someone else's garden from a share link (read-only). */
  const isViewing = computed(() => viewing.value !== null);
  const listPlants = computed(() => viewing.value?.plants ?? plants.value);

  async function loadPassports() {
    const missing = listPlants.value.map((p) => p.plantId).filter((id) => !passportData.value[id]);
    if (!missing.length) return;
    try {
      passportData.value = { ...passportData.value, ...(await getPassports(missing)) };
      loadError.value = false;
    } catch {
      loadError.value = true;
    }
  }

  const SWAPS_PER_PLANT = 3;

  async function loadSwapIdeas() {
    const risky = listPlants.value
      .map((p) => passportData.value[p.plantId])
      .filter((data): data is PassportPlant => !!data && isRisky(data))
      .filter((data) => !(data.plant_id in swapIdeas.value));
    await Promise.all(
      risky.map(async (data) => {
        try {
          const response = await getAlternatives(data.plant_id, { limit: SWAPS_PER_PLANT });
          swapIdeas.value = {
            ...swapIdeas.value,
            [data.plant_id]: response.alternatives.map(
              (alt) => alt.commonName ?? alt.scientificName,
            ),
          };
        } catch {
          // Leave it out; the printout falls back to general advice.
        }
      }),
    );
  }

  watch(
    () => listPlants.value.map((p) => p.plantId).join(','),
    () => void loadPassports(),
  );
  watch(passportData, () => void loadSwapIdeas());

  async function openFromRoute() {
    sharedMissing.value = false;
    const sharedId = route.params.gardenId;
    if (typeof sharedId !== 'string') {
      garden.stopViewing();
      await loadPassports();
      return;
    }
    const key = new URLSearchParams(route.hash.replace(/^#/, '')).get('edit');
    openingShared.value = true;
    const result = await garden.open(sharedId, key);
    openingShared.value = false;
    sharedMissing.value = result === 'missing';
    if (key) {
      // Take the private key out of the address bar so it isn't shared by accident.
      void router.replace({ name: 'shared-garden', params: { gardenId: sharedId } });
    }
    await loadPassports();
  }

  onMounted(() => void openFromRoute());
  watch(
    () => route.params.gardenId,
    () => void openFromRoute(),
  );

  async function getLink() {
    const url = await garden.createLink();
    if (url && gardenId.value) {
      void router.replace({ name: 'shared-garden', params: { gardenId: gardenId.value } });
    }
  }

  async function copyLink(which: 'share' | 'edit') {
    const url = which === 'share' ? shareUrl.value : editUrl.value;
    if (!url) return;
    try {
      await navigator.clipboard.writeText(url);
      copied.value = which;
      setTimeout(() => (copied.value = null), 2000);
    } catch {
      copied.value = null;
    }
  }

  function copyToMine() {
    garden.copyViewingToMine();
    void router.replace({ name: 'my-garden' });
  }

  async function deleteSaved() {
    if (await garden.deleteLink()) {
      confirmingDelete.value = false;
      void router.replace({ name: 'my-garden' });
    }
  }

  const RATINGS = [
    { key: 'Reconsider Planting', tone: 'concern' },
    { key: 'Use Caution', tone: 'caution' },
    { key: 'Lower Concern', tone: 'lower' },
    { key: 'Not Assessed', tone: 'neutral' },
  ] as const;

  const rows = computed(() =>
    listPlants.value.map((plant) => ({
      ...plant,
      data: passportData.value[plant.plantId] ?? null,
    })),
  );

  const breakdown = computed(() =>
    RATINGS.map((rating) => ({
      ...rating,
      count: rows.value.filter((row) => row.data?.recommendation === rating.key).length,
    })),
  );

  const riskyCount = computed(
    () => rows.value.filter((row) => row.data && isRisky(row.data)).length,
  );
  const nativeCount = computed(
    () => rows.value.filter((row) => row.data?.origin === 'native').length,
  );

  function toneFor(recommendation: string | undefined) {
    return RATINGS.find((rating) => rating.key === recommendation)?.tone ?? 'neutral';
  }

  // Tips open inside the garden list instead of sending users to another page.
  const openTips = ref<number[]>([]);

  function toggleTips(plantId: number) {
    openTips.value = openTips.value.includes(plantId)
      ? openTips.value.filter((id) => id !== plantId)
      : [...openTips.value, plantId];
  }

  interface GardenTips {
    kind: 'contain' | 'grow';
    button: string;
    facts: string[];
    generalLabel: string;
    general: string[];
    note?: string;
  }

  function tipsFor(data: PassportPlant | null): GardenTips | null {
    if (!data) return null;
    if (isRisky(data)) {
      return {
        kind: 'contain',
        button: 'How to keep it contained',
        facts: containmentFacts(data),
        generalLabel: 'For any risky plant',
        general: GENERAL_CONTAINMENT_STEPS,
      };
    }
    if (showsGrowingGuide(data)) {
      const guidance = generalGuidance(data);
      return {
        kind: 'grow',
        button: 'Growing tips',
        facts: growingFacts(data),
        generalLabel: data.plant_type
          ? `General guidance for ${data.plant_type.toLowerCase()}s`
          : 'General guidance',
        general: guidance ? [guidance] : [],
        note: 'For watering and soil advice, ask a local indigenous nursery.',
      };
    }
    return null;
  }

  function findSwap(plantId: number) {
    void router.push({ name: 'plant-alternatives', params: { plantId } });
  }

  function printGarden() {
    window.print();
  }

  function clearGarden() {
    garden.clear();
    confirmingClear.value = false;
  }
</script>

<template>
  <div class="garden-page">
    <AppHeader @check-plant="router.push({ name: 'home', hash: '#plant-search-input' })" />

    <main class="app-container garden-main">
      <header class="garden-intro">
        <p class="garden-eyebrow">MY GARDEN</p>
        <h1>{{ isViewing ? 'A shared garden' : 'Your garden check-up' }}</h1>
        <p class="garden-privacy">
          <v-icon icon="mdi-lock-outline" size="16" aria-hidden="true" />
          We save only the plants on your list, never your name or personal details.
        </p>
      </header>

      <v-alert v-if="openingShared" type="info" variant="tonal" class="garden-alert">
        Opening saved garden…
      </v-alert>
      <v-alert
        v-if="isViewing"
        type="info"
        variant="tonal"
        class="garden-alert"
        title="You’re viewing someone’s shared garden"
      >
        You can look at these plants and their tips, but you can’t change this garden.
        <div class="garden-alert__actions">
          <v-btn color="primary" variant="flat" size="small" @click="copyToMine">
            Copy these plants to my garden
          </v-btn>
          <v-btn color="primary" variant="text" size="small" :to="{ name: 'my-garden' }">
            Go to my garden
          </v-btn>
        </div>
      </v-alert>
      <v-alert
        v-if="linkStatus === 'expired' || sharedMissing"
        type="warning"
        variant="tonal"
        class="garden-alert"
        title="This garden link is no longer available"
      >
        It may have been deleted, or it wasn’t changed for 90 days. You can start a new garden
        below.
      </v-alert>

      <section v-if="!listPlants.length && !openingShared" class="garden-empty">
        <v-icon icon="mdi-sprout-outline" size="40" aria-hidden="true" />
        <h2>Your garden is empty</h2>
        <p>Add plants from any plant page to check your whole garden at once.</p>
        <div class="garden-empty__actions">
          <v-btn color="primary" variant="flat" :to="{ name: 'home', hash: '#plant-search-input' }">
            Search plants
          </v-btn>
          <v-btn color="primary" variant="outlined" :to="{ name: 'plant-catalog' }">
            Browse plant catalogue
          </v-btn>
        </div>
      </section>

      <template v-if="listPlants.length">
        <v-alert v-if="loadError" type="error" variant="tonal" class="garden-alert">
          We couldn’t load plant details. Please refresh the page.
        </v-alert>

        <section class="garden-summary" aria-labelledby="summary-heading">
          <h2 id="summary-heading" class="visually-hidden">Garden summary</h2>
          <div class="garden-stats">
            <div class="garden-stat">
              <strong>{{ rows.length }}</strong>
              <span>{{ isViewing ? 'plants in this garden' : 'plants in your garden' }}</span>
            </div>
            <div class="garden-stat garden-stat--concern">
              <strong>{{ riskyCount }}</strong>
              <span>need attention</span>
            </div>
            <div class="garden-stat garden-stat--lower">
              <strong>{{ nativeCount }}</strong>
              <span>are native to Victoria</span>
            </div>
          </div>

          <div
            class="garden-bar"
            role="img"
            :aria-label="breakdown.map((b) => `${b.key}: ${b.count}`).join(', ')"
          >
            <span
              v-for="item in breakdown.filter((b) => b.count)"
              :key="item.key"
              :class="`garden-bar__part garden-bar__part--${item.tone}`"
              :style="{ flexGrow: item.count }"
            />
          </div>
          <ul class="garden-legend">
            <li v-for="item in breakdown" :key="item.key">
              <span :class="`garden-dot garden-dot--${item.tone}`" aria-hidden="true" />
              {{ item.key }} · {{ item.count }}
            </li>
          </ul>
        </section>
      </template>

      <!-- Stays visible after clearing, so the saved links are never hidden. -->
      <section
        v-if="!isViewing && !openingShared && (listPlants.length || gardenId)"
        class="garden-link"
        aria-labelledby="link-heading"
      >
        <div class="garden-link__text">
          <h2 id="link-heading">
            <v-icon icon="mdi-link-variant" size="20" aria-hidden="true" />
            {{ gardenId ? 'Your saved garden' : 'Save your garden' }}
          </h2>
          <p v-if="!gardenId">
            Get a private link to open this list later or on another device. Only the plants are
            saved, never your name or details.
          </p>
          <p v-else>Changes save automatically. Unused gardens are deleted after 90 days.</p>
        </div>

        <div v-if="!gardenId" class="garden-link__actions">
          <v-btn
            color="primary"
            variant="flat"
            prepend-icon="mdi-link-plus"
            :loading="linkStatus === 'saving'"
            @click="getLink"
          >
            Get a private link
          </v-btn>
        </div>
        <template v-else>
          <div class="garden-link__row">
            <p class="garden-link__label">
              <v-icon icon="mdi-eye-outline" size="18" aria-hidden="true" />
              Share link · view only
            </p>
            <p class="garden-link__hint">
              Anyone with this link can see your plants, but can’t change them.
            </p>
            <div class="garden-link__actions">
              <input
                class="garden-link__url"
                :value="shareUrl"
                readonly
                aria-label="Share link, view only"
                @focus="($event.target as HTMLInputElement).select()"
              />
              <v-btn
                color="primary"
                variant="flat"
                prepend-icon="mdi-content-copy"
                @click="copyLink('share')"
              >
                {{ copied === 'share' ? 'Copied' : 'Copy share link' }}
              </v-btn>
            </div>
          </div>
          <div class="garden-link__row garden-link__row--private">
            <p class="garden-link__label">
              <v-icon icon="mdi-key-outline" size="18" aria-hidden="true" />
              Your private edit link · don’t share
            </p>
            <p class="garden-link__hint">
              Use it to keep editing this garden on another device. Anyone with it can change or
              delete your garden.
            </p>
            <div class="garden-link__actions">
              <v-btn
                color="primary"
                variant="outlined"
                prepend-icon="mdi-content-copy"
                @click="copyLink('edit')"
              >
                {{ copied === 'edit' ? 'Copied' : 'Copy private edit link' }}
              </v-btn>
              <span class="garden-link__status" role="status">
                {{ linkStatus === 'saving' ? 'Saving…' : linkStatus === 'saved' ? 'Saved' : '' }}
              </span>
            </div>
          </div>
        </template>

        <p v-if="linkStatus === 'error'" class="garden-link__error" role="alert">
          We couldn’t reach the server just now. Your list is still saved in this browser.
        </p>

        <div v-if="gardenId" class="garden-link__delete">
          <template v-if="!confirmingDelete">
            <button type="button" @click="confirmingDelete = true">Delete saved garden</button>
          </template>
          <template v-else>
            <span>Delete this garden from our server? The link will stop working.</span>
            <v-btn size="small" color="error" variant="flat" @click="deleteSaved">Delete</v-btn>
            <v-btn size="small" variant="text" @click="confirmingDelete = false">Cancel</v-btn>
          </template>
        </div>
      </section>

      <template v-if="listPlants.length">
        <section class="garden-list" aria-label="Plants in your garden">
          <article
            v-for="row in rows"
            :key="row.plantId"
            class="garden-row"
            :class="`garden-row--${toneFor(row.data?.recommendation)}`"
          >
            <div class="garden-row__name">
              <h3>
                <RouterLink
                  :to="{ name: 'plant-assessment', params: { plantId: row.plantId } }"
                  :title="'Open the full plant page'"
                >
                  {{ row.commonName ?? row.data?.common_name ?? row.scientificName }}
                </RouterLink>
              </h3>
              <p>
                <em>{{ row.scientificName }}</em>
              </p>
            </div>
            <div class="garden-row__status">
              <span :class="`garden-chip garden-chip--${toneFor(row.data?.recommendation)}`">
                {{ row.data?.recommendation ?? 'Loading…' }}
              </span>
              <span v-if="row.data?.flowering.label" class="garden-row__meta">
                <v-icon icon="mdi-flower-outline" size="14" aria-hidden="true" />
                Flowers {{ row.data.flowering.label }}
              </span>
            </div>
            <div class="garden-row__actions">
              <v-btn
                v-if="row.data && isRisky(row.data)"
                color="primary"
                variant="flat"
                size="small"
                append-icon="mdi-swap-horizontal"
                @click="findSwap(row.plantId)"
              >
                Find a swap
              </v-btn>
              <v-btn
                v-if="tipsFor(row.data)"
                color="primary"
                variant="outlined"
                size="small"
                :append-icon="
                  openTips.includes(row.plantId) ? 'mdi-chevron-up' : 'mdi-chevron-down'
                "
                :aria-expanded="openTips.includes(row.plantId)"
                :aria-controls="`tips-${row.plantId}`"
                @click="toggleTips(row.plantId)"
              >
                {{ tipsFor(row.data)?.button }}
              </v-btn>
              <v-btn
                v-if="!isViewing"
                variant="text"
                size="small"
                icon="mdi-close"
                :aria-label="`Remove ${row.commonName ?? row.scientificName} from my garden`"
                @click="garden.remove(row.plantId)"
              />
            </div>

            <div
              v-if="tipsFor(row.data)"
              :id="`tips-${row.plantId}`"
              class="garden-tips"
              :class="[
                `garden-tips--${tipsFor(row.data)?.kind}`,
                { 'garden-tips--print-only': !openTips.includes(row.plantId) },
              ]"
            >
              <ul v-if="tipsFor(row.data)?.facts.length">
                <li v-for="fact in tipsFor(row.data)?.facts" :key="fact">{{ fact }}</li>
              </ul>
              <template v-if="tipsFor(row.data)?.general.length">
                <p class="garden-tips__label">{{ tipsFor(row.data)?.generalLabel }}</p>
                <ul>
                  <li v-for="tip in tipsFor(row.data)?.general" :key="tip">{{ tip }}</li>
                </ul>
              </template>
              <p v-if="tipsFor(row.data)?.note" class="garden-tips__label">
                {{ tipsFor(row.data)?.note }}
              </p>
            </div>
            <p v-if="row.data && isRisky(row.data)" class="garden-swap-print">
              <strong>Swap ideas:</strong>
              <template v-if="swapIdeas[row.plantId]?.length">
                {{ swapIdeas[row.plantId]!.join(' · ') }}
              </template>
              <template v-else>
                No close match found. Ask a local indigenous nursery for a native alternative.
              </template>
            </p>
          </article>
        </section>

        <div class="garden-actions">
          <v-btn
            color="primary"
            variant="outlined"
            prepend-icon="mdi-printer-outline"
            @click="printGarden"
          >
            Print or save as PDF
          </v-btn>
          <template v-if="!isViewing">
            <v-btn
              v-if="!confirmingClear"
              variant="text"
              color="error"
              @click="confirmingClear = true"
            >
              Clear my garden
            </v-btn>
            <span v-else class="garden-confirm" role="group" aria-label="Confirm clear">
              <span>Remove all {{ listPlants.length }} plants from your garden?</span>
              <v-btn size="small" color="error" variant="flat" @click="clearGarden">Clear</v-btn>
              <v-btn size="small" variant="text" @click="confirmingClear = false">Cancel</v-btn>
            </span>
          </template>
          <RouterLink :to="{ name: 'plant-catalog' }">Add more plants</RouterLink>
        </div>
      </template>
    </main>

    <AppFooter />
  </div>
</template>

<style scoped>
  .garden-page {
    display: flex;
    min-height: 100vh;
    flex-direction: column;
    background: var(--color-canvas);
  }

  .garden-main {
    flex: 1;
    padding-block: var(--space-xl) var(--space-3xl);
  }

  .garden-eyebrow {
    margin: 0 0 var(--space-xs);
    color: var(--color-accent);
    font-size: 0.75rem;
    font-weight: 800;
    letter-spacing: 0.12em;
  }

  .garden-intro h1 {
    margin: 0;
    font-size: clamp(2rem, 4vw, 2.75rem);
  }

  .garden-privacy {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: var(--space-sm) 0 var(--space-lg);
    color: var(--color-muted);
    font-size: 0.875rem;
  }

  .garden-empty {
    display: grid;
    justify-items: center;
    gap: var(--space-sm);
    padding: var(--space-2xl) var(--space-lg);
    border: 1px dashed var(--color-border-strong);
    border-radius: var(--radius-lg);
    color: var(--color-primary);
    text-align: center;
  }

  .garden-empty h2,
  .garden-empty p {
    margin: 0;
  }

  .garden-empty p {
    color: var(--color-ink-soft);
  }

  .garden-empty__actions,
  .garden-actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--space-sm);
    margin-top: var(--space-sm);
  }

  .garden-alert {
    margin-bottom: var(--space-md);
  }

  .garden-summary {
    padding: var(--space-lg);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    background: var(--color-surface);
  }

  .garden-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: var(--space-md);
    margin-bottom: var(--space-lg);
  }

  .garden-stat strong {
    display: block;
    color: var(--color-primary);
    font-family: var(--font-display);
    font-size: 2.25rem;
    font-weight: 400;
    line-height: 1;
  }

  .garden-stat--concern strong {
    color: var(--color-accent);
  }

  .garden-stat span {
    color: var(--color-ink-soft);
    font-size: 0.875rem;
  }

  .garden-bar {
    display: flex;
    height: 20px;
    overflow: hidden;
    gap: 2px;
    border-radius: var(--radius-pill);
    background: var(--color-surface-muted);
  }

  .garden-bar__part,
  .garden-dot {
    background: var(--color-border-strong);
  }

  .garden-bar__part--concern,
  .garden-dot--concern {
    background: #b5532e;
  }

  .garden-bar__part--caution,
  .garden-dot--caution {
    background: #d9a441;
  }

  .garden-bar__part--lower,
  .garden-dot--lower {
    background: var(--color-primary);
  }

  .garden-legend {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-xs) var(--space-lg);
    margin: var(--space-sm) 0 0;
    padding: 0;
    color: var(--color-ink-soft);
    font-size: 0.875rem;
    list-style: none;
  }

  .garden-legend li {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }

  .garden-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
  }

  .garden-link {
    display: grid;
    gap: var(--space-sm);
    margin-top: var(--space-lg);
    padding: var(--space-lg);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    background: var(--color-success-soft);
  }

  .garden-link h2 {
    display: flex;
    align-items: center;
    gap: var(--space-xs);
    margin: 0;
    font-family: var(--font-body);
    font-size: 1.0625rem;
    font-weight: 700;
  }

  .garden-link__text p {
    margin: 4px 0 0;
    color: var(--color-ink-soft);
    font-size: 0.9375rem;
  }

  .garden-alert__actions {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-xs);
    margin-top: var(--space-sm);
  }

  .garden-link__row {
    display: grid;
    gap: 4px;
    padding-top: var(--space-sm);
    border-top: 1px solid var(--color-border);
  }

  .garden-link__row--private .garden-link__label {
    color: var(--color-accent);
  }

  .garden-link__label {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 0;
    font-weight: 700;
  }

  .garden-link__hint {
    margin: 0 0 var(--space-xs);
    color: var(--color-ink-soft);
    font-size: 0.875rem;
  }

  .garden-link__actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--space-sm);
  }

  .garden-link__url {
    flex: 1 1 320px;
    min-width: 0;
    padding: 10px 12px;
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    color: var(--color-ink);
    font-size: 0.875rem;
  }

  .garden-link__status {
    color: var(--color-muted);
    font-size: 0.875rem;
  }

  .garden-link__error {
    margin: 0;
    color: var(--color-error);
    font-size: 0.875rem;
  }

  .garden-link__delete {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--space-sm);
    font-size: 0.875rem;
  }

  .garden-link__delete button {
    padding: 0;
    border: 0;
    background: none;
    color: var(--color-error);
    font-weight: 700;
    cursor: pointer;
  }

  .garden-list {
    display: grid;
    gap: var(--space-sm);
    margin-block: var(--space-lg);
  }

  .garden-row {
    display: grid;
    grid-template-columns: minmax(0, 2fr) minmax(0, 2fr) auto;
    align-items: center;
    gap: var(--space-md);
    padding: var(--space-md) var(--space-lg);
    border: 1px solid var(--color-border);
    border-left: 4px solid var(--color-border-strong);
    border-radius: 0 var(--radius-md) var(--radius-md) 0;
    background: var(--color-surface);
  }

  .garden-row--concern {
    border-left-color: #b5532e;
  }

  .garden-row--caution {
    border-left-color: #d9a441;
  }

  .garden-row--lower {
    border-left-color: var(--color-primary);
  }

  .garden-row h3 a {
    color: inherit;
    text-decoration: none;
  }

  .garden-row h3 a:hover,
  .garden-row h3 a:focus-visible {
    text-decoration: underline;
    text-underline-offset: 3px;
  }

  .garden-tips {
    grid-column: 1 / -1;
    padding: var(--space-md) var(--space-lg);
    border-radius: var(--radius-md);
    background: var(--color-success-soft);
  }

  .garden-tips--contain {
    background: var(--color-accent-soft);
  }

  .garden-tips ul {
    display: grid;
    gap: 6px;
    margin: 0;
    padding-left: 1.2rem;
    color: var(--color-ink-soft);
    line-height: 1.5;
  }

  .garden-tips__label {
    margin: var(--space-sm) 0 var(--space-xs);
    color: var(--color-muted);
    font-size: 0.8125rem;
    font-weight: 700;
  }

  .garden-row h3 {
    margin: 0;
    font-family: var(--font-body);
    font-size: 1rem;
    font-weight: 700;
  }

  .garden-row__name p {
    margin: 2px 0 0;
    color: var(--color-muted);
    font-size: 0.875rem;
  }

  .garden-row__status {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--space-sm);
  }

  .garden-row__meta {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    color: var(--color-ink-soft);
    font-size: 0.8125rem;
  }

  .garden-chip {
    padding: 2px 10px;
    border-radius: var(--radius-pill);
    background: var(--color-surface-muted);
    font-size: 0.8125rem;
    font-weight: 700;
  }

  .garden-chip--concern,
  .garden-chip--caution {
    background: var(--color-accent-soft);
    color: var(--color-accent);
  }

  .garden-chip--lower {
    background: var(--color-success-soft);
    color: var(--color-primary);
  }

  .garden-row__actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: flex-end;
    gap: var(--space-xs);
  }

  .garden-actions a {
    color: var(--color-primary);
    font-weight: 700;
  }

  @media (max-width: 767px) {
    .garden-row {
      grid-template-columns: 1fr;
    }

    .garden-row__actions {
      justify-content: flex-start;
    }
  }

  .garden-confirm {
    display: inline-flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--space-sm);
    font-size: 0.875rem;
  }

  .garden-tips--print-only,
  .garden-swap-print {
    display: none;
  }

  .garden-swap-print strong {
    margin-right: 0.3em;
  }

  @media print {
    .garden-tips--print-only {
      display: block;
    }

    .garden-swap-print {
      display: block;
      grid-column: 1 / -1;
      margin: 0;
      font-size: 0.875rem;
    }

    .garden-row {
      break-inside: avoid;
    }

    .garden-link,
    .garden-actions,
    .garden-row__actions,
    .garden-privacy {
      display: none;
    }
  }
</style>
