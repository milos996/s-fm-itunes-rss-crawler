import os
import json
import logging
from datetime import datetime, timezone, timedelta
import boto3

from sqlalchemy import and_

from db.base import get_session
import db.models as models


logging.basicConfig(level=logging.NOTSET)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_podcasts_to_scrape(number_of_podcasts_to_scrap: int):
    session = get_session()

    # Podcasts that are not yet scrapped with episodes
    podcasts = (
        session.query(models.Podcast)
        .filter(models.Podcast.status == models.PodcastStatus.Init.value)
        .order_by(models.Podcast.updated_at)
        .limit(number_of_podcasts_to_scrap)
        .all()
    )

    if len(podcasts) < number_of_podcasts_to_scrap:
        # Taking podcasts with status 'Active' which means they already been scrapped,
        # but they should be checked and updated if needed.
        # Time that must passed before next check is one day.
        current_utc_datetime = datetime.now(timezone.utc) - timedelta(days=1)

        podcasts += (
            session.query(models.Podcast)
            .filter(
                and_(
                    models.Podcast.status == models.PodcastStatus.Active.value,
                    models.Podcast.update_at <= current_utc_datetime.date(),
                )
            )
            .order_by(models.Podcast.updated_at)
            .limit(number_of_podcasts_to_scrap - len(podcasts))
            .all()
        )


def format_payload(podcast: models.Podcast):
    payload = {"id": podcast.id, "feed_url": podcast.feed_url}

    return json.dumps(payload)


def run_task(podcast):
    client = boto3.client("ecs")

    response = client.run_task(
        cluster=os.environ.get("ECS_CLUSTER"),
        launchType="FARGATE",
        taskDefinition=os.environ.get("ECS_TASK_DEFINITION"),
        count=1,
        platformVersion="LATEST",
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": [
                    os.environ.get("ECS_TASK_SUBNET_1"),
                ],
                "assignPublicIp": "ENABLED",
                "securityGroups": [os.environ.get("SECURITY_GROUP")],
            }
        },
        overrides={
            "containerOverrides": [
                {
                    "name": os.environ.get("ECS_CONTAINER"),
                    "environment": [
                        {"name": "PODCAST_TO_SCRAPE", "value": format_payload(podcast)},
                    ],
                },
            ]
        },
    )

    failures = response["failures"]

    if len(failures) > 0:
        logger.error(f"Failed spawning ecs task, errors: {failures}")


def get_current_number_of_running_tasks() -> int:
    client = boto3.client("ecs")

    try:
        response = client.list_tasks(
            cluster=os.environ.get("ECS_CLUSTER"), launchType="FARGATE"
        )

        return int(len(response["taskArns"]))
    except Exception as e:
        logger.error(f"Couldn't retrieve number of running tasks. Cause: {e}")
        return int(os.environ.get("NUMBER_OF_PARALLEL_TASKS"))


def lambda_handler(event, context):
    number_of_parallel_tasks_for_scraping = int(
        os.environ.get("NUMBER_OF_PARALLEL_TASKS")
    )

    current_number_of_running_tasks = get_current_number_of_running_tasks()

    # Idea is to always run defined set of tasks and not to overwhelm system
    podcasts = get_podcasts_to_scrape(
        number_of_parallel_tasks_for_scraping - current_number_of_running_tasks
    )

    if len(podcasts) == 0:
        logger.info("No podcasts that should be scrapped at the moment.")
        return

    for podcast in podcasts:
        run_task(podcast)
