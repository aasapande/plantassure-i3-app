# PlantAssure — My Garden & Plant Care Guide: Frontend Guide

For: whoever adds Iteration 3 to the team frontend (Vue 3 + Pinia + Vuetify, Iteration 2 code).
Covers: **My Garden** epic (US 1–9) and **Plant Care Guide / Plant Passport** epic.
Backend contract: `MY_GARDEN_API.md` (the backend must have endpoints 1–6 for this to work).

**Source to copy from:** the working reference app
- Repo: https://github.com/aasapande/plantassure-i3-app (folder `frontend/src/`)
- Live: https://plantassure-i3-web.onrender.com (try **My garden** and any plant page)

The reference frontend was built from our Iteration 2 frontend, so it uses the same folders,
`@/` imports, `http` client, design tokens (`--color-*`, `--space-*`, `--radius-*`) and
Vuetify setup. Most files can be copied as they are.

---

## Overview

| Step | What | Time |
|---|---|---|
| 1 | Copy 9 new files | 10 min |
| 2 | Edit 3 existing files (router, header, plant page) | 30 min |
| 3 | Point the frontend at the backend | 2 min |
| 4 | Test against the acceptance criteria | 30 min |

---

## Step 1 — Copy these files (no changes needed)

All paths are under `frontend/src/`.

| File | What it does | Epic |
|---|---|---|
| `types/passport.ts` | Types: `PassportPlant`, `GardenResponse` | Both |
| `api/passport.ts` | `getPassport(id)`, `getPassports(ids)` (also `getInsights`, harmless if unused) | Both |
| `api/gardens.ts` | Create / get / update / delete garden; sends `X-Garden-Edit-Token` | My Garden |
| `stores/garden.ts` | The garden: list in the browser, private link, auto-save, share-link viewing, copy | My Garden |
| `utils/passportPresentation.ts` | Turns passport data into plain-language lines: “What we know”, growing tips, containment steps, risky/safe rules | Both |
| `views/MyGardenView.vue` | The My Garden page and the shared-garden page | My Garden |
| `components/passport/PlantPassport.vue` | The Plant Passport section on plant pages | Care Guide |
| `components/common/InfoTip.vue` | Small ⓘ button with a plain-language explanation | Care Guide |
| `content/glossary.ts` | Text for the ⓘ tips (`PlantPassport` uses `evidenceStrength`) | Care Guide |

> If the team frontend already has `InfoTip.vue` / `glossary.ts` from the Iteration 2
> “info tips” work, keep yours and just make sure `glossary.ts` has an `evidenceStrength` entry:
> ```ts
> evidenceStrength: {
>   title: 'Evidence strength',
>   text: 'How much verified information we have about this plant. It is not a risk score: a plant with limited evidence is not safer or riskier.',
> },
> ```

Everything these files import already exists in the Iteration 2 frontend
(`@/api/http`, `@/api/plants` → `getAlternatives`, `AppHeader.vue`, `AppFooter.vue`, `pinia`,
`axios`, `vue-router`).

**Do not copy** reference-app-only changes that aren't part of these epics (search thumbnails,
Pl@ntNet photo ID, the 70-second timeout in `api/http.ts` — that was only for Render's free
server waking up).

---

## Step 2 — Edit 3 existing files

### 2.1 `router/index.ts` — add two routes

```ts
import MyGardenView from '@/views/MyGardenView.vue';

// inside routes: [...]
{ path: '/garden', name: 'my-garden', component: MyGardenView },
{ path: '/garden/:gardenId', name: 'shared-garden', component: MyGardenView },
```

The route **names** must be exactly `my-garden` and `shared-garden`; the page and store use them.
Both point to the same page: with a `gardenId` it opens a saved/shared garden.

The hosting must send `/garden/...` to `index.html` (single-page app rewrite). Amplify:
**Rewrites and redirects** → `</^[^.]+$|\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|woff2|ttf|map|json|webp)$)([^.]+$)/>` → `/index.html` (200). If other routes like `/plants/...` already work on refresh, this is already set.

