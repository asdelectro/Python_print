// Global variables
let currentStep = 0;
let currentPrintedBarcode = '';
let scanCheckInterval = null;
let deviceValidationEnabled = true;
let physicalPrintEnabled = true;
let deviceSerial = '';
let deviceReady = false;
let selectedModel = ''; // Selected device model

// Auto mode variables
let autoModeEnabled = false;
let autoCheckInterval = null;
let autoResetTimeout = null;
let lastProcessedSerial = null; 
let failedDevices = new Set();          // Set of device serials that failed validation

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    getConfigStatus();
    loadScannedItems();
});

// Model selection functions
function selectModel(model) {
    selectedModel = model;
    updateModelButtons();
    showStatus(`✅ Выбрана модель: ${model}`, 'success');
    
    // Stop auto mode if running
    if (autoModeEnabled) {
        stopAutoMode();
    }
}

function updateModelButtons() {
    const models = ['RC-102', 'RC-103', 'RC-103G', 'RC-110', 'RC-410'];
    models.forEach(model => {
        const btn = document.getElementById(`model${model.replace('-', '').replace('G', 'g')}`);
        if (btn) {
            if (selectedModel === model) {
                btn.style.background = 'linear-gradient(135deg, #28a745 0%, #20c997 100%)';
                btn.style.opacity = '1';
            } else {
                btn.style.background = '';
                btn.style.opacity = '0.7';
            }
        }
    });
}

function checkModelMatch(deviceSerial) {
    if (!selectedModel || !deviceSerial) return true;
    
    // Extract model prefix from serial (e.g., "RC-102" from "RC-102-012385")
    const serialPrefix = deviceSerial.substring(0, deviceSerial.lastIndexOf('-'));
    
    return serialPrefix === selectedModel;
}

// Scroll functions
function scrollToElement(elementId, offset = 0) {
    const element = document.getElementById(elementId);
    if (element) {
        const elementPosition = element.offsetTop;
        const offsetPosition = elementPosition - offset;
        
        window.scrollTo({
            top: offsetPosition,
            behavior: 'smooth'
        });
    }
}

function autoScrollToActiveStep() {
    if (!autoModeEnabled) return;
    
    // Find active step and scroll to it
    const activeStep = document.querySelector('.step-item.active');
    if (activeStep) {
        const stepId = activeStep.id;
        setTimeout(() => {
            scrollToElement(stepId, 100); // 100px offset from top
        }, 300); // Small delay to allow state updates
    }
}

// Configuration functions
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

async function getConfigStatus() {
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
            showStatus(`Проверки устройства ${deviceValidationEnabled ? 'включены' : 'отключены'}`, 'success');
            resetProcess();
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
            showStatus(`Физическая печать ${physicalPrintEnabled ? 'включена' : 'отключена (симуляция)'}`, 'success');
            updatePrintButtonText();
        }
    } catch (error) {
        showStatus('Ошибка переключения режима печати', 'error');
    }
}

function updatePrintButtonText() {
    const printBtn = document.getElementById('printBtn');
    if (printBtn && !printBtn.disabled) {
        let buttonText = '';
        if (!deviceValidationEnabled && !physicalPrintEnabled) {
            buttonText = 'Симулировать создание этикетки (ТЕСТ)';
        } else if (!deviceValidationEnabled && physicalPrintEnabled) {
            buttonText = 'Создать и распечатать этикетку (ТЕСТ)';
        } else if (deviceValidationEnabled && !physicalPrintEnabled) {
            buttonText = 'Создать этикетку (БЕЗ ПЕЧАТИ)';
        } else {
            buttonText = 'Создать и распечатать этикетку';
        }
        printBtn.innerHTML = buttonText;
    }
}

// Auto Mode Functions
function toggleAutoMode() {
    if (autoModeEnabled) {
        stopAutoMode();
    } else {
        startAutoMode();
    }
}

