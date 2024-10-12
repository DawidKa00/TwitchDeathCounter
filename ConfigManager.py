import os
from typing import Any, Dict
import logging
from ruamel.yaml import YAML, comments


class ConfigManager:
    def __init__(self, config_file: str = 'settings.yaml'):
        self.logger = logging.getLogger(__name__)
        self.config_file = config_file
        self.config: Dict[str, Any] = {}
        self.yaml = YAML()
        self.load_config()

    def load_config(self) -> None:
        """Wczytuje konfigurację z pliku YAML."""
        try:
            if not os.path.exists(self.config_file):
                self.create_default_config()

            with open(self.config_file, 'r', encoding='utf-8') as file:
                self.config = self.yaml.load(file)
            self.logger.info(f"Configuration loaded from {self.config_file}")
        except Exception as e:
            self.logger.error(f"Error loading configuration: {str(e)}")
            raise

    def save_config(self) -> None:
        """Zapisuje aktualną konfigurację do pliku YAML."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as file:
                self.yaml.dump(self.config, file)
            self.logger.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            self.logger.error(f"Error saving configuration: {str(e)}")
            raise

    def create_default_config(self) -> None:
        """Tworzy domyślną konfigurację, jeśli plik nie istnieje."""
        default_config = comments.CommentedMap({
            'channel': 'krwawyy',
            'prefix': "!",
            'spam_bot_enabled': True,
            'spam_bot_messages': 50,
            'spam_bot_message': "Wpisujcie '!death+', aby zwiększyć licznik, istnieje też komenda '!help' w której są wypisane wszystkie komendy!",
            'white_list_enabled': True,
            'white_list': ['your_nickname', 'arquel'],
            'black_list_enabled': False,
            'black_list': ['nick'],
            'emotes': ["aha9", "aha1000", "HAHAHA", "beka", "alejaja", "gachiRoll", "duch", "buh", "xdd", "xpp", "trup",
                       "blushh", "owo", "owoCheer", "Evilowo"],
            'command_cooldown': 15,
            'all_users_mod': True,
            'bot_moderators': ['mod', 'subscriber', 'vip', 'broadcaster'],
            'extra_command_1_enabled': False,
            'extra_command_1': 'malenia',
            'extra_command_1_text': 'Malenia rozwalona po 10 godzinach',
            'extra_command_2_enabled': False,
            'extra_command_2': 'dis',
            'extra_command_2_text': 'Dis rozwalony po 20 latach'
        })

        # Dodawanie komentarzy do konfiguracji
        default_config.yaml_add_eol_comment('Kanał na którym ma działać bot np. "krwawyy"', key='channel')
        default_config.yaml_add_eol_comment('Prefix komend np. "!" lub "^", pamiętaj, aby zmienić prefiksy poniżej!', key='prefix')
        default_config.yaml_add_eol_comment('Wyłącza lub włącza automatyczne wysyłanie wiadomości co spambot_cooldown',
                                            key='spam_bot_enabled')
        default_config.yaml_add_eol_comment('Czas co ile wiadomości ma wysyłać wiadomość', key='spam_bot_messages')
        default_config.yaml_add_eol_comment(
            'Wiadomość wysyłana co x wiadomości, pamiętaj żeby zmienić prefix w wiadomości!', key='spam_bot_message')
        default_config.yaml_add_eol_comment(
            'Czy whitelista ma być włączona (użytkownik wpisany na listę zawsze będzie mógł moderować bota)',
            key='white_list_enabled')
        default_config.yaml_add_eol_comment('Lista użytkowników na whiteliscie', key='white_list')
        default_config.yaml_add_eol_comment(
            'Czy blacklista ma być włączona (użytkownik wpisany na listę nie będzie mógł moderować bota)',
            key='black_list_enabled')
        default_config.yaml_add_eol_comment('Lista użytkowników na blackliscie', key='black_list')
        default_config.yaml_add_eol_comment('Losowe emotki dodawane w wiadomościach', key='emotes')
        default_config.yaml_add_eol_comment(
            'Cooldown na wiadomości, np. 15 oznacza, że przez 15 sekund po napisaniu np. "!death+" kolejne wywołania komendy nie zadziałają',
            key='command_cooldown')
        default_config.yaml_add_eol_comment(
            'Czy wszyscy użytkownicy mogą moderować bota: "!death+", "!death-", "!setdeaths", "!startboss", "!pauseboss", "!finishboss", "!setbossdeaths"',
            key='all_users_mod')
        default_config.yaml_add_eol_comment(
            'Kto może moderować bota, możliwe opcje: "mod", "subscriber", "vip", "broadcaster" lub używaj whitelist/blacklist', key='bot_moderators')
        default_config.yaml_add_eol_comment('Czy włączyć dodatkową komendę?', key='extra_command_1_enabled')
        default_config.yaml_add_eol_comment('Jak ma być wywoływana ta komenda?', key='extra_command_1')
        default_config.yaml_add_eol_comment('Co bot ma pisać gdy, ktoś wpisze komendę?', key='extra_command_1_text')
        default_config.yaml_add_eol_comment('Czy włączyć dodatkową komendę?', key='extra_command_2_enabled')
        default_config.yaml_add_eol_comment('Jak ma być wywoływana ta komenda?', key='extra_command_2')
        default_config.yaml_add_eol_comment('Co bot ma pisać gdy, ktoś wpisze komendę?', key='extra_command_2_text')

        self.config = default_config
        self.save_config()
        self.logger.info(f"Created default configuration file: {self.config_file}")

    def __getitem__(self, key: str) -> Any:
        """Pobiera wartość z konfiguracji za pomocą nawiasów kwadratowych."""
        return self.config.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Ustawia wartość w konfiguracji za pomocą nawiasów kwadratowych."""
        self.config[key] = value