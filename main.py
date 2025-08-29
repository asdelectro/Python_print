# Flask server with RCDevices integration and barcode scanning
# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, jsonify
from print_labels import LabelPrinter
from hardware import RCDevicesClient  # Import class from hardware.py
import requests
import os
from datetime import datetime

app = Flask(__name__)

# Configuration settings
class Config:
    # Device validation settings
    DEVICE_VALIDATION_ENABLED = True  # Set to False to bypass device checks for testing
    REQUIRE_TESTS_OK = True           # Require tests_ok = 1
    REQUIRE_CALIBRATION_OK = True     # Require calibration_ok = 1  
    REQUIRE_PROG_TIME = True          # Require prog_time > 0
    REQUIRE_CALIB_TIME = True         # Require calib_time > 0
    
    # Print settings
    PHYSICAL_PRINT_ENABLED = True     # Set to False to simulate printing without actual print
    
    # Webhook API settings
    WEBHOOK_API_BASE = "http://192.168.88.132:3000/api"
    WEBHOOK_TIMEOUT = 5  # seconds

config = Config()

# HTML template with device info section and scanning functionality

# Create instances
printer = LabelPrinter(enable_logging=False, temp_filename="web_label.pdf")
rc_client = RCDevicesClient()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/toggle_validation', methods=['POST'])
def toggle_validation():
    """Toggle device validation on/off"""
    try:
        config.DEVICE_VALIDATION_ENABLED = not config.DEVICE_VALIDATION_ENABLED
        
        return jsonify({
            'success': True,
            'validation_enabled': config.DEVICE_VALIDATION_ENABLED,
            'message': f'Проверки устройства {"включены" if config.DEVICE_VALIDATION_ENABLED else "отключены"}'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Ошибка переключения режима: {str(e)}'
        })

@app.route('/toggle_print', methods=['POST'])
def toggle_print():
    """Toggle physical printing on/off"""
    try:
        config.PHYSICAL_PRINT_ENABLED = not config.PHYSICAL_PRINT_ENABLED
        
        return jsonify({
            'success': True,
            'print_enabled': config.PHYSICAL_PRINT_ENABLED,
            'message': f'Физическая печать {"включена" if config.PHYSICAL_PRINT_ENABLED else "отключена (симуляция)"}'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Ошибка переключения печати: {str(e)}'
        })

@app.route('/get_config_status')
def get_config_status():
    """Get current configuration status"""
    return jsonify({
        'success': True,
        'validation_enabled': config.DEVICE_VALIDATION_ENABLED,
        'print_enabled': config.PHYSICAL_PRINT_ENABLED
    })

@app.route('/get_validation_status')
def get_validation_status():
    """Get current validation status (legacy endpoint)"""
    return jsonify({
        'success': True,
        'validation_enabled': config.DEVICE_VALIDATION_ENABLED
    })

