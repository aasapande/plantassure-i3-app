<script setup lang="ts">
  import { RouterLink } from 'vue-router';

  import logoUrl from '@/assets/images/plantassure-logo.png';
  import { useGardenStore } from '@/stores/garden';

  const garden = useGardenStore();

  withDefaults(
    defineProps<{
      actionLabel?: string;
    }>(),
    {
      actionLabel: 'Check a Plant',
    },
  );

  defineEmits<{
    checkPlant: [];
  }>();
</script>

<template>
  <header class="app-header">
    <div class="app-container app-header__inner">
      <RouterLink
        class="app-header__brand"
        :to="{ name: 'home', hash: '#top' }"
        aria-label="PlantAssure home"
      >
        <img :src="logoUrl" alt="PlantAssure" />
      </RouterLink>

      <nav class="app-header__nav" aria-label="Primary navigation">
        <RouterLink class="app-header__link" :to="{ name: 'plant-catalog' }">
          Plant catalogue
        </RouterLink>
        <RouterLink class="app-header__link" :to="{ name: 'data-insights' }">
          Data insights
        </RouterLink>
        <RouterLink class="app-header__link" :to="{ name: 'home', hash: '#why-it-matters' }">
          About the data
        </RouterLink>
        <RouterLink class="app-header__garden" :to="{ name: 'my-garden' }" aria-label="My garden">
          <v-icon icon="mdi-sprout-outline" size="18" aria-hidden="true" />
          <span class="app-header__garden-text">My garden</span>
          <span v-if="garden.count" class="app-header__badge">{{ garden.count }}</span>
        </RouterLink>
        <v-btn
          class="app-header__action"
          color="primary"
          variant="flat"
          append-icon="mdi-arrow-right"
          @click="$emit('checkPlant')"
        >
          {{ actionLabel }}
        </v-btn>
      </nav>
    </div>
  </header>
</template>

<style scoped>
  .app-header {
    position: sticky;
    top: 0;
    z-index: 10;
    min-height: 72px;
    background: var(--color-canvas);
    border-bottom: 1px solid var(--color-border);
  }

  .app-header__inner {
    min-height: 72px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-lg);
  }

  .app-header__brand {
    display: inline-flex;
    align-items: center;
    width: 68px;
    height: 68px;
    flex: 0 0 auto;
    border-radius: var(--radius-sm);
  }

  .app-header__brand img {
    display: block;
    width: 68px;
    height: 68px;
    object-fit: contain;
  }

  .app-header__nav {
    display: flex;
    align-items: center;
    gap: var(--space-lg);
  }

  @media (max-width: 1199px) {
    .app-header__action {
      padding-inline: var(--space-md);
    }
  }

  @media (max-width: 767px) {
    .app-header,
    .app-header__inner {
      min-height: 64px;
    }

    .app-header__brand {
      width: 56px;
      height: 56px;
    }

    .app-header__brand img {
      width: 52px;
      height: 52px;
    }
  }
  .app-header__link {
    color: var(--color-ink);
    font-size: 0.9375rem;
    font-weight: 600;
    text-decoration: none;
    white-space: nowrap;
  }

  .app-header__garden {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: var(--color-primary);
    font-size: 0.9375rem;
    font-weight: 700;
    text-decoration: none;
    white-space: nowrap;
  }

  .app-header__badge {
    display: inline-grid;
    min-width: 20px;
    height: 20px;
    place-items: center;
    padding: 0 6px;
    border-radius: var(--radius-pill);
    background: var(--color-accent);
    color: #fff;
    font-size: 0.75rem;
  }

  .app-header__link:hover {
    color: var(--color-primary);
    text-decoration: underline;
    text-underline-offset: 4px;
  }

  @media (max-width: 899px) {
    .app-header__link {
      display: none;
    }
  }

  @media (max-width: 599px) {
    .app-header__nav {
      gap: var(--space-sm);
    }

    .app-header__garden-text {
      display: none;
    }
  }
</style>
