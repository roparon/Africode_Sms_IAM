import os


SECRET_KEY = 'uCoBUfnjcryWnvAECDgFU30Ay5nUX4L1M4e92u_UrWU'
SECURITY_PASSWORD_SALT = '280737699171424552890535568987506604886'


database_url = os.environ.get('DATABASE_URL', 'postgres://default:LsYR7MCT9heG@ep-dawn-breeze-a4wt1a15-pooler.us-east-1.aws.neon.tech:5432/verceldb?sslmode=require')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

SQLALCHEMY_DATABASE_URI = database_url



# This is database
SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:1234@localhost:5432/sms'
#SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:sTxEJqetjnPggUnHzURKOxgjFHFGpCpc@postgres.railway.internal:5432/railway'
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True,}

# Registrations
SECURITY_REGISTERABLE = True
SECURITY_CONFIRMABLE = True

#Recover/Reset
SEURITY_RECOVERABLE = True

#COOKIES SETTINGS
REMEMBER_COOKIE_SAMESITE = 'strict'
SESSION_COOKIE_SAMESITE = 'strict'

#mail settings
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = 'aaronrop40@gmail.com'
MAIL_PASSWORD = 'bstl euao rstv hccr'
MAIL_DEFAULT_SENDER = 'aaronrop40@gmail.com'

# Email settings
SECURITY_CHANGE_EMAIL = True

#recovery settings
SECURITY_RECOVERABLE = True

