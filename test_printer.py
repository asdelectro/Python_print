# TSC Printer Settings Manager
import win32print
import win32gui
import win32con
import win32ui
from ctypes import windll, byref, c_long, c_char_p, Structure, sizeof
from ctypes.wintypes import DWORD, HANDLE
import struct
import logging

class TSCPrinterSettings:
    def __init__(self, printer_name="TSC TE300", enable_logging=True):
        self.printer_name = printer_name
        
        # Configure logging
        if enable_logging:
            logging.basicConfig(level=logging.INFO, 
                              format='%(asctime)s - %(levelname)s - %(message)s')
            self.logger = logging.getLogger(__name__)
        else:
            class NullLogger:
                def debug(self, msg): pass
                def info(self, msg): pass
                def warning(self, msg): pass
                def error(self, msg): pass
            self.logger = NullLogger()
    
    def get_printer_handle(self):
        """Get printer handle"""
        try:
            return win32print.OpenPrinter(self.printer_name)
        except Exception as e:
            self.logger.error(f"Failed to open printer {self.printer_name}: {e}")
            return None
    
    def get_printer_info(self):
        """Get basic printer information"""
        try:
            printer_handle = self.get_printer_handle()
            if not printer_handle:
                return None
            
            try:
                # Get printer info level 2
                printer_info = win32print.GetPrinter(printer_handle, 2)
                
                info = {
                    'printer_name': printer_info['pPrinterName'],
                    'server_name': printer_info['pServerName'],
                    'share_name': printer_info['pShareName'],
                    'port_name': printer_info['pPortName'],
                    'driver_name': printer_info['pDriverName'],
                    'comment': printer_info['pComment'],
                    'location': printer_info['pLocation'],
                    'status': printer_info['Status'],
                    'attributes': printer_info['Attributes']
                }
                
                return info
                
            finally:
                win32print.ClosePrinter(printer_handle)
                
        except Exception as e:
            self.logger.error(f"Error getting printer info: {e}")
            return None
    
    def get_print_capabilities(self):
        """Get printer capabilities"""
        try:
            printer_handle = self.get_printer_handle()
            if not printer_handle:
                return None
            
            try:
                # Get device capabilities
                hdc = win32ui.CreateDC()
                hdc.CreatePrinterDC(self.printer_name)
                
                caps = {
                    'horizontal_resolution': hdc.GetDeviceCaps(win32con.HORZRES),
                    'vertical_resolution': hdc.GetDeviceCaps(win32con.VERTRES),
                    'horizontal_size_mm': hdc.GetDeviceCaps(win32con.HORZSIZE),
                    'vertical_size_mm': hdc.GetDeviceCaps(win32con.VERTSIZE),
                    'logical_pixels_x': hdc.GetDeviceCaps(win32con.LOGPIXELSX),
                    'logical_pixels_y': hdc.GetDeviceCaps(win32con.LOGPIXELSY),
                    'bits_per_pixel': hdc.GetDeviceCaps(win32con.BITSPIXEL),
                    'color_planes': hdc.GetDeviceCaps(win32con.PLANES),
                }
                
                hdc.DeleteDC()
                return caps
                
            finally:
                win32print.ClosePrinter(printer_handle)
                
        except Exception as e:
            self.logger.error(f"Error getting printer capabilities: {e}")
            return None
    
    def get_current_devmode(self):
        """Get current DEVMODE settings"""
        try:
            printer_handle = self.get_printer_handle()
            if not printer_handle:
                return None
            
            try:
                # Get printer info with DEVMODE
                printer_info = win32print.GetPrinter(printer_handle, 2)
                devmode = printer_info['pDevMode']
                
                if devmode:
                    settings = {
                        'device_name': devmode.DeviceName,
                        'paper_size': devmode.PaperSize,
                        'paper_length': devmode.PaperLength,
                        'paper_width': devmode.PaperWidth,
                        'orientation': devmode.Orientation,
                        'copies': devmode.Copies,
                        'default_source': devmode.DefaultSource,
                        'print_quality': devmode.PrintQuality,
                        'color': devmode.Color,
                        'duplex': devmode.Duplex,
                        'y_resolution': devmode.YResolution,
                        'tt_option': devmode.TTOption,
                        'collate': devmode.Collate,
                        'scale': devmode.Scale,
                        'dpi_x': getattr(devmode, 'LogPixels', 'N/A'),
                        'media_type': getattr(devmode, 'MediaType', 'N/A'),
                        'dither_type': getattr(devmode, 'DitherType', 'N/A')
                    }
                    
                    return settings
                
            finally:
                win32print.ClosePrinter(printer_handle)
                
        except Exception as e:
            self.logger.error(f"Error getting DEVMODE: {e}")
            return None
    
    def set_printer_settings(self, settings_dict):
        """Set printer settings via DEVMODE"""
        try:
            printer_handle = self.get_printer_handle()
            if not printer_handle:
                return False
            
            try:
                # Get current printer info
                printer_info = win32print.GetPrinter(printer_handle, 2)
                devmode = printer_info['pDevMode']
                
                if not devmode:
                    self.logger.error("Could not get current DEVMODE")
                    return False
                
                # Modify settings
                for key, value in settings_dict.items():
                    if hasattr(devmode, key):
                        setattr(devmode, key, value)
                        self.logger.info(f"Set {key} = {value}")
                    else:
                        self.logger.warning(f"Property {key} not found in DEVMODE")
                
                # Update printer info
                printer_info['pDevMode'] = devmode
                
                # Set the printer with new settings
                win32print.SetPrinter(printer_handle, 2, printer_info, 0)
                self.logger.info("Printer settings updated successfully")
                return True
                
            finally:
                win32print.ClosePrinter(printer_handle)
                
        except Exception as e:
            self.logger.error(f"Error setting printer settings: {e}")
            return False
    
    def get_paper_sizes(self):
        """Get available paper sizes"""
        try:
            # Common TSC paper sizes
            paper_sizes = {
                1: "Letter (8.5 x 11 in)",
                5: "Legal (8.5 x 14 in)",
                9: "A4 (210 x 297 mm)",
                11: "A5 (148 x 210 mm)",
                256: "User Defined",
                # TSC specific sizes might need to be defined
            }
            
            return paper_sizes
            
        except Exception as e:
            self.logger.error(f"Error getting paper sizes: {e}")
            return {}
    
    def set_custom_paper_size(self, width_mm, height_mm):
        """Set custom paper size in millimeters"""
        try:
            # Convert mm to tenths of millimeter (DEVMODE units)
            width_tenths = int(width_mm * 10)
            height_tenths = int(height_mm * 10)
            
            settings = {
                'PaperSize': 256,  # User defined
                'PaperWidth': width_tenths,
                'PaperLength': height_tenths
            }
            
            return self.set_printer_settings(settings)
            
        except Exception as e:
            self.logger.error(f"Error setting custom paper size: {e}")
            return False
    
    def set_print_quality(self, dpi):
        """Set print quality (DPI)"""
        try:
            settings = {
                'PrintQuality': dpi,
                'YResolution': dpi
            }
            
            return self.set_printer_settings(settings)
            
        except Exception as e:
            self.logger.error(f"Error setting print quality: {e}")
            return False
    
    def set_orientation(self, orientation='portrait'):
        """Set paper orientation"""
        try:
            # 1 = Portrait, 2 = Landscape
            orient_value = 1 if orientation.lower() == 'portrait' else 2
            
            settings = {
                'Orientation': orient_value
            }
            
            return self.set_printer_settings(settings)
            
        except Exception as e:
            self.logger.error(f"Error setting orientation: {e}")
            return False
    
    def send_direct_command(self, command):
        """Send direct command to TSC printer (if supported)"""
        try:
            printer_handle = self.get_printer_handle()
            if not printer_handle:
                return False
            
            try:
                # Create a print job
                job_info = {
                    'pDocName': 'Direct Command',
                    'pOutputFile': None,
                    'pDatatype': 'RAW'
                }
                
                job_id = win32print.StartDocPrinter(printer_handle, 1, job_info)
                if job_id > 0:
                    win32print.StartPagePrinter(printer_handle)
                    
                    # Send command
                    command_bytes = command.encode('utf-8')
                    win32print.WritePrinter(printer_handle, command_bytes)
                    
                    win32print.EndPagePrinter(printer_handle)
                    win32print.EndDocPrinter(printer_handle)
                    
                    self.logger.info(f"Direct command sent: {command}")
                    return True
                else:
                    self.logger.error("Failed to start print job for direct command")
                    return False
                    
            finally:
                win32print.ClosePrinter(printer_handle)
                
        except Exception as e:
            self.logger.error(f"Error sending direct command: {e}")
            return False
    
    def print_settings_report(self):
        """Print current settings to console"""
        print(f"\n=== TSC Printer Settings Report ===")
        print(f"Printer: {self.printer_name}")
        
        # Basic info
        info = self.get_printer_info()
        if info:
            print(f"\nBasic Information:")
            for key, value in info.items():
                print(f"  {key}: {value}")
        
        # Capabilities
        caps = self.get_print_capabilities()
        if caps:
            print(f"\nCapabilities:")
            for key, value in caps.items():
                print(f"  {key}: {value}")
        
        # Current settings
        settings = self.get_current_devmode()
        if settings:
            print(f"\nCurrent DEVMODE Settings:")
            for key, value in settings.items():
                print(f"  {key}: {value}")
        
        print(f"\n=== End Report ===\n")
    
    def configure_for_labels(self, width_mm=46, height_mm=25, dpi=300):
        """Configure printer specifically for label printing"""
        try:
            self.logger.info(f"Configuring for labels: {width_mm}x{height_mm}mm at {dpi}DPI")
            
            success = True
            
            # Set custom paper size
            if not self.set_custom_paper_size(width_mm, height_mm):
                success = False
            
            # Set high DPI for quality
            if not self.set_print_quality(dpi):
                success = False
            
            # Set portrait orientation
            if not self.set_orientation('portrait'):
                success = False
            
            # Additional TSC-specific settings via direct commands
            tsc_commands = [
                "SIZE 46 mm, 25 mm\n",
                "GAP 2 mm, 0 mm\n",
                "DIRECTION 1\n",
                "REFERENCE 0, 0\n",
                "OFFSET 0 mm\n",
                "SET PEEL OFF\n",
                "SET CUTTER OFF\n",
                "SET PARTIAL_CUTTER OFF\n",
                "SET TEAR ON\n",
                "DENSITY 8\n",
                "SPEED 4\n"
            ]
            
            for cmd in tsc_commands:
                if not self.send_direct_command(cmd):
                    self.logger.warning(f"Failed to send command: {cmd.strip()}")
            
            if success:
                self.logger.info("Label configuration completed successfully")
            else:
                self.logger.warning("Label configuration completed with some errors")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error configuring for labels: {e}")
            return False

