'''
Last Modified: 2021-05-06

@author: Jesse M. Barr

Contains:
    -Serial

Changes:
-2021-05-06:
    -Updated connected attribute.
-2021-04-21:
    -Syntax updates
-2021-04-05:
    -Remove all Qt imports.
    -Qt signals replaced with Signals using pydispatch
-2020-06-17:
    -Allow sending a message without broadcasting it, useful for non-printable
        characters.
-2020-09-23:
    -Replace QSerialPort with PySerial.

ToDo:

'''
from time import sleep
from threading import Thread, Lock
from serial.serialutil import SerialBase
from ..Utilities import Signal, PLATFORM

if PLATFORM == 'android':
    from usb4a import usb
    from usbserial4a import serial4a
else:
    from serial.tools import list_ports
    from serial import Serial as pySerial


class Serial(object):
    sigConnected = Signal("serial_connected")
    sigDisconnected = Signal("serial_disconnected")
    sigSendMessage = Signal("serial_sending_message")
    sigMessageReceived = Signal("serial_received_message")

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.serial_port = None
        self.read_thread = None
        self.__connected = False
        self.port_thread_lock = Lock()

    def connect(self, port, baud):
        self.close()
        if PLATFORM == 'android':
            device = usb.get_usb_device(device_name)
            if not device:
                raise SerialException(
                    "Device {} not present!".format(device_name)
                )
            if not usb.has_usb_permission(device):
                usb.request_usb_permission(device)
                return
            self.serial_port = serial4a.get_serial_port(port, baud)
        else:
            self.serial_port = pySerial(port, baud)

        self.__connected = True

        def read_msg_thread():
            err = None
            try:
                while self.read_msg():
                    sleep(0.01)
            except Exception as e:
                err = e
            finally:
                self.close()
                self.sigDisconnected(err)

        self.read_thread = Thread(target=read_msg_thread)
        self.read_thread.daemon = True
        self.read_thread.start()

        self.sigConnected()

    def send(self, msg, announce=True):
        if self.serial_port and self.serial_port.is_open:
            if announce:
                self.sigSendMessage(msg)
            self.serial_port.write(bytes(msg, 'utf8'))
            return msg
        raise Exception("Serial connection not established")

    def read_msg(self):
        with self.port_thread_lock:
            if self.serial_port is None or not self.serial_port.is_open:
                return False
            received_msg = self.serial_port.read(
                self.serial_port.in_waiting
            )
            if received_msg:
                self.sigMessageReceived(bytes(received_msg).decode('utf8'))
            return True

    def close(self):
        if self.serial_port:
            with self.port_thread_lock:
                self.serial_port.close()
                self.serial_port = None
            try:
                # Try to cleanup thread. Not overly important being a daemon
                #   and it should be ended anyway.
                self.read_thread.join()
                self.read_thread = None
            except:
                pass
        self.__connected = False

    def disconnect(self):
        return self.close()

    def isOpen(self):
        if self.serial_port:
            return self.serial_port.is_open
        return False

    def onMessageReceived(self, func, weak=None):
        self.sigMessageReceived.connect(func, weak)

    def onMessageSending(self, func, weak=None):
        self.sigSendMessage.connect(func, weak)

    def onConnected(self, func, weak=None):
        self.sigConnected.connect(func, weak)

    def onDisconnected(self, func, weak=None):
        self.sigDisconnected.connect(func, weak)

    @property
    def port(self):
        return self.serial_port.port

    @property
    def baud(self):
        return self.serial_port.baudrate

    @property
    def Connected(self):
        return self.__connected

    @staticmethod
    def PORTS():
        if PLATFORM == 'android':
            return [
                device.getDeviceName() for device in usb.get_usb_device_list()
            ]
        else:
            return [port.device for port in list_ports.comports()]

    @staticmethod
    def BAUDRATES():
        return SerialBase.BAUDRATES
