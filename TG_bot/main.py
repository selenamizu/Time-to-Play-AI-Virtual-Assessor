from Auxiliary.chat import *


@bot.message_handler(commands=["start"])
def start(message_tg):
    botMessage = message_loading.new_line(message_tg)
    sleep(7.5)
    message_mood.old_line(botMessage)


@bot.message_handler(commands=["main"])
def main(message_tg):
    message_start.new_line(message_tg)


@bot.message_handler(commands=["contacts"])
def contacts(message_tg):
    message_contacts.new_line(message_tg)


@bot.callback_query_handler(func=lambda call: True)
def callback_reception(call):
    commands = ['survey']

    to_message = None  # Если будет ошибка вернемся сюда
    button_from = getattr(button, call.data)
    if button_from is not None:
        to_message = button_from(call.message)  # Сообщение к которому идём (заодно логируем)

    for command in commands:
        if call.data.split(split)[-1] == command:
            command_data = call.data.split(split)[:-1]  # Данные передавающиеся кнопкой

            if command == 'survey':
                save_message = message_start  # Если будет ошибка вернемся сюда

                if len(command_data) == 1:
                    # На этом этапе: command_data = [Тип проверки]
                    Message("Выберите курс обучения 📖",
                            (
                                (
                                    getattr(button, f"{command_data[0]}{split}introduction{split}{command}"),
                                    getattr(button, f"{command_data[0]}{split}process{split}{command}"),
                                ),
                                (button.back_to_survey_type,)), button.back_to_well).old_line(call.message)

                elif command_data[0] == 'lesson' and len(command_data) == 2:
                    Message("Выберите номер урока 📚",
                            (tuple(getattr(button,
                                           f"{split.join(command_data)}{split}{num_lesson}{split}{command}")
                                   for num_lesson in range(1, 7)),
                             (button.back_to_well,)), button.back_to_num_lesson).old_line(call.message)

                elif len(command_data) in (2, 3, 4, 5):
                    if command_data[0] == "well" and len(command_data) == 2 or command_data[0] == "lesson" and len(
                            command_data) == 3:
                        Message("Выберите режим тестирования 👨🏻‍🏫",
                                (
                                    (
                                        getattr(button, f"{'_'.join(command_data)}{split}test{split}{command}"),
                                        getattr(button, f"{'_'.join(command_data)}{split}interview{split}{command}"),
                                        getattr(button, f"{'_'.join(command_data)}{split}friend{split}{command}"),
                                    ),
                                    ((button.back_to_well if command_data[
                                                                 0] == 'well' else button.back_to_num_lesson),)),
                                button.back_to_well).old_line(call.message)

                    elif (command_data[0] == "well" and len(command_data) == 4 or command_data[0] == "lesson" and len(
                            command_data) == 5) and command_data[-1] == 'yes' or (
                            command_data[0] == "well" and len(command_data) == 3 or command_data[0] == "lesson" and len(
                        command_data) == 4) and command_data[-1] != 'friend':
                        data = None

                        if command_data[0] == "lesson" and len(command_data) == 5 and command_data[-1] == 'yes' or \
                                command_data[0] == "lesson" and len(command_data) == 4:
                            data = df.query(f"Lesson == %a" % '_'.join(command_data[1:3]))

                        elif command_data[0] == "well" and len(command_data) == 4 and command_data[-1] == 'yes' or \
                                command_data[0] == "well" and len(command_data) == 3 and command_data[-1]:
                            data = df[df.Lesson.str.startswith(command_data[1])]

                        data = data.sample(min(len(data), config.amount_question[command_data[0]]),
                                           ignore_index=True)

                        questions = data.Question.tolist()
                        materials = data.Material.tolist()

                        if command_data[-1] == 'test':
                            message_temp = Message("Хороший выбор! Давай проведем небольшое тестирование, чтобы "
                                                   "убедиться, что материал с курса был усвоен тобой успешно.\n"
                                                   "Такое тестирование может встретиться на профильном экзамене или "
                                                   "при техническом собеседовании.\n"
                                                   f"Тест содержит в себе {min(len(data), config.amount_question[command_data[0]])} "
                                                   f"вопросов, отвечай на них и не бойся совершать ошибки.\n"
                                                   f"В конце, если будут неточные ответы, я приложу темы, на которые "
                                                   f"стоит еще раз обратить внимание.\n"
                                                   f"Количество попыток не ограничено, также как и время.\n"
                                                   f"Удачи!")

                            botMessage = message_temp.old_line(call.message)
                            sleep(7.5)

                            bot.clear_step_handler_by_chat_id(call.message.chat.id)
                            if len(questions):
                                botMessage = Message(
                                    f"*Вопрос 1/{len(questions)}:* " + questions[0],
                                    ((button.survey_cancel,),)).old_line(botMessage)
                                bot.register_next_step_handler(botMessage, survey_decorator(
                                    botMessage, questions, list(), command_data[-1], materials, list()))
                            else:
                                save_message.old_line(call.message)

                        elif command_data[-1] == 'interview':
                            botMessage = Message("Рады приветствовать тебя в нашей компании!\n"
                                                 "Очень рады, что именно вы заинтересовались нашими вакансиями.\n"
                                                 "Хотим провести для начала небольшой опрос, чтобы лучше "
                                                 "познакомиться.\n"
                                                 "На какую должность вы претендуете?",
                                                 ((button.survey_cancel,),)).old_line(call.message)
                            bot.clear_step_handler_by_chat_id(call.message.chat.id)
                            bot.register_next_step_handler(botMessage,
                                                           survey_interview_1_decorator(
                                                               botMessage, questions,
                                                               materials, command_data))
                        elif command_data[-1] == 'yes':
                            message_temp = Message("Ура!\n"
                                                   "Всегда мечтал быть на месте учителя, ахах, или лучше ведущим на "
                                                   "викторине, правда я мало что понимаю во всем этом…\n"
                                                   "Но давай пробовать, с помощью Brainy потом проверим.")

                            botMessage = message_temp.old_line(call.message)
                            sleep(5)

                            bot.clear_step_handler_by_chat_id(call.message.chat.id)
                            if len(questions):
                                botMessage = Message(
                                    f"*Вопрос 1/{len(questions)}:* " + questions[0],
                                    ((button.survey_cancel,),)).old_line(botMessage)
                                bot.register_next_step_handler(botMessage, survey_decorator(
                                    botMessage, questions, list(), command_data[-2], materials, list()))
                            else:
                                save_message.old_line(call.message)

                    elif (command_data[0] == "well" and len(command_data) == 3 or command_data[0] == "lesson" and len(
                            command_data) == 4) and command_data[-1] == 'friend':
                        botMessage = Message("Хэй! Привет, рад тебя видеть. Как поживаешь?",
                                             ((button.survey_cancel,),)).old_line(call.message)
                        bot.clear_step_handler_by_chat_id(call.message.chat.id)
                        bot.register_next_step_handler(botMessage,
                                                       survey_friend_1_decorator(botMessage, command_data))

                break
    else:
        if to_message is not None and to_message(
                call.message) is None:  # Вызываем функцию, если там нет return, то делаем old_line
            to_message.old_line(call.message)  # Выводить сообщение к которому ведет кнопка

    bot.answer_callback_query(callback_query_id=call.id, show_alert=False)


@bot.message_handler(content_types=['text'])
def watch(message_tg):
    Message.userSendLogger(message_tg)


if __name__ == '__main__':
    print(f"link: https://t.me/{config.Bot}")
    logger.info(f'{config.Bot} start')

bot.infinity_polling()
