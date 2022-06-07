from random import SystemRandom
from string import ascii_letters, digits
from telegram.ext import CommandHandler
from threading import Thread
from time import sleep

from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import sendMessage, sendMarkup, deleteMessage, delete_all_messages, update_all_messages, sendStatusMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.mirror_utils.status_utils.clone_status import CloneStatus
from bot import dispatcher, LOGGER, CLONE_LIMIT, STOP_DUPLICATE, download_dict, download_dict_lock, Interval
from bot.helper.ext_utils.bot_utils import get_readable_file_size, is_gdrive_link, is_gdtot_link, is_appdrive_link, new_thread
from bot.helper.mirror_utils.download_utils.direct_link_generator import gdtot, appdrive
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException

def _clone(message, bot, multi=0):
    args = message.text.split(" ", maxsplit=1)
    reply_to = message.reply_to_message
    link = ''
    if len(args) > 1:
        link = args[1]
        if link.isdigit():
            multi = int(link)
            link = ''
        elif message.from_user.username:
            tag = f"@{message.from_user.username}"
        else:
            tag = message.from_user.mention_html(message.from_user.first_name)
    if reply_to is not None:
        if len(link) == 0:
            link = reply_to.text
        if reply_to.from_user.username:
            tag = f"@{reply_to.from_user.username}"
        else:
            tag = reply_to.from_user.mention_html(reply_to.from_user.first_name)
    is_appdrive = is_appdrive_link(link)
    is_gdtot = is_gdtot_link(link)
    if (is_appdrive or is_gdtot):
        try:
            msg = sendMessage(f"<b>Processing:</b> <code>{link}</code>", context.bot, update)
            LOGGER.info(f"Processing: {link}")
            if is_appdrive:
                appdict = appdrive(link)
                link = appdict.get('gdrive_link')
            if is_gdtot:
                link = gdtot(link)
            deleteMessage(context.bot, msg)
        except ExceptionHandler as e:
            deleteMessage(context.bot, msg)
            LOGGER.error(e)
            return sendMessage(str(e), context.bot, update)
    if is_gdrive_link(link):
        msg = sendMessage(f"<b>Cloning:</b> <code>{link}</code>", context.bot, update)
        LOGGER.info(f"Cloning: {link}")
        status_class = CloneStatus()
        gd = GoogleDriveHelper()
        sendCloneStatus(link, msg, status_class, update, context)
        result = gd.clone(link, status_class)
        deleteMessage(context.bot, msg)
        status_class.set_status(True)
        sendMessage(result, context.bot, update)
        if is_gdtot:
            LOGGER.info(f"Deleting: {link}")
            gd.deleteFile(link)
        if is_appdrive:
            if appdict.get('link_type') == 'login':
                LOGGER.info(f"Deleting: {link}")
                gd.deleteFile(link)
    else:
        sendMessage("<b>Send a Drive / AppDrive / DriveApp / GDToT link along with command</b>", context.bot, update)
        LOGGER.info("Cloning: None")

@new_thread
def cloneNode(update, context):
    _clone(update.message, context.bot)

clone_handler = CommandHandler(BotCommands.CloneCommand, cloneNode, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
dispatcher.add_handler(clone_handler)
