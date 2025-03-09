import requests
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import urljoin, urlparse
from rich.console import Console
from rich.progress import Progress
from rich.table import Table
from concurrent.futures import ThreadPoolExecutor

# Number of threads
THREADS = 10
console = Console()

def fetch_html(url):
    """ Fetch HTML from the website """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Will raise an error for 404, 500 etc.
        return response.text
    except requests.RequestException as e:
        console.print(f"[red]Request failed: {e}[/red]")
        return None

def find_php_parameters(url, results, visited, progress_task):
    """ Recursively find all PHP parameters in URLs """
    if url in visited:
        return
    visited.add(url)

    html_content = fetch_html(url)
    if not html_content:
        return

    soup = BeautifulSoup(html_content, 'html.parser')
    links = soup.find_all('a', href=True)

    # Regex pattern for PHP parameters
    php_param_pattern = re.compile(r'\?.+=.*\.php')  # PHP parameters with .php in URL

    for link in links:
        href = link['href']
        full_url = urljoin(url, href)

        # Check for PHP parameters only
        if ".php" in full_url and php_param_pattern.search(href):
            results.append(full_url)

        # Recursively crawl deeper
        if urlparse(full_url).netloc == urlparse(url).netloc:
            find_php_parameters(full_url, results, visited, progress_task)

    progress_task.advance(1)

def check_live(url):
    """ Check if the URL is live """
    try:
        response = requests.get(url, timeout=5, allow_redirects=False)
        return response.status_code in [200, 301, 302]
    except requests.RequestException:
        return False

def is_valid_url(url):
    """ Validate URL """
    parsed = urlparse(url)
    return bool(parsed.scheme and parsed.netloc)

def multi_thread_scan(url):
    """ Multi-threaded scan with recursion """
    results = []
    visited = set()

    # Create the progress bar task
    with Progress() as progress:
        progress_task = progress.add_task("[bold magenta]Scanning URLs...", total=100)
        with ThreadPoolExecutor(max_workers=THREADS) as executor:
            # Start the recursive scan and update progress
            executor.submit(find_php_parameters, url, results, visited, progress_task)

        # Wait until the progress reaches 100%
        progress.update(progress_task, total=len(results))

    # Filter live URLs (only the working PHP parameters)
    live_results = [link for link in results if check_live(link)]

    return live_results

if __name__ == "__main__":
    target_url = input("Enter target URL: ").strip()
    if not target_url.startswith("http"):
        target_url = "https://" + target_url
    
    if not is_valid_url(target_url):
        console.print("❌ Invalid URL! Please enter a valid website URL.", style="bold red")
    else:
        console.print("\n[bold cyan]⚡️ Generating Website Analysis... Please wait...[/bold cyan]")
        
        with Progress() as progress:
            task = progress.add_task("[bold magenta]Loading...", total=100)
            for _ in range(100):
                time.sleep(0.01)
                progress.update(task, advance=1)
        
        console.print("\n🔍 Scanning for all PHP parameters...\n", style="yellow")
        found_links = multi_thread_scan(target_url)
    
        if found_links:
            table = Table(title="Live PHP Parameters")
            table.add_column("Index", justify="center", style="cyan", no_wrap=True)
            table.add_column("URL", style="magenta")
            
            for idx, link in enumerate(found_links, 1):
                table.add_row(str(idx), link)
            
            console.print(table)
        else:
            console.print("❌ No live PHP parameters found.", style="red")
