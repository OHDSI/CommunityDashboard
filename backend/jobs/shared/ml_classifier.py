"""
Unified ML classifier for all content types.
Extends the existing ArticleClassifier to handle multiple content types.
"""

import logging
import os
import sys
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import numpy as np
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, "/app/jobs")

# Import the existing classifier
try:
    from article_classifier.advanced_classifier import AdvancedOHDSIClassifier
    USE_ADVANCED = True
except ImportError:
    from article_classifier.enhanced_classifier_v2 import EnhancedOHDSIClassifierV2
    USE_ADVANCED = False

logger = logging.getLogger(__name__)


class UnifiedMLClassifier:
    """
    Unified classifier that adapts the ArticleClassifier for multiple content types.
    """
    
    # Content type weights for scoring (adjusted to be more inclusive)
    CONTENT_TYPE_WEIGHTS = {
        'article': 1.0,      # Articles are baseline
        'video': 1.0,        # Videos equally important (many OHDSI tutorials)
        'repository': 1.0,    # Code repos equally important (OHDSI tools)
        'discussion': 0.9,    # Discussions slightly lower (but still valuable)
        'documentation': 1.2  # Official docs higher confidence
    }
    
    # Quality thresholds per content type (more lenient for initial ingestion)
    QUALITY_THRESHOLDS = {
        'article': {'min_length': 0, 'min_authors': 0},  # No abstract requirement - rely on ML classification
        'video': {'min_duration': 30, 'min_views': 0},  # Allow new videos with 0 views
        'repository': {'min_stars': 0, 'min_readme_length': 10},  # Minimal README requirement
        'discussion': {'min_answers': 0, 'min_length': 20},  # Allow unanswered questions
        'documentation': {'min_length': 50}  # Reduced from 100
    }
    
    def __init__(self, 
                 model_dir: str = None,
                 use_gpt: bool = True,
                 gpt_model: str = "gpt-4o-mini"):
        """
        Initialize the unified classifier.
        
        Args:
            model_dir: Directory containing trained models
            use_gpt: Whether to use GPT for enhanced classification
            gpt_model: GPT model to use
        """
        # Initialize the base ArticleClassifier
        if USE_ADVANCED:
            self.base_classifier = AdvancedOHDSIClassifier(
                model_dir=model_dir,
                model_type="xgboost"
            )
            logger.info("Using Advanced OHDSI Classifier")
        else:
            self.base_classifier = EnhancedOHDSIClassifierV2(
                model_dir=model_dir,
                model_type="randomforest"  # Use randomforest to match our retrained model
            )
            logger.info("Using Enhanced OHDSI Classifier V2")
        
        # Load the trained model
        try:
            self.base_classifier.load_model()
            logger.info("Loaded trained RandomForest model")
        except Exception as e:
            logger.warning(f"Could not load model, will use defaults: {e}")
        
        self.use_gpt = use_gpt
        self.gpt_model = gpt_model
        
        # Track statistics
        self.stats = {
            'total_classified': 0,
            'by_type': {},
            'auto_approved': 0,
            'pending_review': 0
        }
    
    def classify(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify content regardless of type.
        
        Args:
            content: Normalized content dictionary
            
        Returns:
            Classification results with scores and categories
        """
        content_type = content.get('content_type', 'article')
        
        # Check quality thresholds
        if not self._meets_quality_threshold(content, content_type):
            logger.warning(f"Content does not meet quality threshold: {content.get('title', 'Unknown')}")
            return {
                'ml_probability': 0.0,
                'gpt_probability': 0.0,
                'combined_probability': 0.0,
                'final_score': 0.0,  # v3: add final_score
                'ai_confidence': 0.0,  # v3: add ai_confidence
                'quality_score': 0.0,  # Quality score for transparency
                'categories': [],  # v3: use 'categories'
                'gpt_reasoning': 'Content does not meet minimum quality thresholds',
                'is_ohdsi_related': False
            }
        
        # Prepare content for classification
        prepared_content = self._prepare_content(content, content_type)
        
        # Get base classification from ArticleClassifier
        try:
            result = self.base_classifier.predict_from_article(prepared_content)
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            result = {
                'ml_probability': 0.5,
                'gpt_probability': 0.5,
                'combined_probability': 0.5,
                'final_score': 0.5,  # v3: add final_score
                'ai_confidence': 0.5,  # v3: add ai_confidence
                'quality_score': 0.5,  # Quality score for transparency
                'categories': [],  # v3: use 'categories'
                'gpt_reasoning': f'Classification error: {str(e)}',
                'is_ohdsi_related': False
            }
        
        # Apply content type adjustments
        adjusted_result = self._adjust_for_content_type(result, content, content_type)
        
        # Apply quality scoring
        quality_score = self._calculate_quality_score(content, content_type)

        # Calculate final_score for v3 schema
        final_score = self._calculate_final_score(
            adjusted_result['combined_probability'],
            quality_score,
            content_type
        )
        adjusted_result['final_score'] = final_score  # v3: use final_score
        adjusted_result['quality_score'] = quality_score  # Store for transparency
        
        # Map for v3 compatibility
        adjusted_result['ai_confidence'] = adjusted_result.get('gpt_probability', 0)  # v3: map to ai_confidence
        if 'predicted_categories' in adjusted_result:
            adjusted_result['categories'] = adjusted_result.pop('predicted_categories')  # v3: rename to categories
        adjusted_result['is_ohdsi_related'] = final_score >= 0.7
        
        # Update statistics
        self.stats['total_classified'] += 1
        self.stats['by_type'][content_type] = self.stats['by_type'].get(content_type, 0) + 1
        if final_score >= 0.7:
            self.stats['auto_approved'] += 1
        else:
            self.stats['pending_review'] += 1
        
        return adjusted_result
    
    def _meets_quality_threshold(self, content: Dict[str, Any], content_type: str) -> bool:
        """Check if content meets minimum quality thresholds."""
        thresholds = self.QUALITY_THRESHOLDS.get(content_type, {})
        
        if content_type == 'article':
            abstract = content.get('abstract', '')
            if len(abstract) < thresholds.get('min_length', 0):
                return False
            if len(content.get('authors', [])) < thresholds.get('min_authors', 0):
                return False
        
        elif content_type == 'video':
            if content.get('media_duration', 0) < thresholds.get('min_duration', 0):
                return False
            if content.get('view_count', 0) < thresholds.get('min_views', 0):
                return False
        
        elif content_type == 'repository':
            readme = content.get('content', '')
            if len(readme) < thresholds.get('min_readme_length', 0):
                return False
        
        elif content_type == 'discussion':
            if content.get('answer_count', 0) < thresholds.get('min_answers', 0):
                return False
        
        elif content_type == 'documentation':
            doc_content = content.get('content', '')
            if len(doc_content) < thresholds.get('min_length', 0):
                return False
        
        return True
    
    def _prepare_content(self, content: Dict[str, Any], content_type: str) -> Dict[str, Any]:
        """
        Prepare content for the ArticleClassifier.
        Adapts different content types to article-like format.
        """
        prepared = {}
        
        # Common fields - ensure we have basic content
        prepared['title'] = content.get('title', 'Untitled Content')
        prepared['pmid'] = content.get('source_id', content.get('id', ''))
        prepared['doi'] = content.get('doi', '')
        prepared['url'] = content.get('url', '')
        prepared['year'] = content.get('year', datetime.now().year)
        prepared['published_date'] = content.get('published_date')
        prepared['keywords'] = content.get('keywords', [])
        prepared['mesh_terms'] = content.get('mesh_terms', [])
        
        # Ensure abstract field exists (required by classifier)
        prepared['abstract'] = ''  # Will be filled based on content type
        
        # Handle authors
        authors = content.get('authors', [])
        if authors:
            prepared['authors'] = authors
        else:
            # Create placeholder author based on source
            prepared['authors'] = [{'name': content.get('channel_name', content.get('owner', 'Unknown'))}]
        
        # Handle abstract/content based on type - ensure we always have something
        if content_type == 'article':
            prepared['abstract'] = content.get('abstract', content.get('content', ''))[:5000]
            prepared['journal'] = content.get('journal', 'Unknown Journal')
        
        elif content_type == 'video':
            # Combine description and transcript for video
            description = content.get('abstract', content.get('description', ''))
            transcript = content.get('transcript', '')
            # If no description, use title as fallback
            if not description and not transcript:
                prepared['abstract'] = content.get('title', 'OHDSI Video Content')
            else:
                prepared['abstract'] = f"{description}\n\nTranscript:\n{transcript}"[:5000]
            prepared['journal'] = content.get('channel_name', 'YouTube')
        
        elif content_type == 'repository':
            # Use README as abstract, or description as fallback
            readme = content.get('content', '')
            if not readme:
                readme = content.get('abstract', content.get('description', ''))
            if not readme:
                readme = f"Repository: {content.get('title', 'OHDSI Repository')}"
            prepared['abstract'] = readme[:5000]
            prepared['journal'] = f"GitHub ({content.get('language', content.get('programming_language', 'Code'))})"
            # Add repository topics as keywords
            topics = content.get('topics', [])
            if topics:
                prepared['keywords'].extend(topics)
        
        elif content_type == 'discussion':
            # Use abstract or content, with title as fallback
            abstract = content.get('abstract', '')
            if not abstract:
                abstract = content.get('content', '')
            if not abstract:
                abstract = f"Discussion: {content.get('title', 'OHDSI Forum Discussion')}"
            prepared['abstract'] = abstract[:5000]
            prepared['journal'] = 'OHDSI Forums'
            # Add tags as keywords
            tags = content.get('tags', [])
            if tags:
                prepared['keywords'].extend(tags)
        
        elif content_type == 'documentation':
            # Use content or abstract, with title as fallback
            doc_content = content.get('content', '')
            if not doc_content:
                doc_content = content.get('abstract', '')
            if not doc_content:
                doc_content = f"Documentation: {content.get('title', 'OHDSI Documentation')}"
            prepared['abstract'] = doc_content[:5000]
            prepared['journal'] = f"OHDSI Documentation ({content.get('doc_type', 'guide')})"
        
        return prepared
    
    def _adjust_for_content_type(self, result: Dict[str, Any], 
                                content: Dict[str, Any], 
                                content_type: str) -> Dict[str, Any]:
        """Adjust classification results based on content type."""
        adjusted = result.copy()
        
        # Apply content type weight
        type_weight = self.CONTENT_TYPE_WEIGHTS.get(content_type, 1.0)
        
        # Adjust probabilities
        adjusted['ml_probability'] = result.get('ml_probability', 0.5) * type_weight
        adjusted['gpt_probability'] = result.get('gpt_probability', 0.5) * type_weight
        
        # Content-specific adjustments with stronger boosts for official sources
        if content_type == 'video':
            # Strong boost for official OHDSI channel
            if 'ohdsi' in content.get('channel_name', '').lower():
                adjusted['ml_probability'] = min(1.0, adjusted['ml_probability'] * 1.5)
                adjusted['gpt_probability'] = min(1.0, adjusted['gpt_probability'] * 1.5)
            # Moderate boost for OHDSI in title
            elif 'ohdsi' in content.get('title', '').lower() or 'omop' in content.get('title', '').lower():
                adjusted['ml_probability'] = min(1.0, adjusted['ml_probability'] * 1.2)
                adjusted['gpt_probability'] = min(1.0, adjusted['gpt_probability'] * 1.2)
        
        elif content_type == 'repository':
            # Strong boost for OHDSI organization repos
            owner_lower = content.get('owner', '').lower()
            if owner_lower in ['ohdsi', 'ohdsi-studies']:
                adjusted['ml_probability'] = min(1.0, adjusted['ml_probability'] * 1.6)
                adjusted['gpt_probability'] = min(1.0, adjusted['gpt_probability'] * 1.6)
            
            # Boost if has OHDSI/OMOP topics or in name
            topics = [t.lower() for t in content.get('topics', [])]
            name_lower = content.get('title', '').lower()
            if any(t in topics for t in ['ohdsi', 'omop', 'cdm', 'atlas', 'hades']):
                adjusted['ml_probability'] = min(1.0, adjusted['ml_probability'] * 1.2)
                adjusted['gpt_probability'] = min(1.0, adjusted['gpt_probability'] * 1.2)
            elif any(t in name_lower for t in ['ohdsi', 'omop', 'cdm', 'atlas', 'hades']):
                adjusted['ml_probability'] = min(1.0, adjusted['ml_probability'] * 1.15)
                adjusted['gpt_probability'] = min(1.0, adjusted['gpt_probability'] * 1.15)
        
        elif content_type == 'discussion':
            # Boost if from OHDSI forums
            if 'forums.ohdsi.org' in content.get('url', ''):
                adjusted['ml_probability'] = min(1.0, adjusted['ml_probability'] * 1.3)
                adjusted['gpt_probability'] = min(1.0, adjusted['gpt_probability'] * 1.3)
            # Additional boost if marked as solved
            if content.get('solved'):
                adjusted['ml_probability'] = min(1.0, adjusted['ml_probability'] * 1.1)
                adjusted['gpt_probability'] = min(1.0, adjusted['gpt_probability'] * 1.1)
        
        elif content_type == 'documentation':
            # Strong boost for official documentation
            if content.get('is_official') or 'ohdsi.org' in content.get('url', ''):
                adjusted['ml_probability'] = min(1.0, adjusted['ml_probability'] * 1.4)
                adjusted['gpt_probability'] = min(1.0, adjusted['gpt_probability'] * 1.4)
        
        # Recalculate combined probability
        adjusted['combined_probability'] = (
            adjusted['ml_probability'] * 0.5 + 
            adjusted['gpt_probability'] * 0.5
        )
        
        return adjusted
    
    def _calculate_quality_score(self, content: Dict[str, Any], content_type: str) -> float:
        """
        Calculate quality score based on content type specific metrics.
        
        Returns:
            Quality score between 0 and 1
        """
        quality_score = 0.5  # Base score
        
        if content_type == 'article':
            # Factor in journal impact, citation count, author count
            if content.get('journal'):
                quality_score += 0.1
            if len(content.get('authors', [])) > 3:
                quality_score += 0.1
            if content.get('mesh_terms'):
                quality_score += 0.1
            if content.get('doi'):
                quality_score += 0.1
            if len(content.get('abstract', '')) > 500:
                quality_score += 0.1
        
        elif content_type == 'video':
            # Factor in views, likes, duration, transcript quality
            views = content.get('view_count', 0)
            if views > 1000:
                quality_score += 0.2
            elif views > 100:
                quality_score += 0.1
            
            duration = content.get('media_duration', 0)
            if duration > 600:  # >10 minutes
                quality_score += 0.1
            
            if content.get('transcript'):
                quality_score += 0.2
            
            # Official channel bonus
            if 'ohdsi' in content.get('channel_name', '').lower():
                quality_score += 0.2
        
        elif content_type == 'repository':
            # Factor in stars, documentation, activity
            stars = content.get('stars_count', 0)
            if stars > 100:
                quality_score += 0.2
            elif stars > 10:
                quality_score += 0.1
            
            if len(content.get('content', '')) > 1000:  # Good README
                quality_score += 0.15
            
            if content.get('license'):
                quality_score += 0.05
            
            # OHDSI org bonus
            if content.get('owner', '').lower() == 'ohdsi':
                quality_score += 0.2
            
            # Recent activity
            if content.get('last_commit_date'):
                quality_score += 0.1
        
        elif content_type == 'discussion':
            # Factor in answers, expert involvement, solution status
            if content.get('solved'):
                quality_score += 0.2
            
            if content.get('expert_answered'):
                quality_score += 0.2
            
            answers = content.get('answer_count', 0)
            if answers > 5:
                quality_score += 0.1
            elif answers > 0:
                quality_score += 0.05
            
            if content.get('accepted_answer') or content.get('best_answer'):
                quality_score += 0.15
        
        elif content_type == 'documentation':
            # Factor in official status, recency, completeness
            if content.get('is_official'):
                quality_score += 0.3
            
            if content.get('is_tutorial'):
                quality_score += 0.1
            
            if len(content.get('content', '')) > 2000:
                quality_score += 0.1
            
            if content.get('doc_version'):
                quality_score += 0.05
        
        return min(1.0, quality_score)
    
    def _calculate_final_score(self, combined_prob: float, 
                              quality_score: float, 
                              content_type: str) -> float:
        """
        Calculate final score combining ML/GPT probability with quality score.
        
        Args:
            combined_prob: Combined ML and GPT probability
            quality_score: Content quality score
            content_type: Type of content
            
        Returns:
            Final score between 0 and 1
        """
        # Weight quality score based on content type
        quality_weights = {
            'article': 0.3,        # Quality matters but ML is primary
            'video': 0.4,          # Quality important (official vs random)
            'repository': 0.35,     # Quality important (maintained vs abandoned)
            'discussion': 0.25,     # ML more important than discussion quality
            'documentation': 0.5    # Quality very important (official vs unofficial)
        }
        
        quality_weight = quality_weights.get(content_type, 0.3)
        ml_weight = 1.0 - quality_weight
        
        final_score = (combined_prob * ml_weight) + (quality_score * quality_weight)
        
        return final_score
    
    def get_stats(self) -> Dict[str, Any]:
        """Get classification statistics."""
        return self.stats
    
    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            'total_classified': 0,
            'by_type': {},
            'auto_approved': 0,
            'pending_review': 0
        }