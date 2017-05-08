#! /usr/bin/env python
from telegram.ext import Updater
from apitoken import apitoken
from telegram.ext import CommandHandler, MessageHandler, Filters
from collections import defaultdict
from validate_email import validate_email
import re
import logging
import argparse

config = defaultdict(dict)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger()


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v',
                        help="increase verbosity",
                        action="count", dest="verb", default=0)
    args = parser.parse_args()
    if args.verb:
        logger.setLevel((50 - args.verb*10))


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
        config[update.message.chat_id] = {'mailinglist': '', 'from': ''}


def mailinglist(bot, update):
    logging.debug("Received message: " + str(update))
    email = parsemail(update.message.text)
    if email:
        config[update.message.chat_id] = {'mailinglist': email}
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
        config[update.message.chat_id] = {'fromaddress': email}
        bot.sendMessage(chat_id=update.message.chat_id,
                        text="OK, " + email +
                             "was saved as the from address")
    else:
        bot.sendMessage(chat_id=update.message.chat_id,
                        text="Not OK: " + update.message.text +
                             " is not a valid address")


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

unknown_handler = MessageHandler(Filters.command, unknown)
dispatcher.add_handler(unknown_handler)


updater.start_polling()
