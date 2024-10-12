import socket
import logging
from typing import Optional


class TwitchConnection:
    def __init__(self, server: str = 'irc.twitch.tv', port: int = 6667):
        self.server: str = server
        self.port: int = port
        self.irc: Optional[socket.socket] = None
        self.username: Optional[str] = None
        self.oauth_token: Optional[str] = None
        self.channel: Optional[str] = None
        self._connected: bool = False

        self.logger = logging.getLogger(__name__)

    def connect(self, username: str, oauth_token: str, channel: str) -> None:
        if self._connected:
            self.logger.warning("Already connected. Disconnecting and reconnecting.")
            self.disconnect()

        self.username = username
        self.oauth_token = oauth_token
        self.channel = channel

        try:
            self.irc = socket.socket()
            self.irc.connect((self.server, self.port))
            self._send_command(f'PASS {self.oauth_token}')
            self._send_command(f'NICK {self.username}')
            self._send_command(f'JOIN #{self.channel}')
            self._send_raw('CAP REQ :twitch.tv/tags\r\n')
            self._connected = True
            self.logger.info(f"Connected to {self.channel} as {self.username}")
        except Exception as e:
            self.logger.error(f"Failed to connect: {str(e)}")
            raise

    def disconnect(self) -> None:
        if self._connected and self.irc:
            try:
                self._send_command(f'PART #{self.channel}')
                self.irc.close()
                self.logger.info(f"Disconnected from {self.channel}")
            except Exception as e:
                self.logger.error(f"Error during disconnection: {str(e)}")
            finally:
                self._connected = False
                self.irc = None

    def is_connected(self) -> bool:
        return self._connected

    def send_privmsg(self, message: str) -> None:
        if not self._connected:
            raise ConnectionError("Not connected to Twitch IRC")
        self._send_command(f'PRIVMSG #{self.channel} :{message}')

    def receive_messages(self) -> str:
        if not self._connected or not self.irc:
            raise ConnectionError("Not connected to Twitch IRC")
        messages = self.irc.recv(4096).decode('utf-8')
        if messages.startswith('PING'):
            self.pong()
        return messages

    def _send_command(self, command: str) -> None:
        if not self.irc:
            raise ConnectionError("Socket not initialized")
        if 'PASS' not in command:
            print(f'< {command}')
        self.irc.send((command + '\r\n').encode())

    def _send_raw(self, message: str) -> None:
        if not self.irc:
            raise ConnectionError("Socket not initialized")
        self.irc.sendall(message.encode())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def pong(self):
        self._send_command('PONG :tmi.twitch.tv')