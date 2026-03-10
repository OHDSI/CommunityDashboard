"""
OpenAI Enhancement Processor for Multi-Source Content Pipeline.
Provides multi-stage AI enrichment for all content types.
"""

import os
import json
import logging
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import time
from functools import lru_cache

import openai
from openai import OpenAI
import redis
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class AIEnhancer:
    """
    Multi-stage AI enhancement processor using OpenAI GPT-4o-mini.
    Provides classification, summarization, concept extraction, and relationship discovery.
    """
    
    def __init__(
        self,
        openai_api_key: str = None,
        redis_client: redis.Redis = None,
        model: str = "gpt-4o-mini",
        cache_ttl: int = 604800  # 7 days
    ):
        """
        Initialize AI enhancer.
        
        Args:
            openai_api_key: OpenAI API key
            redis_client: Redis client for caching
            model: OpenAI model to use
            cache_ttl: Cache time-to-live in seconds
        """
        self.api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        self.redis_client = redis_client
        self.model = model
        self.cache_ttl = cache_ttl
        
        # Initialize OpenAI client
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
            logger.info(f"OpenAI client initialized with model {model}")
        else:
            self.client = None
            logger.warning("No OpenAI API key provided. AI enhancement disabled.")
        
        # Initialize sentence transformer for embeddings
        try:
            self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Sentence transformer initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize sentence transformer: {e}")
            self.encoder = None
        
        # Statistics
        self.stats = {
            'processed': 0,
            'cached': 0,
            'errors': 0,
            'api_calls': 0
        }
    
    def enhance_content(
        self,
        content: Dict[str, Any],
        content_type: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Main enhancement pipeline for content.
        
        Args:
            content: Normalized content dictionary
            content_type: Type of content (article, video, repository, discussion, documentation)
            use_cache: Whether to use cached results
            
        Returns:
            Enhanced content with AI-generated fields
        """
        if not self.client:
            logger.warning("OpenAI client not initialized, returning original content")
            return content
        
        # Generate cache key
        cache_key = self._generate_cache_key(content)
        
        # Check cache
        if use_cache and self.redis_client:
            cached = self._get_cached_enhancement(cache_key)
            if cached:
                self.stats['cached'] += 1
                content.update(cached)
                return content
        
        try:
            # Multi-stage enhancement
            enhancements = {}
            
            # Stage 1: Classification and categorization
            classification = self._classify_content(content, content_type)
            enhancements.update(classification)
            
            # Stage 2: Summarization
            summaries = self._generate_summaries(content, content_type)
            enhancements.update(summaries)
            
            # Stage 3: Concept extraction
            concepts = self._extract_concepts(content, content_type)
            enhancements.update(concepts)
            
            # Stage 4: Quality assessment
            quality = self._assess_quality(content, content_type)
            enhancements.update(quality)
            
            # Stage 5: Generate embeddings
            if self.encoder:
                embeddings = self._generate_embeddings(content, enhancements)
                enhancements['embeddings'] = embeddings
            
            # Add metadata
            enhancements['ai_processing_date'] = datetime.utcnow().isoformat()
            enhancements['ai_model'] = self.model
            
            # Cache the enhancements
            if self.redis_client:
                self._cache_enhancement(cache_key, enhancements)
            
            # Update content with enhancements
            content['ai_enrichment'] = enhancements
            
            self.stats['processed'] += 1
            return content
            
        except Exception as e:
            logger.error(f"Error enhancing content: {e}")
            self.stats['errors'] += 1
            return content
    
    def _classify_content(
        self,
        content: Dict[str, Any],
        content_type: str
    ) -> Dict[str, Any]:
        """
        Classify content for OHDSI relevance and categories.
        """
        prompt = self._get_classification_prompt(content, content_type)
        
        try:
            response = self._call_openai(
                system_prompt=prompt['system'],
                user_prompt=prompt['user'],
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response)
            
            return {
                'is_ohdsi_related': result.get('is_ohdsi_related', False),
                'confidence_score': result.get('confidence', 0.0),
                'categories': result.get('categories', []),  # v3: use 'categories' not 'predicted_categories'
                'classification_reasoning': result.get('reasoning', '')
            }
            
        except Exception as e:
            logger.error(f"Classification error: {e}")
            return {}
    
    def _generate_summaries(
        self,
        content: Dict[str, Any],
        content_type: str
    ) -> Dict[str, Any]:
        """
        Generate various types of summaries.
        """
        prompt = self._get_summary_prompt(content, content_type)
        
        try:
            response = self._call_openai(
                system_prompt=prompt['system'],
                user_prompt=prompt['user'],
                temperature=0.5,
                max_tokens=800,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response)
            
            return {
                'summary': result.get('executive_summary', ''),
                'tldr': result.get('tldr', ''),
                'key_takeaways': result.get('key_takeaways', []),
                'learning_objectives': result.get('learning_objectives', [])
            }
            
        except Exception as e:
            logger.error(f"Summarization error: {e}")
            return {}
    
    def _extract_concepts(
        self,
        content: Dict[str, Any],
        content_type: str
    ) -> Dict[str, Any]:
        """
        Extract key concepts, tools, and entities.
        """
        prompt = self._get_concept_extraction_prompt(content, content_type)
        
        try:
            response = self._call_openai(
                system_prompt=prompt['system'],
                user_prompt=prompt['user'],
                temperature=0.3,
                max_tokens=600,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response)
            
            return {
                'key_concepts': result.get('key_concepts', []),
                'ohdsi_tools_mentioned': result.get('ohdsi_tools', []),
                'medical_terms': result.get('medical_terms', []),
                'technologies': result.get('technologies', []),
                'prerequisites': result.get('prerequisites', []),
                'related_topics': result.get('related_topics', [])
            }
            
        except Exception as e:
            logger.error(f"Concept extraction error: {e}")
            return {}
    
    def _assess_quality(
        self,
        content: Dict[str, Any],
        content_type: str
    ) -> Dict[str, Any]:
        """
        Assess content quality and difficulty.
        """
        prompt = self._get_quality_assessment_prompt(content, content_type)
        
        try:
            response = self._call_openai(
                system_prompt=prompt['system'],
                user_prompt=prompt['user'],
                temperature=0.3,
                max_tokens=400,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response)
            
            return {
                'quality_assessment': result.get('assessment', ''),
                'completeness_score': result.get('completeness', 0.0),
                'technical_accuracy_score': result.get('accuracy', 0.0),
                'relevance_score': result.get('relevance', 0.0),
                'difficulty_score': result.get('difficulty', 0.5),
                'difficulty_level': result.get('difficulty_level', 'intermediate'),
                'target_audience': result.get('target_audience', []),
                'content_freshness': result.get('freshness', 'current')
            }
            
        except Exception as e:
            logger.error(f"Quality assessment error: {e}")
            return {}
    
    def _generate_embeddings(
        self,
        content: Dict[str, Any],
        enhancements: Dict[str, Any]
    ) -> Dict[str, List[float]]:
        """
        Generate semantic embeddings for search.
        """
        if not self.encoder:
            return {}
        
        try:
            embeddings = {}
            
            # Title embedding
            if content.get('title'):
                embeddings['title_embedding'] = self.encoder.encode(
                    content['title'],
                    normalize_embeddings=True
                ).tolist()
            
            # Content embedding (first 2000 chars)
            if content.get('content'):
                embeddings['content_embedding'] = self.encoder.encode(
                    content['content'][:2000],
                    normalize_embeddings=True
                ).tolist()
            
            # Summary embedding
            if enhancements.get('summary'):
                embeddings['summary_embedding'] = self.encoder.encode(
                    enhancements['summary'],
                    normalize_embeddings=True
                ).tolist()
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            return {}
    
    def discover_relationships(
        self,
        content: Dict[str, Any],
        existing_content: List[Dict[str, Any]],
        max_relationships: int = 10
    ) -> Dict[str, List[str]]:
        """
        Discover relationships with existing content.
        """
        relationships = {
            'related_content': [],
            'citations': [],
            'cited_by': [],
            'implements': [],
            'discusses': [],
            'documents': []
        }
        
        if not existing_content:
            return relationships
        
        # Get the current content's ID to exclude self-references
        current_id = content.get('id') or content.get('pmid') or content.get('fingerprint')
        
        try:
            # Use existing citation data if available
            if content.get('citations'):
                citations = content['citations']
                # Store citation PMIDs directly
                relationships['citations'] = citations.get('references', [])
                relationships['cited_by'] = citations.get('cited_by', [])
                # Use similar articles for related content
                similar = citations.get('similar', [])
                if similar:
                    relationships['related_content'].extend(similar[:5])
            
            # Use embeddings for similarity if available
            if self.encoder and content.get('ai_enrichment', {}).get('embeddings'):
                content_embedding = content['ai_enrichment']['embeddings'].get('content_embedding')
                if content_embedding:
                    similarities = []
                    for existing in existing_content:
                        existing_id = existing.get('id')
                        # Skip self-reference
                        if existing_id and str(existing_id) == str(current_id):
                            continue
                        
                        existing_embedding = existing.get('ai_enrichment', {}).get('embeddings', {}).get('content_embedding')
                        if existing_embedding:
                            similarity = np.dot(content_embedding, existing_embedding)
                            similarities.append((existing_id, similarity))
                    
                    # Get top similar content (excluding those already in citations)
                    similarities.sort(key=lambda x: x[1], reverse=True)
                    existing_related = set(relationships['related_content'])
                    for sid, score in similarities[:max_relationships]:
                        if sid not in existing_related and score > 0.7:  # Similarity threshold
                            relationships['related_content'].append(sid)
            
            # Ensure no self-references
            for key in relationships:
                if isinstance(relationships[key], list):
                    relationships[key] = [
                        item for item in relationships[key] 
                        if str(item) != str(current_id)
                    ]
            
            # Extract additional references
            additional_refs = self._extract_references(content, existing_content)
            for key in additional_refs:
                if key in relationships and additional_refs[key]:
                    # Merge without duplicates
                    existing_items = set(relationships[key])
                    for item in additional_refs[key]:
                        if item not in existing_items and str(item) != str(current_id):
                            relationships[key].append(item)
            
            return relationships
            
        except Exception as e:
            logger.error(f"Relationship discovery error: {e}")
            return relationships
    
    def _extract_references(
        self,
        content: Dict[str, Any],
        existing_content: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """
        Extract citation and reference relationships.
        """
        references = {
            'citations': [],
            'implements': [],
            'discusses': []
        }
        
        # Extract PMIDs, DOIs, URLs from content
        text = f"{content.get('title', '')} {content.get('abstract', '')} {content.get('content', '')}"
        
        # Simple pattern matching for references
        import re
        
        # Find PMIDs
        pmids = re.findall(r'PMID:?\s*(\d+)', text, re.IGNORECASE)
        references['citations'].extend(pmids)
        
        # Find DOIs
        dois = re.findall(r'10\.\d{4,}(?:\.\d+)*\/[-._;()\/:a-zA-Z0-9]+', text)
        references['citations'].extend(dois)
        
        # Check if this is implementation of a paper
        if content.get('content_type') == 'repository':
            for existing in existing_content:
                if existing.get('content_type') == 'article':
                    # Check if repo implements the paper
                    if existing.get('title', '').lower() in text.lower():
                        references['implements'].append(existing['id'])
        
        # Check if this discusses other content
        if content.get('content_type') == 'discussion':
            for existing in existing_content:
                if existing.get('url') and existing['url'] in text:
                    references['discusses'].append(existing['id'])
        
        return references
    
    def _call_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 500,
        response_format: Dict = None
    ) -> str:
        """
        Make API call to OpenAI with retry logic.
        """
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                
                kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                
                if response_format:
                    kwargs["response_format"] = response_format
                
                response = self.client.chat.completions.create(**kwargs)
                self.stats['api_calls'] += 1
                
                return response.choices[0].message.content
                
            except openai.RateLimitError:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
                raise
            except Exception as e:
                logger.error(f"OpenAI API error: {e}")
                raise
        
        raise Exception("Max retries exceeded for OpenAI API call")
    
    def _get_classification_prompt(
        self,
        content: Dict[str, Any],
        content_type: str
    ) -> Dict[str, str]:
        """
        Get content-type specific classification prompt.
        """
        # OHDSI categories (4 high-level pillars)
        categories_with_descriptions = """- Observational data standards and management: OMOP CDM, vocabularies (Athena, SNOMED, ICD, LOINC), ETL tools (WhiteRabbit, RabbitInAHat, Usagi), data quality (DQD, Achilles), data governance, interoperability (FHIR, HL7), infrastructure, and data sources (EHR, claims, registry, genomics, wearables, PROs)
- Methodological research: Statistical methods, phenotyping, patient-level prediction (PLP), population-level estimation (PLE), characterization, network studies, machine learning, NLP, distributed analytics, real-world evidence (RWE), health economics, causal inference, and study design
- Open-source analytics development: OHDSI open-source tools (Atlas, HADES, WebAPI), R packages (CohortMethod, PatientLevelPrediction, CohortDiagnostics, FeatureExtraction, EvidenceSynthesis), community tools, software development, OHDSI studies, study packages, and education/training resources
- Clinical applications: Disease-specific studies (cardiovascular, oncology, infectious disease, mental health, neurology, endocrinology, respiratory, rheumatology, pediatrics, imaging), drug safety, pharmacovigilance, regulatory science (FDA, EMA), clinical trials, and public health applications"""

        base_system = f"""You are an expert in OHDSI (Observational Health Data Sciences and Informatics) content classification.

Classify the given {content_type} and return a JSON response with:
{{
  "is_ohdsi_related": boolean,
  "confidence": float (0.0 to 1.0),
  "categories": [list of 1-2 most relevant categories from the provided list],
  "reasoning": "Brief explanation"
}}

Available categories (select 1-2 that best fit):
{categories_with_descriptions}

Consider OHDSI-related if it involves:
- OHDSI tools, methods, or standards
- Observational health research using OMOP CDM
- Network studies or real-world evidence
- Contributors to OHDSI community"""
        
        # Content-type specific adjustments
        if content_type == 'video':
            text = f"""Title: {content.get('title', '')}
Description: {content.get('description', '')}
Channel: {content.get('video_metadata', {}).get('channel_name', '')}
Transcript: {content.get('video_metadata', {}).get('transcript', '')[:1000]}"""
        
        elif content_type == 'repository':
            text = f"""Name: {content.get('title', '')}
Description: {content.get('description', '')}
Owner: {content.get('repository_metadata', {}).get('owner', '')}
README: {content.get('repository_metadata', {}).get('readme_content', '')[:1000]}
Topics: {', '.join(str(x) for x in content.get('repository_metadata', {}).get('topics', []))}"""
        
        elif content_type == 'discussion':
            text = f"""Title: {content.get('title', '')}
Category: {content.get('discussion_metadata', {}).get('category', '')}
Content: {content.get('content', '')[:1000]}
Tags: {', '.join(str(x) for x in content.get('discussion_metadata', {}).get('tags', []))}"""
        
        elif content_type == 'documentation':
            text = f"""Title: {content.get('title', '')}
Source: {content.get('documentation_metadata', {}).get('doc_source', '')}
Content: {content.get('content', '')[:1000]}
Type: {content.get('documentation_metadata', {}).get('doc_type', '')}"""
        
        else:  # article
            text = f"""Title: {content.get('title', '')}
Abstract: {content.get('abstract', '')}
Keywords: {', '.join(str(x) for x in content.get('keywords', []))}
Journal: {content.get('journal', '')}"""
        
        return {
            'system': base_system,
            'user': f"Classify this {content_type}:\n\n{text}"
        }
    
    def _get_summary_prompt(
        self,
        content: Dict[str, Any],
        content_type: str
    ) -> Dict[str, str]:
        """
        Get content-type specific summary prompt.
        """
        system_prompt = f"""You are an expert at summarizing OHDSI-related {content_type} content.

Generate a JSON response with:
{{
  "executive_summary": "150-300 word comprehensive summary",
  "tldr": "One-line summary (max 100 chars)",
  "key_takeaways": ["list", "of", "3-5", "bullet points"],
  "learning_objectives": ["what", "readers", "will", "learn"] // if educational
}}

Focus on:
- Main contributions or findings
- OHDSI tools and methods used
- Practical applications
- Key insights for the OHDSI community"""
        
        # Select appropriate content for summarization
        if content_type == 'video' and content.get('video_metadata', {}).get('transcript'):
            text = content['video_metadata']['transcript'][:3000]
        elif content_type == 'repository' and content.get('repository_metadata', {}).get('readme_content'):
            text = content['repository_metadata']['readme_content'][:3000]
        else:
            text = content.get('content', content.get('abstract', ''))[:3000]
        
        user_prompt = f"""Summarize this {content_type}:

Title: {content.get('title', '')}
Content: {text}"""
        
        return {
            'system': system_prompt,
            'user': user_prompt
        }
    
    def _get_concept_extraction_prompt(
        self,
        content: Dict[str, Any],
        content_type: str
    ) -> Dict[str, str]:
        """
        Get concept extraction prompt.
        """
        system_prompt = f"""You are an expert at extracting concepts from OHDSI-related content.

Extract and return a JSON response with:
{{
  "key_concepts": ["main", "concepts", "discussed"],
  "ohdsi_tools": ["Atlas", "HADES", "etc"],  // OHDSI-specific tools mentioned
  "medical_terms": ["clinical", "terms"],
  "technologies": ["R", "Python", "SQL", "etc"],
  "prerequisites": ["required", "knowledge"],
  "related_topics": ["related", "research", "areas"]
}}

Focus on identifying:
- OHDSI ecosystem tools
- Clinical and research concepts
- Technical requirements
- Learning prerequisites"""
        
        # Use appropriate content
        text = content.get('content', content.get('abstract', ''))[:2000]
        
        return {
            'system': system_prompt,
            'user': f"Extract concepts from this {content_type}:\n\nTitle: {content.get('title', '')}\nContent: {text}"
        }
    
    def _get_quality_assessment_prompt(
        self,
        content: Dict[str, Any],
        content_type: str
    ) -> Dict[str, str]:
        """
        Get quality assessment prompt.
        """
        system_prompt = f"""You are an expert at assessing the quality of OHDSI-related content.

Assess this {content_type} and return a JSON response with:
{{
  "assessment": "Brief quality assessment",
  "completeness": 0.0-1.0,  // How complete is the content
  "accuracy": 0.0-1.0,  // Technical accuracy
  "relevance": 0.0-1.0,  // Relevance to OHDSI community
  "difficulty": 0.0-1.0,  // 0=beginner, 0.5=intermediate, 1=advanced
  "difficulty_level": "beginner|intermediate|advanced",
  "target_audience": ["researchers", "developers", "analysts"],
  "freshness": "current|dated|timeless"  // Content freshness
}}

Consider:
- Completeness of information
- Technical accuracy
- Clarity and organization
- Value to OHDSI community
- Currency of information"""
        
        # Assessment context
        metadata = {
            'published_date': content.get('published_date', ''),
            'source': content.get('source', ''),
            'engagement': content.get('metrics', {})
        }
        
        text = content.get('content', content.get('abstract', ''))[:1500]
        
        return {
            'system': system_prompt,
            'user': f"Assess this {content_type}:\n\nTitle: {content.get('title', '')}\nMetadata: {json.dumps(metadata)}\nContent: {text}"
        }
    
    def _generate_cache_key(self, content: Dict[str, Any]) -> str:
        """
        Generate cache key for content.
        """
        # Use content ID and fingerprint if available
        key_parts = [
            content.get('id', ''),
            content.get('fingerprint', ''),
            content.get('title', ''),
            self.model
        ]
        key_string = '|'.join(filter(None, key_parts))
        return f"ai_enhancement:{hashlib.md5(key_string.encode()).hexdigest()}"
    
    def _get_cached_enhancement(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached enhancement from Redis.
        """
        if not self.redis_client:
            return None
        
        try:
            cached = self.redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
        
        return None
    
    def _cache_enhancement(self, cache_key: str, enhancement: Dict[str, Any]):
        """
        Cache enhancement in Redis.
        """
        if not self.redis_client:
            return
        
        try:
            self.redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(enhancement)
            )
        except Exception as e:
            logger.error(f"Cache storage error: {e}")
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get processing statistics.
        """
        return self.stats.copy()
    
    def batch_enhance(
        self,
        content_items: List[Dict[str, Any]],
        batch_size: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Enhance multiple content items in batches.
        
        Args:
            content_items: List of content items to enhance
            batch_size: Number of items to process in parallel
            
        Returns:
            List of enhanced content items
        """
        enhanced_items = []
        
        for i in range(0, len(content_items), batch_size):
            batch = content_items[i:i + batch_size]
            
            # Process batch
            for item in batch:
                content_type = item.get('content_type', 'article')
                enhanced = self.enhance_content(item, content_type)
                enhanced_items.append(enhanced)
            
            # Brief delay to avoid rate limits
            if i + batch_size < len(content_items):
                time.sleep(1)
        
        return enhanced_items