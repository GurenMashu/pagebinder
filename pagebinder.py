import sys
import argparse
from WebsiteCrawler import WebsitePDFCrawler

def main():
    parser = argparse.ArgumentParser(
        description="Crawl a website and convert it to a single PDF with clickable links",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Basic usage:
    python pagebinder.py https://example.com
  
  With hierarchical index:
    python pagebinder.py https://docs.python.org -i -o python_docs.pdf
  
  Filter specific sections:
    python pagebinder.py https://example.com --include "/docs/" --exclude "/blog/"
  
  Limit crawl depth:
    python pagebinder.py https://example.com --max-depth 2 -m 100
  
  Resume interrupted crawl:
    python pagebinder.py https://example.com --resume
  
  Combine features:
    python pagebinder.py https://example.com -i --include "/api/" --max-depth 3 --resume
"""
    )
    
    parser.add_argument("url", help="Website URL to crawl")
    
    parser.add_argument("-o", "--output", default="website.pdf", 
                       help="Output PDF filename (default: website.pdf)")
    
    parser.add_argument("-m", "--max-pages", type=int, default=50,
                       help="Maximum pages to crawl (default: 50)")
    
    parser.add_argument("--no-headless", action="store_true",
                       help="Run browser in visible mode (default: headless)")
    
    parser.add_argument("-i", "--index", action="store_true",
                       help="Generate hierarchical table of contents with clickable links")
    
    # URL filtering options
    parser.add_argument("--include", action="append", dest="include_patterns",
                       help="Include only URLs matching this pattern (regex). Can be used multiple times.")
    
    parser.add_argument("--exclude", action="append", dest="exclude_patterns",
                       help="Exclude URLs matching this pattern (regex). Can be used multiple times.")
    
    parser.add_argument("--max-depth", type=int, dest="max_depth",
                       help="Maximum URL depth from base URL (e.g., 2 = two levels deep)")
    
    # Progress and resume options
    parser.add_argument("--resume", action="store_true",
                       help="Resume from previous interrupted crawl")
    
    parser.add_argument("--state-file", default="crawler_state.json",
                       help="State file for resume functionality (default: crawler_state.json)")
    
    args = parser.parse_args()

    # for checking url
    if not args.url.startswith(('http://', 'https://')):
        print("❌ Error: URL must start with http:// or https://")
        sys.exit(1)

    crawler = WebsitePDFCrawler(
        base_url=args.url,
        output_file=args.output,
        max_pages=args.max_pages,
        headless=not args.no_headless,
        generate_index=args.index,
        include_patterns=args.include_patterns,
        exclude_patterns=args.exclude_patterns,
        max_depth=args.max_depth,
        resume=args.resume,
        state_file=args.state_file
    )

    crawler.run()

if __name__ == "__main__":
    main()
