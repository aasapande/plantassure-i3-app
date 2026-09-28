import { http } from '@/api/http';

import type { InsightsResponse, PassportPlant } from '@/types/passport';

export async function getPassport(plantId: number): Promise<PassportPlant> {
  const { data } = await http.get<PassportPlant>(`/plants/${plantId}/passport`);
  return data;
}

/** Passports for several plants at once, keyed by plant id. */
export async function getPassports(plantIds: number[]): Promise<Record<number, PassportPlant>> {
  if (!plantIds.length) return {};
  const { data } = await http.get<Record<string, PassportPlant>>('/plants/passports', {
    params: { ids: plantIds.join(',') },
  });
  return Object.fromEntries(Object.entries(data).map(([id, plant]) => [Number(id), plant]));
}

export async function getInsights(): Promise<InsightsResponse> {
  const { data } = await http.get<InsightsResponse>('/insights');
  return data;
}
