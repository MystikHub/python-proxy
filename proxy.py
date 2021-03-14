import datetime
import socket
import time
from threading import Thread

HOST = ''
PORT = 4000
BUFF_SIZE = 65536
waitingToStart = []
cache = {}
blacklist = ['www.youtube.com']

def getRequestText(conn):
    start = time.time()
    # print('Entering getRequestText()')
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

    # print('Got a (hopefully) http request:\n{}'.format(requestText))
    diff = time.time() - start
    if diff > 0.6: print("Request collection took {} seconds".format(diff))

    return requestText

def getRequestType(requestText):
    start = time.time()
    # print('Entering getRequestType()')
    if requestText == '':
        # print('requestText was empty')
        return None, None, None

    # If it's an HTTP request
    requestLines = requestText.split('\n')
    firstLineSplit = requestLines[0].split()

    HttpType = firstLineSplit[0]

    requestHost = None
    requestPort = -1
    for line in requestLines:
        if line.startswith("Host: "):
            url = line.split()[1].split(':')
            requestHost = url[0]
            requestPort = int(url[1]) if len(url) > 1 else 80

    # print('Got a {} request for {}'.format(HttpType, requestHost))
    diff = time.time() - start
    if diff > 0.6: print("Request parsing took " + diff + " seconds")

    return HttpType, requestHost, requestPort

def clientToServer(client, server):
    server.settimeout(60 * 5)
    while True:
        try:
            data = client.recv(BUFF_SIZE)
            server.sendall(data)
            # if len(data.decode('ISO-8859-1')) > 1:
            #     somethingDone = True
        except BlockingIOError:
            pass
        except ConnectionResetError:
            break
        except BrokenPipeError:
            pass
        except socket.timeout:
            break

def serverToClient(server, client):
    server.settimeout(60 * 5)
    while True:
        try:
            data = server.recv(BUFF_SIZE)
            client.sendall(data)
            # if len(data.decode('ISO-8859-1')) > 1:
            #     somethingDone = True
        except BlockingIOError:
            pass
        except ConnectionResetError:
            break
        except BrokenPipeError:
            pass
        except socket.timeout:
            break

def forwardConnection(client, mmc):
    start = time.time()
    global waitingToStart, HttpsCount, HttpCount, cache, blacklist
    # print('Entered forwardRequest()')
    requestText = getRequestText(client)
    HttpType, requestHost, requestPort = getRequestType(requestText)

    # Request body was empty
    if HttpType is None:
        client.close()
        return

    if requestHost in blacklist:
        text = "[{}] {}, {}:{} (blacklisted)".format(datetime.datetime.now().time(), HttpType, requestHost, requestPort)
        mmc.updateOutput(text)
        client.close()
        return

    waitingToStartMember = "[{}] {}, {}:{}".format(datetime.datetime.now().time(), HttpType, requestHost, requestPort)

    # print(waitingToStartMember)
    mmc.updateOutput(waitingToStartMember)
    waitingToStart.append(waitingToStartMember)

    # print("Connections waiting to start: {}".format(waitingToStart))

    # print(requestText)
    serversock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversock.connect((requestHost, requestPort))
    serversock.setblocking(0)

    if HttpType == 'CONNECT':
        # print('We\'ve got a CONNECT request')
        client.sendall("HTTP/1.1 200 OK \r\n\r\n".encode('ISO-8859-1'))
    else:
        # Cache stuff
        requestId = requestText.split("\n")[0]
        if requestId in cache:
            # print("Cache hit")
            mmc.updateOutput("Cache hit")
            client.sendall(cache[requestId])
        else:
            # print("Cache miss")
            mmc.updateOutput("Cache miss")

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

    # print('Connecting to {}:{}'.format(requestHost, requestPort))

    waitingToStart.remove(waitingToStartMember)
    # print("Connection completed, remaining: {}".format(len(waitingToStart)))
    # repetitions = 0
    diff = time.time() - start
    # if diff > 0.6: print("Connection took {} seconds".format(diff))

    serverThread = Thread(target=serverToClient, args=(serversock, client,))
    serverThread.start()

    clientThread = Thread(target=clientToServer, args=(client, serversock,))
    clientThread.start()

def main(mmc):
    global HOST, PORT
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        while True:
            conn, addr = s.accept()
            conn.setblocking(0)
            request = Thread(target=forwardConnection, args=(conn, mmc, ))
            request.start()
