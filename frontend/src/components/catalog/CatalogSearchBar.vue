<script setup lang="ts">
  import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
  import { useRouter } from 'vue-router';

  import { getPlants } from '@/api/plants';
  import AutocompleteDropdown from '@/components/search/AutocompleteDropdown.vue';
  import type { PlantSearchResult } from '@/types/plant';

  // Suggestions come from the catalogue itself (rated plants only), so they
  // always match what the catalogue can show.
  const AUTOCOMPLETE_DELAY = 275;
  const MIN_CHARS = 2;
  const MAX_SUGGESTIONS = 6;
  const LISTBOX_ID = 'catalog-search-suggestions';

  const query = defineModel<string>({ default: '' });

  const emit = defineEmits<{
    search: [query: string];
  }>();

  const router = useRouter();
  const root = ref<HTMLFormElement | null>(null);
  const suggestions = ref<PlantSearchResult[]>([]);
  const isLoading = ref(false);
  const error = ref<string | null>(null);
  const isOpen = ref(false);
  const activeIndex = ref(-1);
  let debounceTimer: ReturnType<typeof setTimeout> | null = null;
  let requestId = 0;

  const activeDescendant = computed(() =>
    isOpen.value && activeIndex.value >= 0
      ? `${LISTBOX_ID}-option-${activeIndex.value}`
      : undefined,
  );

  function closeDropdown() {
    isOpen.value = false;
    activeIndex.value = -1;
  }

  /** Cancels a pending or in-flight lookup so it can't reopen the dropdown. */
  function cancelSuggestions() {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = null;
    requestId += 1;
    isLoading.value = false;
    closeDropdown();
  }

  async function loadSuggestions(term: string) {
    const id = ++requestId;
    isLoading.value = true;
    error.value = null;
    isOpen.value = true;
    try {
      const response = await getPlants({ q: term, size: MAX_SUGGESTIONS, page: 0 });
      if (id !== requestId) return;
      suggestions.value = response.items.map((item) => ({
        plantId: item.plantId,
        scientificName: item.scientificName,
        commonName: item.commonName,
        family: null,
        imageUrl: item.imageUrl,
        imageCredit: item.imageCredit ?? null,
      }));
    } catch {
      if (id !== requestId) return;
      suggestions.value = [];
      error.value = 'We couldn’t load suggestions. Please try again.';
    } finally {
      if (id === requestId) isLoading.value = false;
    }
  }

  function handleInput(value: string) {
    query.value = value;
    activeIndex.value = -1;
    if (debounceTimer) clearTimeout(debounceTimer);
    const term = value.trim();
    if (term.length < MIN_CHARS) {
      requestId += 1;
      suggestions.value = [];
      closeDropdown();
      return;
    }
    debounceTimer = setTimeout(() => void loadSuggestions(term), AUTOCOMPLETE_DELAY);
  }

  function moveActive(direction: 1 | -1) {
    if (!isOpen.value || suggestions.value.length === 0) return;
    const count = suggestions.value.length;
    activeIndex.value =
      activeIndex.value === -1
        ? direction === 1
          ? 0
          : count - 1
        : (activeIndex.value + direction + count) % count;
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      moveActive(1);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      moveActive(-1);
    } else if (event.key === 'Enter' && isOpen.value && activeIndex.value >= 0) {
      event.preventDefault();
      const choice = suggestions.value[activeIndex.value];
      if (choice) selectSuggestion(choice);
    } else if (event.key === 'Escape') {
      event.preventDefault();
      cancelSuggestions();
    }
  }

  function selectSuggestion(suggestion: PlantSearchResult) {
    cancelSuggestions();
    void router.push({ name: 'plant-assessment', params: { plantId: suggestion.plantId } });
  }

  function submitSearch() {
    cancelSuggestions();
    emit('search', query.value.trim());
  }

  function handleDocumentPointerDown(event: PointerEvent) {
    if (root.value?.contains(event.target as Node)) return;
    closeDropdown();
  }

  onMounted(() => document.addEventListener('pointerdown', handleDocumentPointerDown));
  onBeforeUnmount(() => {
    if (debounceTimer) clearTimeout(debounceTimer);
    requestId += 1;
    document.removeEventListener('pointerdown', handleDocumentPointerDown);
  });
</script>

<template>
  <form ref="root" class="catalog-search-bar" role="search" @submit.prevent="submitSearch">
    <div class="catalog-search-bar__field">
      <v-text-field
        :model-value="query"
        class="catalog-search-bar__input"
        variant="outlined"
        color="primary"
        density="comfortable"
        hide-details
        autocomplete="off"
        placeholder="Search the catalogue by common or scientific name"
        aria-label="Search the catalogue by common or scientific name"
        role="combobox"
        aria-autocomplete="list"
        :aria-expanded="isOpen"
        :aria-controls="LISTBOX_ID"
        :aria-activedescendant="activeDescendant"
        @update:model-value="handleInput"
        @keydown="handleKeydown"
      />
      <AutocompleteDropdown
        v-if="isOpen"
        :id="LISTBOX_ID"
        :suggestions="suggestions"
        :is-loading="isLoading"
        :error="error"
        :active-index="activeIndex"
        @activate="activeIndex = $event"
        @select="selectSuggestion"
        @retry="loadSuggestions(query.trim())"
      />
    </div>
    <v-btn
      class="catalog-search-bar__submit"
      type="submit"
      color="primary"
      variant="flat"
      height="52"
    >
      Search
    </v-btn>
  </form>
</template>

<style scoped>
  .catalog-search-bar {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: start;
    gap: var(--space-sm);
    width: 100%;
  }

  .catalog-search-bar__field {
    position: relative;
    min-width: 0;
  }

  .catalog-search-bar__submit {
    min-width: 84px;
  }

  @media (max-width: 479px) {
    .catalog-search-bar {
      grid-template-columns: 1fr;
    }

    .catalog-search-bar__submit {
      width: 100%;
    }
  }
</style>
