# Flask server with simplified print_labels
# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, jsonify
from print_labels import LabelPrinter  # Используем упрощенную версию
from hardware import RCDevicesClient
import requests
import os
from datetime import datetime
import toml

app = Flask(__name__)


# Configuration settings
class Config:
    DEVICE_VALIDATION_ENABLED = True
    REQUIRE_TESTS_OK = True
    REQUIRE_CALIBRATION_OK = True
    REQUIRE_PROG_TIME = True
    REQUIRE_CALIB_TIME = True
    PHYSICAL_PRINT_ENABLED = True
    WEBHOOK_API_BASE = "http://192.168.88.132:3000/api"
    WEBHOOK_TIMEOUT = 5


config = Config()

# Create instances
printer = LabelPrinter()
rc_client = RCDevicesClient()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/toggle_validation", methods=["POST"])
def toggle_validation():
    try:
        config.DEVICE_VALIDATION_ENABLED = not config.DEVICE_VALIDATION_ENABLED
        return jsonify(
            {
                "success": True,
                "validation_enabled": config.DEVICE_VALIDATION_ENABLED,
                "message": f'Проверки устройства {"включены" if config.DEVICE_VALIDATION_ENABLED else "отключены"}',
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": f"Ошибка: {str(e)}"})


@app.route("/toggle_print", methods=["POST"])
def toggle_print():
    try:
        config.PHYSICAL_PRINT_ENABLED = not config.PHYSICAL_PRINT_ENABLED
        return jsonify(
            {
                "success": True,
                "print_enabled": config.PHYSICAL_PRINT_ENABLED,
                "message": f'Печать {"включена" if config.PHYSICAL_PRINT_ENABLED else "отключена"}',
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": f"Ошибка: {str(e)}"})


@app.route("/get_config_status")
def get_config_status():
    return jsonify(
        {
            "success": True,
            "validation_enabled": config.DEVICE_VALIDATION_ENABLED,
            "print_enabled": config.PHYSICAL_PRINT_ENABLED,
        }
    )


@app.route("/device_status")
def device_status():
    try:
        device = rc_client.get_single_device()
        handle = device["handle"]
        mcu_id = device["mcu_id"]
        serial = device["serial"]
        db_info = device["db_info"]

        mcu_str = " ".join(f"{b:02X}" for b in mcu_id) if mcu_id else "Error"

        tests_ok = db_info.get("tests_ok", 0) == 1
        calibration_ok = db_info.get("calibration_ok", 0) == 1
        prog_time_ok = db_info.get("prog_time", 0) > 0
        calib_time_ok = db_info.get("calib_time", 0) > 0

        if config.DEVICE_VALIDATION_ENABLED:
            device_ready = (
                tests_ok and calibration_ok and prog_time_ok and calib_time_ok
            )
        else:
            device_ready = tests_ok

        status = "READY" if device_ready else "NOT READY"

        return jsonify(
            {
                "success": True,
                "handle": f"{handle:X}",
                "mcu_id": mcu_str,
                "serial": serial if serial else "Error",
                "tests_ok": db_info.get("tests_ok", 0),
                "calibration_ok": db_info.get("calibration_ok", 0),
                "prog_time": db_info.get("prog_time", 0),
                "calib_time": db_info.get("calib_time", 0),
                "status": status,
                "device_ready": device_ready,
                "validation_enabled": config.DEVICE_VALIDATION_ENABLED,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route("/get_device_info")
def get_device_info():
    try:
        device = rc_client.get_single_device()
        serial = device["serial"]

        if not serial:
            return jsonify(
                {"success": False, "message": "Не удалось получить серийный номер"}
            )

        return jsonify({"success": True, "serial": serial})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route("/print_label", methods=["POST"])
def print_label():
    try:
        data = request.get_json()
        serial_number = data.get("serial_number", "").strip()

        if not serial_number:
            return jsonify(
                {"success": False, "message": "Серийный номер не может быть пустым"}
            )

        # Проверяем готовность устройства
        device_status_response = device_status()
        device_data = device_status_response.get_json()

        # Создаем и печатаем этикетку
        success = printer.create_and_print_label(
            serial_number=serial_number,
            template_pdf="template51x25.pdf",
            add_datamatrix=True,
            print_after_create=config.PHYSICAL_PRINT_ENABLED,
        )

        if success:
            message = f'Этикетка "{serial_number}" '
            if config.PHYSICAL_PRINT_ENABLED:
                message += "создана и напечатана!"
            else:
                message += "создана (печать симулирована)!"

            return jsonify({"success": True, "message": message})
        else:
            return jsonify(
                {"success": False, "message": "Ошибка при создании этикетки"}
            )

    except Exception as e:
        return jsonify({"success": False, "message": f"Ошибка: {str(e)}"})


@app.route("/check_scan_status", methods=["POST"])
def check_scan_status():
    try:
        data = request.get_json()
        barcode = data.get("barcode", "").strip()

        if not barcode:
            return jsonify({"success": False, "message": "Штрихкод пустой"})

        response = requests.get(
            f"{config.WEBHOOK_API_BASE}/devices",
            params={"limit": 100},
            timeout=config.WEBHOOK_TIMEOUT,
        )

        if response.status_code == 200:
            devices_data = response.json()
            devices = devices_data.get("devices", [])

            for device in devices:
                if device.get("barcode") == barcode:
                    return jsonify(
                        {
                            "success": True,
                            "scanned": True,
                            "status": device.get("status", "unknown"),
                            "timestamp": device.get("scan_timestamp"),
                        }
                    )

            return jsonify(
                {
                    "success": True,
                    "scanned": False,
                    "message": "Штрихкод еще не отсканирован",
                }
            )
        else:
            return jsonify(
                {"success": False, "message": "Ошибка получения данных сканирования"}
            )

    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "message": f"Ошибка соединения: {str(e)}"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Ошибка: {str(e)}"})


@app.route("/get_scanned_items")
def get_scanned_items():
    try:
        response = requests.get(
            f"{config.WEBHOOK_API_BASE}/devices",
            params={"limit": 10},
            timeout=config.WEBHOOK_TIMEOUT,
        )

        if response.status_code == 200:
            devices_data = response.json()
            devices = devices_data.get("devices", [])

            formatted_items = []
            for device in devices:
                try:
                    scan_time = datetime.fromisoformat(device.get("scan_timestamp", ""))
                    formatted_time = scan_time.strftime("%d.%m.%Y %H:%M")
                except:
                    formatted_time = device.get("scan_timestamp", "Unknown")

                formatted_items.append(
                    {
                        "barcode": device.get("barcode", "Unknown"),
                        "status": device.get("status", "unknown"),
                        "timestamp": formatted_time,
                        "scanner_id": device.get("scanner_id", "unknown"),
                    }
                )

            return jsonify({"success": True, "items": formatted_items})
        else:
            return jsonify({"success": False, "message": "Ошибка API", "items": []})

    except requests.exceptions.RequestException as e:
        return jsonify(
            {"success": False, "message": f"Ошибка соединения: {str(e)}", "items": []}
        )
    except Exception as e:
        return jsonify({"success": False, "message": f"Ошибка: {str(e)}", "items": []})


if __name__ == "__main__":
    print("🚀 Запуск веб-сервера принтера этикеток...")
    print("📍 Адрес: http://localhost:5000")
    print(f"🔧 Проверки: {'ВКЛ' if config.DEVICE_VALIDATION_ENABLED else 'ВЫКЛ'}")
    print(f"🖨️ Печать: {'ВКЛ' if config.PHYSICAL_PRINT_ENABLED else 'ВЫКЛ'}")
    print("⏹️  Ctrl+C для остановки")

    app.run(debug=True, host="0.0.0.0", port=5000, threaded=False)
