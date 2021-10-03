#include "imu_bh.hpp"
#include <iostream>
#include <iomanip>

void printBuffer(uint8_t* buffer, size_t len) {
    for (size_t i = 0; i < len; ++i) {
        std::cout << (uint16_t)buffer[i] << " ";
    }
    std::cout << std::endl;
}

int main(int argc, char** argv) {
    std::cout << std::hex << std::setfill('0') << std::setw(2);
    RawImuData msg = {0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0xFFFFFFFFFFFFFFFF};
    std::cout << msg.gryo_x << std::endl;
    std::cout << msg.timestamp << std::endl;
    uint8_t* buf = msg.encode();
    std::cout << (uint16_t)buf[6] << std::endl;
    std::cout << *(uint64_t*)(buf + 14) << std::endl;
    printBuffer(buf, msg.buffer_size());
    RawImuData decoded_msg = RawImuData::decode(buf, msg.buffer_size());
    std::cout << decoded_msg.gryo_x << std::endl;
    std::cout << decoded_msg.timestamp << std::endl;
    delete buf;
}
