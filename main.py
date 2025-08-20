from flask import Flask, render_template_string, request, jsonify
from print_labels import LabelPrinter
import os

app = Flask(__name__)

# HTML template (можно вынести в отдельный файл templates/index.html)
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Принтер этикеток</title>
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

        .header p {
            color: #7f8c8d;
            font-size: 16px;
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

        input[type="text"], input[type="number"], select {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e1e8ed;
            border-radius: 10px;
            font-size: 16px;
            transition: all 0.3s ease;
            background: #f8f9fa;
        }

        input[type="text"]:focus, input[type="number"]:focus, select:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            background: white;
        }

        .checkbox-group {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-top: 5px;
        }

        input[type="checkbox"] {
            width: 20px;
            height: 20px;
            accent-color: #667eea;
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

        .btn:active {
            transform: translateY(0);
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

        .status.loading {
            background: #e2e3e5;
            color: #383d41;
            border: 1px solid #d6d8db;
        }

        .spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-right: 10px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .advanced-options {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
            border: 1px solid #e9ecef;
        }

        .advanced-header {
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 15px;
            color: #495057;
            font-weight: 500;
        }

        .advanced-content {
            display: none;
        }

        .advanced-content.show {
            display: block;
            animation: fadeIn 0.3s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        .toggle-icon {
            transition: transform 0.3s ease;
        }

        .toggle-icon.rotated {
            transform: rotate(180deg);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏷️ Принтер этикеток</h1>
            <p>Создание и печать этикеток с QR-кодами</p>
        </div>

        <form id="labelForm">
            <div class="form-group">
                <label for="serialNumber">Серийный номер *</label>
                <input type="text" id="serialNumber" name="serial_number" placeholder="RC-103-000126" required>
            </div>

            <div class="form-group">
                <label for="templatePdf">Шаблон PDF</label>
                <input type="text" id="templatePdf" name="template_pdf" value="templ_103.pdf" placeholder="templ_103.pdf">
            </div>

            <div class="form-group">
                <div class="checkbox-group">
                    <input type="checkbox" id="addQr" name="add_qr" checked>
                    <label for="addQr">Добавить QR-код</label>
                </div>
            </div>

            <div class="form-group">
                <div class="checkbox-group">
                    <input type="checkbox" id="printAfter" name="print_after" checked>
                    <label for="printAfter">Печатать после создания</label>
                </div>
            </div>

            <div class="advanced-options">
                <div class="advanced-header" onclick="toggleAdvanced()">
                    <span>⚙️ Дополнительные настройки</span>
                    <span class="toggle-icon">▼</span>
                </div>
                <div class="advanced-content" id="advancedContent">
                    <div class="form-group">
                        <label for="scale">Масштаб печати</label>
                        <input type="number" id="scale" name="scale" value="1.0" step="0.1" min="0.1" max="3.0">
                    </div>
                    
                    <div class="form-group">
                        <div class="checkbox-group">
                            <input type="checkbox" id="showGrid" name="show_grid">
                            <label for="showGrid">Показать координатную сетку</label>
                        </div>
                    </div>
                </div>
            </div>

            <button type="submit" class="btn" id="submitBtn">
                🖨️ Создать и распечатать этикетку
            </button>
        </form>

        <div class="status" id="status"></div>
    </div>

    <script>
        function toggleAdvanced() {
            const content = document.getElementById('advancedContent');
            const icon = document.querySelector('.toggle-icon');
            
            content.classList.toggle('show');
            icon.classList.toggle('rotated');
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

        document.getElementById('labelForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const submitBtn = document.getElementById('submitBtn');
            const formData = new FormData(this);
            
            // Convert form data to JSON
            const data = {};
            for (let [key, value] of formData.entries()) {
                if (key === 'add_qr' || key === 'print_after' || key === 'show_grid') {
                    data[key] = true;
                } else {
                    data[key] = value;
                }
            }
            
            // Handle unchecked checkboxes
            const checkboxes = ['add_qr', 'print_after', 'show_grid'];
            checkboxes.forEach(checkbox => {
                if (!data[checkbox]) {
                    data[checkbox] = false;
                }
            });
            
            // Convert scale to float
            data.scale = parseFloat(data.scale);
            
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<div class="spinner"></div>Обработка...';
            showStatus('<div class="spinner"></div>Создание этикетки...', 'loading');
            
            try {
                const response = await fetch('/print_label', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showStatus('✅ ' + result.message, 'success');
                    document.getElementById('serialNumber').value = '';
                } else {
                    showStatus('❌ ' + result.message, 'error');
                }
            } catch (error) {
                showStatus('❌ Ошибка соединения с сервером', 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '🖨️ Создать и распечатать этикетку';
            }
        });

        // Auto-focus on serial number input
        document.getElementById('serialNumber').focus();
    </script>
</body>
</html>"""

# Создаем экземпляр принтера
printer = LabelPrinter(enable_logging=False, temp_filename="web_label.pdf")

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/print_label', methods=['POST'])
def print_label():
    try:
        data = request.get_json()
        
        serial_number = data.get('serial_number', '').strip()
        template_pdf = data.get('template_pdf', 'templ_103.pdf').strip()
        add_qr = data.get('add_qr', True)
        print_after = data.get('print_after', True)
        show_grid = data.get('show_grid', False)
        scale = data.get('scale', 1.0)
        
        if not serial_number:
            return jsonify({
                'success': False,
                'message': 'Серийный номер не может быть пустым'
            })
        
        if not template_pdf:
            template_pdf = 'templ_103.pdf'
        
        # Проверяем существование шаблона
        if not os.path.exists(template_pdf):
            return jsonify({
                'success': False,
                'message': f'Файл шаблона {template_pdf} не найден'
            })
        
        # Создаем и печатаем этикетку
        success = printer.create_and_print_label(
            serial_number=serial_number,
            template_pdf=template_pdf,
            add_qr=add_qr,
            print_after_create=print_after,
            show_grid=show_grid,
            scale=scale
        )
        
        if success:
            if print_after:
                message = f'Этикетка "{serial_number}" успешно создана и отправлена на печать!'
            else:
                message = f'Этикетка "{serial_number}" успешно создана!'
            
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

@app.route('/status')
def status():
    """Статус сервера и доступных принтеров"""
    try:
        printers = printer.get_available_printers()
        return jsonify({
            'success': True,
            'current_printer': printer.printer_name,
            'available_printers': printers,
            'temp_filename': printer.temp_filename
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

if __name__ == '__main__':
    print("🚀 Запуск веб-сервера принтера этикеток...")
    print("📍 Откройте браузер и перейдите по адресу: http://localhost:5000")
    print("⏹️  Для остановки нажмите Ctrl+C")
    
    app.run(debug=True, host='0.0.0.0', port=5000)