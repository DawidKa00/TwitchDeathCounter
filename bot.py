import time
from datetime import timedelta

from python_twitch_irc import TwitchIrc
from dotenv import load_dotenv
import os
import socket
from collections import namedtuple

load_dotenv()
PARTICIPATE_COMMANDS = ['!death+', '!death-', '!deaths']

Message = namedtuple(
    'Message',
    'prefix user channel irc_command irc_args badge_info text text_command text_args',
)
channel = 'krwawyy'


class TwitchBot(TwitchIrc):
    __instance = None

    def __init__(self):

        self._connected = False
        self.irc_server = 'irc.twitch.tv'
        self.irc_port = 6667
        self.irc = socket.socket()
        self.oauth_token = os.getenv("OAUTH_TOKEN")
        self.username = os.getenv("USER_NAME")
        self.channel = channel
        self.deaths = 62
        self.deaths_boss = 0
        self.boss_active = False
        self.boss_start_time = None
        self.boss_name = None
        self.last_death_plus_time = 0
        self.last_death_minus_time = 0
        self.death_command_cooldown = 10
        self.last_stop_boss_time = 0
        self.last_start_boss_time = 0
        self.last_set_deaths_time = 0
        self.users = ['fiz0waty_', 'overpow', 'krwawyy', 'apsik', 'seve__', 'sakyuu', 'aiszjaa', 'mhadox_', 'superjez', 'kebes95', 'martozaur']


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
            self.send_command(f'JOIN #{channel}')
            self.send_raw('CAP REQ :twitch.tv/tags\r\n')
            self._connected = True
            self.is_opened = True
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
                if self.boss_active:
                    time_difference_seconds = round(time.time() - self.boss_start_time)
                    time_difference = timedelta(seconds=time_difference_seconds)
                    self.send_privmsg(message.channel,f'@{message.user} {self.boss_name} robiony od '
                                                      f'{str(time_difference)} i tylko {self.deaths_boss} wyjebki ok w sumie {self.deaths}')
                else:
                    self.send_privmsg(channel, f'@{message.user} {channel} wypierdolił się już {self.deaths} razy beka')
            if message.user.lower() in self.users and message.channel.lower() == channel.lower():
                current_time = time.time()
                if message.text_command == '!death+':
                    if current_time - self.last_death_plus_time >= self.death_command_cooldown:
                        self.deaths += 1
                        print("Incrementing death counter by 1")
                        if self.boss_active:
                            self.deaths_boss += 1
                            self.send_privmsg(channel, f'{self.deaths_boss} wyjebek na bossie i {self.deaths} ugółem baxton')
                        else:
                            self.send_privmsg(channel, f'Wypierdolki: {self.deaths} xdd')
                        self.last_death_plus_time = current_time
                    else:
                        print("Command on cooldown, try again later")

                elif message.text_command == '!death-':
                    if current_time - self.last_death_minus_time >= self.death_command_cooldown:
                        self.deaths -= 1
                        print("Decrementing death counter by 1")
                        if self.boss_active:
                            self.deaths_boss -= 1
                            self.send_privmsg(channel, f'{self.deaths_boss} wyjebek na bossie i {self.deaths} ugółem baxton')
                        else:
                            self.send_privmsg(channel, f'Wypierdolki: {self.deaths}')
                        self.last_death_minus_time = current_time
                    else:
                        print("Command on cooldown, try again later")

                elif message.text.startswith('!setdeaths'):
                    command_parts = message.text.split(' ')
                    if len(command_parts) >= 2:
                        if current_time - self.last_set_deaths_time >= self.death_command_cooldown:
                            try:
                                # Sprawdzenie, czy druga część jest liczbą
                                self.deaths = int(command_parts[1])
                                self.send_privmsg(message.channel, f'Ustawiono liczbę śmierci na: {self.deaths}')
                            except ValueError:
                                self.send_privmsg(channel, f'@{message.user} Coś się zjebało okok oznacz mnie i napisz co jest 5')
                            self.last_set_deaths_time = current_time
                        else:
                            print("Command on cooldown, try again later")

                elif message.text.startswith('!setbossdeaths'):
                    if self.boss_active is False:
                        command_parts = message.text.split()
                        if len(command_parts) >= 2:
                            try:
                                self.deaths_boss = int(command_parts[1])
                                self.send_privmsg(message.channel, f'Ustawiono liczbę śmierci na: {self.deaths_boss}')
                            except ValueError:
                                self.send_privmsg(channel, f'@{message.user} Coś się zjebało okok oznacz mnie i napisz co jest 5')
                    else:
                        pass

                elif message.text.startswith('!startboss'):
                    if self.boss_active is False:
                        command_parts = message.text.split()
                        self.deaths_boss = 0
                        if len(command_parts) >= 2:
                            if current_time - self.last_start_boss_time >= self.death_command_cooldown:
                                try:
                                    self.boss_start_time = time.time()
                                    self.boss_name = str(command_parts[1])
                                    self.send_privmsg(message.channel, f'Boss: {self.boss_name}')
                                    self.boss_active = True
                                except ValueError:
                                    print("Zjebało się")
                                self.last_start_boss_time = current_time
                            else:
                                print("Command on cooldown, try again later")
                    else:
                        pass

                elif message.text_command == '!stopboss':
                    if self.boss_active:
                        if current_time - self.last_stop_boss_time >= self.death_command_cooldown:
                            boss_stop_time = time.time()
                            time_difference_seconds = round(boss_stop_time - self.boss_start_time)
                            time_difference = timedelta(seconds=time_difference_seconds)
                            self.send_privmsg(message.channel, f'{self.boss_name} rozjebany z {self.deaths_boss} '
                                                               f'wyjebkami po {str(time_difference)} PogChomp')
                            self.boss_active = False
                            self.last_stop_boss_time = current_time
                        else:
                            print("Command on cooldown, try again later")
                    else:
                        self.send_privmsg(message.channel, f'Nie ma ustawionego bossa hm')

                elif message.text_command == '!help':
                    self.send_privmsg(message.channel, 'Są takie komendy: '
                                                       '!deaths (dla wszystkich) - wyświetla aktualną liczbę śmierci, '
                                                       '!death+ (mod/vip/wic) - dodaje 1 do licznika, '
                                                       '!death- (mod/vip/wic) - odejmuje 1 od licznika, '
                                                       '!setdeaths {liczba} (mod/vip/wic) - zmienia liczbę śmierci, '
                                                       '!startboss {nazwa_bossa} (mod/vip/wic) - rozpoczyna bossa, '
                                                       '!stopboss (mod/vip/wic) - kończy bossa, '
                                                       '!setbossdeaths {liczba} (mod/vip/wic) - zmienia liczbę śmierci bossa')

    def loop_for_messages(self):
        while self._connected:
            try:
                received_msgs = self.irc.recv(4096).decode()
                for received_msg in received_msgs.split('\r\n'):
                    self.handle_message(received_msg)
            except:
                self._connected = False

    def open(self):
        self.connect()
        self.loop_for_messages()


if __name__ == '__main__':
    tb = TwitchBot()
    channel = input("Podaj kanał z ttv na którym ma działać bot: ")
    user = ' '
    print("Podaj nicki osób które będą mogły moderować bota")
    print("Brak znaków przejdzie dalej")
    while user != '':
        user = input("")
        tb.users.append(user.lower())
        print(tb.users)
    tb.open()
