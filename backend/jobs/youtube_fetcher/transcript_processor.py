"""
Transcript processor for YouTube videos.
Fetches and processes video transcripts for better content analysis.
"""

import os
import sys
import re
import logging
from typing import Dict, Any, List, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.ohdsi_constants import OHDSI_TERMS

# YouTube transcript API
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api.formatters import TextFormatter
    TRANSCRIPT_API_AVAILABLE = True
except ImportError:
    TRANSCRIPT_API_AVAILABLE = False
    logging.warning("youtube-transcript-api not available. Install with: pip install youtube-transcript-api")

logger = logging.getLogger(__name__)


class TranscriptProcessor:
    """
    Processes YouTube video transcripts for content analysis.
    """

    def __init__(self):
        """Initialize transcript processor."""
        self.formatter = TextFormatter() if TRANSCRIPT_API_AVAILABLE else None

        # OHDSI-specific terminology for detection (from shared constants)
        self.ohdsi_terms = OHDSI_TERMS
    
    def fetch_transcript(self, video_id: str) -> Optional[str]:
        """
        Fetch transcript for a YouTube video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Transcript text or None if unavailable
        """
        if not TRANSCRIPT_API_AVAILABLE:
            logger.warning("Transcript API not available")
            return None
        
        try:
            # Try to get transcript in various languages (English preferred)
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Try to get English transcript first
            transcript = None
            try:
                transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
            except:
                # If English not available, get the first available
                try:
                    transcript = transcript_list.find_generated_transcript(['en'])
                except:
                    # Get any available transcript
                    for t in transcript_list:
                        transcript = t
                        break
            
            if transcript:
                transcript_data = transcript.fetch()
                formatted_transcript = self.formatter.format_transcript(transcript_data)
                return formatted_transcript
            
        except Exception as e:
            logger.debug(f"Could not fetch transcript for video {video_id}: {e}")
        
        return None
    
    def process_transcript(self, transcript: str) -> Dict[str, Any]:
        """
        Process transcript to extract structured information.
        
        Args:
            transcript: Raw transcript text
            
        Returns:
            Processed transcript information
        """
        if not transcript:
            return {}
        
        processed = {
            'text': transcript,
            'length': len(transcript),
            'word_count': len(transcript.split()),
            'segments': self._extract_segments(transcript),
            'topics': self._extract_topics(transcript),
            'speakers': self._identify_speakers(transcript),
            'ohdsi_mentions': self._extract_ohdsi_mentions(transcript),
            'key_phrases': self._extract_key_phrases(transcript),
            'questions': self._extract_questions(transcript),
            'urls': self._extract_urls(transcript),
            'quality_score': self._calculate_transcript_quality(transcript)
        }
        
        return processed
    
    def _extract_segments(self, transcript: str) -> List[Dict[str, Any]]:
        """
        Extract logical segments from transcript.
        """
        segments = []
        
        # Split by natural breaks (multiple newlines or long pauses)
        raw_segments = re.split(r'\n{2,}|\.\s{2,}', transcript)
        
        for i, segment in enumerate(raw_segments):
            if len(segment.strip()) > 50:  # Minimum segment length
                segments.append({
                    'index': i,
                    'text': segment.strip()[:1000],  # Limit segment size
                    'word_count': len(segment.split())
                })
        
        return segments[:20]  # Limit to 20 segments
    
    def _extract_topics(self, transcript: str) -> List[str]:
        """
        Extract main topics discussed in the transcript.
        """
        topics = []
        transcript_lower = transcript.lower()
        
        # Check for OHDSI-related topics
        topic_patterns = {
            'Data Standardization': ['standardiz', 'harmoniz', 'common data model', 'cdm'],
            'Cohort Definition': ['cohort', 'phenotype', 'patient selection', 'inclusion criteria'],
            'Network Studies': ['network study', 'multi-site', 'distributed', 'federated'],
            'Real World Evidence': ['real world evidence', 'rwe', 'observational', 'retrospective'],
            'Drug Safety': ['drug safety', 'pharmacovigilan', 'adverse event', 'side effect'],
            'Machine Learning': ['machine learning', 'artificial intelligence', 'prediction model', 'ml ', ' ai '],
            'Clinical Characterization': ['characteriz', 'baseline characteristic', 'demographic'],
            'Causal Inference': ['causal', 'effect estimation', 'propensity score', 'comparative effectiveness'],
            'Data Quality': ['data quality', 'validation', 'completeness', 'accuracy'],
            'Study Design': ['study design', 'protocol', 'analysis plan', 'statistical']
        }
        
        for topic, patterns in topic_patterns.items():
            for pattern in patterns:
                if pattern in transcript_lower:
                    topics.append(topic)
                    break
        
        return list(set(topics))  # Remove duplicates
    
    def _identify_speakers(self, transcript: str) -> List[str]:
        """
        Try to identify speakers in the transcript.
        """
        speakers = []
        
        # Look for speaker patterns
        speaker_patterns = [
            r'^([A-Z][a-z]+ [A-Z][a-z]+):',  # "First Last:"
            r'^\[([^\]]+)\]',  # "[Speaker Name]"
            r'^Speaker (\d+):',  # "Speaker 1:"
        ]
        
        for pattern in speaker_patterns:
            matches = re.findall(pattern, transcript, re.MULTILINE)
            speakers.extend(matches)
        
        # Also look for introductions
        intro_pattern = r'(?:my name is|i\'m|this is)\s+([A-Z][a-z]+ [A-Z][a-z]+)'
        intro_matches = re.findall(intro_pattern, transcript, re.IGNORECASE)
        speakers.extend(intro_matches)
        
        return list(set(speakers))[:10]  # Unique speakers, limit to 10
    
    def _extract_ohdsi_mentions(self, transcript: str) -> Dict[str, List[str]]:
        """
        Extract OHDSI-specific mentions from transcript.
        """
        mentions = {
            'tools': [],
            'concepts': [],
            'databases': []
        }
        
        transcript_lower = transcript.lower()
        
        for category, terms in self.ohdsi_terms.items():
            for term in terms:
                # Use word boundaries for more accurate matching
                pattern = r'\b' + re.escape(term) + r'\b'
                if re.search(pattern, transcript_lower):
                    mentions[category].append(term)
        
        # Remove duplicates
        for category in mentions:
            mentions[category] = list(set(mentions[category]))
        
        return mentions
    
    def _extract_key_phrases(self, transcript: str) -> List[str]:
        """
        Extract key phrases from transcript.
        """
        key_phrases = []
        
        # Simple approach: extract phrases between important markers
        important_markers = [
            'important', 'key point', 'remember', 'note that',
            'the main', 'critical', 'essential', 'fundamental'
        ]
        
        for marker in important_markers:
            pattern = f'{marker}[^.!?]*[.!?]'
            matches = re.findall(pattern, transcript, re.IGNORECASE)
            key_phrases.extend(matches)
        
        # Also extract quoted phrases
        quoted = re.findall(r'"([^"]+)"', transcript)
        key_phrases.extend([q for q in quoted if 10 < len(q) < 200])
        
        return key_phrases[:15]  # Limit to 15 key phrases
    
    def _extract_questions(self, transcript: str) -> List[str]:
        """
        Extract questions from transcript.
        """
        questions = []
        
        # Find sentences ending with question marks
        question_pattern = r'[^.!?]*\?'
        matches = re.findall(question_pattern, transcript)
        
        for match in matches:
            # Clean up the question
            question = match.strip()
            if len(question) > 10:  # Minimum question length
                questions.append(question)
        
        return questions[:20]  # Limit to 20 questions
    
    def _extract_urls(self, transcript: str) -> List[str]:
        """
        Extract URLs mentioned in transcript.
        """
        urls = []
        
        # URL pattern
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        matches = re.findall(url_pattern, transcript)
        urls.extend(matches)
        
        # Also look for mentioned websites
        website_pattern = r'(?:visit|go to|check out|see)\s+(\w+\.(?:com|org|edu|io|net))'
        website_matches = re.findall(website_pattern, transcript, re.IGNORECASE)
        urls.extend([f"https://{site}" for site in website_matches])
        
        return list(set(urls))[:10]  # Unique URLs, limit to 10
    
    def _calculate_transcript_quality(self, transcript: str) -> float:
        """
        Calculate quality score for transcript.
        """
        if not transcript:
            return 0.0
        
        score = 0.5  # Base score
        
        # Length indicator
        word_count = len(transcript.split())
        if word_count > 1000:
            score += 0.2
        elif word_count > 500:
            score += 0.1
        
        # Check for structure (segments)
        if '\n\n' in transcript or '. ' in transcript:
            score += 0.1
        
        # Check for OHDSI-specific content
        ohdsi_mentions = self._extract_ohdsi_mentions(transcript)
        total_mentions = sum(len(m) for m in ohdsi_mentions.values())
        if total_mentions > 5:
            score += 0.2
        elif total_mentions > 2:
            score += 0.1
        
        # Check for technical depth (presence of numbers, technical terms)
        if re.search(r'\b\d+\b', transcript):  # Contains numbers
            score += 0.05
        
        technical_terms = ['analysis', 'method', 'algorithm', 'model', 'data', 'study']
        technical_count = sum(1 for term in technical_terms if term in transcript.lower())
        if technical_count > 3:
            score += 0.05
        
        return min(1.0, score)
    
    def summarize_transcript(self, transcript: str, max_length: int = 500) -> str:
        """
        Create a summary of the transcript.
        """
        if not transcript:
            return ""
        
        # Simple extractive summarization
        sentences = re.split(r'[.!?]+', transcript)
        
        # Score sentences based on important terms
        scored_sentences = []
        for sentence in sentences:
            if len(sentence) < 20:  # Skip very short sentences
                continue
            
            score = 0
            sentence_lower = sentence.lower()
            
            # Score based on OHDSI terms
            for category_terms in self.ohdsi_terms.values():
                for term in category_terms:
                    if term in sentence_lower:
                        score += 2
            
            # Score based on importance markers
            importance_markers = ['important', 'key', 'main', 'critical', 'essential']
            for marker in importance_markers:
                if marker in sentence_lower:
                    score += 1
            
            scored_sentences.append((sentence, score))
        
        # Sort by score and select top sentences
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        
        summary = []
        current_length = 0
        for sentence, _ in scored_sentences:
            if current_length + len(sentence) > max_length:
                break
            summary.append(sentence.strip())
            current_length += len(sentence)
        
        return '. '.join(summary) + '.' if summary else transcript[:max_length]