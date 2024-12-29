from CovertChannelBase import CovertChannelBase
import socket
import time
import random
import hashlib
from scapy.all import IP, UDP, Raw
import threading


class MyCovertChannel(CovertChannelBase):
    """
    - This class uses UDP packet bursting to send and receive covert messages.
    - Recieve functions are implemented in the `Receiver` class.
    - Send functions are implemented in the `Sender` class.
    - Commonly used functions are implemented in the this class class.
    """
    def __init__(self):
        """
        Initializes the covert channel. Parameters will be set dynamically.
        """
        super().__init__()

    def send(self, **params):
        """
        Main send function.
        """
        sender = Sender(self, params)
        sender.run()

    def receive(self, **params):
        """
        Main receive function.
        """
        receiver = Receiver(self, params)
        receiver.run()

    def convert_binary_message_to_string(self, binary_message):
        """
        Converts a binary message to a string.
        """
        return ''.join(chr(int(binary_message[i:i+8], 2)) for i in range(0, len(binary_message), 8))

    def regenerate_burst_sizes(self, burst_sizes, hist, burst_max, history_size):
        """
        - It regenerates the burst sizes based on the history of the message.
        - It sums up the ASCII values of the characters in the history.
        - If the sum is even, it adds -1 to the burst sizes. Otherwise, it adds 1.
        """
        hist = hist[-history_size:]
        ords = [ord(c) for c in hist]
        sum_ords = sum(ords)
        check = sum_ords % 2
        if check == 0:
            additional = -1
        else:
            additional = 1
        for i in range(len(burst_sizes)):
            burst_sizes[i] = ((burst_sizes[i] + additional) % burst_max) + 1
            
        return burst_sizes

    def to_sec(self, ms):
        """
        Converts milliseconds to seconds.

        :param ms: Time duration in milliseconds.
        :return: Time duration in seconds.
        """
        return ms / 1000

