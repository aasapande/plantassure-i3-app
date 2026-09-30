# My Garden — Spring Boot implementation guide

For: the PlantAssure backend (`com.plantky`, Spring Boot 3.3, Java 17, MyBatis-Plus, MySQL).
Goal: add the My Garden epic (US 1–9) to the team backend so it behaves exactly like the working
reference app.

**Files in this folder**

| File | What it is |
|---|---|
| `MY_GARDEN_SPRING_BOOT_GUIDE.md` | This guide: what to build and how, with code that follows our Iteration 1–2 patterns |
| `my-garden-openapi.yaml` | The API contract. Import into Apifox or Swagger Editor to see and try every endpoint |
| `species_passport_i3.sql` | Ready-to-run SQL that adds the Iteration 3 plant data (flowering, spread, care, evidence) for all 880 plants, matched to our `species_data` ids |

**The reference app (already built and working)**

- Website: https://plantassure-i3-web.onrender.com (go to **My garden**)
- API + interactive docs: https://plantassure-i3-api.onrender.com/docs
  (first load can take ~60 s while the free server wakes up)
- Source: `plantassure-i3-app/backend/main.py` (garden and passport endpoints),
  `frontend/src/stores/garden.ts`, `frontend/src/api/gardens.ts`,
  `frontend/src/views/MyGardenView.vue`, `frontend/src/utils/passportPresentation.ts`

The reference backend is Python/FastAPI. This guide is the same design written for our Spring
Boot codebase. **The URLs, request bodies, response bodies and status codes are the same**, so
the reference Vue garden page can be reused without changes.

---

## 1. What's new vs. Iteration 2

| Area | Change |
|---|---|
| Database | 2 new tables (`garden`, `garden_plant`) + 1 new data table (`species_passport`). `species_data` is not changed. |
| Endpoints | 4 garden endpoints + 2 passport endpoints (below). Existing endpoints are not changed. |
| `ErrorCode` | 3 new values |
| `WebMvcConfig` | CORS must also allow `PUT` and `DELETE` |
| Scheduling | One hourly job deletes gardens unused for 90 days |

### Endpoints

| Method | Path | Epic | Edit key? |
|---|---|---|---|
| `POST` | `/api/v1/gardens` | AC 4.1 “Get a private link” | No |
| `GET` | `/api/v1/gardens/{gardenId}` | US 5, US 6 (both links) | No |
| `PUT` | `/api/v1/gardens/{gardenId}` | AC 4.2 auto-save, AC 8.1 Clear | **Yes** |
| `DELETE` | `/api/v1/gardens/{gardenId}` | AC 8.2 Delete | **Yes** |
| `GET` | `/api/v1/plants/passports?ids=3,7,120` | US 2, US 3, US 9 (cards, check-up, tips) | No |
| `GET` | `/api/v1/plants/{plantId}/passport` | Same data, one plant | No |

Swap ideas (AC 3.3, AC 9.1) use our **existing** `GET /api/v1/plants/{plantId}/alternatives`.
Nothing new is needed there.

The edit key goes in the header `X-Garden-Edit-Token`. Full request/response examples are in
`my-garden-openapi.yaml`.

### Only differences from the reference app

1. **Plant ids** are our `species_data.id`. They are not the same numbers as the reference app
   (e.g. id 46 is *Agapanthus* there but *Allittia cardiocarpa* here). The SQL file matches
   plants by `scientific_name`, so it works with our ids.
2. **Errors** use our existing `ErrorResponse` `{ code, message, path }` instead of FastAPI's
   `{ detail }`. An invalid plant list returns **400** (our convention) instead of 422.
   The frontend only looks at the status codes 403 and 404, so this doesn't affect it.

---

## 2. Suggested files

