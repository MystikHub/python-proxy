import datetime
import socket
from threading import Thread

HOST = ''
PORT = 4000
BUFF_SIZE = 65536
cache = {}
blacklist = []
totalTX = 0
totalRX = 0

def getRequestText(conn):
    requestText = ""

    stillreceiving = True
    while stillreceiving:
        try:
            data = conn.recv(BUFF_SIZE)
            if data == b'':
                stillreceiving = False
            else:
                requestText += data.decode('ISO-8859-1')
            if data.decode('ISO-8859-1').endswith("\r\n\r\n"):
                stillreceiving = False
        except BlockingIOError:
            pass

    return requestText

def getHttpInfo(requestText):

    # Request text was empty
    if requestText == '':
        return None, None, None, None

    # Find the first line of the HTTP(S) request
    requestLines = requestText.split('\n')
    firstLineSplit = requestLines[0].split()

    # Http method
    HttpType = firstLineSplit[0]
    HttpURL = firstLineSplit[1]

    requestHost = None
    requestPort = -1
    for line in requestLines:
        if line.startswith("Host: "):
            url = line.split()[1].split(':')
            requestHost = url[0]
            requestPort = int(url[1]) if len(url) > 1 else 80

    return HttpType, HttpURL, requestHost, requestPort

def clientToServer(client, server, serverHost, serverPort, addr, mmc):
    server.settimeout(60 * 5)
    while True:
        if serverHost not in blacklist:
            try:
                data = client.recv(BUFF_SIZE)
                server.sendall(data)

                # Report
                formatted = str(len(data) // 1000) + " KB" if len(data) > 1000 else str(len(data)) + " B"
                if len(data) > 0:
                    report = "[{}] HTTPS Encrypted packet\n      {}:{} -> {}:{}\n      Client to server (TX): {:6s}\n".format(datetime.datetime.now().time(), addr[0], addr[1], serverHost, serverPort, formatted)
                    mmc.updateOutput(report)
            except BlockingIOError:
                pass
            except ConnectionResetError:
                break
            except BrokenPipeError:
                pass
            except socket.timeout:
                break

def serverToClient(server, client, serverHost, serverPort, addr, mmc):
    server.settimeout(60 * 5)
    while True:
        if serverHost not in blacklist:
            try:
                data = server.recv(BUFF_SIZE)
                client.sendall(data)

                # Report
                formatted = str(len(data) // 1000) + " KB" if len(data) > 1000 else str(len(data)) + " B"
                if len(data) > 0:
                    report = "[{}] HTTPS Encrypted packet\n      {}:{} -> {}:{}\n      Server to client (RX): {:6s}\n".format(datetime.datetime.now().time(), serverHost, serverPort, addr[0], addr[1], formatted)
                    mmc.updateOutput(report)
            except BlockingIOError:
                pass
            except ConnectionResetError:
                break
            except BrokenPipeError:
                pass
            except socket.timeout:
                break

def forwardConnection(client, addr, mmc):
    global HttpsCount, HttpCount, cache, blacklist

    requestText = getRequestText(client)
    HttpType, HttpUrl, requestHost, requestPort = getHttpInfo(requestText)

    # Request body was empty
    if HttpType is None:
        client.close()
        return

    # Host is blacklisted
    if requestHost in blacklist:
        text = "[{}] HTTP {}\n      {}:{} -> {}\n      Connection rejected, host is blacklisted\n".format(datetime.datetime.now().time(), HttpType, addr[0], addr[1], HttpUrl)
        mmc.updateOutput(text)
        client.close()
        return


    # Connect to the server
    serversock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversock.connect((requestHost, requestPort))
    serversock.setblocking(0)


    report = ''
    if HttpType == 'CONNECT':
        client.sendall("HTTP/1.1 200 OK \r\n\r\n".encode('ISO-8859-1'))

        serverThread = Thread(target=serverToClient, args=(serversock, client, requestHost, requestPort, addr, mmc, ))
        serverThread.start()

        clientThread = Thread(target=clientToServer, args=(client, serversock, requestHost, requestPort, addr, mmc, ))
        clientThread.start()

        report = "[{}] HTTPS CONNECT\n      {}:{} -> {}".format(datetime.datetime.now().time(), addr[0], addr[1], HttpUrl)
    else:
        report = "[{}] HTTP {}\n      {}:{} -> {}".format(datetime.datetime.now().time(), HttpType, addr[0], addr[1], HttpUrl)

        # Cache stuff
        requestId = requestText.split("\n")[0]
        if requestId in cache:
            report += "\n      Server to client (RX) 0 B"
            report += "\n      CACHE HIT"
            client.sendall(cache[requestId])
        else:
            response = ""
            serversock.sendall(requestText.encode())
            stillreceiving = True
            while stillreceiving:
                try:
                    data = serversock.recv(BUFF_SIZE)
                    if data == b'':
                        stillreceiving = False
                    else:
                        response += data.decode('ISO-8859-1')
                    if data.decode('ISO-8859-1').endswith('\r\n\r\n'):
                        stillreceiving = False
                except BlockingIOError:
                    pass

            encodedResponse = response.encode('ISO-8859-1')
            client.sendall(encodedResponse)

            # Add this request to the cache
            cache[requestId] = encodedResponse

            # Report
            formatted = str(len(response) // 1000) + " KB" if len(response) > 1000 else str(len(response)) + " B"

            report += "\n      Server to client (RX) " + formatted
            report += "\n      CACHE MISS"

    mmc.updateOutput(report + "\n")

def main(mmc):
    global HOST, PORT

    # Set up the proxy server
    proxySocket =  socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxySocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    proxySocket.bind((HOST, PORT))
    proxySocket.listen()

    # Start listening for connections
    while True:
        conn, addr = proxySocket.accept()
        conn.setblocking(0)
        request = Thread(target=forwardConnection, args=(conn, addr, mmc, ))
        request.start()