class Receiver:
    """
    - Represents the receiver of the covert channel.
    - Receives bursts of packets and decodes the covert message.
    """
    sock: socket.socket
    covert_channel: MyCovertChannel
    burstsizes_to_signal: dict
    """
    Keys are burst sizes, values are corresponding signals, e.g. {3= '0', 4= '1'}
    """
    def __init__(self, covert_channel, params):

        """
        - Constructor for the Receiver class.
        - It takes a covert channel object and a set of parameters for the receiver.
        - It sets the parameters and the covert channel object as attributes of the class.
        """
        self.covert_channel = covert_channel

        self.log_file_name = params['log_file_name']
        self.ip = params['ip']
        self.port = params['port']
        self.signal_order = params['signal_order']
        self.signal_order = [str(v) for v in self.signal_order]
        self.delay_waiting_for_burst = params['delay_waiting_for_burst']
        self.stopping_character = params['stopping_character']
        self.shared_secret = params['shared_secret']
        self.burst_max = params['burst_max']
        self.socket_awakening_delay = params['socket_awakening_delay']
        self.history_size = params['history_size']

    def run(self):

        """
        - Runs the receiver.
        - Binds to the UDP socket and starts listening for incoming packets.
        - Calls `receive_burst_sizes` and `receive_main_data` to receive the burst sizes and the covert message.
        - Logs the received data to a file.
        - Closes the socket at the end.
        """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.ip, self.port))

        # print(f"Listening for incoming packets on {self.ip}:{self.port}...")
        try:
            self.receive_burst_sizes()
            received_data = self.receive_main_data()
            self.covert_channel.log_message(received_data, self.log_file_name)
        except Exception as e:
            print(f"ERROR: An exception occurred in Receiver: {e}")
        finally:
            self.sock.close()


    def receive_burst(self):
        """
        Receives a single burst and counts the number of packets.
        Starts timing after the first message and stops after stop signal and timeout.
        """
        burst_count = 0
        start_t = None  # Start time for the burst
        stop_event = threading.Event()  # Event to stop the collector thread
        first_message_event = threading.Event()  # Event to signal the arrival of the first message

        def collect_messages():
            nonlocal burst_count, start_t
            txs = []
            tys = []
            try:
                self.sock.settimeout(None)  # Avoid indefinite blocking
                while not stop_event.is_set():
                    # Non-blocking check if the stop event is set before calling recvfrom
                    try:
                        t1 = time.time()
                        data, addr = self.sock.recvfrom(1024)
                        t2 = time.time()
                        txs.append(t2-t1)
                        current_time = time.time()
                        if start_t is None:
                            # Start the timer after the first message
                            start_t = current_time
                            first_message_event.set()  # Signal that the first message has arrived
                            self.sock.settimeout(self.covert_channel.to_sec(self.socket_awakening_delay))  # Avoid indefinite blocking
                        burst_count += 1
                        t3 = time.time()
                        tys.append(t3-t2)
                    except socket.timeout:
                        # print("DEBUG: Socket timeout")
                        continue
            except Exception as e:
                pass
                # print(f"DEBUG: Collector stopped due to: {e}")
            # print("collector stopped", txs, tys)
        def timer():
            """
            Timer thread to stop collection after a fixed timeout.
            """
            first_message_event.wait()  # Wait until the first message is received
            time.sleep(self.covert_channel.to_sec(self.delay_waiting_for_burst))  # Wait for the timeout after the first message
            stop_event.set()  # Signal the collector thread to stop

        # Start the threads
        collector_thread = threading.Thread(target=collect_messages)
        timer_thread = threading.Thread(target=timer)

        collector_thread.start()
        timer_thread.start()

        # Wait for both threads to complete
        timer_thread.join()  # Ensure the timer thread finishes first
        collector_thread.join()  # Then ensure the collector thread stops

        # Calculate time intervals between packets

        return burst_count


    def receive_burst_sizes(self):
        
        """
        Receives the burst sizes corresponding to the signal order.
        It waits for packets to arrive and records the number of packets in each burst.
        It then maps the burst size to the corresponding signal.
        """
        self.burstsizes_to_signal = {}
        for signal in self.signal_order: 
            burst_count = 0
            while burst_count == 0:
                burst_count = self.receive_burst()
            self.burstsizes_to_signal[burst_count] = signal
        
        # print(f"DEBUG: Received burst_sizes_to_signal: {self.burstsizes_to_signal}")

    def receive_byte(self):
        """
        Receives and decodes a single byte from the covert message.
        The byte is received 8 bits at a time, with each bit represented by a burst size.
        The burst size is converted to a signal using the burst sizes dictionary.
        The signal is then appended to the byte buffer.
        The process is repeated until all 8 bits have been received.
        :return: The decoded byte as a string of 0s and 1s.
        """
        byte_buffer = ""
        burst_count = 0
        while burst_count < 8:
            burst_size = 0
            while burst_size == 0:
                burst_size = self.receive_burst()
            decoded_signal = self.burstsizes_to_signal[burst_size]
            byte_buffer += decoded_signal
            burst_count += 1

        return byte_buffer
    
    def receive_main_data(self):
        """
        Receives and decodes the covert message from UDP packets.

        The covert message is received one byte at a time, with each byte being
        represented by 8 bits. Each bit is represented by a burst size, which
        is decoded using the burst sizes dictionary. The decoded byte is then
        converted to a character and appended to the received data string.

        The process is repeated until the stopping character is received.

        :return: The decoded message as a string.
        """
        received_data = ""
        while True:
            byte_buffer = self.receive_byte()
            # Convert the 8-bit byte buffer to a character
            char = self.covert_channel.convert_eight_bits_to_character(byte_buffer)
            # Append the character to the received data
            received_data += char
            # Check if we have reached the stopping character
            if char == self.stopping_character:    
                break
            # print(f"DEBUG: Current Data: {received_data}")
            # Regenerate the burst sizes dictionary based on the current data
            burst_sizes = self.covert_channel.regenerate_burst_sizes(
                list(self.burstsizes_to_signal.keys()),
                received_data,
                self.burst_max,
                self.history_size
                )
            # Update the burst sizes dictionary
            self.burstsizes_to_signal = {k: v for k, v in zip(burst_sizes, self.signal_order)}
        return received_data