```
src/main/java/com/plantky/
├── common/enums/ErrorCode.java                  (edit: +3 values)
├── common/util/GardenTokens.java                (new)
├── config/WebMvcConfig.java                     (edit: allow PUT, DELETE)
├── config/SchedulingConfig.java                 (new)
├── controller/GardenController.java             (new)
├── controller/PlantPassportController.java      (new)
├── domain/entity/GardenEntity.java              (new)
├── domain/entity/SpeciesPassportEntity.java     (new)
├── domain/query/GardenRequest.java              (new)
├── domain/vo/garden/GardenResponse.java         (new)
├── domain/vo/garden/CreatedGardenResponse.java  (new)
├── domain/vo/passport/PlantPassportVO.java      (new)
├── mapper/GardenMapper.java                     (new)
├── mapper/GardenPlantMapper.java                (new)
├── mapper/SpeciesPassportMapper.java            (new)
├── service/GardenService.java                   (new)
├── service/PlantPassportService.java            (new)
├── service/impl/GardenServiceImpl.java          (new)
├── service/impl/PlantPassportServiceImpl.java   (new)
└── service/job/GardenCleanupJob.java            (new)
src/main/resources/db/
├── garden_i3.sql                                (new, section 3.1)
└── species_passport_i3.sql                      (copy from this folder)
```

---

## 3. Database

### 3.1 Garden tables (`garden_i3.sql`)

Run once, after `species_data` exists.

```sql
-- My Garden: an anonymous random id and a list of plants. No personal data.
CREATE TABLE IF NOT EXISTS garden (
  garden_id        CHAR(36) NOT NULL COMMENT 'random UUID v4, not linked to any person',
  updated_at       DATETIME NOT NULL COMMENT 'UTC; used for the 90-day expiry',
  edit_token_hash  CHAR(64) NOT NULL COMMENT 'SHA-256 hex of the edit key; the key itself is never stored',
  PRIMARY KEY (garden_id),
  KEY idx_garden_updated (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS garden_plant (
  garden_id  CHAR(36)          NOT NULL,
  plant_id   BIGINT UNSIGNED   NOT NULL COMMENT 'species_data.id',
  position   SMALLINT UNSIGNED NOT NULL COMMENT 'keeps the order the user added plants',
  PRIMARY KEY (garden_id, plant_id),
  CONSTRAINT fk_gp_garden  FOREIGN KEY (garden_id) REFERENCES garden (garden_id) ON DELETE CASCADE,
  CONSTRAINT fk_gp_species FOREIGN KEY (plant_id)  REFERENCES species_data (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

- `ON DELETE CASCADE`: deleting a `garden` row removes its plants too (AC 8.2 and expiry).
- The primary key `(garden_id, plant_id)` makes duplicates impossible (AC 1.2, AC 6.4).

### 3.2 Plant passport data (`species_passport_i3.sql`)

Run the file from this folder. It creates `species_passport` (one row per plant, keyed by
`species_data.id`) and inserts all 880 plants, each matched by `scientific_name`. It was tested
against `species_data_i2_backend.sql`: 880 of 880 rows matched. The last line prints the count.

Columns: `common_name` (Iteration 3 filled names, 96% coverage), `plant_type`,
`flowers_jan`…`flowers_dec`, `flowering_label`, `flowering_sources`, `flowering_split`,
`resprouting`, `vegetative_spread`, `dispersal`, `seedbank_longevity`, `wet_soil_tolerance`,
`evidence_strength`, `evidence_available`, `evidence_missing` (comma-separated),
`vicflora_url`.

The file drops and recreates the table, so it is safe to run again after a data refresh.

---

## 4. Error codes

Add to `common/enums/ErrorCode.java`:

```java
    GARDEN_NOT_FOUND(
            HttpStatus.NOT_FOUND,
            "GARDEN_NOT_FOUND",
            "This garden link is no longer available."),
    GARDEN_EDIT_FORBIDDEN(
            HttpStatus.FORBIDDEN,
            "GARDEN_EDIT_FORBIDDEN",
            "You can view this garden but not change it."),
    INVALID_GARDEN_PLANTS(
            HttpStatus.BAD_REQUEST,
            "INVALID_GARDEN_PLANTS",
            "plantIds must contain up to 100 existing plant IDs."),
```

They are thrown as `new BusinessException(ErrorCode.X)` and turned into `ErrorResponse` by the
existing `GlobalExceptionHandler`. No handler changes are needed.

Optional but recommended: a malformed JSON body currently falls through to the generic
`Exception` handler (500). Add a handler for `HttpMessageNotReadableException` that returns
`INVALID_REQUEST` (400).

---

## 5. Security helpers

`common/util/GardenTokens.java`:

```java
package com.plantky.common.util;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.HexFormat;

/** Private edit keys for gardens. Only SHA-256 hashes are stored. */
public final class GardenTokens {

    private static final SecureRandom RANDOM = new SecureRandom();

    private GardenTokens() {
    }

