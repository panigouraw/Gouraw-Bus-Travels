import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

connect_args = {}
ca_file = os.getenv("DB_SSL_CA")  # only needed for cloud databases (path to ca.pem)
if ca_file:
    connect_args["ssl"] = {"ca": ca_file}

engine = create_engine(
    os.getenv("DATABASE_URL"),
    connect_args=connect_args,
    pool_pre_ping=True,   # reconnect automatically if the cloud DB dropped the connection
    pool_recycle=280,
)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()