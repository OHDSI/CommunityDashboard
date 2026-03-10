"""
PMC Full Text Enhancer for extracting complete author affiliations.
Supplements PubMed data with richer metadata from PMC when available.
"""

import logging
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from Bio import Entrez
import time

logger = logging.getLogger(__name__)

# Set NCBI Entrez email (required)
Entrez.email = "ohdsi-dashboard@example.com"


class PMCEnhancer:
    """
    Enhances article metadata by fetching additional data from PMC.
    """
    
    def __init__(self, email: str = None, api_key: str = None):
        """
        Initialize PMC enhancer.
        
        Args:
            email: Email for NCBI Entrez (required by NCBI)
            api_key: NCBI API key (optional, increases rate limit)
        """
        if email:
            Entrez.email = email
        if api_key:
            Entrez.api_key = api_key
        
        self.rate_limit = 0.1 if api_key else 0.5
    
    def enhance_authors_from_pmc(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance author information using PMC full text if available.
        
        Args:
            article: Article dictionary with basic PubMed data
            
        Returns:
            Enhanced article with complete author affiliations if found
        """
        pmc_id = article.get('pmc_id')
        if not pmc_id:
            return article
        
        # Clean PMC ID (remove PMC prefix if present)
        if pmc_id.startswith('PMC'):
            pmc_id = pmc_id[3:]
        
        try:
            # Fetch PMC full text XML
            pmc_authors = self._fetch_pmc_authors(pmc_id)
            
            if pmc_authors:
                # Merge PMC author data with existing PubMed data
                article = self._merge_author_data(article, pmc_authors)
                logger.info(f"Enhanced {len(pmc_authors)} authors from PMC{pmc_id}")
            
        except Exception as e:
            logger.debug(f"Could not enhance from PMC{pmc_id}: {e}")
        
        return article
    
    def _fetch_pmc_authors(self, pmc_id: str) -> List[Dict[str, Any]]:
        """
        Fetch author information from PMC full text.
        
        Args:
            pmc_id: PMC ID (without PMC prefix)
            
        Returns:
            List of author dictionaries with affiliations
        """
        try:
            # Fetch PMC article
            handle = Entrez.efetch(
                db="pmc",
                id=pmc_id,
                rettype="xml",
                retmode="xml"
            )
            
            xml_data = handle.read()
            handle.close()
            
            # Parse XML
            root = ET.fromstring(xml_data)
            
            # Extract authors from PMC XML
            authors = []
            
            # PMC uses different paths for authors
            # Try front matter first (most common)
            contrib_group = root.find('.//front//contrib-group')
            
            if contrib_group is not None:
                for i, contrib in enumerate(contrib_group.findall('.//contrib[@contrib-type="author"]'), 1):
                    author = self._parse_pmc_author(contrib, i)
                    if author:
                        # Also check for affiliations referenced by xref
                        aff_refs = contrib.findall('.//xref[@ref-type="aff"]')
                        if aff_refs and not author.get('affiliation'):
                            # Get referenced affiliations
                            affiliations = self._get_referenced_affiliations(root, aff_refs)
                            if affiliations:
                                author['affiliation'] = '; '.join(affiliations)
                        
                        authors.append(author)
            
            time.sleep(self.rate_limit)  # Rate limiting
            return authors
            
        except Exception as e:
            logger.debug(f"Error fetching PMC{pmc_id}: {e}")
            return []
    
    def _parse_pmc_author(self, contrib: ET.Element, position: int) -> Optional[Dict[str, Any]]:
        """
        Parse author information from PMC contrib element.
        
        Args:
            contrib: PMC contrib XML element
            position: Author position in list
            
        Returns:
            Author dictionary with full metadata
        """
        author = {"position": position}
        
        # Extract name components
        name = contrib.find('.//name')
        if name is not None:
            surname = name.find('.//surname')
            given_names = name.find('.//given-names')
            
            if surname is not None:
                author['last_name'] = surname.text or ''
            if given_names is not None:
                author['first_name'] = given_names.text or ''
                # Extract initials from given names if not separately provided
                if author['first_name'] and 'initials' not in author:
                    parts = author['first_name'].split()
                    author['initials'] = ''.join([p[0] for p in parts if p])
        
        # Check for collab (group authorship)
        collab = contrib.find('.//collab')
        if collab is not None:
            author['name'] = collab.text or ''
            author['is_collective'] = True
        
        # Extract ORCID
        contrib_id = contrib.find('.//contrib-id[@contrib-id-type="orcid"]')
        if contrib_id is not None:
            orcid = contrib_id.text
            if orcid and 'orcid.org/' in orcid:
                orcid = orcid.split('orcid.org/')[-1]
            author['orcid'] = orcid
        
        # Extract affiliation
        aff = contrib.find('.//aff')
        if aff is not None:
            # Get all text content, handling mixed content
            affiliation_parts = []
            if aff.text:
                affiliation_parts.append(aff.text)
            for elem in aff:
                if elem.text:
                    affiliation_parts.append(elem.text)
                if elem.tail:
                    affiliation_parts.append(elem.tail)
            
            if affiliation_parts:
                author['affiliation'] = ' '.join(affiliation_parts).strip()
                # Clean up common artifacts
                author['affiliation'] = author['affiliation'].replace('  ', ' ')
        
        # Build name variations for consistency
        if author.get('first_name') and author.get('last_name'):
            author['name'] = f"{author['last_name']}, {author['first_name']}"
            author['full_name'] = f"{author['first_name']} {author['last_name']}"
        elif author.get('last_name'):
            author['name'] = author['last_name']
            author['full_name'] = author['last_name']
        
        return author if (author.get('name') or author.get('last_name')) else None
    
    def _get_referenced_affiliations(self, root: ET.Element, refs: List[ET.Element]) -> List[str]:
        """
        Get affiliations referenced by xref elements.
        
        Args:
            root: Root XML element
            refs: List of xref elements
            
        Returns:
            List of affiliation strings
        """
        affiliations = []
        
        for ref in refs:
            rid = ref.get('rid')
            if rid:
                # Find the referenced affiliation
                aff = root.find(f'.//aff[@id="{rid}"]')
                if aff is not None:
                    # Extract text content
                    aff_text = ''.join(aff.itertext()).strip()
                    if aff_text:
                        # Remove label/number at beginning (e.g., "1", "a", etc.)
                        import re
                        aff_text = re.sub(r'^[0-9a-z]+\s*', '', aff_text)
                        affiliations.append(aff_text)
        
        return affiliations
    
    def _merge_author_data(self, article: Dict[str, Any], pmc_authors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge PMC author data with existing PubMed data.
        
        Args:
            article: Original article with PubMed authors
            pmc_authors: Authors from PMC with full affiliations
            
        Returns:
            Article with enhanced author information
        """
        existing_authors = article.get('authors', [])
        
        # Match authors by position and name
        for i, author in enumerate(existing_authors):
            if i < len(pmc_authors):
                pmc_author = pmc_authors[i]
                
                # Only update if PMC has affiliation and PubMed doesn't
                if pmc_author.get('affiliation') and not author.get('affiliation'):
                    author['affiliation'] = pmc_author['affiliation']
                    author['affiliation_source'] = 'PMC'
                
                # Add ORCID if available in PMC but not PubMed
                if pmc_author.get('orcid') and not author.get('orcid'):
                    author['orcid'] = pmc_author['orcid']
                
                # Note if names don't match (quality check)
                if author.get('last_name') and pmc_author.get('last_name'):
                    if author['last_name'].lower() != pmc_author['last_name'].lower():
                        logger.warning(f"Author name mismatch at position {i+1}: "
                                     f"PubMed={author['last_name']}, PMC={pmc_author['last_name']}")
        
        # Mark that article was enhanced
        article['pmc_enhanced'] = True
        
        return article