"""
Wiki and documentation scraper for OHDSI documentation sites.
Scrapes and processes documentation from various OHDSI resources.
"""

import os
import re
import logging
import requests
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
import json
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import hashlib

# Add parent directory to path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.base_fetcher import BaseFetcher
from shared.content_relevance import is_ohdsi_related as _is_ohdsi_related_check

logger = logging.getLogger(__name__)


class WikiScraper(BaseFetcher):
    """
    Scrapes documentation from OHDSI wiki and documentation sites.
    """
    
    # OHDSI Documentation Sources
    DOCUMENTATION_SOURCES = [
        {
            'name': 'OHDSI Wiki',
            'base_url': 'https://www.ohdsi.org/web/wiki/doku.php',
            'type': 'dokuwiki',
            'sections': [
                'welcome',
                'projects',
                'data_standardization',
                'methods',
                'tools',
                'studies',
                'education'
            ]
        },
        {
            'name': 'The Book of OHDSI',
            'base_url': 'https://ohdsi.github.io/TheBookOfOhdsi/',
            'type': 'gitbook',
            'sections': [
                'OhdsiAnalyticsTools',
                'CommonDataModel',
                'StandardizedVocabularies',
                'DataQuality',
                'Cohorts',
                'Characterization',
                'PopulationLevelEstimation',
                'PatientLevelPrediction',
                'EvidenceQuality'
            ]
        },
        {
            'name': 'HADES Documentation',
            'base_url': 'https://ohdsi.github.io/Hades/',
            'type': 'static',
            'sections': [
                'rSetup',
                'packageStatuses',
                'installingHades'
            ]
        },
        {
            'name': 'Atlas Documentation',
            'base_url': 'https://github.com/OHDSI/Atlas/wiki',
            'type': 'github_wiki',
            'sections': []
        },
        {
            'name': 'CDM Documentation',
            'base_url': 'https://ohdsi.github.io/CommonDataModel/',
            'type': 'static',
            'sections': [
                'cdm54',
                'cdm60',
                'glossary',
                'faq'
            ]
        }
    ]
    
    # Documentation patterns to identify important pages
    DOC_PATTERNS = {
        'tutorial': r'tutorial|guide|how[-\s]?to|getting[-\s]?started|quickstart',
        'api': r'api|reference|specification|interface',
        'installation': r'install|setup|configuration|deploy',
        'concept': r'concept|overview|introduction|about',
        'faq': r'faq|frequently[-\s]?asked|questions',
        'troubleshooting': r'troubleshoot|debug|error|issue|problem',
        'example': r'example|sample|demo|use[-\s]?case',
        'best_practice': r'best[-\s]?practice|recommendation|guideline'
    }
    
    def __init__(self):
        """
        Initialize Wiki scraper.
        """
        super().__init__(
            source_name='wiki',
            rate_limit=1.0,  # 1 request per second to be respectful
            cache_ttl=3600 * 24  # Cache for 24 hours (documentation doesn't change often)
        )
        
        # Setup session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'OHDSI-Dashboard/1.0 (Documentation Scraper)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        })
        
        # Track visited URLs to avoid duplicates
        self.visited_urls = set()
        
        # Track scraped content
        self.scraped_pages = []
    
    def fetch_all_documentation(self, max_pages_per_source: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch documentation from all configured sources.
        
        Args:
            max_pages_per_source: Maximum pages to scrape per source
            
        Returns:
            List of documentation pages
        """
        all_docs = []
        
        for source in self.DOCUMENTATION_SOURCES:
            try:
                logger.info(f"Scraping documentation from {source['name']}")
                
                if source['type'] == 'dokuwiki':
                    docs = self._scrape_dokuwiki(source, max_pages_per_source)
                elif source['type'] == 'gitbook':
                    docs = self._scrape_gitbook(source, max_pages_per_source)
                elif source['type'] == 'static':
                    docs = self._scrape_static_site(source, max_pages_per_source)
                elif source['type'] == 'github_wiki':
                    docs = self._scrape_github_wiki(source, max_pages_per_source)
                else:
                    logger.warning(f"Unknown documentation type: {source['type']}")
                    continue
                
                all_docs.extend(docs)
                logger.info(f"Scraped {len(docs)} pages from {source['name']}")
                
            except Exception as e:
                logger.error(f"Error scraping {source['name']}: {e}")
        
        # Remove duplicates based on URL
        unique_docs = {}
        for doc in all_docs:
            url = doc.get('url')
            if url and url not in unique_docs:
                unique_docs[url] = doc
        
        return list(unique_docs.values())
    
    def _scrape_dokuwiki(self, source: Dict[str, Any], max_pages: int) -> List[Dict[str, Any]]:
        """
        Scrape DokuWiki documentation.
        
        Args:
            source: Source configuration
            max_pages: Maximum pages to scrape
            
        Returns:
            List of documentation pages
        """
        pages = []
        base_url = source['base_url']
        
        # Scrape main sections
        for section in source.get('sections', []):
            if len(pages) >= max_pages:
                break
            
            try:
                section_url = f"{base_url}?id={section}"
                
                # Skip if already visited
                if section_url in self.visited_urls:
                    continue
                self.visited_urls.add(section_url)
                
                # Fetch page
                response = self.session.get(section_url)
                response.raise_for_status()
                
                # Parse page
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract content
                content_div = soup.find('div', class_='page')
                if not content_div:
                    content_div = soup.find('div', id='content')
                
                if content_div:
                    page_data = self._extract_page_content(
                        soup, section_url, source['name'], section
                    )
                    if page_data:
                        pages.append(page_data)
                    
                    # Find sub-pages
                    links = content_div.find_all('a', href=True)
                    for link in links[:20]:  # Limit sub-pages
                        if len(pages) >= max_pages:
                            break
                        
                        href = link['href']
                        if 'doku.php?id=' in href:
                            sub_url = urljoin(section_url, href)
                            if sub_url not in self.visited_urls:
                                sub_page = self._fetch_single_page(
                                    sub_url, source['name'], section
                                )
                                if sub_page:
                                    pages.append(sub_page)
                
                # Rate limiting
                self._enforce_rate_limit()
                
            except Exception as e:
                logger.error(f"Error scraping DokuWiki section {section}: {e}")
        
        return pages
    
    def _scrape_gitbook(self, source: Dict[str, Any], max_pages: int) -> List[Dict[str, Any]]:
        """
        Scrape GitBook documentation.
        
        Args:
            source: Source configuration
            max_pages: Maximum pages to scrape
            
        Returns:
            List of documentation pages
        """
        pages = []
        base_url = source['base_url']
        
        # First, try to get the summary/TOC
        try:
            toc_url = urljoin(base_url, 'SUMMARY.md')
            response = self.session.get(toc_url)
            
            if response.status_code == 200:
                # Parse TOC to find pages
                toc_pages = self._parse_gitbook_toc(response.text, base_url)
                
                for page_url in toc_pages[:max_pages]:
                    if page_url not in self.visited_urls:
                        page = self._fetch_single_page(
                            page_url, source['name'], 'main'
                        )
                        if page:
                            pages.append(page)
                            
                            if len(pages) >= max_pages:
                                break
            else:
                # Fallback to scraping sections
                for section in source.get('sections', []):
                    if len(pages) >= max_pages:
                        break
                    
                    section_url = urljoin(base_url, f"{section}.html")
                    if section_url not in self.visited_urls:
                        page = self._fetch_single_page(
                            section_url, source['name'], section
                        )
                        if page:
                            pages.append(page)
            
        except Exception as e:
            logger.error(f"Error scraping GitBook: {e}")
        
        return pages
    
    def _scrape_static_site(self, source: Dict[str, Any], max_pages: int) -> List[Dict[str, Any]]:
        """
        Scrape static documentation site.
        
        Args:
            source: Source configuration
            max_pages: Maximum pages to scrape
            
        Returns:
            List of documentation pages
        """
        pages = []
        base_url = source['base_url']
        
        # First try index page
        index_url = base_url
        if index_url not in self.visited_urls:
            index_page = self._fetch_single_page(
                index_url, source['name'], 'index'
            )
            if index_page:
                pages.append(index_page)
        
        # Then scrape configured sections
        for section in source.get('sections', []):
            if len(pages) >= max_pages:
                break
            
            # Try different URL patterns
            section_urls = [
                urljoin(base_url, f"{section}.html"),
                urljoin(base_url, f"{section}/"),
                urljoin(base_url, f"{section}/index.html"),
                urljoin(base_url, section)
            ]
            
            for section_url in section_urls:
                if section_url not in self.visited_urls:
                    page = self._fetch_single_page(
                        section_url, source['name'], section
                    )
                    if page:
                        pages.append(page)
                        break  # Found the section, move to next
        
        return pages
    
    def _scrape_github_wiki(self, source: Dict[str, Any], max_pages: int) -> List[Dict[str, Any]]:
        """
        Scrape GitHub Wiki pages.
        
        Args:
            source: Source configuration
            max_pages: Maximum pages to scrape
            
        Returns:
            List of documentation pages
        """
        pages = []
        base_url = source['base_url']
        
        try:
            # Get the wiki home page
            response = self.session.get(base_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find wiki pages sidebar
            sidebar = soup.find('div', class_='wiki-rightbar') or \
                     soup.find('div', class_='wiki-sidebar')
            
            if sidebar:
                links = sidebar.find_all('a', href=True)
                
                for link in links[:max_pages]:
                    href = link['href']
                    if '/wiki/' in href:
                        page_url = urljoin('https://github.com', href)
                        
                        if page_url not in self.visited_urls:
                            page = self._fetch_single_page(
                                page_url, source['name'], 'wiki'
                            )
                            if page:
                                pages.append(page)
                                
                                if len(pages) >= max_pages:
                                    break
            else:
                # Fallback: scrape the main page
                main_page = self._fetch_single_page(
                    base_url, source['name'], 'wiki'
                )
                if main_page:
                    pages.append(main_page)
            
        except Exception as e:
            logger.error(f"Error scraping GitHub Wiki: {e}")
        
        return pages
    
    def _fetch_single_page(self, url: str, source_name: str, 
                          section: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a single documentation page.
        
        Args:
            url: Page URL
            source_name: Name of documentation source
            section: Section name
            
        Returns:
            Page data or None
        """
        if url in self.visited_urls:
            return None
        
        self.visited_urls.add(url)
        
        try:
            # Rate limiting
            self._enforce_rate_limit()
            
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            return self._extract_page_content(soup, url, source_name, section)
            
        except Exception as e:
            logger.debug(f"Error fetching page {url}: {e}")
            return None
    
    def _extract_page_content(self, soup: BeautifulSoup, url: str, 
                            source_name: str, section: str) -> Optional[Dict[str, Any]]:
        """
        Extract content from a documentation page.
        
        Args:
            soup: BeautifulSoup object
            url: Page URL
            source_name: Documentation source name
            section: Section name
            
        Returns:
            Extracted page data
        """
        try:
            # Extract title
            title = None
            title_elem = soup.find('h1') or soup.find('title')
            if title_elem:
                title = title_elem.get_text().strip()
            
            if not title:
                title = section.replace('_', ' ').title()
            
            # Extract main content
            content = ""
            
            # Try different content containers
            content_selectors = [
                'div.markdown-body',  # GitHub
                'div.content',        # Generic
                'div.page',          # DokuWiki
                'main',              # Semantic HTML
                'article',           # Semantic HTML
                'div#content',       # Generic ID
                'div.documentation', # Generic class
                'div.wiki-content'   # Wiki
            ]
            
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    content = content_elem.get_text(separator='\n', strip=True)
                    break
            
            # Fallback to body
            if not content:
                body = soup.find('body')
                if body:
                    content = body.get_text(separator='\n', strip=True)
            
            # Extract metadata
            description = ""
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                description = meta_desc.get('content', '')
            
            # Extract headings for structure
            headings = []
            for heading in soup.find_all(['h1', 'h2', 'h3'])[:20]:
                headings.append({
                    'level': int(heading.name[1]),
                    'text': heading.get_text().strip()
                })
            
            # Extract code blocks
            code_blocks = []
            for code in soup.find_all(['pre', 'code'])[:10]:
                code_text = code.get_text().strip()
                if len(code_text) > 50:  # Meaningful code block
                    language = 'unknown'
                    # Try to detect language from class
                    if code.get('class'):
                        for cls in code['class']:
                            if 'language-' in cls:
                                language = cls.replace('language-', '')
                                break
                    
                    code_blocks.append({
                        'language': language,
                        'content': code_text[:1000]  # Limit size
                    })
            
            # Extract links
            links = []
            for link in soup.find_all('a', href=True)[:30]:
                link_text = link.get_text().strip()
                if link_text and len(link_text) > 3:
                    links.append({
                        'text': link_text[:100],
                        'url': urljoin(url, link['href'])
                    })
            
            # Determine documentation type
            doc_type = self._classify_documentation(title, content, url)
            
            # Generate unique ID
            doc_id = hashlib.md5(url.encode()).hexdigest()
            
            # Check if OHDSI-related
            is_ohdsi = self._is_ohdsi_related(title, content)
            
            return {
                'doc_id': doc_id,
                'url': url,
                'title': title[:200],  # Limit title length
                'description': description[:500],
                'content': content[:10000],  # Limit content size
                'source_name': source_name,
                'section': section,
                'doc_type': doc_type,
                'headings': headings,
                'code_blocks': code_blocks,
                'links': links[:20],  # Limit links
                'word_count': len(content.split()),
                'has_code': len(code_blocks) > 0,
                'is_ohdsi': is_ohdsi,
                'scraped_at': datetime.now().isoformat(),
                'content_type': 'documentation',
                'source': 'wiki'
            }
            
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {e}")
            return None
    
    def _parse_gitbook_toc(self, toc_content: str, base_url: str) -> List[str]:
        """
        Parse GitBook table of contents.
        
        Args:
            toc_content: TOC markdown content
            base_url: Base URL for resolving relative links
            
        Returns:
            List of page URLs
        """
        urls = []
        
        # Extract markdown links
        link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
        matches = re.findall(link_pattern, toc_content)
        
        for text, href in matches:
            if not href.startswith('http'):
                # Convert .md to .html
                if href.endswith('.md'):
                    href = href[:-3] + '.html'
                page_url = urljoin(base_url, href)
            else:
                page_url = href
            
            urls.append(page_url)
        
        return urls
    
    def _classify_documentation(self, title: str, content: str, url: str) -> str:
        """
        Classify the type of documentation.
        
        Args:
            title: Page title
            content: Page content
            url: Page URL
            
        Returns:
            Documentation type
        """
        combined_text = f"{title} {url} {content[:1000]}".lower()
        
        for doc_type, pattern in self.DOC_PATTERNS.items():
            if re.search(pattern, combined_text):
                return doc_type
        
        # Default classifications based on URL
        if 'api' in url.lower():
            return 'api'
        elif 'tutorial' in url.lower() or 'guide' in url.lower():
            return 'tutorial'
        elif 'install' in url.lower():
            return 'installation'
        
        return 'reference'  # Default
    
    def _is_ohdsi_related(self, title: str, content: str) -> bool:
        """
        Check if documentation is OHDSI-related.

        Args:
            title: Page title
            content: Page content

        Returns:
            True if OHDSI-related
        """
        combined_text = f"{title} {content[:2000]}"
        return _is_ohdsi_related_check(combined_text)
    
    def fetch_ohdsi_documentation(self, max_pages: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch OHDSI-specific documentation.
        
        Args:
            max_pages: Maximum pages to fetch
            
        Returns:
            List of OHDSI documentation pages
        """
        all_docs = self.fetch_all_documentation(max_pages_per_source=max_pages // len(self.DOCUMENTATION_SOURCES))
        
        # Filter for OHDSI-related content
        ohdsi_docs = [doc for doc in all_docs if doc.get('is_ohdsi', False)]
        
        # Sort by relevance (prioritize certain doc types)
        priority_order = ['tutorial', 'installation', 'concept', 'api', 'example', 'reference']
        
        def sort_key(doc):
            doc_type = doc.get('doc_type', 'reference')
            try:
                return priority_order.index(doc_type)
            except ValueError:
                return len(priority_order)
        
        ohdsi_docs.sort(key=sort_key)
        
        logger.info(f"Found {len(ohdsi_docs)} OHDSI-related documentation pages")
        
        return ohdsi_docs[:max_pages]
    
    def analyze_documentation_quality(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze documentation quality metrics.
        
        Args:
            doc: Documentation page data
            
        Returns:
            Quality metrics
        """
        quality = {
            'completeness_score': 0.0,
            'structure_score': 0.0,
            'code_score': 0.0,
            'overall_score': 0.0
        }
        
        # Completeness score
        if doc.get('title'):
            quality['completeness_score'] += 0.2
        if doc.get('description'):
            quality['completeness_score'] += 0.1
        if doc.get('word_count', 0) > 500:
            quality['completeness_score'] += 0.3
        elif doc.get('word_count', 0) > 200:
            quality['completeness_score'] += 0.15
        if doc.get('links'):
            quality['completeness_score'] += 0.1
        
        # Structure score
        headings = doc.get('headings', [])
        if len(headings) > 5:
            quality['structure_score'] += 0.3
        elif len(headings) > 2:
            quality['structure_score'] += 0.15
        
        # Check for good heading hierarchy
        if headings:
            has_h1 = any(h['level'] == 1 for h in headings)
            has_h2 = any(h['level'] == 2 for h in headings)
            if has_h1 and has_h2:
                quality['structure_score'] += 0.2
        
        # Code score
        code_blocks = doc.get('code_blocks', [])
        if len(code_blocks) > 3:
            quality['code_score'] += 0.3
        elif len(code_blocks) > 0:
            quality['code_score'] += 0.15
        
        # Check for language specification in code blocks
        if code_blocks:
            specified_langs = sum(1 for cb in code_blocks if cb['language'] != 'unknown')
            if specified_langs > 0:
                quality['code_score'] += 0.2
        
        # Documentation type bonus
        doc_type = doc.get('doc_type')
        if doc_type in ['tutorial', 'example', 'installation']:
            quality['completeness_score'] += 0.2
        
        # Calculate overall score
        quality['overall_score'] = (
            quality['completeness_score'] * 0.4 +
            quality['structure_score'] * 0.3 +
            quality['code_score'] * 0.3
        )
        
        return quality
    
    def _fetch_single(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Implementation of abstract method from BaseFetcher.
        
        Args:
            query: Query parameters
            
        Returns:
            List of documentation pages
        """
        query_type = query.get('type', 'all')
        
        if query_type == 'all':
            return self.fetch_all_documentation(
                max_pages_per_source=query.get('max_pages', 50)
            )
        
        elif query_type == 'ohdsi':
            return self.fetch_ohdsi_documentation(
                max_pages=query.get('max_pages', 100)
            )
        
        elif query_type == 'source':
            source_name = query.get('source_name')
            for source in self.DOCUMENTATION_SOURCES:
                if source['name'] == source_name:
                    if source['type'] == 'dokuwiki':
                        return self._scrape_dokuwiki(source, query.get('max_pages', 50))
                    elif source['type'] == 'gitbook':
                        return self._scrape_gitbook(source, query.get('max_pages', 50))
                    elif source['type'] == 'static':
                        return self._scrape_static_site(source, query.get('max_pages', 50))
                    elif source['type'] == 'github_wiki':
                        return self._scrape_github_wiki(source, query.get('max_pages', 50))
            return []
        
        else:
            logger.warning(f"Unknown query type: {query_type}")
            return []
    
    def search(self, query: str, max_results: int = 100, 
              filters: Dict[str, Any] = None) -> List[str]:
        """
        Search for documentation page IDs matching the query.
        
        Args:
            query: Search query string
            max_results: Maximum number of results
            filters: Additional filters
            
        Returns:
            List of page URLs as IDs
        """
        # For wiki/documentation, we return URLs as IDs since they're unique
        all_docs = self.fetch_ohdsi_documentation(max_pages=max_results)
        
        # Filter by query
        matching_docs = []
        query_lower = query.lower()
        for doc in all_docs:
            if (query_lower in doc.get('title', '').lower() or 
                query_lower in doc.get('content', '').lower()[:500]):
                matching_docs.append(doc.get('url', ''))
        
        return matching_docs[:max_results]
    
    def fetch_details(self, content_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch detailed information for documentation URLs.
        
        Args:
            content_ids: List of page URLs
            
        Returns:
            List of page details
        """
        results = []
        for url in content_ids:
            # Try to fetch the page directly
            for source in self.DOCUMENTATION_SOURCES:
                if source['base_url'] in url:
                    try:
                        page = self._fetch_single_page(url, source['name'], source['type'])
                        if page:
                            results.append(page)
                            break
                    except Exception as e:
                        logger.error(f"Error fetching page {url}: {e}")
        return results