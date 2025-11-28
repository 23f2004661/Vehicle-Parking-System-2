from flask import Flask
from application.config import LocalDevelopmentConfig
from application.database import db
from application.models import User
from application.security import jwt
from flask_cors import CORS
from application.celery_init import celery_init_app
from celery.schedules import crontab
from flask_caching import Cache

app=None
cache = None
def create_app():
    app=Flask(__name__)
    app.config.from_object(LocalDevelopmentConfig)
    db.init_app(app)
    CORS(app)
    jwt.init_app(app)
    app.app_context().push()
    cache = Cache(app)
    app.app_context().push()
    return app, cache


app,cache=create_app()
celery = celery_init_app(app)

celery.autodiscover_tasks()  

@celery.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(  
        crontab(minute = '*/2'),
        monthly_report.s()  
    )

from application.controllers import *

if __name__ == '__main__':
    # db.create_all()
    # admin=User(username='admin',password='1939',pincode='0000',fullname='Administrator',role='admin')
    # user=User(username='Tarang1712',password='1939',pincode='223355',fullname='Tarang j')
    # db.session.add_all([admin,user])
    # db.session.commit()
    app.run()