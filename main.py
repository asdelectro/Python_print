# Flask server with simplified print_labels
# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, jsonify
from print_labels import LabelPrinter  # Используем упрощенную версию
from hardware import RCDevicesClient
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import os
from datetime import datetime
import toml
import sys
import argparse
import time

app = Flask(__name__)

INVENTREE_URL = "https://192.168.88.132"
INVENTREE_TOKEN = "inv-3d1c37e2156c24a5af7e384099de32dfd12e522d-20251015"
INVENTREE_HEADERS = {
    "Authorization": f"Token {INVENTREE_TOKEN}",
    "Content-Type": "application/json",
}


# Configuration settings
class Config:
    DEVICE_VALIDATION_ENABLED = True
    REQUIRE_TESTS_OK = True
    REQUIRE_CALIBRATION_OK = True
    REQUIRE_PROG_TIME = True
    REQUIRE_CALIB_TIME = True
    PHYSICAL_PRINT_ENABLED = True
    WEBHOOK_API_BASE = "http://192.168.88.132:9000"
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
        # First check if any devices are actually connected
        device_count = rc_client.get_device_count()

        if device_count == 0:
            response_data = {
                "success": False,
                "message": "No devices connected",
                "device_count": 0,
            }
        elif device_count > 1:
            response_data = {
                "success": False,
                "message": f"Multiple devices connected ({device_count}). Only single device supported.",
                "device_count": device_count,
            }
        else:
            # Exactly one device - get its data
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

            response_data = {
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
                "device_count": 1,
            }

        # Create response with no-cache headers for webview
        response = jsonify(response_data)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

        return response

    except Exception as e:
        response_data = {"success": False, "message": str(e), "device_count": 0}
        response = jsonify(response_data)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


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

        # Запрашиваем список недавних устройств
        response = requests.post(
            f"{config.WEBHOOK_API_BASE}/hooks/get-devices",
            json={
                "path": "/api/devices",
                "limit": 10,  # Увеличиваем лимит для поиска
                "minutes": 1,  # Ищем за последний час
            },
            timeout=config.WEBHOOK_TIMEOUT,
        )

        if response.status_code == 200:
            result = response.json()

            if result.get("success"):
                devices = result.get("devices", [])

                # Ищем устройство с нужным серийным номером
                found_device = None
                for device in devices:
                    if (
                        device.get("barcode") == barcode
                        or device.get("serial") == barcode
                    ):
                        found_device = device
                        break

                if found_device:
                    # Устройство найдено!
                    return jsonify(
                        {
                            "success": True,
                            "scanned": True,
                            "status": found_device.get("status", "ready"),
                            "manufacturing_date": found_device.get(
                                "manufacturing_date"
                            ),
                            "sale_date": found_device.get("sale_date"),
                            "age_minutes": found_device.get("age_minutes", 0),
                            "scanner_id": found_device.get("scanner_id", "unknown"),
                            "message": f"Устройство {found_device.get('status', 'ready')} (возраст: {found_device.get('age_minutes', 0)} минут)",
                        }
                    )
                else:
                    # Устройство не найдено в списке
                    return jsonify(
                        {
                            "success": True,
                            "scanned": False,
                            "message": "Устройство не найдено в недавно отсканированных",
                        }
                    )
            else:
                return jsonify(
                    {
                        "success": False,
                        "message": result.get("message", "Ошибка получения данных"),
                    }
                )
        else:
            return jsonify(
                {"success": False, "message": f"Ошибка API: {response.status_code}"}
            )

    except requests.exceptions.Timeout:
        return jsonify({"success": False, "message": "Timeout запроса"})
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "message": f"Ошибка соединения: {str(e)}"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Ошибка: {str(e)}"})


@app.route("/get_scanned_items")
def get_scanned_items():
    try:
        limit = request.args.get("limit", 100, type=int)
        minutes = request.args.get("minutes", 600, type=int)

        response = requests.post(
            f"{config.WEBHOOK_API_BASE}/hooks/get-devices",
            json={"path": "/api/devices", "limit": limit, "minutes": minutes},
            timeout=config.WEBHOOK_TIMEOUT,
        )

        if response.status_code == 200:
            result = response.json()
            devices = result.get("devices", [])
            formatted_items = []

            for device in devices:
                formatted_items.append(
                    {
                        "barcode": device.get("barcode", "Unknown"),
                        "status": device.get("status", "unknown"),
                        "timestamp": device.get("manufacturing_date"),  # ISO formart
                        "scanner_id": device.get("scanner_id", "manufacturing"),
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


# Print comand line
import time


def inventree_delete_if_exists(serial: str) -> bool:
    try:
        response = requests.get(
            f"{INVENTREE_URL}/api/stock/",
            params={"serial": serial, "limit": 1},
            headers=INVENTREE_HEADERS,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        if not data.get("results"):
            print(f"ℹ️  InvenTree: {serial} не найден")
            return True  # всё ок, просто нечего удалять

        pk = data["results"][0]["pk"]
        print(f"🔍 InvenTree: найден ID={pk}, удаляем...")
        requests.delete(
            f"{INVENTREE_URL}/api/stock/{pk}/",
            headers=INVENTREE_HEADERS,
            timeout=10,
            verify=False,
        ).raise_for_status()
        print(f"🗑️  InvenTree: {serial} удалён")
        return True

    except Exception as e:
        print(f"⚠️  InvenTree ошибка: {e}")
        return True  # не блокируем печать даже при ошибке


def cli_print_serial(serial: str):
    print(f"🖨️ CLI-печать серийника: {serial}")
    inventree_delete_if_exists(
        serial
    )  # Для возвратов с таможни.Если такой серийник есть удалим.
    success = printer.create_and_print_label(
        serial_number=serial,
        template_pdf="template51x25.pdf",
        add_datamatrix=True,
        print_after_create=True,
    )

    if success:
        print("⏳ Ожидание завершения отправки в печать...")

        print("✅ Этикетка отправлена в принтер")
        sys.exit(0)
    else:
        print("❌ Ошибка печати этикетки")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Label Printer")
    parser.add_argument(
        "-s",
        "--serial",
        help="Серийный номер для печати (CLI режим)",
        type=str,
    )

    args = parser.parse_args()

    # --- CLI MODE ---
    if args.serial:
        cli_print_serial(args.serial)

    # --- WEB MODE ---
    print("🚀 Запуск веб-сервера принтера этикеток...")
    print("📍 Адрес: http://localhost:5000")
    print(f"🔧 Проверки: {'ВКЛ' if config.DEVICE_VALIDATION_ENABLED else 'ВЫКЛ'}")
    print(f"🖨️ Печать: {'ВКЛ' if config.PHYSICAL_PRINT_ENABLED else 'ВЫКЛ'}")
    print("⏹️  Ctrl+C для остановки")

    app.run(debug=True, host="0.0.0.0", port=5000, threaded=False)
