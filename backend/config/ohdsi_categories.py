"""
OHDSI Category Definitions
Simplified 4-category system for OHDSI-related research and tools

This module provides a centralized, extensible category system that can be:
- Easily extended with new categories
- Imported by any module that needs category information
- Updated without changing code in multiple places
"""

from typing import List, Dict, Set, Optional
from dataclasses import dataclass, field
import json
from pathlib import Path

@dataclass
class CategoryDefinition:
    """Defines a single category with its metadata"""
    name: str
    group: str
    keywords: List[str] = field(default_factory=list)
    description: str = ""
    aliases: List[str] = field(default_factory=list)
    parent: Optional[str] = None  # For hierarchical categories

    def matches(self, text: str) -> bool:
        """Check if this category matches the given text"""
        text_lower = text.lower()

        # Check name
        if self.name.lower() in text_lower:
            return True

        # Check keywords
        for keyword in self.keywords:
            if keyword.lower() in text_lower:
                return True

        # Check aliases
        for alias in self.aliases:
            if alias.lower() in text_lower:
                return True

        return False


class OHDSICategorySystem:
    """
    Centralized category management system for OHDSI
    This class can be extended or configured to add new categories
    """

    def __init__(self, config_file: Optional[Path] = None):
        self.categories: Dict[str, CategoryDefinition] = {}
        self.groups: Dict[str, List[str]] = {}

        # Load from config file if provided, otherwise use defaults
        if config_file and config_file.exists():
            self._load_from_config(config_file)
        else:
            self._initialize_default_categories()

    def _initialize_default_categories(self):
        """Initialize the default OHDSI categories"""

        categories = [
            CategoryDefinition(
                name="Observational data standards and management",
                group="OHDSI",
                keywords=[
                    # OMOP CDM & data model
                    "omop", "cdm", "common data model", "standardized data",
                    "observational medical", "data model",
                    # Vocabularies & terminology
                    "athena", "vocabulary", "terminology", "concept", "snomed",
                    "icd", "loinc", "concept mapping", "code mapping",
                    # Data quality & profiling
                    "dqd", "data quality", "quality dashboard", "data validation",
                    "database profiling", "data profiling",
                    # ETL & conversion tools
                    "etl", "extract transform load", "data conversion",
                    "data pipeline", "data integration", "mapping",
                    "whiterabbit", "rabbitinahat", "usagi",
                    "source to cdm", "source data",
                    # Data governance & standards
                    "governance", "privacy", "security", "hipaa", "gdpr",
                    "compliance", "de-identification",
                    # Interoperability
                    "interoperability", "fhir", "hl7", "standards",
                    "data exchange",
                    # Infrastructure
                    "infrastructure", "deployment", "docker", "kubernetes",
                    "cloud", "server", "database",
                    # Data sources
                    "ehr", "electronic health record", "emr", "clinical data",
                    "hospital data", "claims", "insurance", "billing",
                    "administrative", "medicare", "medicaid",
                    "registry", "disease registry", "patient registry",
                    "imaging data", "dicom", "pacs",
                    "genomic", "genetic", "dna", "rna", "sequencing",
                    "gwas", "pharmacogenomics", "biomarker",
                    "wearable", "sensor", "digital health", "mhealth",
                    "remote monitoring", "patient reported", "pro", "prom",
                    "patient survey", "quality of life",
                ],
                description="OMOP CDM, vocabularies, ETL, data quality, data governance, and data source integration",
                aliases=["CDM", "OMOP", "Data Standards", "ETL", "Data Management"],
            ),
            CategoryDefinition(
                name="Methodological research",
                group="OHDSI",
                keywords=[
                    # Phenotyping
                    "phenotype", "phenotyping", "computable phenotype",
                    "case definition", "cohort identification",
                    # Prediction
                    "patient level prediction", "plp", "risk prediction",
                    "prognostic model", "predictive model",
                    # Estimation
                    "population level estimation", "ple", "causal inference",
                    "comparative effectiveness", "treatment effect",
                    # Characterization
                    "characterization", "descriptive", "baseline characteristics",
                    "incidence", "prevalence",
                    # Network studies
                    "network study", "multi-site", "collaborative", "federated",
                    # Machine learning & AI
                    "machine learning", "deep learning", "neural network",
                    "artificial intelligence", "ensemble", "xgboost",
                    "random forest",
                    # NLP
                    "nlp", "text mining", "clinical notes", "unstructured data",
                    "named entity", "text extraction",
                    # Distributed analytics
                    "distributed analytics", "privacy preserving",
                    "secure multiparty", "differential privacy",
                    # Real-world evidence & health economics
                    "real world evidence", "rwe", "real world data", "rwd",
                    "effectiveness", "health economics", "cost effectiveness",
                    "heor", "economic", "cost benefit",
                    # Methods general
                    "statistical method", "study design", "methodology",
                    "biostatistics", "epidemiology",
                ],
                description="Statistical methods, prediction, estimation, phenotyping, network studies, and evidence generation",
                aliases=["Methods", "PLP", "PLE", "RWE", "Analytics Methods"],
            ),
            CategoryDefinition(
                name="Open-source analytics development",
                group="OHDSI",
                keywords=[
                    # Core analytics tools
                    "atlas", "cohort definition", "cohort builder", "ohdsi atlas",
                    "hades", "r packages", "ohdsi r", "analytics suite",
                    "achilles", "database characterization", "descriptive statistics",
                    "webapi", "rest api", "ohdsi api", "web services",
                    # HADES ecosystem packages
                    "cohortmethod", "selfcontrolledcaseseries",
                    "evidencesynthesis", "cohortdiagnostics",
                    "featureextraction", "populationlevelestimation",
                    "patientlevelprediction",
                    "circe", "arachne", "perseus",
                    # Community & open source
                    "open source", "package", "library", "repository",
                    "community tool", "ohdsi study", "study protocol",
                    "study package",
                    # Education & training
                    "tutorial", "education", "training", "course",
                    "workshop", "learning",
                    # Software development
                    "software development", "r package", "python package",
                    "github", "cran", "api development",
                ],
                description="OHDSI open-source tools, HADES R packages, Atlas, community software, and educational resources",
                aliases=["Tools", "HADES", "Software", "Open Source", "Development"],
            ),
            CategoryDefinition(
                name="Clinical applications",
                group="OHDSI",
                keywords=[
                    # Clinical domains
                    "cardiovascular", "heart", "cardiac", "hypertension",
                    "stroke", "myocardial", "arrhythmia", "heart failure",
                    "cancer", "oncology", "tumor", "chemotherapy",
                    "malignancy", "neoplasm", "carcinoma", "lymphoma",
                    "infection", "covid", "coronavirus", "antimicrobial",
                    "antibiotic", "vaccine", "pandemic", "sepsis", "pneumonia",
                    "mental health", "psychiatry", "depression", "anxiety",
                    "bipolar", "schizophrenia", "psychosis", "adhd",
                    "neurology", "neurological", "alzheimer", "parkinson",
                    "dementia", "epilepsy", "multiple sclerosis", "neuropathy",
                    "diabetes", "endocrine", "thyroid", "metabolic",
                    "insulin", "glucose", "hormone", "obesity",
                    "respiratory", "pulmonary", "asthma", "copd", "lung",
                    "bronchitis",
                    "rheumatology", "arthritis", "autoimmune", "lupus",
                    "rheumatoid", "musculoskeletal", "inflammatory",
                    "pediatric", "children", "infant", "neonatal",
                    "adolescent", "childhood", "congenital",
                    "imaging", "radiology", "mri", "ct scan", "x-ray",
                    "ultrasound", "radiomics", "medical imaging",
                    # Drug safety & regulatory
                    "drug safety", "pharmacovigilance", "adverse event",
                    "adverse drug", "post-market surveillance",
                    "regulatory", "fda", "ema", "pmda",
                    # Clinical general
                    "clinical trial", "patient outcome", "rare disease",
                    "public health", "clinical application",
                ],
                description="Disease-specific studies, drug safety, pharmacovigilance, and regulatory science",
                aliases=["Clinical", "Drug Safety", "Pharmacovigilance", "Disease Studies"],
            ),
        ]

        for cat in categories:
            self.add_category(cat)

    def add_category(self, category: CategoryDefinition):
        """Add a new category to the system"""
        self.categories[category.name] = category

        # Update group mapping
        if category.group not in self.groups:
            self.groups[category.group] = []
        if category.name not in self.groups[category.group]:
            self.groups[category.group].append(category.name)

    def remove_category(self, name: str):
        """Remove a category from the system"""
        if name in self.categories:
            cat = self.categories[name]
            del self.categories[name]

            # Update group mapping
            if cat.group in self.groups:
                self.groups[cat.group].remove(name)

    def get_category(self, name: str) -> Optional[CategoryDefinition]:
        """Get a specific category by name"""
        return self.categories.get(name)

    def get_all_category_names(self) -> List[str]:
        """Get list of all category names"""
        return list(self.categories.keys())

    def get_categories_by_group(self, group: str) -> List[str]:
        """Get all category names in a specific group"""
        return self.groups.get(group, [])

    def get_all_groups(self) -> List[str]:
        """Get list of all group names"""
        return list(self.groups.keys())

    def suggest_categories(self, text: str, max_suggestions: int = 5) -> List[str]:
        """
        Suggest categories based on text content

        Args:
            text: Article title, abstract, or full text
            max_suggestions: Maximum number of suggestions to return

        Returns:
            List of suggested category names, ordered by relevance
        """
        suggestions = []
        scores = {}

        for name, category in self.categories.items():
            if category.matches(text):
                # Simple scoring: count keyword matches
                score = 0
                text_lower = text.lower()

                for keyword in category.keywords:
                    if keyword.lower() in text_lower:
                        score += text_lower.count(keyword.lower())

                if score > 0:
                    scores[name] = score

        # Sort by score and return top suggestions
        sorted_suggestions = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [name for name, _ in sorted_suggestions[:max_suggestions]]

    def export_to_json(self, file_path: Path):
        """Export categories to a JSON file for external use"""
        export_data = {
            "categories": {},
            "groups": self.groups
        }

        for name, cat in self.categories.items():
            export_data["categories"][name] = {
                "group": cat.group,
                "keywords": cat.keywords,
                "description": cat.description,
                "aliases": cat.aliases,
                "parent": cat.parent
            }

        with open(file_path, 'w') as f:
            json.dump(export_data, f, indent=2)

    def _load_from_config(self, config_file: Path):
        """Load categories from a JSON configuration file"""
        with open(config_file, 'r') as f:
            data = json.load(f)

        for name, cat_data in data.get("categories", {}).items():
            category = CategoryDefinition(
                name=name,
                group=cat_data.get("group", "Other"),
                keywords=cat_data.get("keywords", []),
                description=cat_data.get("description", ""),
                aliases=cat_data.get("aliases", []),
                parent=cat_data.get("parent")
            )
            self.add_category(category)


