import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

MSSQL_USER = os.getenv("MSSQL_USER")
MSSQL_PASSWORD = os.getenv("MSSQL_PASSWORD")
MSSQL_HOST = os.getenv("MSSQL_HOST")
MSSQL_PORT = os.getenv("MSSQL_PORT", "1433")
MSSQL_DB = os.getenv("MSSQL_DB")

DATABASE_URL = (
    f"mssql+pyodbc://{MSSQL_USER}:{MSSQL_PASSWORD}"
    f"@{MSSQL_HOST}:{MSSQL_PORT}/{MSSQL_DB}"
    "?driver=ODBC+Driver+17+for+SQL+Server"
)

# For Windows Authentication
# DATABASE_URL = (
#     f"mssql+pyodbc://@{MSSQL_HOST}:{MSSQL_PORT}/{MSSQL_DB}"
#     "?driver=ODBC+Driver+17+for+SQL+Server"
#     "&trusted_connection=yes"
# )

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()