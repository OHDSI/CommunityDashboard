"""
Documentation processor for extracting structured information from documentation pages.
"""

import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords

# Try to download NLTK data if not available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    try:
        nltk.download('punkt', quiet=True)
    except:
        pass

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    try:
        nltk.download('stopwords', quiet=True)
    except:
        pass

logger = logging.getLogger(__name__)


class DocProcessor:
    """
    Processes documentation pages to extract structured information.
    """
    
    def __init__(self):
        """Initialize documentation processor."""
        
        # OHDSI-specific concepts and tools
        self.ohdsi_concepts = {
            'data_model': [
                'omop', 'cdm', 'common data model', 'vocabulary',
                'concept', 'concept_id', 'domain', 'standard concept',
                'source value', 'concept ancestor', 'concept relationship'
            ],
            'tools': [
                'atlas', 'webapi', 'achilles', 'hades', 'whiterabbit',
                'rabbitinahat', 'usagi', 'data quality dashboard', 'dqd',
                'patient level prediction', 'plp', 'cohort method',
                'feature extraction', 'circe', 'calypso', 'heracles',
                'hermes', 'athena', 'perseus', 'argos'
            ],
            'methods': [
                'cohort', 'phenotype', 'characterization', 'estimation',
                'prediction', 'population level', 'patient level',
                'propensity score', 'matching', 'stratification',
                'standardization', 'calibration', 'validation'
            ],
            'data_sources': [
                'claims', 'ehr', 'electronic health record', 'registry',
                'administrative', 'clinical', 'observational',
                'real world data', 'rwd', 'real world evidence', 'rwe'
            ],
            'studies': [
                'protocol', 'study package', 'results', 'evidence',
                'network study', 'multi-database', 'federated',
                'distributed', 'meta-analysis'
            ]
        }
        
        # Documentation quality indicators
        self.quality_indicators = {
            'has_examples': r'example|sample|demo|snippet|usage',
            'has_installation': r'install|setup|configure|deploy|requirement',
            'has_api': r'api|endpoint|method|function|parameter|argument',
            'has_troubleshooting': r'troubleshoot|debug|error|issue|problem|solution',
            'has_tutorial': r'tutorial|guide|walkthrough|step.by.step|how.to',
            'has_reference': r'reference|specification|documentation|manual',
            'has_faq': r'faq|frequently|asked|question',
            'has_glossary': r'glossary|terminology|definition|vocabulary'
        }
        
        # Try to load stopwords
        try:
            self.stop_words = set(stopwords.words('english'))
        except:
            # Fallback to basic stopwords
            self.stop_words = set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 
                                 'on', 'at', 'to', 'for', 'of', 'with', 'by',
                                 'from', 'as', 'is', 'was', 'are', 'were'])
    
    def process_documentation(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a documentation page to extract structured information.
        
        Args:
            doc: Raw documentation data
            
        Returns:
            Processed documentation with extracted information
        """
        processed = {
            'doc_id': doc.get('doc_id'),
            'url': doc.get('url'),
            'title': doc.get('title', ''),
            'source_name': doc.get('source_name'),
            'section': doc.get('section'),
            'doc_type': doc.get('doc_type', 'reference'),
            'content_summary': self._generate_summary(doc),
            'key_concepts': self._extract_key_concepts(doc),
            'ohdsi_mentions': self._extract_ohdsi_mentions(doc),
            'code_examples': self._process_code_blocks(doc),
            'navigation': self._extract_navigation(doc),
            'metadata': self._extract_metadata(doc),
            'quality_indicators': self._assess_quality_indicators(doc),
            'search_keywords': self._generate_search_keywords(doc),
            'learning_objectives': self._extract_learning_objectives(doc),
            'prerequisites': self._extract_prerequisites(doc),
            'related_tools': self._identify_related_tools(doc),
            'version_info': self._extract_version_info(doc),
            'last_updated': doc.get('scraped_at'),
            'quality_score': self._calculate_quality_score(doc)
        }
        
        return processed
    
    def _generate_summary(self, doc: Dict[str, Any]) -> str:
        """
        Generate a summary of the documentation page.
        
        Args:
            doc: Documentation data
            
        Returns:
            Summary text
        """
        content = doc.get('content', '')
        description = doc.get('description', '')
        
        # Use description if available
        if description and len(description) > 50:
            return description
        
        # Otherwise, extract from content
        if not content:
            return ""
        
        # Try to use NLTK sentence tokenization
        try:
            sentences = sent_tokenize(content[:2000])
            # Get first 3 sentences
            summary = ' '.join(sentences[:3])
        except:
            # Fallback to simple splitting
            sentences = content[:2000].split('. ')
            summary = '. '.join(sentences[:3]) + '.'
        
        # Limit length
        if len(summary) > 500:
            summary = summary[:497] + '...'
        
        return summary
    
    def _extract_key_concepts(self, doc: Dict[str, Any]) -> List[str]:
        """
        Extract key concepts from documentation.
        
        Args:
            doc: Documentation data
            
        Returns:
            List of key concepts
        """
        concepts = []
        content = doc.get('content', '').lower()
        title = doc.get('title', '').lower()
        
        # Extract from headings
        for heading in doc.get('headings', []):
            heading_text = heading['text'].lower()
            # Skip generic headings
            if heading_text not in ['introduction', 'overview', 'summary', 'conclusion']:
                concepts.append(heading['text'])
        
        # Extract OHDSI concepts
        combined_text = f"{title} {content[:3000]}"
        
        for category, terms in self.ohdsi_concepts.items():
            for term in terms:
                if term in combined_text:
                    concepts.append(term.title())
        
        # Extract capitalized phrases (likely important terms)
        capitalized_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b'
        capitalized_matches = re.findall(capitalized_pattern, doc.get('content', '')[:3000])
        concepts.extend(capitalized_matches[:10])
        
        # Remove duplicates and limit
        seen = set()
        unique_concepts = []
        for concept in concepts:
            if concept.lower() not in seen:
                seen.add(concept.lower())
                unique_concepts.append(concept)
        
        return unique_concepts[:20]
    
    def _extract_ohdsi_mentions(self, doc: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Extract OHDSI-specific mentions from documentation.
        
        Args:
            doc: Documentation data
            
        Returns:
            Dictionary of OHDSI mentions by category
        """
        mentions = {
            'data_model': [],
            'tools': [],
            'methods': [],
            'data_sources': [],
            'studies': []
        }
        
        content_lower = doc.get('content', '').lower()
        title_lower = doc.get('title', '').lower()
        combined = f"{title_lower} {content_lower[:5000]}"
        
        for category, terms in self.ohdsi_concepts.items():
            for term in terms:
                # Use word boundaries for more accurate matching
                pattern = r'\b' + re.escape(term) + r'\b'
                if re.search(pattern, combined):
                    mentions[category].append(term)
        
        # Remove duplicates
        for category in mentions:
            mentions[category] = list(set(mentions[category]))
        
        return mentions
    
    def _process_code_blocks(self, doc: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process code blocks to extract useful information.
        
        Args:
            doc: Documentation data
            
        Returns:
            Processed code blocks
        """
        processed_blocks = []
        
        for block in doc.get('code_blocks', [])[:10]:  # Limit to 10 blocks
            processed = {
                'language': block.get('language', 'unknown'),
                'length': len(block.get('content', '')),
                'purpose': self._identify_code_purpose(block['content']),
                'has_comments': '/*' in block['content'] or '//' in block['content'] or '#' in block['content'],
                'snippet': block['content'][:500]  # First 500 chars
            }
            
            # Identify OHDSI-specific code
            if any(tool in block['content'].lower() for tool in ['atlas', 'webapi', 'achilles', 'cohort']):
                processed['is_ohdsi_specific'] = True
            
            processed_blocks.append(processed)
        
        return processed_blocks
    
    def _identify_code_purpose(self, code: str) -> str:
        """
        Identify the purpose of a code block.
        
        Args:
            code: Code content
            
        Returns:
            Purpose classification
        """
        code_lower = code.lower()
        
        if 'install' in code_lower or 'pip' in code_lower or 'npm' in code_lower:
            return 'installation'
        elif 'import' in code_lower or 'require' in code_lower or 'library(' in code_lower:
            return 'setup'
        elif 'select' in code_lower or 'from' in code_lower or 'where' in code_lower:
            return 'query'
        elif 'function' in code_lower or 'def ' in code_lower or 'class ' in code_lower:
            return 'implementation'
        elif 'config' in code_lower or 'settings' in code_lower:
            return 'configuration'
        elif 'test' in code_lower or 'assert' in code_lower:
            return 'testing'
        else:
            return 'example'
    
    def _extract_navigation(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract navigation structure from documentation.
        
        Args:
            doc: Documentation data
            
        Returns:
            Navigation information
        """
        navigation = {
            'sections': [],
            'external_links': [],
            'internal_links': [],
            'breadcrumbs': []
        }
        
        # Extract sections from headings
        headings = doc.get('headings', [])
        current_h1 = None
        current_h2 = None
        
        for heading in headings:
            level = heading['level']
            text = heading['text']
            
            if level == 1:
                current_h1 = text
                current_h2 = None
                navigation['sections'].append({
                    'title': text,
                    'level': 1,
                    'subsections': []
                })
            elif level == 2 and current_h1:
                current_h2 = text
                if navigation['sections']:
                    navigation['sections'][-1]['subsections'].append(text)
        
        # Categorize links
        base_url = doc.get('url', '')
        for link in doc.get('links', []):
            link_url = link.get('url', '')
            if link_url.startswith('http'):
                if 'ohdsi' in link_url.lower():
                    navigation['internal_links'].append(link)
                else:
                    navigation['external_links'].append(link)
        
        # Generate breadcrumbs from URL
        if base_url:
            parts = base_url.split('/')
            breadcrumbs = []
            for i, part in enumerate(parts[3:], 3):  # Skip protocol and domain
                if part and not part.startswith('?'):
                    breadcrumbs.append(part.replace('-', ' ').replace('_', ' ').title())
            navigation['breadcrumbs'] = breadcrumbs
        
        return navigation
    
    def _extract_metadata(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from documentation.
        
        Args:
            doc: Documentation data
            
        Returns:
            Metadata dictionary
        """
        metadata = {
            'word_count': doc.get('word_count', 0),
            'has_code': doc.get('has_code', False),
            'heading_count': len(doc.get('headings', [])),
            'link_count': len(doc.get('links', [])),
            'code_block_count': len(doc.get('code_blocks', [])),
            'estimated_reading_time': doc.get('word_count', 0) // 200,  # Assuming 200 words per minute
            'complexity_level': self._assess_complexity(doc),
            'target_audience': self._identify_target_audience(doc)
        }
        
        return metadata
    
    def _assess_complexity(self, doc: Dict[str, Any]) -> str:
        """
        Assess documentation complexity level.
        
        Args:
            doc: Documentation data
            
        Returns:
            Complexity level (beginner, intermediate, advanced)
        """
        content = doc.get('content', '').lower()
        
        # Check for complexity indicators
        beginner_words = ['introduction', 'basic', 'getting started', 'tutorial', 'simple']
        advanced_words = ['advanced', 'expert', 'optimization', 'architecture', 'implementation']
        
        beginner_count = sum(1 for word in beginner_words if word in content)
        advanced_count = sum(1 for word in advanced_words if word in content)
        
        # Check code complexity
        code_blocks = doc.get('code_blocks', [])
        avg_code_length = sum(len(b['content']) for b in code_blocks) / max(len(code_blocks), 1)
        
        if advanced_count > 2 or avg_code_length > 500:
            return 'advanced'
        elif beginner_count > 2 or doc.get('doc_type') == 'tutorial':
            return 'beginner'
        else:
            return 'intermediate'
    
    def _identify_target_audience(self, doc: Dict[str, Any]) -> List[str]:
        """
        Identify target audience for documentation.
        
        Args:
            doc: Documentation data
            
        Returns:
            List of target audiences
        """
        audiences = []
        content_lower = doc.get('content', '').lower()
        title_lower = doc.get('title', '').lower()
        
        # Check for audience indicators
        if any(term in content_lower for term in ['developer', 'api', 'code', 'implement']):
            audiences.append('developers')
        
        if any(term in content_lower for term in ['researcher', 'study', 'analysis', 'cohort']):
            audiences.append('researchers')
        
        if any(term in content_lower for term in ['admin', 'install', 'deploy', 'configure']):
            audiences.append('administrators')
        
        if any(term in content_lower for term in ['analyst', 'query', 'report', 'dashboard']):
            audiences.append('data analysts')
        
        if any(term in title_lower for term in ['tutorial', 'guide', 'getting started']):
            audiences.append('beginners')
        
        # Default to general if no specific audience identified
        if not audiences:
            audiences.append('general')
        
        return audiences
    
    def _assess_quality_indicators(self, doc: Dict[str, Any]) -> Dict[str, bool]:
        """
        Assess quality indicators in documentation.
        
        Args:
            doc: Documentation data
            
        Returns:
            Dictionary of quality indicators
        """
        indicators = {}
        content = doc.get('content', '').lower()
        
        for indicator, pattern in self.quality_indicators.items():
            indicators[indicator] = bool(re.search(pattern, content))
        
        return indicators
    
    def _generate_search_keywords(self, doc: Dict[str, Any]) -> List[str]:
        """
        Generate search keywords for documentation.
        
        Args:
            doc: Documentation data
            
        Returns:
            List of search keywords
        """
        keywords = []
        
        # Add from title
        title_words = doc.get('title', '').split()
        keywords.extend([w.lower() for w in title_words if len(w) > 3])
        
        # Add from key concepts
        keywords.extend([c.lower() for c in self._extract_key_concepts(doc)[:10]])
        
        # Add from OHDSI mentions
        mentions = self._extract_ohdsi_mentions(doc)
        for category_mentions in mentions.values():
            keywords.extend(category_mentions[:3])
        
        # Add doc type
        keywords.append(doc.get('doc_type', 'documentation'))
        
        # Remove duplicates and stopwords
        keywords = [k for k in keywords if k and k not in self.stop_words]
        keywords = list(set(keywords))
        
        return keywords[:30]  # Limit to 30 keywords
    
    def _extract_learning_objectives(self, doc: Dict[str, Any]) -> List[str]:
        """
        Extract learning objectives from documentation.
        
        Args:
            doc: Documentation data
            
        Returns:
            List of learning objectives
        """
        objectives = []
        content = doc.get('content', '')
        
        # Look for objective patterns
        objective_patterns = [
            r'(?:will|should|can)\s+(?:be able to|learn|understand)\s+([^.]+)',
            r'(?:objective|goal|outcome)[:\s]+([^.]+)',
            r'(?:by the end)[^,]+,\s*(?:you will|you should)\s+([^.]+)'
        ]
        
        for pattern in objective_patterns:
            matches = re.findall(pattern, content[:3000], re.IGNORECASE)
            objectives.extend(matches)
        
        # Look in headings for learning-related sections
        for heading in doc.get('headings', []):
            heading_lower = heading['text'].lower()
            if any(word in heading_lower for word in ['learn', 'objective', 'goal', 'outcome']):
                objectives.append(heading['text'])
        
        return objectives[:10]  # Limit to 10 objectives
    
    def _extract_prerequisites(self, doc: Dict[str, Any]) -> List[str]:
        """
        Extract prerequisites from documentation.
        
        Args:
            doc: Documentation data
            
        Returns:
            List of prerequisites
        """
        prerequisites = []
        content = doc.get('content', '').lower()
        
        # Look for prerequisite patterns
        prereq_patterns = [
            r'prerequisite[s]?[:\s]+([^.]+)',
            r'require[s]?[:\s]+([^.]+)',
            r'before\s+(?:you\s+)?(?:begin|start)[^,]+,\s+([^.]+)',
            r'assumes?\s+(?:you\s+)?(?:have|know)\s+([^.]+)'
        ]
        
        for pattern in prereq_patterns:
            matches = re.findall(pattern, content[:2000])
            prerequisites.extend(matches)
        
        # Clean up prerequisites
        cleaned = []
        for prereq in prerequisites:
            # Remove common prefixes
            prereq = re.sub(r'^(you\s+)?(should\s+)?(must\s+)?(need\s+to\s+)?', '', prereq)
            if len(prereq) > 10 and len(prereq) < 200:
                cleaned.append(prereq.strip())
        
        return cleaned[:10]  # Limit to 10 prerequisites
    
    def _identify_related_tools(self, doc: Dict[str, Any]) -> List[str]:
        """
        Identify related OHDSI tools mentioned in documentation.
        
        Args:
            doc: Documentation data
            
        Returns:
            List of related tools
        """
        tools = []
        content = doc.get('content', '').lower()
        
        # Check for each OHDSI tool
        for tool in self.ohdsi_concepts['tools']:
            if tool in content:
                # Check context to ensure it's actually about the tool
                pattern = r'\b' + re.escape(tool) + r'\b'
                if re.search(pattern, content):
                    tools.append(tool.title() if len(tool) > 3 else tool.upper())
        
        return list(set(tools))[:15]  # Unique tools, limit to 15
    
    def _extract_version_info(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract version information from documentation.
        
        Args:
            doc: Documentation data
            
        Returns:
            Version information
        """
        version_info = {
            'version': None,
            'last_updated': None,
            'compatibility': []
        }
        
        content = doc.get('content', '')
        
        # Look for version patterns
        version_patterns = [
            r'version[:\s]+(\d+(?:\.\d+)*)',
            r'v(\d+(?:\.\d+)+)',
            r'release[:\s]+(\d+(?:\.\d+)*)'
        ]
        
        for pattern in version_patterns:
            match = re.search(pattern, content[:1000], re.IGNORECASE)
            if match:
                version_info['version'] = match.group(1)
                break
        
        # Look for date patterns
        date_patterns = [
            r'(?:last\s+)?updated?[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
            r'(?:modified|revised)[:\s]+(\d{4}-\d{2}-\d{2})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, content[:1000], re.IGNORECASE)
            if match:
                version_info['last_updated'] = match.group(1)
                break
        
        # Look for compatibility information
        compat_patterns = [
            r'compatible\s+with\s+([^.,]+)',
            r'requires?\s+([^.,]+(?:version|v)\s*\d+(?:\.\d+)*)',
            r'supports?\s+([^.,]+(?:version|v)\s*\d+(?:\.\d+)*)'
        ]
        
        for pattern in compat_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            version_info['compatibility'].extend(matches[:5])
        
        return version_info
    
    def _calculate_quality_score(self, doc: Dict[str, Any]) -> float:
        """
        Calculate overall quality score for documentation.
        
        Args:
            doc: Documentation data
            
        Returns:
            Quality score (0-1)
        """
        score = 0.0
        
        # Content completeness (30%)
        if doc.get('word_count', 0) > 1000:
            score += 0.15
        elif doc.get('word_count', 0) > 500:
            score += 0.08
        
        if doc.get('description'):
            score += 0.05
        
        if len(doc.get('headings', [])) > 3:
            score += 0.1
        
        # Code examples (20%)
        if doc.get('has_code'):
            score += 0.1
            if len(doc.get('code_blocks', [])) > 2:
                score += 0.1
        
        # Quality indicators (20%)
        indicators = self._assess_quality_indicators(doc)
        indicator_score = sum(1 for v in indicators.values() if v) / len(indicators)
        score += indicator_score * 0.2
        
        # OHDSI relevance (15%)
        if doc.get('is_ohdsi'):
            score += 0.1
        
        mentions = self._extract_ohdsi_mentions(doc)
        if any(mentions.values()):
            score += 0.05
        
        # Documentation type (15%)
        valuable_types = ['tutorial', 'installation', 'example', 'api']
        if doc.get('doc_type') in valuable_types:
            score += 0.15
        elif doc.get('doc_type') == 'reference':
            score += 0.08
        
        return min(1.0, score)
    
    def extract_summary(self, doc: Dict[str, Any], max_length: int = 300) -> str:
        """
        Extract a concise summary of the documentation.
        
        Args:
            doc: Documentation data
            max_length: Maximum summary length
            
        Returns:
            Summary text
        """
        parts = []
        
        # Add title
        title = doc.get('title', 'Documentation')
        parts.append(f"Documentation: {title}")
        
        # Add type and source
        doc_type = doc.get('doc_type', 'reference').title()
        source = doc.get('source_name', 'Unknown')
        parts.append(f"Type: {doc_type} | Source: {source}")
        
        # Add key information
        mentions = self._extract_ohdsi_mentions(doc)
        if mentions.get('tools'):
            parts.append(f"Tools: {', '.join(mentions['tools'][:3])}")
        
        # Add summary or description
        summary = self._generate_summary(doc)
        if summary:
            parts.append(summary[:150])
        
        result = ' | '.join(parts)
        if len(result) > max_length:
            result = result[:max_length-3] + '...'
        
        return result