import logging
import os

from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.routing import Route, Mount

from shared.db import init_connection
from .endpoints import admin, invites, general

load_dotenv()
init_connection()


routes = [
    Route("/", general.AboutPage),
    Route("/oauth/{secret}", invites.LoginGate),
    Route("/login", invites.LoginGate),
    Route("/join/pjatk2021", invites.GuildInviteEndpoint),
    Mount("/admin", routes=admin.routes)
]

middleware = [
    Middleware(SessionMiddleware, secret_key=os.getenv('COOKIE_SECRET', 'someoneforgotcookiesecretrecipe'))
]

if not os.getenv('COOKIE_SECRET'):
    logging.warning('Cookie secret hasn\'t been passed')

app = Starlette(routes=routes)
