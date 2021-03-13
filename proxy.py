import socket
import time
from threading import Thread

HOST = ''
PORT = 4000
BUFF_SIZE = 65536
waitingToStart = []

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
    if diff > 0.6: print("Request collection took " + diff + " seconds")

    return requestText

def getRequestType(requestText):
    start = time.time()
    # print('Entering getRequestType()')
    if requestText == '':
        # print('requestText was empty')
        return None

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

def forwardConnection(client):
    start = time.time()
    global waitingToStart
    # print("Connections waiting to start: {}".format(waitingToStart))
    # print('Entered forwardRequest()')
    requestText = getRequestText(client)
    HttpType, requestHost, requestPort = getRequestType(requestText)
    waitingToStartMember = HttpType + ', ' + requestHost + ', ' + str(requestPort)
    print(waitingToStartMember)
    waitingToStart.append(waitingToStartMember)

    # print(requestText)
    serversock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    if HttpType == 'CONNECT':
        # print('We\'ve got a CONNECT request')
        client.sendall("HTTP/1.1 200 OK \r\n\r\n".encode('ISO-8859-1'))

    serversock.connect((requestHost, requestPort))
    serversock.setblocking(0)

    # print('Connecting to {}:{}'.format(requestHost, requestPort))

    waitingToStart.remove(waitingToStartMember)
    # print("Connection completed, remaining: {}".format(len(waitingToStart)))
    # repetitions = 0
    diff = time.time() - start
    if diff > 0.6: print("Connection took " + diff + " seconds")
    while True:
        somethingDone = False
        try:
            data = client.recv(BUFF_SIZE)
            serversock.sendall(data)
            # if len(data.decode('ISO-8859-1')) > 1:
            #     somethingDone = True
        except BlockingIOError:
            pass
        except ConnectionResetError:
            break
        except BrokenPipeError:
            break

        try:
            data = serversock.recv(BUFF_SIZE)
            client.sendall(data)
            # if len(data.decode('ISO-8859-1')) > 1:
            #     somethingDone = True
        except BlockingIOError:
            pass
        except ConnectionResetError:
            break
        except BrokenPipeError:
            break

        # if somethingDone:
        #     repetitions += 1
        #     print("Connection repetitions: {}".format(repetitions))

    serversock.close()
    client.close()

if __name__ == "__main__":
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        while True:
            conn, addr = s.accept()
            conn.setblocking(0)
            request = Thread(target=forwardConnection, args=(conn, ))
            request.start()
