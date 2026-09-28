import { isAxiosError } from 'axios';
import { defineStore } from 'pinia';
import { computed, ref, watch } from 'vue';

import { createGarden, deleteGarden, getGarden, updateGarden } from '@/api/gardens';
import { getPassports } from '@/api/passport';

// Anonymous garden: plant ids and names in this browser, plus (optionally) a
// saved copy on the server. The server only ever receives plant ids.
//
// Two links per saved garden:
//   share link  /garden/<id>              view only, safe to share
//   edit link   /garden/<id>#edit=<key>   owner only; the key lives after "#",
//                                         which browsers never send to servers
const STORAGE_KEY = 'plantassure.garden.v2';
const SYNC_DELAY_MS = 600;

export interface GardenPlant {
  plantId: number;
  scientificName: string;
  commonName: string | null;
}

export type LinkStatus = 'none' | 'saving' | 'saved' | 'error' | 'expired';
export type OpenResult = 'own' | 'viewing' | 'missing' | 'error';

interface Saved {
  plants: GardenPlant[];
  gardenId: string | null;
  editToken: string | null;
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
    const gardenId = typeof parsed?.gardenId === 'string' ? parsed.gardenId : null;
    const editToken = typeof parsed?.editToken === 'string' ? parsed.editToken : null;
    // A saved garden without its key (made before edit keys existed) can't be
    // changed any more, so this browser simply stops syncing to it.
    return { plants, gardenId: gardenId && editToken ? gardenId : null, editToken };
  } catch {
    return { plants: [], gardenId: null, editToken: null };
  }
}

function status(error: unknown): number | undefined {
  return isAxiosError(error) ? error.response?.status : undefined;
}

async function withNames(plantIds: number[]): Promise<GardenPlant[]> {
  const passports = await getPassports(plantIds);
  return plantIds
    .filter((plantId) => passports[plantId])
    .map((plantId) => ({
      plantId,
      scientificName: passports[plantId]!.scientific_name,
      commonName: passports[plantId]!.common_name,
    }));
}

export const useGardenStore = defineStore('garden', () => {
  const saved = readSaved();
  const plants = ref<GardenPlant[]>(saved.plants);
  const gardenId = ref<string | null>(saved.gardenId);
  const editToken = ref<string | null>(saved.gardenId ? saved.editToken : null);
  const linkStatus = ref<LinkStatus>(saved.gardenId ? 'saved' : 'none');
  /** Someone else's garden opened from a share link. Never saved or synced. */
  const viewing = ref<{ gardenId: string; plants: GardenPlant[] } | null>(null);
  let syncTimer: ReturnType<typeof setTimeout> | undefined;

  const count = computed(() => plants.value.length);
  const shareUrl = computed(() =>
    gardenId.value ? `${window.location.origin}/garden/${gardenId.value}` : null,
  );
  const editUrl = computed(() =>
    gardenId.value && editToken.value
      ? `${window.location.origin}/garden/${gardenId.value}#edit=${editToken.value}`
      : null,
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

  function forgetLink(next: LinkStatus) {
    gardenId.value = null;
    editToken.value = null;
    linkStatus.value = next;
  }

  async function syncNow() {
    if (!gardenId.value || !editToken.value) return;
    linkStatus.value = 'saving';
    try {
      await updateGarden(
        gardenId.value,
        plants.value.map((plant) => plant.plantId),
        editToken.value,
      );
      linkStatus.value = 'saved';
    } catch (error) {
      const code = status(error);
      if (code === 404) forgetLink('expired');
      else if (code === 403) forgetLink('error');
      else linkStatus.value = 'error';
    }
  }

  /** Saves the current list on the server and returns the share link. */
  async function createLink(): Promise<string | null> {
    linkStatus.value = 'saving';
    try {
      const garden = await createGarden(plants.value.map((plant) => plant.plantId));
      gardenId.value = garden.gardenId;
      editToken.value = garden.editToken;
      linkStatus.value = 'saved';
      return shareUrl.value;
    } catch {
      linkStatus.value = 'error';
      return null;
    }
  }

  /**
   * Opens /garden/<id>. With the edit key it becomes this browser's own
   * garden; without it, it's shown read-only and nothing is replaced.
   */
  async function open(id: string, key: string | null): Promise<OpenResult> {
    if (!key && id === gardenId.value && editToken.value) {
      viewing.value = null;
      return 'own';
    }
    try {
      const garden = await getGarden(id);
      const named = await withNames(garden.plantIds);
      if (key) {
        plants.value = named;
        gardenId.value = garden.gardenId;
        editToken.value = key;
        linkStatus.value = 'saved';
        viewing.value = null;
        return 'own';
      }
      viewing.value = { gardenId: garden.gardenId, plants: named };
      return 'viewing';
    } catch (error) {
      viewing.value = null;
      if (status(error) === 404) {
        if (id === gardenId.value) forgetLink('expired');
        return 'missing';
      }
      return 'error';
    }
  }

  function stopViewing() {
    viewing.value = null;
  }

  /** Adds the plants from a shared garden to this browser's own garden. */
  function copyViewingToMine() {
    for (const plant of viewing.value?.plants ?? []) add(plant);
    viewing.value = null;
  }

  /** Deletes the saved copy from the server; the list stays in this browser. */
  async function deleteLink(): Promise<boolean> {
    if (!gardenId.value || !editToken.value) return true;
    try {
      await deleteGarden(gardenId.value, editToken.value);
      forgetLink('none');
      return true;
    } catch (error) {
      if (status(error) === 404) {
        forgetLink('none');
        return true;
      }
      linkStatus.value = 'error';
      return false;
    }
  }

  watch(
    [plants, gardenId, editToken],
    ([value, id, key]) => {
      try {
        localStorage.setItem(
          STORAGE_KEY,
          JSON.stringify({ plants: value, gardenId: id, editToken: key }),
        );
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
    viewing,
    count,
    shareUrl,
    editUrl,
    has,
    add,
    remove,
    clear,
    createLink,
    open,
    stopViewing,
    copyViewingToMine,
    deleteLink,
  };
});
