class Config():
    Debug = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class LocalDevelopmentConfig(Config):
    Debug = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///project_db.sqlite3'
    JWT_SECRET_KEY = 'super-secret'
    CACHE_TYPE = "RedisCache"
    CACHE_REDIS_HOST = "localhost"
    CACHE_REDIS_PORT = 6379
    CACHE_REDIS_DB = 2
