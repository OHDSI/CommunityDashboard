import {
  Database,
  Brain,
  Code,
  Stethoscope,
  type LucideIcon
} from 'lucide-react'

/**
 * Comprehensive OHDSI category definition with icons, colors, and metadata.
 * Used in explorer, search, review, and filter components.
 */
export interface OHDSICategory {
  name: string
  icon: LucideIcon
  description: string
  color: string
  bgColor: string
  borderColor: string
  keywords: string[]
}

/**
 * Full OHDSI category definitions with icons, descriptions, and styling.
 * This is the canonical source for all category metadata in the application.
 */
export const OHDSI_CATEGORIES: OHDSICategory[] = [
  {
    name: 'Observational data standards and management',
    icon: Database,
    description: 'OMOP CDM, vocabularies, ETL, data quality, data governance, and data source integration',
    color: 'text-blue-600',
    bgColor: 'from-blue-100/50 to-blue-50/30',
    borderColor: 'border-l-blue-500',
    keywords: ['omop', 'cdm', 'vocabulary', 'etl', 'data quality', 'standards', 'data model', 'data governance', 'ehr', 'claims']
  },
  {
    name: 'Methodological research',
    icon: Brain,
    description: 'Statistical methods, prediction, estimation, phenotyping, network studies, and evidence generation',
    color: 'text-purple-600',
    bgColor: 'from-purple-100/50 to-purple-50/30',
    borderColor: 'border-l-purple-500',
    keywords: ['methods', 'prediction', 'estimation', 'phenotyping', 'characterization', 'network studies', 'real-world evidence', 'machine learning']
  },
  {
    name: 'Open-source analytics development',
    icon: Code,
    description: 'OHDSI open-source tools, HADES R packages, Atlas, community software, and educational resources',
    color: 'text-green-600',
    bgColor: 'from-green-100/50 to-green-50/30',
    borderColor: 'border-l-green-500',
    keywords: ['open source', 'tools', 'software', 'hades', 'atlas', 'r package', 'github', 'development', 'community']
  },
  {
    name: 'Clinical applications',
    icon: Stethoscope,
    description: 'Disease-specific studies, drug safety, pharmacovigilance, and regulatory science',
    color: 'text-red-600',
    bgColor: 'from-red-100/50 to-red-50/30',
    borderColor: 'border-l-red-500',
    keywords: ['clinical', 'drug safety', 'disease', 'pharmacovigilance', 'regulatory', 'oncology', 'cardiovascular', 'mental health']
  }
]

/**
 * Flat list of category names for use in selects, filters, and badges.
 */
export const CATEGORY_NAMES: string[] = OHDSI_CATEGORIES.map(c => c.name)

/**
 * Default fallback category list for the review page when the API is unavailable.
 */
export const REVIEW_FALLBACK_CATEGORIES: string[] = [
  'Observational data standards and management',
  'Methodological research',
  'Open-source analytics development',
  'Clinical applications'
]
