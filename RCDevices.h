#ifndef __RCDEVICES_H__
#define __RCDEVICES_H__

#ifdef _USRDLL
  #define RCAPI __declspec(dllexport) __stdcall
#else
  #define RCAPI __declspec(dllimport) __stdcall
#endif

#ifndef __RCDEVICES__
typedef unsigned char uint8;
typedef unsigned int uint32;
#endif

#define ERR_DB_OK               0
#define ERR_DB_INVALID_PARAM    1
#define ERR_DB_GENERAL          2
#define ERR_DB_NO_DEVICE        3
#define ERR_DB_SERIAL_MISMATCH  4
#define ERR_DB_CALIB_DATA       5

#ifdef __cplusplus
extern "C"
{
#endif

uint32 RCAPI GetDeviceList(uint32 * list);
uint32 RCAPI GetDeviceMCUId(uint32 handle, uint8 * id);
uint32 RCAPI GetDeviceSerial(uint32 handle, char * serial);
uint32 RCAPI GetDeviceDatabaseInfo(uint32 handle, uint8 * tests_ok, uint8 * calibration_ok, uint32 * prog_time, uint32 * calib_time);

#ifdef __cplusplus
}
#endif

#endif // __RCDEVICES_H__
