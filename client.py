# client_gui.py
import socket
import threading
import tkinter as tk
from tkinter import messagebox

GRID, SIZE, STONE = 15, 30, 13

class GobangClientGUI:
    def __init__(self):
        # ===== 遊戲狀態 =====
        self.started = False
        self.my_turn = False
        self.my_color = 0   # 1=黑 2=白
        self.op_color = 0

        # ===== UI =====
        self.window = tk.Tk()
        self.window.title("五子棋 CLIENT（等待中）")

        self.top = tk.Frame(self.window)
        self.top.pack(pady=5)

        self.btn_black = tk.Button(self.top, text="我要當黑棋（先手）", command=self.choose_black)
        self.btn_black.pack(side=tk.LEFT, padx=5)

        self.btn_white = tk.Button(self.top, text="我要當白棋（後手）", command=self.choose_white)
        self.btn_white.pack(side=tk.LEFT, padx=5)

        self.canvas = tk.Canvas(self.window, width=GRID*SIZE, height=GRID*SIZE, bg="#F4DAB6")
        self.canvas.pack()

        self.btn_reset = tk.Button(self.window, text="重開遊戲", command=self.reset_request)
        self.btn_reset.pack(pady=5)

        self.canvas.bind("<Button-1>", self.click)

        self.draw_board()
        self.board = [[0]*GRID for _ in range(GRID)]

        # ===== SOCKET =====
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect(("127.0.0.1", 8000))
            print("已連線至 SERVER")
        except:
            messagebox.showerror("錯誤", "無法連線到 SERVER")
            self.window.destroy()
            return

        threading.Thread(target=self.recv_loop, daemon=True).start()

    # ===============================
    # 選擇先後手
    # ===============================
    def choose_black(self):
        if self.started:
            return
        self.sock.sendall("COLOR,black\n".encode())
        self.disable_color_buttons()

    def choose_white(self):
        if self.started:
            return
        self.sock.sendall("COLOR,white\n".encode())
        self.disable_color_buttons()

    def disable_color_buttons(self):
        self.btn_black.config(state=tk.DISABLED)
        self.btn_white.config(state=tk.DISABLED)

    # ===============================
    # 畫面
    # ===============================
    def draw_board(self):
        for i in range(GRID):
            self.canvas.create_line(SIZE/2, SIZE/2+i*SIZE, SIZE/2+(GRID-1)*SIZE, SIZE/2+i*SIZE)
            self.canvas.create_line(SIZE/2+i*SIZE, SIZE/2, SIZE/2+i*SIZE, SIZE/2+(GRID-1)*SIZE)

    def draw_stone(self, x, y, color):
        px, py = SIZE/2 + x*SIZE, SIZE/2 + y*SIZE
        fill = "black" if color==1 else "white"
        self.canvas.create_oval(px-STONE, py-STONE, px+STONE, py+STONE, fill=fill)

    # ===============================
    # 點擊下棋（只送請求）
    # ===============================
    def click(self, event):
        if not self.started or not self.my_turn:
            return
        x, y = event.x//SIZE, event.y//SIZE
        if not (0 <= x < GRID and 0 <= y < GRID):
            return
        if self.board[y][x] != 0:
            return
        self.sock.sendall(f"MOVE,{x},{y}\n".encode())
        # 自己下棋時立即畫自己的棋
        self.place_stone(x, y, self.my_color)
        self.my_turn = False

    # ===============================
    def place_stone(self, x, y, color):
        self.board[y][x] = color
        self.draw_stone(x, y, color)

    # ===============================
    # RESET
    # ===============================
    def reset_request(self):
        self.sock.sendall("RESET\n".encode())

    def reset_board(self):
        self.canvas.delete("all")
        self.draw_board()
        self.board = [[0]*GRID for _ in range(GRID)]
        self.started = False
        self.my_turn = False
        self.my_color = 0
        self.op_color = 0
        self.window.title("五子棋 CLIENT（等待中）")
        self.btn_black.config(state=tk.NORMAL)
        self.btn_white.config(state=tk.NORMAL)

    # ===============================
    # 接收 server 訊息
    # ===============================
    def recv_loop(self):
        try:
            while True:
                data = self.sock.recv(1024)
                if not data:
                    messagebox.showwarning("斷線", "與 server 連線中斷")
                    break
                data = data.decode().strip()

                # --- 遊戲已滿 ---
                if data == "FULL":
                    messagebox.showinfo("遊戲已滿", "遊戲已滿，請稍後再試")
                    self.sock.close()
                    self.window.destroy()
                    break

                # --- 遊戲開始 ---
                if data.startswith("START"):
                    _, color = data.split(",")
                    self.started = True
                    if color == "black":
                        self.my_color = 1
                        self.op_color = 2
                        self.my_turn = True
                        self.window.title("五子棋 CLIENT（黑棋）")
                    else:
                        self.my_color = 2
                        self.op_color = 1
                        self.my_turn = False
                        self.window.title("五子棋 CLIENT（白棋）")

                # --- 落子 ---
                elif data.startswith("MOVE"):
                    _, x, y = data.split(",")
                    x, y = int(x), int(y)

                    if self.board[y][x] != 0:
                        continue  # 防止重複落子

                    # 畫對手棋
                    self.place_stone(x, y, self.op_color)
                    # 輪到自己下棋
                    self.my_turn = True

                # --- 勝負 ---
                elif data.startswith("WIN"):
                    _, winner = data.split(",")
                    if int(winner) == self.my_color:
                        messagebox.showinfo("結果", "🎉 你贏了！")
                    else:
                        messagebox.showinfo("結果", "😢 你輸了！")

                # --- 重置 ---
                elif data == "RESET":
                    self.reset_board()

        except:
            messagebox.showwarning("斷線", "與 server 連線中斷")
            try: self.sock.close()
            except: pass
            self.window.destroy()

    # ===============================
    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    GobangClientGUI().run()
