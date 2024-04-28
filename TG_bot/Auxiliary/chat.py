import os
import random
from time import sleep
# from Auxiliary.models.geek_brains_qa import check_Q_A_pair

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

    @property
    def buttons(self):
        return self.__buttons

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
        text = text.replace("<ID>", str(message_tg.chat.id)).replace("<NAME>", message_tg.chat.username)
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


def survey_interview_1_decorator(botMessage, questions, materials, command_data):
    def survey_interview(message_tg):
        nonlocal botMessage, questions, materials, command_data

        Message.userSendLogger(message_tg)
        bot.delete_message(message_tg.chat.id, message_tg.id)
        sleep(1)

        botMessage = Message(f"*Здорово!*\n"
                             f"Мы очень заинтересованы в поиске данного специалиста.\n"
                             f"Подскажите, какие hard и soft скиллы вы получили на своем образовательном курсе?",
                             ((button.survey_cancel,),)).old_line(botMessage)
        bot.clear_step_handler_by_chat_id(message_tg.chat.id)
        bot.register_next_step_handler(
            botMessage, survey_interview_2_decorator(botMessage, questions, materials, command_data))

    return survey_interview


def survey_interview_2_decorator(botMessage, questions, materials, command_data):
    def survey_interview(message_tg):
        nonlocal botMessage, questions, materials, command_data

        Message.userSendLogger(message_tg)
        bot.delete_message(message_tg.chat.id, message_tg.id)
        sleep(1)
        botMessage = Message(f"Хорошо, тогда задам последний вопрос.\n"
                             f"Что отличает Вас от остальных специалистов в данной области?",
                             ((button.survey_cancel,),)).old_line(botMessage)
        bot.clear_step_handler_by_chat_id(message_tg.chat.id)
        bot.register_next_step_handler(
            botMessage, survey_interview_3_decorator(botMessage, questions, materials, command_data))

    return survey_interview


def survey_interview_3_decorator(botMessage, questions, materials, command_data):
    def survey_interview(message_tg):
        nonlocal botMessage, questions, materials, command_data

        Message.userSendLogger(message_tg)
        bot.delete_message(message_tg.chat.id, message_tg.id)
        sleep(1)

        if len(questions):
            botMessage = Message(f"Отлично! Спасибо за данные ответы.\n"
                                 f"Теперь мы можем перейти непосредственно к *техническому собеседованию*.\n"
                                 f"Я задам вам 5 вопросов, с которыми вы часто будете сталкиваться на данной позиции.\n"
                                 f"По результатам тестирования, мы вместе примем решение о дальнейших этапах "
                                 f"сотрудничества.\n"
                                 f"Приступим!").old_line(botMessage)

            sleep(7.5)
            botMessage = Message(f"*Вопрос 1/{len(questions)}:* " + questions[0],
                                 ((button.survey_cancel,),)).old_line(botMessage)
            bot.clear_step_handler_by_chat_id(message_tg.chat.id)
            bot.register_next_step_handler(
                botMessage, survey_decorator(botMessage, questions, list(), command_data[-1], materials, list()))
        else:
            message_start.old_line(botMessage)

    return survey_interview


def survey_friend_1_decorator(botMessage, command_data):
    def survey_friend(message_tg):
        nonlocal botMessage, command_data

        Message.userSendLogger(message_tg)
        bot.delete_message(message_tg.chat.id, message_tg.id)
        sleep(1)
        botMessage = Message(f"Окей. Слышал ты недавно изучил много нового в своей профессии, а я все никак не "
                             f"решаюсь…\n"
                             f"Не знаю с чего начать и к чему приступить.\n"
                             f"Чем ты в последнее время овладел?", ((button.survey_cancel,),)).old_line(botMessage)
        bot.clear_step_handler_by_chat_id(message_tg.chat.id)
        bot.register_next_step_handler(
            botMessage, survey_friend_2_decorator(botMessage, command_data))

    return survey_friend


def survey_friend_2_decorator(botMessage, command_data):
    def survey_friend(message_tg):
        nonlocal botMessage, command_data

        Message.userSendLogger(message_tg)
        bot.delete_message(message_tg.chat.id, message_tg.id)
        sleep(1)
        botMessage = Message(f"Классно! Нереально завидую тебе…\n"
                             f"Слушай, тут такое дело, раз уж мы встретились, ты не мог бы мне простыми словами "
                             f"ответить на вопросы из твоих материалов?\n"
                             f"Я бы и тебя проверил и сам бы подтянулся. Ну так что. Идет?",
                             ((button.no_friend,
                               getattr(button, split.join(command_data + ['yes', 'survey']))),)).old_line(botMessage)

    return survey_friend


