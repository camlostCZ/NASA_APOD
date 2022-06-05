"""
NASA Image-of-the-day Downloader

Requires:
    Python 3.9+
"""

import logging
import re
import ssl
import urllib.request
import urllib.error

from pathlib import Path
from typing import Generator, Optional, Sequence

IMG_FILENAME_FORMAT = "image_{date}.jpg"

URL_BASE = "https://apod.nasa.gov/apod/archivepix.html"
PATTERN_SUBPAGE = r'^(\d{4}[^:]+):\s+<a href="([^"]+)[^>]+>([^<]+)<\/a>.*$'
PATTERN_IMAGE = r'^<img src="([^"]+)"$'

DATE_START = "2020-01-01"    # ISO 8601 format


def get_parent_url(url: str) -> str:
    """
    Get parent URL from a specified URL.

    Args:
        url: Common HTTP(s) URL.

    Returns:
        A parent URL (part after and incl. the last '/' removed).
    """
    return re.sub("/[^/]+$", "", url)


def load_archive(
        url: str, 
        pattern: re.Pattern, 
        date_start: str
    ) -> Generator[tuple[str, str], None, None]:
    """
    Load a page from the specified URL and return required lines
    as tuples of relevant data.
    Uses yield to allow for lazy evaluation.

    Args:
        url: Source URL
        pattern: Pattern used to filter web page lines
        start_date: The oldest day (yyyy-MM-dd) included in the results

    Yields:
        A triplet of date, link and title of a linked page.
    """
    
    date_fixed = date_start.replace("-", "")[2:]    # Get rid of '-' and first 2 digits
    page_start = f"ap{date_fixed}"

    with urllib.request.urlopen(url) as f:
        for item in f:
            line = item.decode('ISO-8859-1').strip()
            logging.debug(line)
            if (match := pattern.match(line)):
                when, link, title = match.groups()
                if link >= page_start:    # Yield only links in the date range
                    yield (when, link, title)
    # End of function


def find_image_on_page(page_url: str) -> Optional[str]:
    """
    Find image link on the specified URL.

    Args:
        page_url: Page on which we're searching for an image

    Returns:
        Image link or None if none found.
    """
    result = None
    with urllib.request.urlopen(page_url) as page:
        for item in page:
            line = item.decode('ISO-8859-1').strip()
            pattern = re.compile(PATTERN_IMAGE, re.IGNORECASE)
            if (match := pattern.match(line)):
                result = match[1]
    return result


def save_images(pages: Sequence[tuple[str, str, str]], base_url: str) -> None:
    """
    Save images from a sequence of pages.

    Args:
        pages: Sequence of page information
        base_url: Base (parent) URL (page links expected to be realative)
    """
    for when, link, title in pages:
        logging.info("Got link to page for {}: {}".format(when, title))
        
        url_page = "/".join([base_url, link])
        img_link = find_image_on_page(url_page)
        if img_link is not None:
            logging.info(f"Image found at {img_link}")
            url_img = "/".join([base_url, img_link])
            filename = IMG_FILENAME_FORMAT.replace("{date}", link[2:8])
            save_image_from_url(url_img, filename)


def save_image_from_url(url: str, name: str, folder: str = "./") -> None:
    """
    Save image from the specified URL to disk.

    Args:
        url: URL of an image
        name: Filename used to save image
        folder: Directory (folder) used to save image to. Defaults to "./".
    """
    with urllib.request.urlopen(url) as page:
        p = Path(folder) / name
        with open(p, mode="wb") as f:
            f.write(page.read())


def main() -> None:
    """
    Main function.
    """
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
        level=logging.INFO)

    try:
        # Since usage of other external libraries is not allowed,
        # we are forced to give up security.
        # Otherwise, usage of the certifi module would be a proper way.
        ssl._create_default_https_context = ssl._create_unverified_context

        archive_links = load_archive(URL_BASE, 
            re.compile(PATTERN_SUBPAGE), DATE_START)

        save_images(archive_links, get_parent_url(URL_BASE))
    except urllib.error.URLError as e:
        logging.error(e)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted by user.")
