import json
import requests
import logging
from typing import List, Optional

from pyquery import PyQuery as pq
from concurrent.futures import ThreadPoolExecutor, as_completed

from db.base import get_session
import db.models as models

logging.basicConfig(level=logging.NOTSET)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_html_content(url: str) -> Optional[bytes]:
    try:
        res = requests.get(url)

        return res.content
    except Exception as e:
        logger.error(f"Failed getting content from url: {url}. Cause: {e}")

    return None


def get_links_from_podcasts(html: bytes) -> List[str]:
    d = pq(html)

    a_podcasts_tags = d("#selectedcontent li a")

    links = [i.attr("href") for i in a_podcasts_tags.items("a")]

    return links


def get_podcast_data(url: str) -> dict:
    PODCAST_API_JSON = (
        "https://itunes.apple.com/lookup?resultentity=PODCAST&id={id}&output=json"
    )
    parts = url.split("/")
    id = parts[-1].split("id")[-1]

    res = requests.get(PODCAST_API_JSON.format(id=id))

    return res.json()


def format_data(data: dict):
    if data["resultCount"] == 0:
        raise Exception("No results")

    data = data["results"][0]

    return {
        "collection_id": data["collectionId"],
        "track_id": data["trackId"],
        "feed_url": data["feedUrl"],
        "genre_ids": data["genreIds"],
        "genres_names": data["genres"],
    }


def persist_data(podcasts: List[dict]):
    session = get_session()

    with session.begin():
        for podcast in podcasts:
            session.add(
                models.Podcast(
                    collection_id=podcast["collection_id"],
                    track_id=podcast["track_id"],
                    feed_url=podcast["feed_url"],
                    genre_ids=podcast["genre_ids"],
                    genres_names=podcast["genres_names"],
                )
            )


def process_message(message: dict):
    NUMBER_OF_WORKERS = 10
    urls_to_scrape = message["categories_urls_to_parse"]

    data_to_save = []

    with ThreadPoolExecutor(max_workers=NUMBER_OF_WORKERS) as executor:
        for url in urls_to_scrape:
            html = get_html_content(url)

            links = get_links_from_podcasts(html)

            future_to_link = {
                executor.submit(get_podcast_data, link): link for link in links
            }

            data_to_save = []

            for future in as_completed(future_to_link):
                link = future_to_link[future]

                try:
                    data = future.result()

                    data_to_save.append(format_data(data))

                except Exception as e:
                    logger.error(
                        f"Failed to retrieve data for link: {link}. Cause: {e}"
                    )

            try:
                persist_data(data_to_save)
            except Exception as e:
                logger.error(f"Failed to save data for category: {url}. Cause: {e}")


def lambda_handler(event, context):
    for record in event["Records"]:
        body = json.loads(record["body"])
        message = json.loads(body["Message"])

        process_message(message)
