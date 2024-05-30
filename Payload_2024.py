import time
import subprocess
import picamera
import smbus2
import RPi.GPIO as GPIO
import pandas as pd
from datetime import datetime
 
# Setup I2C bus
i2c_bus = smbus2.SMBus(1)

# Constants for TMP275
TMP275_ADDRESS = 0x48
TMP275_TEMP_REG = 0x00

# Setup GPIO for arming switch
ARMING_SWITCH_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(ARMING_SWITCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Data logging setup
data_log_path = '/payload/flight_data.csv'
data_columns = ['timestamp', 'temperature', 'accel_x', 'accel_y', 'accel_z']
data_log = []

# Read temperature from TMP275
def read_temperature():
    temp_raw = i2c_bus.read_word_data(TMP275_ADDRESS, TMP275_TEMP_REG)
    temp_c = ((temp_raw & 0xFF) << 8 | (temp_raw >> 8)) / 256.0
    return temp_c

# Read acceleration from LSM9DS1 
def read_imu_data():
    # LSM9DS1 I2C addresses
    LSM9DS1_XLG = 0x6B
    LSM9DS1_MAG = 0x1E
    
    accel_x_l = i2c_bus.read_byte_data(LSM9DS1_XLG, 0x28)
    accel_x_h = i2c_bus.read_byte_data(LSM9DS1_XLG, 0x29)
    accel_x = (accel_x_h << 8) | accel_x_l
    
    accel_y_l = i2c_bus.read_byte_data(LSM9DS1_XLG, 0x2A)
    accel_y_h = i2c_bus.read_byte_data(LSM9DS1_XLG, 0x2B)
    accel_y = (accel_y_h << 8) | accel_y_l
    
    accel_z_l = i2c_bus.read_byte_data(LSM9DS1_XLG, 0x2C)
    accel_z_h = i2c_bus.read_byte_data(LSM9DS1_XLG, 0x2D)
    accel_z = (accel_z_h << 8) | accel_z_l
    
    # Convert to g's
    accel_x_g = accel_x * 0.000061
    accel_y_g = accel_y * 0.000061
    accel_z_g = accel_z * 0.000061
   
    return {'accel_x': accel_x_g, 'accel_y': accel_y_g, 'accel_z': accel_z_g}

# Check if the system is armed
def is_system_armed():
    return GPIO.input(ARMING_SWITCH_PIN) == GPIO.LOW

# Main function
def main():
    with picamera.PiCamera() as camera:
        while True:
            if is_system_armed():
                # Start recording video
                h264_path = '/Payload/Flight/Footage.h264'
                mp4_path = '/Payload/Flight/Footage.mp4'
                
                camera.start_recording(h264_path)
                print("Recording started.")
                
                try:
                    while is_system_armed():
                        # Read temperature
                        temperature = read_temperature()
                        
                        # Read IMU data
                        imu_data = read_imu_data()
                        
                        # Log data with timestamp
                        timestamp = datetime.now().isoformat()
                        data_log.append([timestamp, temperature, imu_data['accel_x'], imu_data['accel_y'], imu_data['accel_z']])
                        print(f"{timestamp}: Temperature: {temperature:.2f} C, Accelerometer X: {imu_data['accel_x']:.2f} g, "
                              f"Accelerometer Y: {imu_data['accel_y']:.2f} g, Accelerometer Z: {imu_data['accel_z']:.2f} g")
                        
                        # Continue recording
                        camera.wait_recording(1)
                
                finally:
                    camera.stop_recording()
                    print("Recording stopped.")
                    
                    # Save data log to CSV
                    df = pd.DataFrame(data_log, columns=data_columns)
                    df.to_csv(data_log_path, index=False)
                    print("Data logged to CSV.")
                    
                    # Convert the video to MP4 using ffmpeg
                    convert_command = f"ffmpeg -r 30 -i {h264_path} -vcodec copy {mp4_path}"
                    subprocess.run(convert_command, shell=True)
                    print("Video converted to MP4.")
            else:
                print("System not armed.")
                time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Program terminated.")
    finally:
        GPIO.cleanup()