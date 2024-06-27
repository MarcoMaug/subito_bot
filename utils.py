import json
import requests
import logging
from logging.handlers import RotatingFileHandler

def set_log(logname, level, logger_name):
    level_diz = {'debug': logging.DEBUG, 'info': logging.INFO, 'warning': logging.WARNING}
    logger = logging.getLogger(logger_name)
    logger.setLevel(level_diz[level.lower()])
    handler = RotatingFileHandler(logname, maxBytes=100000, backupCount=5, encoding='utf-8')
    handler.setLevel(level_diz[level.lower()])
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

def read_json_file(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

def read_account_info(json_data):
    token=json_data["token"]
    chat_id=json_data["chat_id"]
    return token, chat_id

def send_message(message, token, chat_id):
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}"
    response = requests.get(url).json()
    return response.status_code