import sys
import argparse
from WebsiteCrawler import WebsitePDFCrawler

def main():
    parser = argparse.ArgumentParser(
        description="Crawl a website and convert it to a single PDF with clickable links",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python website_crawler.py https://example.com
  python website_crawler.py https://docs.python.org -o python_docs.pdf -m 100
  python website_crawler.py https://blog.example.com --no-headless -m 25
        """
    )
    
    parser.add_argument("url", help="Website URL to crawl")
    parser.add_argument("-o", "--output", default="website.pdf", 
                       help="Output PDF filename (default: website.pdf)")
    parser.add_argument("-m", "--max-pages", type=int, default=50,
                       help="Maximum pages to crawl (default: 50)")
    parser.add_argument("--no-headless", action="store_true",
                       help="Run browser in visible mode (default: headless)")
    
    args = parser.parse_args()
    
    # Validate URL
    if not args.url.startswith(('http://', 'https://')):
        print("❌ Error: URL must start with http:// or https://")
        sys.exit(1)
    
    # Create crawler instance
    crawler = WebsitePDFCrawler(
        base_url=args.url,
        output_file=args.output,
        max_pages=args.max_pages,
        headless=not args.no_headless
    )
    
    # Run the crawler
    crawler.run()


if __name__ == "__main__":
    main()