    /** 32 random bytes, URL-safe Base64 (43 characters). Shown to the user once. */
    public static String newEditToken() {
        byte[] bytes = new byte[32];
        RANDOM.nextBytes(bytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }

    public static String hash(String token) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256")
                    .digest(token.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digest);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 not available", e);
        }
    }

    /** Constant-time comparison, so timing can't reveal how much of a guess was right. */
    public static boolean matches(String token, String storedHash) {
        if (token == null || token.isBlank() || storedHash == null) {
            return false;
        }
        return MessageDigest.isEqual(
                hash(token).getBytes(StandardCharsets.US_ASCII),
                storedHash.getBytes(StandardCharsets.US_ASCII));
    }
}
```

---

## 6. Entities and mappers

`map-underscore-to-camel-case: true` is already on, so `garden_id` ↔ `gardenId`.

```java
package com.plantky.domain.entity;

@Data
@TableName("garden")
public class GardenEntity {

    /** Random UUID v4 created by the backend. */
    @TableId(value = "garden_id", type = IdType.INPUT)
    private String gardenId;

    /** UTC. Reset on every save; gardens older than 90 days are deleted. */
    private LocalDateTime updatedAt;

    /** SHA-256 hex of the edit key. Never returned by the API. */
    private String editTokenHash;
}
```

```java
package com.plantky.mapper;

@Mapper
public interface GardenMapper extends BaseMapper<GardenEntity> {

    @Delete("DELETE FROM garden WHERE updated_at < #{cutoff}")
    int deleteUpdatedBefore(@Param("cutoff") LocalDateTime cutoff);
}
```

`garden_plant` has a two-column key, which `BaseMapper` doesn't handle well, so it uses plain
annotated SQL:

```java
package com.plantky.mapper;

@Mapper
public interface GardenPlantMapper {

    @Select("SELECT plant_id FROM garden_plant WHERE garden_id = #{gardenId} ORDER BY position")
    List<Long> findPlantIds(@Param("gardenId") String gardenId);

    @Delete("DELETE FROM garden_plant WHERE garden_id = #{gardenId}")
    int deleteByGardenId(@Param("gardenId") String gardenId);

    @Insert("""
            <script>
            INSERT INTO garden_plant (garden_id, plant_id, position) VALUES
            <foreach collection="plantIds" item="plantId" index="position" separator=",">
              (#{gardenId}, #{plantId}, #{position})
            </foreach>
            </script>
            """)
    int insertAll(@Param("gardenId") String gardenId, @Param("plantIds") List<Long> plantIds);
}
```

```java
package com.plantky.domain.entity;

@Data
@TableName("species_passport")
public class SpeciesPassportEntity {

    @TableId(value = "species_id", type = IdType.INPUT)
    private Long speciesId;
    private String commonName;
    private String plantType;
    private Boolean flowersJan;
    private Boolean flowersFeb;
    private Boolean flowersMar;
    private Boolean flowersApr;
    private Boolean flowersMay;
    private Boolean flowersJun;
    private Boolean flowersJul;
    private Boolean flowersAug;
    private Boolean flowersSep;
    private Boolean flowersOct;
    private Boolean flowersNov;
    private Boolean flowersDec;
    private String floweringLabel;
    private Integer floweringSources;
    private Boolean floweringSplit;
    private String resprouting;
    private String vegetativeSpread;
    private String dispersal;
    private String seedbankLongevity;
    private String wetSoilTolerance;
    private String evidenceStrength;
    private String evidenceAvailable;
    private String evidenceMissing;
    private String vicfloraUrl;

    public List<Boolean> floweringMonths() {
        return Stream.of(flowersJan, flowersFeb, flowersMar, flowersApr, flowersMay, flowersJun,
                        flowersJul, flowersAug, flowersSep, flowersOct, flowersNov, flowersDec)
                .map(Boolean.TRUE::equals)
                .toList();
    }
}
```

```java
@Mapper
public interface SpeciesPassportMapper extends BaseMapper<SpeciesPassportEntity> {
}
```

---

## 7. Request and response classes

```java
package com.plantky.domain.query;

@Data
public class GardenRequest {
    /** species_data ids. Missing = empty list. Checked in the service. */
    private List<Long> plantIds;
}
```

```java
package com.plantky.domain.vo.garden;

