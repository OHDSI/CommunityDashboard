"""
Shared OHDSI constants and terminology.

Centralizes all OHDSI-related keyword lists, tool names, concept terms,
and term dictionaries used across fetchers and post-processors.
"""

# ============================================================================
# OHDSI Tool Names
# ============================================================================
OHDSI_TOOLS = [
    'atlas',
    'webapi',
    'achilles',
    'hades',
    'whiterabbit',
    'rabbitinahat',
    'usagi',
    'data quality dashboard',
    'patient level prediction',
    'cohort method',
    'feature extraction',
    'circe',
    'calypso',
    'heracles',
    'hermes',
    'athena',
]

# Canonical tool names (mixed case, for display and case-sensitive matching)
OHDSI_TOOLS_DISPLAY = [
    'Atlas',
    'WebAPI',
    'Achilles',
    'HADES',
    'WhiteRabbit',
    'RabbitInAHat',
    'Usagi',
    'DataQualityDashboard',
    'PatientLevelPrediction',
    'CohortMethod',
    'FeatureExtraction',
]

# ============================================================================
# OHDSI Concepts
# ============================================================================
OHDSI_CONCEPTS = [
    'omop',
    'cdm',
    'common data model',
    'vocabulary',
    'concept',
    'concept set',
    'cohort',
    'cohort definition',
    'phenotype',
    'characterization',
    'estimation',
    'prediction',
    'standardized',
    'observational',
    'observational health',
    'real world evidence',
]

# ============================================================================
# Combined OHDSI Keywords (for relevance checking)
# ============================================================================
# This is the superset used by _is_ohdsi_related() across all fetchers.
OHDSI_KEYWORDS = [
    'ohdsi',
    'omop',
    'cdm',
    'common data model',
    'atlas',
    'achilles',
    'hades',
    'webapi',
    'whiterabbit',
    'rabbitinahat',
    'usagi',
    'data quality dashboard',
    'patient level prediction',
    'patient-level prediction',
    'cohort method',
    'feature extraction',
    'observational health',
    'population level estimation',
    'population-level estimation',
    'vocabulary',
    'concept set',
    'cohort definition',
    'phenotype',
    'characterization',
]

# ============================================================================
# Short Keywords (for tag/topic matching where full phrases are uncommon)
# ============================================================================
OHDSI_TAG_KEYWORDS = [
    'ohdsi',
    'omop',
    'cdm',
    'atlas',
    'hades',
]

# ============================================================================
# OHDSI Terms with Descriptions (for post-processors)
# ============================================================================
# Structured term dictionary used by PostProcessor and TranscriptProcessor.
OHDSI_TERMS = {
    'tools': [
        'atlas', 'webapi', 'achilles', 'hades', 'whiterabbit',
        'rabbitinahat', 'usagi', 'data quality dashboard',
        'patient level prediction', 'cohort method', 'feature extraction',
        'circe', 'calypso', 'heracles', 'hermes', 'athena',
    ],
    'concepts': [
        'omop', 'cdm', 'common data model', 'observational health',
        'ohdsi', 'vocabulary', 'concept', 'concept set',
        'cohort', 'cohort definition',
        'phenotype', 'characterization', 'estimation', 'prediction',
        'standardized', 'observational', 'real world evidence',
    ],
    'technical': [
        'sql', 'r package', 'python', 'java', 'postgresql',
        'sql server', 'oracle', 'redshift', 'bigquery', 'spark',
        'docker', 'kubernetes', 'api', 'rest', 'graphql',
    ],
    'clinical': [
        'ehr', 'claims', 'registry', 'clinical trial',
        'patient', 'diagnosis', 'procedure', 'medication',
        'outcome', 'exposure', 'condition', 'drug',
    ],
    'databases': [
        'claims', 'ehr', 'electronic health record', 'administrative',
        'clinical', 'real world data', 'rwd', 'real world evidence', 'rwe',
    ],
}

# ============================================================================
# Discourse-Specific Constants
# ============================================================================
DISCOURSE_MONITORED_CATEGORIES = [
    'announcements',
    'researchers',
    'implementers',
    'developers',
    'cdm',
    'vocabulary-users',
    'atlas-users',
    'achilles-users',
    'hades-developers',
    'webapi-developers',
    'study-questions',
    'covid-19',
]

DISCOURSE_SEARCH_TERMS = [
    'OMOP CDM',
    'Atlas',
    'HADES',
    'Achilles',
    'WebAPI',
    'WhiteRabbit',
    'DataQualityDashboard',
    'PatientLevelPrediction',
    'CohortMethod',
    'FeatureExtraction',
    'study protocol',
    'cohort definition',
    'concept set',
    'phenotype',
    'characterization',
]

# ============================================================================
# YouTube-Specific Constants
# ============================================================================
YOUTUBE_SEARCH_QUERIES = [
    'OHDSI',
    'OMOP CDM',
    'OHDSI Atlas',
    'HADES OHDSI',
    'Observational Health Data Sciences',
    'OHDSI symposium',
    'OHDSI tutorial',
    'OMOP Common Data Model',
]

# ============================================================================
# GitHub-Specific Constants
# ============================================================================
GITHUB_SEARCH_QUERIES = [
    'OHDSI',
    'OMOP CDM',
    'OMOP Common Data Model',
    'Atlas OHDSI',
    'HADES in:readme',
    'Achilles OHDSI',
    'WebAPI OHDSI',
    'WhiteRabbit ETL',
    'DataQualityDashboard',
    'PatientLevelPrediction',
    'CohortMethod',
    'topic:ohdsi',
    'topic:omop',
    'topic:cdm',
]

GITHUB_OHDSI_ORGS = [
    'OHDSI',
    'OHDSI-Studies',
    'ohdsi-studies',
]

# ============================================================================
# Known OHDSI Discourse Category IDs
# ============================================================================
OHDSI_DISCOURSE_CATEGORY_IDS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
