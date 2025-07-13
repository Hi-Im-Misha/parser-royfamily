import tkinter as tk
from tkinter import ttk, messagebox
import threading
import sys
from parser_logic import run_parser 

class TextRedirector:
    def __init__(self, widget):
        self.widget = widget

    def write(self, message):
        if message.strip():
            self.widget.config(state='normal')
            self.widget.insert("end", message)
            self.widget.see("end")
            self.widget.config(state='disabled')

    def flush(self):
        pass

class SimpleParserApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Парсер RoyFamily")
        self.root.geometry("600x400")

        ttk.Label(root, text="Ссылка на категорию:").pack(pady=5)
        self.link_entry = ttk.Entry(root, width=80)
        self.link_entry.pack(pady=5)
        self.link_entry.insert(0, "")

        self.start_button = ttk.Button(root, text="Начать", command=self.start_parsing)
        self.start_button.pack(pady=10)

        self.progress = ttk.Progressbar(root, mode="indeterminate")
        self.progress.pack(pady=5, fill="x", padx=10)

        self.log_output = tk.Text(root, height=15, state="disabled", bg="#f8f8f8")
        self.log_output.pack(padx=10, pady=10, fill="both", expand=True)

        # Перенаправляем stdout и stderr
        sys.stdout = TextRedirector(self.log_output)
        sys.stderr = TextRedirector(self.log_output)

    def start_parsing(self):
        self.start_button.config(state="disabled")
        self.progress.start()
        self.log_output.config(state='normal')
        self.log_output.delete("1.0", "end")
        self.log_output.config(state='disabled')

        url = self.link_entry.get().strip()
        thread = threading.Thread(target=self.run_parser_thread, args=(url,))
        thread.start()

    def run_parser_thread(self, url):
        try:
            run_parser(url)
            messagebox.showinfo("Готово", "Парсинг завершён успешно.")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
        finally:
            self.progress.stop()
            self.start_button.config(state="normal")

if __name__ == "__main__":
    root = tk.Tk()
    app = SimpleParserApp(root)
    root.mainloop()
