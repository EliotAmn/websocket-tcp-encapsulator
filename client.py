import socket
import threading
import time
import websocket

# You can use this class into your own project
class WsTCPEncapsulator:
    def __init__(self):
        # Websocket server URL (wss if SSL, ws if not SSL)
        self.url = "wss://example.com/ws-tunnel"

        # Password defined in server.py
        self.password = "MySecurePassword"


        self.proxyconn = None
        self.connections = {}
        self.closed = False
        threading.Thread(target=self.start).start()

    def start(self):

        while True:
            print("[INFO]", "Starting encapsulator...")
            try:

                while True:
                    if self.url != "":
                        self.proxyconn = websocket.WebSocketApp(self.url, on_open=self.on_open, on_close=self.on_close, on_message=self.on_message)
                        self.proxyconn.run_forever()
                    time.sleep(2)
            except Exception as e:
                print("ERROR", "Encapsulator WS error: {}. Restarting...".format(e))
                time.sleep(3)

    def on_open(self, ws):
        print("[INFO]", "Connected to server !")
        ws.send(self.password)

    def on_close(self, ws, code, reason):
        self.closed = True
        print("[ERR]", "Websocket disconnected")

    def on_message(self, ws, data):
        decoded = data
        token = decoded.split(';')[0]
        if token == "AUTH":
            tkn = decoded.split(';')[1]
            ip = decoded.split(';')[2]
            port = decoded.split(';')[3].replace("|", "")
            c = ConnectionInstance(tkn, ip, int(port), self)
            self.connections[decoded.split(';')[1]] = c
        elif token == "CLOSE":
            token = decoded.split(';')[1]
            if token in self.connections:
                self.connections[token].close()
        elif token in self.connections:
            hexdata = decoded.split(";")[1].replace("|", "")
            bytesdata = bytes.fromhex(hexdata)
            self.connections[token].conn.send(bytesdata)
        else:
            self.proxyconn.send(str("CLOSE" + ";" + token + "|"))

class ConnectionInstance:
    
    def __init__(self, token: str, ip: str, port: int, manager: WsTCPEncapsulator):
        self.token = token
        self.ip = ip
        self.port = port
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.connect((self.ip, self.port))
        self.closed = False
        self.manager = manager
        self.thread = threading.Thread(target=self.recv_thread)
        self.thread.start()

    def close(self):
        if not self.closed:
            self.closed = True
            self.manager.connections.pop(self.token)

    def recv_thread(self):
        try:
            while not self.closed:
                data = self.conn.recv(1024)
                if not data:
                    self.manager.proxyconn.send(str("CLOSE" + ";" + self.token + "|"))
                    self.conn.close()
                    self.close()
                    return
                self.manager.proxyconn.send(str(self.token + ";" + str(data.hex()) + "|"))
        except (ConnectionAbortedError, ConnectionResetError):
            self.manager.proxyconn.send(str("CLOSE" + ";" + self.token + "|"))
            self.conn.close()
            self.close()
            return

WsTCPEncapsulator()
