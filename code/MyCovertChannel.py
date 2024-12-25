from CovertChannelBase import CovertChannelBase
import socket
import time
import hashlib

def to_sec(ms):
    return ms / 1000

class Receiver:
    sock: socket.socket
    covert_channel: CovertChannelBase
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

    def run(self):
        """
        Runs the receiver to listen and process incoming bursts.
        """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print("Socket created", type(self.sock))
        self.sock.bind((self.ip, self.port))

        print(f"Listening for incoming packets on {self.ip}:{self.port}...")
        try:
            self.receive_burst_sizes()
            print(f"DEBUG: Received burst sizes (receiver): {self.burstsizes_to_signal}")
            received_data = self.receive_main_data()
            self.covert_channel.log_message(received_data, self.log_file_name)
        except Exception as e:
            print(f"ERROR: An exception occurred in Receiver: {e}")
        finally:
            self.sock.close()

    def receive_burst_sizes(self):
        self.burstsizes_to_signal = {}
        for signal in self.signal_order:  # Wait for 3 predefined bursts
            burst_count = 0
            while burst_count == 0:
                burst_count = self.receive_burst()
            print(f"DEBUG: Received burst of size {burst_count}")
            self.burstsizes_to_signal[burst_count] = signal
        
    def receive_burst(self):
        """
        Receives a single burst and counts the number of packets.
        """
        self.sock.settimeout(to_sec(self.delay_waiting_for_burst))
        burst_count = 0

        try:
            while True:
                self.sock.recvfrom(1024)
                burst_count += 1
        except socket.timeout:
            pass

        return burst_count

    def receive_main_data(self):
        """
        Receives and decodes the covert message from UDP packets.
        """
        data = ""
        byte_buffer = ""
        while True:
            burst_count = 0
            while burst_count == 0:
                burst_count = self.receive_burst()
            decoded_signal = self.burstsizes_to_signal[burst_count]
            byte_buffer += decoded_signal
            if len(byte_buffer) == 8:
                char = self.covert_channel.convert_eight_bits_to_character(byte_buffer)
                data += char
                if char == self.stopping_character:    
                    break
                byte_buffer = ""
                print(f"DEBUG: Data: {data}")
        return data


class Sender:
    sock: socket.socket
    covert_channel: CovertChannelBase
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

    def run(self):
        """
        Runs the sender to generate and send bursts based on hashed sizes.
        """
        self.sock = self.create_socket()
        # Generate encrypted burst sizes
        self.generate_hash_based_burst_size()
        print(f"DEBUG: Generated bit to burst size (sender): {self.signal_to_burstsize}")
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
        hashed = input_data.decode("utf-8")
        sizes = [0, 0, 0]
        while sizes[0] == sizes[1] or sizes[1] == sizes[2] or sizes[0] == sizes[2]:
            hashed = hashlib.sha256(hashed.encode()).hexdigest()
            sizes[0] = (int(hashed[0:8], 16) % 10) + 1
            sizes[1] = (int(hashed[8:16], 16) % 10) + 1
            sizes[2] = (int(hashed[16:24], 16) % 10) + 1

        self.signal_to_burstsize = {
            k: v for k, v in zip(self.signal_order, sizes)
        }
 
    def create_socket(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return sock
    
    def send_burst(self, burst_size):
        """
        Sends a single burst of packets.
        """
        for _ in range(burst_size):
            self.sock.sendto(self.send_dump_data, (self.ip, self.port))
        time.sleep(to_sec(self.delay_between_bursts))
    
    def send_burst_sizes(self):
        """
        Sends predefined burst sizes.
        """
        for size in self.signal_to_burstsize.values():
            print(f"DEBUG: Sending burst of size {size}")
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
        print(f"DEBUG: Sending main data: {message} {type(message)}")
        for signal in message:
            size = self.signal_to_burstsize[signal]
            print(f"DEBUG: Sending burst of size {size}")
            self.send_burst(size)



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
