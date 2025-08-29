# main_app.py - main application with direct DLL calls
# -*- coding: utf-8 -*-
import ctypes
import sys
import os
import platform
from ctypes import c_uint32, c_uint64, c_uint8, c_char_p, POINTER, byref, create_string_buffer

# Global variables for DLL and functions
dll = None
GetDeviceList = None
GetDeviceMCUId = None
GetDeviceSerial = None
GetDeviceDatabaseInfo = None
ERR_DB_OK = 0



def init_dll():
    """Initialize DLL"""
    global dll, GetDeviceList, GetDeviceMCUId, GetDeviceSerial, GetDeviceDatabaseInfo
    
    # Find DLL
    exe_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
    dll_path = os.path.join(exe_dir, "RCDevices.dll")
    
    if not os.path.exists(dll_path):
        raise FileNotFoundError(f"DLL not found: {dll_path}")
    
    # Load DLL - use cdll for 64-bit DLL
    dll = ctypes.cdll.LoadLibrary(dll_path)
    
    # Setup functions without suffixes for 64-bit DLL
    try:
        # Try without suffixes first (64-bit)
        GetDeviceList = dll.GetDeviceList
        GetDeviceMCUId = dll.GetDeviceMCUId  
        GetDeviceSerial = dll.GetDeviceSerial
        GetDeviceDatabaseInfo = dll.GetDeviceDatabaseInfo
    except AttributeError:
        # If not found, try with suffixes (32-bit)
        dll = ctypes.windll.LoadLibrary(dll_path)
        GetDeviceList = getattr(dll, "GetDeviceList@4")
        GetDeviceMCUId = getattr(dll, "GetDeviceMCUId@8")
        GetDeviceSerial = getattr(dll, "GetDeviceSerial@8") 
        GetDeviceDatabaseInfo = getattr(dll, "GetDeviceDatabaseInfo@20")
    
    # Setup argument types and return types
    GetDeviceList.argtypes = [POINTER(c_uint32)]
    GetDeviceList.restype = c_uint32
    
    GetDeviceMCUId.argtypes = [c_uint32, POINTER(c_uint8)]
    GetDeviceMCUId.restype = c_uint32
    
    GetDeviceSerial.argtypes = [c_uint32, c_char_p]
    GetDeviceSerial.restype = c_uint32
    
    GetDeviceDatabaseInfo.argtypes = [c_uint32, POINTER(c_uint8), POINTER(c_uint8), POINTER(c_uint64), POINTER(c_uint64)]
    GetDeviceDatabaseInfo.restype = c_uint32

def get_device_list():
    """Get list of devices"""
    device_count = GetDeviceList(None)
    if device_count == 0:
        return []
    
    devices = (c_uint32 * device_count)()
    GetDeviceList(devices)
    return [devices[i] for i in range(device_count)]

def get_device_mcu_id(handle):
    """Get device MCU ID"""
    size = GetDeviceMCUId(handle, None)
    if size == 0:
        return None
    
    hwid = (c_uint8 * size)()
    GetDeviceMCUId(handle, hwid)
    return [hwid[i] for i in range(size)]

def get_device_serial(handle):
    """Get device serial number"""
    size = GetDeviceSerial(handle, None)
    if size == 0:
        return None
    
    serial_buffer = create_string_buffer(size)
    GetDeviceSerial(handle, serial_buffer)
    return serial_buffer.value.decode('utf-8')

def get_device_database_info(handle):
    """Get database information"""
    tests_ok = c_uint8()
    calibration_ok = c_uint8()
    prog_time = c_uint64()
    calib_time = c_uint64()
    
    result = GetDeviceDatabaseInfo(handle, byref(tests_ok), byref(calibration_ok), 
                                  byref(prog_time), byref(calib_time))
    

    
    return {
        "result": result,
        "tests_ok": tests_ok.value,
        "calibration_ok": calibration_ok.value,
        "prog_time": prog_time.value,
        "calib_time": calib_time.value
    }

class RCDevicesClient:
    def __init__(self):
        init_dll()
    
    def get_device_list(self):
        """Get list of devices"""
        return get_device_list()
    
    def get_device_count(self):
        """Get number of devices"""
        return len(get_device_list())
    
    def get_device_mcu_id(self, handle):
        """Get device MCU ID"""
        return get_device_mcu_id(handle)
    
    def get_device_serial(self, handle):
        """Get device serial number"""
        return get_device_serial(handle)
    
    def get_device_database_info(self, handle):
        """Get device database information"""
        return get_device_database_info(handle)
    
    def get_all_devices_info(self):
        """Get all information for all devices"""
        devices = get_device_list()
        result = []
        
        for handle in devices:
            device_info = {
                "handle": handle,
                "mcu_id": get_device_mcu_id(handle),
                "serial": get_device_serial(handle),
                "db_info": get_device_database_info(handle)
            }
            result.append(device_info)
        
        return result
    
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
        """Get version info"""
        return {
            "success": True,
            "version": "2.0",
            "architecture": "64-bit" if platform.machine().endswith('64') else "32-bit",
            "mode": "Direct DLL"
        }

def main():
    try:
        # Create client
        client = RCDevicesClient()
        
        # Check version
        version_info = client.get_version()
        print(f"DLL Client version: {version_info['version']} ({version_info['architecture']}) - {version_info['mode']}")
        
        # Get single device (will fail if 0 or >1 devices)
        try:
            print("\n=== ПЕРВЫЙ ВЫЗОВ ===")
            device = client.get_single_device()
            print("Single device mode: SUCCESS")
            
            handle = device["handle"]
            print(f"Handle: 0x{handle:X}")
            
            # Serial number
            serial = device["serial"]
            if serial:
                print(f"Serial: {serial}")
            else:
                print("Serial: Error")
            
            # Database info
            db_info = device["db_info"]
            print(f"Database result: {db_info['result']}")
            print(f"Tests OK: {db_info['tests_ok']}")
            print(f"Calibration OK: {db_info['calibration_ok']}")
            
            # ВТОРОЙ ВЫЗОВ для проверки
            print("\n=== ВТОРОЙ ВЫЗОВ (через 2 секунды) ===")
            import time
            time.sleep(0.1)
            
            device2 = client.get_single_device()
            db_info2 = device2["db_info"]
            print(f"Database result: {db_info2['result']}")
            print(f"Tests OK: {db_info2['tests_ok']}")
            print(f"Calibration OK: {db_info2['calibration_ok']}")
            
            # ТРЕТИЙ ВЫЗОВ для проверки
            print("\n=== ТРЕТИЙ ВЫЗОВ (через 5 секунд) ===")
            time.sleep(0.1)
            
            device3 = client.get_single_device()
            db_info3 = device3["db_info"]
            print(f"Database result: {db_info3['result']}")
            print(f"Tests OK: {db_info3['tests_ok']}")
            print(f"Calibration OK: {db_info3['calibration_ok']}")
        
        except Exception as device_error:
            print(f"Single device mode: FAILED - {device_error}")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()