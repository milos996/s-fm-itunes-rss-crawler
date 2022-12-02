import json
from os import path
from aws_cdk import Stack, Duration
from aws_cdk.aws_ec2 import (
    Vpc,
    CfnInternetGateway,
    CfnVPCGatewayAttachment,
    InstanceType,
    InstanceClass,
    InstanceSize,
    SubnetSelection,
    SubnetType,
    SecurityGroup,
)
from constructs import Construct
from aws_cdk.aws_rds import (
    DatabaseInstance,
    DatabaseInstanceEngine,
    PostgresEngineVersion,
    Credentials,
)
from aws_cdk.aws_logs import LogGroup
from aws_cdk.aws_secretsmanager import Secret, SecretStringGenerator
from aws_cdk.aws_ecs import Cluster, FargateTaskDefinition, ContainerImage, LogDriver
from aws_cdk.aws_ecr import Repository, TagMutability
from aws_cdk.aws_sqs import Queue
from aws_cdk.aws_lambda import Function, Runtime, Code, Code
from aws_cdk.aws_iam import (
    PolicyStatement,
    Effect,
)
from aws_cdk.aws_lambda_event_sources import SqsEventSource
from aws_cdk.aws_events import Rule, Schedule
from aws_cdk.aws_events_targets import SqsQueue as EventTargetSqsQueue

LAMBDA_TIMEOUT_IN_SECONDS = 15 * 60


