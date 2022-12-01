import os
import logging
import json
from lxml import etree
from datetime import datetime
import requests
from typing import List, Optional
from db.models import models
from db.base import get_session

from dotenv import load_dotenv

logging.basicConfig(level=logging.NOTSET)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


load_dotenv()


def update_podcast(id, data):
    session = get_session()

    podcast = session.query(models.Podcast).filter(models.Podcast.id == id).first()

    if podcast.status != models.PodcastStatus.Active.value:
        with session.begin():
            podcast.name = data["name"]
            podcast.published_date = data["published_date"]

            session.add(podcast)


def create_new_episodes(podcast_id: str, episodes_data: List[dict]):
    session = get_session()

    existing_episodes = (
        session.query(models.PodcastEpisode)
        .filter(models.PodcastEpisode.podcast_id == podcast_id)
        .all()
    )

    episodes_external_ids = [episode.external_id for episode in existing_episodes]

    with session.begin():
        for episode in episodes_data:
            if episode["external_id"] not in episodes_external_ids:
                session.add(
                    models.PodcastEpisode(
                        title=episode["title"],
                        link=episode["link"],
                        published_date=episode["published_date"],
                        external_id=episode["external_id"],
                        episode_number=episode["episode_number"],
                        episode_duration=episode["episode_duration"],
                        podcast_id=podcast_id,
                    )
                )


def get_datetime(str: str) -> datetime:
    PUBLISHED_DATE_FORMAT = "%a, %d %b %Y %H:%M:%S %z"

    return datetime.strptime(str, PUBLISHED_DATE_FORMAT)


def get_xml_content(url: str) -> Optional[bytes]:
    try:
        res = requests.get(url)

        return res.content
    except Exception as e:
        logger.error(f"Failed getting content from url: {url}. Cause: {e}")

    return None


def get_additional_podcast_information(etree) -> dict:
    name = etree.find("channel/title", namespaces=etree.nsmap).text
    published_date = etree.find("channel/pubDate").text

    published_date = get_datetime(published_date)

    return {"name": name, "published_date": published_date}


def get_all_episodes_information(etree) -> List[dict]:
    episode_items = etree.findall("channel/item", namespaces=etree.nsmap)

    formatted_episodes_data = []

    for item in episode_items:
        title = item.find("title").text
        link = item.find("link").text
        published_date = get_datetime(item.find("pubDate").text)
        external_id = item.find("guid").text
        episode_number = item.find("{*}episode").text
        episode_duration = item.find("{*}duration").text

        formatted_episodes_data.append(
            {
                "title": title,
                "link": link,
                "published_date": published_date,
                "external_id": external_id,
                "episode_number": episode_number,
                "episode_duration": episode_duration,
            }
        )

    return formatted_episodes_data


def main():
    podcast_to_scrape = json.loads(os.environ.get("PODCAST_TO_SCRAPE", "{}"))

    podcast_id = podcast_to_scrape["id"]
    feed_url = podcast_to_scrape["feed_url"]

    xml_content = get_xml_content(feed_url)

    if xml_content is None:
        return

    root = etree.fromstring(xml_content)

    podcast_data = get_additional_podcast_information(root)

    episodes_data = get_all_episodes_information(root)

    update_podcast(podcast_id, podcast_data)

    create_new_episodes(podcast_id, episodes_data)


if __name__ == "__main__":
    main()
