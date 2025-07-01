import socket
import threading
import json
import os
import re

# Constants
LOCK = threading.Lock()
DATA_FILE = 'data.json'
SERVER_PORT = 1234

# Utility functions
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, 'r') as file:
        return json.load(file)

def save_data(data):
    with LOCK:
        with open(DATA_FILE, 'w') as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

# Command handlers
def handle_join(client_ip, data, client_socket):
    if client_ip not in data:
        data[client_ip] = []
        save_data(data)
        client_socket.sendall(b"CONFIRMJOIN")
    else:
        client_socket.sendall(b"CLIENTALREADYCONNECTED")

def handle_create_file(client_ip, data, client_socket, filename, size):
    if any(f['filename'] == filename for f in data.get(client_ip, [])):
        client_socket.sendall(b"FILEALREADYEXISTS")
    else:
        data[client_ip].append({"filename": filename, "size": size})
        save_data(data)
        client_socket.sendall(f"CONFIRMCREATEFILE {filename}".encode())

def handle_delete_file(client_ip, data, client_socket, filename):
    if any(f['filename'] == filename for f in data.get(client_ip, [])):
        data[client_ip] = [f for f in data[client_ip] if f['filename'] != filename]
        save_data(data)
        client_socket.sendall(f"CONFIRMDELETEFILE {filename}".encode())
    else:
        client_socket.sendall(b"FILENOTFOUND")

def handle_search(data, client_socket, filename_pattern):
    try:
        regex = re.compile(filename_pattern)
        results = [
            f"FILE {f['filename']} {ip} {f['size']}" 
            for ip, files in data.items()
            for f in files if regex.search(f['filename'])
        ]
        if results:
            client_socket.sendall("\n".join(results).encode())
        else:
            client_socket.sendall(b"FILENOTFOUND")
    except re.error:
        client_socket.sendall(b"INVALIDREGEX")

def handle_leave(client_ip, data, client_socket):
    if client_ip in data:
        del data[client_ip]
        save_data(data)
        client_socket.sendall(b"CONFIRMLEAVE")

def handle_list_files(data, client_socket):
    results = [
        f"FILE {f['filename']} {ip} {f['size']}" 
        for ip, files in data.items()
        for f in files
    ]
    if results:
        client_socket.sendall("\n".join(results).encode())
    else:
        client_socket.sendall(b"ANYFILE")

# Client handler
def handle_client(client_socket, client_address, data):
    client_ip = client_address[0]
    while True:
        try:
            message = client_socket.recv(1024).decode()
            if not message:
                break

            print(f"[LOG] {client_ip} sent: {message}")
            command, *args = message.split()

            if command == 'JOIN':
                handle_join(client_ip, data, client_socket)
            elif command == 'CREATEFILE':
                filename, size = args
                handle_create_file(client_ip, data, client_socket, filename, int(size))
            elif command == 'DELETEFILE':
                handle_delete_file(client_ip, data, client_socket, args[0])
            elif command == 'SEARCH':
                handle_search(data, client_socket, args[0])
            elif command == 'LEAVE':
                handle_leave(client_ip, data, client_socket)
            elif command == 'LISTFILES':
                handle_list_files(data, client_socket)
        except Exception as e:
            print(f"[ERROR] {client_ip}: {e}")
            break

    client_socket.close()

# Main server function
def main():
    data = load_data()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("", SERVER_PORT))
    server_socket.listen(5)
    print(f"[SERVER] Listening on port {SERVER_PORT}")

    try:
        while True:
            client_socket, client_address = server_socket.accept()
            print(f"[CONNECTION] {client_address} connected.")
            threading.Thread(target=handle_client, args=(client_socket, client_address, data)).start()
    except KeyboardInterrupt:
        print("[SERVER] Shutting down.")
    finally:
        server_socket.close()

if __name__ == "__main__":
    main()