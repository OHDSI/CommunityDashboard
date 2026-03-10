"""
PubMed article retriever with comprehensive data extraction.
Fetches articles and extracts all available metadata including authors, dates, MeSH terms, etc.
"""

import os
import re
import time
import calendar
import threading
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Dict, Optional, Any
from io import StringIO
from html import unescape
import logging
import requests

from Bio import Entrez, Medline
from lxml import etree

# Import PMC enhancer for complete author affiliations
try:
    from .pmc_enhancer import PMCEnhancer
except ImportError:
    PMCEnhancer = None
    logger.warning("PMC enhancer not available - author affiliations may be incomplete")

logger = logging.getLogger(__name__)

# Set NCBI Entrez email (required)
Entrez.email = os.getenv("NCBI_ENTREZ_EMAIL") or "ohdsi-dashboard@example.com"
if not os.getenv("NCBI_ENTREZ_EMAIL"):
    logger.warning("NCBI_ENTREZ_EMAIL not set. Using default: ohdsi-dashboard@example.com")


class PubMedRetriever:
    """
    Retrieves articles from PubMed with comprehensive metadata extraction.
    """
    
    def __init__(self, email: str = None, api_key: str = None, enhance_from_pmc: bool = True):
        """
        Initialize the PubMed retriever.
        
        Args:
            email: Email for NCBI Entrez (required by NCBI)
            api_key: NCBI API key (optional, increases rate limit)
            enhance_from_pmc: Whether to fetch additional data from PMC when available
        """
        if email:
            Entrez.email = email
        if api_key:
            Entrez.api_key = api_key

        # Store API key for direct HTTP calls (e.g., ELink)
        self.api_key = api_key

        # Rate limiting (in seconds between requests)
        self.rate_limit = 0.1 if api_key else 0.5

        # Persistent HTTP session for connection pooling (reuses TCP connections)
        self._session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=5,
            pool_maxsize=5,
            max_retries=0,  # We handle retries ourselves
        )
        self._session.mount('https://', adapter)

        # Initialize PMC enhancer if available and enabled
        self.enhance_from_pmc = enhance_from_pmc
        self.pmc_enhancer = None
        if enhance_from_pmc and PMCEnhancer:
            self.pmc_enhancer = PMCEnhancer(email=email, api_key=api_key)
            logger.info("PMC enhancement enabled for complete author affiliations")
    
    def search_pubmed(self, query: str, max_results: int = 100,
                     start_date: str = None, end_date: str = None) -> List[str]:
        """
        Search PubMed for articles matching the query.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            start_date: Start date for search (YYYY/MM/DD format)
            end_date: End date for search (YYYY/MM/DD format)
            
        Returns:
            List of PubMed IDs
        """
        # Build query with date filter if provided
        if start_date and end_date:
            query = f"({query}) AND ({start_date}[PDAT] : {end_date}[PDAT])"
        elif end_date:
            # Last year if only end date provided
            query = f"({query}) AND (2023/01/01[PDAT] : {end_date}[PDAT])"
        
        try:
            # Search PubMed
            handle = Entrez.esearch(
                db="pubmed",
                term=query,
                retmax=max_results,
                sort="relevance",
                retmode="xml"
            )
            results = Entrez.read(handle)
            handle.close()
            
            pmids = results.get("IdList", [])
            logger.info(f"Found {len(pmids)} articles for query: {query[:100]}...")
            
            return pmids
            
        except Exception as e:
            logger.error(f"PubMed search failed: {e}")
            return []
    
    def fetch_article_details(self, pmids: List[str], batch_size: int = 50) -> List[Dict]:
        """
        Fetch comprehensive article metadata using XML format for maximum data.
        
        Args:
            pmids: List of PubMed IDs
            batch_size: Number of articles to fetch at once
            
        Returns:
            List of article dictionaries with all available metadata
        """
        if not pmids:
            return []
        
        articles = []
        
        for i in range(0, len(pmids), batch_size):
            batch = pmids[i:i+batch_size]
            
            try:
                # Fetch records in XML format for complete data
                handle = Entrez.efetch(
                    db="pubmed",
                    id=",".join(batch),
                    rettype="xml",
                    retmode="xml"
                )
                
                xml_data = handle.read()
                handle.close()
                
                # Parse XML tree
                root = ET.fromstring(xml_data)

                # Process each PubmedArticle
                parsed_articles = []
                for article_elem in root.findall('.//PubmedArticle'):
                    article = self._parse_xml_article(article_elem)
                    if article:
                        parsed_articles.append(article)

                # Enhance PMC authors concurrently
                if self.pmc_enhancer:
                    pmc_articles = [a for a in parsed_articles if a.get('pmc_id')]
                    if pmc_articles:
                        max_pmc_workers = 5 if self.api_key else 2
                        with ThreadPoolExecutor(max_workers=max_pmc_workers) as pmc_executor:
                            future_to_idx = {}
                            for idx, art in enumerate(parsed_articles):
                                if art.get('pmc_id'):
                                    future_to_idx[pmc_executor.submit(
                                        self.pmc_enhancer.enhance_authors_from_pmc, art
                                    )] = idx
                            for future in as_completed(future_to_idx):
                                idx = future_to_idx[future]
                                try:
                                    parsed_articles[idx] = future.result()
                                except Exception as e:
                                    logger.debug(f"PMC enhancement failed for {parsed_articles[idx].get('pmid')}: {e}")

                articles.extend(parsed_articles)
                
                time.sleep(self.rate_limit)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Error fetching XML batch {i//batch_size + 1}: {e}")
                # Try fallback to MEDLINE format
                try:
                    fallback_articles = self._fetch_medline_fallback(batch)
                    articles.extend(fallback_articles)
                except Exception as e2:
                    logger.error(f"Fallback also failed: {e2}")
        
        logger.info(f"Fetched comprehensive details for {len(articles)} articles")
        return articles
    
    def fetch_pubmed_details(self, pmids: List[str]) -> List[Dict]:
        """Alias for backward compatibility"""
        return self.fetch_article_details(pmids)
    
    def search_and_fetch(self, query: str, max_results: int = 100,
                        start_date: str = None, end_date: str = None) -> List[Dict]:
        """
        Search PubMed and fetch complete article details in one call.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            start_date: Start date for search (YYYY/MM/DD format)
            end_date: End date for search (YYYY/MM/DD format)
            
        Returns:
            List of article dictionaries with complete metadata
        """
        # First search for PMIDs
        pmids = self.search_pubmed(query, max_results, start_date, end_date)
        
        if not pmids:
            return []
        
        # Then fetch complete details
        return self.fetch_article_details(pmids)
    
    def _parse_xml_article(self, article_elem: ET.Element) -> Optional[Dict]:
        """
        Parse a PubmedArticle XML element to extract all available metadata.
        """
        try:
            # Get MedlineCitation
            medline = article_elem.find('.//MedlineCitation')
            if medline is None:
                return None
            
            # Extract PMID
            pmid_elem = medline.find('.//PMID')
            if pmid_elem is None:
                return None
            pmid = pmid_elem.text
            
            # Extract article details
            article = medline.find('.//Article')
            if article is None:
                return None
            
            # Title
            title = self._get_text(article, './/ArticleTitle', '')
            vernacular_title = self._get_text(article, './/VernacularTitle')
            
            # Abstract - handle structured abstracts
            abstract_text, abstract_sections = self._extract_abstract(article)
            
            # Authors with full information including ORCID
            authors = self._extract_authors_xml(article)
            
            # All dates - comprehensive date extraction
            dates = self._extract_all_dates(article, medline, article_elem)
            
            # Journal information
            journal_info = self._extract_journal_info(article, medline)
            
            # Keywords and MeSH terms
            keywords = self._extract_keywords(medline)
            mesh_terms = self._extract_mesh_terms(medline)
            
            # Publication types
            pub_types = [pt.text for pt in article.findall('.//PublicationType') if pt.text]
            
            # Identifiers - DOI, PMC ID, etc.
            doi = self._extract_doi_xml(article, article_elem)
            pmc_id = self._extract_pmc_id(article_elem)
            
            # Funding information
            grants = self._extract_grants(article)
            
            # Language
            language = self._get_text(article, './/Language', 'eng')
            
            # Chemical list
            chemicals = self._extract_chemicals(medline)
            
            # References
            ref_count = self._get_text(medline, './/NumberOfReferences', '0')
            
            # Build comprehensive article dict
            article_dict = {
                # Identifiers
                "id": f"PMID{pmid}",
                "pmid": pmid,
                "pmc_id": pmc_id,
                "doi": doi,
                
                # Titles
                "title": title,
                "vernacular_title": vernacular_title,
                
                # Abstract
                "abstract": abstract_text,
                "abstract_sections": abstract_sections,
                
                # Authors - comprehensive info
                "authors": authors,
                "author_count": len(authors),
                
                # Journal
                "journal": journal_info.get('title', ''),
                "journal_info": journal_info,
                
                # Dates - all available dates
                "year": dates.get('year', ''),
                "published_date": dates.get('published_date'),
                "electronic_date": dates.get('electronic_date'),
                "print_date": dates.get('print_date'),
                "received_date": dates.get('received_date'),
                "accepted_date": dates.get('accepted_date'),
                "revised_date": dates.get('revised_date'),
                "pubmed_date": dates.get('pubmed_date'),
                "medline_date": dates.get('medline_date'),
                
                # Publication details
                "volume": self._get_text(article, './/Volume'),
                "issue": self._get_text(article, './/Issue'),
                "pages": self._extract_pages(article),
                
                # Classification
                "keywords": keywords,
                "mesh_terms": mesh_terms,
                "publication_types": pub_types,
                "chemicals": chemicals,
                
                # Language
                "language": language,
                
                # Funding
                "grants": grants,
                "has_funding": len(grants) > 0,
                
                # References
                "reference_count": int(ref_count) if ref_count.isdigit() else 0,
                
                # URL
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                
                # Status
                "medline_status": medline.get('Status', 'PubMed'),
                "indexing_method": medline.get('IndexingMethod'),
                
                # Full text availability
                "has_pmc_full_text": pmc_id is not None,
                "pmc_url": f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/" if pmc_id else None
            }
            
            return article_dict
            
        except Exception as e:
            logger.error(f"Error parsing XML article: {e}")
            return None
    
    def _get_text(self, elem: ET.Element, path: str, default: str = None) -> Optional[str]:
        """Safely extract text from XML element"""
        found = elem.find(path)
        return found.text if found is not None and found.text else default
    
    def _extract_abstract(self, article: ET.Element) -> tuple[str, Dict[str, str]]:
        """Extract abstract text and structured sections"""
        abstract_elem = article.find('.//Abstract')
        if abstract_elem is None:
            return '', {}
        
        sections = {}
        full_text_parts = []
        
        # Handle structured abstract with labels
        for abstract_text in abstract_elem.findall('.//AbstractText'):
            label = abstract_text.get('Label', '')
            text = ''.join(abstract_text.itertext()) if abstract_text.text or len(abstract_text) else ''
            
            if label:
                sections[label] = text
                full_text_parts.append(f"{label}: {text}")
            elif text:
                full_text_parts.append(text)
        
        full_text = ' '.join(full_text_parts)
        return self._clean_text(full_text), sections
    
    def _extract_authors_xml(self, article: ET.Element) -> List[Dict[str, Any]]:
        """Extract comprehensive author information including ORCID"""
        authors = []
        author_list = article.find('.//AuthorList')
        
        if author_list is None:
            return authors
        
        for i, author_elem in enumerate(author_list.findall('.//Author'), 1):
            author = {
                "position": i,
                "last_name": self._get_text(author_elem, 'LastName', ''),
                "first_name": self._get_text(author_elem, 'ForeName', ''),
                "initials": self._get_text(author_elem, 'Initials', ''),
                "affiliation": None,
                "orcid": None,
                "is_equal_contributor": author_elem.get('EqualContrib') == 'Y'
            }
            
            # Build name variations
            if author['first_name'] and author['last_name']:
                author['name'] = f"{author['last_name']}, {author['first_name']}"
                author['full_name'] = f"{author['first_name']} {author['last_name']}"
            elif author['last_name'] and author['initials']:
                author['name'] = f"{author['last_name']} {author['initials']}"
                author['full_name'] = author['name']
            elif author['last_name']:
                author['name'] = author['last_name']
                author['full_name'] = author['last_name']
            else:
                # Check for collective name
                collective = self._get_text(author_elem, 'CollectiveName')
                if collective:
                    author['name'] = collective
                    author['full_name'] = collective
                    author['is_collective'] = True
                else:
                    continue
            
            # Extract ORCID if available
            for identifier in author_elem.findall('.//Identifier'):
                if identifier.get('Source') == 'ORCID':
                    orcid = identifier.text
                    # Clean ORCID (remove URL prefix if present)
                    if orcid and 'orcid.org/' in orcid:
                        orcid = orcid.split('orcid.org/')[-1]
                    author['orcid'] = orcid
                    break
            
            # Extract affiliation
            affiliation_elem = author_elem.find('.//AffiliationInfo/Affiliation')
            if affiliation_elem is not None:
                author['affiliation'] = affiliation_elem.text
            
            authors.append(author)
        
        return authors
    
    def _extract_all_dates(self, article: ET.Element, medline: ET.Element, root: ET.Element) -> Dict[str, Any]:
        """Extract all available dates from the article"""
        dates = {}
        
        # Primary publication date
        pub_date = article.find('.//PubDate')
        if pub_date is not None:
            year = self._get_text(pub_date, 'Year')
            month = self._get_text(pub_date, 'Month')
            day = self._get_text(pub_date, 'Day')
            
            # Handle MedlineDate (e.g., "2023 Nov-Dec")
            if not year:
                medline_date = self._get_text(pub_date, 'MedlineDate')
                if medline_date:
                    year_match = re.search(r'(\d{4})', medline_date)
                    if year_match:
                        year = year_match.group(1)
            
            if year:
                dates['year'] = year
                dates['published_date'] = self._format_date(year, month, day)
        
        # Electronic publication date
        article_date = article.find('.//ArticleDate')
        if article_date is not None:
            date_type = article_date.get('DateType', 'Electronic')
            year = self._get_text(article_date, 'Year')
            month = self._get_text(article_date, 'Month') 
            day = self._get_text(article_date, 'Day')
            if year:
                if date_type == 'Electronic':
                    dates['electronic_date'] = self._format_date(year, month, day)
                else:
                    dates['print_date'] = self._format_date(year, month, day)
        
        # MEDLINE dates
        date_completed = medline.find('.//DateCompleted')
        if date_completed is not None:
            year = self._get_text(date_completed, 'Year')
            month = self._get_text(date_completed, 'Month')
            day = self._get_text(date_completed, 'Day')
            if year:
                dates['medline_date'] = self._format_date(year, month, day)
        
        date_revised = medline.find('.//DateRevised')
        if date_revised is not None:
            year = self._get_text(date_revised, 'Year')
            month = self._get_text(date_revised, 'Month')
            day = self._get_text(date_revised, 'Day')
            if year:
                dates['revised_date'] = self._format_date(year, month, day)
        
        # History dates (received, accepted, etc.)
        pubmed_data = root.find('.//PubmedData')
        if pubmed_data is not None:
            history = pubmed_data.find('.//History')
            if history is not None:
                for pub_date in history.findall('.//PubMedPubDate'):
                    status = pub_date.get('PubStatus')
                    year = self._get_text(pub_date, 'Year')
                    month = self._get_text(pub_date, 'Month')
                    day = self._get_text(pub_date, 'Day')
                    
                    if year and status:
                        date_str = self._format_date(year, month, day)
                        if status == 'received':
                            dates['received_date'] = date_str
                        elif status == 'accepted':
                            dates['accepted_date'] = date_str
                        elif status == 'revised':
                            dates['last_revised_date'] = date_str
                        elif status == 'pubmed':
                            dates['pubmed_date'] = date_str
                        elif status == 'entrez':
                            dates['entrez_date'] = date_str
        
        # Determine best primary date
        if 'published_date' not in dates:
            if 'electronic_date' in dates:
                dates['published_date'] = dates['electronic_date']
            elif 'print_date' in dates:
                dates['published_date'] = dates['print_date']
            elif 'pubmed_date' in dates:
                dates['published_date'] = dates['pubmed_date']
            elif 'year' in dates:
                dates['published_date'] = f"{dates['year']}-01-01T00:00:00"
        
        return dates
    
    def _format_date(self, year: str, month: str = None, day: str = None) -> str:
        """Format date components into ISO format"""
        if not year:
            return None
        
        # Convert month name to number if needed
        if month and not month.isdigit():
            month_num = None
            for i, m in enumerate(calendar.month_abbr[1:], 1):
                if m.lower() == month[:3].lower():
                    month_num = str(i)
                    break
            month = month_num
        
        # Ensure proper formatting
        if month:
            month = month.zfill(2)
        if day:
            day = day.zfill(2)
        
        if month and day:
            return f"{year}-{month}-{day}T00:00:00"
        elif month:
            return f"{year}-{month}-01T00:00:00"
        else:
            return f"{year}-01-01T00:00:00"
    
    def _extract_journal_info(self, article: ET.Element, medline: ET.Element) -> Dict[str, str]:
        """Extract comprehensive journal information"""
        journal = article.find('.//Journal')
        journal_info = {}
        
        if journal is not None:
            journal_info['title'] = self._get_text(journal, 'Title', '')
            journal_info['iso_abbreviation'] = self._get_text(journal, 'ISOAbbreviation')
            
            # ISSNs
            for issn in journal.findall('.//ISSN'):
                issn_type = issn.get('IssnType', '')
                if issn_type == 'Electronic':
                    journal_info['issn_electronic'] = issn.text
                elif issn_type == 'Print':
                    journal_info['issn_print'] = issn.text
        
        # Additional info from MedlineJournalInfo
        medline_journal = medline.find('.//MedlineJournalInfo')
        if medline_journal is not None:
            journal_info['country'] = self._get_text(medline_journal, 'Country')
            journal_info['medline_ta'] = self._get_text(medline_journal, 'MedlineTA')
            journal_info['nlm_unique_id'] = self._get_text(medline_journal, 'NlmUniqueID')
        
        return journal_info
    
    def _extract_keywords(self, medline: ET.Element) -> List[str]:
        """Extract author-provided keywords"""
        keywords = []
        
        # Get author keywords
        for keyword_list in medline.findall('.//KeywordList'):
            for keyword in keyword_list.findall('.//Keyword'):
                if keyword.text:
                    keywords.append(keyword.text)
        
        return keywords
    
    def _extract_mesh_terms(self, medline: ET.Element) -> List[Dict[str, Any]]:
        """Extract MeSH terms with metadata"""
        mesh_terms = []
        mesh_list = medline.find('.//MeshHeadingList')
        
        if mesh_list is not None:
            for heading in mesh_list.findall('.//MeshHeading'):
                descriptor = heading.find('.//DescriptorName')
                if descriptor is not None and descriptor.text:
                    mesh_term = {
                        'descriptor_name': descriptor.text,
                        'descriptor_ui': descriptor.get('UI', ''),
                        'is_major_topic': descriptor.get('MajorTopicYN') == 'Y',
                        'qualifiers': []
                    }
                    
                    # Add qualifiers
                    for qualifier in heading.findall('.//QualifierName'):
                        if qualifier.text:
                            mesh_term['qualifiers'].append({
                                'name': qualifier.text,
                                'ui': qualifier.get('UI', ''),
                                'is_major': qualifier.get('MajorTopicYN') == 'Y'
                            })
                    
                    mesh_terms.append(mesh_term)
        
        return mesh_terms
    
    def _extract_doi_xml(self, article: ET.Element, root: ET.Element) -> Optional[str]:
        """Extract DOI from XML article"""
        # Try ELocationID
        for elocation in article.findall('.//ELocationID'):
            if elocation.get('EIdType') == 'doi':
                return elocation.text
        
        # Try ArticleIdList in PubmedData
        pubmed_data = root.find('.//PubmedData')
        if pubmed_data is not None:
            for article_id in pubmed_data.findall('.//ArticleId'):
                if article_id.get('IdType') == 'doi':
                    return article_id.text
        
        return None
    
    def _extract_pmc_id(self, root: ET.Element) -> Optional[str]:
        """Extract PMC ID if available"""
        pubmed_data = root.find('.//PubmedData')
        if pubmed_data is not None:
            for article_id in pubmed_data.findall('.//ArticleId'):
                if article_id.get('IdType') == 'pmc':
                    pmc_id = article_id.text
                    # Clean PMC ID
                    if pmc_id and pmc_id.startswith('PMC'):
                        return pmc_id
                    elif pmc_id:
                        return f"PMC{pmc_id}"
        return None
    
    def _extract_grants(self, article: ET.Element) -> List[Dict[str, str]]:
        """Extract funding/grant information"""
        grants = []
        grant_list = article.find('.//GrantList')
        
        if grant_list is not None:
            for grant in grant_list.findall('.//Grant'):
                grant_info = {
                    'grant_id': self._get_text(grant, 'GrantID'),
                    'agency': self._get_text(grant, 'Agency', ''),
                    'country': self._get_text(grant, 'Country'),
                    'acronym': self._get_text(grant, 'Acronym')
                }
                if grant_info['agency']:  # Only add if agency exists
                    grants.append(grant_info)
        
        return grants
    
    def _extract_chemicals(self, medline: ET.Element) -> List[Dict[str, str]]:
        """Extract chemical substances"""
        chemicals = []
        chemical_list = medline.find('.//ChemicalList')
        
        if chemical_list is not None:
            for chemical in chemical_list.findall('.//Chemical'):
                name_elem = chemical.find('NameOfSubstance')
                if name_elem is not None:
                    chem_info = {
                        'registry_number': self._get_text(chemical, 'RegistryNumber'),
                        'name': name_elem.text or '',
                        'ui': name_elem.get('UI', '')
                    }
                    chemicals.append(chem_info)
        
        return chemicals
    
    def _extract_pages(self, article: ET.Element) -> Optional[str]:
        """Extract page information"""
        pagination = article.find('.//Pagination')
        if pagination is not None:
            # Try MedlinePgn first (most complete)
            medline_pgn = self._get_text(pagination, 'MedlinePgn')
            if medline_pgn:
                return medline_pgn
            
            # Try StartPage-EndPage
            start = self._get_text(pagination, 'StartPage')
            end = self._get_text(pagination, 'EndPage')
            if start and end:
                return f"{start}-{end}"
            elif start:
                return start
        
        return None
    
    def _clean_text(self, text: str) -> str:
        """Clean HTML/XML tags from text"""
        if not isinstance(text, str):
            return ""
        
        # Unescape HTML entities
        text = unescape(text)
        
        try:
            # Parse XML and extract text
            parser = etree.XMLParser(recover=True)
            root = etree.fromstring(f"<root>{text}</root>", parser=parser)
            clean_text = "".join(root.itertext())
        except:
            # Fallback: simple tag removal
            clean_text = re.sub(r'<[^>]*>', '', text)
        
        return clean_text.strip().replace('\n', ' ')
    
    def _fetch_medline_fallback(self, pmids: List[str]) -> List[Dict]:
        """Fallback method using MEDLINE format when XML fails"""
        articles = []
        
        try:
            handle = Entrez.efetch(
                db="pubmed",
                id=",".join(pmids),
                rettype="medline",
                retmode="text"
            )
            records = handle.read()
            handle.close()
            
            for record in Medline.parse(StringIO(records)):
                article = self._parse_medline_record(record)
                articles.append(article)
        except Exception as e:
            logger.error(f"MEDLINE fallback failed: {e}")
        
        return articles
    
    def _parse_medline_record(self, record: Dict) -> Dict:
        """
        Parse a Medline record (fallback when XML parsing fails).
        """
        # Extract authors
        authors = []
        author_names = record.get('AU', [])
        affiliations = record.get('AD', [])
        full_authors = record.get('FAU', [])
        
        for i, author_name in enumerate(author_names):
            author_obj = {
                "name": author_name,
                "position": i + 1,
                "affiliation": None,
                "full_name": None
            }
            
            # Try to get full name
            if i < len(full_authors):
                author_obj["full_name"] = full_authors[i]
            
            # Try to match affiliation
            if affiliations and i < len(affiliations):
                author_obj["affiliation"] = affiliations[i]
            elif affiliations and len(affiliations) == 1:
                author_obj["affiliation"] = affiliations[0]
            
            authors.append(author_obj)
        
        # Parse dates
        dp_date = record.get('DP', '')
        dep_date = record.get('DEP', '')
        edat = record.get('EDAT', '')
        
        # Extract year
        year = self._extract_year(dp_date)
        if not year and edat:
            year = edat.split('/')[0] if '/' in edat else ''
        
        article = {
            "id": f"PMID{record.get('PMID', '')}",
            "pmid": record.get('PMID'),
            "title": record.get('TI', ''),
            "abstract": self._clean_text(record.get('AB', '')),
            "authors": authors,
            "journal": record.get('JT', '') or record.get('TA', ''),
            "year": year,
            "published_date": self._parse_date(dp_date, dep_date),
            "volume": record.get('VI'),
            "issue": record.get('IP'),
            "pages": record.get('PG'),
            "keywords": record.get('OT', []),  # Other terms (keywords)
            "mesh_terms": [{"descriptor_name": term} for term in record.get('MH', [])],
            "doi": self._extract_doi(record),
            "language": record.get('LA', ['eng'])[0] if record.get('LA') else 'eng',
            "publication_types": record.get('PT', []),
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{record.get('PMID', '')}/"
        }
        
        return article
    
    def _extract_year(self, date_str: str) -> str:
        """Extract year from date string"""
        if not date_str:
            return ""
        match = re.search(r'\b(19|20)\d{2}\b', date_str)
        return match.group(0) if match else ""
    
    def _parse_date(self, dp_date: str, dep_date: str = None) -> str:
        """Parse date string to ISO format from MEDLINE format"""
        # Try DEP date first if available
        if dep_date:
            try:
                if len(dep_date) == 8 and dep_date.isdigit():
                    year = dep_date[:4]
                    month = dep_date[4:6]
                    day = dep_date[6:8]
                    return f"{year}-{month}-{day}T00:00:00"
            except:
                pass
        
        # Parse DP field
        if dp_date:
            try:
                # Handle various formats
                if re.match(r'\d{4}\s+\w+\s+\d{1,2}', dp_date):
                    # "2024 Feb 21"
                    parts = dp_date.split()
                    year = parts[0]
                    month_str = parts[1][:3]
                    day = parts[2].zfill(2)
                    
                    for i, month in enumerate(calendar.month_abbr[1:], 1):
                        if month.lower() == month_str.lower():
                            return f"{year}-{str(i).zfill(2)}-{day}T00:00:00"
                
                elif re.match(r'\d{4}\s+\w+$', dp_date):
                    # "2023 Nov"
                    parts = dp_date.split()
                    year = parts[0]
                    month_str = parts[1][:3]
                    
                    for i, month in enumerate(calendar.month_abbr[1:], 1):
                        if month.lower() == month_str.lower():
                            return f"{year}-{str(i).zfill(2)}-01T00:00:00"
                
                # Just year
                year = self._extract_year(dp_date)
                if year:
                    return f"{year}-01-01T00:00:00"
            except Exception as e:
                logger.warning(f"Failed to parse date '{dp_date}': {e}")
        
        return datetime.now().isoformat()
    
    def _extract_doi(self, record: Dict) -> Optional[str]:
        """Extract DOI from Medline record"""
        # Check AID field
        for aid in record.get('AID', []):
            if aid.lower().endswith('[doi]'):
                return aid.replace(' [doi]', '')
        
        # Check LID field
        lid = record.get('LID', '')
        if '[doi]' in lid:
            return lid.split(' [doi]')[0]
        
        # Check SO field for DOI pattern
        so = record.get('SO', '')
        doi_match = re.search(r'doi:\s*(10\.\d+/[^\s]+)', so, re.IGNORECASE)
        if doi_match:
            return doi_match.group(1)
        
        return None
    
    def fetch_minimal_metadata(self, pmids: List[str], batch_size: int = 100) -> Dict[str, Dict]:
        """
        Fetch minimal metadata (title, year, first author) for a list of PMIDs.
        
        Args:
            pmids: List of PubMed IDs
            batch_size: Batch size for API calls
            
        Returns:
            Dictionary mapping PMIDs to metadata objects
        """
        if not pmids:
            return {}
            
        metadata = {}
        unique_pmids = list(set(pmids))  # Remove duplicates
        
        logger.info(f"Fetching minimal metadata for {len(unique_pmids)} unique PMIDs")
        
        for i in range(0, len(unique_pmids), batch_size):
            batch = unique_pmids[i:i+batch_size]
            
            try:
                # Fetch summary information from PubMed
                handle = Entrez.esummary(db="pubmed", id=",".join(batch), retmode="xml")
                tree = ET.parse(handle)
                root = tree.getroot()
                handle.close()
                
                for doc_sum in root.findall('.//DocSum'):
                    pmid = None
                    title = None
                    year = None
                    first_author = None
                    journal = None
                    
                    # Extract PMID
                    pmid_elem = doc_sum.find('.//Id')
                    if pmid_elem is not None:
                        pmid = pmid_elem.text
                    
                    if not pmid:
                        continue
                    
                    # Extract fields from Item elements
                    for item in doc_sum.findall('.//Item'):
                        name = item.get('Name', '')
                        
                        if name == 'Title' and item.text:
                            title = item.text
                        elif name == 'PubDate' and item.text:
                            # Extract year from publication date
                            pub_date = item.text
                            year_match = re.search(r'(\d{4})', pub_date)
                            if year_match:
                                year = int(year_match.group(1))
                        elif name == 'AuthorList' and item.text:
                            # Get first author
                            authors = item.text.split(',')
                            if authors:
                                first_author = authors[0].strip()
                        elif name == 'Source' and item.text:
                            journal = item.text
                    
                    # Store metadata
                    metadata[pmid] = {
                        'id': pmid,
                        'title': title or f'PMID: {pmid}',
                        'year': year,
                        'first_author': first_author,
                        'journal': journal,
                        'inDatabase': False,  # Will be checked later
                        'externalUrl': f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/'
                    }
                
                time.sleep(self.rate_limit)
                
            except Exception as e:
                logger.error(f"Error fetching metadata for batch: {e}")
                # Create basic metadata for failed items
                for pmid in batch:
                    if pmid not in metadata:
                        metadata[pmid] = {
                            'id': pmid,
                            'title': f'PMID: {pmid}',
                            'year': None,
                            'first_author': None,
                            'journal': None,
                            'inDatabase': False,
                            'externalUrl': f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/'
                        }
        
        logger.info(f"Successfully fetched metadata for {len(metadata)} PMIDs")
        return metadata
    
    def _enrich_citations_with_metadata(self, pmid_list: List[str], metadata_dict: Dict[str, Dict]) -> List[Dict]:
        """
        Convert a list of PMIDs to a list of metadata objects.
        
        Args:
            pmid_list: List of PMID strings
            metadata_dict: Dictionary mapping PMIDs to metadata
            
        Returns:
            List of metadata objects for the PMIDs
        """
        enriched = []
        
        for pmid in pmid_list:
            if pmid in metadata_dict:
                enriched.append(metadata_dict[pmid])
            else:
                # Fallback for PMIDs without metadata
                enriched.append({
                    'id': pmid,
                    'title': f'PMID: {pmid}',
                    'year': None,
                    'first_author': None,
                    'journal': None,
                    'inDatabase': False,
                    'externalUrl': f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/'
                })
        
        return enriched
    
    def _fetch_single_citation(self, pmid: str, base_url: str, max_retries: int = 3,
                                rate_limiter: threading.Semaphore = None) -> tuple:
        """
        Fetch citations for a single PMID with retry logic.
        Thread-safe for use with concurrent.futures.

        Returns:
            (pmid_str, citation_dict, citation_pmid_set)
        """
        params = {
            "dbfrom": "pubmed",
            "db": "pubmed",
            "cmd": "neighbor",
            "id": str(pmid),
            "retmode": "json",
            "tool": "ohdsi-dashboard",
            "email": Entrez.email or "",
        }
        if self.api_key:
            params["api_key"] = self.api_key

        pmid_str = str(pmid)
        found_pmids = set()

        for attempt in range(max_retries):
            try:
                # Rate limit: acquire before each request
                if rate_limiter:
                    rate_limiter.acquire()

                timeout = 5 + (attempt * 3)  # 5s, 8s, 11s
                response = self._session.get(base_url, params=params, timeout=timeout)
                response.raise_for_status()
                data = response.json()

                result = {"cited_by": [], "references": [], "similar": []}

                for linkset in data.get("linksets", []):
                    for linksetdb in linkset.get("linksetdbs", []):
                        link_name = linksetdb.get("linkname", "")
                        links = [str(lid) for lid in linksetdb.get("links", [])]

                        if "pubmed_pubmed_citedin" in link_name:
                            result["cited_by"] = links
                            found_pmids.update(links)
                        elif "pubmed_pubmed_refs" in link_name:
                            result["references"] = links
                            found_pmids.update(links)
                        elif link_name == "pubmed_pubmed":
                            similar = links[:5]
                            result["similar"] = similar
                            found_pmids.update(similar)

                return (pmid_str, result, found_pmids)

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                backoff = (2 ** attempt) + 0.5
                if attempt < max_retries - 1:
                    logger.warning(f"Citation fetch timeout for PMID {pmid} "
                                   f"(attempt {attempt + 1}/{max_retries}), retrying in {backoff:.1f}s")
                    time.sleep(backoff)
                else:
                    logger.error(f"Citation fetch failed for PMID {pmid} after {max_retries} attempts: {e}")

            except Exception as e:
                logger.error(f"Error fetching citations for PMID {pmid}: {e}")
                break

        return (pmid_str, {"cited_by": [], "references": [], "similar": []}, set())

    def fetch_citations(self, pmids: List[str], batch_size: int = 100, fetch_metadata: bool = True) -> Dict:
        """
        Fetch citation information for PMIDs using NCBI ELink with concurrent requests.

        Note: ELink aggregates results when multiple IDs are sent in one request,
        so we query one PMID at a time to get per-article data. Requests are
        parallelized with a thread pool, respecting NCBI rate limits.

        Args:
            pmids: List of PubMed IDs
            batch_size: Ignored (kept for backward compat). Uses 1 PMID per request.
            fetch_metadata: Whether to fetch minimal metadata for citations

        Returns:
            Dictionary mapping PMIDs to citation data with optional metadata
        """
        citations = {}
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"

        # Track all citation PMIDs we need metadata for
        all_citation_pmids = set()

        # Concurrent workers for citation fetching.
        # NCBI tolerates ~3 concurrent connections well with API key.
        # Higher concurrency triggers aggressive throttling/timeouts.
        max_workers = 3 if self.api_key else 1
        rate_limiter = threading.Semaphore(max_workers)

        def release_tokens():
            """Continuously release rate limiter tokens at the allowed rate."""
            interval = 1.0 / (10.0 if self.api_key else 3.0)  # per-request interval
            while not stop_event.is_set():
                time.sleep(interval)
                try:
                    rate_limiter.release()
                except ValueError:
                    pass  # Semaphore already at max

        stop_event = threading.Event()
        token_thread = threading.Thread(target=release_tokens, daemon=True)
        token_thread.start()

        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(
                        self._fetch_single_citation, pmid, base_url, 3, rate_limiter
                    ): pmid for pmid in pmids
                }

                for future in as_completed(futures):
                    pmid_str, result, found = future.result()
                    citations[pmid_str] = result
                    all_citation_pmids.update(found)
        finally:
            stop_event.set()

        # Fetch minimal metadata if requested
        if fetch_metadata and all_citation_pmids:
            logger.info(f"Fetching metadata for {len(all_citation_pmids)} citations")
            metadata = self.fetch_minimal_metadata(list(all_citation_pmids))

            # Convert citation lists to include metadata
            for source_id in citations:
                citations[source_id]["cited_by"] = self._enrich_citations_with_metadata(
                    citations[source_id]["cited_by"], metadata
                )
                citations[source_id]["references"] = self._enrich_citations_with_metadata(
                    citations[source_id]["references"], metadata
                )
                citations[source_id]["similar"] = self._enrich_citations_with_metadata(
                    citations[source_id]["similar"], metadata
                )

        return citations
    
    def articles_to_bibtex(self, articles: List[Dict], output_file: str):
        """
        Convert articles to BibTeX format.
        
        Args:
            articles: List of article dictionaries
            output_file: Path to output BibTeX file
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            for article in articles:
                pmid = article.get('pmid', '')
                
                # Get author string
                authors = article.get('authors', [])
                if authors:
                    author_str = " and ".join([
                        a.get("name", "") if isinstance(a, dict) else str(a)
                        for a in authors
                    ])
                else:
                    author_str = ""
                
                # Extract year
                year = article.get('year', '')
                if not year and article.get('published_date'):
                    year = article['published_date'][:4]
                
                # Write BibTeX entry
                f.write(f"@article{{PMID{pmid},\n")
                f.write(f'  title = {{{article.get("title", "")}}},\n')
                f.write(f'  author = {{{author_str}}},\n')
                f.write(f'  journal = {{{article.get("journal", "")}}},\n')
                f.write(f'  year = {{{year}}},\n')
                
                if article.get('volume'):
                    f.write(f'  volume = {{{article["volume"]}}},\n')
                if article.get('issue'):
                    f.write(f'  number = {{{article["issue"]}}},\n')
                if article.get('pages'):
                    f.write(f'  pages = {{{article["pages"]}}},\n')
                if article.get('doi'):
                    f.write(f'  doi = {{{article["doi"]}}},\n')
                if article.get('abstract'):
                    abstract = article['abstract'].replace('"', "'")
                    f.write(f'  abstract = {{{abstract}}},\n')
                
                f.write(f'  url = {{{article.get("url", "")}}},\n')
                f.write(f'  pmid = {{{pmid}}}\n')
                f.write("}\n\n")
        
        logger.info(f"Saved {len(articles)} articles to {output_file}")


# For backward compatibility
ArticleRetriever = PubMedRetriever