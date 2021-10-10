#include "imu_bh.hpp"
#include <iostream>
#include <iomanip>
#include <assert.h>

void printBuffer(uint8_t* buffer, size_t len) {
    for (size_t i = 0; i < len; ++i) {
        std::cout << (uint16_t)buffer[i] << " ";
    }
    std::cout << std::endl;
}

int main(int argc, char** argv) {
    std::cout << std::hex << std::setfill('0') << std::setw(2);
    RawImuData msg = {0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0xFFFFFFFFFFFFFFFF};
    std::unique_ptr<uint8_t> buf = msg.encode();
    printBuffer(buf.get(), msg.buffer_size());
    RawImuData decoded_msg = RawImuData::decode(buf, msg.buffer_size());
    assert(msg.gyro_x == decoded_msg.gyro_x);
    assert(msg.timestamp == decoded_msg.timestamp);
}
