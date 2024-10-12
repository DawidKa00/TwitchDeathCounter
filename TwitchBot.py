
import logging
import os
import random
import threading
import time

from datetime import timedelta, datetime
from typing import Optional, Any
from TwitchConnection import TwitchConnection
from ConfigManager import ConfigManager
from dotenv import load_dotenv

load_dotenv()


class TwitchBot:
    def __init__(self):

        from CommandHandler import CommandHandler
        self.username = os.getenv("USER_NAME")
        self.oauth_token = os.getenv("OAUTH_TOKEN")

        self.deaths = 0  # Licznik ogólnych śmierci
        self.boss_paused = False  # Flaga, czy boss jest zatrzymany
        self.boss_paused_time = timedelta()
        self.boss_start_time: Optional[datetime] = None
        self.boss_pause_time = None
        self.boss_name = ""  # Nazwa bossa
        self.boss_timer = timedelta()  # Timer dla bossa (jeśli potrzebny)
        self.deaths_boss = 0  # Licznik śmierci bossa
        self.boss_active = False
        self.message_count = 0

        self.temp_timer = None
        self.temp_boss = ' '
        self.temp_boss_deaths = ' '
        self.temp_deaths = ' '

        self.config_manager = ConfigManager()
        self.connection = TwitchConnection()
        self.command_handler = CommandHandler(self, self.config_manager)

        self.channel = self.config_manager['channel']  # Nazwa kanału (zmień na właściwą)
        self.emotes = self.config_manager['emotes']  # Lista emotikon do użycia

        self.name_file = self.channel + '.txt'
        self.read_data_from_file()

    def start(self):
        """Rozpocznij działanie bota."""
        logging.basicConfig(filename=(self.channel + ".log"), encoding='utf-8', level=logging.INFO,
                            format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        try:
            self.connection.connect(self.username, self.oauth_token, self.channel)
            logging.info(f"Bot connected to {self.channel} as {self.username}")
            self.listen_to_chat()
        except Exception as e:
            logging.error(f"Error starting bot: {str(e)}")
            self.connection.disconnect()

    def listen_to_chat(self):
        """Nasłuchuje wiadomości na czacie Twitcha."""
        while self.connection.is_connected():
            try:
                message = self.connection.receive_messages()
                self.handle_message(message)
            except Exception as e:
                logging.error(f"Error receiving message: {str(e)}")
                self.connection.disconnect()
                break

    def handle_message(self, message: str):
        """Przetwarzaj wiadomości i wykonuj odpowiednie komendy."""
        message = message.strip()  # Usuwamy białe znaki z początku i końca
        try:
            # Podział wiadomości na tagi i pozostałą część
            if message.startswith('@'):
                tag_part, rest = message.split(' ', 1)
                tags = tag_part[1:].split(';')  # Usuwamy '@' i dzielimy po ';'
            else:
                return

            # Rozdzielamy użytkownika i resztę wiadomości
            if ' :' in rest:
                user_part, command_part = rest.split(' :', 1)
            else:
                logging.warning(f"No command part found in message: {rest}")
                return

            user_info = user_part.split('!')
            user = user_info[0][1:]  # Ekstrakcja użytkownika
            command = command_part.split()[0]  # Pierwszy element po ':', czyli komenda
            args = command_part.split()[1:]  # Reszta to argumenty
            badge = tags[1][7:]
            authorized = self.is_authorized(badge, user)

            if self.config_manager['spam_bot_enabled']:
                if self.message_count >= self.config_manager['spam_bot_messages']:
                    print("tutaj bym coś napisał ehhe")
                    self.connection.send_privmsg(self.config_manager['spam_bot_message'] + " " + random.choice(self.config_manager['emotes']))
                    self.message_count = 0
                self.message_count += 1

            # Sprawdzenie, czy komenda zaczyna się od prefiksu
            prefix = self.config_manager['prefix']
            if command.startswith(prefix):
                command = command[1:]  # Usuwamy prefix
                response = self.command_handler.execute_command(command, user, authorized, args)
                if response:
                    self.connection.send_privmsg(response)

        except Exception as e:
            logging.error(f"Failed to process message: {message} | Error: {str(e)}")

    def read_data_from_file(self):
        self.boss_name = ""
        try:
            with open(self.name_file, 'r', encoding='utf-8') as file:
                data = file.read().splitlines()
                if len(data) == 1:
                    temp = data[0].split(" ")
                    self.deaths = int(temp[1])

                elif len(data) == 5:
                    temp = data[0].split(" ")
                    self.deaths = int(temp[1])
                    temp = data[2].split(" ")
                    self.boss_name = " ".join(temp[1:])
                    if data[2] != ' ':
                        self.boss_active = False
                        self.boss_paused = True
                    if data[3] != ' ':
                        temp = data[3].split(" ")
                        self.deaths_boss = int(temp[1])
                    if data[4] != ' ':
                        temp = data[4].split(" ")
                        time_str = temp[1]
                        h, m, s = map(int, time_str.split(':'))
                        self.boss_timer = timedelta(hours=h, minutes=m, seconds=s)
                    else:
                        self.boss_timer = timedelta()
                else:
                    print(f'Error: Incorrect data format in file {self.name_file}.')
        except FileNotFoundError as e:
            logging.error(e)
            print(f'Error: File {self.name_file} not found. Creating...')

        if self.boss_active and not self.boss_paused:
            self.boss_start_time = datetime.now() - self.boss_timer
        else:
            self.boss_start_time = None

    def write_data_to_file(self):
        """
            Zapisuje aktualne dane do pliku, w tym liczbę śmierci, nazwę bossa, liczbę śmierci bossa oraz czas bossa.
        """
        self.boss_timer = self.calculate_and_format_boss_time()

        try:
            with open(self.name_file, 'w', encoding='utf-8') as file:
                if self.boss_active or self.boss_paused:
                    file.write(
                        f'śmierci: {self.deaths}\n\n'
                        f'boss: {self.boss_name}\n'
                        f'śmierci: {self.deaths_boss}\n'
                        f'czas: {self.boss_timer}'
                    )
                else:
                    file.write(f'śmierci: {self.deaths}\n\n \n \n ')
        except FileNotFoundError as e:
            logging.error(f'Error: File {self.name_file} not found. {e}')
            print(f'Error: File {self.name_file} not found.')

    def pause_boss(self):
        if self.boss_active and not self.boss_paused:
            self.boss_paused = True
            self.boss_active = False
            self.boss_pause_time = datetime.now()

    def resume_boss(self):
        current_time = datetime.now()

        if not self.boss_active:
            # Pierwsze uruchomienie bossa
            self.boss_active = True
            if type(self.boss_timer) == str:
                t = datetime.strptime(self.boss_timer, "%H:%M:%S")
                self.boss_timer = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
            self.boss_start_time = current_time - self.boss_timer
            self.boss_paused = False
            self.boss_pause_time = None
        elif self.boss_paused:
            # Wznowienie po pauzie
            if self.boss_pause_time:
                self.boss_paused_time += current_time - datetime.strptime(self.boss_pause_time, '%H:%M:%S')
            self.boss_paused = False
            self.boss_pause_time = None
            if self.boss_start_time is None:
                self.boss_start_time = current_time - self.boss_timer

    def clear_temps(self):
        self.temp_boss = ' '
        self.temp_boss_deaths = ' '
        self.temp_deaths = ' '
        self.temp_timer = ' '

    def calculate_and_format_boss_time(self):
        current_time = datetime.now()

        # Jeśli boss nie jest aktywny lub start nie jest ustawiony, zwracamy dotychczasowy czas
        if not self.boss_active or self.boss_start_time is None:
            return self.boss_timer

        # Obliczanie czasu, w zależności od tego, czy boss jest wstrzymany
        if self.boss_paused:
            elapsed_time = (self.boss_pause_time or current_time) - self.boss_start_time
        else:
            elapsed_time = current_time - self.boss_start_time

        # Odejmujemy czas, w którym boss był wstrzymany
        total_time = elapsed_time - self.boss_paused_time

        # Konwersja czasu na sekundy
        total_seconds = int(total_time.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        # Zwracamy sformatowany czas jako string
        return f'{hours:02d}:{minutes:02d}:{seconds:02d}'

    def __getitem__(self, key: str) -> Any:
        """Pobiera wartość z konfiguracji za pomocą nawiasów kwadratowych."""
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Ustawia wartość w konfiguracji za pomocą nawiasów kwadratowych."""
        setattr(self, key, value)

    def is_authorized(self, badge: str, user: str) -> bool:
        """
        Sprawdź, czy użytkownik ma uprawnienia do używania komendy,
        na podstawie rang (badge) i ustawień w 'bot_moderators'.
        """
        if self.config_manager['all_users_mod']: return True

        if self.config_manager['white_list_enabled']:
            if user in self.config_manager['white_list']:
                return True

        elif self.config_manager['black_list_enabled']:
            if user in self.config_manager['black_list']:
                return False

        # Parsowanie badge do listy rang
        user_badges = [b.split('/')[0] for b in badge.split(',')]

        # Sprawdzenie, czy jakakolwiek ranga z user_badges jest w bot_moderators
        for user_badge in user_badges:
            if user_badge in self.config_manager['bot_moderators']:
                return True

        return False


def write_data_thread():
    finished_timer = 0.0
    while True:
        bot.write_data_to_file()
        if finished_timer < 10.0:
            finished_timer += 0.5
        else:
            finished_timer = 0.0
            bot.clear_temps()
        time.sleep(0.5)


if __name__ == "__main__":
    bot = TwitchBot()

    write_data_thread = threading.Thread(target=write_data_thread)
    start_thread = threading.Thread(target=bot.start)

    start_thread.start()
    write_data_thread.start()
