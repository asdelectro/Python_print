# Flask server with RCDevices integration and barcode scanning
# -*- coding: utf-8 -*-
from flask import Flask, render_template_string, request, jsonify
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
            max-width: 600px;
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

        .scan-section {
            background: #fff3cd;
            border: 2px solid #ffeaa7;
            border-radius: 15px;
            padding: 20px;
            margin: 20px 0;
            text-align: center;
            display: none;
        }

        .scan-section.show {
            display: block;
            animation: fadeIn 0.5s ease-in;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .scan-title {
            color: #856404;
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 15px;
        }

        .scan-barcode {
            background: white;
            border: 2px solid #ffeaa7;
            border-radius: 10px;
            padding: 15px;
            font-family: 'Courier New', monospace;
            font-size: 16px;
            font-weight: bold;
            color: #2c3e50;
            margin: 15px 0;
        }

        .scanned-items {
            background: #e8f4fd;
            border: 1px solid #bee5eb;
            border-radius: 10px;
            padding: 15px;
            margin-top: 20px;
            max-height: 200px;
            overflow-y: auto;
        }

        .scanned-item {
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 14px;
        }

        .scanned-item:last-child {
            margin-bottom: 0;
        }

        .barcode-text {
            font-family: 'Courier New', monospace;
            font-weight: bold;
            color: #2c3e50;
        }

        .status-badge {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }

        .status-ready {
            background: #d4edda;
            color: #155724;
        }

        .status-preready {
            background: #fff3cd;
            color: #856404;
        }

        .timestamp {
            font-size: 11px;
            color: #6c757d;
            margin-top: 4px;
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

        .btn-scan {
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            margin-top: 15px;
        }

        .btn-scan:hover {
            box-shadow: 0 10px 25px rgba(40, 167, 69, 0.3);
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

        .stats-header {
            color: #2c3e50;
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 10px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏷️ Принтер этикеток</h1>
            <div style="font-size: 12px; color: #6c757d; margin-top: 5px;">
                <div>
                    Проверки устройства: <span id="validationStatus" style="font-weight: bold;"></span>
                    <button type="button" onclick="toggleValidation()" style="margin-left: 10px; padding: 2px 8px; font-size: 11px; border: 1px solid #ccc; background: white; border-radius: 4px; cursor: pointer;">
                        Переключить
                    </button>
                </div>
                <div style="margin-top: 5px;">
                    Физическая печать: <span id="printStatus" style="font-weight: bold;"></span>
                    <button type="button" onclick="togglePrint()" style="margin-left: 10px; padding: 2px 8px; font-size: 11px; border: 1px solid #ccc; background: white; border-radius: 4px; cursor: pointer;">
                        Переключить
                    </button>
                </div>
            </div>
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

        <!-- Scan Section -->
        <div id="scanSection" class="scan-section">
            <div class="scan-title">📷 Отсканируйте напечатанную этикетку</div>
            <div class="scan-barcode" id="scanBarcode">Ожидание сканирования...</div>
            <button type="button" class="btn btn-scan" onclick="checkScanStatus()">
                🔍 Проверить статус сканирования
            </button>
            <button type="button" class="btn" onclick="hideScanSection()">
                ✅ Завершить
            </button>
        </div>

        <!-- Scanned Items Preview -->
        <div id="scannedItems" class="scanned-items" style="display: none;">
            <div class="stats-header">📋 Последние отсканированные этикетки</div>
            <div id="itemsList"></div>
        </div>

        <div class="status" id="status"></div>
    </div>

    <script>
        let currentPrintedBarcode = '';
        let scanCheckInterval = null;
        let deviceValidationEnabled = true; // Default state
        let physicalPrintEnabled = true; // Default state
        
        function updateValidationStatus() {
            const statusElement = document.getElementById('validationStatus');
            if (deviceValidationEnabled) {
                statusElement.textContent = 'ВКЛЮЧЕНЫ';
                statusElement.style.color = '#28a745';
            } else {
                statusElement.textContent = 'ОТКЛЮЧЕНЫ (ТЕСТ)';
                statusElement.style.color = '#dc3545';
            }
        }
        
        function updatePrintStatus() {
            const statusElement = document.getElementById('printStatus');
            if (physicalPrintEnabled) {
                statusElement.textContent = 'ВКЛЮЧЕНА';
                statusElement.style.color = '#28a745';
            } else {
                statusElement.textContent = 'ОТКЛЮЧЕНА (СИМУЛЯЦИЯ)';
                statusElement.style.color = '#ff6b35';
            }
        }
        
        async function toggleValidation() {
            try {
                const response = await fetch('/toggle_validation', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                
                const result = await response.json();
                if (result.success) {
                    deviceValidationEnabled = result.validation_enabled;
                    updateValidationStatus();
                    await loadDeviceInfo(); // Refresh device info with new validation setting
                    showStatus(`Проверки устройства ${deviceValidationEnabled ? 'включены' : 'отключены'}`, 'success');
                }
            } catch (error) {
                showStatus('Ошибка переключения режима проверок', 'error');
            }
        }
        
        async function togglePrint() {
            try {
                const response = await fetch('/toggle_print', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                
                const result = await response.json();
                if (result.success) {
                    physicalPrintEnabled = result.print_enabled;
                    updatePrintStatus();
                    await loadDeviceInfo(); // Refresh device info to update button text
                    showStatus(`Физическая печать ${physicalPrintEnabled ? 'включена' : 'отключена (симуляция)'}`, 'success');
                }
            } catch (error) {
                showStatus('Ошибка переключения режима печати', 'error');
            }
        }
        
        async function getValidationStatus() {
            try {
                const response = await fetch('/get_config_status');
                const result = await response.json();
                if (result.success) {
                    deviceValidationEnabled = result.validation_enabled;
                    physicalPrintEnabled = result.print_enabled;
                    updateValidationStatus();
                    updatePrintStatus();
                }
            } catch (error) {
                console.error('Error getting config status:', error);
            }
        }
        
        function formatTime(timestamp) {
            if (!timestamp || timestamp <= 0) return 'Не установлено';
            const date = new Date(timestamp * 1000);
            const day = String(date.getDate()).padStart(2, '0');
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const year = date.getFullYear();
            const hours = String(date.getHours()).padStart(2, '0');
            const minutes = String(date.getMinutes()).padStart(2, '0');
            return `${day}.${month}.${year} ${hours}:${minutes}`;
        }

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

        function showScanSection(barcode) {
            currentPrintedBarcode = barcode;
            document.getElementById('scanBarcode').textContent = `Ожидание сканирования: ${barcode}`;
            document.getElementById('scanSection').classList.add('show');
            
            // Start automatic checking for scan
            startScanChecking();
        }

        function hideScanSection() {
            document.getElementById('scanSection').classList.remove('show');
            currentPrintedBarcode = '';
            stopScanChecking();
            loadScannedItems(); // Refresh scanned items list
        }

        function startScanChecking() {
            stopScanChecking(); // Clear any existing interval
            
            scanCheckInterval = setInterval(async () => {
                if (!currentPrintedBarcode) return;
                
                try {
                    const response = await fetch('/check_scan_status', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ barcode: currentPrintedBarcode })
                    });
                    
                    const result = await response.json();
                    
                    if (result.success && result.scanned) {
                        document.getElementById('scanBarcode').innerHTML = `
                            ✅ <strong>ОТСКАНИРОВАНО!</strong><br>
                            ${currentPrintedBarcode}<br>
                            <small>Статус: ${result.status}</small>
                        `;
                        stopScanChecking();
                        
                        setTimeout(() => {
                            hideScanSection();
                        }, 3000);
                    }
                } catch (error) {
                    console.error('Error checking scan status:', error);
                }
            }, 2000); // Check every 2 seconds
        }

        function stopScanChecking() {
            if (scanCheckInterval) {
                clearInterval(scanCheckInterval);
                scanCheckInterval = null;
            }
        }

        async function checkScanStatus() {
            if (!currentPrintedBarcode) return;
            
            try {
                const response = await fetch('/check_scan_status', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ barcode: currentPrintedBarcode })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    if (result.scanned) {
                        showStatus(`✅ Этикетка ${currentPrintedBarcode} отсканирована (статус: ${result.status})`, 'success');
                        hideScanSection();
                    } else {
                        showStatus('ℹ️ Этикетка еще не отсканирована', 'error');
                    }
                } else {
                    showStatus('❌ ' + result.message, 'error');
                }
            } catch (error) {
                showStatus('❌ Ошибка проверки статуса сканирования', 'error');
            }
        }

        async function loadScannedItems() {
            try {
                const response = await fetch('/get_scanned_items');
                const result = await response.json();
                
                if (result.success && result.items.length > 0) {
                    const itemsList = document.getElementById('itemsList');
                    const scannedItems = document.getElementById('scannedItems');
                    
                    itemsList.innerHTML = result.items.map(item => `
                        <div class="scanned-item">
                            <div>
                                <div class="barcode-text">${item.barcode}</div>
                                <div class="timestamp">${item.timestamp}</div>
                            </div>
                            <div class="status-badge status-${item.status}">${item.status.toUpperCase()}</div>
                        </div>
                    `).join('');
                    
                    scannedItems.style.display = 'block';
                } else {
                    document.getElementById('scannedItems').style.display = 'none';
                }
            } catch (error) {
                console.error('Error loading scanned items:', error);
            }
        }

        async function getDeviceSerial() {
            try {
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
                    
                    const testsOk = result.tests_ok === 1;
                    const calibOk = result.calibration_ok === 1;
                    const progTimeOk = result.prog_time > 0;
                    const calibTimeOk = result.calib_time > 0;
                    
                    // ВРЕМЕННО ДЛЯ ТЕСТОВ: отключить проверки калибровки
                    // const isDeviceReady = testsOk && calibOk && progTimeOk && calibTimeOk;
                    const isDeviceReady = testsOk && progTimeOk; // Проверяем только тесты и время программирования
                    
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
                            <strong>Program Time:</strong> ${formatTime(result.prog_time)}
                            <span class="status-icon ${progTimeOk ? 'green' : 'red'}">${progTimeOk ? '✅' : '❌'}</span>
                        </div>
                        <div class="device-field">
                            <strong>Calibration Time:</strong> ${formatTime(result.calib_time)}
                            <span class="status-icon ${calibTimeOk ? 'green' : 'red'}">${calibTimeOk ? '✅' : '❌'}</span>
                        </div>
                        <div class="device-field">
                            <strong>Status:</strong> ${isDeviceReady ? 'READY' : 'NOT READY'}
                            <span class="status-icon ${isDeviceReady ? 'green' : 'red'}">${isDeviceReady ? '✅' : '❌'}</span>
                        </div>
                        ${warningHtml}
                    `;
                    
                    const submitBtn = document.getElementById('submitBtn');
                    if (isDeviceReady) {
                        submitBtn.disabled = false;
                        submitBtn.classList.remove('disabled');
                        
                        // Update button text based on modes
                        let buttonText = '';
                        if (!deviceValidationEnabled && !physicalPrintEnabled) {
                            buttonText = '🧪 Симулировать создание этикетки (ТЕСТ)';
                        } else if (!deviceValidationEnabled && physicalPrintEnabled) {
                            buttonText = '🧪 Создать и распечатать этикетку (ТЕСТ)';
                        } else if (deviceValidationEnabled && !physicalPrintEnabled) {
                            buttonText = '🖨️ Создать этикетку (БЕЗ ПЕЧАТИ)';
                        } else {
                            buttonText = '🖨️ Создать и распечатать этикетку';
                        }
                        submitBtn.innerHTML = buttonText;
                    } else {
                        submitBtn.disabled = true;
                        submitBtn.classList.add('disabled');
                        if (deviceValidationEnabled) {
                            submitBtn.innerHTML = '❌ Устройство не готово к печати';
                        } else {
                            submitBtn.innerHTML = '❌ Устройство недоступно';
                        }
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
                    showScanSection(serialNumber); // Show scan section after successful print
                } else {
                    showStatus('❌ ' + result.message, 'error');
                }
            } catch (error) {
                showStatus('❌ Ошибка соединения с сервером', 'error');
            } finally {
                await loadDeviceInfo();
            }
        });

        // Load initial data
        loadDeviceInfo();
        loadScannedItems();
        getValidationStatus(); // Get current config status
        
        // Auto-refresh scanned items every 10 seconds
        setInterval(loadScannedItems, 10000);
    </script>
</body>
</html>"""

# Create instances
printer = LabelPrinter(enable_logging=False, temp_filename="web_label.pdf")
rc_client = RCDevicesClient()

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

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
    
    app.run(debug=True, host='0.0.0.0', port=5000)