# Example usage and testing
if __name__ == "__main__":
    # Initialize printer settings manager
    tsc_settings = TSCPrinterSettings("TSC TE300", enable_logging=True)
    
    print("Testing TSC Printer Settings Manager...")
    
    # Print current settings report
    tsc_settings.print_settings_report()
    
    # Show available paper sources
    print("\nAvailable paper sources:")
    sources = tsc_settings.get_available_paper_sources()
    for code, name in sources.items():
        print(f"  {code}: {name}")
    
    # Configure for label printing
    print("\nConfiguring printer for 46x25mm labels...")
    result = tsc_settings.configure_for_labels(width_mm=46, height_mm=25, dpi=300)
    print(f"Configuration result: {result}")
    
    # Show how to open driver properties dialog
    print("\nTo access TSC-specific settings like Speed and Darkness:")
    print("1. Run this script as Administrator for driver changes")
    print("2. Or open printer properties manually:")
    print(f"   Control Panel > Devices and Printers > Right-click '{tsc_settings.printer_name}' > Printing Preferences")
    print("3. Or use the method below:")
    
    # Uncomment to open properties dialog
    # tsc_settings.show_driver_properties_dialog()
    
    # Send a test command
    print("\nSending test TSC command...")
    result = tsc_settings.send_direct_command("PRINT 1\r\n")
    print(f"Test command result: {result}")
    
    print("\nTesting completed.")
    print("\nNote: Some settings require Administrator privileges to modify.")
    print("TSC-specific settings (Speed, Darkness) are best configured through:")
    print("- The printer driver's properties dialog")
    print("- Direct TSC commands")
    print("- TSC printer software tools")