function startAutoMode() {
    if (!selectedModel) {
        showStatus('❌ Сначала выберите модель устройства!', 'error');
        return;
    }
    
    autoModeEnabled = true;
    document.getElementById('autoModeBtn').style.display = 'none';
    document.getElementById('stopAutoBtn').style.display = 'block';
    document.getElementById('connectBtn').style.display = 'none';
    
    showStatus(`Автоматический режим включен для модели ${selectedModel} - проверка устройств каждую секунду`, 'success');
    
    // Start automatic device checking
    autoCheckInterval = setInterval(autoCheckDevice, 1000);
}

function stopAutoMode() {
    autoModeEnabled = false;
    document.getElementById('autoModeBtn').style.display = 'block';
    document.getElementById('stopAutoBtn').style.display = 'none';
    document.getElementById('connectBtn').style.display = 'block';
    
    // Clear all intervals
    if (autoCheckInterval) {
        clearInterval(autoCheckInterval);
        autoCheckInterval = null;
    }
    
    if (autoResetTimeout) {
        clearTimeout(autoResetTimeout);
        autoResetTimeout = null;
    }
    
    // Clear last processed device memory
    lastProcessedSerial = null;
    
    showStatus('Автоматический режим отключен', 'success');
    // Clear failed devices list when switching to manual mode
    failedDevices.clear();
    resetProcess();
}

