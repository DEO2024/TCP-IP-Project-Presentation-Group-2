# server_gui.py
import socket        
import threading      


# Server 基本
HOST = "0.0.0.0"       # 監聽所有網卡 IP
PORT = 8000            # 連線 Port
GRID = 15              # 棋盤大小（15x15）


class GobangServer:
    def __init__(self):
        
# 建立 Server Socket
     
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((HOST, PORT))
        self.sock.listen()
        print("Server 啟動，等待玩家連線...")

        
        # 遊戲狀態資料
       
        self.clients = []      # 所有連線中的 client socket
        self.colors = {}       # client socket -> 棋子顏色（1=黑, 2=白）
        self.black_taken = False   # 黑棋是否已被選走
        self.lock = threading.Lock()  # 鎖定顏色選擇（避免同時選黑）

        self.board = [[0] * GRID for _ in range(GRID)]  # 棋盤資料
        self.turn = 0          # 目前輪到誰（0=未開始, 1=黑, 2=白）

        # 啟動接收玩家連線的背景執行緒
        threading.Thread(target=self.accept_clients, daemon=True).start()

        # 主執行緒保持運作
        while True:
            pass


    #    接受玩家連線
 
    def accept_clients(self):
        while True:
            conn, addr = self.sock.accept()
            print("玩家連線：", addr)

        
            # 遊戲已滿（僅允許 2 人）
        
            if len([c for c in self.clients if c in self.colors]) >= 2:
                try:
                    conn.sendall("FULL\n".encode())
                except:
                    pass
                conn.close()
                print(f"玩家 {addr} 連線被拒，遊戲已滿")
                continue

            # 記錄 client
            self.clients.append(conn)

            # 為每位玩家開一條處理訊息的執行緒
            threading.Thread(
                target=self.handle_client,
                args=(conn,),
                daemon=True
            ).start()


    # 處理單玩家的訊息

    def handle_client(self, conn):
        addr = conn.getpeername()
        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    break

                data = data.decode().strip()

               
                # 玩家選擇棋子顏色
          
                if data.startswith("COLOR"):
                    _, color = data.split(",")

                    # 遊戲已開始則忽略
                    if self.turn != 0:
                        continue

                    # 使用 lock 確保同時間只處理一個選擇
                    with self.lock:
                        # 玩家選擇黑棋
                        if color == "black" and not self.black_taken:
                            self.colors[conn] = 1
                            self.black_taken = True
                            print(f"玩家 {addr} 選擇黑棋")

                        # 玩家選擇白棋
                        elif color == "white" and 2 not in self.colors.values():
                            self.colors[conn] = 2
                            print(f"玩家 {addr} 選擇白棋")

                
                        # 自動幫另一位玩家分配剩餘顏色
                     
                        for c in self.clients:
                            if c not in self.colors:
                                if 1 not in self.colors.values():
                                    self.colors[c] = 1
                                    self.black_taken = True
                                else:
                                    self.colors[c] = 2

                  
                        # 若黑白棋皆已分配 強制遊戲開始
                            if (
                            1 in self.colors.values() and
                            2 in self.colors.values() and
                            self.turn == 0
                        ):
                                self.start_game()

       
                # 玩家落子
                
                if data.startswith("MOVE"):
                    # 遊戲尚未開始
                    if self.turn == 0:
                        continue

                    _, x, y = data.split(",")
                    x, y = int(x), int(y)
                    color = self.colors.get(conn, 0)

                    # 不是該玩家的回合
                    if color != self.turn:
                        continue

                    # 超出棋盤
                    if not (0 <= x < GRID and 0 <= y < GRID):
                        continue

                    # 該位置已有棋子
                    if self.board[y][x] != 0:
                        continue

                    # 更新棋盤
                    self.board[y][x] = color

                    # 廣播落子給所有玩家
                    self.broadcast(f"MOVE,{x},{y}")

       
                    # 勝負的判斷
               
                    if self.check_win(color):
                        self.broadcast(f"WIN,{color}")
                        self.reset()
                        continue

                    # 換另一方下棋
                    self.turn = 2 if self.turn == 1 else 1


                # 玩家請求重置遊戲
    
                if data == "RESET":
                    self.broadcast("RESET")
                    self.reset()

        except ConnectionResetError:
            pass
        finally:
            print(f"玩家 {addr} 斷線")
            self.remove_client(conn)


    # 移除斷線玩家



    
    def remove_client(self, conn):
        if conn in self.clients:
            self.clients.remove(conn)
        if conn in self.colors:
            del self.colors[conn]

        # 若遊戲進行中有人斷線 → 重置
        if self.turn != 0:
            self.broadcast("RESET")
            self.reset()

        try:
            conn.close()
        except:
            pass
    # 開始遊戲（黑棋先手）

    def start_game(self):
        self.turn = 1
        print("遊戲開始，黑棋先手")

        for c in self.clients:
            color = self.colors.get(c, 0)
            if color == 1:
                c.sendall("START,black\n".encode())
            elif color == 2:
                c.sendall("START,white\n".encode())


    # 用於重置遊戲狀態
    def reset(self):
        print("遊戲重置，回到等待狀態")
        self.board = [[0] * GRID for _ in range(GRID)]
        self.turn = 0
        self.black_taken = False
        self.colors.clear()
# 廣播訊息給所有玩家
    def broadcast(self, msg):
        for c in self.clients:
            try:
                c.sendall((msg + "\n").encode())
            except:
                pass

  
    # 勝負判斷（五子連線）
    def check_win(self, c):
        # 四個方向：橫、直、右下斜、右上斜
        dirs = [(1, 0), (0, 1), (1, 1), (1, -1)]

        for y in range(GRID):
            for x in range(GRID):
                if self.board[y][x] != c:
                    continue

                for dx, dy in dirs:
                    cnt = 1
                    for k in range(1, 5):
                        nx = x + dx * k
                        ny = y + dy * k
                        if (
                            0 <= nx < GRID and
                            0 <= ny < GRID and
                            self.board[ny][nx] == c
                        ):
                            cnt += 1
                        else:
                            break

                    if cnt >= 5:
                        return True
        return False


# 程式進入點
if __name__ == "__main__":
    GobangServer()
