#!/usr/bin/env python3
"""
Website to PDF Crawler
A tool to crawl websites and convert them to a single PDF with clickable links.
"""

import os
import sys
import time
from urllib.parse import urljoin, urlparse
from pathlib import Path
import tempfile
import shutil

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import PyPDF2
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


class WebsitePDFCrawler:
    def __init__(self, base_url, output_file="website.pdf", max_pages=50, headless=True):
        self.base_url = base_url.rstrip('/')
        self.domain = urlparse(base_url).netloc
        self.output_file = output_file
        self.max_pages = max_pages
        self.headless = headless
        self.visited_urls = set()
        self.pdf_files = []
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
            service = webdriver.FirefoxService(executable_path=geckodriver_path)
            self.driver = webdriver.Firefox(service=service, options=options)
            self.driver.set_window_size(1200, 800)
            print("✓ Firefox driver initialized successfully")
        except WebDriverException as e:
            print(f"✗ Error initializing Firefox driver: {e}")
            print(f"Make sure geckodriver is available at: {geckodriver_path}")
            sys.exit(1)
    
    def get_geckodriver_path(self):
        """Get the path to geckodriver, checking project directory first"""
        # Check project directory first
        script_dir = Path(__file__).parent
        local_geckodriver = script_dir / "drivers" / "geckodriver"
        
        if local_geckodriver.exists():
            return str(local_geckodriver)
        
        # Fallback to system PATH
        import shutil
        system_geckodriver = shutil.which("geckodriver")
        if system_geckodriver:
            return system_geckodriver
        
        # If neither found, return local path (will cause error with helpful message)
        return str(local_geckodriver)
    
    def is_same_domain(self, url):
        """Check if URL belongs to the same domain"""
        return urlparse(url).netloc == self.domain
    
    def get_page_links(self, current_url):
        """Extract all links from the current page"""
        links = set()
        try:
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Find all anchor tags
            anchor_elements = self.driver.find_elements(By.TAG_NAME, "a")
            
            for anchor in anchor_elements:
                href = anchor.get_attribute("href")
                if href:
                    full_url = urljoin(current_url, href)
                    # Only include HTTP/HTTPS links from same domain
                    if (full_url.startswith(('http://', 'https://')) and 
                        self.is_same_domain(full_url) and
                        full_url not in self.visited_urls):
                        links.add(full_url)
        
        except Exception as e:
            print(f"Warning: Error extracting links from {current_url}: {e}")
        
        return links
    
    def save_page_as_pdf(self, url, filename):
        """Save current page as PDF using browser's print function"""
        try:
            self.driver.get(url)
            
            # Wait for page to fully load
            time.sleep(3)
            
            # Execute print to PDF
            pdf_data = self.driver.execute_cdp_cmd("Page.printToPDF", {
                "format": "A4",
                "printBackground": True,
                "marginTop": 0.4,
                "marginBottom": 0.4,
                "marginLeft": 0.4,
                "marginRight": 0.4,
                "preferCSSPageSize": True
            })
            
            # Save PDF data
            import base64
            with open(filename, "wb") as f:
                f.write(base64.b64decode(pdf_data['data']))
            
            return True
            
        except Exception as e:
            print(f"Error saving {url} as PDF: {e}")
            return False
    
    def crawl_website(self):
        """Crawl the website and collect all pages"""
        print(f"🕷️  Starting crawl of {self.base_url}")
        
        # Create temporary directory for PDF files
        self.temp_dir = tempfile.mkdtemp()
        print(f"📁 Created temporary directory: {self.temp_dir}")
        
        # Initialize with base URL
        urls_to_visit = [self.base_url]
        
        while urls_to_visit and len(self.visited_urls) < self.max_pages:
            current_url = urls_to_visit.pop(0)
            
            if current_url in self.visited_urls:
                continue
                
            print(f"📄 Processing: {current_url}")
            self.visited_urls.add(current_url)
            
            # Generate PDF filename
            pdf_filename = os.path.join(
                self.temp_dir, 
                f"page_{len(self.visited_urls):03d}.pdf"
            )
            
            # Save page as PDF
            if self.save_page_as_pdf(current_url, pdf_filename):
                self.pdf_files.append(pdf_filename)
                print(f"  ✓ Saved as PDF: {os.path.basename(pdf_filename)}")
                
                # Get links from current page and add to queue
                new_links = self.get_page_links(current_url)
                urls_to_visit.extend(new_links)
                print(f"  📎 Found {len(new_links)} new links")
            else:
                print(f"  ✗ Failed to save PDF")
        
        print(f"✅ Crawl complete! Processed {len(self.visited_urls)} pages")
    
    def merge_pdfs(self):
        """Merge all PDF files into a single document"""
        if not self.pdf_files:
            print("❌ No PDF files to merge")
            return False
            
        print(f"📚 Merging {len(self.pdf_files)} PDF files...")
        
        try:
            merger = PyPDF2.PdfMerger()
            
            for pdf_file in self.pdf_files:
                if os.path.exists(pdf_file):
                    merger.append(pdf_file)
                    print(f"  ➕ Added: {os.path.basename(pdf_file)}")
            
            # Write merged PDF
            with open(self.output_file, 'wb') as output:
                merger.write(output)
            
            merger.close()
            print(f"✅ Successfully created: {self.output_file}")
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
            print("🚀 Website PDF Crawler starting...")
            
            # Setup browser
            self.setup_driver()
            
            # Crawl website
            self.crawl_website()
            
            # Merge PDFs
            if self.merge_pdfs():
                file_size = os.path.getsize(self.output_file) / (1024 * 1024)
                print(f"📖 Final PDF size: {file_size:.2f} MB")
                print(f"📍 Output file: {os.path.abspath(self.output_file)}")
            
        except KeyboardInterrupt:
            print("\n⏹️  Crawl interrupted by user")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
        finally:
            self.cleanup()


