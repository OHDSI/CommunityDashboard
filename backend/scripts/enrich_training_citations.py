#!/usr/bin/env python3
"""
Enrich training BibTeX files with citation metadata for improved classification.
This script adds citation counts and overlap information to training data.

Usage:
    python enrich_training_citations.py
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import logging
import pickle
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import time

from Bio import Entrez
from jobs.article_classifier.retriever import PubMedRetriever
import pandas as pd
import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure Entrez
Entrez.email = os.getenv("NCBI_ENTREZ_EMAIL", "ohdsi-dashboard@example.com")
if os.getenv("NCBI_ENTREZ_API_KEY"):
    Entrez.api_key = os.getenv("NCBI_ENTREZ_API_KEY")


class TrainingDataEnricher:
    """Enrich training data with citation information."""
    
    def __init__(self, data_dir: str = None):
        """Initialize the enricher."""
        self.data_dir = Path(data_dir) if data_dir else Path("/app/jobs/article_classifier/data")
        self.retriever = PubMedRetriever()
        
        # Cache for citation data to avoid repeated API calls
        self.cache_file = self.data_dir / "citation_cache.pkl"
        self.citation_cache = self.load_cache()
        
        # Store sets of PMIDs for overlap calculations
        self.positive_pmids = set()
        self.negative_pmids = set()
        
    def load_cache(self) -> Dict:
        """Load cached citation data if available."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'rb') as f:
                    cache = pickle.load(f)
                logger.info(f"Loaded cache with {len(cache)} entries")
                return cache
            except Exception as e:
                logger.warning(f"Could not load cache: {e}")
        return {}
    
    def save_cache(self):
        """Save citation cache to disk."""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.citation_cache, f)
            logger.info(f"Saved cache with {len(self.citation_cache)} entries")
        except Exception as e:
            logger.error(f"Could not save cache: {e}")
    
    def parse_bibtex(self, filepath: str) -> List[Dict]:
        """Parse a BibTeX file and return list of entries."""
        with open(filepath, 'r', encoding='utf-8') as f:
            parser = BibTexParser(common_strings=True)
            parser.customization = convert_to_unicode
            bib_db = bibtexparser.load(f, parser=parser)
        
        entries = []
        for entry in bib_db.entries:
            # Extract PMID from various possible fields
            pmid = None
            if 'pmid' in entry:
                pmid = entry['pmid'].replace('PMID', '').strip()
            elif 'pubmed' in entry:
                pmid = entry['pubmed'].replace('PMID', '').strip()
            elif 'ID' in entry and entry['ID'].startswith('PMID'):
                pmid = entry['ID'].replace('PMID', '').strip()
            
            if pmid:
                entries.append({
                    'pmid': pmid,
                    'title': entry.get('title', ''),
                    'year': entry.get('year', ''),
                    'journal': entry.get('journal', ''),
                    'authors': entry.get('author', ''),
                    'abstract': entry.get('abstract', '')
                })
        
        return entries
    
    def get_citation_info(self, pmid: str) -> Dict:
        """Get citation information for a PMID."""
        # Check cache first
        if pmid in self.citation_cache:
            return self.citation_cache[pmid]
        
        try:
            # Use PubMed E-utilities to get citation data
            # Get cited by (papers that cite this one)
            cited_by_ids = []
            try:
                handle = Entrez.elink(
                    dbfrom="pubmed",
                    id=pmid,
                    linkname="pubmed_pubmed_citedin"
                )
                result = Entrez.read(handle)
                handle.close()
                
                if result and result[0].get("LinkSetDb"):
                    links = result[0]["LinkSetDb"][0].get("Link", [])
                    cited_by_ids = [link["Id"] for link in links[:100]]  # Limit to 100
            except Exception as e:
                logger.debug(f"Could not get cited_by for {pmid}: {e}")
            
            # Get references (papers this one cites)
            reference_ids = []
            try:
                handle = Entrez.elink(
                    dbfrom="pubmed",
                    id=pmid,
                    linkname="pubmed_pubmed_refs"
                )
                result = Entrez.read(handle)
                handle.close()
                
                if result and result[0].get("LinkSetDb"):
                    links = result[0]["LinkSetDb"][0].get("Link", [])
                    reference_ids = [link["Id"] for link in links[:100]]  # Limit to 100
            except Exception as e:
                logger.debug(f"Could not get references for {pmid}: {e}")
            
            # Get related/similar papers
            similar_ids = []
            try:
                handle = Entrez.elink(
                    dbfrom="pubmed",
                    id=pmid,
                    linkname="pubmed_pubmed"
                )
                result = Entrez.read(handle)
                handle.close()
                
                if result and result[0].get("LinkSetDb"):
                    links = result[0]["LinkSetDb"][0].get("Link", [])
                    similar_ids = [link["Id"] for link in links[:20]]  # Limit to 20
            except Exception as e:
                logger.debug(f"Could not get similar for {pmid}: {e}")
            
            citation_info = {
                'cited_by': cited_by_ids,
                'references': reference_ids,
                'similar': similar_ids,
                'cited_by_count': len(cited_by_ids),
                'reference_count': len(reference_ids)
            }
            
            # Cache the result
            self.citation_cache[pmid] = citation_info
            
            # Rate limit to be respectful
            time.sleep(0.34)  # ~3 requests per second
            
            return citation_info
            
        except Exception as e:
            logger.error(f"Error getting citations for {pmid}: {e}")
            return {
                'cited_by': [],
                'references': [],
                'similar': [],
                'cited_by_count': 0,
                'reference_count': 0
            }
    
    def calculate_overlap_features(self, pmid: str, citation_info: Dict) -> Dict:
        """Calculate overlap with positive/negative training sets."""
        features = {}
        
        # Convert citation IDs to sets
        cited_by_set = set(citation_info.get('cited_by', []))
        references_set = set(citation_info.get('references', []))
        
        # Calculate overlaps with positive set
        features['cites_positive'] = len(references_set & self.positive_pmids)
        features['cited_by_positive'] = len(cited_by_set & self.positive_pmids)
        features['positive_overlap_ratio'] = (
            (features['cites_positive'] + features['cited_by_positive']) / 
            max(len(cited_by_set) + len(references_set), 1)
        )
        
        # Calculate overlaps with negative set
        features['cites_negative'] = len(references_set & self.negative_pmids)
        features['cited_by_negative'] = len(cited_by_set & self.negative_pmids)
        features['negative_overlap_ratio'] = (
            (features['cites_negative'] + features['cited_by_negative']) / 
            max(len(cited_by_set) + len(references_set), 1)
        )
        
        # Net overlap score (positive - negative)
        features['net_overlap_score'] = (
            features['positive_overlap_ratio'] - features['negative_overlap_ratio']
        )
        
        return features
    
    def enrich_dataset(self, input_file: str, output_file: str, label: int) -> pd.DataFrame:
        """Enrich a BibTeX file with citation features."""
        logger.info(f"Processing {input_file}")
        
        # Parse the BibTeX file
        entries = self.parse_bibtex(input_file)
        logger.info(f"Found {len(entries)} entries")
        
        # Store PMIDs for overlap calculations
        pmid_set = {e['pmid'] for e in entries if e.get('pmid')}
        if label == 1:
            self.positive_pmids.update(pmid_set)
        else:
            self.negative_pmids.update(pmid_set)
        
        # Enrich each entry
        enriched_entries = []
        for i, entry in enumerate(entries):
            if i % 10 == 0:
                logger.info(f"Processing entry {i+1}/{len(entries)}")
            
            pmid = entry.get('pmid')
            if not pmid:
                continue
            
            # Get citation information
            citation_info = self.get_citation_info(pmid)
            
            # Add citation features
            entry.update({
                'cited_by_count': citation_info['cited_by_count'],
                'reference_count': citation_info['reference_count'],
                'has_citations': citation_info['cited_by_count'] > 0,
                'has_references': citation_info['reference_count'] > 0,
                'citation_ratio': (
                    citation_info['cited_by_count'] / 
                    max(citation_info['reference_count'], 1)
                ),
                'label': label
            })
            
            # Store full citation data for later overlap calculation
            entry['_citations'] = citation_info
            
            enriched_entries.append(entry)
        
        # Save intermediate results
        self.save_cache()
        
        return pd.DataFrame(enriched_entries)
    
    def add_overlap_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add overlap features after all data is loaded."""
        logger.info("Calculating overlap features...")
        
        for idx, row in df.iterrows():
            pmid = row.get('pmid')
            if not pmid or '_citations' not in row:
                continue
            
            overlap_features = self.calculate_overlap_features(pmid, row['_citations'])
            for key, value in overlap_features.items():
                df.at[idx, key] = value
        
        # Remove temporary citation data
        if '_citations' in df.columns:
            df = df.drop('_citations', axis=1)
        
        return df
    
    def run(self):
        """Run the enrichment process."""
        # File paths
        positive_bib = self.data_dir / "enriched_articles_ohdsi_reformatted.bib"
        negative_bib = self.data_dir / "No_OHDSI_Citations.bib"
        
        # Process positive examples
        logger.info("Processing positive examples...")
        positive_df = self.enrich_dataset(
            str(positive_bib),
            str(self.data_dir / "positive_enriched.json"),
            label=1
        )
        
        # Process negative examples
        logger.info("Processing negative examples...")
        negative_df = self.enrich_dataset(
            str(negative_bib),
            str(self.data_dir / "negative_enriched.json"),
            label=0
        )
        
        # Combine datasets
        all_df = pd.concat([positive_df, negative_df], ignore_index=True)
        
        # Add overlap features now that we have all PMIDs
        all_df = self.add_overlap_features(all_df)
        
        # Save enriched data
        output_file = self.data_dir / "enriched_training_data.json"
        all_df.to_json(str(output_file), orient='records', indent=2)
        logger.info(f"Saved enriched data to {output_file}")
        
        # Save as pickle for faster loading
        pickle_file = self.data_dir / "enriched_training_data.pkl"
        all_df.to_pickle(str(pickle_file))
        logger.info(f"Saved pickle to {pickle_file}")
        
        # Print statistics
        logger.info("\nEnrichment Statistics:")
        logger.info(f"Total entries: {len(all_df)}")
        logger.info(f"Positive examples: {len(positive_df)}")
        logger.info(f"Negative examples: {len(negative_df)}")
        logger.info(f"Entries with citations: {all_df['has_citations'].sum()}")
        logger.info(f"Entries with references: {all_df['has_references'].sum()}")
        logger.info(f"Avg citations (positive): {positive_df['cited_by_count'].mean():.2f}")
        logger.info(f"Avg citations (negative): {negative_df['cited_by_count'].mean():.2f}")
        logger.info(f"Avg positive overlap: {all_df['positive_overlap_ratio'].mean():.3f}")
        
        # Save final cache
        self.save_cache()
        
        return all_df


if __name__ == "__main__":
    enricher = TrainingDataEnricher()
    enricher.run()