class Sender:
    sock: socket.socket
    covert_channel: MyCovertChannel
    signal_to_burstsize: dict
    """
    Keys are the signals and values are the burst sizes, e.g. {'0'= 4, '1'= 3}
    """
    def __init__(self, covert_channel, params):
        """
        Initializes a Sender object with the given parameters.

        :param covert_channel: The CovertChannelBase object to use for sending.
        :param params: A dictionary containing the following parameters:
            - log_file_name: The name of the log file to store the sent data.
            - ip: The IP address of the receiver.
            - port: The port of the receiver.
            - signal_order: A list of the order of the signals in the covert channel.
            - delay_between_bursts: The delay in seconds between each burst.
            - send_dump_data: The data to be sent in each burst.
            - shared_secret: The shared secret used for the covert channel.
            - burst_max: The maximum number of packets in a burst.
        """
        self.covert_channel = covert_channel
        
        self.log_file_name = params['log_file_name']
        self.ip = params['ip']
        self.port = params['port']
        self.signal_order = params['signal_order']
        self.signal_order = [str(v) for v in self.signal_order]
        self.delay_between_bursts = params['delay_between_bursts']
        self.send_dump_data = params['send_dump_data']
        if isinstance(self.send_dump_data, str):
            self.send_dump_data = self.send_dump_data.encode()
        self.shared_secret = params['shared_secret']
        self.burst_max = params['burst_max']
        self.history_size = params['history_size']

    def run(self):

        """
        Starts the sender. It creates a socket, generates the burst sizes using the
        shared secret and the timestamp, sends the predefined burst sizes, and sends
        the main data. It then closes the socket.

        """
        self.sock = self.create_socket()
        self.generate_hash_based_burst_size()
        self.send_burst_sizes()
        self.send_main_data()

        self.sock.close()

    def generate_hash_based_burst_size(self):

        """
        Generates burst sizes based on a shared secret and the current timestamp.
        The burst sizes are generated as follows:
        - The current timestamp and the shared secret are concatenated and hashed with SHA-256.
        - The resulting hash is split into 8 byte chunks, and each chunk is converted to an integer and reduced modulo self.burst_max.
        - The resulting list of integers is used as the burst sizes.
        - If there are any duplicate burst sizes, the process is repeated with the previous hash as input until a set of unique burst sizes is generated.
        """
        timestamp = int(time.time())
        input_data = f"{timestamp}{self.shared_secret}".encode()
        hashed = hashlib.sha256(input_data).hexdigest()
        sizes = [(int(hashed[i:i+8], 16) % self.burst_max) + 1 for i in range(0, 24, 8)]

        while len(set(sizes)) != len(sizes):
            hashed = hashlib.sha256(hashed.encode()).hexdigest()
            sizes = [(int(hashed[i:i+8], 16) % self.burst_max) + 1 for i in range(0, 24, 8)]

        self.signal_to_burstsize = {k: v for k, v in zip(self.signal_order, sizes)}
        # print(f"DEBUG: Generated signal_to_burstsize: {self.signal_to_burstsize}")

    def create_socket(self):
        """
        Creates a UDP socket to be used for sending packets.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return sock
    
    def createUDPPacket(self, ip, port, data):
        """
        Creates a UDP packet for sending over the covert channel.

        Parameters:
        ip (str): Destination IP address.
        port (int): Destination port.
        data (bytes): Payload of the packet.
        """
        return IP(dst=ip) / UDP(dport=port) / Raw(data)

    def send_burst(self, burst_size):
        """
        Sends a burst of packets.

        Parameters:
        burst_size (int): The number of packets in the burst.

        The function sends a burst of packets with the payload specified in `send_dump_data` to the IP address and port specified in `ip` and `port` respectively.
        The delay between packets is specified in `delay_between_bursts`.
        """
        for _ in range(burst_size):
            packet = self.createUDPPacket(self.ip, self.port, self.send_dump_data)
            CovertChannelBase.send(self.covert_channel, packet)
        time.sleep(self.covert_channel.to_sec(self.delay_between_bursts))
    
    def send_burst_sizes(self):
        """
        Sends burst sizes corresponding to the signal order.
        """
        for size in self.signal_to_burstsize.values():
            self.send_burst(size)

    def send_main_data(self):
        """
        Sends a random binary message of length between 5 and 10 over the covert channel.
        The message is first logged to a file, then sent over the channel by converting the binary message to a string and sending each character as a burst of packets with a size corresponding to the signal order.
        The burst sizes are updated every 8 characters using the regenerate_burst_sizes method of the covert channel object.
        """
        message = self.covert_channel.generate_random_binary_message_with_logging(
            log_file_name=self.log_file_name,
            min_length=16,
            max_length=16
        )
        message_str = self.covert_channel.convert_binary_message_to_string(message)
        # print(f"DEBUG: Sending main data: \n{message}\nString: {message_str}")
        byte_clock = 0
        start_time = time.time()
        for index, signal in enumerate(message):
            size = self.signal_to_burstsize[signal]
            self.send_burst(size)
            if index == len(message) - 1:
                end_time = time.time()
                total_time = end_time - start_time
                # print(f"DEBUG: Time taken to send main data: {total_time}")
            byte_clock += 1
            if byte_clock == 8:
                byte_clock = 0
                byte_index = index // 8
                hist = message_str[:byte_index+1]
                burst_sizes = self.covert_channel.regenerate_burst_sizes(
                    list(self.signal_to_burstsize.values()),
                    hist,
                    self.burst_max,
                    self.history_size
                )
                self.signal_to_burstsize = {k: v for k, v in zip(self.signal_order, burst_sizes)}
                # print(f"DEBUG: Updated burst sizes: {self.signal_to_burstsize} using hist: {hist}")
                # input("Press enter to continue...")