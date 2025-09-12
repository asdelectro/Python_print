# Desktop версия с webview - улучшенная
import webview
import threading
import time
from main import app


def start_flask():
    # Даем время webview на запуск
    time.sleep(1)
    app.run(debug=False, host="127.0.0.1", port=5000, use_reloader=False, threaded=True)


def main():
    # Запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(target=start_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Даем Flask время запуститься
    time.sleep(2)

    # Создаем desktop окно с отключенным кэшированием
    webview.create_window(
        title="Принтер этикеток RCDevices",
        url="http://127.0.0.1:5000",
        width=1200,
        height=800,
        min_size=(800, 600),
        resizable=True,
        # Отключаем кэширование для WebView
        js_api=None,  # Можно добавить JS API если нужно
    )

    # Запускаем с отключенной отладкой для стабильности
    webview.start(
        debug=False,
        # Принудительно используем нативный движок
        gui="cef" if hasattr(webview, "CEF") else None,
    )


if __name__ == "__main__":
    main()
