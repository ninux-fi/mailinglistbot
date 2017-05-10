import datetime
from peewee import Model, CharField, IntegerField, ForeignKeyField,\
        DateTimeField, PrimaryKeyField, BooleanField
from peewee import OperationalError
from playhouse.sqlite_ext import SqliteExtDatabase

db = SqliteExtDatabase(None)

# models


class BaseModel(Model):
    class Meta:
        database = db


class telegramgroup(BaseModel):
    groupid = PrimaryKeyField()
    groupname = CharField()


class config(BaseModel):
    groupid = ForeignKeyField(telegramgroup, primary_key=True,
                              to_field='groupid')
    fromemail = CharField(default="")
    mailinglist = CharField(default="")
    enabled = BooleanField(default=True)


class user(BaseModel):
    userid = PrimaryKeyField()
    useradded = DateTimeField(default=datetime.datetime.now)
    username = CharField()


class message(BaseModel):
    groupid = ForeignKeyField(telegramgroup, to_field='groupid')
    fromuser = ForeignKeyField(user, to_field='userid')
    timesent = DateTimeField(default=datetime.datetime.now)
    text = CharField()


# methods

def savemailinglist(chat_id, email, title):
    try:
        c = config.get(config.groupid == chat_id)
    except config.DoesNotExist:
        raise
    c.mailinglist = email
    c.save()


def savefromaddress(chat_id, email, title):

    try:
        c = config.get(config.groupid == chat_id)
        c.fromemail = email
    except config.DoesNotExist:
        raise
    c.save()


def savemessage(chat_id, sender, text, title, sender_id):

    try:
        c = telegramgroup.get(telegramgroup.groupid == chat_id)
    except telegramgroup.DoesNotExist:
        raise

    try:
        c = user.get(user.userid == sender_id)
    except user.DoesNotExist:
        u = user.create(userid=sender_id, username=sender)
        u.save()

    c = message.create(groupid=chat_id, fromuser=sender_id, text=text)
    c.save()


def delgroup(chat_id):

    try:
        c = config.get(config.groupid == chat_id)
    except:
        raise
    c.enabled = False
    c.save()

    try:
        g = telegramgroup.get(telegramgroup.groupid == chat_id)
    except telegramgroup.DoesNotExist:
        raise
    g.delete_instance()


def savegroup(chat_id, title):

    try:
        g = telegramgroup.get(telegramgroup.groupid == chat_id)
    except telegramgroup.DoesNotExist:
        g = telegramgroup.create(groupid=chat_id, groupname=title)
        g.save()

    try:
        c = config.get(groupid=chat_id)
        c.enabled = True
    except config.DoesNotExist:
        c = config.create(groupid=chat_id)
    c.save()


def setup_db(dbfile):
    db.init(dbfile)
    db.connect()
    try:
        db.create_tables([config, user, message, telegramgroup])
    except OperationalError:
        pass


def close_db():
    db.close()
