"""
README processor for extracting structured information from repository documentation.
"""

import os
import sys
import re
import logging
from typing import Dict, Any, List, Optional
import markdown
from bs4 import BeautifulSoup

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.ohdsi_constants import OHDSI_TOOLS_DISPLAY

logger = logging.getLogger(__name__)


class ReadmeProcessor:
    """
    Processes README files to extract structured information.
    """
    
    def __init__(self):
        """Initialize README processor."""
        self.markdown_parser = markdown.Markdown(
            extensions=['extra', 'toc', 'tables', 'fenced_code']
        )
    
    def process_readme(self, readme_content: str) -> Dict[str, Any]:
        """
        Process README content to extract structured information.
        
        Args:
            readme_content: Raw README content (markdown)
            
        Returns:
            Structured information extracted from README
        """
        if not readme_content:
            return {}
        
        # Convert markdown to HTML for easier parsing
        html_content = self.markdown_parser.convert(readme_content)
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract sections
        sections = self._extract_sections(soup, readme_content)
        
        # Extract specific information
        extracted = {
            'sections': sections,
            'installation': self._extract_installation(sections, readme_content),
            'usage': self._extract_usage(sections, readme_content),
            'requirements': self._extract_requirements(sections, readme_content),
            'features': self._extract_features(sections, readme_content),
            'badges': self._extract_badges(readme_content),
            'links': self._extract_links(soup),
            'code_blocks': self._extract_code_blocks(soup),
            'tables': self._extract_tables(soup),
            'images': self._extract_images(soup),
            'contact': self._extract_contact_info(readme_content),
            'license_info': self._extract_license_info(sections, readme_content),
            'citations': self._extract_citations(readme_content),
            'ohdsi_specific': self._extract_ohdsi_specific(readme_content)
        }
        
        # Calculate documentation quality
        extracted['doc_quality'] = self._calculate_doc_quality(extracted)
        
        return extracted
    
    def _extract_sections(self, soup: BeautifulSoup, raw_content: str) -> Dict[str, str]:
        """Extract main sections from README."""
        sections = {}
        
        # Try to extract from HTML headers
        current_section = None
        current_content = []
        
        for element in soup.children:
            if element.name in ['h1', 'h2', 'h3']:
                # Save previous section
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                
                # Start new section
                current_section = element.get_text().strip().lower()
                current_content = []
            elif current_section:
                if hasattr(element, 'get_text'):
                    current_content.append(element.get_text().strip())
        
        # Save last section
        if current_section:
            sections[current_section] = '\n'.join(current_content)
        
        # If no sections found, try regex on raw content
        if not sections:
            pattern = r'^#{1,3}\s+(.+?)$'
            matches = re.finditer(pattern, raw_content, re.MULTILINE)
            
            section_positions = []
            for match in matches:
                section_name = match.group(1).strip().lower()
                section_positions.append((section_name, match.start(), match.end()))
            
            for i, (name, start, end) in enumerate(section_positions):
                if i < len(section_positions) - 1:
                    content_end = section_positions[i + 1][1]
                else:
                    content_end = len(raw_content)
                
                content = raw_content[end:content_end].strip()
                sections[name] = content
        
        return sections
    
    def _extract_installation(self, sections: Dict[str, str], raw_content: str) -> Dict[str, Any]:
        """Extract installation instructions."""
        installation = {
            'method': None,
            'commands': [],
            'dependencies': []
        }
        
        # Look for installation section
        install_section = None
        for key in sections:
            if any(word in key for word in ['install', 'setup', 'getting started']):
                install_section = sections[key]
                break
        
        if not install_section:
            install_section = raw_content
        
        # Extract package manager commands
        patterns = {
            'pip': r'pip install[\s\-]+([^\n]+)',
            'npm': r'npm install[\s\-]+([^\n]+)',
            'yarn': r'yarn add[\s\-]+([^\n]+)',
            'conda': r'conda install[\s\-]+([^\n]+)',
            'r': r'install\.packages\(["\']([^"\']+)["\']',
            'devtools': r'devtools::install_github\(["\']([^"\']+)["\']',
            'remotes': r'remotes::install_github\(["\']([^"\']+)["\']'
        }
        
        for method, pattern in patterns.items():
            matches = re.findall(pattern, install_section, re.IGNORECASE)
            if matches:
                installation['method'] = method
                installation['commands'].extend(matches)
        
        # Extract dependencies
        dep_patterns = [
            r'require[sd]?\s*[:\-]?\s*([^\n]+)',
            r'dependenc(?:y|ies)\s*[:\-]?\s*([^\n]+)',
            r'prerequisite[s]?\s*[:\-]?\s*([^\n]+)'
        ]
        
        for pattern in dep_patterns:
            matches = re.findall(pattern, install_section, re.IGNORECASE)
            installation['dependencies'].extend(matches)
        
        return installation
    
    def _extract_usage(self, sections: Dict[str, str], raw_content: str) -> Dict[str, Any]:
        """Extract usage examples."""
        usage = {
            'examples': [],
            'commands': [],
            'api_calls': []
        }
        
        # Look for usage section
        usage_section = None
        for key in sections:
            if any(word in key for word in ['usage', 'example', 'how to', 'quick start']):
                usage_section = sections[key]
                break
        
        if not usage_section:
            usage_section = raw_content[:5000]  # Check first 5KB
        
        # Extract code blocks that look like usage examples
        code_blocks = re.findall(r'```(?:[\w]+)?\n(.*?)\n```', usage_section, re.DOTALL)
        usage['examples'] = code_blocks[:5]  # Limit to 5 examples
        
        # Extract command line usage
        cli_patterns = [
            r'^\$\s+(.+)$',
            r'^>\s+(.+)$',
            r'python\s+(\S+\.py[^\n]*)',
            r'Rscript\s+(\S+\.R[^\n]*)'
        ]
        
        for pattern in cli_patterns:
            matches = re.findall(pattern, usage_section, re.MULTILINE)
            usage['commands'].extend(matches)
        
        # Extract API/function calls
        api_patterns = [
            r'(\w+)\([^\)]*\)',  # Function calls
            r'(\w+)\.(\w+)\([^\)]*\)',  # Method calls
        ]
        
        for pattern in api_patterns[:1]:  # Limit to avoid too many matches
            matches = re.findall(pattern, usage_section)
            usage['api_calls'].extend(matches[:10])  # Limit to 10
        
        return usage
    
    def _extract_requirements(self, sections: Dict[str, str], raw_content: str) -> List[str]:
        """Extract requirements/dependencies."""
        requirements = []
        
        # Look for requirements section
        req_section = None
        for key in sections:
            if any(word in key for word in ['requirement', 'dependenc', 'prerequisite']):
                req_section = sections[key]
                break
        
        # Also check for requirements.txt content
        req_file_pattern = r'requirements\.txt.*?\n((?:.*\n){1,20})'
        req_file_matches = re.findall(req_file_pattern, raw_content, re.IGNORECASE)
        
        if req_file_matches:
            for match in req_file_matches:
                lines = match.strip().split('\n')
                requirements.extend([l.strip() for l in lines if l.strip() and not l.startswith('#')])
        
        # Check for package.json dependencies
        package_pattern = r'"dependencies":\s*{([^}]+)}'
        package_matches = re.findall(package_pattern, raw_content)
        if package_matches:
            deps = package_matches[0]
            dep_pattern = r'"([^"]+)":\s*"[^"]+"'
            requirements.extend(re.findall(dep_pattern, deps))
        
        # Check for R package dependencies
        r_deps_pattern = r'Imports:\s*([^\n]+(?:\n\s+[^\n]+)*)'
        r_deps_matches = re.findall(r_deps_pattern, raw_content)
        if r_deps_matches:
            deps = r_deps_matches[0].replace('\n', ' ').replace(',', ' ')
            requirements.extend(deps.split())
        
        return list(set(requirements))  # Remove duplicates
    
    def _extract_features(self, sections: Dict[str, str], raw_content: str) -> List[str]:
        """Extract key features."""
        features = []
        
        # Look for features section
        feature_section = None
        for key in sections:
            if any(word in key for word in ['feature', 'capability', 'functionality']):
                feature_section = sections[key]
                break
        
        if not feature_section:
            feature_section = raw_content[:3000]
        
        # Extract bullet points
        bullet_patterns = [
            r'^\s*[\*\-\+]\s+(.+)$',
            r'^\s*\d+\.\s+(.+)$'
        ]
        
        for pattern in bullet_patterns:
            matches = re.findall(pattern, feature_section, re.MULTILINE)
            features.extend(matches[:20])  # Limit to 20 features
        
        return features
    
    def _extract_badges(self, content: str) -> List[Dict[str, str]]:
        """Extract badges (shields.io, travis-ci, etc.)."""
        badges = []
        
        # Common badge patterns
        badge_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        matches = re.findall(badge_pattern, content[:2000])  # Usually at the top
        
        for alt_text, url in matches:
            if any(domain in url for domain in ['shields.io', 'travis-ci', 'codecov', 'github.com/.*badge']):
                badges.append({
                    'alt': alt_text,
                    'url': url,
                    'type': self._identify_badge_type(url)
                })
        
        return badges
    
    def _identify_badge_type(self, url: str) -> str:
        """Identify badge type from URL."""
        if 'build' in url or 'travis' in url or 'ci' in url:
            return 'build'
        elif 'coverage' in url or 'codecov' in url:
            return 'coverage'
        elif 'version' in url or 'release' in url:
            return 'version'
        elif 'license' in url:
            return 'license'
        elif 'downloads' in url:
            return 'downloads'
        else:
            return 'other'
    
    def _extract_links(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract important links."""
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text().strip()
            
            if text and href and not href.startswith('#'):
                # Categorize link
                link_type = 'other'
                if 'documentation' in text.lower() or 'docs' in text.lower():
                    link_type = 'documentation'
                elif 'demo' in text.lower() or 'example' in text.lower():
                    link_type = 'demo'
                elif 'paper' in text.lower() or 'publication' in text.lower():
                    link_type = 'publication'
                elif 'ohdsi' in href.lower():
                    link_type = 'ohdsi'
                
                links.append({
                    'text': text[:100],  # Limit text length
                    'url': href,
                    'type': link_type
                })
        
        return links[:30]  # Limit to 30 links
    
    def _extract_code_blocks(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract code blocks with language info."""
        code_blocks = []
        
        for code in soup.find_all('code'):
            parent = code.parent
            if parent and parent.name == 'pre':
                language = 'unknown'
                # Try to detect language from class
                if parent.get('class'):
                    for cls in parent['class']:
                        if 'language-' in cls:
                            language = cls.replace('language-', '')
                            break
                
                code_blocks.append({
                    'language': language,
                    'content': code.get_text()[:500]  # Limit size
                })
        
        return code_blocks[:10]  # Limit to 10 code blocks
    
    def _extract_tables(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract tables from README."""
        tables = []
        
        for table in soup.find_all('table'):
            table_data = {
                'headers': [],
                'rows': []
            }
            
            # Extract headers
            thead = table.find('thead')
            if thead:
                for th in thead.find_all('th'):
                    table_data['headers'].append(th.get_text().strip())
            
            # Extract rows
            tbody = table.find('tbody')
            if tbody:
                for tr in tbody.find_all('tr')[:20]:  # Limit rows
                    row = []
                    for td in tr.find_all('td'):
                        row.append(td.get_text().strip())
                    table_data['rows'].append(row)
            
            if table_data['headers'] or table_data['rows']:
                tables.append(table_data)
        
        return tables[:5]  # Limit to 5 tables
    
    def _extract_images(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract images from README."""
        images = []
        
        for img in soup.find_all('img'):
            images.append({
                'src': img.get('src', ''),
                'alt': img.get('alt', ''),
                'title': img.get('title', '')
            })
        
        return images[:10]  # Limit to 10 images
    
    def _extract_contact_info(self, content: str) -> Dict[str, List[str]]:
        """Extract contact information."""
        contact = {
            'emails': [],
            'urls': [],
            'twitter': [],
            'github': []
        }
        
        # Extract emails
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        contact['emails'] = list(set(re.findall(email_pattern, content)))[:5]
        
        # Extract Twitter handles
        twitter_pattern = r'@[\w]+'
        contact['twitter'] = list(set(re.findall(twitter_pattern, content)))[:5]
        
        # Extract GitHub usernames/repos
        github_pattern = r'github\.com/([^/\s]+)(?:/([^/\s]+))?'
        github_matches = re.findall(github_pattern, content)
        for user, repo in github_matches[:5]:
            if repo:
                contact['github'].append(f"{user}/{repo}")
            else:
                contact['github'].append(user)
        
        return contact
    
    def _extract_license_info(self, sections: Dict[str, str], raw_content: str) -> Dict[str, str]:
        """Extract license information."""
        license_info = {
            'type': None,
            'text': None
        }
        
        # Look for license section
        for key in sections:
            if 'license' in key:
                license_info['text'] = sections[key][:500]
                break
        
        # Identify license type
        licenses = {
            'MIT': r'MIT License',
            'Apache 2.0': r'Apache License,? Version 2\.0',
            'GPL-3.0': r'GNU General Public License v3\.0',
            'BSD': r'BSD \d-Clause',
            'LGPL': r'GNU Lesser General Public License'
        }
        
        for license_type, pattern in licenses.items():
            if re.search(pattern, raw_content, re.IGNORECASE):
                license_info['type'] = license_type
                break
        
        return license_info
    
    def _extract_citations(self, content: str) -> List[str]:
        """Extract citations and references."""
        citations = []
        
        # Look for DOI patterns
        doi_pattern = r'10\.\d{4,}/[-._;()/:\w]+'
        citations.extend([f"DOI: {doi}" for doi in re.findall(doi_pattern, content)])
        
        # Look for PubMed IDs
        pmid_pattern = r'PMID:?\s*(\d+)'
        citations.extend([f"PMID: {pmid}" for pmid in re.findall(pmid_pattern, content, re.IGNORECASE)])
        
        # Look for arXiv papers
        arxiv_pattern = r'arXiv:(\d{4}\.\d{4,5})'
        citations.extend([f"arXiv: {arxiv}" for arxiv in re.findall(arxiv_pattern, content)])
        
        return citations[:10]  # Limit to 10 citations
    
    def _extract_ohdsi_specific(self, content: str) -> Dict[str, Any]:
        """Extract OHDSI-specific information."""
        ohdsi = {
            'mentions': [],
            'tools': [],
            'cdm_version': None,
            'study_info': {}
        }
        
        # OHDSI tool mentions
        for tool in OHDSI_TOOLS_DISPLAY:
            if re.search(r'\b' + tool + r'\b', content, re.IGNORECASE):
                ohdsi['tools'].append(tool)
        
        # CDM version
        cdm_pattern = r'CDM\s*v?(\d+(?:\.\d+)?)'
        cdm_match = re.search(cdm_pattern, content, re.IGNORECASE)
        if cdm_match:
            ohdsi['cdm_version'] = cdm_match.group(1)
        
        # Study protocol info
        if 'study protocol' in content.lower():
            ohdsi['study_info']['has_protocol'] = True
        
        if 'cohort definition' in content.lower():
            ohdsi['study_info']['has_cohorts'] = True
        
        if 'concept set' in content.lower():
            ohdsi['study_info']['has_concepts'] = True
        
        return ohdsi
    
    def _calculate_doc_quality(self, extracted: Dict[str, Any]) -> float:
        """Calculate documentation quality score."""
        score = 0.0
        
        # Check for important sections
        if extracted.get('sections'):
            important_sections = ['installation', 'usage', 'example', 'license', 'contributing']
            for section in important_sections:
                if any(section in key for key in extracted['sections'].keys()):
                    score += 0.1
        
        # Check for installation instructions
        if extracted.get('installation', {}).get('commands'):
            score += 0.15
        
        # Check for usage examples
        if extracted.get('usage', {}).get('examples'):
            score += 0.15
        
        # Check for requirements
        if extracted.get('requirements'):
            score += 0.1
        
        # Check for badges (indicates maintenance)
        if extracted.get('badges'):
            score += 0.05 * min(len(extracted['badges']), 3)
        
        # Check for OHDSI-specific content
        if extracted.get('ohdsi_specific', {}).get('tools'):
            score += 0.1
        
        # Check for contact info
        if extracted.get('contact', {}).get('emails') or extracted.get('contact', {}).get('github'):
            score += 0.05
        
        # Check for license
        if extracted.get('license_info', {}).get('type'):
            score += 0.1
        
        return min(1.0, score)