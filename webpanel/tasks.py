import os
import re

from hikari import RESTApp, Embed

from sendgrid import SendGridAPIClient, Mail

from shared.colors import *
from shared.documents import VerificationRequest, TrustedUser, VerificationMethod, GuildConfiguration, Reviewer


async def apply_trusted_role(tu: TrustedUser, conf: GuildConfiguration):
    async with RESTApp().acquire(os.getenv("DISCORD_TOKEN"), "Bot") as bot:
        user = await bot.fetch_user(tu.identity.user_id)
        await bot.add_role_to_member(
            conf.guild_id, user, conf.trusted_role_id
        )

        embed = Embed(
            title='Zrobione!',
            description="Pomyślnie zweryfikowano! Możesz zarządzać weryfikacją poprzez komendę `/manage sign-out`",
            color=OK
        )
        embed.add_field("Data weryfikacji", tu.when.isoformat())
        embed.add_field("Powiązany numer studenta", tu.student_number)
        embed.add_field("Metoda weryfikacji", tu.verification_method.value)

        await user.send(embed=embed)


async def send_trust_confirmation(vr: VerificationRequest):
    sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
    mail = Mail(
        from_email=('gadoneko@free.itny.me', 'ガード猫'),
        to_emails=vr.google.email
    )
    mail.dynamic_template_data = {
        'who': vr.google.name,
        'student_num': vr.trust.student_number,
        'guild': vr.identity.guild_name,
        'discord': vr.identity.user_name,
    }
    mail.template_id = 'd-409b6361287f46a7949f030b399b4817'
    sg.send(mail)


async def send_rejection_mail(vr: VerificationRequest, message: str):
    sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
    mail = Mail(
        from_email=('gadoneko@free.itny.me', 'ガード猫'),
        to_emails=vr.google.email
    )
    mail.dynamic_template_data = {
        'guild': vr.identity.guild_name,
        'reason': message
    }
    mail.template_id = 'd-774ffd7fe61e457b85b6674cc1d0e001'
    sg.send(mail)


async def send_rejection_dm(vr: VerificationRequest, message: str):
    async with RESTApp().acquire(os.getenv("DISCORD_TOKEN"), "Bot") as bot:
        user = await bot.fetch_user(vr.identity.user_id)

        embed = Embed(
            title='O nie!',
            description=f"Nie udało się pomyślnie zweryfikować twojego konta z powodu: {message}",
            color=WARN
        )

        await user.send(embed=embed)


async def notify_requested_id(vr: VerificationRequest):
    async with RESTApp().acquire(os.getenv("DISCORD_TOKEN"), "Bot") as bot:
        user = await bot.fetch_user(vr.identity.user_id)
        await user.send(
            embed=Embed(
                title='Papers please!',
                description=f'Weryfikujący poprosił o wysłanie legitymacji studenckiej w celu potwierdzenia tożsamości, odwiedź {os.getenv("VERIFICATION_URL")}verify/{vr.code} aby przesłać dokument.',
                url=f'{os.getenv("VERIFICATION_URL")}verify/{vr.code}',
                colour=WARN
            )
        )
        # await user.send(f'Weryfikujący poprosił o wysłanie legitymacji studenckiej w celu potwierdzenia tożsamości, odwiedź {os.getenv("VERIFICATION_URL")}verify/{vr.code} aby przesłać dokument.')


async def notify_reviewers(vr: VerificationRequest):
    async with RESTApp().acquire(os.getenv("DISCORD_TOKEN"), "Bot") as bot:
        rs = Reviewer.objects(identity__guild_id=vr.identity.guild_id)

        for reviewer in [await bot.fetch_user(r.identity.user_id) for r in rs]:
            await reviewer.send(
                embed=Embed(
                    title='Nowa osoba do weryfikacji!',
                    description=f'{vr.identity.user_name} oczekuje na weryfikację!',
                    url='https://free.itny.me/admin/login',
                    colour=INFO
                )
            )