### 2.2 `components/layout/AppHeader.vue` — “My garden” link with count (AC 1.1)

In `<script setup>`:

```ts
import { useGardenStore } from '@/stores/garden';

const garden = useGardenStore();
```

In the nav, before the “Check a Plant” button:

```vue
<RouterLink class="app-header__garden" :to="{ name: 'my-garden' }" aria-label="My garden">
  <v-icon icon="mdi-sprout-outline" size="18" aria-hidden="true" />
  <span class="app-header__garden-text">My garden</span>
  <span v-if="garden.count" class="app-header__badge">{{ garden.count }}</span>
</RouterLink>
```

Styles:

```css
.app-header__garden {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--color-primary);
  font-size: 0.9375rem;
  font-weight: 700;
  text-decoration: none;
  white-space: nowrap;
}

.app-header__badge {
  display: inline-grid;
  min-width: 20px;
  height: 20px;
  place-items: center;
  padding: 0 6px;
  border-radius: var(--radius-pill);
  background: var(--color-accent);
  color: #fff;
  font-size: 0.75rem;
}

@media (max-width: 599px) {
  .app-header__garden-text {
    display: none; /* icon + count only on phones */
  }
}
```

### 2.3 `views/PlantAssessmentView.vue` — “Add to my garden” + Plant Passport

**a) Imports** (`<script setup>`):

```ts
import PlantPassport from '@/components/passport/PlantPassport.vue';
import { getPassport } from '@/api/passport';
import type { PassportPlant } from '@/types/passport';
import { useGardenStore } from '@/stores/garden';
```

**b) State and actions** (after `assessmentData` is defined):

```ts
const garden = useGardenStore();
const passport = ref<PassportPlant | null>(null);

const inGarden = computed(() =>
  assessmentData.value ? garden.has(assessmentData.value.plant.plantId) : false,
);

// AC 1.1 / 1.2: add on first click, remove when clicked again ("In my garden")
function toggleGarden() {
  const plant = assessmentData.value?.plant;
  if (!plant) return;
  if (garden.has(plant.plantId)) garden.remove(plant.plantId);
  else
    garden.add({
      plantId: plant.plantId,
      scientificName: plant.scientificName,
      commonName: plant.commonName ?? passport.value?.common_name ?? null,
    });
}

// Care Guide AC 1.3: if the passport can't load, the rest of the page still works
watch(
  () => assessmentData.value?.plant.plantId,
  async (plantId) => {
    passport.value = null;
    if (!plantId) return;
    try {
      passport.value = await getPassport(plantId);
    } catch {
      passport.value = null;
    }
  },
  { immediate: true },
);
```

(`ref`, `computed`, `watch` are already imported from `vue` in this file — add any that aren't.)

**c) Button** — in the plant identity block, under the family line:

```vue
<v-btn
  class="assessment-garden-btn"
  color="primary"
  :variant="inGarden ? 'flat' : 'outlined'"
  :prepend-icon="inGarden ? 'mdi-check' : 'mdi-sprout-outline'"
  @click="toggleGarden"
>
  {{ inGarden ? 'In my garden' : 'Add to my garden' }}
</v-btn>
```

```css
.assessment-garden-btn {
  margin-top: var(--space-md);
}
```

**d) Plant Passport** — at the end of the assessment content (after the evidence sections,
before the page footer):

```vue
<PlantPassport v-if="passport" :plant="passport" />
```

---

## Step 3 — Point at the backend

The frontend already reads `VITE_API_BASE_URL` (default `/api/v1`). Nothing new to set: the
new calls go to the same backend as the existing ones.

The backend must allow `PUT`, `DELETE` and the `X-Garden-Edit-Token` header for the Amplify
address (CORS — listed in `MY_GARDEN_API.md`, “Rules”). If saving fails with a CORS error in the
browser console, that is the cause.

---

## Step 4 — Test against the acceptance criteria