@Getter
@Builder
public class GardenResponse {
    private final String gardenId;
    private final List<Long> plantIds;
    /** Serialised as e.g. "2026-09-29T11:55:39". */
    private final LocalDateTime updatedAt;
}
```

```java
@Getter
@Builder
public class CreatedGardenResponse {
    private final String gardenId;
    private final List<Long> plantIds;
    private final LocalDateTime updatedAt;
    /** Returned only by POST /gardens. Never stored in plain text. */
    private final String editToken;
}
```

The passport uses **snake_case** JSON on purpose, so the reference Vue code works unchanged.
Records keep it short; `@JsonNaming` must be on every nested record too.

```java
package com.plantky.domain.vo.passport;

@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public record PlantPassportVO(
        Long plantId,
        String scientificName,
        String commonName,
        String recommendation,          // "Reconsider Planting" | "Use Caution" | "Lower Concern" | "Not Assessed"
        String origin,                  // "native" | "introduced" | null
        String establishment,
        String plantType,
        Traits traits,
        Flowering flowering,
        Spread spread,
        String wetSoilTolerance,
        LocalRecords localRecords,
        boolean griisListedIntroduced,
        Evidence evidence,
        String vicfloraUrl) {

    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public record Traits(String growthForm, String woodiness, String lifeHistory,
                         Double heightMinM, Double heightMaxM) {}

    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public record Flowering(List<Boolean> months, String label, int sources, boolean splitPattern) {}

    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public record Spread(String resprouting, String vegetativeSpread, String dispersal,
                         String seedbankLongevity) {}

    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public record LocalRecords(Integer vba100Count, Integer vba100LatestYear,
                               Integer alaCount, String alaLatestDate) {}

    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public record Evidence(String strength, List<String> available, List<String> missing) {}
}
```

> Check after building: `height_min_m` / `height_max_m` and `vba100_count` must come out exactly
> like that. If Jackson splits the digits differently, put `@JsonProperty("vba100_count")` etc.
> on those components.

---

## 8. Garden service

```java
package com.plantky.service;

public interface GardenService {
    CreatedGardenResponse create(List<Long> plantIds);
    GardenResponse get(String gardenId);
    GardenResponse update(String gardenId, String editToken, List<Long> plantIds);
    void delete(String gardenId, String editToken);
}
```

```java
package com.plantky.service.impl;

@Service
@RequiredArgsConstructor
public class GardenServiceImpl implements GardenService {

    public static final int MAX_PLANTS = 100;
    public static final Duration RETENTION = Duration.ofDays(90);

    private final GardenMapper gardenMapper;
    private final GardenPlantMapper gardenPlantMapper;
    private final SpeciesDataMapper speciesDataMapper;

    @Override
    @Transactional
    public CreatedGardenResponse create(List<Long> rawPlantIds) {
        List<Long> plantIds = cleanPlantIds(rawPlantIds);
        String editToken = GardenTokens.newEditToken();

        GardenEntity garden = new GardenEntity();
        garden.setGardenId(UUID.randomUUID().toString()); // version 4, SecureRandom
        garden.setUpdatedAt(nowUtc());
        garden.setEditTokenHash(GardenTokens.hash(editToken));
        gardenMapper.insert(garden);
        savePlants(garden.getGardenId(), plantIds);

        return CreatedGardenResponse.builder()
                .gardenId(garden.getGardenId())
                .plantIds(plantIds)
                .updatedAt(garden.getUpdatedAt())
                .editToken(editToken)
                .build();
    }

    @Override
    @Transactional(readOnly = true)
    public GardenResponse get(String rawGardenId) {
        GardenEntity garden = loadLiveGarden(parseGardenId(rawGardenId));
        return toResponse(garden);
    }

    @Override
    @Transactional
    public GardenResponse update(String rawGardenId, String editToken, List<Long> rawPlantIds) {
        GardenEntity garden = loadLiveGarden(parseGardenId(rawGardenId)); // 404 first
        requireEditToken(garden, editToken);                              // then 403
        List<Long> plantIds = cleanPlantIds(rawPlantIds);                 // then 400

        garden.setUpdatedAt(nowUtc()); // resets the 90-day expiry
        gardenMapper.updateById(garden);
        savePlants(garden.getGardenId(), plantIds);
        return toResponse(garden);
    }

