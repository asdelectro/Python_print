# Flask server with RCDevices integration
# -*- coding: utf-8 -*-
from flask import Flask, render_template_string, request, jsonify
from print_labels import LabelPrinter
from hardware import RCDevicesClient  # Import class from hardware.py
import os

app = Flask(__name__)

# HTML template with device info section
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Принтер этикеток - RCDevices</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        .container {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            padding: 40px;
            width: 100%;
            max-width: 500px;
            animation: slideIn 0.5s ease-out;
        }

        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(-30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .header {
            text-align: center;
            margin-bottom: 30px;
        }

        .header h1 {
            color: #2c3e50;
            font-size: 28px;
            font-weight: 600;
            margin-bottom: 10px;
        }

        .device-info {
            background: #e8f4fd;
            border: 1px solid #bee5eb;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
            font-size: 14px;
            line-height: 1.6;
        }

        .device-info.error {
            background: #f8d7da;
            border-color: #f5c6cb;
            color: #721c24;
        }

        .device-info.success {
            background: #d4edda;
            border-color: #c3e6cb;
            color: #155724;
        }

        .device-field {
            margin-bottom: 8px;
            font-family: 'Courier New', monospace;
            display: flex;
            align-items: center;
        }

        .device-field strong {
            color: #2c3e50;
            min-width: 140px;
        }

        .status-icon {
            margin-left: 10px;
            font-size: 16px;
        }

        .status-icon.green {
            color: #28a745;
        }

        .status-icon.red {
            color: #dc3545;
        }

        .device-warning {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            color: #856404;
            padding: 15px;
            border-radius: 10px;
            margin: 15px 0;
            font-weight: 500;
            text-align: center;
        }

        .btn.disabled {
            background: #6c757d !important;
            cursor: not-allowed !important;
            transform: none !important;
            box-shadow: none !important;
        }

        .form-group {
            margin-bottom: 20px;
        }

        label {
            display: block;
            color: #34495e;
            font-weight: 500;
            margin-bottom: 8px;
            font-size: 14px;
        }

        input[type="text"] {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e1e8ed;
            border-radius: 10px;
            font-size: 16px;
            transition: all 0.3s ease;
            background: #f8f9fa;
        }

        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            background: white;
        }

        .btn {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 10px;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.3);
        }

        .btn:disabled {
            background: #bdc3c7;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }

        .status {
            margin-top: 20px;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            font-weight: 500;
            display: none;
        }

        .status.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }

        .status.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏷️ Принтер этикеток</h1>
        </div>

        <div id="deviceInfo" class="device-info">
            📡 Загрузка информации об устройстве...
        </div>

        <form id="labelForm">
            <div class="form-group">
                <label for="serialNumber">Серийный номер *</label>
                <input type="text" id="serialNumber" name="serial_number" placeholder="Будет заполнен автоматически" readonly>
            </div>

            <button type="button" class="btn" onclick="getDeviceSerial()">
                🔄 Получить серийный номер с устройства
            </button>

            <button type="submit" class="btn" id="submitBtn">
                🖨️ Создать и распечатать этикетку
            </button>
        </form>

        <div class="status" id="status"></div>
    </div>

    <script>
        function showStatus(message, type) {
            const status = document.getElementById('status');
            status.className = `status ${type}`;
            status.innerHTML = message;
            status.style.display = 'block';
            
            if (type === 'success') {
                setTimeout(() => {
                    status.style.display = 'none';
                }, 5000);
            }
        }

        async function getDeviceSerial() {
            try {
                // Сначала обновляем информацию об устройстве
                await loadDeviceInfo();
                
                const response = await fetch('/get_device_info');
                const result = await response.json();
                
                if (result.success) {
                    document.getElementById('serialNumber').value = result.serial;
                    showStatus('✅ Серийный номер получен с устройства', 'success');
                } else {
                    showStatus('❌ ' + result.message, 'error');
                }
            } catch (error) {
                showStatus('❌ Ошибка соединения с сервером', 'error');
            }
        }

        async function loadDeviceInfo() {
            try {
                const response = await fetch('/device_status');
                const result = await response.json();
                
                const deviceInfo = document.getElementById('deviceInfo');
                
                if (result.success) {
                    deviceInfo.className = 'device-info success';
                    
                    // Check device readiness
                    const testsOk = result.tests_ok === 1;
                    const calibOk = result.calibration_ok === 1;
                    const progTimeOk = result.prog_time > 0;
                    const calibTimeOk = result.calib_time > 0;
                    
                    const isDeviceReady = testsOk && calibOk && progTimeOk && calibTimeOk;
                    
                    let warningHtml = '';
                    if (!isDeviceReady) {
                        warningHtml = '<div class="device-warning">⚠️ <strong>УСТРОЙСТВО НЕ ГОТОВО!</strong> Печать этикетки заблокирована.</div>';
                    }
                    
                    deviceInfo.innerHTML = `
                        ✅ <strong>Устройство подключено</strong><br><br>
                        <div class="device-field">
                            <strong>Serial:</strong> ${result.serial}
                        </div>
                        <div class="device-field">
                            <strong>Tests OK:</strong> ${result.tests_ok}
                            <span class="status-icon ${testsOk ? 'green' : 'red'}">${testsOk ? '✅' : '❌'}</span>
                        </div>
                        <div class="device-field">
                            <strong>Calibration OK:</strong> ${result.calibration_ok}
                            <span class="status-icon ${calibOk ? 'green' : 'red'}">${calibOk ? '✅' : '❌'}</span>
                        </div>
                        <div class="device-field">
                            <strong>Program Time:</strong> ${result.prog_time}
                            <span class="status-icon ${progTimeOk ? 'green' : 'red'}">${progTimeOk ? '✅' : '❌'}</span>
                        </div>
                        <div class="device-field">
                            <strong>Calibration Time:</strong> ${result.calib_time}
                            <span class="status-icon ${calibTimeOk ? 'green' : 'red'}">${calibTimeOk ? '✅' : '❌'}</span>
                        </div>
                        <div class="device-field">
                            <strong>Status:</strong> ${isDeviceReady ? 'READY' : 'NOT READY'}
                            <span class="status-icon ${isDeviceReady ? 'green' : 'red'}">${isDeviceReady ? '✅' : '❌'}</span>
                        </div>
                        ${warningHtml}
                    `;
                    
                    // Enable/disable print button based on device readiness
                    const submitBtn = document.getElementById('submitBtn');
                    if (isDeviceReady) {
                        submitBtn.disabled = false;
                        submitBtn.classList.remove('disabled');
                        submitBtn.innerHTML = '🖨️ Создать и распечатать этикетку';
                    } else {
                        submitBtn.disabled = true;
                        submitBtn.classList.add('disabled');
                        submitBtn.innerHTML = '❌ Устройство не готово к печати';
                    }
                } else {
                    deviceInfo.className = 'device-info error';
                    deviceInfo.innerHTML = `❌ <strong>Ошибка:</strong> ${result.message}`;
                }
            } catch (error) {
                const deviceInfo = document.getElementById('deviceInfo');
                deviceInfo.className = 'device-info error';
                deviceInfo.innerHTML = '❌ <strong>Ошибка соединения с сервером</strong>';
            }
        }

        document.getElementById('labelForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const submitBtn = document.getElementById('submitBtn');
            const serialNumber = document.getElementById('serialNumber').value.trim();
            
            // Check if button is disabled (device not ready)
            if (submitBtn.disabled || submitBtn.classList.contains('disabled')) {
                showStatus('❌ Устройство не готово к печати. Проверьте статус устройства.', 'error');
                return;
            }
            
            if (!serialNumber) {
                showStatus('❌ Сначала получите серийный номер с устройства', 'error');
                return;
            }
            
            submitBtn.disabled = true;
            submitBtn.innerHTML = '⏳ Печать...';
            
            try {
                const response = await fetch('/print_label', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        serial_number: serialNumber,
                        template_pdf: 'templ_103.pdf',
                        add_qr: true,
                        print_after: true
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showStatus('✅ ' + result.message, 'success');
                } else {
                    showStatus('❌ ' + result.message, 'error');
                }
            } catch (error) {
                showStatus('❌ Ошибка соединения с сервером', 'error');
            } finally {
                // Restore button state based on device readiness
                await loadDeviceInfo(); // Refresh device status to restore proper button state
            }
        });

        // Load device info on page load
        loadDeviceInfo();
    </script>
