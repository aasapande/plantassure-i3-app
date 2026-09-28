import { isAxiosError } from 'axios';
import { defineStore } from 'pinia';
import { computed, ref, watch } from 'vue';

import { createGarden, deleteGarden, getGarden, updateGarden } from '@/api/gardens';
import { getPassports } from '@/api/passport';

// Anonymous garden: plant ids and names in this browser, plus (optionally) a
// random garden id for the private link. The server only ever receives plant
// ids. No personal information is collected or stored.
const STORAGE_KEY = 'plantassure.garden.v2';
const SYNC_DELAY_MS = 600;

export interface GardenPlant {
  plantId: number;
  scientificName: string;
  commonName: string | null;
}

export type LinkStatus = 'none' | 'saving' | 'saved' | 'error' | 'expired';

interface Saved {
  plants: GardenPlant[];
  gardenId: string | null;
}

function readSaved(): Saved {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null') as Partial<Saved> | null;
    const plants = Array.isArray(parsed?.plants)
      ? parsed.plants.filter(
          (item): item is GardenPlant =>
            typeof item?.plantId === 'number' && typeof item?.scientificName === 'string',
        )
      : [];
    return { plants, gardenId: typeof parsed?.gardenId === 'string' ? parsed.gardenId : null };
  } catch {
    return { plants: [], gardenId: null };
  }
}

function isNotFound(error: unknown): boolean {
  return isAxiosError(error) && error.response?.status === 404;
}

export const useGardenStore = defineStore('garden', () => {
  const saved = readSaved();
  const plants = ref<GardenPlant[]>(saved.plants);
  const gardenId = ref<string | null>(saved.gardenId);
  const linkStatus = ref<LinkStatus>(saved.gardenId ? 'saved' : 'none');
  let syncTimer: ReturnType<typeof setTimeout> | undefined;

  const count = computed(() => plants.value.length);
  const shareUrl = computed(() =>
    gardenId.value ? `${window.location.origin}/garden/${gardenId.value}` : null,
  );

  function has(plantId: number): boolean {
    return plants.value.some((plant) => plant.plantId === plantId);
  }

  function add(plant: GardenPlant) {
    if (!has(plant.plantId)) plants.value.push(plant);
  }

  function remove(plantId: number) {
    plants.value = plants.value.filter((plant) => plant.plantId !== plantId);
  }

  function clear() {
    plants.value = [];
  }

  function forgetLink(status: LinkStatus) {
    gardenId.value = null;
    linkStatus.value = status;
  }

  async function syncNow() {
    if (!gardenId.value) return;
    linkStatus.value = 'saving';
    try {
      await updateGarden(
        gardenId.value,
        plants.value.map((plant) => plant.plantId),
      );
      linkStatus.value = 'saved';
    } catch (error) {
      if (isNotFound(error)) forgetLink('expired');
      else linkStatus.value = 'error';
    }
  }

  /** Saves the current list on the server and returns the private link. */
  async function createLink(): Promise<string | null> {
    linkStatus.value = 'saving';
    try {
      const garden = await createGarden(plants.value.map((plant) => plant.plantId));
      gardenId.value = garden.gardenId;
      linkStatus.value = 'saved';
      return shareUrl.value;
    } catch {
      linkStatus.value = 'error';
      return null;
    }
  }

  /** Opens a garden from a private link. Returns false if it doesn't exist. */
  async function openShared(id: string): Promise<boolean> {
    try {
      const garden = await getGarden(id);
      const passports = await getPassports(garden.plantIds);
      plants.value = garden.plantIds
        .filter((plantId) => passports[plantId])
        .map((plantId) => ({
          plantId,
          scientificName: passports[plantId]!.scientific_name,
          commonName: passports[plantId]!.common_name,
        }));
      gardenId.value = garden.gardenId;
      linkStatus.value = 'saved';
      return true;
    } catch (error) {
      if (isNotFound(error)) linkStatus.value = 'expired';
      else linkStatus.value = 'error';
      return false;
    }
  }

  /** Deletes the garden from the server; the list stays in this browser. */
  async function deleteLink(): Promise<boolean> {
    if (!gardenId.value) return true;
    try {
      await deleteGarden(gardenId.value);
      forgetLink('none');
      return true;
    } catch (error) {
      if (isNotFound(error)) {
        forgetLink('none');
        return true;
      }
      linkStatus.value = 'error';
      return false;
    }
  }

  watch(
    [plants, gardenId],
    ([value, id]) => {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ plants: value, gardenId: id }));
      } catch {
        // Storage unavailable (e.g. private mode): the list still works for this visit.
      }
    },
    { deep: true },
  );

  // Keep the saved garden up to date when the list changes.
  watch(
    () => plants.value.map((plant) => plant.plantId).join(','),
    () => {
      if (!gardenId.value) return;
      clearTimeout(syncTimer);
      syncTimer = setTimeout(() => void syncNow(), SYNC_DELAY_MS);
    },
  );

  return {
    plants,
    gardenId,
    linkStatus,
    count,
    shareUrl,
    has,
    add,
    remove,
    clear,
    createLink,
    openShared,
    deleteLink,
  };
});
