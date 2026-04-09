import requests
import time
from typing import List, Dict, Any

def search_academic_papers(query: str, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Searches Semantic Scholar Open API for papers matching the given query.
    Returns a list of dictionaries with paper details.
    """
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,authors,year,abstract,url,citationCount,venue"
    }
    
    try:
        response = None
        for attempt in range(3):
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 429:
                # Rate limited, wait and retry
                time.sleep(2 * (attempt + 1))
                continue
            response.raise_for_status()
            break
            
        data = response.json()
        
        results = []
        for paper in data.get("data", []):
            authors = [author["name"] for author in paper.get("authors", [])]
            # Construct a citation key (first author's last name + year)
            first_author = authors[0].split()[-1] if authors else "Unknown"
            year = paper.get("year") or "XXXX"
            cite_key = f"{first_author}{year}".lower()
            
            results.append({
                "title": paper.get("title", ""),
                "authors": authors,
                "year": year,
                "abstract": paper.get("abstract", "")[:500] if paper.get("abstract") else "", # truncate abstract
                "url": paper.get("url", ""),
                "venue": paper.get("venue") or "Academic Submission",
                "citationCount": paper.get("citationCount", 0),
                "cite_key": cite_key
            })
        return results
    except Exception as e:
        print(f"Failed to search papers for query '{query}': {e}")
        return []

def format_papers_to_text(papers: List[Dict[str, Any]]) -> str:
    """Formats papers so the LLM can easily read them."""
    if not papers:
        return "No relevant papers found.\n"
    text = ""
    for idx, p in enumerate(papers, 1):
        author_str = ", ".join(p['authors'][:3]) + (" et al." if len(p['authors']) > 3 else "")
        text += f"[{idx}] Citation Key: {p['cite_key']}\n"
        text += f"Title: {p['title']}\n"
        text += f"Authors: {author_str}\n"
        text += f"Year: {p['year']}\n"
        text += f"Abstract snippet: {p['abstract']}\n"
        text += f"URL: {p['url']}\n\n"
    return text