</body>
</html>"""

# Create instances
printer = LabelPrinter(enable_logging=False, temp_filename="web_label.pdf")
rc_client = RCDevicesClient()

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/device_status')
def device_status():
    """Get device status"""
    try:
        device = rc_client.get_single_device()
        
        handle = device["handle"]
        mcu_id = device["mcu_id"]
        serial = device["serial"]
        db_info = device["db_info"]
        
        mcu_str = ' '.join(f'{b:02X}' for b in mcu_id) if mcu_id else 'Error'
        status = 'READY' if db_info['result'] == 0 and db_info['tests_ok'] and db_info['calibration_ok'] else 'ERROR'
        
        return jsonify({
            'success': True,
            'handle': f'{handle:X}',
            'mcu_id': mcu_str,
            'serial': serial if serial else 'Error',
            'tests_ok': db_info['tests_ok'],
            'calibration_ok': db_info['calibration_ok'],
            'prog_time': db_info['prog_time'],
            'calib_time': db_info['calib_time'],
            'status': status
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
        
        # Create and print label
        success = printer.create_and_print_label(
            serial_number=serial_number,
            template_pdf='templ_103.pdf',
            add_qr=True,
            print_after_create=True
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Этикетка "{serial_number}" успешно создана и отправлена на печать!'
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

if __name__ == '__main__':
    print("🚀 Запуск веб-сервера принтера этикеток с RCDevices...")
    print("📍 Откройте браузер и перейдите по адресу: http://localhost:5000")
    print("⏹️  Для остановки нажмите Ctrl+C")
    
    app.run(debug=True, host='0.0.0.0', port=5000)