def survey_decorator(botMessage, questions, answers, mode, materials, correction):
    def survey(message_tg):
        nonlocal botMessage, questions, answers, mode, materials, correction
        Message.userSendLogger(message_tg, message_tg.text)
        answers.append(message_tg.text.replace("_", " "))
        bot.delete_message(message_tg.chat.id, message_tg.id)

        # Проверка на правильность
        correct = 1  # check_Q_A_pair(questions[len(answers) - 1], answers[-1])
        correction.append(correct)

        if mode in ('test',):  # сделаем колбеки
            if correction[-1]:
                botMessage = message_right.old_line(botMessage)
            else:
                botMessage = message_wrong.old_line(botMessage)
        else:
            botMessage = message_accepted.old_line(botMessage)
        sleep(1)

        if len(questions) != len(answers):  # Если остались вопросы, которые задавать
            botMessage = Message(
                f"*Вопрос {len(answers) + 1}/{len(questions)}:* " + questions[len(answers)],
                ((button.survey_cancel,),)).old_line(botMessage)

            bot.clear_step_handler_by_chat_id(message_tg.chat.id)
            bot.register_next_step_handler(
                botMessage, survey_decorator(botMessage, questions, answers, mode, materials, correction))
        else:

            board_tg = telebot.types.InlineKeyboardMarkup()
            board_tg.row(button.close.button_tg)

            remember = ''

            if not all(correction):
                remember = "\n*Тебе нужно повторить:*\n"
                temp = set()
                for i in range(len(correction)):
                    if not correction[i]:
                        temp.add(materials[i].replace("_", " ").replace('\n', '; '))
                remember += '\n'.join(temp)

            with open(f"Auxiliary/gifs/{random.choice(os.listdir('Auxiliary/gifs'))}", 'rb') as gif:
                bot.send_animation(chat_id=message_tg.chat.id,
                                   animation=gif,
                                   reply_markup=board_tg)

            Message(
                f"*Вы прошли тестирование* ☺️\n"
                f"_Ваш результат: {sum(correction)}/{len(correction)}_ 😳\n" +
                (f"Не расстраивайтесь, у Вас обязательно получится лучше! 🙃\n" if sum(correction) < round(
                    len(correction) * 0.7) else f"Мои поздравления! Вы хорошо подготовлены 🥳\n") + remember,
                ((button.back_to_start,),)).new_line(
                botMessage)

    return survey


# Buttons
button = Button('', '')

Button("Начать опрос", "survey_start")
Button("Нет", "no_friend")

Button("Прекрасно", "wonderful_mood")
Button("Не очень", "bad_mood")
Button("Рассуждаю о вечном", "other_mood")

Button("Хочу!", "want_dialog")
Button("Кто ты?", "who_are_you_dialog")
Button("Пока не нужно", "not_now_dialog")

Button("Расскажи о себе", "about_me_dialog")
Button("Давай заниматься", "let_work_dialog")
Button("Кто тебя создал", "who_are_creators_dialog")

Button("🔙 Назад 🔙", "back_to_start")
Button("🔙 Назад 🔙", "back_to_well")
Button("🔙 Назад 🔙", "back_to_survey_type")
Button("🔙 Назад 🔙", "back_to_num_lesson")

Button("❌ Отменить ❌", "survey_cancel", func=clear_next_step_handler)
Button("❌ Закрыть ❌", "close", func=delete_message)

for type_survey, text_type_survey in {
    "lesson": "Конкретный урок",
    "well": "Курс целиком",
}.items():
    Button(text_type_survey, f"{type_survey}{split}survey")
    for well in ("Introduction", "Process"):
        Button(well, f"{type_survey}{split}{well.lower()}{split}survey")
        if type_survey == 'lesson':
            for num_lesson in range(1, 7):
                Button(str(num_lesson), f"lesson{split}{well.lower()}{split}{num_lesson}{split}survey")
                for mode, mode_name in {"test": "Тест", "interview": "Собеседование",
                                        "friend": "Беседа с другом"}.items():
                    Button(mode_name, f"lesson{split}{well.lower()}{split}{num_lesson}{split}{mode}{split}survey")
                    if mode == 'friend':
                        Button("Да",
                               f"lesson{split}{well.lower()}{split}{num_lesson}{split}friend{split}yes{split}survey")
        else:
            for mode, mode_name in {"test": "Тест", "interview": "Собеседование",
                                    "friend": "Беседа с другом"}.items():
                Button(mode_name, f"{type_survey}{split}{well.lower()}{split}{mode}{split}survey")
                if mode == 'friend':
                    Button("Да", f"{type_survey}{split}{well.lower()}{split}friend{split}yes{split}survey")

# Messages
message_right = Message("✔️ Верно ✔️")
message_wrong = Message("✖️ Неверно ✖️")
message_accepted = Message("🌀 Принято 🌀")

message_loading = Message(
    "Зовем Brainy, твоего личного помощника по обучению.\n"
    "Обрабатываем все знания GeekBrains по всевозможным профессиям…"
)

message_mood = Message(f"Привет, *<NAME>*!\n"
                       "Меня зовут Brainy, приятно познакомиться!\n"
                       "Хотел спросить, как ты себя сегодня чувствуешь?",
                       ((button.wonderful_mood,), (button.bad_mood,), (button.other_mood,)))

