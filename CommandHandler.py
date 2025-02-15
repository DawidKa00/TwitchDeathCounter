import logging
import random
import time
from datetime import datetime

import TwitchBot

class CommandHandler:
    def __init__(self, twitch_bot: TwitchBot, config):
        self.last_command_times = {
            'death_plus': 0.0,
            'death_minus': 0.0,
            'start_boss': 0.0,
            'finish_boss': 0.0,
            'pause_boss': 0.0,
            'resume_boss': 0.0,
            'set_deaths': 0.0,
            'set_boss_deaths': 0.0,
        }

        self.twitch_bot = twitch_bot
        self.config = config

        self.commands_single_arg = {
            'deaths': self.show_deaths,
            'death+': self.increment_deaths,
            'death-': self.decrement_deaths,
            'finishboss': self.finish_boss,
            'pauseboss': self.pause_boss,
            'resumeboss': self.resume_boss,
        }

        self.commands_with_args = {
            'setdeaths': self.set_deaths,
            'setbossdeaths': self.set_boss_deaths,
            'startboss': self.start_boss,
        }

        self.commands_without_args = {
            'author': self.show_author,
            'help': self.show_help,
        }

        if self.config['extra_command_1_enabled']: self.commands_without_args[self.config['extra_command_1']] = self.command_1
        if self.config['extra_command_2_enabled']: self.commands_without_args[self.config['extra_command_2']] = self.command_2

        self.logger = logging.getLogger(__name__)

    def execute_command(self, command: str, user: str, authorized: bool, args: list) -> str:
        """Wykonuje odpowiednią komendę."""
        command = command.lower()
        # Sprawdzamy komendy bez argumentów
        if command in self.commands_without_args:
            return self.commands_without_args[command]()

        # Sprawdzamy komendy z jednym argumentem (tylko user)
        if command in self.commands_single_arg:
            return self.commands_single_arg[command](user, authorized)

        # Sprawdzamy komendy z dodatkowymi argumentami (user + args)
        if command in self.commands_with_args:
            return self.commands_with_args[command](user, authorized, args)


    def show_deaths(self, user: str) -> str:
        """Wyświetl aktualną liczbę śmierci."""
        if self.twitch_bot["boss_active"] and not self.twitch_bot['boss_paused']:
            return (f'@{user} {self.twitch_bot['boss_name']} robiony od '
                    f'{self.twitch_bot["boss_timer"]} i tylko {self.twitch_bot['deaths_boss']} wyjebki ok w sumie {self.twitch_bot['deaths']}')
        else:
            return (f'@{user} {self.twitch_bot['channel']} wypierdolił się już '
                    f'{self.twitch_bot['deaths']} razy {random.choice(self.twitch_bot['emotes'])}')

    def increment_deaths(self, user: str, authorized: bool) -> str:
        """Zwiększ licznik śmierci."""
        if authorized and self.is_cooldown_elapsed('death_plus'):
            self.twitch_bot['deaths'] += 1

            if (self.twitch_bot['boss_active']) and not self.twitch_bot['boss_paused']:
                self.twitch_bot['deaths_boss'] = (self.twitch_bot['deaths_boss'] or 0) + 1
                self.last_command_times['death_plus'] = time.time()
                self.logger.info(
                    f"> {user}: {self.config['prefix']}death+ - deaths: {self.twitch_bot['deaths']} - "
                    f"boss_name: {self.twitch_bot['boss_name']}, deaths_boss: {self.twitch_bot['deaths_boss']}")
                return (f'{self.twitch_bot['deaths_boss']} wyjebek na bossie i {self.twitch_bot['deaths']} '
                        f'ugółem {random.choice(self.twitch_bot['emotes'])}, {self.twitch_bot["boss_timer"]}')
            else:
                self.logger.info(f"> {user}: death+ - deaths: {self.twitch_bot['deaths']}")
            return f'Wypierdolki: {self.twitch_bot['deaths']} {random.choice(self.twitch_bot['emotes'])}'

    def decrement_deaths(self, user: str, authorized: bool) -> str:
        """Zmniejsz licznik śmierci."""
        if authorized and self.is_cooldown_elapsed('death_minus'):
            self.twitch_bot['deaths'] = max(0, self.twitch_bot['deaths'] - 1)
            if self.twitch_bot['boss_active'] and not self.twitch_bot['boss_paused']:
                self.twitch_bot['deaths_boss'] = max(0, (self.twitch_bot['deaths_boss'] or 0) - 1)
                self.last_command_times['death_minus'] = time.time()
                self.logger.info(
                    f"> {user}: {self.config['prefix']}death- - deaths: {self.twitch_bot['deaths']} - "
                    f"boss_name: {self.twitch_bot['boss_name']}, deaths_boss: {self.twitch_bot['deaths_boss']}")
                return (f'{self.twitch_bot['deaths_boss']} wyjebek na bossie i {self.twitch_bot['deaths']} '
                        f'ugółem {random.choice(self.twitch_bot['emotes'])}')
            else:
                self.logger.info(f"> {user}: {self.config['prefix']}death- - deaths: {self.twitch_bot['deaths']}")
            return f'Wypierdolki: {self.twitch_bot['deaths']} {random.choice(self.twitch_bot['emotes'])}'
        return "Nie masz uprawnień do używania tej komendy."

    def show_help(self) -> str:
        """Pokaż dostępne komendy."""
        return (
            f"Są dostępne komendy: {self.config['prefix']}deaths (liczba śmierci), "
            f"{self.config['prefix']}death+ (dodaj 1), {self.config['prefix']}death- (odejmij 1), "
            f"{self.config['prefix']}setdeaths liczba (ustaw liczbę śmierci), "
            f"{self.config['prefix']}startboss nazwa (rozpocznij bossa), "
            f"{self.config['prefix']}finishboss (zakończ bossa), "
            f"{self.config['prefix']}pauseboss (pauza bossa), "
            f"{self.config['prefix']}resumeboss (wznów bossa), "
            f"{self.config['prefix']}setbossdeaths liczba (ustaw śmierci bossa), "
            f"{self.config['prefix']}author (info o autorze). "
            f"Cooldown: {self.config['command_cooldown']}s."
        )

    @staticmethod
    def show_author() -> str:
        """Pokaż info o autorze."""
        return ('Zostałem stworzony przez Krwawyy, z propozycjami lub błędami pisz na pw na Twitchu okok, '
                'jakbyś chciał coś dodać napisz to wyśle link do GitHuba wuda')

    def start_boss(self, user: str, authorized: bool, args: list) -> str:
        """Rozpocznij bossa."""
        if authorized and self.is_cooldown_elapsed('start_boss'):
            if not self.twitch_bot['boss_active'] and not self.twitch_bot['boss_paused']:
                if len(args) >= 1:
                    if args[len(args) - 1] == '\U000e0000':
                        args.pop(len(args) - 1)
                    self.twitch_bot['boss_name'] = ' '.join(args)
                    self.twitch_bot['boss_active'] = True
                    self.twitch_bot['boss_paused'] = False
                    self.twitch_bot['deaths_boss'] = 0
                    self.twitch_bot['boss_start_time'] = datetime.now()
                    self.last_command_times['start_boss'] = time.time()
                    self.logger.info(f"> {user}: {self.config['prefix']}startboss {self.twitch_bot['boss_name']} - "
                                     f"deaths: {self.twitch_bot['deaths']}")
                    return f'Boss: {self.twitch_bot['boss_name']} {random.choice(self.twitch_bot['emotes'])}'
            return (f'@{user} Boss {self.twitch_bot['boss_name']} jest aktywny zakończ go wpisując '
                    f'"{self.config['prefix']}finishboss" '
                    f'przed zaczęciem nowego {random.choice(self.twitch_bot['emotes'])}')

    def finish_boss(self, user: str, authorized: bool) -> str:
        """Zakończ bossa."""
        if authorized and self.is_cooldown_elapsed('finish_boss'):
            if self.twitch_bot['boss_active'] or self.twitch_bot['boss_paused']:
                self.twitch_bot['boss_active'] = False
                self.twitch_bot['boss_paused'] = False
                self.last_command_times['finish_boss'] = time.time()
                self.logger.info(
                    f"> {user}: {self.config['prefix']}finishboss - boss_name: {self.twitch_bot['boss_name']} - "
                    f"deaths: {self.twitch_bot['deaths']} - boss_deaths: {self.twitch_bot['deaths_boss']}")
                return (f'@{user} {self.twitch_bot['boss_name']} rozwalony z {self.twitch_bot['deaths_boss']} '
                        f'wyjebkami {random.choice(self.twitch_bot['emotes'])} po {self.twitch_bot['boss_timer']}')
            return "Nie ma ustawionego bossa hm"

    def pause_boss(self, user: str, authorized: bool) -> str:
        """Zatrzymaj bossa."""
        if authorized and self.is_cooldown_elapsed('pause_boss'):
            if self.twitch_bot['boss_active']:
                self.twitch_bot.pause_boss()  # Używamy nowej metody
                self.last_command_times['pause_boss'] = time.time()
                self.logger.info(
                    f"> {user}: {self.config['prefix']}pauseboss - boss_name: {self.twitch_bot['boss_name']} - "
                    f"deaths: {self.twitch_bot['deaths']} - boss_deaths: {self.twitch_bot['deaths_boss']}")
                return (f' {self.twitch_bot['channel']} się zmęczył po {self.twitch_bot['deaths_boss']} wyjebkach, czas: {self.twitch_bot['boss_timer']} '
                        f'{random.choice(self.twitch_bot['emotes'])}')
            return f"Nie ma ustawionego bossa hm"

    def resume_boss(self, user: str, authorized: bool) -> str:
        """Wznów bossa."""
        if authorized and self.is_cooldown_elapsed('resume_boss'):
            if self.twitch_bot['boss_paused']:
                self.twitch_bot.resume_boss()  # Używamy nowej metody
                self.last_command_times['resume_boss'] = time.time()
                self.logger.info(
                    f"> {user}: {self.config['prefix']}resumeboss - boss_name: {self.twitch_bot['boss_name']} - "
                    f"deaths: {self.twitch_bot['deaths']} - boss_deaths: {self.twitch_bot['deaths_boss']}")
                return f'@{user} Boss: {self.twitch_bot['boss_name']} wznowiony {random.choice(self.twitch_bot['emotes'])}'
            return "Nie ma ustawionego bossa hm"

    def set_deaths(self, user: str, authorized: bool, args: list) -> str:
        """Ustaw liczbę śmierci."""
        if authorized and self.is_cooldown_elapsed('set_deaths'):
            if len(args) > 0 and args[0].isnumeric():
                try:
                    self.twitch_bot['deaths'] = int(args[0])
                    self.last_command_times['set_deaths'] = time.time()
                    self.logger.info(
                        f"> {user}: {self.config['prefix']}setdeaths {int(args[0])}  - "
                        f"deaths: {self.twitch_bot['deaths']}")
                    return (f'Ustawiono liczbę śmierci na: {self.twitch_bot['deaths']} '
                            f'{random.choice(self.twitch_bot['emotes'])}')
                except ValueError:
                    return (f'@{user} Coś się Zepsuło {random.choice(self.twitch_bot['emotes'])} napisz do '
                            f'Krwawyy z błędem "/w Krwawyy nie działa"')

    def set_boss_deaths(self, user: str,authorized: bool, args: list) -> str:
        """Ustaw liczbę śmierci bossa."""
        if authorized and self.is_cooldown_elapsed('set_boss_deaths'):
            if (self.twitch_bot['boss_active'] or self.twitch_bot['boss_paused']) and len(args) >= 1:
                try:
                    self.twitch_bot['deaths_boss'] = int(args[0])
                    self.last_command_times['set_boss_deaths'] = time.time()
                    self.logger.info(
                        f"> {user}: {self.config['prefix']}setbossdeaths {int(args[0])} - boss_name: "
                        f"{self.twitch_bot['boss_name']} - deaths: {self.twitch_bot['deaths']} - "
                        f"boss_deaths: {self.twitch_bot['deaths_boss']}")
                    return f'Ustawiono liczbę śmierci na bossie na: {self.twitch_bot['deaths_boss']}'
                except ValueError:
                    return (f'@{user} Coś się Zepsuło {random.choice(self.twitch_bot['emotes'])} '
                            f'oznacz mnie albo napisz priv "/w Krwawyy nie działa"')
            return "Nie ma ustawionego bossa hm"


    def is_cooldown_elapsed(self, command: str) -> bool:
        """Sprawdza, czy minął odpowiedni cooldown od ostatniego wywołania."""  # Pobiera cooldown z konfiguracji
        last_time = self.last_command_times.get(command, 0)
        return time.time() - last_time >= self.config['command_cooldown']


    def command_1(self):
        return self.config['extra_command_1_text']

    def command_2(self):
        return self.config['extra_command_2_text']