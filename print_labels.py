# Simplified label printer with Data Matrix instead of QR
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
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
import re
import win32api

# Data Matrix import
try:
    from pylibdmtx import pylibdmtx

    DATAMATRIX_AVAILABLE = True
except ImportError:
    print("Warning: Data Matrix not available")
    DATAMATRIX_AVAILABLE = False


class LabelPrinter:
    def __init__(
        self,
        enable_logging=True,
        temp_filename="temp_label.pdf",
        db_host="192.168.88.132",
        db_port=5432,
        db_name="production_db",
        db_user="emqx_user",
        db_password="zxtbd",
    ):

        # Label position settings
        self.serialLabel_x_mm = 33.55
        self.serialLabel_y_mm = 16.85
        self.serialLabel_font_size = 6

        # Type
        self.typeLabel_x_mm = 2
        self.typeLabel_y_mm = 19
        self.typeLabel_font_size = 4

        # FCC
        self.fccLabel_x_mm = 25
        self.fccLabel_y_mm = 2

        # power parametrs labels
        self.powerLabels_font_size = 4

        self.powerULabel_x_mm = 23.5
        self.powerULabel_y_mm = 13.1

        self.powerALabel_x_mm = 34.5
        self.powerALabel_y_mm = 13.1

        self.powerWLabel_x_mm = 44.4
        self.powerWLabel_y_mm = 13.1

        self.powerILabel_x_mm = 23.5
        self.powerILabel_y_mm = 11.2

        self.powermAhLabel_x_mm = 33.2
        self.powermAhLabel_y_mm = 11.2

        self.powerWhLabel_x_mm = 44.1
        self.powerWhLabel_y_mm = 11.2

        # Data Matrix settings
        self.dm_x_mm = 18
        self.dm_y_mm = 4.1
        self.dm_size_mm = 5
        self.dm_pixels = 300  # High resolution for printing

        # Print settings
        self.print_scale = 0.5
        self.printer_name = "TSC TE300"
        self.print_dpi = 600

        # Print margins
        self.print_offset_x = 1
        self.print_offset_y = 5
        self.print_width = None
        self.print_height = None

        # Database settings
        self.db_config = {
            "host": db_host,
            "port": db_port,
            "database": db_name,
            "user": db_user,
            "password": db_password,
        }

        # Get computer name for station_id
        self.station_id = socket.gethostname()

        # Logging settings
        self.enable_logging = enable_logging
        self.temp_filename = temp_filename

        # Configure logging
        if self.enable_logging:
            logging.basicConfig(
                level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
            )
            self.logger = logging.getLogger(__name__)
            self.logger.info(f"LabelPrinter initialized (Station: {self.station_id})")
        else:

            class NullLogger:
                def debug(self, msg):
                    pass

                def info(self, msg):
                    pass

                def warning(self, msg):
                    pass

                def error(self, msg):
                    pass

            self.logger = NullLogger()

    def get_db_connection(self):
        """Connect to PostgreSQL database"""
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except Exception as e:
            self.logger.error(f"Database connection error: {e}")
            return None

    def save_device_to_db(self, barcode: str):
        """Save device to database with preready status"""
        try:
            self.logger.info(f"Saving to database: {barcode}")

            conn = self.get_db_connection()
            if not conn:
                raise Exception("Failed to connect to database")

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

                    cursor.execute(
                        sql, (barcode, "print_label", self.station_id, "preready")
                    )
                    result = cursor.fetchone()
                    conn.commit()

                    if result:
                        self.logger.info(f"Successfully saved to database: {barcode}")
                        return True
                    else:
                        raise Exception("No result from database")

            except Exception as db_error:
                conn.rollback()
                self.logger.error(f"SQL error: {db_error}")
                raise
            finally:
                conn.close()

        except Exception as e:
            self.logger.error(f"Database save error: {e}")
            return False

    def create_datamatrix_image(self, data: str, size_pixels: int = None):
        """Create Data Matrix image"""
        if not DATAMATRIX_AVAILABLE:
            self.logger.warning("Data Matrix not available")
            return None

        if size_pixels is None:
            size_pixels = self.dm_pixels

        try:
            # Generate Data Matrix
            encoded = pylibdmtx.encode(data.encode("utf-8"))

            if encoded:
                # Convert to image
                dm_img = Image.frombytes(
                    "RGB", (encoded.width, encoded.height), encoded.pixels
                )

                # Scale to required size
                dm_img = dm_img.resize((size_pixels, size_pixels), Image.NEAREST)

                return dm_img
            else:
                print("Error creating Data Matrix")
                return None

        except Exception as e:
            self.logger.error(f"Data Matrix creation error: {e}")
            return None

    def add_datamatrix_to_canvas(
        self, canvas_obj, data: str, x_mm: float, y_mm: float, size_mm: float
    ):
        """Add Data Matrix to canvas"""
        try:
            # Create Data Matrix image
            pixels_per_mm = self.print_dpi / 25.4  # Convert DPI to pixels per mm
            size_pixels = int(size_mm * pixels_per_mm)

            dm_img = self.create_datamatrix_image(data, size_pixels)
            if dm_img is None:
                return False

            # Save temporary image
            temp_dm_path = "temp_datamatrix.png"
            dm_img.save(temp_dm_path)

            # Add to canvas
            canvas_obj.drawImage(
                temp_dm_path,
                x_mm * mm,
                y_mm * mm,
                width=size_mm * mm,
                height=size_mm * mm,
                preserveAspectRatio=True,
            )

            # Remove temporary file
            try:
                os.remove(temp_dm_path)
            except:
                pass

            self.logger.info(f"Data Matrix added at position ({x_mm}, {y_mm})")
            return True

        except Exception as e:
            self.logger.error(f"Error adding Data Matrix: {e}")
            return False

    def _Create102Label(self, c, serial_number):
        # Add serial number
        c.setFont("Helvetica-Bold", self.serialLabel_font_size)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(
            self.serialLabel_x_mm * mm, self.serialLabel_y_mm * mm, serial_number
        )

        # Add type label
        c.setFont("Helvetica-Bold", self.typeLabel_font_size)
        c.drawString(
            self.typeLabel_x_mm * mm, self.typeLabel_y_mm * mm, "Type RADIACODE-102"
        )

        # Add FCC label
        c.setFont("Helvetica-Bold", self.powerLabels_font_size)
        c.drawString(
            self.fccLabel_x_mm * mm, self.fccLabel_y_mm * mm, "FCC ID: 2BDDP-102"
        )

        # Add power labels
        c.drawString(self.powerULabel_x_mm * mm, self.powerULabel_y_mm * mm, "5.0 V")
        c.drawString(self.powerILabel_x_mm * mm, self.powerILabel_y_mm * mm, "3.7 V")
        c.drawString(self.powerALabel_x_mm * mm, self.powerALabel_y_mm * mm, "0.5 A")
        c.drawString(self.powerWLabel_x_mm * mm, self.powerWLabel_y_mm * mm, "2.5 W")
        c.drawString(
            self.powermAhLabel_x_mm * mm, self.powermAhLabel_y_mm * mm, "1000 mAh"
        )
        c.drawString(self.powerWhLabel_x_mm * mm, self.powerWhLabel_y_mm * mm, "3.7 Wh")

    def _Create103Label(self, c, serial_number):
        # Add serial number
        c.setFont("Helvetica-Bold", self.serialLabel_font_size)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(
            self.serialLabel_x_mm * mm, self.serialLabel_y_mm * mm, serial_number
        )
        # Add type label
        c.setFont("Helvetica-Bold", self.typeLabel_font_size)
        c.drawString(
            self.typeLabel_x_mm * mm, self.typeLabel_y_mm * mm, "Type RADIACODE-103"
        )

        # Add FCC label
        c.setFont("Helvetica-Bold", self.powerLabels_font_size)
        c.drawString(
            self.fccLabel_x_mm * mm, self.fccLabel_y_mm * mm, "FCC ID: 2BDDP-103"
        )

        # Add power labels
        c.drawString(self.powerULabel_x_mm * mm, self.powerULabel_y_mm * mm, "5.0 V")
        c.drawString(self.powerILabel_x_mm * mm, self.powerILabel_y_mm * mm, "3.7 V")
        c.drawString(self.powerALabel_x_mm * mm, self.powerALabel_y_mm * mm, "0.5 A")
        c.drawString(self.powerWLabel_x_mm * mm, self.powerWLabel_y_mm * mm, "2.5 W")
        c.drawString(
            self.powermAhLabel_x_mm * mm, self.powermAhLabel_y_mm * mm, "1000 mAh"
        )
        c.drawString(self.powerWhLabel_x_mm * mm, self.powerWhLabel_y_mm * mm, "3.7 Wh")
        # ...

    def _Create103GLabel(self, c, serial_number):
        """Создание этикетки для RC-103G"""
        # Add serial number
        c.setFont("Helvetica-Bold", self.serialLabel_font_size)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(
            self.serialLabel_x_mm * mm, self.serialLabel_y_mm * mm, serial_number
        )

        # Add type label
        c.setFont("Helvetica-Bold", self.typeLabel_font_size)
        c.drawString(
            self.typeLabel_x_mm * mm, self.typeLabel_y_mm * mm, "Type RADIACODE-103G"
        )

        # Add FCC label
        c.setFont("Helvetica-Bold", self.powerLabels_font_size)
        c.drawString(
            self.fccLabel_x_mm * mm, self.fccLabel_y_mm * mm, "FCC ID: 2BDDP-103"
        )

        # Add power labels
        c.drawString(self.powerULabel_x_mm * mm, self.powerULabel_y_mm * mm, "5.0 V")
        c.drawString(self.powerILabel_x_mm * mm, self.powerILabel_y_mm * mm, "3.7 V")
        c.drawString(self.powerALabel_x_mm * mm, self.powerALabel_y_mm * mm, "0.5 A")
        c.drawString(self.powerWLabel_x_mm * mm, self.powerWLabel_y_mm * mm, "2.5 W")
        c.drawString(
            self.powermAhLabel_x_mm * mm, self.powermAhLabel_y_mm * mm, "1000 mAh"
        )
        c.drawString(self.powerWhLabel_x_mm * mm, self.powerWhLabel_y_mm * mm, "3.7 Wh")
        # ...

    def _Create110Label(self, c, serial_number):
        """Создание этикетки для RC-110"""
        # Add serial number
        c.setFont("Helvetica-Bold", self.serialLabel_font_size)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(
            self.serialLabel_x_mm * mm, self.serialLabel_y_mm * mm, serial_number
        )

        # Add type label
        c.setFont("Helvetica-Bold", self.typeLabel_font_size)
        c.drawString(
            self.typeLabel_x_mm * mm, self.typeLabel_y_mm * mm, "Type RADIACODE-110"
        )

        # Add FCC label
        c.setFont("Helvetica-Bold", self.powerLabels_font_size)
        c.drawString(
            self.fccLabel_x_mm * mm, self.fccLabel_y_mm * mm, "FCC ID: 2BDDP-110"
        )

        # Add power labels
        c.drawString(self.powerULabel_x_mm * mm, self.powerULabel_y_mm * mm, "5.0 V")
        c.drawString(self.powerILabel_x_mm * mm, self.powerILabel_y_mm * mm, "3.7 V")
        c.drawString(self.powerALabel_x_mm * mm, self.powerALabel_y_mm * mm, "0.8 A")
        c.drawString(self.powerWLabel_x_mm * mm, self.powerWLabel_y_mm * mm, "4.0 W")
        c.drawString(
            self.powermAhLabel_x_mm * mm, self.powermAhLabel_y_mm * mm, "1500 mAh"
        )
        c.drawString(
            self.powerWhLabel_x_mm * mm, self.powerWhLabel_y_mm * mm, "5.55 Wh"
        )

    def _validate_serial_number(self, serial_number: str) -> str:
        patterns = {
            "RC-102": r"^RC-102-\d{6}$",
            "RC-103": r"^RC-103-\d{6}$",
            "RC-103G": r"^RC-103G-\d{6}$",
            "RC-110": r"^RC-110-\d{6}$",
        }

        for device_type, pattern in patterns.items():
            if re.match(pattern, serial_number):
                return device_type

        raise ValueError(
            f"Неверный формат серийного номера: {serial_number}. "
            f"Ожидается формат: RC-XXX-XXXXXX или RC-XXXG-XXXXXX"
        )

    def create_label(
        self,
        serial_number: str,
        template_pdf: str,
        output_pdf: str = None,
        add_datamatrix=True,
    ):
        """Create label with serial number and Data Matrix"""
        if output_pdf is None:
            output_pdf = self.temp_filename

        self.logger.info(f"Creating label: {serial_number}")

        # Remove existing file
        if os.path.exists(output_pdf):
            try:
                os.remove(output_pdf)
            except Exception as e:
                self.logger.error(f"Could not delete file {output_pdf}: {e}")

        # Template dimensions
        template_width = 51 * mm
        template_height = 25 * mm

        # Validate serial number and get device type
        try:
            device_type = self._validate_serial_number(serial_number)
        except ValueError as e:
            self.logger.error(str(e))
            return False

        # Create PDF in memory
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=(template_width, template_height))

        # Select label creation function based on device type
        try:
            if device_type == "RC-102":
                self._Create102Label(c, serial_number)
            elif device_type == "RC-103":
                self._Create103Label(c, serial_number)
            elif device_type == "RC-103G":
                self._Create103GLabel(c, serial_number)
            elif device_type == "RC-110":
                self._Create110Label(c, serial_number)
        except Exception as e:
            self.logger.error(f"Error creating label for {device_type}: {e}")
            return False

        # Add Data Matrix
        if add_datamatrix:
            if self.add_datamatrix_to_canvas(
                c, serial_number, self.dm_x_mm, self.dm_y_mm, self.dm_size_mm
            ):
                self.logger.info("Data Matrix added to label")
            else:
                self.logger.warning("Data Matrix not created")

        c.save()
        packet.seek(0)

        # Merge with template
        try:
            new_pdf = PdfReader(packet)
            template = PdfReader(template_pdf)
            page = template.pages[0]
            page.merge_page(new_pdf.pages[0])

            writer = PdfWriter()
            writer.add_page(page)
            with open(output_pdf, "wb") as f:
                writer.write(f)

            self.logger.info(f"Label created: {output_pdf}")
            return True
        except Exception as e:
            self.logger.error(f"Label creation error: {e}")
            return False

    def pdf_to_image(self, pdf_path: str):
        """Convert PDF to image"""
        try:
            pdf_document = fitz.open(pdf_path)
            page = pdf_document[0]
            mat = fitz.Matrix(self.print_dpi / 72, self.print_dpi / 72)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))

            # Сохраняем в BMP (без сжатия)
            temp_bmp = "temp_uncompressed.bmp"
            image.save(temp_bmp, "BMP")
            image = Image.open(temp_bmp)

            # Удаляем временный файл
            try:
                os.remove(temp_bmp)
            except:
                pass

            pdf_document.close()
            return image
        except Exception as e:
            self.logger.error(f"PDF conversion error: {e}")
            return None

    def print_pdf_directly(self, pdf_path: str, printer_name: str = None):
        """Print PDF directly without conversion"""
        if printer_name is None:
            printer_name = self.printer_name

        try:
            win32api.ShellExecute(0, "print", pdf_path, f'/d:"{printer_name}"', ".", 0)
            self.logger.info("PDF printed directly")
            return True
        except Exception as e:
            self.logger.error(f"Direct PDF printing error: {e}")
            return False

    def print_label(
        self, pdf_path: str = None, printer_name: str = None, scale: float = None
    ):
        """Print label"""
        if pdf_path is None:
            pdf_path = self.temp_filename
        if printer_name is None:
            printer_name = self.printer_name
        if scale is None:
            scale = self.print_scale

        self.logger.info(f"Printing: {pdf_path}")

        try:
            # Convert to image
            image = self.pdf_to_image(pdf_path)
            if image is None:
                return False

            # Scale image
            if scale != 1.0:
                original_width, original_height = image.size
                new_width = int(original_width * scale)
                new_height = int(original_height * scale)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Print
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

            self.logger.info("Printing completed")
            return True
        except Exception as e:
            self.logger.error(f"Printing error: {e}")
            return False

    def create_and_print_label(
        self,
        serial_number: str,
        template_pdf: str,
        output_pdf: str = None,
        add_datamatrix=True,
        print_after_create=True,
        printer_name: str = None,
        scale: float = None,
    ):
        """Create and print label with Data Matrix and save to database"""
        if output_pdf is None:
            output_pdf = self.temp_filename

        self.logger.info(f"Processing label: {serial_number}")

        try:
            # Save to database
            if not self.save_device_to_db(serial_number):
                raise Exception("Database save error")

            # Create label
            if not self.create_label(
                serial_number, template_pdf, output_pdf, add_datamatrix
            ):
                raise Exception("Label creation error")

            # Print if needed
            if print_after_create:
                if self.print_label(output_pdf, printer_name, scale):
                    self.logger.info(
                        f"Label {serial_number} printed and saved to database"
                    )
                    return True
                else:
                    self.logger.error(f"Printing error for {serial_number}")
                    return False
            else:
                self.logger.info(f"Label {serial_number} created and saved to database")
                return True

        except Exception as e:
            self.logger.error(f"Processing error for {serial_number}: {e}")
            return False


# Simple test
if __name__ == "__main__":
    printer = LabelPrinter(enable_logging=True)

    # Test Data Matrix
    print("Testing Data Matrix...")

    # Create and print label (test without actual printing)
    result = printer.create_and_print_label(
        "RC-103G-000000",
        "template51x25.pdf",
        output_pdf="web_label.pdf",
        print_after_create=True,  # Don't print, just create PDF
        add_datamatrix=True,
    )

    print(f"Result: {result}")
