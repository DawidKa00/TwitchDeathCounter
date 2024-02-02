import random
import time
import threading
from datetime import timedelta, datetime

from python_twitch_irc import TwitchIrc
from dotenv import load_dotenv
import os
import socket
from collections import namedtuple
from ruamel.yaml import YAML, comments

load_dotenv()

Message = namedtuple(
    'Message',
    'prefix user channel irc_command irc_args badge_info text text_command text_args',
)


class TwitchBot(TwitchIrc):
    __instance = None

    def __init__(self, channel):

        self._connected = False
        self.irc_server = 'irc.twitch.tv'
        self.irc_port = 6667
        self.irc = socket.socket()
        self.oauth_token = os.getenv("OAUTH_TOKEN")
        self.username = os.getenv("USER_NAME")
        self.channel = channel
        self.deaths = 0
        self.deaths_boss = ' '
        self.boss_active = False
        self.boss_stopped = False
        self.boss_start_time = None
        self.boss_name = ' '
        self.boss_timer = ' '
        self.boss_timer_file = ' '
        self.last_death_plus_time = 0
        self.last_death_minus_time = 0
        self.command_cooldown = 15
        self.last_stop_boss_time = 0
        self.last_start_boss_time = 0
        self.last_set_deaths_time = 0
        self.last_resume_boss_time = 0
        self.spambot_cooldown = 300
        self.name_file = self.channel + '.txt'
        self.spam_bot_enabled = True
        self.white_list_enabled = False
        self.white_list = []
        self.black_list_enabled = False
        self.black_list = []
        self.emotes = []
        self.all_users_mod = True
        self.bot_moderators = []

    def send_privmsg(self, channel, text):
        self.send_command(f'PRIVMSG #{channel} :{text}')

    def send_command(self, command):
        if 'PASS' not in command:
            print(f'< {command}')

        self.irc.send((command + '\r\n').encode())

    def send_raw(self, message):
        self.irc.sendall(bytes(message, 'utf-8'))

    def connect(self):
        if not self._connected:
            self.irc.connect((self.irc_server, self.irc_port))
            self.send_command(f'PASS {self.oauth_token}')
            self.send_command(f'NICK {self.username}')
            self.send_command(f'JOIN #{self.channel}')
            self.send_raw('CAP REQ :twitch.tv/tags\r\n')
            self._connected = True
            self.loop_for_messages()
        else:
            self.open()

    @staticmethod
    def get_user_from_prefix(prefix):
        """
            Odczytanie nazwy użytkownika z prefiksu
            :param prefix: prefiks
            :type prefix: str
            :return: Zwrócenie nazwy użytkownika
        """
        domain = prefix.split('!')[0]
        if domain.endswith('.tmi.twitch.tv'):
            return domain.replace('.tmi.twitch.tv', '')
        if 'tmi.twitch.tv' not in domain:
            return domain
        return None

    def parse_message(self, received_msg):
        parts = received_msg.split(' ')
        prefix = None
        user = None
        channel = None
        text = None
        text_command = None
        text_args = None
        badge_info = None
        irc_command = None
        irc_args = None

        if parts[0].startswith(':'):
            prefix = parts[0][1:]
            user = self.get_user_from_prefix(prefix)
            parts = parts[1:]

        elif parts[0].startswith('@'):
            prefix = parts[1][1:]
            user = self.get_user_from_prefix(prefix)
            badge_info = parts[0]
            parts = parts[2:]

        text_start = next(
            (idx for idx, part in enumerate(parts) if part.startswith(':')),
            None
        )
        if text_start is not None:
            text_parts = parts[text_start:]
            text_parts[0] = text_parts[0][1:]
            text = ' '.join(text_parts)
            text_command = text_parts[0]
            text_args = text_parts[1:]
            parts = parts[:text_start]

        irc_command = parts[0]
        irc_args = parts[1:]

        hash_start = next(
            (idx for idx, part in enumerate(irc_args) if part.startswith('#')),
            None
        )
        if hash_start is not None:
            channel = irc_args[hash_start][1:]

        message = Message(
            prefix=prefix,
            user=user,
            channel=channel,
            text=text,
            text_command=text_command,
            text_args=text_args,
            badge_info=badge_info,
            irc_command=irc_command,
            irc_args=irc_args,
        )
        return message

    def parse_badge(self, badge_info):
        parts = badge_info.split(';')
        for badge in ['mod', 'subscriber', 'vip']:
            if f'{badge}=1' in parts and badge in self.bot_moderators:
                return True
        if 'broadcaster' in self.bot_moderators and 'broadcaster/1' in parts[1]:
            return True
        return False

    def handle_template_command(self, message, template):
        text = template.format(**{'message': message})
        self.send_privmsg(message.channel, text)

    def handle_message(self, received_msg):
        if len(received_msg) == 0:
            return
        message = self.parse_message(received_msg)

        if message.irc_command == 'PING':
            self.send_command('PONG :tmi.twitch.tv')

        if message.irc_command == 'PRIVMSG':

            if message.text_command == '!deaths':
                if self.boss_active and self.boss_stopped is False:
                    self.send_privmsg(message.channel, f'@{message.user} {self.boss_name} robiony od '
                                                       f'{self.boss_timer} i tylko {self.deaths_boss} wyjebki ok w sumie {self.deaths}')
                else:
                    self.send_privmsg(message.channel,
                                      f'@{message.user} {message.channel} wypierdolił się już {self.deaths} razy {random.choice(self.emotes)}')

            elif message.text_command == '!help':
                self.send_privmsg(message.channel, '⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀ ⠀ ⠀ ⠀ ⠀⠀⠀  '
                                                   'Są takie komendy:⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀ '
                                                   '⠀⠀⠀⠀!deaths - wyświetla aktualną liczbę śmierci, '
                                                   '⠀⠀⠀⠀!death+ - dodaje 1 do licznika,⠀⠀⠀⠀⠀⠀⠀⠀ '
                                                   '⠀⠀⠀⠀!death- - odejmuje 1 od licznika, '
                                                   '⠀⠀⠀⠀!setdeaths {liczba} - zmienia liczbę śmierci, '
                                                   '⠀⠀⠀⠀!startboss {nazwa} - rozpoczyna bossa, '
                                                   '⠀⠀⠀⠀!finishboss - kończy bossa,⠀⠀⠀⠀  '
                                                   '⠀⠀⠀⠀!stopboss - pauzuje bossa,⠀⠀⠀⠀  '
                                                   '⠀⠀⠀⠀!resumeboss - wznawia bossa,⠀⠀⠀⠀  '
                                                   '⠀⠀⠀⠀!author - info o autorze,⠀⠀⠀⠀  '
                                                   '⠀⠀⠀⠀!setbossdeaths {liczba} - zmienia śmierci ⠀⠀⠀⠀⠀⠀⠀⠀bossa')

            elif message.text_command == '!author':
                self.send_privmsg(message.channel, 'Zostałem stworzony przez Krwawyy, z propozycjami lub błędami pisz na pw na Twitchu '
                                                   'okok , jakbyś chciał coś dodać napisz to wyśle link do GitHuba wuda')

            # if message.user.lower() in self.users and message.channel.lower() == message.channel.lower() or self.parse_badge(
            #         message.badge_info):
            if (
                    self.all_users_mod or
                    (not self.all_users_mod and self.white_list_enabled and message.user.lower() in self.white_list) or
                    (not self.all_users_mod and self.white_list_enabled and self.parse_badge(message.badge_info)) or
                    (not self.all_users_mod and not self.white_list_enabled and self.parse_badge(message.badge_info)) or
                    (not self.all_users_mod and not self.black_list_enabled and self.parse_badge(message.badge_info))
            ):
                if self.black_list_enabled and message.user.lower() in self.black_list:
                    return
                print(message)
                current_time = time.time()
                if message.text_command == '!death+':
                    if current_time - self.last_death_plus_time >= self.command_cooldown:
                        self.deaths += 1
                        if self.boss_active and self.boss_stopped is False:
                            if self.deaths_boss == ' ':
                                self.deaths_boss = 0
                            self.deaths_boss += 1
                            self.send_privmsg(message.channel,
                                              f'{self.deaths_boss} wyjebek na bossie i {self.deaths} ugółem {random.choice(self.emotes)}')
                        else:
                            self.send_privmsg(message.channel, f'Wypierdolki: {self.deaths} {random.choice(self.emotes)}')
                        self.last_death_plus_time = current_time

                elif message.text.startswith('!startboss'):
                    command_parts = message.text.split()
                    self.deaths_boss = 0
                    if len(command_parts) >= 2:
                        if current_time - self.last_start_boss_time >= self.command_cooldown:
                            try:
                                self.boss_start_time = time.time()
                                self.boss_timer_file = '00:00:00'
                                self.boss_name = str(command_parts[1])
                                self.send_privmsg(message.channel, f'Boss: {self.boss_name} {random.choice(self.emotes)}')
                                self.boss_active = True
                                self.boss_stopped = False
                            except ValueError:
                                print("Zjebało się")
                            self.last_start_boss_time = current_time

                elif message.text_command == '!finishboss':
                    if self.boss_active:
                        if current_time - self.last_stop_boss_time >= self.command_cooldown:
                            boss_stop_time = time.time()
                            time_difference_seconds = round(boss_stop_time - self.boss_start_time)
                            time_difference = timedelta(seconds=time_difference_seconds)
                            time_delta_from_string = datetime.strptime(self.boss_timer_file,
                                                                       '%H:%M:%S') - datetime.strptime(
                                '00:00:00', '%H:%M:%S')
                            self.boss_timer = time_difference + time_delta_from_string
                            self.send_privmsg(message.channel, f'{self.boss_name} rozjebany z {self.deaths_boss} '
                                                               f'wyjebkami po {str(self.boss_timer)} {random.choice(self.emotes)}')
                            self.boss_active = False
                            self.boss_name = ' '
                            self.deaths_boss = ' '
                            self.boss_timer = ' '
                            self.last_stop_boss_time = current_time
                    else:
                        self.send_privmsg(message.channel, f'Nie ma ustawionego bossa hm')

                elif message.text_command == '!death-':
                    if current_time - self.last_death_minus_time >= self.command_cooldown:
                        self.deaths -= 1
                        if self.boss_active and self.boss_stopped is False:
                            if self.deaths_boss == ' ':
                                self.deaths_boss = 0
                            if self.deaths_boss > 0: self.deaths_boss -= 1
                            self.send_privmsg(message.channel,
                                              f'{self.deaths_boss} wyjebek na bossie i {self.deaths} ugółem {random.choice(self.emotes)}')
                        else:
                            self.send_privmsg(message.channel, f'Wypierdolki: {self.deaths} {random.choice(self.emotes)}')
                        self.last_death_minus_time = current_time

                elif message.text.startswith('!setdeaths'):
                    command_parts = message.text.split(' ')
                    if len(command_parts) >= 2:
                        if current_time - self.last_set_deaths_time >= self.command_cooldown:
                            try:
                                self.deaths = int(command_parts[1])
                                self.send_privmsg(message.channel, f'Ustawiono liczbę śmierci na: {self.deaths} {random.choice(self.emotes)}')
                            except ValueError:
                                self.send_privmsg(message.channel,
                                                  f'@{message.user} Coś się zjebało {random.choice(self.emotes)} napisz do Krwawyy z błędem')
                            self.last_set_deaths_time = current_time

                elif message.text.startswith('!setbossdeaths'):
                    if self.boss_active:
                        command_parts = message.text.split()
                        if len(command_parts) >= 2:
                            try:
                                self.deaths_boss = int(command_parts[1])
                                self.send_privmsg(message.channel,
                                                  f'Ustawiono liczbę śmierci na bossie na: {self.deaths_boss}')
                            except ValueError:
                                self.send_privmsg(message.channel,
                                                  f'@{message.user} Coś się zjebało {random.choice(self.emotes)} oznacz mnie i napisz co jest 5')

                elif message.text_command == '!stopboss':
                    if self.boss_active:
                        if current_time - self.last_stop_boss_time >= self.command_cooldown:
                            self.boss_stopped = True
                            self.send_privmsg(message.channel,
                                              f'@{message.user} {message.channel} się zmęczył po {self.deaths_boss} '
                                              f'wyjebkach {random.choice(self.emotes)}')
                            self.last_stop_boss_time = current_time
                            try:
                                self.read_data_from_file()
                            except ValueError:
                                print("Zjebało się")
                    else:
                        self.send_privmsg(message.channel, f'Nie ma ustawionego bossa hm')

                elif message.text_command == '!resumeboss':
                    if self.boss_active and self.boss_stopped:
                        if current_time - self.last_resume_boss_time >= self.command_cooldown:
                            try:
                                self.read_data_from_file()
                                self.boss_stopped = False
                                self.boss_start_time = time.time()
                                self.send_privmsg(message.channel, f'@{message.user} Boss: {self.boss_name} wznowiony {random.choice(self.emotes)}')
                            except ValueError:
                                print("Zjebało się")
                            self.last_resume_boss_time = current_time
                    else:
                        self.send_privmsg(message.channel, f'Nie ma ustawionego bossa hm')

    def loop_for_messages(self):
        while self._connected:
            try:
                received_msgs = self.irc.recv(4096).decode()
                for received_msg in received_msgs.split('\r\n'):
                    self.handle_message(received_msg)
            except Exception as e:
                print(e)
                self._connected = False

    @staticmethod
    def create_db_file_if_not_exists(file_name):
        try:
            with open(file_name, 'x', encoding='utf-8') as file:
                print(f'File {file_name} created successfully.')
        except FileExistsError:
            print(f'Reading data from {file_name}.')

    def read_data_from_file(self):
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
                    self.boss_name = temp[1]
                    if data[2] != ' ':
                        self.boss_active = True
                        self.boss_stopped = True
                    if data[3] != ' ':
                        temp = data[3].split(" ")
                        self.deaths_boss = int(temp[1])
                    if data[4] != ' ':
                        temp = data[4].split(" ")
                        self.boss_timer_file = str(temp[1])
                else:
                    print(f'Error: Incorrect data format in file {self.name_file}.')
        except FileNotFoundError:
            print(f'Error: File {self.name_file} not found.')

    def write_data_to_file(self):
        if self.boss_active and self.boss_stopped is False:
            time_difference_seconds = round(time.time() - self.boss_start_time)
            time_difference = timedelta(seconds=time_difference_seconds)
            time_delta_from_string = datetime.strptime(self.boss_timer_file, '%H:%M:%S') - datetime.strptime('00:00:00',
                                                                                                             '%H:%M:%S')
            self.boss_timer = time_difference + time_delta_from_string
        elif self.boss_active and self.boss_stopped:
            self.boss_timer = datetime.strptime(self.boss_timer_file, '%H:%M:%S') - datetime.strptime('00:00:00',
                                                                                                      '%H:%M:%S')
        try:
            with open(self.name_file, 'w', encoding='utf-8') as file:
                if self.boss_active or self.boss_stopped:
                    file.write(
                        f'śmierci: {self.deaths}\n\nboss: {self.boss_name}\nśmierci: {self.deaths_boss}\nczas: {self.boss_timer}')
                else:
                    file.write(
                        f'śmierci: {self.deaths}\n\n \n \n ')
        except FileNotFoundError:
            print(f'Error: File {self.name_file} not found.')

    @staticmethod
    def create_or_load_settings():
        settings_file_name = 'settings.yaml'
        yaml = YAML()
        try:
            with open(settings_file_name, 'r', encoding='utf-8') as file:
                settings = yaml.load(file)
                print(f'File {settings_file_name} already exists. Loaded existing settings.')
                return settings
        except FileNotFoundError:
            default_settings = {
                'channel': 'krwawyy',
                'spam_bot_enabled': True,
                'spambot_cooldown': 300,
                'white_list_enabled': False,
                'white_list': ['krwawyy'],
                'black_list_enabled': False,
                'black_list': ['krwawyy', 'overpow'],
                'emotes': ["aha9", "aha1000", "HAHAHA", "beka", "alejaja", "gachiRoll", "duch", "buh", "xdd", "xpp", "trup",
                           "blushh", "owo", "owoCheer", "Evilowo"],
                'command_cooldown': 15,
                'all_users_mod': True,
                'bot_moderators': ['mod', 'subscriber', 'vip', 'broadcaster']

            }
            default_settings = comments.CommentedMap(default_settings)
            default_settings.yaml_add_eol_comment('Kanał na którym ma działać bot np. "krwawyy"', key='channel')
            default_settings.yaml_add_eol_comment('Wyłącza lub włącza automatyczne wysyłanie wiadomości co spambot_cooldown', key='spam_bot_enabled')
            default_settings.yaml_add_eol_comment('Czas co ile ma pisać wiadomość', key='spambot_cooldown')
            default_settings.yaml_add_eol_comment('Czy whitelista ma być włączona (użytkownik wpisany na listę zawsze będzie mógł moderować bota)', key='white_list_enabled')
            default_settings.yaml_add_eol_comment('Lista użytkowników na whiteliscie', key='white_list')
            default_settings.yaml_add_eol_comment('Czy blacklista ma być włączona (użytkownik wpisany na listę nie będzie mógł moderować bota)', key='black_list_enabled')
            default_settings.yaml_add_eol_comment('Lista użytkowników na blackliscie', key='black_list')
            default_settings.yaml_add_eol_comment('Losowe emotki dodawane w wiadomościach', key='emotes')
            default_settings.yaml_add_eol_comment('Cooldown na wiadomości, np. 15 oznacza, że przez 15 sekund po napisaniu np. "!death+" kolejne wywołania komendy nie zadziałają', key='command_cooldown')
            default_settings.yaml_add_eol_comment('Czy wszyscy użytkownicy mogą moderować bota: "!death+", "!death-", "!setdeaths", "!startboss", "!stopboss", "!finishboss", "!setbossdeaths"', key='all_users_mod')
            default_settings.yaml_add_eol_comment('Kto może moderować bota, możliwe opcje: "mod", "subscriber", "vip", "broadcaster"', key='bot_moderators')

            with open(settings_file_name, 'w', encoding='utf-8') as file:
                yaml.dump(default_settings, file)
                print(f'File {settings_file_name} created with default settings.')
                return default_settings
        except Exception:
            print('Błąd, usuń plik settings.yaml i spróbuj ponownie')

    def apply_settings_from_file(self, settings):
        self.channel = settings['channel']
        self.spam_bot_enabled = settings['spam_bot_enabled']
        self.spambot_cooldown = settings['spambot_cooldown']

        if bool(settings['white_list']):
            self.white_list_enabled = settings['white_list_enabled']
            self.white_list = settings['white_list']
        else:
            self.white_list_enabled = False
        if bool(settings['black_list']):
            self.black_list_enabled = settings['black_list_enabled']
            self.black_list = settings['black_list']
        else:
            self.black_list_enabled = False
        self.emotes = settings['emotes']
        self.command_cooldown = settings['command_cooldown']
        self.all_users_mod = settings['all_users_mod']
        self.bot_moderators = settings['bot_moderators']

    def open(self):
        self.create_db_file_if_not_exists(self.name_file)

        settings = self.create_or_load_settings()
        self.apply_settings_from_file(settings)
        self.connect()
        self.loop_for_messages()


def write_data_thread():
    sec = 0
    while True:
        tb.write_data_to_file()
        time.sleep(0.5)
        if tb.spam_bot_enabled:
            if sec >= tb.spambot_cooldown:
                tb.send_privmsg(tb.channel, "Wpisujcie '!death+', aby zwiększyć licznik bota bo dziadek zapomina okok ,"
                                            f" istnieje też komenda !help w której są wypisane wszystkie komendy! {random.choice(tb.emotes)}"
                                            f" gdyby dziadek włączył tego bota u siebie to licznik zmieniał by się na bieżąco xddShrug")
                sec = 0
            sec += 0.5



if __name__ == '__main__':
    # tb = TwitchBot(input("Podaj nazwę kanału: "))
    tb = TwitchBot('krwawyy')
    tb.read_data_from_file()

    write_data_thread = threading.Thread(target=write_data_thread)
    open_thread = threading.Thread(target=tb.open)

    # Uruchamiamy oba wątki
    write_data_thread.start()
    open_thread.start()
