import os
import random
from time import sleep

import pandas as pd
import telebot
from loguru import logger

from Auxiliary import config

split = '_'
df = pd.read_csv("Auxiliary/Questions.csv")
bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode='html')


class Message:
    def __init__(self, text: str, buttons=None, *from_buttons, func=lambda *args: None):
        self.__text = text  # Текст сообщения
        self.__buttons = buttons  # Двумерный кортеж с кнопками в виде InlineKeyboardButton
        self.__board_tg = None  # Клавиатура кнопок под сообщением: InlineKeyboardMarkup
        if buttons:
            self.__board_tg = telebot.types.InlineKeyboardMarkup()
            for row in (map(lambda x: x.button_tg, buttons1D) for buttons1D in buttons):
                self.__board_tg.row(*row)
        for from_button in from_buttons:  # Кнопки которые ведут к этому сообщению
            from_button.to_messages += (self,)
        self.__func = func  # Функция, которая должна происходить при вызове сообщения

    def __call__(self, *args):
        return self.__func(*args)

    def __getitem__(self, item):
        return self.__buttons[item[0]][item[1]]

    def new_line(self, message_tg, delete_message=True, userSendLogger=True):
        if userSendLogger:
            self.userSendLogger(message_tg)
        if delete_message:
            bot.delete_message(message_tg.chat.id, message_tg.id)
        return self.__botSendMessage(message_tg)

    def old_line(self, message_tg, text=None, userSendLogger=False):
        if userSendLogger:
            self.userSendLogger(message_tg, text)
        return self.__botEditMessage(message_tg)

    @staticmethod
    def __trueText(text, message_tg):
        text = text.replace("<ID>", str(message_tg.chat.id))
        return text

    @staticmethod
    def userSendLogger(message_tg, text=None):
        if text is None:
            if '\n' in message_tg.text:
                logger.info(f'{message_tg.from_user.username} ({message_tg.chat.id}): \n{message_tg.text}')
            else:
                logger.info(f'{message_tg.from_user.username} ({message_tg.chat.id}): {message_tg.text}')
        else:
            if '\n' in text:
                logger.info(f'{message_tg.chat.username} ({message_tg.chat.id}): \n{text}')
            else:
                logger.info(f'{message_tg.chat.username} ({message_tg.chat.id}): {text}')

    def __botSendMessage(self, message_tg, parse_mode='MARKDOWN', indent=3):
        text = self.__trueText(self.__text, message_tg)
        botMessage = bot.send_message(chat_id=message_tg.chat.id, text=text, reply_markup=self.__board_tg,
                                      parse_mode=parse_mode)
        if self.__board_tg is None:
            if '\n' in text:
                logger.info(f"{config.Bot} ({botMessage.chat.username}, {message_tg.chat.id}):\n{text}\n")
            else:
                logger.info(f"{config.Bot} ({botMessage.chat.username}, {message_tg.chat.id}): {text}")
        else:
            reply_markup_text = ''
            for reply_markup1 in botMessage.json['reply_markup']['inline_keyboard']:

                for reply_markup2 in reply_markup1:
                    reply_markup_text += f'[{reply_markup2["text"]}]' + (' ' * indent)
                reply_markup_text = reply_markup_text[:-indent]

                reply_markup_text += '\n'
            reply_markup_text = reply_markup_text[:-1]
            logger.info(
                f"{config.Bot} ({botMessage.chat.username}, {message_tg.chat.id}):\n{text}\n{reply_markup_text}\n")
        return botMessage

    def __botEditMessage(self, message_tg, parse_mode='MARKDOWN', indent=3):
        text = self.__trueText(self.__text, message_tg)
        botMessage = bot.edit_message_text(chat_id=message_tg.chat.id, message_id=message_tg.id, text=text,
                                           reply_markup=self.__board_tg,
                                           parse_mode=parse_mode)
        if self.__board_tg is None:
            if '\n' in text:
                logger.info(f"{config.Bot} ({botMessage.chat.username}, {message_tg.chat.id}):\n{text}\n")
            else:
                logger.info(f"{config.Bot} ({botMessage.chat.username}, {message_tg.chat.id}): {text}")
        else:
            reply_markup_text = ''
            for reply_markup1 in botMessage.json['reply_markup']['inline_keyboard']:

                for reply_markup2 in reply_markup1:
                    reply_markup_text += f'[{reply_markup2["text"]}]' + (' ' * indent)
                reply_markup_text = reply_markup_text[:-indent]

                reply_markup_text += '\n'
            reply_markup_text = reply_markup_text[:-1]
            logger.info(
                f"{config.Bot} ({botMessage.chat.username}, {message_tg.chat.id}):\n{text}\n{reply_markup_text}\n")
        return botMessage


class Button:
    instances = list()  # Список со всеми объектами класса

    def __init__(self, text: str, callback_data: str, *to_messages: Message,
                 func=lambda to_messages, message_tg: None):
        self.text = text  # текст кнопки
        self.callback_data = callback_data  # Скрытые (уникальные) данные, несущиеся кнопкой
        self.button_tg = telebot.types.InlineKeyboardButton(
            self.text, callback_data=self.callback_data)  # кнопка в виде объекта InlineKeyboardButton
        self.to_messages = to_messages  # Сообщения, к которым ведёт кнопка
        self.__func = func  # Функция отбора сообщения из to_messages на основе предыдущего сообщения / вспомогательное
        self.instances.append(self)

    def __call__(self, message_tg,
                 userSendLogger=True) -> Message:  # При вызове кновки отдаем сообщение к которому будем идти
        if userSendLogger:
            Message.userSendLogger(message_tg, f'[{self.text}]')
        if self.__func(self.to_messages, message_tg) is not None:
            return self.__func(self.to_messages, message_tg)
        elif self.to_messages:
            return self.to_messages[0]

    def __getattr__(self, callback_data):  # выполняем поиск кнопки по её скрытым данным, т.к они уникальные
        for instance in self.instances:
            if instance.callback_data == callback_data:
                return instance


