
# UDP Covert Channel Documentation

## Choosen Covert Type: Covert Storage Channel that exploits Packet Bursting using UDP [Code: CSC-PB-UDP]

This documentation describes the implementation of a UDP-based covert channel. The covert channel uses packet bursting to transmit covert messages between a sender and receiver.

---

## Overview

The UDP covert channel consists of three main components:

1. **CovertChannelBase**: The base class providing shared utilities for the covert channel.
2. **MyCovertChannel**: The main class that integrates both the sender and receiver logic and provides utilities for message conversion and burst size generation.
3. **Sender and Receiver**: These handle sending and receiving messages using bursts of UDP packets.

---

## MyCovertChannel Class

### Description

The `MyCovertChannel` class acts as the main interface to send and receive covert messages. It integrates `Sender` and `Receiver` classes for their respective roles and includes utilities for:

- Message conversion.
- Burst size generation and regeneration.
- Time unit conversions.

### Methods

#### `send(**params)`
- Initializes a `Sender` instance with given parameters and starts the sending process.

#### `receive(**params)`
- Initializes a `Receiver` instance with given parameters and starts the receiving process.

#### `convert_binary_message_to_string(binary_message)`
- Converts a binary message to its string representation by interpreting each 8 bits as a character.

#### `regenerate_burst_sizes(burst_sizes, hist, burst_max)`
- Modifies burst sizes based on the history of the message.
- Adds ±1 to burst sizes depending on whether the sum of ASCII values in the history is even or odd.

#### `to_sec(ms)`
- Converts milliseconds to seconds.

---

## Receiver Class

### Description

The `Receiver` class listens for UDP packets, decodes covert messages from bursts of packets, and logs the received data.

### Parameters

- **log_file_name**: Name of the file to log received data.
- **ip**: IP address to bind the socket.
- **port**: Port to bind the socket.
- **signal_order**: List of signal-to-burst mappings.
- **delay_waiting_for_burst**: Delay to wait for a burst after receiving the first packet.
- **stopping_character**: Character marking the end of the message.
- **shared_secret**: Shared secret for burst size generation.
- **burst_max**: Maximum burst size.
- **socket_awakening_delay**: Socket timeout duration.

### Methods

#### `run()`
- Binds the socket and starts listening for incoming packets.
- Calls `receive_burst_sizes` to map signals to burst sizes.
- Calls `receive_main_data` to decode and log the covert message.

#### `receive_burst()`
- Counts packets in a single burst.
- Uses threads for message collection and timeout control.

#### `receive_burst_sizes()`
- Maps burst sizes to signals by receiving predefined bursts for each signal in `signal_order`.

#### `receive_byte()`
- Receives and decodes a single byte (8 bits) from bursts.

#### `receive_main_data()`
- Receives and decodes the complete covert message until the stopping character is reached.
- Dynamically regenerates burst sizes based on received history.

---

## Sender Class

### Description

The `Sender` class sends covert messages as bursts of UDP packets. Each burst represents a signal corresponding to a binary message.

### Parameters

- **log_file_name**: Name of the log file to store sent data.
- **ip**: IP address of the receiver.
- **port**: Port of the receiver.
- **signal_order**: List of signals used in the covert channel.
- **delay_between_bursts**: Delay between bursts in seconds.
- **send_dump_data**: Data payload for each packet.
- **shared_secret**: Shared secret for burst size generation.
- **burst_max**: Maximum burst size.

### Methods

#### `run()`
- Creates a UDP socket.
- Generates and sends burst sizes for predefined signals.
- Sends the main covert message.

#### `generate_hash_based_burst_size()`
- Uses a hash-based mechanism to generate unique burst sizes.
- Ensures burst sizes are unique and derived from the shared secret and current timestamp.

#### `create_socket()`
- Creates a UDP socket for packet transmission.

#### `createUDPPacket(ip, port, data)`
- Creates a Scapy-based UDP packet with the specified IP, port, and data payload.

#### `send_burst(burst_size)`
- Sends a burst of packets based on the specified burst size.

#### `send_burst_sizes()`
- Sends bursts representing the predefined signals.

#### `send_main_data()`
- Sends the covert message in binary form, with each bit represented by a burst of packets.
- Updates burst sizes dynamically based on message history.

---

## Covert Message Flow

### Sending

1. The sender generates burst sizes for each signal based on a shared secret.
2. Predefined bursts are sent to establish the signal-to-burst mapping.
3. The covert message is sent as a series of bursts, with each burst representing a bit in the binary message.
4. Burst sizes are updated dynamically based on the history of sent messages.

### Receiving

1. The receiver listens for bursts and counts packets to map burst sizes to signals.
2. It decodes the covert message by receiving bursts for each byte (8 bits).
3. The process continues until the stopping character is received.
4. Burst sizes are updated dynamically based on the received history.

---

## Utilities

### Burst Size Regeneration

- Burst sizes are dynamically adjusted based on the ASCII sum of the message history.
- Even sum: Subtract 1 from each burst size.
- Odd sum: Add 1 to each burst size.

### Message Conversion

- Binary messages are converted to strings by interpreting each 8 bits as a character.
- Strings are converted back to binary for transmission.

---

## Example Parameters

### Receiver Parameters
```python
{
    'log_file_name': 'receiver_log.txt',
    'ip': '127.0.0.1',
    'port': 12345,
    'signal_order': [0, 1],
    'delay_waiting_for_burst': 200,
    'stopping_character': '\0',
    'shared_secret': 'mysecret',
    'burst_max': 10,
    'socket_awakening_delay': 100
}
```

### Sender Parameters
```python
{
    'log_file_name': 'sender_log.txt',
    'ip': '127.0.0.1',
    'port': 12345,
    'signal_order': [0, 1],
    'delay_between_bursts': 0.2,
    'send_dump_data': 'test',
    'shared_secret': 'mysecret',
    'burst_max': 10
}
```

---

## Debugging Tips

- Ensure `signal_order` is consistent between the sender and receiver.
- Verify that burst sizes remain unique during hash generation.
- Use the log files to track sent and received messages.
- Monitor the socket timeout settings to avoid blocking issues.

---


## References

- Scapy Documentation: [https://scapy.net/](https://scapy.net/)
- Python Socket Programming: [https://docs.python.org/3/library/socket.html](https://docs.python.org/3/library/socket.html)



