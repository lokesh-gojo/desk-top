import re
from bs4 import BeautifulSoup

def clean_html(html_content: str) -> str:
    """Strip navigation bars, scripts, styles, and extract coherent text."""
    if not html_content:
        return ""
        
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Remove unwanted tags
    for tag in soup(["script", "style", "nav", "footer", "noscript", "svg", "header", "form", "button"]):
        tag.decompose()
        
    # Get text
    text = soup.get_text(separator="\n")
    
    # Normalize whitespaces
    lines = [line.strip() for line in text.splitlines()]
    # Remove short garbage lines
    meaningful_lines = [line for line in lines if len(line) > 10 or line.endswith(":")]
    
    cleaned = "\n".join(meaningful_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
