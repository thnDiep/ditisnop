import requests
from bs4 import BeautifulSoup
from slugify import slugify


def clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    keywords = ["nav", "ads"]
    _remove_elements(soup, keywords)
    _fix_internal_links(soup)
    return str(soup)


def fetch_articles(api_url, limit=50):
    articles = []
    url = api_url

    count = 0
    while url and count < limit:
        print(f"[INFO] - Fetching: {url}")
        resp = requests.get(url)
        data = resp.json()
        articles.extend(data["articles"])
        count += len(data["articles"])
        url = data.get("next_page")
    return articles


def save_md(article_dir, title, html_url, md):
    slug = slugify(title)
    md_with_html_url = md.strip() + f"\n\nArticle URL: {html_url}\n"
    with open(f"{article_dir}/{slug}.md", "w", encoding="utf-8") as f:
        f.write(md_with_html_url)

    return slug


def _remove_elements(soup: BeautifulSoup, keywords: list[str]) -> None:
    """
    Remove all elements whose tag name is in keywords or any of their classes include a keyword.

    Args:
        soup (BeautifulSoup): Parsed HTML soup.
        keywords (list[str]): Keywords to match in tag names or class names.
    """

    for tag in soup.find_all():
        class_list = tag.get("class", [])
        if tag.name in keywords or any(
            kw in cls for cls in class_list for kw in keywords
        ):
            print(f"[DEBUG] Removed: <{tag.name} class='{class_list}'>")
            tag.decompose()


def _fix_internal_links(soup: BeautifulSoup) -> None:
    """
    Fix internal anchor links to use slugified heading text as IDs.

    For each <a href="#...">:
    - Find the corresponding <a name="...">.
    - Find the nearest heading tag after it.
    - Assign a slugified ID to the heading.
    - Update the href to point to the slugified ID.

    Args:
        soup (BeautifulSoup): Parsed HTML soup.
    """
    for link in soup.find_all("a", href=True):
        if link["href"].startswith("#"):
            ref = link["href"][1:]  # remove #
            anchor = soup.find("a", attrs={"name": ref})
            if anchor:
                heading = anchor.find_next(["h1", "h2", "h3", "h4", "h5", "h6"])
                if heading:
                    heading_text = heading.get_text(strip=True)
                    slug = slugify(heading_text)
                    heading["id"] = slug
                    link["href"] = f"#{slug}"