def delete_message(_, message_tg):
    bot.delete_message(message_tg.chat.id, message_tg.id)


def clear_next_step_handler(_, message_tg):
    bot.clear_step_handler_by_chat_id(
        message_tg.chat.id)  # просто очищаем step_handler
    # ничего не возращаем, чтобы дальше шло как с обычными кнопками


def survey_decorator(botMessage, questions, answers, type_survey, count):
    def survey(message_tg):
        nonlocal botMessage, questions, answers, type_survey, count
        Message.userSendLogger(message_tg, message_tg.text)
        answers.append(message_tg.text)
        bot.delete_message(message_tg.chat.id, message_tg.id)

        # Проверка на правильность
        count += 1

        if type_survey in ('lesson', 'well'):  # сделаем колбеки
            botMessage = message_right.old_line(botMessage)
        else:
            botMessage = message_accepted.old_line(botMessage)
        sleep(1)

        if len(questions) != len(answers):  # Если остались вопросы, которые задавать
            botMessage = Message(
                f"*Вопрос {len(answers) + 1}/{len(questions)}:* " + questions[len(answers)],
                ((button.survey_cancel,),)).old_line(botMessage)

            bot.clear_step_handler_by_chat_id(message_tg.chat.id)
            bot.register_next_step_handler(botMessage,
                                           survey_decorator(botMessage, questions, answers, type_survey, count))
        else:
            questions = list(map(lambda x: "*Вопрос:* " + x, questions))
            answers = list(map(lambda x: "*Ответ:* " + x, answers))
            mix = list(map(lambda x: '\n'.join(x), zip(questions, answers)))
            history = f"\n_История теста:_\n" + '\n\n'.join(mix)

            board_tg = telebot.types.InlineKeyboardMarkup()
            board_tg.row(button.close.button_tg)

            with open(f"Auxiliary/gifs/{random.choice(os.listdir('Auxiliary/gifs'))}", 'rb') as gif:
                bot.send_animation(chat_id=message_tg.chat.id,
                                   animation=gif,
                                   reply_markup=board_tg)

            Message(
                f"*Вы прошли тестирование* ☺️\n"
                f"_Ваш результат: {count}/{len(questions)}_ 😳\n" +
                (f"Не расстраивайтесь, у Вас обязательно получится лучше! 🙃\n" if count < int(
                    len(questions) * 0.7) else f"Мои поздравления! Вы хорошо подготовлены 🥳\n") + history,
                ((button.back_to_start,),)).new_line(
                botMessage)

    return survey


button = Button('', '')

Button("❌ Закрыть ❌", "close", func=delete_message)
Button("🔙 Назад 🔙", "back_to_well")

message_right = Message("✔️ Верно ✔️")
message_wrong = Message("❌ Неверно ❌")
message_accepted = Message("🌀 Принято 🌀")

for type_survey, text_type_survey in {
    "lesson": "Конкретный урок",
    "well": "Курс целиком",
    "exam": "Экзамен"
}.items():
    Button(text_type_survey, f"{type_survey}{split}survey")
    for well in ("Introduction", "Process"):
        Button(well, f"{type_survey}{split}{well.lower()}{split}survey")
        if type_survey == 'lesson':
            for num_lesson in range(1, 7):
                Button(str(num_lesson), f"lesson{split}{well.lower()}{split}{num_lesson}{split}survey")

message_start = Message(f"*Привет* 😇\n"
                        f"Я помогу тебе проверить *свои знания* 💁🏼‍♂️\n"
                        f"Ты можешь пройти *тест* по 👨🏻‍🏫\n"
                        f"├ _Конкретному уроку_\n"
                        f"├ _Всему курсу_\n"
                        f"└ _Экзамен_",
                        (
                            (
                                Button("Начать опрос", "survey_start"),
                            ),
                        ))

Button("❌ Отменить ❌", "survey_cancel", message_start, func=clear_next_step_handler)

message_contacts = Message("*Наши контакты:*\n"
                           "├ `Родионов Семён` -> @Sefixnep\n"
                           "├ `Березина Алёна` -> @mizzzu23\n"
                           "├ `Рябов Денис` -> @denpower\n"
                           "├ `Андрей Глинский` -> @AI\_glinsky\n"
                           "└ `Дементьев Эдуард` -> @SilaVelesa",
                           (
                               (
                                   button.close,
                               ),
                           ))

message_survey_type = Message("Какую проверку хотите пройти? 📚",
                              (
                                  (
                                      getattr(button, f"lesson{split}survey"),
                                      getattr(button, f"well{split}survey"),
                                      getattr(button, f"exam{split}survey"),
                                  ),
                                  (
                                      Button("🔙 Назад 🔙", "back_to_start", message_start),
                                  ),
                              ), button.survey_start, Button("🔙 Назад 🔙", "back_to_survey_type"))
