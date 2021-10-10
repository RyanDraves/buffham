#include "imu_bh.h"
#include <assert.h>
#include <stdio.h>

void printBuffer(uint8_t* buffer, size_t len) {
    for (size_t i = 0; i < len; ++i) {
        printf("%02X ", buffer[i]);
    }
    printf("\n");
}

int main(int argc, char** argv) {
    RawImuData msg = {0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0xFFFFFFFFFFFFFFFF};
    uint8_t* buf = RawImuData_encode(&msg);
    printBuffer(buf,  RawImuData_buffer_size(&msg));
    RawImuData decoded_msg = RawImuData_decode(buf, RawImuData_buffer_size(&msg));
    assert(msg.gyro_x == decoded_msg.gyro_x);
    assert(msg.timestamp == decoded_msg.timestamp);
    free(buf);
}
