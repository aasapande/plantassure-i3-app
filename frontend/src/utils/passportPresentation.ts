import type { EvidenceType, PassportPlant } from '@/types/passport';

/**
 * Turns Iteration 3 pipeline values into short plain-language lines.
 * Every data line comes from a real value; a missing value produces no line.
 * General guidance is labelled separately in the UI.
 */

const RISKY = new Set(['Reconsider Planting', 'Use Caution']);

export function isRisky(plant: PassportPlant): boolean {
  return RISKY.has(plant.recommendation);
}

/** Planting tips are only shown for plants we would want people to plant. */
export function showsGrowingGuide(plant: PassportPlant): boolean {
  return (
    plant.recommendation === 'Lower Concern' ||
    (plant.recommendation === 'Not Assessed' && plant.origin === 'native')
  );
}

export function formatHeight(plant: PassportPlant): string | null {
  const { height_min_m: min, height_max_m: max } = plant.traits;
  if (max === null) return null;
  const fmt = (value: number) =>
    value < 1 ? value.toFixed(1) : String(Math.round(value * 10) / 10);
  return min === null || min === max ? `up to ${fmt(max)} m` : `${fmt(min)}–${fmt(max)} m`;
}

function lifespan(lifeHistory: string | null): string | null {
  if (!lifeHistory) return null;
  const parts = lifeHistory.split(' ');
  if (parts.length === 1 && parts[0] === 'perennial') return 'lives for many years';
  if (parts.length === 1 && parts[0] === 'annual') return 'lasts about a year';
  if (parts.length === 1 && parts[0] === 'biennial') return 'lives about two years';
  if (parts.includes('perennial') || parts.includes('short_lived_perennial')) {
    return 'can live one year or several';
  }
  return null;
}

function latestLocalYear(plant: PassportPlant): number | null {
  const years: number[] = [];
  const vbaYear = Number(plant.local_records.vba100_latest_year);
  if (Number.isFinite(vbaYear)) years.push(vbaYear);
  const alaYear = Number(String(plant.local_records.ala_latest_date ?? '').slice(0, 4));
  if (Number.isFinite(alaYear) && alaYear > 1800) years.push(alaYear);
  return years.length ? Math.max(...years) : null;
}

export function localRecordCount(plant: PassportPlant): number {
  return plant.local_records.vba100_count + plant.local_records.ala_count;
}

function capitalise(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export function whatWeKnow(plant: PassportPlant): string[] {
  const lines: string[] = [];
  const available = new Set(plant.evidence.available);

  if (available.has('origin')) {
    const settled = plant.establishment === 'naturalised' ? ', and now spreads in the wild' : '';
    lines.push(
      plant.origin === 'native'
        ? 'Native to Victoria'
        : plant.origin === 'introduced'
          ? `Introduced to Victoria${settled}`
          : 'Origin in Victoria is uncertain',
    );
  }
  if (available.has('rating')) {
    lines.push(`Rated “${plant.recommendation}” using Victoria’s official weed list`);
  }
  if (available.has('local_records')) {
    const year = latestLocalYear(plant);
    const count = localRecordCount(plant);
    lines.push(
      `Officially recorded ${count} ${count === 1 ? 'time' : 'times'} in Monash${year ? ` (latest ${year})` : ''}`,
    );
  }
  if (available.has('traits') && plant.plant_type) {
    const height = formatHeight(plant);
    const life = lifespan(plant.traits.life_history);
    lines.push(
      [capitalise(plant.plant_type.toLowerCase()), height, life].filter(Boolean).join(', '),
    );
  }
  if (available.has('flowering') && plant.flowering.label) {
    lines.push(`Flowers ${plant.flowering.label}`);
  }
  if (available.has('griis')) {
    lines.push('Listed on Australia’s national register of introduced plants');
  }
  return lines;
}

const MISSING_LINES: Record<Exclude<EvidenceType, 'griis'>, string> = {
  rating: 'No official weed rating yet. That doesn’t mean it’s safe.',
  origin: 'Whether it is native or introduced',
  local_records: 'No official records in Monash yet',
  traits: 'Its size and growth form',
  flowering: 'When it flowers',
};

export function whatWeDontKnow(plant: PassportPlant): string[] {
  return plant.evidence.missing
    .filter((type): type is Exclude<EvidenceType, 'griis'> => type !== 'griis')
    .map((type) => MISSING_LINES[type]);
}

/** Facts for "Growing it", derived by simple rules from real values. */
export function growingFacts(plant: PassportPlant): string[] {
  const lines: string[] = [];
  const max = plant.traits.height_max_m;
  if (max !== null) {
    if (max < 0.5) lines.push('Low-growing: suits garden edges and pots');
    else if (max < 2) lines.push('Suits the front or middle of a garden bed');
    else if (max < 5) lines.push('Suits the back of a bed or as a screen');
    else lines.push('Grows into a tree: allow plenty of room from buildings and pipes');
  }
  const life = lifespan(plant.traits.life_history);
  if (life) lines.push(capitalise(life));
  if (plant.flowering.label) lines.push(`Flowers ${plant.flowering.label}`);
  if (plant.wet_soil_tolerance) lines.push(plant.wet_soil_tolerance);
  return lines;
}

// Draft general guidance per plant type. Must be reviewed by the team
// before release; always shown with a "General guidance" label.
const GENERAL_GUIDANCE: Record<string, string> = {
  Tree: 'Plant in autumn or winter. Water deeply once a week through its first summer. Keep mulch a hand-width away from the trunk.',
  Shrub:
    'Plant in autumn. Water in well, then weekly through the first summer. Mulch around the plant, not against the stem.',
  Grass:
    'Plant in autumn or spring. Water regularly until it is established, then only in long dry spells.',
  Herb: 'Plant in autumn or spring. Keep the soil lightly moist until it is established.',
  Climber: 'Give it something to climb. Plant in autumn and water weekly through the first summer.',
  Fern: 'Plant in a shady, sheltered spot and keep the soil moist.',
};

export function generalGuidance(plant: PassportPlant): string | null {
  return plant.plant_type ? (GENERAL_GUIDANCE[plant.plant_type] ?? null) : null;
}

/** Facts for "Keeping it in your garden" (risky plants), from real values only. */
export function containmentFacts(plant: PassportPlant): string[] {
  const lines: string[] = [];
  if (plant.flowering.label) {
    lines.push(`Flowers ${plant.flowering.label}: remove flowers before they set seed`);
  }
  if (plant.spread.resprouting === 'resprouts') {
    lines.push('Can regrow after being cut back: remove the roots, not just the top');
  } else if (plant.spread.resprouting === 'partial_resprouting') {
    lines.push('May regrow from the base after cutting');
  }
  if (plant.spread.vegetative_spread === 'vegetative') {
    lines.push('Spreads by runners or roots: grow it in a pot or behind a root barrier');
  }
  if (plant.spread.dispersal) {
    const eaten = plant.spread.dispersal.includes('eating the fruit');
    lines.push(
      `Seeds are spread by ${plant.spread.dispersal}${eaten ? ': pick fruit before it ripens' : ''}`,
    );
  }
  if (plant.spread.seedbank_longevity?.includes('persistent')) {
    lines.push('Seeds can survive in soil for years: keep checking for seedlings');
  }
  return lines;
}

export const GENERAL_CONTAINMENT_STEPS = [
  'Bag seed heads and put them in the rubbish bin, not green waste',
  'Never dump clippings near bushland, parks or creeks',
  'Check nearby for seedlings and pull them out early',
];
