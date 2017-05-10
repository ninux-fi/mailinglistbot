#! /usr/bin/env python
from telegram.ext import Updater
from apitoken import apitoken
from telegram.ext import CommandHandler, MessageHandler, Filters
from collections import defaultdict
from validate_email import validate_email
import re
import logging
import argparse
import db

config = defaultdict(dict)
logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO)
logger = logging.getLogger()

messages = defaultdict(list)

my_user_id = 393647190

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v',
                        help="increase verbosity",
                        action="count", dest="verb", default=0)
    parser.add_argument('-d',
                        help="SQLite database file",
                        action="store", dest="db", default=None)
    args = parser.parse_args()

    if args.verb:
        logger.setLevel((50 - args.verb*10))

    if args.db:
        db.setup_db(args.db)
    else:
        db.setup_db(":memory:")


def parsemail(mail_string):
    logging.debug("Parsing string: %s" % mail_string)
    email_re = re.search(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.])",
                         mail_string)
    if email_re:
        email = email_re.group()
        if validate_email(email):
            logging.debug("Extraced valid email %s" % email)
            return email

    logging.debug("Could not extrac valid email %s" % mail_string)
    return ''


def start(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id,
                    text="Hello, if you include me as an admin "
                          "to a telegram group, i will read all "
                          "the messages and send a daily digest "
                          "in a mailing list of your choice.")
    if update.message.chat_id not in config:
        config[update.message.chat_id] = {'name': update.message.chat.title,
                                          'mailinglist': '', 'from': ''}


def dumpconfig(bot, update):
    for k, v in config.items():
        print k
        for kk, vv in config[k].items():
            print kk, ":", vv
    for chat_id, v in messages.items():
        print chat_id
        for msg in v:
            print " ", msg


def mailinglist(bot, update):
    logging.debug("Received message: " + str(update))
    email = parsemail(update.message.text)
    if email:
        db.savemailinglist(update.message.chat_id, email,
                           update.message.chat.title)
        bot.sendMessage(chat_id=update.message.chat_id,
                        text="OK, " + email +
                             "was saved as the mailinglist address")
    else:
        bot.sendMessage(chat_id=update.message.chat_id,
                        text="Not OK: " + update.message.text +
                             " is not a valid address")


def fromaddress(bot, update):
    logging.debug("Received message: " + str(update))
    email = parsemail(update.message.text)
    if email:
        db.savefromaddress(update.message.chat_id, email,
                           update.message.chat.title)
        bot.sendMessage(chat_id=update.message.chat_id,
                        text="OK, " + email +
                             "was saved as the from address")
    else:
        bot.sendMessage(chat_id=update.message.chat_id,
                        text="Not OK: " + update.message.text +
                             " is not a valid address")


def messagehandler(bot, update):

    if update.message.new_chat_member:
        if update.message.new_chat_member.id == my_user_id:
            db.savegroup(update.message.chat_id, update.message.chat.title)
    elif update.message.left_chat_member:
        if update.message.left_chat_member.id == my_user_id:
            db.delgroup(update.message.chat_id)
    elif update.message.chat.type == "group":
        db.savemessage(update.message.chat_id,
                       update.message.from_user.username,
                       update.message.text, update.message.chat.title,
                       update.message.from_user.id)

def dumpmessages(bot, update):
    chat_id = update.message.chat.id
    msgs = db.dumpmessages(chat_id)
    for m in msgs:
        print m[0], m[1], m[2]

def unknown(bot, update):
        bot.sendMessage(chat_id=update.message.chat_id,
                        text="Sorry, I didn't understand that command.")



parse_arguments()
updater = Updater(token=apitoken)
dispatcher = updater.dispatcher


start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)
mailinglist_handler = CommandHandler('mailinglist', mailinglist)
dispatcher.add_handler(mailinglist_handler)
fromaddress_handler = CommandHandler('from', fromaddress)
dispatcher.add_handler(fromaddress_handler)
dumpconfig_handler = CommandHandler('dumpconfig', dumpconfig)
dispatcher.add_handler(dumpconfig_handler)
dumpmessages_handler = CommandHandler('messages', dumpmessages)
dispatcher.add_handler(dumpmessages_handler)

unknown_handler = MessageHandler(Filters.command, unknown)
dispatcher.add_handler(unknown_handler)

message_handler = MessageHandler(Filters.all, messagehandler)
dispatcher.add_handler(message_handler)

updater.start_polling()
updater.idle()

db.close_db()
