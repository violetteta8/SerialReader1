import logging
import serial
#from config import ComA, BaudA, ComB, BaudB
import time
from datetime import datetime
import os
import shutil
import ftplib

path = 'C:\\Users\\tviolett\\Documents\\Javad\\'                            # Define path for data storage
newpath = 1
msg = ''

try:                                                                        # Try to make the path by making new directory
    os.mkdir(path)
    newpath = -1
except OSError as error:                                                    # If path already exists
    print(error)                                                           # Print the error message
    msg = error
    newpath = 0

logfile = os.path.join(path, datetime.now().strftime('sample_%Y%m%d-%H%M')+".log")
FORMAT = "%(asctime)s — %(name)s — %(levelname)s — %(funcName)s:%(lineno)d — %(message)s"
logging.basicConfig(filename=logfile, format=FORMAT)
logger = logging.getLogger()
logger.setLevel(level=logging.INFO)

if newpath == -1:
    logging.info('New directory created.')
else:
    logging.info(msg)


timestr = time.strftime("%Y%m%d-%H%M")   
SampleDur = 0                                                               # Declare variable to hold user-defined sample duration
SampleGNSS = 1
TestStr = ""
splitdata = 0
SID = 0
SIDholder = 0
StationNum = 0
ShutdownStr = ''
shutdown = 'False'

try:
    ser = serial.Serial('COM29',115200)
    logging.info('Serial port A Opened')
except:
    logging.exception('Serial Port A Not Available')

try:
    ser2 = serial.Serial('COM30',115200)
    logging.info('Serial port B Opened')
except:
    logging.exception('Serial Port B Not Available')

ser2.flushInput()                                                           # Flush Serial Port 2 Inbound buffer to ensure no junk bytes are present
ser2.flushOutput()                                                          # Flush Serial Port 2 Outbound buffer to ensure no junk bytes are present
time.sleep(3)                                                               # Short delay to ensure buffer was flushed.


while SampleDur == 0 and (SampleGNSS != 0 or SampleGNSS != -1):                                                       # If SampleDur is 0, no data has come in from datalogger so:
    bytesToRead = ser2.inWaiting()                                          # Check if there are any bytes in the port, assign to "bytesToRead"
    print(bytesToRead)                                                      # Print value in command window
    if bytesToRead == 0:                                                    # If there are no bytes to read:
        ser2.write(b'Ready\r')                                            # Send "Ready<CR><LF>" out to datalogger to notify the datalogger the PC is ready to run the script
        ser2.flushInput()                                                   # Flush both inboud and outbound buffers as the "Ready" message is now in the dataloggers serial buffer
        ser2.flushOutput()
        time.sleep(60)                                                      # Delay 1 minute before returning to top of While loop as that's the scan rate of datalogger
    #elif bytesToRead > 3:                                                   # If we have more than 3 bytes, there are likely junk bytes. Expecting 12hr sampling (720 minutes)
       # ser2.flushInput()                                                   # Flush ports
        #ser2.flushOutput()
        #time.sleep(60)                                                      # Delay 1 minute before returning to top of While loop
    else:
        TestStr = ser2.read_until('\n', bytesToRead)                                  # If not 0 or > 3 bytes from "inWaiting()", read number of bytes into SampleDur
        print(TestStr) #SampleDur = int(SampleDur)
        TestStr = TestStr.decode("utf-8")
        if TestStr.startswith('SID'):
            splitdata = TestStr.split(",") # Change variable from tyep Bytes to type Integer
            print(splitdata)                                                    # Print value to know how many bytes are expected
            SIDholder = splitdata[0].split(":")
            print(SIDholder)
            SID = SIDholder[1]
            print(SID)
            StationNum = splitdata[1]
            print(StationNum)
            SampleDur = splitdata[2]
            print(SampleDur)
            SampleGNSS = -1
        elif TestStr == 'No Sample':
            SampleGNSS = 0
            break
        else:
            SampleDur == 0
        ser2.flushInput()                                                   # Flush both ports
        ser2.flushOutput()
        time.sleep(5)                                                       # Delay a few seconds before moving into sampling loop