async function autoCheckDevice() {
    if (!autoModeEnabled) return;
    
    try {
        // Add cache-busting to prevent webview caching issues
        const timestamp = Date.now();
        const response = await fetch(`/device_status?_t=${timestamp}`, {
            method: 'GET',
            headers: {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        });
        const result = await response.json();
        
        if (result.success && result.serial&& result.device_count === 1) {
            // Check model match
            if (!checkModelMatch(result.serial)) {
                const detectedModel = result.serial.substring(0, result.serial.lastIndexOf('-'));
                alert(`⚠️ АВТОМАТИЧЕСКИЙ РЕЖИМ ОСТАНОВЛЕН!\n\nПодключена модель: ${detectedModel}\nВыбрана модель: ${selectedModel}\n\nОтключите устройство!`);
                showStatus(`❌ ОШИБКА: Подключена модель ${detectedModel}, но выбрана ${selectedModel}! Отключите устройство!`, 'error');
                document.getElementById('deviceSerial').textContent = `❌ НЕВЕРНАЯ МОДЕЛЬ: ${result.serial}`;
                document.getElementById('progressText').textContent = `Ожидается ${selectedModel}, подключена ${detectedModel}`;
                stopAutoMode();
                return;
            }
            
            // Check if this device has already failed validation
            if (failedDevices.has(result.serial)) {
                document.getElementById('deviceSerial').textContent = `❌ НЕ ПРОШЛО ПРОВЕРКУ: ${result.serial}`;
                document.getElementById('progressText').textContent = 'Устройство не прошло проверки - отключите его';
                showStatus('❌ Это устройство уже не прошло проверки - отключите его', 'error');
                
                // Offer to check device in diagnostic tool
                if (confirm(`⚠️ Устройство не прошло проверки!\n\nСерийный номер: ${result.serial}\n\nОткрыть диагностику устройства?`)) {
                    window.open(`http://192.168.88.132:5000/?serial=${encodeURIComponent(result.serial)}`, '_blank');
                }
                
                return; // Do not process further
            } 

            // Check if this is the same device we just processed successfully
            if (lastProcessedSerial === result.serial) {
                // Same device still connected - show warning to disconnect
                if (currentStep === 0) { // Only show if we're in waiting state
                    document.getElementById('deviceSerial').textContent = `⚠️ ОТКЛЮЧИТЕ УСТРОЙСТВО: ${result.serial}`;
                    document.getElementById('progressText').textContent = 'Отключите обработанное устройство для продолжения';
                    showStatus('⚠️ Отключите предыдущее устройство перед подключением нового', 'error');
                }
                return; // Don't process the same device again
            }
            
            // New device found - proceed with automatic processing flow
            if (deviceSerial !== result.serial || currentStep < 1) {
                // New device or restart processing
                deviceSerial = result.serial;
                lastProcessedSerial = null; // Reset since we're starting new processing
                document.getElementById('deviceSerial').textContent = deviceSerial;
                
                // Step 1: Connect
                updateStepState('step1', 'active');
                updateProgress(1);
                autoScrollToActiveStep();
                
                setTimeout(() => {
                    updateStepState('step1', 'completed');
                    document.querySelector('#step1 .step-description').textContent = 'Устройство автоматически подключено';
                    
                    // Step 2: Validate
                    autoValidateDevice(result);
                }, 500);
            }
        } else {
            // No device detected - reset if needed
            if (currentStep > 0 && currentStep < 4) {
                await new Promise(resolve => setTimeout(resolve, 3000));
                resetProcess();
                showStatus('Устройство отключено - ожидание нового подключения', 'error');
            } else if (currentStep === 4) {
                // Шаг 4 - ожидание сканирования, НЕ сбрасываем процесс
                // Показываем что устройство отключено, но продолжаем ждать сканирование
                if (currentPrintedBarcode) {
                    document.getElementById('deviceSerial').textContent = `📱 ОЖИДАНИЕ СКАНИРОВАНИЯ: ${currentPrintedBarcode}`;
                    document.getElementById('progressText').textContent = 'Устройство отключено - ожидание сканирования этикетки';
                     deviceSerial = '';
                    // НЕ вызываем resetProcess() - продолжаем ждать сканирование
                }
            }
            
            // Clear processed device memory when no device connected
            if (currentStep === 0) {
                lastProcessedSerial = null;
                // Also clear failed devices list when device disconnects
                failedDevices.clear();
                document.getElementById('deviceSerial').textContent = 'Автоматический режим: Ожидание устройства...';
                document.getElementById('progressText').textContent = 'Автоматический режим: Ожидание устройства';
            }
        }
    } catch (error) {
        console.error('Auto check error:', error);
    }
}


async function autoValidateDevice(deviceData) {
    if (!autoModeEnabled) return;
    
    updateStepState('step2', 'active');
    updateProgress(2);
    autoScrollToActiveStep();
    
    // Show device status information box
    document.getElementById('deviceStatusBox').style.display = 'block';
    
    // Update status display with device data
    document.getElementById('serialValue').textContent = deviceData.serial || 'Error';
    document.getElementById('testsValue').textContent = deviceData.tests_ok;
    document.getElementById('calibValue').textContent = deviceData.calibration_ok;
    document.getElementById('statusValue').textContent = deviceData.status;
    
    // Check device validation parameters
    const testsOk = deviceData.tests_ok === 1;
    const calibOk = deviceData.calibration_ok === 1;
    const progTimeOk = deviceData.prog_time > 0;
    const calibTimeOk = deviceData.calib_time > 0;
    
    // Update validation status icons
    document.getElementById('serialIcon').textContent = deviceData.serial ? '✅' : '❌';
    document.getElementById('testsIcon').textContent = testsOk ? '✅' : '❌';
    document.getElementById('calibIcon').textContent = calibOk ? '✅' : '❌';
    
    // Determine overall device readiness based on validation settings
    let isReady = false;
    if (deviceValidationEnabled) {
        // Full validation required
        isReady = testsOk && calibOk && progTimeOk && calibTimeOk;
    } else {
        // Test mode - only serial number required
        isReady = deviceData.serial && deviceData.serial !== 'Error';
    }
    
    document.getElementById('statusIcon').textContent = isReady ? '✅' : '❌';
    
    if (isReady) {
        // Device passed validation - proceed to printing
        deviceReady = true;
        updateStepState('step2', 'completed');
        document.querySelector('#step2 .step-description').textContent = 'Устройство автоматически верифицировано';
        
        const modeText = deviceValidationEnabled ? '' : ' (тестовый режим)';
        showStatus(`✅ Устройство готово - автоматическая печать${modeText}`, 'success');
        
        // Automatically start printing after 1 second delay
        setTimeout(() => {
            if (autoModeEnabled) {
                autoPrintLabel();
            }
        }, 1000);
    } else {
        // Device failed validation - add to failed devices list
        deviceReady = false;
        updateStepState('step2', 'pending');
        
        // Build detailed error message
        let errorMsg = 'Устройство не готово (авто): ';
        if (!deviceData.serial || deviceData.serial === 'Error') {
            errorMsg += 'Серийный номер не получен. ';
        }
        if (!testsOk) errorMsg += 'Tests не пройдены. ';
        if (deviceValidationEnabled) {
            if (!calibOk) errorMsg += 'Калибровка не выполнена. ';
            if (!progTimeOk) errorMsg += 'Программирование не выполнено. ';
            if (!calibTimeOk) errorMsg += 'Время калибровки не установлено. ';
        }
        
        // Add device to failed devices blacklist
        failedDevices.add(deviceData.serial);
        
        showStatus('❌ ' + errorMsg + ' ОТКЛЮЧИТЕ УСТРОЙСТВО!', 'error');
        
        // Display warning to disconnect failed device
        document.getElementById('deviceSerial').textContent = `❌ НЕ ПРОШЛО ПРОВЕРКУ: ${deviceData.serial}`;
        document.getElementById('progressText').textContent = 'Устройство не прошло проверки - отключите его';
        
        // Offer to check device in diagnostic tool
        setTimeout(() => {
            if (confirm(`⚠️ Устройство не прошло проверки!\n\nСерийный номер: ${deviceData.serial}\n\nОткрыть диагностику устройства?`)) {
                window.open(`http://192.168.88.132:5000/?serial=${encodeURIComponent(deviceData.serial)}`, '_blank');
            }
        }, 500);
        
        // Scroll to error message at the top after short delay
        setTimeout(() => {
            scrollToElement('deviceSerial', 150);
        }, 1500);
    }
}
async function autoPrintLabel() {
    if (!autoModeEnabled || !deviceReady || !deviceSerial) return;
    
    updateStepState('step3', 'active');
    updateProgress(3);
    autoScrollToActiveStep(); // Auto scroll to step 3
    
    try {
        const response = await fetch('/print_label', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                serial_number: deviceSerial,
            })
        });

        const result = await response.json();

        if (result.success) {
            updateStepState('step3', 'completed');
            document.querySelector('#step3 .step-description').textContent = 'Этикетка автоматически напечатана';
            
            // Enable step 4
            updateStepState('step4', 'active');
            updateProgress(4);
            autoScrollToActiveStep(); // Auto scroll to step 4
            
            // Show scan section
            currentPrintedBarcode = deviceSerial;
            document.getElementById('scanContent').style.display = 'block';
            document.getElementById('scanBarcode').textContent = `Ожидание сканирования: ${deviceSerial}`;
            
            // Start automatic scan checking
            startScanChecking();
            
            showStatus('✅ ' + result.message + ' - ожидание сканирования', 'success');
        } else {
            showStatus('❌ Ошибка печати: ' + result.message, 'error');
            
            // Reset after 3 seconds to try again
            setTimeout(() => {
                if (autoModeEnabled) {
                    resetProcess();
                }
            }, 3000);
        }
    } catch (error) {
        showStatus('❌ Ошибка соединения при печати', 'error');
        
        // Reset after 3 seconds to try again
        setTimeout(() => {
            if (autoModeEnabled) {
                resetProcess();
            }
        }, 3000);
    }
}

