import os
from datetime import datetime

from aiohttp import ClientSession
from bson import ObjectId
from dotenv import load_dotenv
from google.auth.transport import requests
from google.oauth2 import id_token
from hikari import RESTApp
from mongoengine import Q, QuerySet
from starlette.applications import Starlette
from starlette.endpoints import HTTPEndpoint
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.templating import Jinja2Templates

from discordcat.embed_factory import embed_success
from webgate.invites import gen_guild_invite
from shared.documents import VerificationLink, TrustedUser, GuildConfiguration, VerificationMethod
from shared.db import init_connection

load_dotenv()
init_connection()

rest = RESTApp()
templates = Jinja2Templates(directory="templates")


class AboutPage(HTTPEndpoint):
    async def get(self, request: Request):
        return templates.TemplateResponse(
            "home.html", {"request": request, "invitation": os.getenv("INVITATION")}
        )


# class ExceptionsPreviewer(HTTPEndpoint):
#     async def get(self, request: Request):
#         exception = db["exceptions"].find_one(
#             {"_id": ObjectId(request.path_params["_id"])}
#         )
#
#         if exception is None:
#             raise HTTPException(status_code=404)
#
#         return templates.TemplateResponse(
#             "report.html", {"request": request, "exception": exception}
#         )


class LoginGate(HTTPEndpoint):
    async def get(self, request: Request):
        secret = request.path_params["secret"]

        link_data: VerificationLink = VerificationLink.objects(secret_code=secret).first()
        if not link_data:
            raise HTTPException(404, 'Takie wiązanie nie istnieje')

        return templates.TemplateResponse(
            "oauth-login.html",
            {
                "request": request,
                "secret": secret,
                "redirect": f"{os.getenv('VERIFICATION_URL')}login",
            },
        )

    async def post(self, request: Request):
        form = await request.form()
        secret = form["state"]
        credential = form["credential"]
        # link_data = db["link"].find_one({"secret": secret})
        link_data: VerificationLink = VerificationLink.objects(secret_code=secret).first()

        if not link_data:
            raise HTTPException(404)

        if link_data.trust:
            return PlainTextResponse('Już dokonano rejestracji z tego linku!')

        try:
            id_info = id_token.verify_oauth2_token(
                credential,
                requests.Request(),
                "415405805208-n7irpdbl5go8cs5jf15i8005gd53iume.apps.googleusercontent.com",
            )
            assert id_info.get("sub") is not None
        except ValueError:
            # Invalid token
            return PlainTextResponse("Fuck you", status_code=400)

        previous_verification = TrustedUser.objects(
            Q(identity=link_data.identity) | Q(student_number=id_info["email"][:6])
        ).first()

        if previous_verification:
            return PlainTextResponse(
                f"Te dane już są połączone z {previous_verification}"
            )

        async with rest.acquire(os.getenv("DISCORD_TOKEN"), "Bot") as client:
            user = await client.fetch_user(link_data.identity.user_id)
            when = datetime.now()

            guild_conf: GuildConfiguration = GuildConfiguration\
                .objects(managed_by__guild_id=link_data.identity.guild_id).first()
            await client.add_role_to_member(
                link_data.identity.guild_id, link_data.identity.user_id, guild_conf.trusted_role_id
            )

            trust = TrustedUser()
            trust.identity = link_data.identity
            trust.student_number = id_info["email"][:6]
            trust.verification_method = VerificationMethod.OAUTH
            trust.verification_context = id_info | {"credential": credential}
            trust.save()

            embed = embed_success(
                "Pomyślnie zweryfikowano! Możesz zarządzać weryfikacją poprzez komendę `/manage self`"
            )
            embed.add_field("Data weryfikacji", when.isoformat())
            embed.add_field("Powiązany numer studenta", id_info["email"])
            embed.add_field("Metoda weryfikacji", "OAuth login")

            await user.send(embed=embed)

            link_data.trust = trust
            link_data.save()

        return templates.TemplateResponse("verified.html", {"request": request})


class GuildInviteEndpoint(HTTPEndpoint):
    def get(self, request: Request):
        return templates.TemplateResponse("guild-invite.html", {"request": request})

    async def post(self, request: Request):
        async with ClientSession() as cs:
            async with cs.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={
                    "secret": env.get("RECAPTCHA_SECRET"),
                    "response": (await request.form()).get("g-recaptcha-response"),
                },
            ) as response:
                if (await response.json())["success"]:
                    return templates.TemplateResponse(
                        "guild-invited.html",
                        {
                            "request": request,
                            "invitation_url": str(
                                await gen_guild_invite(874612942623113216)
                            ),
                        },
                    )


routes = [
    Route("/", AboutPage),
    Route("/oauth/{secret}", LoginGate),
    Route("/login", LoginGate),
    # Route("/exceptions/{_id}", ExceptionsPreviewer),
    Route("/join/pjatk2021", GuildInviteEndpoint),
]
app = Starlette(routes=routes)
