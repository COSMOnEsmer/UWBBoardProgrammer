/* ********************************************************************************* */
/* Copyright 2021-2023 NXP
 * All rights reserved.
 *
 * SPDX-License-Identifier: BSD-3-Clause
 ********************************************************************************** */
/* WARNING : DO NOT MODIFY THIS FILE; MAKE SURE CLANG FORMATTER IS TURNED OFF. */
/* clang-format off */

PRIMARY_SERVICE(service_gatt, gBleSig_GenericAttributeProfile_d)
CHARACTERISTIC(char_service_changed, gBleSig_GattServiceChanged_d, (gGattCharPropIndicate_c) )
VALUE(value_service_changed, gBleSig_GattServiceChanged_d, (gPermissionNone_c), 4, 0x00, 0x00, 0x00, 0x00)
CCCD(cccd_service_changed)

PRIMARY_SERVICE(service_gap, gBleSig_GenericAccessProfile_d)
CHARACTERISTIC(char_device_name, gBleSig_GapDeviceName_d, (gGattCharPropRead_c) )
VALUE(value_device_name, gBleSig_GapDeviceName_d, (gPermissionFlagReadable_c), 12, "NXP_BLE_QPPS")
CHARACTERISTIC(char_appearance, gBleSig_GapAppearance_d, (gGattCharPropRead_c) )
VALUE(value_appearance, gBleSig_GapAppearance_d, (gPermissionFlagReadable_c), 2, UuidArray(gGenericHeartrateSensor_c))
CHARACTERISTIC(char_ppcp, gBleSig_GapPpcp_d, (gGattCharPropRead_c) )
VALUE(value_ppcp, gBleSig_GapPpcp_d, (gPermissionFlagReadable_c), 8, 0x0A, 0x00, 0x10, 0x00, 0x64, 0x00, 0xE2, 0x04)

PRIMARY_SERVICE_UUID128(service_ubp, uuid_service_ubp)
CHARACTERISTIC_UUID128(char_ubp_info, uuid_info_ubp, gGattCharPropRead_c)
VALUE_UUID128_VARLEN(value_ubp_info, uuid_info_ubp, gPermissionFlagReadable_c, 256, 1, 0)
CHARACTERISTIC_UUID128(char_ubp_data, uuid_data_ubp, gGattCharPropNotify_c)
VALUE_UUID128_VARLEN(value_ubp_data, uuid_data_ubp, gPermissionNone_c, 64, 1, 0)
CCCD(cccd_ubp_data)
