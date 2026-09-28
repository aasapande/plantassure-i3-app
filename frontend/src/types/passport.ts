/** Shape of one plant in the Iteration 3 pipeline output (plants_i3.json). */
export type EvidenceType = 'rating' | 'origin' | 'local_records' | 'traits' | 'flowering' | 'griis';

export interface PassportPlant {
  plant_id: number;
  scientific_name: string;
  common_name: string | null;
  recommendation: 'Reconsider Planting' | 'Use Caution' | 'Lower Concern' | 'Not Assessed';
  origin: string | null;
  establishment: string | null;
  plant_type: string | null;
  traits: {
    growth_form: string | null;
    woodiness: string | null;
    life_history: string | null;
    height_min_m: number | null;
    height_max_m: number | null;
  };
  flowering: {
    months: Array<boolean | null> | null;
    label: string | null;
    sources: number;
    split_pattern: boolean;
  };
  spread: {
    resprouting: string | null;
    vegetative_spread: string | null;
    dispersal: string | null;
    seedbank_longevity: string | null;
  };
  wet_soil_tolerance: string | null;
  local_records: {
    vba100_count: number;
    vba100_latest_year: number | string | null;
    ala_count: number;
    ala_latest_date: string | null;
  };
  griis_listed_introduced: boolean;
  evidence: {
    strength: 'Strong' | 'Moderate' | 'Limited';
    available: EvidenceType[];
    missing: EvidenceType[];
  };
  vicflora_url: string | null;
}

export interface InsightsResponse {
  flowering: { months: string[]; counts: number[]; total: number };
  origin: { introduced: number; native: number; total: number };
  plantTypes: Array<{ type: string; total: number; risky: number; pct: number }>;
  minGroupSize: number;
}

export interface GardenResponse {
  gardenId: string;
  plantIds: number[];
  updatedAt: string;
}
