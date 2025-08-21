#include <windows.h>
#include <stdio.h>

#include "..\RCDevices.h"

int main()    
{
  // Получить список приборов
  uint32 device_count = GetDeviceList(NULL);
  if (device_count == 0)
  {
    printf("No devices found\n");
    return -1;
  }
  uint32 * devices = new uint32[device_count];
  GetDeviceList(devices);

  // Получить информацию о приборах
  uint32 i, j;
  for (i = 0; i < device_count; i++)
  {
   uint32 handle = devices[i];
   printf("--- Device #%d, handle = %X ---\n", i, handle);

   // Получить аппаратный серийный номер прибора
   printf(" MCU Id:");
   uint32 size = GetDeviceMCUId(handle, NULL);
   if (size == 0)
     printf(" Error in GetDeviceMCUId()");
   else
   {
     uint8 * hwid = new uint8[size];
     GetDeviceMCUId(handle, hwid);
     for (j = 0; j < size; j++)
       printf(" %02X", hwid[j]);
   }
   printf("\n");

   // Получить пользовательский (читабельный) серийный номер прибора
   printf(" Serial: ");
   size = GetDeviceSerial(handle, NULL);
   if (size == 0)
     printf("Error in GetDeviceSerial()");
   else
   {
     char * serial = new char[size];
     GetDeviceSerial(handle, serial);
     printf("%s", serial);
   }
   printf("\n");

   // Получить информацию о приборе из БД
   uint8 tests_ok, calibration_ok;
   uint32 prog_time, calib_time;
   uint32 result = GetDeviceDatabaseInfo(handle, &tests_ok, &calibration_ok, &prog_time, &calib_time);
   if (result != ERR_DB_OK)
     printf("Error %d in GetDeviceDatabaseInfo()", result);
   else
   {
     printf(" Tests Ok:   %d\n"
            " Calib Ok:   %d\n"
            " Prog  Time: %d\n"
            " Calib Time: %d", tests_ok, calibration_ok, prog_time, calib_time);
   }
   printf("\n");
  }
  return 0;
}
