import socket
import os
import threading
import logging
from gi.repository import GLib

logger = logging.getLogger(__name__)
SOCKET_PATH = "/tmp/cyber_radio.sock"

class IPCHandler:
    def __init__(self, main_window):
        self.main_window = main_window
        self.socket = None

    def create_socket(self):
        """Creates and listens on the Unix socket."""
        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)

        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.bind(SOCKET_PATH)
        self.socket.listen(1)

        thread = threading.Thread(target=self._listen_for_connections, daemon=True)
        thread.start()

    def _listen_for_connections(self):
        while True:
            try:
                connection, client_address = self.socket.accept()
                self.handle_connection(connection)
            except Exception as e:
                logger.error(f"IPC connection error: {e}")
                break

    def handle_connection(self, connection):
        try:
            data = connection.recv(1024).decode()
            if data:
                logger.info(f"Received IPC command: {data}")
                # Use GLib.idle_add to call the main window methods from the main thread
                GLib.idle_add(self.main_window.handle_ipc_command, data)
        finally:
            connection.close()

    @staticmethod
    def send_command(command):
        """Connects to the socket and sends a command."""
        if not os.path.exists(SOCKET_PATH):
            logger.error("Cyber Radio is not running.")
            return False

        try:
            client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client_socket.connect(SOCKET_PATH)
            client_socket.sendall(command.encode())
        except Exception as e:
            logger.error(f"Failed to send IPC command: {e}")
            return False
        finally:
            client_socket.close()
        
        return True