if SampleGNSS == -1:

    #SID = SID.decode("utf-8")
    #StationNum = StationNum.decode("utf-8")
    SampleDur = int(SampleDur)

                                   # Create timestamp string for file naming
    fn = StationNum + "_" + SID + "_Javad_"                                                           # Define site ID for file naming -- Do this via communication to datalogger?
    ext = ".jps"                                                                # Set raw file name extension from Javad to .jps
    jpsname = fn + timestr + ext                                                # Concatenate to make file name
    t_end = time.time()+ SampleDur * 60                                         # Set end time "t_end" to current time + user define minutes * 60s
    file = open(os.path.join(path,jpsname),'wb')                                # Open a new file in directory for binary writing
    cmdA = """cmd /c "jps2rin.exe """                                           # Set command line commands to convert the .jps to RINEX file type for OPUS
    cmdB = " /opus /o="
    cmdC = " /of="
    cmdstr = cmdA + path + jpsname + cmdB + path + cmdC + fn + timestr + '"'    # Create full command line string
    ftp_host = 'ftpext.usgs.gov'                                                # Define the FTP host name
    ftp_user = 'anonymous'                                                      # Define FTP user name
    ftp_pass = ''                                                               # Define FTP password

    ser.write(bytes(b'em,,/msg/def\r\n'))                                       # Send "enable default message output" command to Javad through Serial Port 1
    time.sleep(1)                                                               # Wait 1 second before moving into sample loop

    file.truncate(0)                                                            # Ensure file is completely clean before sample loop

    print('Run Started')                                                        
    while time.time() < t_end:                                                  # While current time is less than end time
        bytesToRead = ser.inWaiting()                                           # Check buffer for bytes available
        print(bytesToRead)                                                      # Print how many bytes are in buffer
        rl = ser.read(bytesToRead)                                              # Read number of bytes in buffer to "rl"
        print(rl)                                                               # Print the bytes
        file.write(rl)                                                          # Write the bytes to the open .jps file
        time.sleep(2)                                                           # Delay 2 sec to ensure next message(s) are there for continuing While loop

    file.close()                                                                # After While loop finishes
    ser.write(bytes(b'dm,,/msg/def\r\n'))                                       # Send "disable message output" command to Javad
    time.sleep(1)                                                               # Delay 1 second
    ser.close()                                                                 # Close both serial port A
    os.system(cmdstr)                                                           # Output the command-line command to convert .jps to RINEX

    numfiles = len([name for name in os.listdir(path) if name.endswith('o')]) # Check directory for files ending in "o" (indicating OPUS file), store the count in "numfiles"
    print(numfiles)
    numFiles = str(numfiles)
    logging.info(numFiles + ' files to push to FTP.')                                         # Print the number of OPUS files
    if numfiles >= 1:                                                            # If more than X -- perhaps always send after every sample period instead of waiting for multiple files? Unless user starts manually?
        ftp = ftplib.FTP(ftp_host, ftp_user, ftp_pass)                          # Open connection to USGS public FTP server
        ftp.cwd('from_pub/wr/GCES_GNSS')                                        # Move into the server to appropriate directory for file storage
        for files in os.listdir(path):       # For the files in the local directory
            if files.endswith('o'):                                             # If the file extension ends in "o" (OPUS file)
                ftpResponse = ftp.storbinary('STOR ' + files, open(path + files,"rb")) # Send the "STOR" command to send files to the FTP
                print(ftpResponse)
                if ftpResponse == ("226 Transfer complete."):
                    os.remove(path + files)
                    print('File Deleted')
                    logging.info(path + files + ' deleted.')
                else:
                    print('Unsuccessful transfer, file not deleted.')
                    logging.info(path + files + ' not deleted.')
                    continue
            else:                                                               # If no more "o" files
                continue                                                        # Move on

    print('Run Complete')                                                      # Run Complete
    logging.info("Run Complete.")
    ser2.flushInput()
    ser2.flushOutput()
else:
    ser2.flushInput()
    ser2.flushOutput()
    
while shutdown == 'False':                                                       # If SampleDur is 0, no data has come in from datalogger so:
    bytesToRead = ser2.inWaiting()                                          # Check if there are any bytes in the port, assign to "bytesToRead"
    print(bytesToRead)                                                      # Print value in command window
    if bytesToRead == 0:                                                    # If there are no bytes to read:
        ser2.write(b'Run Complete\r')                                            # Send "Ready<CR><LF>" out to datalogger to notify the datalogger the PC is ready to run the script
        ser2.flushInput()                                                   # Flush both inboud and outbound buffers as the "Ready" message is now in the dataloggers serial buffer
        ser2.flushOutput()
        time.sleep(60)                                                      # Delay 1 minute before returning to top of While loop as that's the scan rate of datalogger
    #elif bytesToRead > 3:                                                   # If we have more than 3 bytes, there are likely junk bytes. Expecting 12hr sampling (720 minutes)
       # ser2.flushInput()                                                   # Flush ports
        #ser2.flushOutput()
        #time.sleep(60)                                                      # Delay 1 minute before returning to top of While loop
    else:
        ShutdownStr = ser2.read_until('\n', bytesToRead)                     # If not 0 or > 3 bytes from "inWaiting()", read number of bytes into SampleDur
        ShutdownStr = ShutdownStr.decode("utf-8")
        print(ShutdownStr) #SampleDur = int(SampleDur)
        ser2.flushInput()
        ser2.flushOutput()
        if ShutdownStr == ('Shutdown'):
            shutdown = 'True'
            ser2.close()
            logging.info('System shutting down')
            print('System shutting down')
            time.sleep(5)
            #os.system("shutdown /s /t 1")
