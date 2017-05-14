#! /usr/bin/env python
from telegram.ext import Updater
from apitoken import apitoken, my_user_id
from telegram.ext import CommandHandler, MessageHandler, Filters, Job
from collections import defaultdict
from validate_email import validate_email
import re
import logging
import argparse
import db
from cStringIO import StringIO
import datetime
import smtplib
from email.mime.text import MIMEText

# Globals

logger = logging.getLogger()
args = None
sendinterval = 1440

# Helper functions

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v',
                        help="increase verbosity",
                        action="count", dest="verb", default=0)
    parser.add_argument('-d',
                        help="SQLite database file",
                        action="store", dest="db", default=None)
    parser.add_argument('-l',
                        help="Log to file instead of stdout",
                        action="store", dest="logfile", default=None)

    parser.add_argument('-t',
                        help="Send digest emails every X minutes",
                        action="store", dest="sendinterval", default=1440,
                        type=int)

    args = parser.parse_args()

    global sendinterval
    sendinterval = args.sendinterval

    if args.db:
        db.setup_db(args.db)
    else:
        db.setup_db(":memory:")

    if args.logfile:
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filename=args.logfile,
            level=logging.INFO)
    else:
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO)

    if args.verb:
        logger.setLevel((50 - args.verb*10))


def parsemail(mail_string):

    logging.debug("Parsing string: %s" % mail_string)
    email_re = re.search(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-.]+\.[a-zA-Z]{2,})",
                         mail_string)
    if email_re:
        email = email_re.group()
        if validate_email(email):
            logging.debug("Extraced valid email %s" % email)
            return email

    logging.debug("Could not extract valid email %s" % mail_string)
    return ''


def prettyprintleft(ul, u, d, s):
    l = ul.encode('ascii', 'ignore').encode('ascii')
    left_margin = 32  # max username width
    if d:
        print >> s, ""
        print >> s, d[:left_margin-1].ljust(left_margin+1)
    print >> s, u.rjust(left_margin+1),
    line_width = 40
    first_line = l[0:line_width]
    print >> s, "|", first_line.ljust(line_width), "|"
    for line in [l[i:i+line_width] for i in range(line_width, len(l), line_width)]:
        print >> s, "".ljust(left_margin+1), "|", line.ljust(line_width), "|"


def prettyprintright(ul, u, d, s):

    l = ul.encode('ascii', 'ignore').encode('ascii')
    left_margin = 32  # max username width
    if d:
        print >> s, ""
        print >> s, d[:left_margin-1].ljust(left_margin+1)
    print >> s, "".rjust(left_margin+1),
    line_width = 40
    first_line = l[0:line_width]
    print >> s, "|", first_line.ljust(line_width), "|", u
    for line in [l[i:i+line_width] for i in range(line_width, len(l),
                                                  line_width)]:
        print >> s, "".ljust(left_margin+1), "|", line.ljust(line_width), "|"


def dumpmessages(chat_id):
    msgs = db.dumpmessages(chat_id)
    s = StringIO()
    left = True
    if len(msgs):
        prettyprintleft(msgs[0][2], msgs[0][0], str(msgs[0][1]), s)
    if len(msgs) > 1:
        for i in range(1, len(msgs)):
            if msgs[i-1][0] != msgs[i][0]:
                left = not left
            if msgs[i][1] - msgs[i-1][1] > datetime.timedelta(0, 300):
                datesent = str(msgs[i][1])
            else:
                datesent = ""

            if left:
                prettyprintleft(msgs[i][2], msgs[i][0], datesent, s)
            else:
                prettyprintright(msgs[i][2], msgs[i][0], datesent, s)
    return s.getvalue()


def sendmessages(chat_id):

    fr, ml, enabled = db.getaddresses(chat_id)
    if fr and ml and enabled:
        m = dumpmessages(chat_id)
        sendemail(m, "", fr, ml)
        logger.info("Sent digest email for group "+str(chat_id))
    else:
        logger.info("Won't send email, as I am missing addresses for group " +
                    str(chat_id) + " or conf is disabled")


def sendemail(body, groupname, fromemail, mailinglist):

    msg = MIMEText(body)

    msg['Subject'] = "[mailinglistbot] Digest conversations from"\
                     " Telegram group " + groupname
    msg['From'] = fromemail
    msg['To'] = mailinglist

    try:
        s = smtplib.SMTP('localhost')
    except:
        logger.error("Could not open socket to localhost:25."
                     " Is SMTP running on this server?")
    try:
        s.sendmail(msg['From'], [msg['To']], msg.as_string())
        s.quit()
    except:
        logger.error("Could not send email!")


def senddigest(bot=None, job=None):
    groups = db.get_active_groups()
    print groups
    logger.info("Starting to send digest messages")
    for g in groups:
        sendmessages(g)


# Message/Command handlers


def start(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id,
                    text="Hello, if you include me "
                         "to a telegram group, i will read all "
                         "the messages and send a daily digest "
                         "in a mailing list of your choice.")


