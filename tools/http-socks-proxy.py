"""超简单 HTTP→SOCKS5 代理（threading 版本）"""
import socket, threading, struct

SOCKS_HOST, SOCKS_PORT = '127.0.0.1', 10808
HTTP_HOST, HTTP_PORT = '127.0.0.1', 10809

def handle(client):
    try:
        # 读 CONNECT 请求的第一行
        data = b''
        while b'\r\n\r\n' not in data:
            data += client.recv(4096)
        first_line = data.split(b'\r\n')[0].decode()
        method, target, _ = first_line.split()
        if method != 'CONNECT':
            client.close(); return
        host, port = target.split(':')
        port = int(port)

        # SOCKS5 连接
        remote = socket.socket()
        remote.settimeout(10)
        remote.connect((SOCKS_HOST, SOCKS_PORT))
        # 握手
        remote.sendall(b'\x05\x01\x00')
        remote.recv(2)
        # CONNECT
        host_b = host.encode()
        req = b'\x05\x01\x00\x03' + bytes([len(host_b)]) + host_b + struct.pack('>H', port)
        remote.sendall(req)
        resp = remote.recv(10)
        if resp[1] != 0:
            client.close(); remote.close(); return

        client.sendall(b'HTTP/1.1 200 Connection Established\r\n\r\n')

        # 双向转发
        remote.settimeout(60)
        client.settimeout(60)
        def pipe(a, b):
            try:
                while True:
                    d = a.recv(8192)
                    if not d: break
                    b.sendall(d)
            except: pass
        t1 = threading.Thread(target=pipe, args=(client, remote), daemon=True)
        t2 = threading.Thread(target=pipe, args=(remote, client), daemon=True)
        t1.start(); t2.start()
        t1.join(); t2.join()
    except Exception as e:
        pass
    finally:
        try: client.close()
        except: pass
        try: remote.close()
        except: pass

server = socket.socket()
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HTTP_HOST, HTTP_PORT))
server.listen(50)
print(f'代理已启动: HTTP {HTTP_HOST}:{HTTP_PORT} → SOCKS5 {SOCKS_HOST}:{SOCKS_PORT}')
while True:
    client, _ = server.accept()
    threading.Thread(target=handle, args=(client,), daemon=True).start()
