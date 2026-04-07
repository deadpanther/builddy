"""Twitter API v2 service — search mentions (Bearer) and post replies (OAuth 1.0a)."""

import hashlib
import hmac
import logging
import time
import urllib.parse
import uuid
import base64

import httpx
from config import settings

logger = logging.getLogger(__name__)

TWITTER_API_BASE = "https://api.twitter.com/2"


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _bearer_headers() -> dict:
    """Headers for read-only endpoints (search)."""
    return {
        "Authorization": f"Bearer {settings.TWITTER_BEARER_TOKEN}",
        "Content-Type": "application/json",
    }


def _oauth1_headers(method: str, url: str, body: str = "") -> dict:
    """Build OAuth 1.0a Authorization header for write endpoints (tweet)."""
    oauth_nonce = uuid.uuid4().hex
    oauth_timestamp = str(int(time.time()))

    oauth_params = {
        "oauth_consumer_key": settings.TWITTER_API_KEY,
        "oauth_nonce": oauth_nonce,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": oauth_timestamp,
        "oauth_token": settings.TWITTER_ACCESS_TOKEN,
        "oauth_version": "1.0",
    }

    # Collect all params (oauth + body if form-encoded)
    all_params = dict(oauth_params)

    # Build parameter string (sorted)
    param_string = "&".join(
        f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(v, safe='')}"
        for k, v in sorted(all_params.items())
    )

    # Build signature base string
    base_string = (
        f"{method.upper()}&"
        f"{urllib.parse.quote(url, safe='')}&"
        f"{urllib.parse.quote(param_string, safe='')}"
    )

    # Build signing key
    signing_key = (
        f"{urllib.parse.quote(settings.TWITTER_API_SECRET, safe='')}&"
        f"{urllib.parse.quote(settings.TWITTER_ACCESS_SECRET, safe='')}"
    )

    # HMAC-SHA1
    signature = base64.b64encode(
        hmac.new(
            signing_key.encode(),
            base_string.encode(),
            hashlib.sha1,
        ).digest()
    ).decode()

    oauth_params["oauth_signature"] = signature

    # Build Authorization header
    auth_header = "OAuth " + ", ".join(
        f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(v, safe="")}"'
        for k, v in sorted(oauth_params.items())
    )

    return {
        "Authorization": auth_header,
        "Content-Type": "application/json",
    }


def twitter_configured() -> bool:
    """Check if Twitter credentials are present."""
    return bool(settings.TWITTER_BEARER_TOKEN and settings.TWITTER_API_KEY)


# ---------------------------------------------------------------------------
# API calls
# ---------------------------------------------------------------------------

async def search_mentions(since_id: str | None = None) -> list[dict]:
    """Search for recent mentions of @builddy using Twitter API v2."""
    if not settings.TWITTER_BEARER_TOKEN:
        logger.warning("TWITTER_BEARER_TOKEN not set — skipping mention search")
        return []

    query = "@builddy -is:retweet"
    params = {
        "query": query,
        "max_results": 10,
        "tweet.fields": "created_at,author_id,text,conversation_id",
        "expansions": "author_id",
        "user.fields": "username,name,profile_image_url",
    }
    if since_id:
        params["since_id"] = since_id

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{TWITTER_API_BASE}/tweets/search/recent",
                headers=_bearer_headers(),
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
                "twitter_name": author.get("name", ""),
                "profile_image": author.get("profile_image_url", ""),
            })

        logger.info("Found %d mentions", len(mentions))
        return mentions

    except Exception as e:
        logger.error("Failed to search mentions: %s", str(e))
        return []


async def post_reply(tweet_id: str, text: str) -> dict | None:
    """Post a reply tweet using OAuth 1.0a (write access)."""
    if not settings.TWITTER_ACCESS_TOKEN:
        logger.warning("TWITTER_ACCESS_TOKEN not set — skipping reply")
        return None

    url = f"{TWITTER_API_BASE}/tweets"
    payload = {
        "text": text,
        "reply": {
            "in_reply_to_tweet_id": tweet_id,
        },
    }

    try:
        headers = _oauth1_headers("POST", url)
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                headers=headers,
                json=payload,
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info("Posted reply to tweet %s", tweet_id)
            return data

    except Exception as e:
        logger.error("Failed to post reply to %s: %s", tweet_id, str(e))
        return None