class SFmItunesRssCrawlerStack(Stack):
    vpc: Vpc = None
    db: DatabaseInstance = None
    security_group_1: SecurityGroup = None
    database_credentials_secret: Secret = None

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.build_vpc()
        self.build_database()
        self.build_podcast_preparation_component()
        self.build_podcast_scraper_component()

    def build_vpc(self):
        self.vpc = Vpc(
            self,
            "podcast-scraper-vpc",
            cidr="10.0.0.0/16",
            nat_gateways=1,
        )

        self.security_group_1 = SecurityGroup(
            self, "scraper_security_group_1", self.vpc
        )

        internet_gateway = CfnInternetGateway(self, "podcast-scraper-ig")

        CfnVPCGatewayAttachment(
            self,
            "internet-gateway-attachment",
            vpc_id=self.vpc.vpc_id,
            internet_gateway_id=internet_gateway.ref,
        )

    def build_podcast_preparation_component(self):
        category_queue = Queue(
            self,
            "category-queue",
            visibility_timeout=Duration.seconds(LAMBDA_TIMEOUT_IN_SECONDS * 2),
        )

        popular_podcasts_fetch_queue = Queue(
            self,
            "popular-podcasts-fetch-queue",
            visibility_timeout=Duration.seconds(LAMBDA_TIMEOUT_IN_SECONDS * 2),
        )

        itunes_category_parser_lambda = self.build_lambda(
            "itunes_category_parser_lambda",
            "itunes_category_parser.py",
            env_variables={
                "POPULAR_PODCASTS_QUEUE_URL": popular_podcasts_fetch_queue.queue_url,
                "NUMBER_OF_ITEMS_PER_CLUSTERS": 5,
            },
        )

        itunes_popular_podcast_parser_lambda = self.build_lambda(
            "itunes_popular_podcast_parser_lambda",
            "itunes_popular_podcast_parser.py",
            vpc_id=self.vpc.vpc_id,
            env_variables={
                "DB_USERNAME": "postgres",
                "DB_PASSWORD": self.database_credentials_secret.secret_value,
                "DB_HOST": f"{self.db.db_instance_endpoint_address}:{self.db.db_instance_endpoint_port}",
                "DB_NAME": "scraper_podcasts",
            },
        )

        itunes_category_parser_lambda.add_event_source(SqsEventSource(category_queue))

        itunes_popular_podcast_parser_lambda.add_event_source(
            SqsEventSource(popular_podcasts_fetch_queue)
        )

        Rule(
            self,
            "ScrapeCategoriesRules",
            schedule=Schedule.cron(day="*", hour="4", minute="0"),
            targets=[EventTargetSqsQueue(category_queue)],
        )

    def build_lambda(
        self,
        lambda_id,
        handler,
        vpc_id=None,
        subnet_type=SubnetType.PRIVATE_WITH_NAT,
        env_variables={},
    ):
        extra_config = {}

        if vpc_id is not None:
            extra_config = {
                "vpc": vpc_id,
                "vpc_subnets": SubnetSelection(subnet_type=subnet_type),
            }

        function = Function(
            self,
            lambda_id,
            runtime=Runtime.PYTHON_3_9,
            handler=handler,
            code=Code.from_asset(
                path.join(path.dirname(path.abspath(".")), f"src/lambdas/{handler}")
            ),
            timeout=Duration.seconds(LAMBDA_TIMEOUT_IN_SECONDS),
            environment=env_variables,
            **extra_config,
        )

        return function

    def build_podcast_scraper_component(self):
        SCRAPER_ECR_REPO = "podcast_scraper"
        ECS_CLUSTER = "PodcastScraperCluster"
        PODCAST_SCRAPER_TASK_DEFINITION = "PodcastScraperFargateTaskDefinition"

        ecr_repository = Repository(
            self, SCRAPER_ECR_REPO, image_tag_mutability=TagMutability.IMMUTABLE
        )
        ecr_repository.add_lifecycle_rule(max_image_count=5)

        ecs_cluster = Cluster(self, ECS_CLUSTER, vpc=self.vpc)

        podcast_scraper_fargate_task_definition = FargateTaskDefinition(
            self,
            PODCAST_SCRAPER_TASK_DEFINITION,
            memory_limit_mib=1024,
            cpu=512,
        )

        podcast_scraper_container_log_group = LogGroup(
            self, "/ecs/PodcastScraperContainer"
        )

        podcast_scraper_fargate_task_definition.add_container(
            "PodcastScraperContainer",
            image=ContainerImage.from_ecr_repository(ecr_repository),
            logging=LogDriver.aws_logs(
                stream_prefix="ecs", log_group=podcast_scraper_container_log_group
            ),
        )

        podcast_scraper_queue = Queue(
            self,
            "podcast-scraper-queue",
            visibility_timeout=Duration.seconds(LAMBDA_TIMEOUT_IN_SECONDS * 2),
        )

        private_subnet_id = self.vpc.select_subnets(
            subnet_type=SubnetType.PRIVATE_WITH_NAT
        ).subnet_ids[0]

        mediator_podcast_scraper_lambda = self.build_lambda(
            "mediator_podcast_scraper_lambda",
            "mediator_podcast_scraper.py",
            vpc_id=self.vpc.vpc_id,
            env_variables={
                "NUMBER_OF_PARALLEL_TASKS": 5,
                "ECS_CLUSTER": ecs_cluster.cluster_name,
                "SECURITY_GROUP": self.security_group_1.security_group_id,
                "ECS_TASK_SUBNET_1": private_subnet_id,
                "ECS_TASK_DEFINITION": podcast_scraper_fargate_task_definition.task_definition_arn,
            },
        )

        run_ecs_task_policy = PolicyStatement(
            effect=Effect.ALLOW,
            actions=["ecs:RunTask", "iam:GetRole", "iam:PassRole"],
            resources=["*"],
        )

        mediator_podcast_scraper_lambda.add_event_source(
            SqsEventSource(podcast_scraper_queue)
        )
        mediator_podcast_scraper_lambda.role.add_to_principal_policy(
            run_ecs_task_policy
        )

        Rule(
            self,
            "ScrapePodcastRule",
            schedule=Schedule.rate(Duration.minutes(10)),
            targets=[EventTargetSqsQueue(podcast_scraper_queue)],
        )

    def build_database(self):
        self.database_credentials_secret = Secret(
            self,
            "db-secret",
            generate_secret_string=SecretStringGenerator(
                secret_string_template=json.stringify({"username": "postgres"}),
                generate_string_key="password",
            ),
        )

        self.db = DatabaseInstance(
            self,
            "Postgres-Instance",
            engine=DatabaseInstanceEngine.postgres(
                version=PostgresEngineVersion.VER_14_1
            ),
            instance_type=InstanceType.of(InstanceClass.D2, InstanceSize.MEDIUM),
            credentials=Credentials.from_secret(self.database_credentials_secret),
            vpc=self.vpc,
            vpc_subnets=SubnetSelection(subnet_type=SubnetType.PRIVATE_WITH_NAT),
        )
