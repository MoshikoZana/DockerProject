import telebot
from loguru import logger
import os
import time
from telebot.types import InputFile
from polybot.img_proc import Img
import requests


class Bot:

    def __init__(self, token, telegram_chat_url):
        # create a new instance of the TeleBot class.
        # all communication with Telegram servers are done using self.telegram_bot_client
        self.telegram_bot_client = telebot.TeleBot(token)

        # remove any existing webhooks configured in Telegram servers
        self.telegram_bot_client.remove_webhook()
        time.sleep(0.5)

        # set the webhook URL
        self.telegram_bot_client.set_webhook(url=f'{telegram_chat_url}/{token}/', timeout=60)

        logger.info(f'Telegram Bot information\n\n{self.telegram_bot_client.get_me()}')

    def send_text(self, chat_id, text):
        self.telegram_bot_client.send_message(chat_id, text)

    def send_text_with_quote(self, chat_id, text, quoted_msg_id):
        self.telegram_bot_client.send_message(chat_id, text, reply_to_message_id=quoted_msg_id)

    def is_current_msg_photo(self, msg):
        return 'photo' in msg

    def download_user_photo(self, msg):
        """
        Downloads the photos that sent to the Bot to `photos` directory (should be existed)
        :return:
        """
        if not self.is_current_msg_photo(msg):
            raise RuntimeError(f'Message content of type \'photo\' expected')

        file_info = self.telegram_bot_client.get_file(msg['photo'][-1]['file_id'])
        data = self.telegram_bot_client.download_file(file_info.file_path)
        folder_name = file_info.file_path.split('/')[0]

        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        with open(file_info.file_path, 'wb') as photo:
            photo.write(data)

        return file_info.file_path

    def send_photo(self, chat_id, img_path):
        if not os.path.exists(img_path):
            raise RuntimeError("Image path doesn't exist")

        self.telegram_bot_client.send_photo(
            chat_id,
            InputFile(img_path)
        )

    def handle_message(self, msg):
        """Bot Main message handler"""
        logger.info(f'Incoming message: {msg}')
        self.send_text(msg['chat']['id'], f'Your original message: {msg["text"]}')


class QuoteBot(Bot):
    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')

        if msg["text"] != 'Please don\'t quote me':
            self.send_text_with_quote(msg['chat']['id'], msg["text"], quoted_msg_id=msg["message_id"])


def swear_words_github():
    repo = ('https://raw.githubusercontent.com/MoshikoZana/List-of-Dirty-Naughty-Obscene-and-Otherwise-Bad-Words'
            '/master/en')
    response = requests.get(repo)
    if response.status_code == 200:
        swear_words = [line.strip() for line in response.text.split('\n')]
        return swear_words
    else:
        return []


class ObjectDetectionBot(Bot):
    def __init__(self, token, telegram_chat_url=None):
        super().__init__(token, telegram_chat_url)
        self.swear_words_count = 0
        self.swear_words = swear_words_github()
        self.swear_response = [
            "Excuse me... who do you think I am that you're being filthy here? Stop it.",
            "Seriously? You're just going to continue to swear? I'm an image processing bot not a prostitute!",
            "(╯°□°)╯︵ ┻━┻ WHAT'S WRONG WITH YOU!"
        ]
        self.default_response = "Sorry, I didn't understand that. Type /help for available commands."

    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')
        if 'text' in msg:
            message = msg['text'].lower()

            if message.startswith('/'):
                self.handle_command(msg, message)
            else:
                self.handle_non_command(msg, message)
        if self.is_current_msg_photo(msg):
            caption = msg.get('caption', '').lower()
            if 'rotate' in caption:
                photo_download = self.download_user_photo(msg)
                image = Img(photo_download)
                image.rotate()
                rotated_image = image.save_img()
                self.send_photo(msg['chat']['id'], rotated_image)

            if 'blur' in caption:
                photo_download = self.download_user_photo(msg)
                image = Img(photo_download)
                image.blur()
                blured_image = image.save_img()
                self.send_photo(msg['chat']['id'], blured_image)

            if 'contour' in caption:
                photo_download = self.download_user_photo(msg)
                image = Img(photo_download)
                image.contour()
                contour_image = image.save_img()
                self.send_photo(msg['chat']['id'], contour_image)

    def handle_command(self, msg, command):
        if command == '/start':
            start_response = "Hey there! Welcome to Image Processing Bot! For available commands type \"/help\""
            self.send_text(msg['chat']['id'], start_response)
        elif command == '/help':
            help_response = ("How to use Image Processing Bot: \nSimply upload a photo to me, and add your desired "
                             "filter in the caption.\nSupported filters: Rotate, Blur, Contour, Salt n pepper, "
                             "concat and segment.")
            self.send_text(msg['chat']['id'], help_response)
        else:
            self.send_text(msg['chat']['id'], self.default_response)

    def handle_non_command(self, msg, message):
        if message in self.swear_words:
            bot_response = self.swear_response[self.swear_words_count % len(self.swear_response)]
            self.swear_words_count = (self.swear_words_count + 1) % len(self.swear_response)
            self.send_text(msg['chat']['id'], bot_response)
        elif 'thanks' in message or 'thank' in message:
            gratitude_response = ("You're welcome! If you need any further assistance, try using the available "
                                  "commands :)")
            self.send_text(msg['chat']['id'], gratitude_response)
        else:
            self.send_text(msg['chat']['id'], self.default_response)

    #if self.is_current_msg_photo(msg):
        photo_path = self.download_user_photo(msg)

        # TODO upload the photo to S3
        # TODO send a request to the `yolo5` service for prediction
        # TODO send results to the Telegram end-user



