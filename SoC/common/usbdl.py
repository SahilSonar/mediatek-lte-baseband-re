#!/usr/bin/env python3

import argparse
import binascii
import serial
import struct
import time


def auto_int(i):
    return int(i, 0)

def hex_int(i):
    return int(i, 16)


class UsbDl:
    commands = {
        'CMD_C8': 0xC8, # Don't know the meaning of this yet.
        'CMD_READ32': 0xD1,
        'CMD_WRITE32': 0xD4,
        'CMD_JUMP_DA': 0xD5,
        'CMD_GET_TARGET_CONFIG': 0xD8,
        'CMD_UART1_LOG_EN': 0xDB,
        'CMD_GET_HW_SW_VER': 0xFC,
        'CMD_GET_HW_CODE': 0xFD,
    }

    socs = {
        0x0279: {
            'name': "MT6797",
            'brom': 0x00000000,
            'brom_size': 0x14000,
            'sram': 0x00100000,
            'sram_size': 0x30000,
            'l2_sram': 0x00200000, # Functional spec says this is 0x00400000, but that's incorrect.
            'l2_sram_size': 0x100000,
            'efusec': 0x10206000,
            'cqdma_base': 0x10212C00,
            'tmp_addr': 0x110001A0,
            'brom_g_bounds_check': (
                (0x0010276C, 0x00000000),
                (0x00105704, 0x00000000),
            ),
        },
        0x0321: {
            'name': "MT6735",
            'brom': 0x00000000,
            'brom_size': 0x10000,
            'sram': 0x00100000,
            'sram_size': 0x10000,
            'l2_sram': 0x00200000,
            'l2_sram_size': 0x40000,
            'efusec': 0x10206000,
            'cqdma_base': 0x10217C00,
            'tmp_addr': 0x110001A0,
            'brom_g_bounds_check': (
                (0x00102760, 0x00000000),
                (0x00105704, 0x00000000),
            ),
        },
        0x0335: {
            'name': "MT6737M",
            'brom': 0x00000000,
            'brom_size': 0x10000,
            'sram': 0x00100000,
            'sram_size': 0x10000,
            'l2_sram': 0x00200000,
            'l2_sram_size': 0x40000,
            'efusec': 0x10206000,
            'cqdma_base': 0x10217C00,
            'tmp_addr': 0x110001A0,
            'brom_g_bounds_check': (
                (0x00102760, 0x00000000),
                (0x00105704, 0x00000000),
            ),
        },
        0x8163: {
            'name': "MT8163",
            'brom': 0x00000000,
            'brom_size': 0x14000,
            'sram': 0x00100000,
            'sram_size': 0x10000,
            'l2_sram': 0x00200000,
            'l2_sram_size': 0x40000,
            'efusec': 0x10206000,
            'cqdma_base': 0x10212C00,
            'tmp_addr': 0x110001A0,
            'brom_g_bounds_check': (
                (0x00102868, 0x00000000),
            ),
        },
    }

    def __init__(self, port, timeout=1, write_timeout=1, debug=False):
        self.debug = debug
        self.ser = serial.Serial(port, timeout=timeout, write_timeout=write_timeout)
        hw_code = self.cmd_get_hw_code()
        self.soc = self.socs[hw_code]
        print("{} detected!".format(self.soc['name']))

    def _send_bytes(self, data):
        data = bytes(data)
        if self.debug:
            print("-> {}".format(binascii.b2a_hex(data)))
        self.ser.write(data)
        echo = self.ser.read(len(data))
        if self.debug:
            print("<- {}".format(binascii.b2a_hex(echo)))
        if echo != data:
            raise Exception

    def _recv_bytes(self, count):
        data = self.ser.read(count)
        if self.debug:
            print("<- {}".format(binascii.b2a_hex(data)))
        if len(data) != count:
            raise Exception
        return bytes(data)

    def get_word(self):
        '''Read a big-endian 16-bit integer from the serial port.'''
        return struct.unpack('>H', self._recv_bytes(2))[0]

    def put_word(self, word):
        '''Write a big-endian 16-bit integer to the serial port.'''
        self._send_bytes(struct.pack('>H', word))

    def get_dword(self):
        '''Read a big-endian 32-bit integer from the serial port.'''
        return struct.unpack('>I', self._recv_bytes(4))[0]

    def put_dword(self, dword):
        '''Write a big-endian 32-bit integer to the serial port.'''
        self._send_bytes(struct.pack('>I', dword))

    def cmd_C8(self, subcommand):
        subcommands = {
            'B0': 0xB0,
            'B1': 0xB1,
            'B2': 0xB2,
            'B3': 0xB3,
            'B4': 0xB4,
            'B5': 0xB5,
            'B6': 0xB6,
            'B7': 0xB7,
            'B8': 0xB8,
            'B9': 0xB9,
            'BA': 0xBA,
            'C0': 0xC0,
            'C1': 0xC1,
            'C2': 0xC2,
            'C3': 0xC3,
            'C4': 0xC4,
            'C5': 0xC5,
            'C6': 0xC6,
            'C7': 0xC7,
            'C8': 0xC8,
            'C9': 0xC9,
            'CA': 0xCA,
            'CB': 0xCB,
            'CC': 0xCC,
        }
        self._send_bytes([self.commands['CMD_C8']])
        self._send_bytes([subcommands[subcommand]])
        sub_data = struct.unpack('B', self._recv_bytes(1))[0]

        status = self.get_word()
        if status != 0:
            print(status)
            raise Exception

        return sub_data

    def cmd_read32(self, addr, word_count):
        '''Read 32-bit words starting at an address.

        addr: The 32-bit starting address as an int.
        word_count: The number of words to read as an int.
        '''
        words = []

        self._send_bytes([self.commands['CMD_READ32']])
        self.put_dword(addr)
        self.put_dword(word_count)

        status = self.get_word()
        if status != 0:
            print(status)
            raise Exception

        for i in range(word_count):
            words.append(self.get_dword())

        status = self.get_word()
        if status != 0:
            print(status)
            raise Exception

        return words

    def cmd_write32(self, addr, words):
        '''Write 32 bit words starting at an address.

        addr: A 32-bit address as an int.
        words: A list of 32-bit ints to write starting at address addr.
        '''
        self._send_bytes([self.commands['CMD_WRITE32']])
        self.put_dword(addr)
        self.put_dword(len(words))

        status = self.get_word()
        if status > 0xff:
            print(status)
            raise Exception

        for word in words:
            self.put_dword(word)

        status = self.get_word()
        if status > 0xff:
            print(status)
            raise Exception

    def cmd_jump_da(self, addr):
        self._send_bytes([self.commands['CMD_JUMP_DA']])
        self.put_dword(addr)

        status = self.get_word()
        if status > 0xff:
            print(status)
            raise Exception

    def cmd_get_target_config(self):
        self._send_bytes([self.commands['CMD_GET_TARGET_CONFIG']])

        target_config = self.get_dword()
        print("Target config: 0x{:08X}".format(target_config))
        print("\tSBC enabled: {}".format(True if (target_config & 0x1) else False))
        print("\tSLA enabled: {}".format(True if (target_config & 0x2) else False))
        print("\tDAA enabled: {}".format(True if (target_config & 0x4) else False))

        status = self.get_word()
        if status > 0xff:
            print(status)
            raise Exception

    def cmd_get_hw_sw_ver(self):
        self._send_bytes([self.commands['CMD_GET_HW_SW_VER']])
        hw_subcode = self.get_word()
        hw_ver = self.get_word()
        sw_ver = self.get_word()

        status = self.get_word()
        if status != 0:
            print(status)
            raise Exception

        return (hw_subcode, hw_ver, sw_ver)

    def cmd_get_hw_code(self):
        self._send_bytes([self.commands['CMD_GET_HW_CODE']])
        hw_code = self.get_word()

        status = self.get_word()
        if status != 0:
            print(status)
            raise Exception

        return hw_code

    def cqdma_read32(self, addr, word_count):
        '''Read 32-bit words starting at an address, using the CQDMA peripheral.

        addr: The 32-bit starting address as an int.
        word_count: The number of words to read as an int.
        '''

        tmp_addr = self.soc['tmp_addr']
        cqdma_base = self.soc['cqdma_base']

        words = []
        for i in range(word_count):
            # Set DMA source address.
            self.cmd_write32(cqdma_base+0x1C, [addr+i*4])
            # Set DMA destination address.
            self.cmd_write32(cqdma_base+0x20, [tmp_addr])
            # Set DMA transfer length in bytes.
            self.cmd_write32(cqdma_base+0x24, [4])
            # Start DMA transfer.
            self.cmd_write32(cqdma_base+0x08, [0x00000001])
            # Stop and reset DMA transfer.
            self.cmd_write32(cqdma_base+0x0C, [0x00000001])
            # Read word from tmp_addr.
            words.extend(self.cmd_read32(tmp_addr, 1))

        return words

    def cqdma_write32(self, addr, words):
        '''Write 32 bit words starting at an address, using the CQDMA peripheral.

        addr: A 32-bit address as an int.
        words: A list of 32-bit ints to write starting at address addr.
        '''

        tmp_addr = self.soc['tmp_addr']
        cqdma_base = self.soc['cqdma_base']

        for i in range(len(words)):
            # Write word to tmp_addr.
            self.cmd_write32(tmp_addr, [words[i]])
            # Set DMA source address.
            self.cmd_write32(cqdma_base+0x1C, [tmp_addr])
            # Set DMA destination address.
            self.cmd_write32(cqdma_base+0x20, [addr+i*4])
            # Set DMA transfer length in bytes.
            self.cmd_write32(cqdma_base+0x24, [4])
            # Start DMA transfer.
            self.cmd_write32(cqdma_base+0x08, [0x00000001])
            # Stop and reset DMA transfer.
            self.cmd_write32(cqdma_base+0x0C, [0x00000001])
            # Write dummy word to tmp_addr for error detection.
            self.cmd_write32(tmp_addr, [0xc0ffeeee])

    def memory_read(self, addr, count, cqdma=False):
        '''Read a range of memory to a byte array.

        addr: A 32-bit address as an int.
        count: The length of data to read, in bytes.
        '''
        word_count = count//4
        if (count % 4) > 0:
            word_count += 1

        words = []
        if cqdma:
            words = self.cqdma_read32(addr, word_count)
        else:
            words = self.cmd_read32(addr, word_count)

        data = b''
        for word in words:
            data += struct.pack('<I', word)

        return data[:count]

    def memory_write(self, addr, data, cqdma=False):
        '''Write a byte array to a range of memory.

        addr: A 32-bit address as an int.
        data: The data to write.
        '''
        data = bytes(data)

        # Pad the byte array.
        remaining_bytes = (len(data) % 4)
        if remaining_bytes > 0:
            data += b'\0' * (4 - remaining_bytes)

        words = []
        for i in range(0, len(data), 4):
            words.append(struct.unpack_from('<I', data, i)[0])

        if cqdma:
            self.cqdma_write32(addr, words)
        else:
            self.cmd_write32(addr, words)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('port', type=str, help="The serial port you want to connect to.")
    args = parser.parse_args()

    usbdl = UsbDl(args.port, debug=False)

    # Disable WDT.
    print("Disabling WDT...")
    usbdl.cmd_write32(0x10007000, [0x22000000])

    # Get the security configuration of the target.
    usbdl.cmd_get_target_config()

    # Dump efuses to file.
    print("Dumping efuses...")
    efuses = usbdl.memory_read(usbdl.soc['efusec'], 0x1000)
    efuse_file = open("{}-efuses.bin".format(usbdl.soc['name'].lower()), 'wb')
    efuse_file.write(efuses)
    efuse_file.close()

    # Print a string to UART0.
    for byte in "Hello, there!\r\n".encode('utf-8'):
        usbdl.cmd_write32(0x11002000, [byte])

    # The C8 B1 command disables caches.
    usbdl.cmd_C8('B1')

    # Assume we have to use the CQDMA to access restricted memory.
    use_cqdma = True

    # Check if the bounds check method is available.
    if usbdl.soc.get('brom_g_bounds_check', False):
        # Disable bounds check.
        for (addr, data) in usbdl.soc['brom_g_bounds_check']:
            usbdl.cqdma_write32(addr, [data])

        # We can use normal read32/write32 commands now.
        use_cqdma = False

    # NOTE: Using the CQDMA method to dump a large (>4kB) chunk of memory,
    # like the entire BROM, will almost certainly fail and cause the CPU to
    # reset. To work around this, try dumping the memory in smaller chunks,
    # like 1kB, and saving them to disk, then reboot the SoC into BROM mode
    # again and dump the next chunk until you've dumped the memory you're
    # interested in.

    # Dump BROM.
    print("Dumping BROM...")
    start_time = time.time()
    brom = usbdl.memory_read(usbdl.soc['brom'], usbdl.soc['brom_size'], cqdma=use_cqdma)
    end_time = time.time()
    elapsed = end_time - start_time
    if len(brom) != usbdl.soc['brom_size']:
        print("Error: Failed to dump entire BROM.")
        sys.exit(1)

    print("Dumped the {}-byte BROM in {} seconds ({} bytes per second).".format(len(brom), elapsed, int(len(brom)/elapsed)))
    brom_file = open("{}-brom.bin".format(usbdl.soc['name'].lower()), 'wb')
    brom_file.write(brom)
    brom_file.close()