    @Override
    @Transactional
    public void delete(String rawGardenId, String editToken) {
        GardenEntity garden = loadLiveGarden(parseGardenId(rawGardenId));
        requireEditToken(garden, editToken);
        gardenMapper.deleteById(garden.getGardenId()); // garden_plant rows go by ON DELETE CASCADE
    }

    // ------------------------------------------------------------ helpers

    /**
     * Only real random (version 4) UUIDs are accepted. Anything else is a 404, so gardens
     * can't be found by guessing simple ids.
     */
    private String parseGardenId(String raw) {
        try {
            UUID parsed = UUID.fromString(raw);
            String normalised = parsed.toString();
            if (parsed.version() == 4 && normalised.equals(raw.toLowerCase(Locale.ROOT))) {
                return normalised;
            }
        } catch (IllegalArgumentException ignored) {
            // fall through to 404
        }
        throw new BusinessException(ErrorCode.GARDEN_NOT_FOUND);
    }

    /** 404 if missing or older than 90 days (even if the hourly clean-up hasn't run yet). */
    private GardenEntity loadLiveGarden(String gardenId) {
        GardenEntity garden = gardenMapper.selectById(gardenId);
        if (garden == null || garden.getUpdatedAt().isBefore(nowUtc().minus(RETENTION))) {
            throw new BusinessException(ErrorCode.GARDEN_NOT_FOUND);
        }
        return garden;
    }

    private void requireEditToken(GardenEntity garden, String editToken) {
        if (!GardenTokens.matches(editToken, garden.getEditTokenHash())) {
            throw new BusinessException(ErrorCode.GARDEN_EDIT_FORBIDDEN);
        }
    }

    /** Missing = empty. Max 100, all positive, all must exist. Duplicates dropped, order kept. */
    private List<Long> cleanPlantIds(List<Long> raw) {
        if (raw == null) {
            return List.of();
        }
        if (raw.size() > MAX_PLANTS || raw.stream().anyMatch(id -> id == null || id <= 0)) {
            throw new BusinessException(ErrorCode.INVALID_GARDEN_PLANTS);
        }
        List<Long> unique = new ArrayList<>(new LinkedHashSet<>(raw));
        if (!unique.isEmpty()) {
            Long found = speciesDataMapper.selectCount(
                    new LambdaQueryWrapper<SpeciesDataEntity>().in(SpeciesDataEntity::getId, unique));
            if (found == null || found != unique.size()) {
                throw new BusinessException(ErrorCode.INVALID_GARDEN_PLANTS);
            }
        }
        return unique;
    }

    private void savePlants(String gardenId, List<Long> plantIds) {
        gardenPlantMapper.deleteByGardenId(gardenId);
        if (!plantIds.isEmpty()) {
            gardenPlantMapper.insertAll(gardenId, plantIds);
        }
    }

    private GardenResponse toResponse(GardenEntity garden) {
        return GardenResponse.builder()
                .gardenId(garden.getGardenId())
                .plantIds(gardenPlantMapper.findPlantIds(garden.getGardenId()))
                .updatedAt(garden.getUpdatedAt())
                .build();
    }

    private static LocalDateTime nowUtc() {
        return LocalDateTime.now(ZoneOffset.UTC).truncatedTo(ChronoUnit.SECONDS);
    }
}
```

---

## 9. Garden controller

```java
package com.plantky.controller;

@Validated
@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/gardens")
@Tag(name = "Gardens", description = "Iteration 3 My Garden: anonymous saved gardens")
public class GardenController {

    static final String EDIT_HEADER = "X-Garden-Edit-Token";

    private final GardenService gardenService;

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    @Operation(summary = "Create a saved garden (returns the edit key once)")
    public CreatedGardenResponse create(@RequestBody GardenRequest request) {
        return gardenService.create(request.getPlantIds());
    }

    @GetMapping("/{gardenId}")
    @Operation(summary = "Read a garden (share link and edit link)")
    public GardenResponse get(@PathVariable String gardenId) {
        return gardenService.get(gardenId);
    }

    @PutMapping("/{gardenId}")
    @Operation(summary = "Replace the garden's plant list (needs the edit key)")
    public GardenResponse update(
            @PathVariable String gardenId,
            @RequestHeader(value = EDIT_HEADER, required = false) String editToken,
            @RequestBody GardenRequest request) {
        return gardenService.update(gardenId, editToken, request.getPlantIds());
    }

