import socket

HOST = ''
PORT = 4000
BUFF_SIZE = 4096

def getRequestText(conn, sendback=False):
    print('Entering getRequestText()')
    requestText = ""
    while True:
        data = conn.recv(BUFF_SIZE)
        if not data: break
        if sendback:
            conn.sendall(data)
        try:
            requestText += data.decode('ISO-8859-1')
        except Exception as e:
            print(e)
        print("Got some data:\n\n{}".format(data.decode('ISO-8859-1')))

    print('Got a (hopefully) http request:\n{}'.format(requestText))
    return requestText

def getRequestType(requestText):
    print('Entering getRequestType()')
    if requestText == '':
        print('requestText was empty')
        return 'other', 'localhost'

    # If it's an HTTP request
    requestLines = requestText.split('\n')
    firstLineSplit = requestLines[0].split()

    HttpType = firstLineSplit[0]

    requestHost = ""
    requestPort = 0
    for line in requestLines:
        if line.startswith("Host: "):
            url = line.split()[1].split(':')
            requestHost = url[0]
            if requestHost.startswith("www."):
                requestHost = requestHost[4:]
            requestPort = int(url[1]) if len(url) > 1 else 80

    print('Got a {} request for {}'.format(HttpType, requestHost))
    return HttpType, requestHost, requestPort

def forwardRequest(client):
    print('Entered forwardRequest()')
    requestText = getRequestText(client)#, sendback=True)
    HttpType, requestHost, requestPort = getRequestType(requestText)
    print(HttpType + ', ' + requestHost)

    # print(requestText)
    serversock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversock.settimeout(5)

    if HttpType == 'CONNECT':
        print('We\'ve got a CONNECT request')
        client.sendall("HTTP/1.1 200 OK \r\n".encode())

    serversock.connect((requestHost, requestPort))
        
    print('Connecting to {}:{}'.format(requestHost, requestPort))
    serversock.sendall(requestText.encode())

    print("Starting response receival loop")
    response = ''
    while True:
        data = serversock.recv(BUFF_SIZE)
        if not data:
            print("{}, {}, {}".format(requestHost, requestPort, serversock))
            print('Response has ended')
            break
        else:
            try:
                response += data.decode('ISO-8859-1')
            except e:
                print(e)
            client.sendall(data)

    print('Response: ' + response)
    serversock.close()
    conn.close()

if __name__ == "__main__":
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        conn, addr = s.accept()
        with conn:
            forwardRequest(conn)
