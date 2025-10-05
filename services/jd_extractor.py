from bs4 import BeautifulSoup
import requests

def extract_jd_from_url(url: str) -> str:
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove scripts/styles/noscript
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        # Extract text preserving paragraphs and newlines
        paragraphs = soup.find_all(['p', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        visible_text = "\n\n".join(p.get_text(separator=" ", strip=True) for p in paragraphs)

        if len(visible_text) > 0:
            return visible_text
        else:
            raise RuntimeError("Extracted text is empty with fallback method.")
    except Exception as e:
        raise RuntimeError(f"Failed to extract JD from URL with both methods: {str(e)}")
