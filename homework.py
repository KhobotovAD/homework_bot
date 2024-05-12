import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telebot
from dotenv import load_dotenv

from exceptions import (EmptyAPIResponse, HttpStatusNotOK, RequestError)

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

GREETINGS_TEXT = (
    'Привет, я буду оповещать тебя'
    ' о статусе твоей домашней работы!!!'
)

SUCCESSFUL_SENDING_TEXT = 'Сообщение успешно отправлено'

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Функция проверяет доступность переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def send_message(bot, message):
    """Функция отправляет сообщение в Telegram-бот."""
    logging.debug('Отправляется сообщение в Telegram...')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Cообщение в Telegram отправлено.')
    except telebot.apihelper.ApiException as error:
        logging.error('При отправке сообщения в Telegram '
                      f'произошла ошибка {error}')


def get_api_answer(timestamp):
    """Функция запрашивает Endpoint API-сервиса."""
    data_for_request = {
        'url': ENDPOINT,
        'params': {'from_date': timestamp},
        'headers': HEADERS,
    }
    logging.debug('Запрос к эндпоинту {url} API-сервиса '
                  'c данными заголовка {headers} и параметрами '
                  '{params} отправлено.'.format(**data_for_request))
    try:
        homework_statuses = requests.get(**data_for_request)
    except requests.exceptions.RequestException as error:
        raise RequestError(f'Сбой в работе программы: Эндпоинт {ENDPOINT} '
                           f'недоступен. Код ответа API: {error}.')
    homework_status_code = homework_statuses.status_code
    if homework_status_code != HTTPStatus.OK:
        raise HttpStatusNotOK('Статус ответа API не 200, '
                              f'а {homework_statuses.status_code}')
    return homework_statuses.json()


def check_response(response):
    """Функция проверяет ответ API на соответствие документации API сервиса."""
    if not isinstance(response, dict):
        raise TypeError('В ответе API домашки "response" '
                        'по типу не является словарем.')
    if 'homeworks' not in response:
        raise EmptyAPIResponse(
            'В ответе API домашки нет ключа "homeworks".'
        )
    if 'current_date' not in response:
        raise EmptyAPIResponse(
            'В ответе API домашки нет ключа "current_date".'
        )
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError('В ответе API домашки под ключом "homeworks" '
                        'данные приходят не в виде списка.')
    return homeworks


def parse_status(homework):
    """Функция извлекает информацию о домашней работе и статус этой работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if 'homework_name' not in homework:
        raise KeyError(
            'В ответе API домашки нет ключа "homework_name".'
        )
    if 'status' not in homework:
        raise KeyError(
            'В ответе API домашки нет ключа "status".'
        )
    if homework_status not in HOMEWORK_VERDICTS.keys():
        raise KeyError('Отсутствует допустимый статус домашки')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        logging.critical('Переменные окружения недоступны.')
        sys.exit('Ошибка: Токены не прошли валидацию')
    previous_status = None
    bot = telebot.TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                homework = homeworks[0]
                new_status = parse_status(homework)
            else:
                new_status = 'Новые статусы в ответе API отсутствуют.'
                logging.DEBUG(new_status)
        except EmptyAPIResponse as error:
            logger.error(error)
        except Exception as error:
            message = (f'Сбой в работе программы: {error}.')
            logging.exception(message)
        finally:
            if previous_status != new_status:
                send_message(bot, new_status)
                previous_status = new_status
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(module)s, %(lineno)d,'
               '%(funcName)s, %(levelname)s, %(message)s'
    )
    main()