def mailinglist(bot, update):
    logging.debug("Received message: " + str(update))
    email = parsemail(update.message.text)
    if email:
        db.savemailinglist(update.message.chat_id, email,
                           update.message.chat.title)
        bot.sendMessage(chat_id=update.message.chat_id,
                        text="OK, " + email +
                             " was saved as the mailinglist address")
        logger.info("Changed mailinglist address to "+email)
    else:
        bot.sendMessage(chat_id=update.message.chat_id,
                        text="Not OK: " + update.message.text +
                             " is not a valid address")


def fromaddress(bot, update):
    pass
    # I decided to keep the from email static to bot@firenze.ninux.network
    logging.debug("Received message: " + str(update))
    email = parsemail(update.message.text)
    if email:
        db.savefromaddress(update.message.chat_id, email,
                           update.message.chat.title)
        bot.sendMessage(chat_id=update.message.chat_id,
                        text="OK, " + email +
                             " was saved as the from address")
        logger.info("Changed from address to "+email)
    else:
        bot.sendMessage(chat_id=update.message.chat_id,
                        text="Not OK: " + update.message.text +
                             " is not a valid address")


def messagehandler(bot, update):

    # FIXME we need a Filter for this, not do it here
    if update.message.new_chat_member and update.message.new_chat_member.id \
            == my_user_id or update.message.group_chat_created:
            db.savegroup(update.message.chat_id, update.message.chat.title)
    elif update.message.left_chat_member:
        if update.message.left_chat_member.id == my_user_id:
            db.delgroup(update.message.chat_id)


def texthandler(bot, update):
    if update.message.chat.type == "group":
        db.savemessage(update.message.chat_id,
                       update.message.from_user.username,
                       update.message.text, update.message.chat.title,
                       update.message.from_user.id)


def dumpmessages_h(bot, update):
    chat_id = update.message.chat.id
    return dumpmessages(chat_id)


def enable_h(bot, update, job_queue, chat_data):
    chat_id = update.message.chat.id
    fromemail, mailinglist, enabled = db.getaddresses(chat_id)
    if not fromemail:
        bot.sendMessage(chat_id=update.message.chat_id,
                        text="Can not enable the bot, missing 'From' email")
        return
    if not mailinglist:
        bot.sendMessage(chat_id=update.message.chat_id,
                        text="Can not enable the bot, missing 'mailinglist'"
                             " email")
        return
    if not enabled:
        if db.enable(chat_id):
            bot.sendMessage(chat_id=update.message.chat_id,
                            text="Ok, will send digest once every %s minutes"
                            " to %s from %s" %
                            (str(sendinterval), mailinglist, fromemail))

            # TODO interval should be a command parameter, with a lower bound
            job = Job(senddigest, sendinterval*60, repeat=True)
            chat_data['job'] = job
            job_queue.put(job)
    else:
            bot.sendMessage(chat_id=update.message.chat_id,
                            text="Group already enabled")


def disable_h(bot, update, job_queue, chat_data):
    chat_id = update.message.chat.id
    if db.disable(chat_id):
            bot.sendMessage(chat_id=update.message.chat_id,
                            text="Group disabled")
            if 'job' in chat_data:
                job = chat_data['job']
                job.schedule_removel()
                del chat_data['job']


def unknown(bot, update):
        bot.sendMessage(chat_id=update.message.chat_id,
                        text="Sorry, I didn't understand that command.")


def sendmessages_h(bot, update):

    senddigest()
    #chat_id = update.message.chat.id
    #sendmessages(chat_id)

# main function


def run():
    parse_arguments()
    updater = Updater(token=apitoken)
    dispatcher = updater.dispatcher

    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)
    mailinglist_handler = CommandHandler('mailinglist', mailinglist)
    dispatcher.add_handler(mailinglist_handler)
    #fromaddress_handler = CommandHandler('from', fromaddress)
    #dispatcher.add_handler(fromaddress_handler)
    dumpmessages_handler = CommandHandler('messages', dumpmessages_h)
    dispatcher.add_handler(dumpmessages_handler)
    sendmessages_handler = CommandHandler('sendmessages', sendmessages_h)
    dispatcher.add_handler(sendmessages_handler)

    enable_handler = CommandHandler('enable', enable_h,
                                    pass_job_queue=True, pass_chat_data=True)
    dispatcher.add_handler(enable_handler)

    disable_handler = CommandHandler('disable', disable_h,
                                     pass_job_queue=True, pass_chat_data=True)
    dispatcher.add_handler(disable_handler)

    unknown_handler = MessageHandler(Filters.command, unknown)
    dispatcher.add_handler(unknown_handler)

    text_handler = MessageHandler(Filters.text, texthandler)
    dispatcher.add_handler(text_handler)

    message_handler = MessageHandler(Filters.all, messagehandler,
                                     pass_job_queue=True, pass_chat_data=True)
    dispatcher.add_handler(message_handler)

    updater.start_polling()
    updater.idle()

    db.close_db()
