import { http } from '@/api/http';

import type { GardenResponse } from '@/types/passport';

// Only plant ids are ever sent. No names or personal details.

export async function createGarden(plantIds: number[]): Promise<GardenResponse> {
  const { data } = await http.post<GardenResponse>('/gardens', { plantIds });
  return data;
}

export async function getGarden(gardenId: string): Promise<GardenResponse> {
  const { data } = await http.get<GardenResponse>(`/gardens/${encodeURIComponent(gardenId)}`);
  return data;
}

export async function updateGarden(gardenId: string, plantIds: number[]): Promise<GardenResponse> {
  const { data } = await http.put<GardenResponse>(`/gardens/${encodeURIComponent(gardenId)}`, {
    plantIds,
  });
  return data;
}

export async function deleteGarden(gardenId: string): Promise<void> {
  await http.delete(`/gardens/${encodeURIComponent(gardenId)}`);
}
