import serial
import time
import threading
import struct 

# =============================================================================
#  CLASS TO MANAGE SERIAL COMMUNICATION
# =============================================================================

class SerialCommunication:
    """
    Manages the serial port connection, including reading and writing data.
    It uses a separate thread to continuously read incoming data without blocking
    the main program.
    """
    def __init__(self, port, baudrate=115200, timeout=1):
        """
        Initializes the serial communication and the reading thread.
        Args:
            port (str): The serial port to connect to (e.g., "COM11" or "/dev/ttyUSB0").
            baudrate (int): The communication speed in bits per second.
            timeout (int): Read timeout value in seconds.
        """
        self.ser = None
        try:
            self.ser = serial.Serial(port, baudrate, timeout=timeout)
            print(f"Serial port '{port}' opened successfully at {baudrate} bps.")
        except serial.SerialException as e:
            print(f"ERROR: Could not open serial port '{port}'.")
            print(f"Error detail: {e}")
            print("Please check if the port is correct and not in use by another program.")
            raise

        self.received_data = {}
        self.running = True
        
        # Start a background thread to read data from the serial port
        self.read_thread = threading.Thread(target=self._read_serial_data)
        self.read_thread.daemon = True # Allows the main program to exit even if this thread is running
        self.read_thread.start()

    def _read_serial_data(self):
        """
        This method runs in the background thread to read and process data.
        It expects data in a specific comma-separated format:
        "id,v1,v2,v3,v4,latency,id,v1,v2,v3,v4,latency,..."
        """
        while self.running:
            if self.ser and self.ser.in_waiting > 0:
                try:
                    # Read one line (until a newline character) from the serial port
                    line_bytes = self.ser.readline()
                    # Decode the bytes into a UTF-8 string and remove whitespace/null chars
                    line_str = line_bytes.decode('utf-8').strip()
                    line_str = line_str.rstrip('\x00')

                    # Skip empty lines
                    if not line_str:
                        continue

                    print(f"Received: '{line_str}'")
                    
                    parts = line_str.split(',')

                    # Check if the data is valid (must be in blocks of 6 values)
                    if len(parts) >= 2 and len(parts) % 6 == 0:
                        # Process each block of data
                        for i in range(0, len(parts), 6):
                            block = parts[i:i+6]
                            try:
                                robot_id = int(block[0])
                                velocities = [float(v) for v in block[1:5]]
                                latency = float(block[5])

                                # Store the parsed data in a dictionary
                                self.received_data[robot_id] = {
                                    'velocities': velocities,
                                    'latency': latency,
                                    'timestamp': time.time() # Record when the data was received
                                }
                            except (ValueError, IndexError):
                                print(f"  -> Warning: Malformed data block received: {block}")
                    else:
                        # If the format is not recognized, store it as raw data
                        self.received_data['raw'] = line_str

                except UnicodeDecodeError:
                    print(f"  -> Warning: Unicode decode error. Received data might be corrupted.")
                except Exception as e:
                    print(f"  -> Unexpected error in reading thread: {e}")
            
            # Brief pause to prevent the loop from consuming 100% CPU
            time.sleep(0.01)

    # --- 2. KEY CHANGE IN THE CLASS ---
    def send_command(self, command):
        """
        Sends a command string or a bytes object to the serial port.
        This allows sending both human-readable text and packed binary data.
        """
        if self.ser and self.ser.is_open:
            data_to_send = None
            
            # If the command is a string, encode it to bytes.
            if isinstance(command, str):
                if not command.endswith('\n'):
                    command += '\n' # Ensure the command ends with a newline
                data_to_send = command.encode('utf-8')
            
            # If the command is already bytes, use it directly.
            elif isinstance(command, bytes):
                data_to_send = command
            
            else:
                print(f"ERROR: Data type '{type(command)}' cannot be sent.")
                return

            try:
                self.ser.write(data_to_send)
                # print(f"Sent: {data_to_send}") # Uncomment for debugging
            except serial.SerialException as e:
                print(f"ERROR while sending data: {e}")

    def get_data(self, robot_id):
        """Returns the last received data for a specific robot ID."""
        return self.received_data.get(robot_id)

    def close(self):
        """Closes the serial port and safely stops the reading thread."""
        print("Closing serial communication...")
        self.running = False
        if hasattr(self, 'read_thread'):
            self.read_thread.join() # Wait for the thread to finish
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Serial port closed.")

# =============================================================================
#  EXAMPLE USAGE IN THE MAIN SCRIPT
# =============================================================================

if __name__ == "__main__":
    SERIAL_PORT = "COM11" # Change this to your serial port
    BAUDRATE = 115200

    communicator = None
    try:
        # Initialize the communication handler
        communicator = SerialCommunication(SERIAL_PORT, BAUDRATE)
        
        target_robot_id = 0
        counter = 0

        while True:
            # --- 3. KEY CHANGE IN THE MAIN LOOP ---
            
            # Create a list of 12 integers to be sent.
            values_to_send = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
            
            # Define the data format for packing:
            # '<' specifies little-endian byte order, common for ARM processors (like STM32).
            # '12i' specifies twelve 32-bit signed integers.
            data_format = '<12i'
            
            # Pack the list of values into a bytes object according to the specified format.
            # The '*' unpacks the list into individual arguments for the pack function.
            command_in_bytes = struct.pack(data_format, *values_to_send)
            
            # Send the packed bytes object over serial.
            communicator.send_command(command_in_bytes)
            
            # Get the latest data received from the target robot.
            current_data = communicator.get_data(target_robot_id)
            
            print("-" * 30)
            if current_data:
                print(f"Last data received from Robot {target_robot_id}:")
                print(f"  - Velocities: {current_data['velocities']}")
                print(f"  - Latency: {current_data['latency']:.4f} s")
                print(f"  - Received: {time.time() - current_data['timestamp']:.2f} s ago")
            else:
                print(f"Waiting for data from Robot {target_robot_id}...")

            counter += 1
            time.sleep(1) # Wait for 1 second before the next iteration.

    except serial.SerialException:
        print("Program terminated due to a serial port failure.")
    except KeyboardInterrupt:
        print("\nProgram interrupted by user.")
    finally:
        # Ensure the serial port is closed properly on exit.
        if communicator:
            communicator.close()
