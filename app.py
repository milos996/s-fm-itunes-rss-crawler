#!/usr/bin/env python3
import aws_cdk as cdk

from s_fm_itunes_rss_crawler.s_fm_itunes_rss_crawler_stack import (
    SFmItunesRssCrawlerStack,
)


app = cdk.App()
SFmItunesRssCrawlerStack(
    scope=app,
    construct_id="SFmItunesRssCrawlerStack",
    env=cdk.Environment(
        region="eu-west-1",
        account="124214512412",  # should represent account id
    ),
)

app.synth()
