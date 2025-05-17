import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin

# --- Configuration ---
URL = "https://gis.ess.washington.edu/data/raster/tenmeter/byquad/master.html"
DOWNLOAD_DIR = "../Documents/soilense_data/DEM/washington_dem_tiles"
TEST_DOWNLOAD_LIMIT = None # Set this to the number of files you want to download for testing
# ---------------------

def download_file(url, directory):
    """Downloads a file from a URL to a specified directory."""
    local_filename = url.split('/')[-1]
    filepath = os.path.join(directory, local_filename)

    if os.path.exists(filepath):
        print(f"File already exists: {local_filename}. Skipping download.")
        return True # Indicate that the file was skipped (exists)

    print(f"Downloading: {local_filename} to {filepath}") # <-- Modified print
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"Successfully downloaded: {local_filename}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {local_filename}: {e}")
        return False

def scrape_and_download(url, download_dir, limit=None):
    """Scrapes links from a webpage and downloads specified files, with an optional limit."""
    print(f"Accessing: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()

    except requests.exceptions.RequestException as e:
        print(f"Error accessing {url}: {e}")
        return

    # --- Diagnosis Prints ---
    print(f"Current working directory: {os.getcwd()}")
    # Use os.path.abspath to show the full, resolved path
    resolved_download_dir = os.path.abspath(download_dir)
    print(f"Resolved download directory path: {resolved_download_dir}")
    # --- End Diagnosis Prints ---

    # Create download directory if it doesn't exist
    if not os.path.exists(resolved_download_dir):
        # Use the resolved path for creation
        os.makedirs(resolved_download_dir)
        print(f"Created download directory: {resolved_download_dir}")
    else:
         print(f"Download directory already exists: {resolved_download_dir}") # Added check

    soup = BeautifulSoup(response.content, 'html.parser')

    links = soup.find_all('a')
    print(f"Found {len(links)} potential links.")
    downloaded_count = 0

    for link in links:
        href = link.get('href')
        if href and href.endswith('.zip'):
            file_url = urljoin(url, href)

            # Use the resolved path for downloading
            if download_file(file_url, resolved_download_dir):
                downloaded_count += 1

            if limit is not None and downloaded_count >= limit:
                print(f"Reached download limit of {limit}. Stopping.")
                break

    print("-" * 20)
    print(f"Finished checking links. Attempted to download {downloaded_count} .zip files (or skipped if already present).")

if __name__ == "__main__":
    scrape_and_download(URL, DOWNLOAD_DIR, limit=TEST_DOWNLOAD_LIMIT)