import random
import socket
import threading
from flask import Flask
from flask_sock import Sock

config = {
    "servers": [
        {
            "name": "my-device",
            "listen_port": 3033, # Websocket server port (client.py use this port) Ex: client connect to wss://example.com:3033/ws-tunnel
            "password": "MySecurePassword",
            "ports": {
                "4000": { # Local port 4000 redirects to port 22 on the device running client.py.
                    "redirect_ip": "127.0.0.1",
                    "redirect_port": 22
                },
                "4001": { # Local port 4001 redirects to port 8080 on the device running client.py.
                    "redirect_ip": "127.0.0.1",
                    "redirect_port": 8080
                },
                "4002": { # Local port 4003 redirects to port 80 on the "192.168.1.1" host in the network of device running client.py.
                    "redirect_ip": "192.168.1.1",
                    "redirect_port": 80
                }
            }
        }
    ]
}


def recvall(sock):
    builded = ""
    while not builded.endswith("|"):
        builded += sock.receive()
    liste = builded.split("|")[:-1]
    return [x for x in liste]


def log(type, message, instance=None):
    types = {
        "INFO": bcolors.OKGREEN,
        "WARNING": bcolors.WARNING,
        "ERROR": bcolors.FAIL
    }
    print("[{}] [{}] {}".format(instance, types[type] + type + bcolors.ENDC, message) + bcolors.ENDC)


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class TunnelInstance:
    def __init__(self, config: dict):
        self.config = config
        self.port = config['listen_port']
        self.name = config['name']
        self.tokens = {}
        log("INFO", "Starting encapsulator server on port {}...".format(self.port), self.name)
        self.app = Flask(__name__)
        self.sock = Sock(self.app)
        self.host_connected = False
        self.deviceconn = None

        @self.sock.route('/ws-tunnel')
        def echo(sock):

            log("INFO", "Host connected ! Waiting login...", self.name)
            login = sock.receive()
            if login != self.config['password']:
                log("WARNING", "Client fails authentification", self.name)
                return
            log("INFO", "Client authentificated !", self.name)
            self.host_connected = True
            self.deviceconn = sock

            while True:
                try:
                    list = recvall(sock)
                except (ConnectionResetError, BrokenPipeError):
                    break

                for data in list:
                    if data == "":
                        continue
                    data = data
                    token = data.split(";")[0]
                    if token == "CLOSE":
                        if data.split(";")[1] in self.tokens:
                            self.tokens[data.split(";")[1]].client.close()
                            del self.tokens[data.split(";")[1]]
                    elif token in self.tokens:
                        self.tokens[token].client.send(bytes.fromhex(data.split(";")[1]))
                    else:
                        print("Token not found ( {} )".format(token))

            log("ERROR", "Host disconnected ! ({})".format("EMPTY"), self.name)
            log("WARNING", "Disconnecting all clients...", self.name)
            [x.stop() for x in self.tokens.values()]

        self.servers = []
        log("INFO", "Opening ports...", self.name)
        for source, data in config['ports'].items():
            try:
                self.servers.append(SocketServer(data['redirect_ip'], int(data['redirect_port']), int(source), self))
                log("INFO", "Local port {} opened.".format(source), self.name)
            except OSError as e:
                log("ERROR", "Port {} is already in use.".format(source), self.name)

        self.app.run(host='0.0.0.0', port=self.port, threaded=True)

class ClientSocketConnection:
    def __init__(self, token, client, instance):
        self.client = client
        self.token = token
        self.closed = False
        self.instance = instance
        threading.Thread(target=self.recv_thread).start()

    def stop(self):
        self.closed = True
        self.client.close()

    def recv_thread(self):
        while not self.closed:
            try:
                data = self.client.recv(1024)
                if not data:
                    self.instance.deviceconn.send(str("CLOSE" + ";" + self.token + "|"))
                    if self.token in self.instance.tokens:
                        del self.instance.tokens[self.token]
                        self.client.close()
                    break
                self.instance.deviceconn.send(str(self.token + ";" + str(data.hex()) + "|"))
            except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                break


class SocketServer:
    def __init__(self, redirect_ip, redirect_port, listen_port, instance):
        self.redirect_ip = redirect_ip
        self.redirect_port = redirect_port
        self.listen_port = listen_port
        self.instance = instance
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(('0.0.0.0', self.listen_port))
        self.server.listen(5)
        self.stopped = False
        threading.Thread(target=self.start).start()

    def start(self):
        while not self.stopped:
            client = self.server.accept()[0]
            if not self.instance.host_connected:
                client.close()
                continue
            if self.stopped:
                return
            i = 0
            while i == 0 or str(i) in self.instance.tokens:
                i = random.randint(1, 999999999)
                
            self.instance.deviceconn.send("AUTH;{};{};{}|".format(i, self.redirect_ip, self.redirect_port))
            cli = ClientSocketConnection(str(i), client, self.instance)
            self.instance.tokens[str(i)] = cli

for server in config['servers']:
    TunnelInstance(server)
