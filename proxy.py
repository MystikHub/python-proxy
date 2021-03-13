import socket

HOST = '127.0.0.1'
PORT = 4000

def getRequestType(connection):
    requestString = ''
    while True:
        try:
            data = conn.recv(1024)
            if not data:
                break
            conn.sendall(data)
            requestString += data.decode()
        except:
            # Not an HTTP request
            return 'other'

    splitString = requestString.split()
    
    return 'HTTP ' + splitString[0]

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    conn, addr = s.accept()
    with conn:
        # print('Connected by', addr)
        # print(conn)
        print(getRequestType(conn))
        conn.close()
