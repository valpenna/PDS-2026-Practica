import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "miclavesecreta")
    TESTING = False
    SESSION_TYPE = "filesystem"
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)


class DevelopmentConfig(Config):
    TESTING = False
    DB_USER = os.environ.get("DB_USER", "vale")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "vale")
    DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
    DB_PORT = os.environ.get("DB_PORT", "5432")
    DB_NAME = os.environ.get("DB_NAME", "grupo25")

    SQLALCHEMY_ENGINES = {
        "default": (
            f"postgresql+psycopg2://"
            f"{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        )
    }


class ProductionConfig(Config):
    SQLALCHEMY_ENGINES = {"default": os.environ.get("DATABASE_URL")}


class TestingConfig(Config):
    SQLALCHEMY_ENGINES = {"default": os.environ.get("DATABASE_URL")}

    TESTING = True


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
