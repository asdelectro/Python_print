# Упрощенная версия print_labels.py - с Data Matrix вместо QR
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing
from PyPDF2 import PdfReader, PdfWriter
import io
import win32print
import win32ui
from PIL import Image, ImageWin
import fitz
import logging
import os
import psycopg2
import socket
from datetime import datetime

# Data Matrix импорт
try:
    from pylibdmtx import pylibdmtx
    DATAMATRIX_AVAILABLE = True
except ImportError:
    print("Warning: Data Matrix недоступен")
    DATAMATRIX_AVAILABLE = False

class LabelPrinter:
    def __init__(self, enable_logging=True, temp_filename="temp_label.pdf",
                 db_host='192.168.88.132', db_port=5432, db_name='production_db',
                 db_user='emqx_user', db_password='zxtbd'):
        
        # Label position settings
        self.label_x_mm = 27
        self.label_y_mm = 13.3
        self.label_font_size = 6
        
        # Data Matrix settings (заменили QR)
        self.dm_x_mm = 19
        self.dm_y_mm = 2
        self.dm_size_mm = 5
        self.dm_pixels = 300  # Высокое разрешение для печати
        
        # Print settings
        self.print_scale = 1.0
        self.printer_name = "TSC TE300"
        self.print_dpi = 300
        
        # Print margins
        self.print_offset_x = 0
        self.print_offset_y = -20
        self.print_width = None
        self.print_height = None
        
        # Database settings
        self.db_config = {
            'host': db_host,
            'port': db_port,
            'database': db_name,
            'user': db_user,
            'password': db_password
        }
        
        # Get computer name for station_id
        self.station_id = socket.gethostname()
        
        # Logging and file settings
        self.enable_logging = enable_logging
        self.temp_filename = temp_filename
        
        # Configure simple logging
        if self.enable_logging:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s'
            )
            self.logger = logging.getLogger(__name__)
            self.logger.info(f"LabelPrinter initialized (Station: {self.station_id})")
        else:
            class NullLogger:
                def debug(self, msg): pass
                def info(self, msg): pass
                def warning(self, msg): pass
                def error(self, msg): pass
            self.logger = NullLogger()
    
    def get_db_connection(self):
        """Подключение к PostgreSQL"""
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except Exception as e:
            self.logger.error(f"Ошибка подключения к БД: {e}")
            return None
    
    def save_device_to_db(self, barcode: str):
        """Сохранение устройства в БД со статусом preready"""
        try:
            self.logger.info(f"Сохранение в БД: {barcode}")
            
            conn = self.get_db_connection()
            if not conn:
                raise Exception("Не удалось подключиться к базе данных")
            
            try:
                with conn.cursor() as cursor:
                    sql = """
                    INSERT INTO ready_devices (barcode, scanner_id, scan_timestamp, station_id, status)
                    VALUES (%s, %s, NOW(), %s, %s)
                    ON CONFLICT (barcode)
                    DO UPDATE SET
                        scan_timestamp = NOW(),
                        updated_at = NOW(),
                        scanner_id = EXCLUDED.scanner_id,
                        station_id = EXCLUDED.station_id,
                        status = EXCLUDED.status
                    RETURNING id;
                    """
                    
                    cursor.execute(sql, (barcode, 'print_label', self.station_id, 'preready'))
                    result = cursor.fetchone()
                    conn.commit()
                    
                    if result:
                        self.logger.info(f"Успешно сохранено в БД: {barcode}")
                        return True
                    else:
                        raise Exception("Не получен результат от БД")
                        
            except Exception as db_error:
                conn.rollback()
                self.logger.error(f"Ошибка SQL: {db_error}")
                raise
            finally:
                conn.close()
                
        except Exception as e:
            self.logger.error(f"Ошибка сохранения в БД: {e}")
            return False
    
    def create_datamatrix_image(self, data: str, size_pixels: int = None):
        """Создание Data Matrix изображения"""
        if not DATAMATRIX_AVAILABLE:
            self.logger.warning("Data Matrix недоступен")
            return None
        
        if size_pixels is None:
            size_pixels = self.dm_pixels
            
        try:
            # Генерируем Data Matrix
            encoded = pylibdmtx.encode(data.encode('utf-8'))
            
            if encoded:
                # Конвертируем в изображение
                dm_img = Image.frombytes('RGB', (encoded.width, encoded.height), encoded.pixels)
                
                # Масштабируем до нужного размера
                dm_img = dm_img.resize((size_pixels, size_pixels), Image.NEAREST)
                
                return dm_img
            else:
                print("Ошибка создания Data Matrix")
                return None
                
        except Exception as e:
            self.logger.error(f"Ошибка создания Data Matrix: {e}")
            return None
    
    def add_datamatrix_to_canvas(self, canvas_obj, data: str, x_mm: float, y_mm: float, size_mm: float):
        """Добавление Data Matrix на canvas"""
        try:
            # Создаем изображение Data Matrix
            pixels_per_mm = self.print_dpi / 25.4  # Конвертация DPI в пиксели на мм
            size_pixels = int(size_mm * pixels_per_mm)
            
            dm_img = self.create_datamatrix_image(data, size_pixels)
            if dm_img is None:
                return False
            
            # Сохраняем временное изображение
            temp_dm_path = "temp_datamatrix.png"
            dm_img.save(temp_dm_path)
            
            # Добавляем на canvas
            canvas_obj.drawImage(
                temp_dm_path,
                x_mm * mm,
                y_mm * mm,
                width=size_mm * mm,
                height=size_mm * mm,
                preserveAspectRatio=True
            )
            
            # Удаляем временный файл
            try:
                os.remove(temp_dm_path)
            except:
                pass
            
            self.logger.info(f"Data Matrix добавлен на позицию ({x_mm}, {y_mm})")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка добавления Data Matrix: {e}")
            return False
    
    def create_label(self, serial_number: str, template_pdf: str, output_pdf: str = None, add_datamatrix=True):
        """Создание этикетки с серийным номером и Data Matrix"""
        if output_pdf is None:
            output_pdf = self.temp_filename
            
        self.logger.info(f"Создание этикетки: {serial_number}")
        
        # Удаляем существующий файл
        if os.path.exists(output_pdf):
            try:
                os.remove(output_pdf)
            except Exception as e:
                self.logger.error(f"Не удалось удалить файл {output_pdf}: {e}")
        
        # Размеры шаблона - 2.00" x 1.00" (50,8 mm x 25,4 mm)
        template_width = 50.8 * mm
        template_height = 25.4 * mm
        
        # Создаем PDF в памяти
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=(template_width, template_height))
        
        # Добавляем серийный номер
        c.setFont("Helvetica-Bold", self.label_font_size)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(self.label_x_mm * mm, self.label_y_mm * mm, serial_number)
        
        # Добавляем Data Matrix
        if add_datamatrix:
            if self.add_datamatrix_to_canvas(c, serial_number, self.dm_x_mm, self.dm_y_mm, self.dm_size_mm):
                self.logger.info("Data Matrix добавлен на этикетку")
            else:
                self.logger.warning("Data Matrix не создан")
        
        c.save()
        packet.seek(0)
        
        # Объединяем с шаблоном
        try:
            new_pdf = PdfReader(packet)
            template = PdfReader(template_pdf)
            page = template.pages[0]
            page.merge_page(new_pdf.pages[0])
            
            writer = PdfWriter()
            writer.add_page(page)
            with open(output_pdf, "wb") as f:
                writer.write(f)
            
            self.logger.info(f"Этикетка создана: {output_pdf}")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка создания этикетки: {e}")
            return False
    
    def pdf_to_image(self, pdf_path: str):
        """Конвертация PDF в изображение"""
        try:
            pdf_document = fitz.open(pdf_path)
            page = pdf_document[0]
            mat = fitz.Matrix(self.print_dpi / 72, self.print_dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("ppm")
            image = Image.open(io.BytesIO(img_data))
            pdf_document.close()
            return image
        except Exception as e:
            self.logger.error(f"Ошибка конвертации PDF: {e}")
            return None
    
    def print_label(self, pdf_path: str = None, printer_name: str = None, scale: float = None):
        """Печать этикетки"""
        if pdf_path is None:
            pdf_path = self.temp_filename
        if printer_name is None:
            printer_name = self.printer_name
        if scale is None:
            scale = self.print_scale
        
        self.logger.info(f"Печать: {pdf_path}")
        
        try:
            # Конвертируем в изображение
            image = self.pdf_to_image(pdf_path)
            if image is None:
                return False
            
            # Масштабирование
            if scale != 1.0:
                original_width, original_height = image.size
                new_width = int(original_width * scale)
                new_height = int(original_height * scale)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Печать
            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(printer_name)
            hdc.StartDoc("Label Print")
            hdc.StartPage()
            
            dib = ImageWin.Dib(image)
            width = self.print_width or image.size[0]
            height = self.print_height or image.size[1]
            x, y = self.print_offset_x, self.print_offset_y
            
            dib.draw(hdc.GetHandleOutput(), (x, y, x + width, y + height))
            
            hdc.EndPage()
            hdc.EndDoc()
            hdc.DeleteDC()
            
            self.logger.info("Печать завершена")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка печати: {e}")
            return False
    
    def create_and_print_label(self, serial_number: str, template_pdf: str, 
                             output_pdf: str = None, add_datamatrix=True,
                             print_after_create=True, printer_name: str = None, 
                             scale: float = None):
        """Создание и печать этикетки с Data Matrix и записью в БД"""
        if output_pdf is None:
            output_pdf = self.temp_filename
        
        self.logger.info(f"Обработка этикетки: {serial_number}")
        
        try:
            # Сохраняем в БД
            if not self.save_device_to_db(serial_number):
                raise Exception("Ошибка записи в базу данных")
            
            # Создаем этикетку
            if not self.create_label(serial_number, template_pdf, output_pdf, add_datamatrix):
                raise Exception("Ошибка создания этикетки")
            
            # Печатаем если нужно
            if print_after_create:
                if self.print_label(output_pdf, printer_name, scale):
                    self.logger.info(f"Этикетка {serial_number} напечатана и записана в БД")
                    return True
                else:
                    self.logger.error(f"Ошибка печати {serial_number}")
                    return False
            else:
                self.logger.info(f"Этикетка {serial_number} создана и записана в БД")
                return True
                
        except Exception as e:
            self.logger.error(f"Ошибка обработки {serial_number}: {e}")
            return False
    
    def get_available_printers(self):
        """Получение списка доступных принтеров"""
        try:
            printers = []
            for printer in win32print.EnumPrinters(2):
                printers.append(printer[2])
            return printers
        except Exception as e:
            self.logger.error(f"Ошибка получения принтеров: {e}")
            return []
    
    def test_db_connection(self):
        """Тест подключения к БД"""
        try:
            conn = self.get_db_connection()
            if conn:
                conn.close()
                self.logger.info("Подключение к БД успешно")
                return True
            else:
                self.logger.error("Ошибка подключения к БД")
                return False
        except Exception as e:
            self.logger.error(f"Тест БД провален: {e}")
            return False
    
    def test_datamatrix(self, test_data: str = "TEST-123"):
        """Тест создания Data Matrix"""
        try:
            img = self.create_datamatrix_image(test_data, 200)
            if img:
                img.save("test_datamatrix.png")
                self.logger.info(f"Тест Data Matrix успешен: test_datamatrix.png")
                return True
            else:
                self.logger.error("Ошибка создания тестового Data Matrix")
                return False
        except Exception as e:
            self.logger.error(f"Ошибка тестирования Data Matrix: {e}")
            return False

# Простой тест
if __name__ == "__main__":
    printer = LabelPrinter(enable_logging=True)
    
    # Тест Data Matrix
    print("Тестирование Data Matrix...")
    if printer.test_datamatrix("RC103-12323232"):
        print("Data Matrix работает")
    
    if printer.test_db_connection():
        print("База данных доступна")
    
    # Создать и напечатать этикетку (тестирование без печати)
    result = printer.create_and_print_label(
        "RC103-12323232", 
        "templ_103.pdf",
        output_pdf="web_label.pdf",  # Сохранить как web_label.pdf
        print_after_create=True,    # Не печатать, только создать PDF
        add_datamatrix=True
    )
    
    print(f"Результат: {result}")