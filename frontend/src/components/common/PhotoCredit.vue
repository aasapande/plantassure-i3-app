<script setup lang="ts">
  // Photographer credit required by the photo's Creative Commons licence.
  defineProps<{
    credit: string;
    pageUrl?: string | null;
  }>();
</script>

<template>
  <p class="photo-credit">
    <a v-if="pageUrl" :href="pageUrl" target="_blank" rel="noopener">{{ credit }}</a>
    <template v-else>{{ credit }}</template>
  </p>
</template>

<style scoped>
  .photo-credit {
    margin: 4px 0 0;
    overflow: hidden;
    color: var(--color-muted);
    font-size: 0.6875rem;
    line-height: 1.4;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .photo-credit a {
    color: inherit;
    text-decoration: none;
  }

  .photo-credit a:hover {
    text-decoration: underline;
  }
</style>
