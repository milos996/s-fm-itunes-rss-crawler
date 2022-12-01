import os

from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session as SessionType

path = os.path.abspath(__file__)
directory = os.path.dirname(path)

alembic_cfg = Config(f"{directory}/alembic.ini")
alembic_cfg.set_main_option("script_location", f"{directory}/migration")

db_dialect = os.environ.get("DB_DIALECT", "postgresql")
db_username = os.environ.get("DB_USERNAME", "postgres")
db_password = os.environ.get("DB_PASSWORD", "Pass2022!")
db_host = os.environ.get("DB_HOST", "localhost:5432")
db_name = os.environ.get("DB_NAME", "scraper_test")

engine = create_engine(
    f"{db_dialect}://{db_username}:{db_password}@{db_host}/{db_name}"
)

Session = sessionmaker(bind=engine)


def get_session() -> SessionType:
    return Session() 
