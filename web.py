# web.py — FLOAT AI Desktop Assistant
# Google search, website opener, Wikipedia, Weather, News

import logging
import webbrowser
from urllib.parse import quote_plus

import requests

from config import WEATHER_API_KEY, NEWS_API_KEY, DEFAULT_CITY, log
from brain import ask_groq

logger = logging.getLogger("FLOAT.web")

# ─── Known site aliases ───────────────────────────────────────────────────────
SITE_MAP = {
    "youtube":   "https://www.youtube.com",
    "gmail":     "https://mail.google.com",
    "google":    "https://www.google.com",
    "netflix":   "https://www.netflix.com",
    "github":    "https://github.com",
    "reddit":    "https://www.reddit.com",
    "twitter":   "https://www.twitter.com",
    "instagram": "https://www.instagram.com",
    "facebook":  "https://www.facebook.com",
    "linkedin":  "https://www.linkedin.com",
    "amazon":    "https://www.amazon.com",
    "wikipedia": "https://www.wikipedia.org",
    "spotify":   "https://open.spotify.com",
    "whatsapp":  "https://web.whatsapp.com",
    "maps":      "https://maps.google.com",
    "news":      "https://news.google.com",
    "chatgpt":   "https://chat.openai.com",
    "bard":      "https://bard.google.com",
}


# ─── Open Website ─────────────────────────────────────────────────────────────
def open_site(query: str) -> str:
    """Open a known website or a URL in the default browser."""
    q = query.lower().strip()

    # Check alias map
    for name, url in SITE_MAP.items():
        if name in q:
            webbrowser.open(url)
            return f"Opening {name}."

    # If it looks like a URL
    if "." in q:
        if not q.startswith("http"):
            q = "https://" + q
        webbrowser.open(q)
        return f"Opening {q}."

    return f"I don't know the website for '{query}'."


# ─── Google Search ────────────────────────────────────────────────────────────
def google_search(query: str) -> str:
    """Open Google search results for the query."""
    url = f"https://www.google.com/search?q={quote_plus(query)}"
    webbrowser.open(url)
    return f"Searching Google for: {query}."


# ─── Wikipedia ────────────────────────────────────────────────────────────────
def wikipedia_search(query: str) -> str:
    """Search Wikipedia and return a 3-sentence summary."""
    try:
        import wikipedia
        wikipedia.set_lang("en")
        try:
            summary = wikipedia.summary(query, sentences=3, auto_suggest=True)
            return summary
        except wikipedia.exceptions.DisambiguationError as e:
            # Pick the first option
            summary = wikipedia.summary(e.options[0], sentences=3)
            return summary
        except wikipedia.exceptions.PageError:
            return f"I couldn't find a Wikipedia article on '{query}'."
    except Exception as e:
        logger.error(f"Wikipedia error: {e}")
        return "I had trouble searching Wikipedia."


# ─── Weather ──────────────────────────────────────────────────────────────────
def get_weather(city: str | None = None) -> str:
    """Get current weather for a city using OpenWeatherMap."""
    city = city or DEFAULT_CITY
    if not WEATHER_API_KEY:
        return "Weather API key not configured. Please add WEATHER_API_KEY to your .env file."
    try:
        url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={quote_plus(city)}&appid={WEATHER_API_KEY}&units=metric"
        )
        resp = requests.get(url, timeout=10)
        data = resp.json()

        if data.get("cod") != 200:
            return f"I couldn't get weather for {city}. {data.get('message', '')}"

        weather  = data["weather"][0]["description"].capitalize()
        temp     = data["main"]["temp"]
        feels    = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        wind     = data["wind"]["speed"]

        return (
            f"Weather in {city}: {weather}. "
            f"Temperature is {temp:.1f}°C, feels like {feels:.1f}°C. "
            f"Humidity {humidity}%, wind speed {wind} m/s."
        )
    except Exception as e:
        logger.error(f"Weather error: {e}")
        return "I couldn't fetch the weather right now."


# ─── News Headlines ───────────────────────────────────────────────────────────
def get_news(country: str = "in", count: int = 5) -> str:
    """Fetch top headlines using NewsAPI."""
    if not NEWS_API_KEY:
        return "News API key not configured. Please add NEWS_API_KEY to your .env file."
    try:
        url = (
            f"https://newsapi.org/v2/top-headlines"
            f"?country={country}&pageSize={count}&apiKey={NEWS_API_KEY}"
        )
        resp = requests.get(url, timeout=10)
        data = resp.json()

        articles = data.get("articles", [])
        if not articles:
            return "I couldn't find any news headlines."

        headlines = []
        for i, article in enumerate(articles[:count], 1):
            title = article.get("title", "")
            if title and "[Removed]" not in title:
                headlines.append(f"{i}. {title}")

        if not headlines:
            return "No headlines available right now."

        return "Here are today's top headlines: " + " ... ".join(headlines)
    except Exception as e:
        logger.error(f"News error: {e}")
        return "I couldn't fetch the news right now."
