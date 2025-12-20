import argparse
import binascii

def binary_to_hex(input_file, output_file):
    """
    Reads a binary file and converts it to a hex-encoded text file.
    """
    try:
        with open(input_file, 'rb') as f_in:
            binary_data = f_in.read()
            hex_data = binascii.hexlify(binary_data).decode('ascii')
        with open(output_file, 'w') as f_out:
            f_out.write(hex_data)
        print(f"Successfully converted binary file '{input_file}' to hex file '{output_file}'.")
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

def hex_to_binary(input_file, output_file):
    """
    Reads a hex-encoded text file and converts it back to a binary file.
    """
    try:
        with open(input_file, 'r') as f_in:
            hex_data = f_in.read().strip()
            binary_data = binascii.unhexlify(hex_data)
        with open(output_file, 'wb') as f_out:
            f_out.write(binary_data)
        print(f"Successfully converted hex file '{input_file}' to binary file '{output_file}'.")
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.")
    except binascii.Error as e:
        print(f"Error decoding hex data: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

def main():
    """
    Main function to parse arguments and call the appropriate conversion function.
    """
    parser = argparse.ArgumentParser(description="Convert files to and from hex representation.")
    parser.add_argument('-i', '--input', required=True, help="Input file path.")
    parser.add_argument('-o', '--output', required=True, help="Output file path.")
    parser.add_argument('-m', '--mode', required=True, choices=['to_hex', 'from_hex'], help="Conversion mode: 'to_hex' (binary to hex) or 'from_hex' (hex to binary).")

    args = parser.parse_args()

    if args.mode == 'to_hex':
        binary_to_hex(args.input, args.output)
    elif args.mode == 'from_hex':
        hex_to_binary(args.input, args.output)

if __name__ == "__main__":
    main()