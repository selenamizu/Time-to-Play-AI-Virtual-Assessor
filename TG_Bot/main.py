from Auxiliary.chat import *


@bot.message_handler(commands=["start"])
def start(message_tg):
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
                    to_message = Message("Выберите курс обучения 📖",
                                         (
                                             (
                                                 getattr(button,
                                                         f"{command_data[0]}{split}introduction{split}{command}"),
                                                 getattr(button, f"{command_data[0]}{split}process{split}{command}"),
                                             ),
                                             (button.back_to_survey_type,)
                                         ), button.back_to_well)
                    to_message.old_line(call.message)

                elif command_data[0] == 'lesson' and len(command_data) == 2:
                    Message("Выберите номер урока:",
                            (tuple(getattr(button,
                                           f"{split.join(command_data)}{split}{num_lesson}{split}{command}")
                                   for num_lesson in range(1, 7)),
                             (button.back_to_well,))).old_line(call.message)

                elif len(command_data) in (2, 3):
                    questions = None

                    if command_data[0] in ('well', 'exam') and len(command_data) == 2:
                        # На этом этапе: command_data = [Тип проверки, курс обучения]
                        questions = df.Question[df.Lesson.str.startswith(command_data[1])]

                    elif len(command_data) == 3:
                        # На этом этапе: command_data = ['lesson', курс обучения, урок]
                        questions = df.query(f"Lesson == %a" % '_'.join(command_data[1:3])).Question

                    questions = questions.sample(min(len(questions), config.amount_question[command_data[0]]),
                                                 ignore_index=True).tolist()

                    bot.clear_step_handler_by_chat_id(call.message.chat.id)
                    if len(questions):
                        botMessage = Message(
                            f"*Вопрос 1/{len(questions)}:* " + questions[0],
                            ((button.survey_cancel,),), ).old_line(call.message)
                        bot.register_next_step_handler(botMessage, survey_decorator(
                            botMessage, questions, [], command_data[0], 0))
                    else:
                        save_message.old_line(call.message)

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
