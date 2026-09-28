<script setup lang="ts">
  // Photographer credit required by the photo's Creative Commons licence.
  defineProps<{
    credit: string;
    pageUrl?: string | null;
    /** Sits on the bottom edge of the photo instead of below it. */
    overlay?: boolean;
  }>();
</script>

<template>
  <p class="photo-credit" :class="{ 'photo-credit--overlay': overlay }">
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

  .photo-credit--overlay {
    position: absolute;
    right: 0;
    bottom: 0;
    left: 0;
    z-index: 1;
    margin: 0;
    padding: 3px 8px;
    background: rgb(0 0 0 / 45%);
    color: #fff;
    font-size: 0.625rem;
  }

  .photo-credit a {
    color: inherit;
    text-decoration: none;
  }

  .photo-credit a:hover {
    text-decoration: underline;
  }
</style>
