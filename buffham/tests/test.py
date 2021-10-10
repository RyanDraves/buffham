from buffham.tests.imu_bh import RawImuData

msg = RawImuData(0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0xFFFFFFFFFFFFFFFF)

buffer = msg.encode()

decoded_msg = RawImuData.decode(buffer)

print(msg.accel_x, msg.accel_y, msg.accel_z, msg.timestamp)
print(decoded_msg.accel_x, decoded_msg.accel_y, decoded_msg.accel_z, decoded_msg.timestamp)
