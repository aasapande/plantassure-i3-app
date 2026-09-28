/**
 * Plain-language explanations for terms shown in the app.
 * Keep each entry short: one or two sentences a first-time gardener can follow.
 */
export interface GlossaryEntry {
  title: string;
  text: string;
  icon?: string;
}

export const glossary = {
  // Where the plant comes from
  origin: {
    title: 'Origin',
    text: 'Whether the plant is native to Victoria or was brought here from somewhere else.',
  },
  native: {
    title: 'Native',
    icon: 'mdi-leaf',
    text: 'Grew naturally in Victoria before European settlement. Usually suits local wildlife and conditions.',
  },
  introduced: {
    title: 'Introduced',
    icon: 'mdi-earth',
    text: 'Brought to Victoria from another place, on purpose or by accident. Some introduced plants become weeds.',
  },
  uncertain: {
    title: 'Uncertain origin',
    text: 'Experts are not sure whether this plant is native to Victoria or was brought in.',
  },

  // How settled the plant is in the wild
  victorianStatus: {
    title: 'Status in Victoria',
    text: 'How well the plant has settled into Victoria’s wild areas, according to VicFlora.',
  },
  naturalised: {
    title: 'Naturalised',
    icon: 'mdi-sprout-outline',
    text: 'An introduced plant that now grows and spreads in the wild on its own, without help from people.',
  },
  adventive: {
    title: 'Adventive',
    text: 'An introduced plant found in the wild a few times, but not yet spreading on its own.',
  },

  // Risk
  environmentalConcern: {
    title: 'Environmental concern',
    icon: 'mdi-alert-circle-outline',
    text: 'How likely the plant is to escape gardens and harm local bushland. Ratings come from Victoria’s official weed list.',
  },
  concernLevels: {
    title: 'What the ratings mean',
    text: 'Very High and High: likely to spread and cause harm. Moderately High and Medium: can spread in some conditions. Lower: little evidence of harm.',
  },
  notAssessed: {
    title: 'Not Assessed',
    text: 'This plant is not on Victoria’s weed list, so it has no rating. That does not prove it is safe.',
  },
  plantingGuidance: {
    title: 'Planting guidance',
    text: 'Our advice, based on the plant’s environmental concern rating. Reconsider Planting = Very High or High. Use Caution = Moderately High or Medium. Lower Concern = Lower.',
  },
  legalStatus: {
    title: 'Legal status',
    text: 'Whether Victorian law restricts growing or selling this plant. This is separate from environmental concern.',
  },
  legalUnavailable: {
    title: 'Legal status unavailable',
    text: 'We don’t have verified legal information for this plant yet. Check with Agriculture Victoria or your local council.',
  },

  // Local sightings
  seenLocally: {
    title: 'Seen locally',
    text: 'How many times this plant has been officially recorded in the City of Monash. It shows where the plant grows, not how risky it is.',
  },

  // Plant features
  growthForm: {
    title: 'Growth form',
    text: 'The plant’s general shape, such as herb, grass, shrub, tree, climber or fern.',
  },
  lifeHistory: {
    title: 'Life history',
    text: 'How long the plant lives. Annual: about one year. Biennial: two years. Perennial: many years.',
  },
  woodiness: {
    title: 'Woodiness',
    text: 'Woody plants have hard stems, like shrubs and trees. Herbaceous plants have soft, green stems.',
  },
  height: {
    title: 'Height',
    text: 'The usual height range of a fully grown plant, in metres.',
  },
  family: {
    title: 'Plant family',
    text: 'A group of related plants with shared features. For example, wattles and peas are both in the Fabaceae family.',
  },
  evidenceStrength: {
    title: 'Evidence strength',
    text: 'How much verified information we have about this plant. It is not a risk score: a plant with limited evidence is not safer or riskier.',
  },
  whyItMatches: {
    title: 'Why it matches',
    text: 'These plants share your plant’s shape, woodiness, lifespan and height. None is rated as a weed risk: some are rated Lower on Victoria’s weed list, others have no rating yet.',
  },

  // Data sources
  vicflora: {
    title: 'VicFlora',
    text: 'The Royal Botanic Gardens Victoria’s online guide to the plants of Victoria.',
  },
  vba: {
    title: 'Victorian Biodiversity Atlas (VBA)',
    text: 'The Victorian Government’s database of plant and animal sightings, recorded by ecologists and trained volunteers.',
  },
  advisoryList: {
    title: 'Advisory List (2022)',
    text: 'Victoria’s official list of environmental weeds, published by the state government. Each listed plant has a risk rating.',
  },
  austraits: {
    title: 'AusTraits',
    text: 'A national scientific database of Australian plant traits, such as size, lifespan, flowering time and how seeds spread.',
  },
  ala: {
    title: 'Atlas of Living Australia (ALA)',
    text: 'Australia’s national collection of plant and animal records, from museums, researchers and the public.',
  },
  griis: {
    title: 'GRIIS Australia',
    text: 'The Global Register of Introduced and Invasive Species: a list of plants introduced to Australia.',
  },
  inaturalist: {
    title: 'iNaturalist',
    text: 'A worldwide nature-sharing site. We only use photos that their owners have shared under open licences, and credit each one.',
  },
} satisfies Record<string, GlossaryEntry>;

export type GlossaryKey = keyof typeof glossary;

/** Maps a VicFlora establishment value (e.g. "naturalised") to its glossary entry, if any. */
export function establishmentGlossaryKey(status: string | null | undefined): GlossaryKey | null {
  switch (status?.toLowerCase()) {
    case 'native':
      return 'native';
    case 'naturalised':
      return 'naturalised';
    case 'adventive':
      return 'adventive';
    default:
      return null;
  }
}

export function originGlossaryKey(status: string | null | undefined): GlossaryKey | null {
  switch (status) {
    case 'NATIVE':
      return 'native';
    case 'INTRODUCED':
      return 'introduced';
    case 'UNCERTAIN':
      return 'uncertain';
    default:
      return null;
  }
}