@app.route('/device_status')
def device_status():
    """Get device status"""
    try:
        device = rc_client.get_single_device()
         # 
        print(f"DEBUG: Raw device data: {device}")
        print(f"DEBUG: db_info: {device.get('db_info', {})}")
        print(f"DEBUG: tests_ok value: {device['db_info'].get('tests_ok')} (type: {type(device['db_info'].get('tests_ok'))})")
        
        handle = device["handle"]
        mcu_id = device["mcu_id"]
        serial = device["serial"]
        db_info = device["db_info"]
      
        
        mcu_str = ' '.join(f'{b:02X}' for b in mcu_id) if mcu_id else 'Error'
        
        # Use same validation logic as frontend
        tests_ok = db_info.get('tests_ok', 0) == 1
        calibration_ok = db_info.get('calibration_ok', 0) == 1
        prog_time_ok = db_info.get('prog_time', 0) > 0
        calib_time_ok = db_info.get('calib_time', 0) > 0
        
        if config.DEVICE_VALIDATION_ENABLED:
            # Full validation - all conditions must be met
            device_ready = tests_ok and calibration_ok and prog_time_ok and calib_time_ok
        else:
            # Test mode - minimal validation
            device_ready = tests_ok
            
        status = 'READY' if device_ready else 'NOT READY'
        
        return jsonify({
            'success': True,
            'handle': f'{handle:X}',
            'mcu_id': mcu_str,
            'serial': serial if serial else 'Error',
            'tests_ok': db_info.get('tests_ok', 0),
            'calibration_ok': db_info.get('calibration_ok', 0),
            'prog_time': db_info.get('prog_time', 0),
            'calib_time': db_info.get('calib_time', 0),
            'status': status,
            'device_ready': device_ready,  # Add explicit ready flag
            'validation_enabled': config.DEVICE_VALIDATION_ENABLED
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/get_device_info')
def get_device_info():
    """Get device serial number"""
    try:
        device = rc_client.get_single_device()
        serial = device["serial"]
        
        if not serial:
            return jsonify({
                'success': False,
                'message': 'Не удалось получить серийный номер с устройства'
            })
        
        return jsonify({
            'success': True,
            'serial': serial
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/print_label', methods=['POST'])
def print_label():
    """Print label with serial from device"""
    try:
        data = request.get_json()
        serial_number = data.get('serial_number', '').strip()
        
        if not serial_number:
            return jsonify({
                'success': False,
                'message': 'Серийный номер не может быть пустым'
            })
        
        # Double-check device readiness on server side
        device_status_response = device_status()
        device_data = device_status_response.get_json()
        
        if not device_data.get('success', False):
            return jsonify({
                'success': False,
                'message': 'Ошибка получения статуса устройства'
            })
        
        if not device_data.get('device_ready', False):
            return jsonify({
                'success': False,
                'message': 'Устройство не готово к печати. Проверьте статус устройства.'
            })
        
        # Create and print label with conditional physical printing
        success = printer.create_and_print_label(
            serial_number=serial_number,
            template_pdf='templ_103.pdf',
            add_qr=True,
            print_after_create=config.PHYSICAL_PRINT_ENABLED  # Use config setting
        )
        
        if success:
            if config.PHYSICAL_PRINT_ENABLED:
                message = f'Этикетка "{serial_number}" успешно создана и отправлена на печать!'
            else:
                message = f'Этикетка "{serial_number}" создана (печать симулирована). Запись в БД выполнена.'
                
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Ошибка при создании или печати этикетки'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Ошибка сервера: {str(e)}'
        })

@app.route('/check_scan_status', methods=['POST'])
def check_scan_status():
    """Check if a barcode has been scanned"""
    try:
        data = request.get_json()
        barcode = data.get('barcode', '').strip()
        
        if not barcode:
            return jsonify({
                'success': False,
                'message': 'Штрихкод не может быть пустым'
            })
        
        # Query webhook API to check if barcode exists and get status
        response = requests.get(f"{config.WEBHOOK_API_BASE}/devices", params={'limit': 100}, timeout=config.WEBHOOK_TIMEOUT)
        
        if response.status_code == 200:
            devices_data = response.json()
            devices = devices_data.get('devices', [])
            
            # Look for the specific barcode
            for device in devices:
                if device.get('barcode') == barcode:
                    return jsonify({
                        'success': True,
                        'scanned': True,
                        'status': device.get('status', 'unknown'),
                        'timestamp': device.get('scan_timestamp')
                    })
            
            # Barcode not found in scanned devices
            return jsonify({
                'success': True,
                'scanned': False,
                'message': 'Штрихкод еще не отсканирован'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Ошибка получения данных из системы сканирования'
            })
            
    except requests.exceptions.RequestException as e:
        return jsonify({
            'success': False,
            'message': f'Ошибка соединения с системой сканирования: {str(e)}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Ошибка сервера: {str(e)}'
        })

@app.route('/get_scanned_items')
def get_scanned_items():
    """Get recent scanned items from webhook API"""
    try:
        response = requests.get(f"{config.WEBHOOK_API_BASE}/devices", params={'limit': 10}, timeout=config.WEBHOOK_TIMEOUT)
        
        if response.status_code == 200:
            devices_data = response.json()
            devices = devices_data.get('devices', [])
            
            # Format devices for frontend
            formatted_items = []
            for device in devices:
                try:
                    # Parse timestamp
                    scan_time = datetime.fromisoformat(device.get('scan_timestamp', ''))
                    formatted_time = scan_time.strftime('%d.%m.%Y %H:%M')
                except:
                    formatted_time = device.get('scan_timestamp', 'Unknown')
                
                formatted_items.append({
                    'barcode': device.get('barcode', 'Unknown'),
                    'status': device.get('status', 'unknown'),
                    'timestamp': formatted_time,
                    'scanner_id': device.get('scanner_id', 'unknown')
                })
            
            return jsonify({
                'success': True,
                'items': formatted_items
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Ошибка получения данных из системы сканирования',
                'items': []
            })
            
    except requests.exceptions.RequestException as e:
        return jsonify({
            'success': False,
            'message': f'Ошибка соединения с системой сканирования: {str(e)}',
            'items': []
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Ошибка сервера: {str(e)}',
            'items': []
        })

if __name__ == '__main__':
    print("🚀 Запуск веб-сервера принтера этикеток с RCDevices и сканированием...")
    print("📍 Откройте браузер и перейдите по адресу: http://localhost:5000")
    print("🔗 Подключение к системе сканирования: http://192.168.88.132:3000")
    print("📊 Мониторинг базы данных: http://192.168.88.132/adminer")
    print(f"🔧 Проверки устройства: {'ВКЛЮЧЕНЫ' if config.DEVICE_VALIDATION_ENABLED else 'ОТКЛЮЧЕНЫ (ТЕСТ)'}")
    print(f"🖨️ Физическая печать: {'ВКЛЮЧЕНА' if config.PHYSICAL_PRINT_ENABLED else 'ОТКЛЮЧЕНА (СИМУЛЯЦИЯ)'}")
    print("⏹️  Для остановки нажмите Ctrl+C")
    
   # app.run(debug=True, host='0.0.0.0', port=5000)
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=False)