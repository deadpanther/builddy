"""Twitter API v2 service — search mentions and post replies using httpx."""

import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)

TWITTER_API_BASE = "https://api.twitter.com/2"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.TWITTER_BEARER_TOKEN}",
        "Content-Type": "application/json",
    }


async def search_mentions(since_id: str | None = None) -> list[dict]:
    """Search for recent mentions of @builddy using Twitter API v2."""
    query = "@builddy -is:retweet"
    params = {
        "query": query,
        "max_results": 20,
        "tweet.fields": "created_at,author_id,text,conversation_id",
        "expansions": "author_id",
        "user.fields": "username",
    }
    if since_id:
        params["since_id"] = since_id

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{TWITTER_API_BASE}/tweets/search/recent",
                headers=_headers(),
                params=params,
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()

        mentions = []
        users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
        for tweet in data.get("data", []):
            author = users.get(tweet.get("author_id", ""), {})
            mentions.append({
                "tweet_id": tweet["id"],
                "tweet_text": tweet["text"],
                "twitter_username": author.get("username", "unknown"),
            })

        logger.info("Found %d mentions", len(mentions))
        return mentions

    except Exception as e:
        logger.error("Failed to search mentions: %s", str(e))
        return []


async def post_reply(tweet_id: str, text: str) -> dict | None:
    """Post a reply tweet to a given tweet."""
    payload = {
        "text": text,
        "reply": {
            "in_reply_to_tweet_id": tweet_id,
        },
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{TWITTER_API_BASE}/tweets",
                headers=_headers(),
                json=payload,
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info("Posted reply to tweet %s", tweet_id)
            return data

    except Exception as e:
        logger.error("Failed to post reply: %s", str(e))
        return None
