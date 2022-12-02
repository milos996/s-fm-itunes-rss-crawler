import os
import json
import requests
import logging
import boto3
from typing import List, Optional
from pyquery import PyQuery as pq

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


def get_links_from_sub_genres(html: bytes) -> List[str]:
    d = pq(html)

    a_sub_genres_tags = d("#genre-nav ul.list.top-level-subgenres a body")

    links = [i.attr("href") for i in a_sub_genres_tags.items("a")]

    return links


def send_event_for_parsing_popular_podcasts(event: dict):
    sqs_client = boto3.client("sqs")
    queue_url = os.environ.get("POPULAR_PODCASTS_QUEUE_URL")

    try:
        response = sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(event),
        )

        logger.info(
            f"Successfully send event to queue: {queue_url}. Response: {response}"
        )
    except Exception as e:
        logger.error(f"Failed to send event to queue: {queue_url}. Cause: {e}")


def get_clusters_from_links(links: List[str]):
    clusters_size = int(os.environ.get("NUMBER_OF_ITEMS_PER_CLUSTERS")) - 1

    clusters = [
        links[i : i + clusters_size] for i in range(0, len(links), clusters_size)
    ]

    return clusters


def lambda_handler(event, context):
    ITUNES_PODCAST_CATEGORIES_URL = "https://podcasts.apple.com/us/genre/podcasts/id26"

    html = get_html_content(ITUNES_PODCAST_CATEGORIES_URL)

    if html is None:
        return

    links = get_links_from_sub_genres(html)

    if links == []:
        logger.info(
            f"Categories links scrapped from url: {ITUNES_PODCAST_CATEGORIES_URL}, are not found."
        )
        return

    clusters_of_links = get_clusters_from_links(links)

    for cluster in clusters_of_links:
        cluster_data = {"categories_urls_to_parse": cluster}

        send_event_for_parsing_popular_podcasts(cluster_data)