# Create a singleton instance for easy import
category_system = OHDSICategorySystem()

# Export commonly used functions
def get_all_categories() -> List[str]:
    """Get list of all OHDSI category names"""
    return category_system.get_all_category_names()

def get_categories_by_group(group: str) -> List[str]:
    """Get categories in a specific group"""
    return category_system.get_categories_by_group(group)

def suggest_categories(text: str, max_suggestions: int = 5) -> List[str]:
    """Suggest categories based on text"""
    return category_system.suggest_categories(text, max_suggestions)

# For backward compatibility and easy access
OHDSI_CATEGORIES = category_system.get_all_category_names()


# Mapping from old (42-category) names to new (4-category) names
OLD_TO_NEW_CATEGORY_MAP: Dict[str, str] = {
    # Core OHDSI Tools
    "OMOP CDM": "Observational data standards and management",
    "Athena Vocabulary": "Observational data standards and management",
    "WhiteRabbit": "Observational data standards and management",
    "RabbitInAHat": "Observational data standards and management",
    "Usagi": "Observational data standards and management",
    "Data Quality Dashboard": "Observational data standards and management",
    "Atlas": "Open-source analytics development",
    "HADES": "Open-source analytics development",
    "Achilles": "Open-source analytics development",
    "WebAPI": "Open-source analytics development",
    # Analytics & Methods
    "Phenotyping": "Methodological research",
    "Patient-Level Prediction": "Methodological research",
    "Population-Level Estimation": "Methodological research",
    "Characterization": "Methodological research",
    "Network Studies": "Methodological research",
    "Machine Learning": "Methodological research",
    "Natural Language Processing": "Methodological research",
    # Clinical Domains
    "Cardiovascular": "Clinical applications",
    "Oncology": "Clinical applications",
    "Infectious Disease": "Clinical applications",
    "Mental Health": "Clinical applications",
    "Neurology": "Clinical applications",
    "Endocrinology": "Clinical applications",
    "Respiratory": "Clinical applications",
    "Rheumatology": "Clinical applications",
    "Pediatrics": "Clinical applications",
    "Imaging": "Clinical applications",
    # Data Sources
    "EHR Data": "Observational data standards and management",
    "Claims Data": "Observational data standards and management",
    "Registry Data": "Observational data standards and management",
    "Imaging Data": "Observational data standards and management",
    "Genomics": "Observational data standards and management",
    "Wearables & Sensors": "Observational data standards and management",
    "Patient-Reported Outcomes": "Observational data standards and management",
    # Technical
    "ETL & Data Conversion": "Observational data standards and management",
    "Infrastructure": "Observational data standards and management",
    "Data Governance": "Observational data standards and management",
    "Interoperability": "Observational data standards and management",
    "Distributed Analytics": "Methodological research",
    # Community
    "OHDSI Studies": "Open-source analytics development",
    "Community Tools": "Open-source analytics development",
    "Education & Training": "Open-source analytics development",
    # Regulatory & Policy
    "Regulatory Science": "Clinical applications",
    "Real-World Evidence": "Methodological research",
    "Health Economics": "Methodological research",
    # Additional names from AI enhancer / frontend that may appear in data
    "Athena": "Observational data standards and management",
    "White Rabbit": "Observational data standards and management",
    "Rabbit in a Hat": "Observational data standards and management",
    "Perseus": "Open-source analytics development",
    "Circe": "Open-source analytics development",
    "Arachne": "Open-source analytics development",
    "PatientLevelPrediction": "Open-source analytics development",
    "CohortMethod": "Open-source analytics development",
    "SelfControlledCaseSeries": "Open-source analytics development",
    "EvidenceSynthesis": "Open-source analytics development",
    "CohortDiagnostics": "Open-source analytics development",
    "FeatureExtraction": "Open-source analytics development",
    "PopulationLevelEstimation": "Open-source analytics development",
    "Data Sources": "Observational data standards and management",
    "Vocabulary": "Observational data standards and management",
    "ETL": "Observational data standards and management",
    "Methods": "Methodological research",
    "Tools Development": "Open-source analytics development",
    "Drug Safety": "Clinical applications",
    "Pharmacovigilance": "Clinical applications",
    "Real World Evidence": "Methodological research",
    "Comparative Effectiveness": "Methodological research",
    "Patient Outcomes": "Clinical applications",
    "Clinical Trials": "Clinical applications",
    "Cancer Research": "Clinical applications",
    "COVID-19": "Clinical applications",
    "Rare Diseases": "Clinical applications",
    "Quality Improvement": "Clinical applications",
    "Public Health": "Clinical applications",
    "Observational Studies": "Methodological research",
    "Methods Library": "Open-source analytics development",
    # Frontend-only names
    "Data Quality": "Observational data standards and management",
    "Community": "Open-source analytics development",
    "Education": "Open-source analytics development",
    "Prediction": "Methodological research",
    "Clinical Characterization": "Methodological research",
}


def map_old_categories(old_categories: List[str]) -> List[str]:
    """Map old category names to new ones, deduplicating.

    Categories that already match new names are passed through.
    Unknown categories are dropped.
    """
    new_category_names = set(category_system.get_all_category_names())
    mapped = set()
    for cat in old_categories:
        # Already a new category name
        if cat in new_category_names:
            mapped.add(cat)
            continue
        # Try exact match in mapping
        new = OLD_TO_NEW_CATEGORY_MAP.get(cat)
        if new:
            mapped.add(new)
            continue
        # Try case-insensitive match
        for old_key, new_val in OLD_TO_NEW_CATEGORY_MAP.items():
            if cat.lower() == old_key.lower():
                mapped.add(new_val)
                break
    return sorted(mapped)
