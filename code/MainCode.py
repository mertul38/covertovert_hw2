from CovertChannelBase import CovertChannelBase
import socket
import time

class MyCovertChannel(CovertChannelBase):
    def __init__(self):
        """
        Initializes the covert channel. Parameters will be set dynamically.
        """
        super().__init__()

    def binary_to_string(self, binary_message):
        """
        Converts a binary message (string of 0s and 1s) into a readable string using `convert_eight_bits_to_character`.
        Each 8 bits are converted into an ASCII character.
        """
        decoded_string = ""
        for i in range(0, len(binary_message), 8):
            eight_bits = binary_message[i:i + 8]
            if len(eight_bits) == 8:  # Ensure it's a complete byte
                decoded_string += self.convert_eight_bits_to_character(eight_bits)
        return decoded_string

    def send(
            self,
            log_file_name,
            ip,
            port,
            burst_size_one,
            burst_size_zero,
            burst_size_stop,
            delay_between_bursts,
            send_dump_data
            ):
        """
        Sends a covert message using UDP packet bursting.
        :param log_file_name: Log file to store the random message.
        :param ip: Receiver's IP address.
        :param port: Receiver's port.
        :param burst_size_one: Number of packets in a burst representing binary `1`.
        :param burst_size_zero: Number of packets in a burst representing binary `0`.
        :param delay_between_bursts: Delay between bursts (seconds).
        """
        current_timestamp = int(time.time())  # Current time in seconds
        timestamp_mod = current_timestamp % 256  # Reduce to 8 bits using modulo
        timestamp_byte = bytes([timestamp_mod])  # Convert to a single byte

        print(f"Original timestamp: {current_timestamp}")
        print(f"Timestamp mod 256: {timestamp_mod}")
        print(f"Timestamp byte: {timestamp_byte}")
        
        # Convert `send_dump_data` to bytes
        if isinstance(send_dump_data, int):  # Integer directly
            if send_dump_data < 0 or send_dump_data > 255:
                raise ValueError("send_dump_data must be in the range 0-255 to fit in a single byte.")
            send_dump_data = bytes([send_dump_data])  # Convert to a single byte
        elif isinstance(send_dump_data, str):  # Binary or hex as string
            if send_dump_data.startswith("0b"):  # Binary string
                send_dump_data = bytes([int(send_dump_data, 2)])
            elif send_dump_data.startswith("0x"):  # Hexadecimal string
                send_dump_data = bytes([int(send_dump_data, 16)])
            else:
                raise ValueError("send_dump_data string must start with '0b' for binary or '0x' for hex.")

        print(f"Converted send_dump_data to bytes: {send_dump_data}")
        # Generate a random binary message
        binary_message = self.generate_random_binary_message_with_logging(
            log_file_name,
            min_length=4,
            max_length=4
            )
        print(f"Binary message to send: {binary_message}")


        # Create a UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            for bit in binary_message:
                if bit == '1':
                    # Send a burst of packets for binary `1`
                    for _ in range(burst_size_one):
                        sock.sendto(send_dump_data, (ip, port))
                elif bit == '0':
                    # Send a smaller burst of packets for binary `0`
                    for _ in range(burst_size_zero):
                        sock.sendto(send_dump_data, (ip, port))
                
                # Delay between bursts
                time.sleep(delay_between_bursts)

            # Send a stop signal (special burst)
            for _ in range(burst_size_stop):  # Stop signal: 3 packets
                sock.sendto(send_dump_data, (ip, port))
            print("DEBUG: Sent stop signal")
        except Exception as e:
            print(f"ERROR: An exception occurred in send: {e}")
        finally:
            sock.close()

    def receive(
            self,
            log_file_name,
            ip,
            port,
            burst_size_one,
            burst_size_zero,
            burst_size_stop,
            delay_between_bursts
            ):
        """
        Receives and decodes the covert message from UDP packets.
        :param log_file_name: Log file to store the decoded message.
        :param ip: Receiver's IP address.
        :param port: Receiver's port.
        :param burst_size_one: Number of packets for binary `1`.
        :param burst_size_zero: Number of packets for binary `0`.
        :param delay_between_bursts: Delay between bursts (seconds).
        """
        # Bind the UDP socket to listen for incoming packets
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((ip, port))

        print(f"Listening for incoming packets on {ip}:{port}...")

        decoded_message = ""
        burst_count = 0
        is_timeout_set = False
        stop_received = False  # Track if the stop signal is received

        try:
            while not stop_received:
                try:
                    # Set a timeout to differentiate bursts
                    if not is_timeout_set:
                        sock.settimeout(delay_between_bursts / 2)
                        is_timeout_set = True
                    data, addr = sock.recvfrom(1024)
                    # Increment burst count for each received packet
                    burst_count += 1

                except socket.timeout:
                    # Timeout indicates the end of a burst
                    if burst_count == burst_size_one:
                        decoded_message += '1'
                        print("DEBUG: Decoded bit: '1'")
                    elif burst_count == burst_size_zero:
                        decoded_message += '0'
                        print("DEBUG: Decoded bit: '0'")
                    elif burst_count == burst_size_stop:
                        stop_received = True
                        print("DEBUG: Stop signal received.")
                    else:
                        print(f"DEBUG: Unexpected burst count: {burst_count}. Ignored.")

                    # Reset burst count for the next burst
                    burst_count = 0
                    is_timeout_set = False
                    # Debug current decoded message after each timeout
                    print("Current Decoded message: ", decoded_message)

        except Exception as e:
            print(f"ERROR: An exception occurred in receive: {e}")
        finally:
            print(f"Final Binary Message: {decoded_message}")
            # Convert the binary message into a string
            decoded_string = self.binary_to_string(decoded_message)
            print(f"Decoded Message as String: {decoded_string}")
            self.log_message(decoded_string, log_file_name)
            sock.close()