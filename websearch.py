"""
websearch.py
------------
Gives Jarvis the ability to search the internet. Uses DuckDuckGo's
plain HTML results page directly (just `requests` + a bit of regex)
instead of the duckduckgo-search package used in the desktop version -
that package pulls in extra native dependencies that are unreliable to
compile for Android. This is a bit more fragile if DuckDuckGo changes
their page layout, but far more likely to actually build.
"""

import re
import requests

SEARCH_URL = "https://html.duckduckgo.com/html/"


def _clean(html_fragment: str) -> str:
    return re.sub(r"<.*?>", "", html_fragment).strip()


def search_web(query: str, max_results: int = 5) -> str:
    try:
        response = requests.post(
            SEARCH_URL,
            data={"q": query},
            headers={"User-Agent": "Mozilla/5.0 (Android) JarvisApp/1.0"},
            timeout=15,
        )
        html = response.text

        titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, re.DOTALL)
        snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)

        results = []
        for title, snippet in zip(titles[:max_results], snippets[:max_results]):
            results.append(f"- {_clean(title)}: {_clean(snippet)}")

        if not results:
            return "No results found."
        return "\n".join(results)

    except Exception as e:
        return f"Web search failed with error: {e}"
