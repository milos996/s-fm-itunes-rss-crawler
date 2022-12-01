import aws_cdk as core
import aws_cdk.assertions as assertions

from s_fm_itunes_rss_crawler.s_fm_itunes_rss_crawler_stack import SFmItunesRssCrawlerStack

# example tests. To run these tests, uncomment this file along with the example
# resource in s_fm_itunes_rss_crawler/s_fm_itunes_rss_crawler_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = SFmItunesRssCrawlerStack(app, "s-fm-itunes-rss-crawler")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
