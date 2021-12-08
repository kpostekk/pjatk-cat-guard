from datetime import datetime
from enum import Enum

from lightbulb import Context
from mongoengine import Document, LongField, EnumField, DateTimeField, DynamicField, EmbeddedDocumentField, \
    EmbeddedDocument, StringField, ReferenceField, NULLIFY, DynamicDocument, ListField


class VerificationMethod(Enum):
    OAUTH = 'oauth'  # user verified by OAuth flow
    ROLE_ASSIGNED = 'role'  # user verified manually by staff
    ROLE_ENFORCED = 'enforced'  # staff has run command
    MIGRATED = 'migrated'  # user added to the collection due to migration
    CONTEXT_PROVIDED = 'context'  # user added to the collection, while checking his permissions


class UserIdentity(EmbeddedDocument):
    guild_id = LongField(required=True)
    guild_name = StringField(null=True)
    user_id = LongField(required=True)
    user_name = StringField(null=True)

    @staticmethod
    def from_context(ctx: Context):
        uid = UserIdentity()
        uid.guild_id = ctx.get_guild().id
        uid.user_id = ctx.user.id
        uid.guild_name = ctx.get_guild().name
        uid.user_name = str(ctx.user)
        return uid


class TrustedUser(Document):
    identity = EmbeddedDocumentField(UserIdentity, unique=True, required=True)
    verification_method = EnumField(VerificationMethod, required=True)
    verification_context = DynamicField()
    student_number = StringField(r's\d{5}')
    when = DateTimeField(default=datetime.now)


class GuildConfiguration(DynamicDocument):
    guild_id = LongField(required=True)
    trusted_role_id = LongField(required=True)
    additional_staff = ListField(LongField())
    additional_staff_roles = ListField(LongField())


class VerificationLink(Document):
    identity = EmbeddedDocumentField(UserIdentity, required=True)
    secret_code = StringField(required=True)
    trust = ReferenceField(TrustedUser, reverse_delete_rule=NULLIFY, null=True)


class CaptchaInvites(Document):
    identity = EmbeddedDocumentField(UserIdentity, required=True)
    invite_alias = StringField(required=True, unique=True)


class ExecutedCommand(EmbeddedDocument):
    name = StringField()
    options = DynamicField()


class AuditLog(Document):
    identity = EmbeddedDocumentField(UserIdentity, required=True)
    exec_cmd = EmbeddedDocumentField(ExecutedCommand, required=True)
    interaction = LongField(required=True)
    requested = DateTimeField(default=datetime.now)
    completed = DateTimeField(null=True)

