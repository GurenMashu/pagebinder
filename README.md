# PAGEBINDER

A clean, efficient Python tool that crawls websites and converts them into a single PDF document with additional features (check CLI options).

## Features 

- **Full Website Crawling**: Automatically discovers and crawls all pages within a domain
- **Visual Preservation**: Generated PDFs look exactly like the original website
- **Clickable Links**: All links in the original website remain functional in the PDF
- **Firefox-Based**: Uses Firefox WebDriver for reliable rendering
- **Customizable**: Configurable page limits and output options
- **Clean Output**: Professional-looking merged PDF documents

## Prerequisites 

Before using this tool, you need:

1. **Python 3.7+**
2. **Firefox Browser** - The tool uses Firefox for web rendering

**That's it!** GeckoDriver is included in the project, so no additional system dependencies are required.

## Installation 

1. **Clone the repository:**
```bash
git clone https://github.com/GurenMashu/pagebinder.git
cd pagebinder
```

2. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

3. **Make geckodriver executable (Linux/Mac only):**
```bash
chmod +x drivers/geckodriver
```

**Windows users:** The geckodriver is ready to use, no additional steps needed.

**You're ready to go!** The tool includes everything needed to run.

## Usage 💻

### Basic Usage
```bash
python website_crawler.py https://example.com
```

### Advanced Options
```bash
# Specify output filename and maximum pages
python website_crawler.py https://docs.python.org -o python_docs.pdf -m 100 -i 

# Run in visible mode (non-headless)
python website_crawler.py https://blog.example.com --no-headless -m 25

# Show help
python website_crawler.py --help
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `url` | Website URL to crawl (required) | - |
| `-o, --output` | Output PDF filename | `website.pdf` |
| `-m, --max-pages` | Maximum pages to crawl | `50` |
| `--no-headless` | Run browser in visible mode | Headless mode |
| `-i, --index` | Generate hierarchical table of contents with clickable links | - |
| `--include` | Include only URLs matching this pattern (regex). Can be used multiple times | - |
| `--exclude` | Exclude URLs matching this pattern (regex). Can be used multiple times | - |
| `--max-depth` | Maximum URL depth from base URL (e.g., 2 = two levels deep) | - |
| `--resume` | Resume from previous interrupted crawl | - |
| `--state-file` | State file for resume functionality (default: crawler_state.json) | - |

## How It Works 🔧

1. **Initialization**: Sets up Firefox WebDriver with optimized settings
2. **Crawling**: Starting from the base URL, discovers all internal links
3. **PDF Generation**: Converts each page to PDF while preserving layout and links
4. **Merging**: Combines all individual PDFs into a single document
5. **Cleanup**: Removes temporary files and closes browser

## Examples 📖

### Documentation Site
```bash
python website_crawler.py https://requests.readthedocs.io -o requests_docs.pdf -m 75 --max-depth 2
```

### Blog or News Site
```bash
python website_crawler.py https://realpython.com/blog/ -o realpython_blog.pdf -m 100 -i 
```

### Small Website (All Pages)
```bash
python website_crawler.py https://smallwebsite.com -m 1000
```

## Output 📄

The tool generates:
- A single PDF file with all crawled pages
- Preserved visual styling and layout
- Functional clickable links
- Progress feedback during crawling
- File size information upon completion
- Hierarchical index
- State files to save current extent of crawl - user-enabled

## Limitations ⚠️

- Only crawls pages within the same domain
- Requires JavaScript-enabled browser (Firefox)
- Large sites may take considerable time to process
- PDF size depends on content and number of pages
- Some dynamic content may not render identically

## Contributing 🤝

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License 📝

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Troubleshooting 🔍

### Common Issues

**"geckodriver not found"**
- Make sure geckodriver is installed and in your PATH
- Try specifying the full path to geckodriver

**"Connection refused" or timeout errors**
- Check your internet connection
- Some websites may block automated requests
- Try reducing the crawl speed or using `--no-headless` mode

**Large PDF files**
- Consider reducing the `--max-pages` limit
- Some sites have many pages or large images

**Memory issues**
- Close other applications while crawling large sites
- Reduce the maximum pages limit
- Consider splitting large sites into multiple smaller PDFs
