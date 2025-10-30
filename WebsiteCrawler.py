import os
import sys
import time
import json
import re
import tempfile
import shutil
import base64
import PyPDF2

from urllib.parse import urljoin, urlparse
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader

from tqdm import tqdm


class WebsitePDFCrawler:
    def __init__(self, base_url, output_file="website.pdf", max_pages=50, headless=True, 
                 generate_index=False, include_patterns=None, exclude_patterns=None, 
                 max_depth=None, resume=False, state_file="crawler_state.json"):
        self.base_url = base_url.rstrip('/')
        self.domain = urlparse(base_url).netloc
        self.output_file = output_file
        self.max_pages = max_pages
        self.headless = headless
        self.generate_index = generate_index
        self.include_patterns = include_patterns or []
        self.exclude_patterns = exclude_patterns or []
        self.max_depth = max_depth
        self.resume = resume
        self.state_file = state_file
        
        self.visited_urls = set()
        self.urls_to_visit = []
        self.pdf_files = []
        self.page_info = []
        self.temp_dir = None
        self.driver = None
        
    def setup_driver(self):
        """Setup Firefox WebDriver with proper options"""
        options = Options()
        if self.headless:
            options.add_argument("--headless")
        
        # Optimize for PDF generation
        options.add_argument("--width=1200")
        options.add_argument("--height=800")
        options.set_preference("print.always_print_silent", True)
        options.set_preference("print.show_print_progress", False)
        
        # Set geckodriver path
        geckodriver_path = self.get_geckodriver_path()
        
        try:
            service = FirefoxService(executable_path=geckodriver_path)
            self.driver = webdriver.Firefox(service=service, options=options)
            self.driver.set_window_size(1200, 800)
            print("✓ Firefox driver initialized successfully")
        except WebDriverException as e:
            print(f"✗ Error initializing Firefox driver: {e}")
            print(f"Make sure geckodriver is available at: {geckodriver_path}")
            sys.exit(1)
    
    def get_geckodriver_path(self):
        """Get the path to geckodriver, checking project directory first"""
        script_dir = Path(__file__).parent
        local_geckodriver = script_dir / "drivers" / "geckodriver"
        
        if local_geckodriver.exists():
            return str(local_geckodriver)
    
        system_geckodriver = shutil.which("geckodriver")
        if system_geckodriver:
            return system_geckodriver
        
        return str(local_geckodriver)
    
    def is_same_domain(self, url):
        """Check if URL belongs to the same domain"""
        return urlparse(url).netloc == self.domain
    
    def _get_url_depth(self, url):
        """Calculate URL depth from base URL"""
        base_path = urlparse(self.base_url).path.rstrip('/').split('/')
        url_path = urlparse(url).path.rstrip('/').split('/')
        return len(url_path) - len(base_path)
    
    def _matches_patterns(self, url):
        """Check if URL matches include/exclude patterns"""
        # If include patterns specified, URL must match at least one
        if self.include_patterns:
            if not any(re.search(pattern, url) for pattern in self.include_patterns):
                return False
        
        # If exclude patterns specified, URL must not match any
        if self.exclude_patterns:
            if any(re.search(pattern, url) for pattern in self.exclude_patterns):
                return False
        
        return True
    
    def get_page_title(self):
        """Extract page title from current page"""
        try:
            title = self.driver.title
            if title and title.strip():
                return title.strip()
            
            h1_elements = self.driver.find_elements(By.TAG_NAME, "h1")
            if h1_elements:
                return h1_elements[0].text.strip()
            
            return self.driver.current_url
            
        except Exception as e:
            return self.driver.current_url
    
    def get_page_links(self, current_url):
        """Extract all links from the current page"""
        links = []
        try:
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        
            anchor_elements = self.driver.find_elements(By.TAG_NAME, "a")
        
            for anchor in anchor_elements:
                href = anchor.get_attribute("href")
                if href:
                    full_url = urljoin(current_url, href)
                    full_url = full_url.split('#')[0].rstrip('/')
                
                    if (full_url.startswith(('http://', 'https://')) and
                        self.is_same_domain(full_url) and
                        full_url not in self.visited_urls and
                        full_url not in links and
                        not self._should_skip_url(full_url) and
                        self._matches_patterns(full_url) and
                        (self.max_depth is None or self._get_url_depth(full_url) <= self.max_depth)):
                        links.append(full_url)
    
        except Exception as e:
            print(f"Warning: Error extracting links from {current_url}: {e}")
    
        return links

    def _should_skip_url(self, url):
        """Skip URLs that typically cause issues"""
        skip_patterns = [
            '.pdf', '.doc', '.zip', '.exe', '.jpg', '.png', '.gif',
            'mailto:', 'tel:', 'javascript:',
            '/search?', '/login', '/logout', '/register'
        ]
        return any(pattern in url.lower() for pattern in skip_patterns)
    
    def save_page_as_pdf(self, url, filename):
        """Save current page as PDF using Firefox's print function"""
        try:
            self.driver.get(url)
            
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))   
            )
            time.sleep(5)
            
            pdf_data = self.driver.print_page()
            
            with open(filename, "wb") as f:
                f.write(base64.b64decode(pdf_data))
            
            return True
            
        except Exception as e:
            print(f"Error saving {url} as PDF: {e}")
            return self._save_page_screenshot_fallback(url, filename)
    
    def _save_page_screenshot_fallback(self, url, filename):
        """Fallback method using screenshot and reportlab"""
        try:
            total_height = self.driver.execute_script("return document.body.scrollHeight")
            self.driver.set_window_size(1200, total_height)
            
            screenshot_path = filename.replace('.pdf', '.png')
            self.driver.save_screenshot(screenshot_path)
            
            c = canvas.Canvas(filename, pagesize=A4)
            img = ImageReader(screenshot_path)
            
            page_width, page_height = A4
            c.drawImage(img, 0, 0, width=page_width, height=page_height, preserveAspectRatio=True)
            c.save()
            
            os.remove(screenshot_path)
            
            return True
            
        except Exception as e:
            print(f"Fallback method also failed: {e}")
            return False
    
    def get_pdf_page_count(self, pdf_path):
        """Get the number of pages in a PDF file"""
        try:
            with open(pdf_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                return len(pdf_reader.pages)
        except Exception as e:
            print(f"Warning: Could not get page count for {pdf_path}: {e}")
            return 1
    
    def save_state(self):
        """Save crawl state to JSON file"""
        state = {
            'base_url': self.base_url,
            'visited_urls': list(self.visited_urls),
            'urls_to_visit': self.urls_to_visit,
            'pdf_files': self.pdf_files,
            'page_info': self.page_info,
            'temp_dir': self.temp_dir,
            'timestamp': time.time()
        }
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save state: {e}")
    
    def load_state(self):
        """Load crawl state from JSON file"""
        if not os.path.exists(self.state_file):
            return False
        
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            if state['base_url'] != self.base_url:
                print("⚠️  State file is for a different URL, starting fresh")
                return False
            
            self.visited_urls = set(state['visited_urls'])
            self.urls_to_visit = state['urls_to_visit']
            self.pdf_files = state['pdf_files']
            self.page_info = state['page_info']
            self.temp_dir = state['temp_dir']
            
            print(f"✓ Resumed from previous state: {len(self.visited_urls)} pages already crawled")
            return True
            
        except Exception as e:
            print(f"⚠️  Could not load state: {e}, starting fresh")
            return False
    
    def cleanup_state(self):
        """Remove state file after successful completion"""
        if os.path.exists(self.state_file):
            try:
                os.remove(self.state_file)
                print("🗑️  State file cleaned up")
            except Exception as e:
                print(f"Warning: Could not remove state file: {e}")
    
    def crawl_website(self):
        """Crawl the website and collect all pages"""
        print(f"🕷️  Starting crawl of {self.base_url}")
        
        # Try to resume if requested
        if self.resume and self.load_state():
            # Verify temp directory still exists
            if not self.temp_dir or not os.path.exists(self.temp_dir):
                print("⚠️  Temporary directory missing, starting fresh")
                self.visited_urls = set()
                self.urls_to_visit = []
                self.pdf_files = []
                self.page_info = []
                self.temp_dir = None
        
        # Create temporary directory if needed
        if not self.temp_dir:
            self.temp_dir = tempfile.mkdtemp()
            print(f"Created temporary directory: {self.temp_dir}")
        
        # Initialize with base URL if starting fresh
        if not self.urls_to_visit:
            self.urls_to_visit = [self.base_url]
        
        # Progress tracking
        pbar = tqdm(total=self.max_pages, initial=len(self.visited_urls), desc="Crawling pages")
        
        try:
            while self.urls_to_visit and len(self.visited_urls) < self.max_pages:
                current_url = self.urls_to_visit.pop(0)
                
                if current_url in self.visited_urls:
                    continue
                
                self.visited_urls.add(current_url)
                
                # Generate PDF filename
                pdf_filename = os.path.join(
                    self.temp_dir, 
                    f"page_{len(self.visited_urls):03d}.pdf"
                )
                
                # Save page as PDF
                if self.save_page_as_pdf(current_url, pdf_filename):
                    page_title = self.get_page_title()
                    
                    self.page_info.append({
                        'title': page_title,
                        'url': current_url,
                        'pdf_path': pdf_filename,
                        'page_count': 0
                    })
                    
                    self.pdf_files.append(pdf_filename)
                    
                    # Get links from current page and add to queue
                    new_links = self.get_page_links(current_url)
                    self.urls_to_visit.extend(new_links)
                
                # Update progress and save state
                pbar.update(1)
                self.save_state()
        
        finally:
            pbar.close()
        
        print(f"Complete! Processed {len(self.visited_urls)} pages")
    
    def _build_hierarchical_structure(self):
        """Build tree structure from URLs for hierarchical index"""
        tree = {'_pages': [], '_children': {}}
        
        for info in self.page_info:
            # Get path relative to base URL
            base_path = urlparse(self.base_url).path.rstrip('/')
            url_path = urlparse(info['url']).path.rstrip('/')
            
            # Remove base path to get relative path
            if url_path.startswith(base_path):
                relative_path = url_path[len(base_path):].lstrip('/')
            else:
                relative_path = url_path.lstrip('/')
            
            if not relative_path:
                # Root page
                tree['_pages'].append(info)
                continue
            
            path_parts = relative_path.split('/')
            current = tree
            
            # Navigate/create tree structure
            for i, part in enumerate(path_parts[:-1]):
                if part not in current['_children']:
                    current['_children'][part] = {'_pages': [], '_children': {}}
                current = current['_children'][part]
            
            # Add page to final location
            current['_pages'].append(info)
        
        return tree
    
    def generate_hierarchical_index_pdf(self):
        """Generate hierarchical index page with clickable links"""
        if not self.page_info:
            return None
        
        print("Generating hierarchical index with clickable links...")
        
        index_filename = os.path.join(self.temp_dir, "index.pdf")
        c = canvas.Canvas(index_filename, pagesize=A4)
        width, height = A4
        
        # Title
        c.setFont("Helvetica-Bold", 20)
        c.drawString(1*inch, height - 1*inch, "Table of Contents")
        
        # Calculate page counts
        for info in self.page_info:
            info['page_count'] = self.get_pdf_page_count(info['pdf_path'])
        
        # Calculate starting pages (temporary, will adjust for index later)
        temp_page = 1
        for info in self.page_info:
            info['temp_start_page'] = temp_page
            temp_page += info['page_count']
        
        # Build hierarchical structure
        tree = self._build_hierarchical_structure()
        
        # Generate index content
        y_position = height - 1.5*inch
        line_height = 0.25*inch
        page_num = 1
        link_rects = []
        
        def draw_tree(node, level=0):
            nonlocal y_position, page_num, c
            indent = level * 0.4 * inch
            
            # Draw pages at this level
            for info in node['_pages']:
                # Check if we need a new page
                if y_position < 1*inch:
                    c.showPage()
                    page_num += 1
                    y_position = height - 1*inch
                
                c.setFont("Helvetica", 10)
                
                # Truncate long titles
                title = info['title']
                max_title_length = int(75 - (level * 5))
                if len(title) > max_title_length:
                    title = title[:max_title_length-3] + "..."
                
                # Draw title and page number
                title_text = f"• {title}"
                page_text = f"{info['temp_start_page']}"
                
                c.drawString(1*inch + indent, y_position, title_text)
                c.drawRightString(width - 1*inch, y_position, page_text)
                
                # Store rectangle for clickable area
                link_rects.append({
                    'page': page_num - 1,
                    'rect': (1*inch + indent, y_position - 3, width - 1*inch, y_position + 12),
                    'dest_page': info['temp_start_page']
                })
                
                y_position -= line_height
            
            # Draw child sections
            for section_name, section_content in sorted(node['_children'].items()):
                # Check if we need a new page
                if y_position < 1*inch:
                    c.showPage()
                    page_num += 1
                    y_position = height - 1*inch
                
                # Draw section header
                c.setFont("Helvetica-Bold", 10)
                section_display = section_name.replace('-', ' ').replace('_', ' ').title()
                c.drawString(1*inch + indent, y_position, section_display.upper())
                y_position -= line_height
                
                # Recurse for children
                c.setFont("Helvetica", 10)
                draw_tree(section_content, level + 1)
        
        draw_tree(tree)
        c.save()
        
        # Adjust page numbers for index pages
        index_page_count = page_num
        for info in self.page_info:
            info['start_page'] = info['temp_start_page'] + index_page_count
        
        # Add clickable links
        self._add_links_to_index(index_filename, link_rects, index_page_count)
        
        print(f"  ✓ Hierarchical index generated with {index_page_count} page(s)")
        return index_filename, index_page_count
    
    def _add_links_to_index(self, index_filename, link_rects, index_page_count):
        """Add clickable link annotations to the index PDF"""
        try:
            with open(index_filename, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                pdf_writer = PyPDF2.PdfWriter()
                
                for page in pdf_reader.pages:
                    pdf_writer.add_page(page)
                
                for link_info in link_rects:
                    page_idx = link_info['page']
                    rect = link_info['rect']
                    dest_page = link_info['dest_page'] + index_page_count
                    
                    pdf_writer.add_link(
                        page_number=page_idx,
                        page_destination=dest_page,
                        rect=rect
                    )
                
                with open(index_filename, 'wb') as output_file:
                    pdf_writer.write(output_file)
            
            print("  ✓ Added clickable links to index")
            
        except Exception as e:
            print(f"  ⚠️  Warning: Could not add clickable links: {e}")
    
    def merge_pdfs(self):
        """Merge all PDF files into a single document"""
        if not self.pdf_files:
            print("❌ No PDF files to merge")
            return False
            
        print(f"Merging {len(self.pdf_files)} PDF files...")
        
        try:
            merger = PyPDF2.PdfMerger()
            
            # Add index if requested
            if self.generate_index:
                index_result = self.generate_hierarchical_index_pdf()
                if index_result:
                    index_file, index_page_count = index_result
                    merger.append(index_file)
                    print(f"  ➕ Added index ({index_page_count} page(s))")
            
            # Add all content PDFs
            for pdf_file in self.pdf_files:
                if os.path.exists(pdf_file):
                    merger.append(pdf_file)
            
            # Write merged PDF
            with open(self.output_file, 'wb') as output:
                merger.write(output)
            
            merger.close()
            print(f"Successfully created: {self.output_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error merging PDFs: {e}")
            return False
    
    def cleanup(self):
        """Clean up temporary files and close driver"""
        if self.driver:
            self.driver.quit()
            print("🔒 Firefox driver closed")
        
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            print("🗑️  Temporary files cleaned up")
    
    def run(self):
        """Main execution method"""
        try:
            print("Pagebinder starting...")
            
            if self.generate_index:
                print("Hierarchical index generation enabled")
            if self.include_patterns:
                print(f"Include patterns: {self.include_patterns}")
            if self.exclude_patterns:
                print(f"Exclude patterns: {self.exclude_patterns}")
            if self.max_depth is not None:
                print(f"Max depth: {self.max_depth}")
            if self.resume:
                print("⏯ Resume mode enabled")
            
            # Setup browser
            self.setup_driver()
            
            # Crawl website
            self.crawl_website()
            
            # Merge PDFs
            if self.merge_pdfs():
                file_size = os.path.getsize(self.output_file) / (1024 * 1024)
                print(f"Final PDF size: {file_size:.2f} MB")
                print(f"Output file: {os.path.abspath(self.output_file)}")
                
                # Clean up state file on success
                self.cleanup_state()
            
        except KeyboardInterrupt:
            print("\n⏹Crawl interrupted by user")
            print("Progress saved. Run with --resume to continue")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.cleanup()
