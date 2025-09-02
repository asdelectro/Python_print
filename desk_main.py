# Desktop версия с Tkinter и webview
# pip install webview

import webview
import threading
from main import app

def start_flask():
    app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False)

def main():
    # Запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(target=start_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Создаем desktop окно
    webview.create_window(
        title='Принтер этикеток RCDevices',
        url='http://127.0.0.1:5000',
        width=1200,
        height=800,
        min_size=(800, 600),
        resizable=True
    )
    
    webview.start(debug=False)

if __name__ == '__main__':
    main()