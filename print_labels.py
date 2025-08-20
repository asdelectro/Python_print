from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from PyPDF2 import PdfReader, PdfWriter
import io
import win32print
import win32ui
from PIL import Image, ImageWin
import fitz
import logging
import os


class LabelPrinter:
    def __init__(self, enable_logging=True, temp_filename="temp_label.pdf"):
        # Label position settings
        self.label_x_mm = 27
        self.label_y_mm = 13.3
        self.label_font_size = 6
        
        # QR code settings
        self.qr_x_mm = 19
        self.qr_y_mm = 2
        self.qr_size_mm = 5
        
        # Print settings
        self.print_scale = 1.0
        self.printer_name = "TSC TE300"
        self.print_dpi = 300
        
        # Print margins
        self.print_offset_x = 0
        self.print_offset_y = -20
        self.print_width = None
        self.print_height = None
        
        # Logging and file settings
        self.enable_logging = enable_logging
        self.temp_filename = temp_filename
        
        # Configure logging
        if self.enable_logging:
            logging.basicConfig(
                level=logging.DEBUG,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler('label_printer.log'),
                    logging.StreamHandler()
                ]
            )
            self.logger = logging.getLogger(__name__)
            self.logger.info("LabelPrinter initialized with logging enabled")
        else:
            # Disable logging
            self.logger = logging.getLogger(__name__)
            self.logger.disabled = True
            # Create null logger that does nothing
            class NullLogger:
                def debug(self, msg): pass
                def info(self, msg): pass
                def warning(self, msg): pass
                def error(self, msg): pass
                def critical(self, msg): pass
            self.logger = NullLogger()
    
    def create_label(self, serial_number: str, template_pdf: str, output_pdf: str = None, 
                    show_grid=False, add_qr=True):
        """Create label with serial number and QR code"""
        if output_pdf is None:
            output_pdf = self.temp_filename
            
        self.logger.debug(f"Creating label for serial: {serial_number}")
        
        # Remove existing file if it exists
        if os.path.exists(output_pdf):
            try:
                os.remove(output_pdf)
                self.logger.debug(f"Removed existing file: {output_pdf}")
            except Exception as e:
                self.logger.error(f"Could not remove existing file {output_pdf}: {e}")
        
        template_width = 46 * mm
        template_height = 25 * mm
        
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=(template_width, template_height))
        
        # Serial number
        c.setFont("Helvetica-Bold", self.label_font_size)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(self.label_x_mm * mm, self.label_y_mm * mm, serial_number)
        self.logger.debug(f"Added serial number at ({self.label_x_mm}, {self.label_y_mm})")
        
        # QR code
        if add_qr:
            try:
                qr_code = qr.QrCodeWidget(serial_number)
                bounds = qr_code.getBounds()
                qr_size = self.qr_size_mm * mm
                width_qr, height_qr = bounds[2] - bounds[0], bounds[3] - bounds[1]
                d = Drawing(
                    qr_size, qr_size,
                    transform=[qr_size / width_qr, 0, 0, qr_size / height_qr, 0, 0]
                )
                d.add(qr_code)
                renderPDF.draw(d, c, self.qr_x_mm * mm, self.qr_y_mm * mm)
                self.logger.debug(f"Added QR code at ({self.qr_x_mm}, {self.qr_y_mm})")
            except Exception as e:
                self.logger.error(f"QR code creation error: {e}")
        
        # Coordinate grid
        if show_grid:
            self.logger.debug("Adding coordinate grid")
            c.setStrokeColorRGB(1, 0, 0)
            c.setLineWidth(0.3)
            
            for x in range(0, 50, 5):
                x_pos = x * mm
                if x_pos <= template_width:
                    c.line(x_pos, 0, x_pos, template_height)
                    c.setFont("Helvetica", 4)
                    c.setFillColorRGB(1, 0, 0)
                    c.drawString(x_pos + 0.5 * mm, 0.5 * mm, str(x))
            
            for y in range(0, 30, 5):
                y_pos = y * mm
                if y_pos <= template_height:
                    c.line(0, y_pos, template_width, y_pos)
                    c.setFont("Helvetica", 4)
                    c.setFillColorRGB(1, 0, 0)
                    c.drawString(0.5 * mm, y_pos + 0.5 * mm, str(y))
            
            c.setStrokeColorRGB(1, 0.7, 0.7)
            c.setLineWidth(0.1)
            
            for x in range(1, 46):
                x_pos = x * mm
                c.line(x_pos, 0, x_pos, template_height)
            
            for y in range(1, 25):
                y_pos = y * mm
                c.line(0, y_pos, template_width, y_pos)
        
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
            
            self.logger.info(f"Label created successfully: {output_pdf}")
        except Exception as e:
            self.logger.error(f"Error creating label: {e}")
            raise
    
    def pdf_to_image(self, pdf_path: str) -> Image.Image:
        """Convert PDF to image"""
        try:
            self.logger.debug(f"Converting PDF to image: {pdf_path}")
            pdf_document = fitz.open(pdf_path)
            page = pdf_document[0]
            mat = fitz.Matrix(self.print_dpi / 72, self.print_dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("ppm")
            image = Image.open(io.BytesIO(img_data))
            pdf_document.close()
            self.logger.debug(f"PDF converted to image: {image.size}")
            return image
        except Exception as e:
            self.logger.error(f"PDF conversion error: {e}")
            return None
    
    def print_label(self, pdf_path: str = None, printer_name: str = None, scale: float = None):
        """Print label with scaling"""
        if pdf_path is None:
            pdf_path = self.temp_filename
        if printer_name is None:
            printer_name = self.printer_name
        if scale is None:
            scale = self.print_scale
        
        self.logger.info(f"Starting print job: {pdf_path} with scale {scale}")
        
        try:
            image = self.pdf_to_image(pdf_path)
            if image is None:
                return False
            
            # Apply scaling
            if scale != 1.0:
                original_width, original_height = image.size
                new_width = int(original_width * scale)
                new_height = int(original_height * scale)
                image_scaled = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                self.logger.debug(f"Image scaled: {original_width}x{original_height} -> {new_width}x{new_height}")
            else:
                image_scaled = image
            
            # Create printer context
            self.logger.debug(f"Connecting to printer: {printer_name}")
            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(printer_name)
            hdc.StartDoc("Label Print Job")
            hdc.StartPage()
            
            # Print with offset
            dib = ImageWin.Dib(image_scaled)
            width = self.print_width if self.print_width is not None else image_scaled.size[0]
            height = self.print_height if self.print_height is not None else image_scaled.size[1]
            x = self.print_offset_x
            y = self.print_offset_y
            
            self.logger.debug(f"Print area: x={x}, y={y}, width={width}, height={height}")
            dib.draw(hdc.GetHandleOutput(), (x, y, x + width, y + height))
            
            hdc.EndPage()
            hdc.EndDoc()
            hdc.DeleteDC()
            
            self.logger.info("Print job completed successfully")
            return True
        except Exception as e:
            self.logger.error(f"Print error: {e}")
            return False
    
    def get_available_printers(self):
        """Get list of available printers"""
        printers = []
        try:
            for printer in win32print.EnumPrinters(2):
                printers.append(printer[2])
            self.logger.debug(f"Found {len(printers)} printers")
        except Exception as e:
            self.logger.error(f"Error getting printers: {e}")
        return printers
    
    def create_and_print_label(self, serial_number: str, template_pdf: str, 
                             output_pdf: str = None, show_grid=False, add_qr=True,
                             print_after_create=True, printer_name: str = None, 
                             scale: float = None):
        """Create and print label"""
        if output_pdf is None:
            output_pdf = self.temp_filename
        
        self.logger.info(f"Creating and printing label: {serial_number}")
        
        self.create_label(serial_number, template_pdf, output_pdf, show_grid, add_qr)
        
        if print_after_create:
            return self.print_label(output_pdf, printer_name, scale)
        return True
    
    def set_temp_filename(self, filename: str):
        """Set the temporary filename for label files"""
        self.temp_filename = filename
        self.logger.debug(f"Temporary filename set to: {filename}")
    
    def enable_disable_logging(self, enable: bool):
        """Enable or disable logging at runtime"""
        self.enable_logging = enable
        if enable:
            self.logger.disabled = False
            if hasattr(self.logger, 'handlers'):
                # Re-enable existing handlers
                for handler in self.logger.handlers:
                    handler.setLevel(logging.DEBUG)
            self.logger.info("Logging enabled")
        else:
            self.logger.info("Logging disabled")
            self.logger.disabled = True
    
    def print_settings(self):
        """Print current settings"""
        print(f"=== LABEL SETTINGS ===")
        print(f"Label position: X={self.label_x_mm}mm, Y={self.label_y_mm}mm")
        print(f"Font size: {self.label_font_size}")
        print(f"QR position: X={self.qr_x_mm}mm, Y={self.qr_y_mm}mm")
        print(f"QR size: {self.qr_size_mm}mm")
        
        print(f"\n=== PRINT SETTINGS ===")
        print(f"Printer: {self.printer_name}")
        print(f"Scale: {self.print_scale} ({int(self.print_scale*100)}%)")
        print(f"DPI: {self.print_dpi}")
        print(f"Offset: X={self.print_offset_x}px, Y={self.print_offset_y}px")
        print(f"Print area: {self.print_width}x{self.print_height}")
        
        print(f"\n=== FILE SETTINGS ===")
        print(f"Temporary filename: {self.temp_filename}")
        print(f"Logging enabled: {self.enable_logging}")
        
        print(f"\n=== AVAILABLE PRINTERS ===")
        printers = self.get_available_printers()
        for i, printer in enumerate(printers, 1):
            print(f"{i}. {printer}")


# Usage examples
if __name__ == "__main__":
    # Initialize with logging disabled and custom temp filename
    printer = LabelPrinter(enable_logging=False, temp_filename="label.pdf")
    
    # Or with logging enabled (default)
    # printer = LabelPrinter()
    
    # Or with default temp filename and logging disabled
    # printer = LabelPrinter(enable_logging=False)

    # Create labels (will use same filename and overwrite)
     #printer.create_and_print_label("RC-103-000123", "templ_103.pdf", scale=1.0)
     #printer.create_and_print_label("RC-103-000124", "templ_103.pdf", scale=1.0)
    
    # Change temp filename if needed
     #printer.set_temp_filename("my_label.pdf")
     #printer.create_and_print_label("RC-103-000125", "templ_103.pdf", scale=1.0)
    
    # Enable/disable logging at runtime
    printer.create_and_print_label("RC-103-000126", "templ_103.pdf", scale=1.0)
    #printer.enable_disable_logging(False)  # Disable logging
    
    # Show settings
    printer.print_settings()