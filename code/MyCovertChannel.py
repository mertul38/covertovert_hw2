from CovertChannelBase import CovertChannelBase
import socket
import time
import random
import hashlib
from scapy.all import IP, UDP, Raw
import threading

def to_sec(ms):
    return ms / 1000

class MyCovertChannel(CovertChannelBase):
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

    def regenerate_burst_sizes(self, burst_sizes, hist, burst_max):
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

class Receiver:
    sock: socket.socket
    covert_channel: MyCovertChannel
    burstsizes_to_signal: dict
    def __init__(self, covert_channel, params):
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

    def run(self):
        """
        Runs the receiver to listen and process incoming bursts.
        """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.ip, self.port))

        print(f"Listening for incoming packets on {self.ip}:{self.port}...")
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
        Starts timing after the first message and stops after the timeout.
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
                            self.sock.settimeout(to_sec(self.socket_awakening_delay))  # Avoid indefinite blocking
                        burst_count += 1
                        t3 = time.time()
                        tys.append(t3-t2)
                    except socket.timeout:
                        # print("DEBUG: Socket timeout")
                        continue
            except Exception as e:
                print(f"DEBUG: Collector stopped due to: {e}")
            print("collector stopped", txs, tys)
        def timer():
            """
            Timer thread to stop collection after a fixed timeout.
            """
            first_message_event.wait()  # Wait until the first message is received
            time.sleep(to_sec(self.delay_waiting_for_burst))  # Wait for the timeout after the first message
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
        self.burstsizes_to_signal = {}
        for signal in self.signal_order:  # Wait for 3 predefined bursts
            burst_count = 0
            while burst_count == 0:
                burst_count = self.receive_burst()
            self.burstsizes_to_signal[burst_count] = signal
        
        print(f"DEBUG: Received burst_sizes_to_signal: {self.burstsizes_to_signal}")

    def receive_byte(self):
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
        """
        received_data = ""
        while True:
            byte_buffer = self.receive_byte()
            char = self.covert_channel.convert_eight_bits_to_character(byte_buffer)
            received_data += char
            if char == self.stopping_character:    
                break
            print(f"DEBUG: Current Data: {received_data}")
            burst_sizes = self.covert_channel.regenerate_burst_sizes(
                list(self.burstsizes_to_signal.keys()),
                received_data,
                self.burst_max
                )
            self.burstsizes_to_signal = {k: v for k, v in zip(burst_sizes, self.signal_order)}
        return received_data

class Sender:
    sock: socket.socket
    covert_channel: MyCovertChannel
    signal_to_burstsize: dict
    def __init__(self, covert_channel, params):
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

    def run(self):
        """
        Runs the sender to generate and send bursts based on hashed sizes.
        """
        self.sock = self.create_socket()
        # Generate encrypted burst sizes
        self.generate_hash_based_burst_size()
        # Send predefined burst sizes
        self.send_burst_sizes()
        self.send_main_data()

        self.sock.close()

    def generate_hash_based_burst_size(self):
        """
        Generate burst sizes using timestamp and shared secret with a hash function.
        """
        timestamp = int(time.time())
        input_data = f"{timestamp}{self.shared_secret}".encode()
        hashed = hashlib.sha256(input_data).hexdigest()
        sizes = [(int(hashed[i:i+8], 16) % self.burst_max) + 1 for i in range(0, 24, 8)]

        while len(set(sizes)) != len(sizes):
            hashed = hashlib.sha256(hashed.encode()).hexdigest()
            sizes = [(int(hashed[i:i+8], 16) % self.burst_max) + 1 for i in range(0, 24, 8)]

        self.signal_to_burstsize = {k: v for k, v in zip(self.signal_order, sizes)}
        print(f"DEBUG: Generated signal_to_burstsize: {self.signal_to_burstsize}")

    def create_socket(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return sock
    
    def createUDPPacket(self, ip, port, data):
        """
        Creates a UDP packet using the given destination IP, port, and payload data.
        """
        return IP(dst=ip) / UDP(dport=port) / Raw(data)

    def send_burst(self, burst_size):
        """
        Sends a single burst of packets.
        """
        for _ in range(burst_size):
            packet = self.createUDPPacket(self.ip, self.port, self.send_dump_data)
            CovertChannelBase.send(self.covert_channel, packet)
        time.sleep(to_sec(self.delay_between_bursts))
    
    def send_burst_sizes(self):
        """
        Sends predefined burst sizes.
        """
        for size in self.signal_to_burstsize.values():
            self.send_burst(size)

    def send_main_data(self):
        """
        Sends main data.
        """
        message = self.covert_channel.generate_random_binary_message_with_logging(
            log_file_name=self.log_file_name,
            min_length=5,
            max_length=10
        )
        message_str = self.covert_channel.convert_binary_message_to_string(message)
        print(f"DEBUG: Sending main data: \n{message}\nString: {message_str}")
        byte_clock = 0
        for index, signal in enumerate(message):
            size = self.signal_to_burstsize[signal]
            self.send_burst(size)
            byte_clock += 1
            if byte_clock == 8:
                byte_clock = 0
                byte_index = index // 8
                hist = message_str[:byte_index+1]
                burst_sizes = self.covert_channel.regenerate_burst_sizes(
                    list(self.signal_to_burstsize.values()),
                    hist,
                    self.burst_max
                )
                self.signal_to_burstsize = {k: v for k, v in zip(self.signal_order, burst_sizes)}
                print(f"DEBUG: Updated burst sizes: {self.signal_to_burstsize} using hist: {hist}")
                # input("Press enter to continue...")