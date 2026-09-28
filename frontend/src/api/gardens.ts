import { http } from '@/api/http';

import type { GardenResponse } from '@/types/passport';

// Only plant ids are ever sent. No names or personal details.
// Changing or deleting a garden needs its private edit key; viewing doesn't.

const EDIT_HEADER = 'X-Garden-Edit-Token';

export interface CreatedGarden extends GardenResponse {
  editToken: string;
}

export async function createGarden(plantIds: number[]): Promise<CreatedGarden> {
  const { data } = await http.post<CreatedGarden>('/gardens', { plantIds });
  return data;
}

export async function getGarden(gardenId: string): Promise<GardenResponse> {
  const { data } = await http.get<GardenResponse>(`/gardens/${encodeURIComponent(gardenId)}`);
  return data;
}

export async function updateGarden(
  gardenId: string,
  plantIds: number[],
  editToken: string,
): Promise<GardenResponse> {
  const { data } = await http.put<GardenResponse>(
    `/gardens/${encodeURIComponent(gardenId)}`,
    { plantIds },
    { headers: { [EDIT_HEADER]: editToken } },
  );
  return data;
}

export async function deleteGarden(gardenId: string, editToken: string): Promise<void> {
  await http.delete(`/gardens/${encodeURIComponent(gardenId)}`, {
    headers: { [EDIT_HEADER]: editToken },
  });
}
