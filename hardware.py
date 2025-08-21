# main_app.py - main application for any Python
# -*- coding: utf-8 -*-
import subprocess
import json
import os

class RCDevicesClient:
    def __init__(self, exe_path="dll_wrapper.exe"):
        self.exe_path = exe_path
        
        # Check if EXE exists
        if not os.path.exists(exe_path):
            # Look for it next to the script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            exe_path = os.path.join(script_dir, "dll_wrapper.exe")
            if os.path.exists(exe_path):
                self.exe_path = exe_path
            else:
                raise FileNotFoundError(f"dll_wrapper.exe not found: {exe_path}")
    
    def _call_exe(self, command, *args):
        """Call EXE with command"""
        cmd = [self.exe_path, command] + [str(arg) for arg in args]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                # If there's stderr, use it, otherwise try to parse stdout
                if result.stderr.strip():
                    return {"success": False, "error": f"Process error: {result.stderr.strip()}"}
                
            # Try to parse JSON from stdout
            try:
                return json.loads(result.stdout.strip())
            except json.JSONDecodeError:
                return {"success": False, "error": f"Invalid JSON response: {result.stdout}"}
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timeout"}
        except Exception as e:
            return {"success": False, "error": f"Execution error: {str(e)}"}
    
    def get_device_list(self):
        """Get list of devices"""
        result = self._call_exe("list")
        if result["success"]:
            return result["devices"]
        else:
            raise Exception(f"Error getting devices: {result['error']}")
    
    def get_device_count(self):
        """Get number of devices"""
        result = self._call_exe("list")
        if result["success"]:
            return result["count"]
        else:
            raise Exception(f"Error getting device count: {result['error']}")
    
    def get_device_mcu_id(self, handle):
        """Get device MCU ID"""
        result = self._call_exe("mcu_id", f"0x{handle:X}")
        if result["success"]:
            return result["mcu_id"]
        else:
            raise Exception(f"Error getting MCU ID: {result['error']}")
    
    def get_device_serial(self, handle):
        """Get device serial number"""
        result = self._call_exe("serial", f"0x{handle:X}")
        if result["success"]:
            return result["serial"]
        else:
            raise Exception(f"Error getting serial: {result['error']}")
    
    def get_device_database_info(self, handle):
        """Get device database information"""
        result = self._call_exe("db_info", f"0x{handle:X}")
        if result["success"]:
            return result["db_info"]
        else:
            raise Exception(f"Error getting DB info: {result['error']}")
    
    def get_all_devices_info(self):
        """Get all information for all devices"""
        result = self._call_exe("all")
        if result["success"]:
            return result["devices"]
        else:
            raise Exception(f"Error getting all devices info: {result['error']}")
    
    def get_single_device(self):
        """Get single device info. Raises exception if 0 or more than 1 device found"""
        device_count = self.get_device_count()
        
        if device_count == 0:
            raise Exception("No devices found. Check connection and drivers.")
        elif device_count > 1:
            raise Exception(f"Multiple devices found ({device_count}). Only single device mode supported.")
        
        # Get info for the single device
        all_devices = self.get_all_devices_info()
        return all_devices[0]
    
    def get_version(self):
        """Get wrapper version"""
        result = self._call_exe("version")
        if result["success"]:
            return result
        else:
            raise Exception(f"Error getting version: {result['error']}")

def main():
    try:
        # Create client
        client = RCDevicesClient()
        
        # Check version
        version_info = client.get_version()
        print(f"DLL Wrapper version: {version_info['version']} ({version_info['architecture']})")
        
        # Get single device (will fail if 0 or >1 devices)
        try:
            device = client.get_single_device()
            print("Single device mode: SUCCESS")
            
            handle = device["handle"]
            print(f"\n=== Device Information ===")
            print(f"Handle: 0x{handle:X}")
            
            # MCU ID
            mcu_id = device["mcu_id"]
            if mcu_id:
                mcu_str = " ".join(f"{b:02X}" for b in mcu_id)
                print(f"MCU ID: {mcu_str}")
            else:
                print("MCU ID: Error")
            
            # Serial number
            serial = device["serial"]
            if serial:
                print(f"Serial: {serial}")
            else:
                print("Serial: Error")
            
            # Database info
            db_info = device["db_info"]
            if db_info["result"] == 0:  # ERR_DB_OK
                print(f"Tests OK: {db_info['tests_ok']}")
                print(f"Calibration OK: {db_info['calibration_ok']}")
                print(f"Program Time: {db_info['prog_time']}")
                print(f"Calibration Time: {db_info['calib_time']}")
                
                # Device status
                status = "READY" if db_info["tests_ok"] and db_info["calibration_ok"] else "NOT READY"
                print(f"Status: {status}")
            else:
                print(f"Database Error: {db_info['result']}")
                print("Status: ERROR")
        
        except Exception as device_error:
            print(f"Single device mode: FAILED - {device_error}")
            
            # Fallback: show all devices info
            device_count = client.get_device_count()
            print(f"\nFallback: Found {device_count} devices")
            
            if device_count > 0:
                all_devices = client.get_all_devices_info()
                for i, device in enumerate(all_devices):
                    handle = device["handle"]
                    print(f"Device #{i}: handle = 0x{handle:X}")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()