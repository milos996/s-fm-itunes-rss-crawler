import uuid
from typing import cast

import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID

PostgreSQLUUID = cast("sqlalchemy.types.TypeEngine[uuid.UUID]", UUID(as_uuid=True))


Base = declarative_base()