    @DeleteMapping("/{gardenId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    @Operation(summary = "Delete the saved garden (needs the edit key)")
    public void delete(
            @PathVariable String gardenId,
            @RequestHeader(value = EDIT_HEADER, required = false) String editToken) {
        gardenService.delete(gardenId, editToken);
    }
}
```

`required = false` on the header is deliberate: a missing key should give our **403**
`GARDEN_EDIT_FORBIDDEN`, not Spring's default 400.

---

## 10. Passport service and controller

The recommendation uses the **same rule as our `RecommendationService.determineLevel`**
(Very High/High → Reconsider Planting, Moderately High/Medium → Use Caution, Lower → Lower
Concern, otherwise Not Assessed), so garden badges always match the assessment page.

```java
package com.plantky.service.impl;

@Service
@RequiredArgsConstructor
public class PlantPassportServiceImpl implements PlantPassportService {

    private static final int MAX_IDS = 100;

    private final SpeciesDataMapper speciesDataMapper;
    private final SpeciesPassportMapper speciesPassportMapper;
    private final PlantClassificationService plantClassificationService;

    @Override
    public Map<String, PlantPassportVO> findPassports(List<Long> requestedIds) {
        List<Long> ids = requestedIds.stream().distinct().limit(MAX_IDS).toList();
        if (ids.isEmpty()) {
            return Map.of();
        }
        Map<Long, SpeciesDataEntity> species = speciesDataMapper.selectBatchIds(ids).stream()
                .collect(Collectors.toMap(SpeciesDataEntity::getId, s -> s));
        Map<Long, SpeciesPassportEntity> extra = speciesPassportMapper.selectBatchIds(ids).stream()
                .collect(Collectors.toMap(SpeciesPassportEntity::getSpeciesId, p -> p));

        Map<String, PlantPassportVO> result = new LinkedHashMap<>();
        for (Long id : ids) {                       // unknown ids are simply left out
            SpeciesDataEntity s = species.get(id);
            if (s != null) {
                result.put(String.valueOf(id), toVO(s, extra.get(id)));
            }
        }
        return result;
    }

    @Override
    public PlantPassportVO findPassport(Long plantId) {
        PlantPassportVO vo = findPassports(List.of(plantId)).get(String.valueOf(plantId));
        if (vo == null) {
            throw new PlantNotFoundException();
        }
        return vo;
    }

    private PlantPassportVO toVO(SpeciesDataEntity s, SpeciesPassportEntity p) {
        boolean hasFlowering = p != null && p.getFloweringLabel() != null;
        return new PlantPassportVO(
                s.getId(),
                s.getScientificName(),
                p != null && p.getCommonName() != null ? p.getCommonName() : s.getVernacularName(),
                recommendation(plantClassificationService.resolveEnvironmentalConcern(s)),
                s.getEstablishmentMeans() == null ? null : s.getEstablishmentMeans().toLowerCase(Locale.ROOT),
                s.getDegreeOfEstablishment(),
                p == null ? null : p.getPlantType(),
                new PlantPassportVO.Traits(s.getGrowthForm(), s.getWoodiness(), s.getLifeHistory(),
                        s.getHeightMin(), s.getHeightMax()),
                new PlantPassportVO.Flowering(
                        hasFlowering ? p.floweringMonths() : null,
                        hasFlowering ? p.getFloweringLabel() : null,
                        p == null || p.getFloweringSources() == null ? 0 : p.getFloweringSources(),
                        p != null && Boolean.TRUE.equals(p.getFloweringSplit())),
                p == null ? new PlantPassportVO.Spread(null, null, null, null)
                        : new PlantPassportVO.Spread(p.getResprouting(), p.getVegetativeSpread(),
                                p.getDispersal(), p.getSeedbankLongevity()),
                p == null ? null : p.getWetSoilTolerance(),
                new PlantPassportVO.LocalRecords(
                        s.getVba100RecordCount(), s.getVba100MostRecentYear(), s.getAlaRecordCount(),
                        s.getAlaMostRecentDate() == null ? null : s.getAlaMostRecentDate().toString()),
                Boolean.TRUE.equals(s.getGriisListed()),
                new PlantPassportVO.Evidence(
                        p == null ? "Limited" : p.getEvidenceStrength(),
                        p == null ? List.of() : splitList(p.getEvidenceAvailable()),
                        p == null ? List.of() : splitList(p.getEvidenceMissing())),
                p == null ? null : p.getVicfloraUrl());
    }

