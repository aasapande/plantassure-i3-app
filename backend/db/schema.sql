-- PlantAssure Iteration 3 -- relational schema (MySQL 8)
-- Plant data comes from the Iteration 3 pipeline; gardens hold only plant ids.

DROP TABLE IF EXISTS garden_plant;
DROP TABLE IF EXISTS garden;
DROP TABLE IF EXISTS plant_alternative;
DROP TABLE IF EXISTS plant_evidence;
DROP TABLE IF EXISTS plant_flowering;
DROP TABLE IF EXISTS plant_local_records;
DROP TABLE IF EXISTS plant;

CREATE TABLE plant (
  plant_id              INT UNSIGNED  NOT NULL,
  scientific_name       VARCHAR(150)  NOT NULL,
  common_name           VARCHAR(200)  NULL,
  common_name_source    VARCHAR(40)   NULL,      -- VicFlora / VBA / DEECA Advisory List / ALA
  family                VARCHAR(80)   NULL,
  origin                ENUM('native','introduced','uncertain') NULL,
  establishment         VARCHAR(40)   NULL,      -- native / naturalised / adventive
  risk_rating           VARCHAR(60)   NULL,      -- raw DEECA Advisory List value
  recommendation        ENUM('Reconsider Planting','Use Caution','Lower Concern','Not Assessed') NOT NULL,
  plant_type            ENUM('Tree','Shrub','Grass','Herb','Climber','Fern') NULL,
  growth_form           VARCHAR(60)   NULL,
  woodiness             VARCHAR(40)   NULL,
  life_history          VARCHAR(80)   NULL,
  height_min_m          DECIMAL(6,2)  NULL,
  height_max_m          DECIMAL(6,2)  NULL,
  flowering_label       VARCHAR(60)   NULL,      -- e.g. "Sep–Nov"
  flowering_sources     TINYINT UNSIGNED NOT NULL DEFAULT 0,
  flowering_split       BOOLEAN       NOT NULL DEFAULT FALSE,
  resprouting           VARCHAR(40)   NULL,
  vegetative_spread     VARCHAR(40)   NULL,
  dispersal             VARCHAR(120)  NULL,
  seedbank_longevity    VARCHAR(40)   NULL,
  wet_soil_tolerance    VARCHAR(80)   NULL,
  griis_listed_introduced BOOLEAN     NOT NULL DEFAULT FALSE,
  evidence_strength     ENUM('Strong','Moderate','Limited') NOT NULL,
  alternatives_status   VARCHAR(60)   NOT NULL,
  vicflora_url          VARCHAR(200)  NULL,
  PRIMARY KEY (plant_id),
  UNIQUE KEY uk_plant_scientific_name (scientific_name),
  KEY idx_plant_recommendation (recommendation),
  KEY idx_plant_common_name (common_name)
) ENGINE=InnoDB;

-- One row per month the plant flowers (1 = Jan ... 12 = Dec)
CREATE TABLE plant_flowering (
  plant_id  INT UNSIGNED     NOT NULL,
  month     TINYINT UNSIGNED NOT NULL,
  PRIMARY KEY (plant_id, month),
  CONSTRAINT fk_flowering_plant FOREIGN KEY (plant_id) REFERENCES plant (plant_id) ON DELETE CASCADE,
  CONSTRAINT chk_flowering_month CHECK (month BETWEEN 1 AND 12)
) ENGINE=InnoDB;

-- Occurrence evidence in the City of Monash (VBA_FLORA100 + ALA)
CREATE TABLE plant_local_records (
  plant_id            INT UNSIGNED NOT NULL,
  vba100_count        INT UNSIGNED NOT NULL DEFAULT 0,
  vba100_latest_year  SMALLINT UNSIGNED NULL,
  ala_count           INT UNSIGNED NOT NULL DEFAULT 0,
  ala_latest_year     SMALLINT UNSIGNED NULL,
  PRIMARY KEY (plant_id),
  CONSTRAINT fk_records_plant FOREIGN KEY (plant_id) REFERENCES plant (plant_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Which kinds of verified evidence exist for each plant
CREATE TABLE plant_evidence (
  plant_id       INT UNSIGNED NOT NULL,
  evidence_type  ENUM('rating','origin','local_records','traits','flowering','griis') NOT NULL,
  PRIMARY KEY (plant_id, evidence_type),
  CONSTRAINT fk_evidence_plant FOREIGN KEY (plant_id) REFERENCES plant (plant_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Swap suggestions from the pipeline's strict four-trait match
CREATE TABLE plant_alternative (
  plant_id        INT UNSIGNED     NOT NULL,
  alternative_id  INT UNSIGNED     NOT NULL,
  rank_order      TINYINT UNSIGNED NOT NULL,
  PRIMARY KEY (plant_id, alternative_id),
  CONSTRAINT fk_alt_plant FOREIGN KEY (plant_id) REFERENCES plant (plant_id) ON DELETE CASCADE,
  CONSTRAINT fk_alt_alternative FOREIGN KEY (alternative_id) REFERENCES plant (plant_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- My Garden: an anonymous random id and a list of plants. No personal data.
CREATE TABLE garden (
  garden_id   CHAR(36)  NOT NULL,     -- random UUID v4, not linked to any person
  updated_at  DATETIME  NOT NULL,     -- used for the 90-day expiry
  PRIMARY KEY (garden_id),
  KEY idx_garden_updated (updated_at)
) ENGINE=InnoDB;

CREATE TABLE garden_plant (
  garden_id  CHAR(36)          NOT NULL,
  plant_id   INT UNSIGNED      NOT NULL,
  position   SMALLINT UNSIGNED NOT NULL,
  PRIMARY KEY (garden_id, plant_id),
  CONSTRAINT fk_gp_garden FOREIGN KEY (garden_id) REFERENCES garden (garden_id) ON DELETE CASCADE,
  CONSTRAINT fk_gp_plant FOREIGN KEY (plant_id) REFERENCES plant (plant_id)
) ENGINE=InnoDB;