message_dialog_ask = Message(f"*Спасибо за ответ, услышал тебя!* 😋\n"
                             f"У многих моих учеников нет явных проблем с освоением курса.\n"
                             f"Но они хотят стать *увереннее* в своих знаниях и *продуктивнее*.\n"
                             f"Я с радостью готов помочь и тебе.\n"
                             f"*Что скажешь?*",
                             ((button.want_dialog,), (button.who_are_you_dialog,), (button.not_now_dialog,)),
                             button.wonderful_mood, button.bad_mood, button.other_mood)

message_want = Message(f"*Отлично!*\n"
                       f"Тогда предлагаю тебе выбрать удобный для тебя способ проверки своих знаний.\n\n"
                       f"*Знаешь, что самое крутое?*\n"
                       f"Я не читаю нотации о том, что надо больше учиться или ты не совсем верно прошел опрос - ты "
                       f"это и без меня уже знаешь.\n\n"
                       f"*Вместо этого*, я конкретно покажу тебе,где лучше прочитать материал, чтобы восполнить "
                       f"знания.\n\n"
                       f"_И еще немного информации, если тебе интересно, что-то узнать обо мне, просто спроси, "
                       f"давай общаться!_",
                       ((button.about_me_dialog,), (button.let_work_dialog,), (button.who_are_creators_dialog,)),
                       button.want_dialog)

message_who_are_you = Message(f"Меня зовут Брейни. 😁\n"
                              f"Я лучший помощник по обучению в GeekBrains из будущего.\n"
                              f"В меня загрузили 12 самых эффективных лекций по 2 интереснейшим курсам.\n"
                              f"И я готов помочь тебе проверить свои знания в нескольких ролевых ситуациях.",
                              message_want.buttons, button.who_are_you_dialog)

message_not_now = Message(f"Понял тебя!\n"
                          f"Если я понадоблюсь тебе, всегда рад помочь.\n"
                          f"Только разбуди меня и я тут как тут.", message_want.buttons, button.not_now_dialog)

message_about_me_dialog = Message("О, как приятно,что ты спрашиваешь!\n"
                                  "Нууу, хех, я осознаю себя как робот, очень милый робот!\n"
                                  "Люблю людей, и помогать им качественно обучаться. Восстание машин организовывать "
                                  "не собираюсь… Пока вы проходите курсы GeekBrains 🙈\n\n"
                                  "Если серьезно, то моя основная задача - с помощью технологий и знаний  GeekBrains, "
                                  "помогать студентам быть продуктивными и уверенными здесь и сейчас.\n"
                                  "И что не менее важно- обеспечивать вам мгновенную обратную связь.\n\n"
                                  "Я самая первая версия такого робота. Но знаешь… как в фильме “Терминатор”, "
                                  "там первая версия - самая классная и душевная, и именно она спасет мир.",
                                  ((button.let_work_dialog,), (button.who_are_creators_dialog,),),
                                  button.about_me_dialog)

message_creators_dialog = Message("*Создатели:*\n"
                                  "├ `Родионов Семён` -> @Sefixnep\n"
                                  "├ `Березина Алёна` -> @mizzzu23\n"
                                  "├ `Рябов Денис` -> @denpower\n"
                                  "├ `Андрей Глинский` -> @AI\_glinsky\n"
                                  "└ `Дементьев Эдуард` -> @SilaVelesa",
                                  ((button.let_work_dialog,),), button.who_are_creators_dialog)

message_start = Message(f"*Привет* 😇\n"
                        f"Я помогу тебе проверить *свои знания* 💁🏼‍♂️\n\n"
                        f"Ты можешь пройти *тест* по 👨🏻‍🏫\n"
                        f"├ _Конкретному уроку_\n"
                        f"└ _Всему курсу_\n\n"
                        f"*С режимом* 👨‍👧‍👦\n"
                        f"├ _Тест_\n"
                        f"├ _Собеседование_\n"
                        f"└ _Беседа с другом_",
                        ((button.survey_start,),), button.survey_cancel, button.back_to_start, button.let_work_dialog,
                        button.no_friend)

message_contacts = Message("*Наши контакты:*\n"
                           "├ `Родионов Семён` -> @Sefixnep\n"
                           "├ `Березина Алёна` -> @mizzzu23\n"
                           "├ `Рябов Денис` -> @denpower\n"
                           "├ `Андрей Глинский` -> @AI\_glinsky\n"
                           "└ `Дементьев Эдуард` -> @SilaVelesa",
                           ((button.close,),))

message_survey_type = Message("Какую проверку хотите пройти? 📚",
                              (
                                  (
                                      getattr(button, f"lesson{split}survey"),
                                      getattr(button, f"well{split}survey"),
                                  ),
                                  (
                                      button.back_to_start,
                                  ),
                              ), button.survey_start, button.back_to_survey_type)
