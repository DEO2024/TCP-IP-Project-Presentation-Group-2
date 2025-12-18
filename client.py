import socket              # TCP/IP 網路通訊
import threading           # 多執行緒（避免 GUI 被阻塞）
import tkinter as tk       # GUI 視窗
from tkinter import messagebox  # 彈出對話框
# 遊戲相關
GRID = 15    # 棋盤格數（15x15）
SIZE = 30    # 每一格像素大小
STONE = 13   # 棋子半徑大小
class GobangClientGUI:
    def __init__(self):
        # 遊戲狀態
        self.started = False      # 遊戲是否開始
        self.my_turn = False      # 是否輪到自己下棋
        self.my_color = 0         # 自己棋子顏色（1=黑棋, 2=白棋）
        self.op_color = 0         # 對手棋子顏色
        # 建立主視窗
        self.window = tk.Tk()
        self.window.title("五子棋 CLIENT（等待中）")
        # 上方控制區（選擇顏色）
        
        self.top = tk.Frame(self.window)
        self.top.pack(pady=5)

        # 選擇黑棋（先手）
        self.btn_black = tk.Button(
            self.top,
            text="我要當黑棋（先手）",
            command=self.choose_black
        )
        self.btn_black.pack(side=tk.LEFT, padx=5)

        # 選擇白棋（後手）
        self.btn_white = tk.Button(
            self.top,
            text="我要當白棋（後手）",
            command=self.choose_white
        )
        self.btn_white.pack(side=tk.LEFT, padx=5)


        # 棋盤畫布
        self.canvas = tk.Canvas(
            self.window,
            width=GRID * SIZE,
            height=GRID * SIZE,
            bg="#F4DAB6"
        )
        self.canvas.pack()


        # 重開遊戲按鈕
        self.btn_reset = tk.Button(
            self.window,
            text="重開遊戲",
            command=self.reset_request
        )
        self.btn_reset.pack(pady=5)

        # 滑鼠左鍵點擊
        self.canvas.bind("<Button-1>", self.click)


        # 畫棋盤格線
        self.draw_board()
        # 棋盤狀態陣列（0=空, 1=黑, 2=白）
        self.board = [[0] * GRID for _ in range(GRID)]
        # Socket 連線設定
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # 連線到 Server（IP 與 Port）
            self.sock.connect(("192.168.250.206", 8000))
            print("已連線至 SERVER")
        except:
            # 連線失敗提示
            messagebox.showerror("錯誤", "無法連線到 SERVER")
            self.window.destroy()
            return

        #    啟動接收資料的背景執行 緒
        threading.Thread(target=self.recv_loop, daemon=True).start()
 # 選擇棋子顏色（黑 / 白）
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

    # 停用顏色選擇按鈕（避免重複點擊）
    def disable_color_buttons(self):
        self.btn_black.config(state=tk.DISABLED)
        self.btn_white.config(state=tk.DISABLED)


    # 畫初棋盤格線
    def draw_board(self):
        for i in range(GRID):
            # 橫線
            self.canvas.create_line(
                SIZE / 2,
                SIZE / 2 + i * SIZE,
                SIZE / 2 + (GRID - 1) * SIZE,
                SIZE / 2 + i * SIZE
            )
            # 直線
            self.canvas.create_line(
                SIZE / 2 + i * SIZE,
                SIZE / 2,
                SIZE / 2 + i * SIZE,
                SIZE / 2 + (GRID - 1) * SIZE
            )


    # 畫初棋子

    def draw_stone(self, x, y, color):
        px = SIZE / 2 + x * SIZE
        py = SIZE / 2 + y * SIZE
        fill = "black" if color == 1 else "white"
        self.canvas.create_oval(
            px - STONE, py - STONE,
            px + STONE, py + STONE,
            fill=fill
        )
    # 滑鼠點擊下棋

    def click(self, event):
        # 遊戲未開始或不是自己回合 → 不可下棋
        if not self.started or not self.my_turn:
            return

        # 計算棋盤座標
        x = event.x // SIZE
        y = event.y // SIZE

        # 如果超出棋盤範圍
        if not (0 <= x < GRID and 0 <= y < GRID):
            return

        # 如果該位置有棋子
        if self.board[y][x] != 0:
            return

        # 傳送落子請求給 Server
        self.sock.sendall(f"MOVE,{x},{y}\n".encode())

        # 立即畫出自己的棋
        self.place_stone(x, y, self.my_color)
        self.my_turn = False

    # 放置棋子（更新陣列 + 畫圖）
    def place_stone(self, x, y, color):
        self.board[y][x] = color
        self.draw_stone(x, y, color)
# 重置遊戲（送出請求）
    def reset_request(self):
        self.sock.sendall("RESET\n".encode())
# 重置棋盤與狀態
    def reset_board(self):
        self.canvas.delete("all")
        self.draw_board()
        self.board = [[0] * GRID for _ in range(GRID)]
        self.started = False
        self.my_turn = False
        self.my_color = 0
        self.op_color = 0
        self.window.title("五子棋 CLIENT（等待中）")
        self.btn_black.config(state=tk.NORMAL)
        self.btn_white.config(state=tk.NORMAL)

    #
    # 接收 Server 訊息（背景執行緒）
   
    def recv_loop(self):
        try:
            while True:
                data = self.sock.recv(1024)
                if not data:
                    messagebox.showwarning("斷線", "與 server 連線中斷")
                    break

                data = data.decode().strip()
            # 遊戲人數超過兩人
                
                if data == "FULL":
                    messagebox.showinfo("遊戲已滿", "遊戲已滿，請稍後再試")
                    self.sock.close()
                    self.window.destroy()
                    break

                
        # 遊戲開始
               
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

              
                # 對手落子
   
                elif data.startswith("MOVE"):
                    _, x, y = data.split(",")
                    x, y = int(x), int(y)

                    # 防止重複落子
                    if self.board[y][x] != 0:
                        continue

                    self.place_stone(x, y, self.op_color)
                    self.my_turn = True

    
                # 勝負的結果
                elif data.startswith("WIN"):
                    _, winner = data.split(",")
                    if int(winner) == self.my_color:
                        messagebox.showinfo("結果", "🎉 你贏了！")
                    else:
                        messagebox.showinfo("結果", "😢 你輸了！")

         
                # 重置遊戲
           
                elif data == "RESET":
                    self.reset_board()

        except:
            messagebox.showwarning("斷線", "與 server 連線中斷")
            try:
                self.sock.close()
            except:
                pass
            self.window.destroy()
 #啟動 GUI
    def run(self):
        self.window.mainloop()


# 程式進入點
if __name__ == "__main__":
    GobangClientGUI().run()