Use a normal window as the **owner** and a **private/incognito window** as **another user**
(the share link only shows the read-only view in a browser that doesn't own the garden).

### My Garden

| Check | Expected | AC |
|---|---|---|
| Plant page → **Add to my garden** | Button → “In my garden” ✓; header badge 1 | 1.1 |
| Reload the plant page | Still “In my garden”; click it → removed, badge −1 | 1.2 |
| **My garden** with plants in 2+ tiers | “Your garden check-up”, 3 stats, coloured bar + legend | 2.1, 2.2 |
| **My garden** with no plants | “Your garden is empty” + Search plants / Browse plant catalogue | 2.3 |
| Risky plant card | Badge, flowering (if known), **Find a swap**, **How to keep it contained** | 3.1 |
| **How to keep it contained** | Opens in place: plant steps + “For any risky plant” list | 3.2 |
| **Find a swap** | Opens Find a Better Plant for that plant | 3.3 |
| Lower Concern / native Not Assessed | **Growing tips** instead; non-native Not Assessed: no buttons | 3.4 |
| **Get a private link** | Share link + private edit link + “Changes save automatically…” | 4.1 |
| Add/remove a plant | Status next to “Copy private edit link” → “Saved” | 4.2 |
| Open edit link in another browser | Same plants, stats, bar; `#edit=…` disappears from the address bar | 5.1, 7.2 |
| Open a deleted garden's link | “This garden link is no longer available” | 5.2 |
| Share link in **incognito** | “A shared garden”, banner, no ×/Clear/Delete/link panel | 6.1, 6.2 |
| **Copy these plants to my garden** (incognito) | Plants copied to that browser's garden, no duplicates; original unchanged | 6.3–6.6 |
| Link panel | Share link and “Your private edit link · don’t share” in separate boxes | 7.1 |
| **Copy private edit link** | Button says “Copied” briefly | 7.2 |
| **Clear my garden** → confirm | List empty, links still shown and still work | 8.1 |
| **Delete saved garden** → confirm | Both links → “no longer available”; list stays in the browser | 8.2 |
| **Print or save as PDF** | All tips (even closed ones) + “Swap ideas:” for risky plants; no buttons/links | 9.1 |

### Plant Care Guide (Plant Passport)

| Check | Expected | AC |
|---|---|---|
| Any plant page | “Plant Passport — Everything we know about this plant” + evidence badge with ⓘ | 1.1, 1.2 |
| Stop the backend passport endpoint / bad id | Rest of the page still shows, no passport | 1.3 |
| Plant with gaps | “What we don’t know yet” card; no rating → “…That doesn’t mean it’s safe.” | 2.2, 2.3 |
| Lower Concern / native Not Assessed | “Growing it” card + “General guidance” + nursery note | 3.1–3.4 |
| Reconsider Planting / Use Caution | “Already have it? Keep it in your garden” + general steps; no “Growing it” | 3.5, 4.1–4.3 |
| Footer | Sources list; “Full description on VicFlora” opens a new tab | 5.1, 5.2 |

---

## How it works (for debugging)

- **Garden list** is saved in the browser under `localStorage` key `plantassure.garden.v2`
  (plants, and once saved: `gardenId`, `editToken`). Clearing site data empties it.
- **No API call** until “Get a private link”. Then every change sends `PUT` about 0.6 s later.
- **Share link** `/garden/{id}` → `GET` only → read-only view.
  **Edit link** `/garden/{id}#edit={key}` → the page stores the key and removes it from the
  address bar.
- If a browser already owns the garden, opening its share link shows the owner view
  (that's why US 6 is tested in incognito).
- The store reacts only to **403** (stops saving, keeps the list) and **404** (“no longer
  available”). Other errors show “We couldn’t reach the server just now”.
- **Plant ids** are whatever our backend returns (`species_data.id`), so nothing changes in
  the frontend for that.
- **Passport JSON is snake_case** (`plant_id`, `flowering.label`) — the types expect that. If the
  passport section is blank but the request succeeds, check the backend's field names.
