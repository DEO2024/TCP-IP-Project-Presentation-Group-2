# server_gui.py
import socket
import threading

HOST = "0.0.0.0"
PORT = 8000
GRID = 15

class GobangServer:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((HOST, PORT))
        self.sock.listen()
        print("Server 啟動，等待玩家連線...")

        self.clients = []      # 目前連線的 client
        self.colors = {}       # conn -> 1(黑) / 2(白)
        self.black_taken = False
        self.lock = threading.Lock()  # 保護顏色選擇流程

        self.board = [[0] * GRID for _ in range(GRID)]
        self.turn = 0          # 0=尚未開始, 1=黑, 2=白

        threading.Thread(target=self.accept_clients, daemon=True).start()
        while True:
            pass

    # ===============================
    def accept_clients(self):
        while True:
            conn, addr = self.sock.accept()
            print("玩家連線：", addr)

            # 遊戲已滿，拒絕第三位以上
            if len([c for c in self.clients if c in self.colors]) >= 2:
                try:
                    conn.sendall("FULL\n".encode())
                except:
                    pass
                conn.close()
                print(f"玩家 {addr} 連線被拒，遊戲已滿")
                continue

            self.clients.append(conn)
            threading.Thread(
                target=self.handle_client,
                args=(conn,),
                daemon=True
            ).start()

    # ===============================
    def handle_client(self, conn):
        addr = conn.getpeername()
        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                data = data.decode().strip()

                # ---------- 選顏色 ----------
                if data.startswith("COLOR"):
                    _, color = data.split(",")

                    if self.turn != 0:
                        continue  # 遊戲已開始不能再選

                    with self.lock:
                        # 當前 client 選黑棋
                        if color == "black" and not self.black_taken:
                            self.colors[conn] = 1
                            self.black_taken = True
                            print(f"玩家 {addr} 選擇黑棋")
                        # 當前 client 選白棋
                        elif color == "white" and 2 not in self.colors.values():
                            self.colors[conn] = 2
                            print(f"玩家 {addr} 選擇白棋")

                        # 自動分配另一位剩餘顏色
                        for c in self.clients:
                            if c not in self.colors:
                                if 1 not in self.colors.values():
                                    self.colors[c] = 1
                                    self.black_taken = True
                                else:
                                    self.colors[c] = 2

                        # 如果兩色都分配完成且遊戲尚未開始 → 立即開始
                        if 1 in self.colors.values() and 2 in self.colors.values() and self.turn == 0:
                            self.start_game()

                # ---------- 落子 ----------
                if data.startswith("MOVE"):
                    if self.turn == 0:
                        continue

                    _, x, y = data.split(",")
                    x, y = int(x), int(y)
                    color = self.colors.get(conn, 0)

                    if color != self.turn:
                        continue
                    if not (0 <= x < GRID and 0 <= y < GRID):
                        continue
                    if self.board[y][x] != 0:
                        continue

                    self.board[y][x] = color
                    self.broadcast(f"MOVE,{x},{y}")

                    if self.check_win(color):
                        self.broadcast(f"WIN,{color}")
                        self.reset()
                        continue

                    self.turn = 2 if self.turn == 1 else 1

                # ---------- 重開 ----------
                if data == "RESET":
                    self.broadcast("RESET")
                    self.reset()

        except ConnectionResetError:
            pass
        finally:
            print(f"玩家 {addr} 斷線")
            self.remove_client(conn)

    # ===============================
    def remove_client(self, conn):
        if conn in self.clients:
            self.clients.remove(conn)
        if conn in self.colors:
            del self.colors[conn]
        if self.turn != 0:
            self.broadcast("RESET")
            self.reset()
        try:
            conn.close()
        except:
            pass

    # ===============================
    def start_game(self):
        self.turn = 1  # 黑棋先手
        print("遊戲開始，黑棋先手")
        for c in self.clients:
            color = self.colors.get(c, 0)
            if color == 1:
                c.sendall("START,black\n".encode())
            elif color == 2:
                c.sendall("START,white\n".encode())

    # ===============================
    def reset(self):
        print("遊戲重置，回到等待狀態")
        self.board = [[0] * GRID for _ in range(GRID)]
        self.turn = 0
        self.black_taken = False
        self.colors.clear()

    # ===============================
    def broadcast(self, msg):
        for c in self.clients:
            try:
                c.sendall((msg + "\n").encode())
            except:
                pass

    # ===============================
    def check_win(self, c):
        dirs = [(1,0),(0,1),(1,1),(1,-1)]
        for y in range(GRID):
            for x in range(GRID):
                if self.board[y][x] != c:
                    continue
                for dx, dy in dirs:
                    cnt = 1
                    for k in range(1,5):
                        nx, ny = x + dx*k, y + dy*k
                        if 0 <= nx < GRID and 0 <= ny < GRID and self.board[ny][nx]==c:
                            cnt += 1
                        else:
                            break
                    if cnt >= 5:
                        return True
        return False

if __name__ == "__main__":
    GobangServer()