    /** Same mapping as RecommendationService.determineLevel. */
    private static String recommendation(EnvironmentalConcern concern) {
        RecommendationLevel level = switch (concern) {
            case VERY_HIGH, HIGH -> RecommendationLevel.RECONSIDER_PLANTING;
            case MODERATELY_HIGH, MEDIUM -> RecommendationLevel.USE_CAUTION;
            case LOWER -> RecommendationLevel.LOWER_CONCERN;
            default -> RecommendationLevel.NOT_ASSESSED;
        };
        return level.getDisplayLabel();
    }

    private static List<String> splitList(String csv) {
        return csv == null || csv.isBlank() ? List.of() : List.of(csv.split(","));
    }
}
```

```java
package com.plantky.controller;

@Validated
@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/plants")
@Tag(name = "Plant Passports", description = "Iteration 3 plant details for My Garden")
public class PlantPassportController {

    private final PlantPassportService plantPassportService;

    @GetMapping("/passports")
    @Operation(summary = "Passports for many plants (ids=3,7,120)")
    public Map<String, PlantPassportVO> findPassports(@RequestParam(defaultValue = "") String ids) {
        List<Long> parsed = new ArrayList<>();
        for (String part : ids.split(",")) {
            if (part.isBlank()) {
                continue;
            }
            try {
                parsed.add(Long.parseLong(part.trim()));
            } catch (NumberFormatException e) {
                throw new BusinessException(ErrorCode.INVALID_REQUEST, "ids must be numbers.");
            }
        }
        return plantPassportService.findPassports(parsed);
    }

    @GetMapping("/{plantId}/passport")
    @Operation(summary = "Passport for one plant")
    public PlantPassportVO findPassport(@Positive @PathVariable Long plantId) {
        return plantPassportService.findPassport(plantId);
    }
}
```

`/passports` doesn't clash with the existing `/{plantId}/assessment` routes; Spring prefers the
literal path.

---

## 11. Expiry job

```java
package com.plantky.config;

@Configuration
@EnableScheduling
public class SchedulingConfig {
}
```

```java
package com.plantky.service.job;

@Slf4j
@Component
@RequiredArgsConstructor
public class GardenCleanupJob {

    private final GardenMapper gardenMapper;