function updateProgress(step) {
    currentStep = step;
    const progressFill = document.getElementById('mainProgress');
    const progressText = document.getElementById('progressText');
    
    const progressPercentage = (step / 4) * 100;
    progressFill.style.width = progressPercentage + '%';
    
    switch(step) {
        case 0:
            progressText.textContent = autoModeEnabled ? 'Автоматический режим: Ожидание устройства' : 'Готов к работе';
            break;
        case 1:
            progressText.textContent = 'Шаг 1 из 4: Подключение устройства';
            break;
        case 2:
            progressText.textContent = 'Шаг 2 из 4: Проверка в базе данных';
            break;
        case 3:
            progressText.textContent = 'Шаг 3 из 4: Печать этикетки';
            break;
        case 4:
            progressText.textContent = 'Шаг 4 из 4: Сканирование этикетки';
            break;
    }
}

function updateStepState(stepId, state) {
    const step = document.getElementById(stepId);
    const icon = step.querySelector('.step-icon');
    
    // Remove all state classes
    step.classList.remove('pending', 'active', 'completed');
    
    // Add new state
    step.classList.add(state);
    
    if (state === 'completed') {
        icon.textContent = '✓';
    } else if (state === 'active') {
        const stepNum = stepId.replace('step', '');
        icon.textContent = stepNum;
    }
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
            
            if (result.success && result.scanned && result.status === 'ready') {
                document.getElementById('scanBarcode').innerHTML = `
                    ✅ <strong>ОТСКАНИРОВАНО!</strong><br>
                    ${currentPrintedBarcode}<br>
                    <small>Статус: ${result.status}</small>
                `;
                stopScanChecking();
                
                // Complete step 4 
                updateStepState('step4', 'completed');
                document.querySelector('#step4 .step-description').textContent = 'Этикетка отсканирована, процесс завершен';
                
                showStatus('✅ Процесс обработки устройства завершен успешно!', 'success');
                loadScannedItems(); // Refresh scanned items
                
                // Remember this device as processed
                lastProcessedSerial = deviceSerial;
                
                // Auto reset based on mode
                if (autoModeEnabled) {
                    // In auto mode, reset after 3 seconds and continue checking for new devices
                    autoResetTimeout = setTimeout(() => {
                        resetProcess();
                        showStatus('Готов к обработке следующего устройства - отключите предыдущее', 'success');
                        // Scroll back to top for next device
                        setTimeout(() => {
                            scrollToElement('deviceSerial', 150);
                        }, 500);
                    }, 3000);
                } else {
                    // In manual mode, reset after 5 seconds
                    setTimeout(() => {
                        resetProcess();
                    }, 5000);
                }
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

function resetProcess() {
    currentStep = 0;
    currentPrintedBarcode = '';
    deviceReady = false;
    
    // Clear auto reset timeout
    if (autoResetTimeout) {
        clearTimeout(autoResetTimeout);
        autoResetTimeout = null;
    }
    
    // Reset progress
    updateProgress(0);
    document.getElementById('deviceSerial').textContent = autoModeEnabled ? 
        'Автоматический режим: Ожидание устройства...' : 'Ожидание подключения...';
    
    // Reset all steps
    updateStepState('step1', 'pending');
    updateStepState('step2', 'pending');
    updateStepState('step3', 'pending');
    updateStepState('step4', 'pending');
    
    // Reset step descriptions
    document.querySelector('#step1 .step-description').textContent = 'Проверка подключения и получение данных';
    document.querySelector('#step2 .step-description').textContent = 'Автоматическая валидация параметров устройства';
    document.querySelector('#step3 .step-description').textContent = 'Создание и печать этикетки';
    document.querySelector('#step4 .step-description').textContent = 'Ожидание сканирования напечатанной этикетки';
    
    // Reset buttons
    document.getElementById('printBtn').disabled = true;
    document.getElementById('printBtn').innerHTML = 'Создать и распечатать этикетку';
    
    // Hide elements
    document.getElementById('deviceStatusBox').style.display = 'none';
    document.getElementById('scanContent').style.display = 'none';
    
    // Reset status values
    document.getElementById('serialValue').textContent = '-';
    document.getElementById('testsValue').textContent = '-';
    document.getElementById('calibValue').textContent = '-';
    document.getElementById('statusValue').textContent = '-';
    document.getElementById('serialIcon').textContent = '⏳';
    document.getElementById('testsIcon').textContent = '⏳';
    document.getElementById('calibIcon').textContent = '⏳';
    document.getElementById('statusIcon').textContent = '⏳';
    
    stopScanChecking();
}

// Manual mode functions (original functionality)
async function connectDevice() {
    if (autoModeEnabled) {
        showStatus('Отключите автоматический режим для ручного управления', 'error');
        return;
    }
    
    if (!selectedModel) {
        showStatus('❌ Сначала выберите модель устройства!', 'error');
        return;
    }
    
    updateStepState('step1', 'active');
    updateProgress(1);
    
    try {
        // Add cache-busting to prevent webview caching issues
        const timestamp = Date.now();
        const response = await fetch(`/device_status?_t=${timestamp}`, {
            method: 'GET',
            headers: {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        });
        const result = await response.json();
        
        if (result.success && result.serial) {
            // Check model match
            if (!checkModelMatch(result.serial)) {
                const detectedModel = result.serial.substring(0, result.serial.lastIndexOf('-'));
                alert(`⚠️ РАБОТА ОСТАНОВЛЕНА!\n\nПодключена модель: ${detectedModel}\nВыбрана модель: ${selectedModel}\n\nОтключите устройство!`);
                showStatus(`❌ ОШИБКА: Подключена модель ${detectedModel}, но выбрана ${selectedModel}!`, 'error');
                updateStepState('step1', 'pending');
                updateProgress(0);
                return;
            }
            
            deviceSerial = result.serial;
            document.getElementById('deviceSerial').textContent = deviceSerial;
            
            // Mark step 1 as completed
            updateStepState('step1', 'completed');
            document.querySelector('#step1 .step-description').textContent = 'Устройство успешно подключено';
            
            // Automatically start step 2 validation
            updateStepState('step2', 'active');
            updateProgress(2);
            
            // Show device status information
            document.getElementById('deviceStatusBox').style.display = 'block';
            
            // Update device status display
            document.getElementById('serialValue').textContent = result.serial || 'Error';
            document.getElementById('testsValue').textContent = result.tests_ok;
            document.getElementById('calibValue').textContent = result.calibration_ok;
            document.getElementById('statusValue').textContent = result.status;
            
            // Check validation parameters
            const testsOk = result.tests_ok === 1;
            const calibOk = result.calibration_ok === 1;
            const progTimeOk = result.prog_time > 0;
            const calibTimeOk = result.calib_time > 0;
            
            // Update validation icons
            document.getElementById('serialIcon').textContent = result.serial ? '✅' : '❌';
            document.getElementById('testsIcon').textContent = testsOk ? '✅' : '❌';
            document.getElementById('calibIcon').textContent = calibOk ? '✅' : '❌';
            
            // Determine device readiness
            let isReady = false;
            if (deviceValidationEnabled) {
                isReady = testsOk && calibOk && progTimeOk && calibTimeOk;
            } else {
                isReady = result.serial && result.serial !== 'Error';
            }
            
            document.getElementById('statusIcon').textContent = isReady ? '✅' : '❌';
            
            if (isReady) {
                // Device is ready for printing
                deviceReady = true;
                updateStepState('step2', 'completed');
                document.querySelector('#step2 .step-description').textContent = 'Устройство верифицировано и готово';
                
                // Enable manual printing step
                document.getElementById('printBtn').disabled = false;
                updateStepState('step3', 'active');
                updateProgress(3);
                updatePrintButtonText();
                
                const modeText = deviceValidationEnabled ? '' : ' (тестовый режим)';
                showStatus(`✅ Устройство прошло проверку и готово к печати${modeText}`, 'success');
            } else {
                // Device validation failed
                deviceReady = false;
                updateStepState('step2', 'pending');
                updateProgress(2);
                
                // Build error message
                let errorMsg = 'Устройство не готово: ';
                if (!result.serial || result.serial === 'Error') {
                    errorMsg += 'Серийный номер не получен. ';
                }
                if (!testsOk) errorMsg += 'Tests не пройдены. ';
                if (deviceValidationEnabled) {
                    if (!calibOk) errorMsg += 'Калибровка не выполнена. ';
                    if (!progTimeOk) errorMsg += 'Программирование не выполнено. ';
                    if (!calibTimeOk) errorMsg += 'Время калибровки не установлено. ';
                }
                
                showStatus('❌ ' + errorMsg, 'error');
                
                // Offer to check device in diagnostic tool
                setTimeout(() => {
                    if (confirm(`⚠️ Устройство не прошло проверки!\n\nСерийный номер: ${result.serial}\n\nОткрыть диагностику устройства?`)) {
                        window.open(`http://192.168.88.132:5000/?serial=${encodeURIComponent(result.serial)}`, '_blank');
                    }
                }, 500);
            }
            
        } else {
            // Device connection failed
            updateStepState('step1', 'pending');
            updateProgress(0);
            showStatus('❌ Ошибка подключения устройства: ' + (result.message || 'Неизвестная ошибка'), 'error');
        }
    } catch (error) {
        updateStepState('step1', 'pending');
        updateProgress(0);
        showStatus('❌ Ошибка соединения с сервером', 'error');
    }
}

async function printLabel() {
    if (autoModeEnabled) {
        showStatus('Отключите автоматический режим для ручного управления', 'error');
        return;
    }
    
    if (!deviceReady || !deviceSerial) {
        showStatus('❌ Устройство не готово к печати', 'error');
        return;
    }

    const printBtn = document.getElementById('printBtn');
    printBtn.disabled = true;
    printBtn.innerHTML = '⏳ Печать...';

    try {
        const response = await fetch('/print_label', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                serial_number: deviceSerial,
            })
        });

        const result = await response.json();

        if (result.success) {
            updateStepState('step3', 'completed');
            document.querySelector('#step3 .step-description').textContent = 'Этикетка успешно напечатана';
            
            // Enable step 4
            updateStepState('step4', 'active');
            updateProgress(4);
            
            // Show scan section
            currentPrintedBarcode = deviceSerial;
            document.getElementById('scanContent').style.display = 'block';
            document.getElementById('scanBarcode').textContent = `Ожидание сканирования: ${deviceSerial}`;
            
            // Start automatic scan checking
            startScanChecking();
            
            showStatus('✅ ' + result.message, 'success');
        } else {
            printBtn.disabled = false;
            updatePrintButtonText();
            showStatus('❌ ' + result.message, 'error');
        }
    } catch (error) {
        printBtn.disabled = false;
        updatePrintButtonText();
        showStatus('❌ Ошибка соединения с сервером', 'error');
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
            if (result.scanned && result.status === 'ready') {
                showStatus(`✅ Этикетка ${currentPrintedBarcode} отсканирована (статус: ${result.status})`, 'success');
                document.getElementById('scanBarcode').innerHTML = `
                    ✅ <strong>ОТСКАНИРОВАНО!</strong><br>
                    ${currentPrintedBarcode}<br>
                    <small>Статус: ${result.status}</small>
                `;
            } else if (result.scanned && result.status !== 'ready') {
                showStatus(`ℹ️ Этикетка отсканирована, но статус "${result.status}" - ожидание статуса "ready"`, 'error');
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
            const statsContainer = document.getElementById('scanStats');
            const statsBlock = document.getElementById('statsBlock');
            
            // Calculate statistics
            const now = new Date();
            const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
            
            let todayCount = 0;
            let todayByModel = {};
            
            result.items.forEach(item => {
                // Extract model from barcode (e.g., "RC-102" from "RC-102-012385")
                const model = item.barcode.substring(0, item.barcode.lastIndexOf('-'));
                
                // Check if item is from today
                if (item.timestamp) {
                    try {
                        const itemDate = new Date(item.timestamp + 'Z');
                        if (itemDate >= todayStart) {
                            todayCount++;
                            
                            if (!todayByModel[model]) {
                                todayByModel[model] = 0;
                            }
                            todayByModel[model]++;
                        }
                    } catch (e) {
                        console.error('Error parsing timestamp:', e);
                    }
                }
            });
            
            // Build statistics HTML - only today
            let statsHTML = '<div style="margin-top: 12px;">';
            
            statsHTML += '<div style="background: rgba(0, 212, 255, 0.1); border: 1px solid rgba(0, 212, 255, 0.25); border-radius: 12px; padding: 16px;">';
            statsHTML += '<div style="font-weight: bold; font-size: 16px; margin-bottom: 12px; color: #00d4ff;">🗓️ Сегодня изготовлено:</div>';
            
            if (todayCount > 0) {
                statsHTML += `<div style="display: flex; justify-content: space-between; padding: 10px; background: rgba(255, 215, 0, 0.15); border-radius: 8px; margin-bottom: 8px; font-weight: bold; font-size: 18px;">
                    <span>Всего:</span><span style="color: #ffd700;">${todayCount}</span>
                </div>`;
                
                const sortedTodayModels = Object.keys(todayByModel).sort();
                sortedTodayModels.forEach(model => {
                    const count = todayByModel[model];
                    statsHTML += `<div style="display: flex; justify-content: space-between; padding: 8px 10px; background: rgba(255, 255, 255, 0.05); border-radius: 8px; margin-bottom: 5px;">
                        <span>${model}:</span><span style="color: #00d4ff; font-weight: bold;">${count}</span>
                    </div>`;
                });
            } else {
                statsHTML += '<div style="text-align: center; color: #8899aa;">Нет записей за сегодня</div>';
            }
            statsHTML += '</div>';
            statsHTML += '</div>';
            
            // Display statistics
            if (statsContainer && statsBlock) {
                statsContainer.innerHTML = statsHTML;
                statsBlock.style.display = 'flex';
            }
            
            // Build numbered items list
            itemsList.innerHTML = result.items.map((item, index) => {
                let localTime = 'Unknown';
                
                if (item.timestamp) {
                    try {
                        // get local time from UTC ISO string
                        const date = new Date(item.timestamp + 'Z'); // Append 'Z' to indicate UTC
                        if (!isNaN(date.getTime())) {
                            localTime = date.toLocaleString('ru-RU', {
                                day: '2-digit',
                                month: '2-digit',
                                year: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                            });
                        }
                    } catch (e) {
                        console.error('Error parsing timestamp:', e);
                    }
                }
                
                return `
                    <div class="scanned-item">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <div style="min-width: 30px; height: 30px; background: rgba(0, 212, 255, 0.2); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; color: #00d4ff; font-size: 14px;">
                                ${index + 1}
                            </div>
                            <div>
                                <div class="barcode-text">${item.barcode}</div>
                                <div class="timestamp">${localTime}</div>
                            </div>
                        </div>
                        <div class="status-badge status-${item.status}">${item.status.toUpperCase()}</div>
                    </div>
                `;
            }).join('');
            
            scannedItems.style.display = 'block';
        } else {
            document.getElementById('scannedItems').style.display = 'none';
            const statsBlock = document.getElementById('statsBlock');
            if (statsBlock) {
                statsBlock.style.display = 'none';
            }
        }
    } catch (error) {
        console.error('Error loading scanned items:', error);
    }
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

// Auto-refresh scanned items every 5 minutes
setInterval(loadScannedItems, 300000); // 300,000 ms = 5 minutes