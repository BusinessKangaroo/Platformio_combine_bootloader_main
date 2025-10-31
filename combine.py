Import("env")
import os

bootloader = "bootloader.hex"

def parse_intel_hex(filename):
    """Parse Intel HEX file and return list of (address, data) tuples"""
    records = []
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line.startswith(':'):
                continue
            
            # Parse Intel HEX record
            byte_count = int(line[1:3], 16)
            address = int(line[3:7], 16)
            record_type = int(line[7:9], 16)
            
            if record_type == 0:  # Data record
                data = []
                for i in range(byte_count):
                    data.append(int(line[9 + i*2:11 + i*2], 16))
                records.append((address, data))
            elif record_type == 1:  # End of file
                break
    
    return records

def create_intel_hex(records, filename):
    """Create Intel HEX file from list of (address, data) tuples"""
    with open(filename, 'w') as f:
        for address, data in records:
            byte_count = len(data)
            # Create data record (type 00)
            line = f":{byte_count:02X}{address:04X}00"
            
            checksum = byte_count + (address >> 8) + (address & 0xFF) + 0x00
            for byte_val in data:
                line += f"{byte_val:02X}"
                checksum += byte_val
            
            checksum = (-checksum) & 0xFF
            line += f"{checksum:02X}"
            f.write(line + '\n')
        
        # End of file record
        f.write(":00000001FF\n")

def combine_hex_files(bootloader_file, firmware_file, output_file):
    """Combine bootloader and firmware hex files"""
    try:
        # Parse both files
        bootloader_records = parse_intel_hex(bootloader_file)
        firmware_records = parse_intel_hex(firmware_file)
        
        # Combine records (bootloader first, then firmware)
        combined_records = bootloader_records + firmware_records
        
        # Sort by address
        combined_records.sort(key=lambda x: x[0])
        
        # Create combined hex file
        create_intel_hex(combined_records, output_file)
        
        return True
    except Exception as e:
        print(f"❌ Error combining hex files: {e}")
        return False

def after_build(source, target, env):
    # Convert .elf to .hex first if needed
    elf_file = target[0].get_path()
    hex_file = elf_file.replace('.elf', '.hex')
    
    # Generate hex file if it doesn't exist
    if not os.path.exists(hex_file):
        env.Execute(f'avr-objcopy -O ihex "{elf_file}" "{hex_file}"')
    
    firmware = hex_file
    combined = os.path.join(env["PROJECT_DIR"], "combined.hex")
    
    # Check if bootloader exists
    bootloader_path = os.path.join(env["PROJECT_DIR"], bootloader)
    if not os.path.exists(bootloader_path):
        print(f"❌ Bootloader file not found: {bootloader_path}")
        return
    
    # Check if firmware hex exists
    if not os.path.exists(firmware):
        print(f"❌ Firmware hex not found: {firmware}")
        return
    
    # Combine hex files without external tools
    if combine_hex_files(bootloader_path, firmware, combined):
        print("✅ Combined hex written to:", combined)
    else:
        print("❌ Failed to combine hex files")

env.AddPostAction("$BUILD_DIR/firmware.elf", after_build)