    /** Hourly: delete gardens not changed for 90 days (their plants go by cascade). */
    @Scheduled(initialDelay = 60_000, fixedDelay = 3_600_000)
    public void deleteExpiredGardens() {
        LocalDateTime cutoff = LocalDateTime.now(ZoneOffset.UTC).minus(GardenServiceImpl.RETENTION);
        int deleted = gardenMapper.deleteUpdatedBefore(cutoff);
        if (deleted > 0) {
            log.info("Deleted {} expired gardens", deleted); // count only, never ids or keys
        }
    }
}
```

---

## 12. CORS

In `config/WebMvcConfig.java`, the browser must be allowed to send `PUT` and `DELETE`:

```java
                .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
```

`allowedHeaders("*")` already covers `X-Garden-Edit-Token`. The Amplify origin is already in
`plantky.cors.allowed-origins`.

---

## 13. Privacy and security checklist

These are what make the epic's “no personal data” promise true. Please keep all of them.

- [ ] Store only `garden_id`, `updated_at`, `edit_token_hash` and plant ids. No names, emails,
      IP addresses, user agents or cookies.
- [ ] Never store or log the plain edit key. Store only the SHA-256 hash; compare with
      `MessageDigest.isEqual`.
- [ ] `GET` never returns `editToken` or `editTokenHash`. Only `POST` returns `editToken`, once.
- [ ] Don't log request headers or full URLs for `/api/v1/gardens/**`. Leave the Tomcat access
      log off (`server.tomcat.accesslog.enabled` is `false` by default). If nginx or a load
      balancer sits in front on EC2, turn off its access log or drop the client IP from it.
- [ ] Garden ids come only from `UUID.randomUUID()`. Never accept a client-chosen id.
- [ ] Non-UUID-v4 ids return 404, not 400, so ids can't be probed.
- [ ] Gardens older than 90 days are hidden on read and deleted hourly.

---

## 14. Tests (one per acceptance criterion that touches the backend)

Following our existing `PlantControllerTest` style (`@WebMvcTest` + `MockMvc`) for the controller,
plus a service test with mocked mappers:

| Test | Expect | AC |
|---|---|---|
| `POST {"plantIds":[3,7]}` | 201, UUID v4 `gardenId`, 43-char `editToken`, `plantIds` `[3,7]` | 4.1 |
| `POST {"plantIds":[3,3,7]}` | `plantIds` `[3,7]` (duplicates dropped, order kept) | 1.2, 6.4 |
| `POST` with 101 ids / id `0` / unknown id | 400 `INVALID_GARDEN_PLANTS` | 4.1 |
| `POST {}` | 201, `plantIds` `[]` | 4.1 |
| `GET` existing garden | 200, no `editToken` field | 6.1, 7.2 |
| `GET /gardens/123` or a UUID v1 | 404 `GARDEN_NOT_FOUND` | 5.2 |
| `GET` garden with `updated_at` 91 days ago | 404 | 5.2 |
| `PUT` without header / wrong key | 403 `GARDEN_EDIT_FORBIDDEN`, list unchanged | 6.1, 6.5 |
| `PUT` with key | 200, new list, `updatedAt` moved forward | 4.2 |
| `PUT {"plantIds":[]}` with key | 200, `[]`; `GET` still 200 | 8.1 |
| `DELETE` without key | 403, garden still readable | 6.1 |
| `DELETE` with key | 204; then `GET` 404 and `PUT` 404 | 8.2 |
| `GardenCleanupJob` | deletes only gardens older than 90 days | 5.2 |
| `GET /plants/passports?ids=3,99999` | 200, only key `"3"` | 2.1 |
| `GET /plants/passports?ids=abc` | 400 `INVALID_REQUEST` | — |
| Passport for a Very High risk plant | `recommendation` `"Reconsider Planting"` (same as `/assessment`) | 2.2, 3.1 |
| Passport JSON keys | snake_case, e.g. `plant_id`, `flowering.label`, `height_max_m` | 3.1 |

Quick manual test with curl (local):

```bash
BASE=http://localhost:8080/api/v1
curl -s -X POST $BASE/gardens -H 'Content-Type: application/json' -d '{"plantIds":[3,7]}'
curl -s $BASE/gardens/<gardenId>
curl -s -o /dev/null -w '%{http_code}\n' -X PUT $BASE/gardens/<gardenId> -H 'Content-Type: application/json' -d '{"plantIds":[3]}'
curl -s -X PUT $BASE/gardens/<gardenId> -H 'Content-Type: application/json' -H 'X-Garden-Edit-Token: <editToken>' -d '{"plantIds":[3]}'
curl -s -o /dev/null -w '%{http_code}\n' -X DELETE $BASE/gardens/<gardenId> -H 'X-Garden-Edit-Token: <editToken>'
curl -s "$BASE/plants/passports?ids=3,7"
```

(Expected: 201 JSON, 200 JSON, **403**, 200 JSON, **204**, passports JSON.)

---

## 15. What the frontend does (so the backend makes sense)

Full detail is in `../MY_GARDEN_API.md` section 4. In short:

- **Adding plants needs no API call.** The list lives in the browser (`localStorage` key
  `plantassure.garden.v2`). The server is only used after “Get a private link”.
- **Share link:** `/garden/{gardenId}` → `GET` only, shown read-only.
- **Edit link:** `/garden/{gardenId}#edit={editToken}`. The key sits after `#`, so browsers
  never send it to any server. The page reads it, keeps it in `localStorage`, sends it in
  `X-Garden-Edit-Token`, and removes it from the address bar.
- **Auto-save:** about 600 ms after any change, `PUT` with the full list.
- **Copy these plants to my garden:** frontend only. Nothing is sent to the shared garden.
- **Status codes the frontend reacts to:** `404` → “This garden link is no longer available”;
  `403` → stop syncing, keep the list in the browser.
- **Print / PDF:** frontend only; swap names come from the existing `/alternatives?limit=3`.

To reuse the reference frontend, copy `stores/garden.ts`, `api/gardens.ts`, `api/passport.ts`,
`types/passport.ts`, `utils/passportPresentation.ts` and `views/MyGardenView.vue`, add the
`/garden` and `/garden/:gardenId` routes, and point `VITE_API_BASE_URL` at our backend.
