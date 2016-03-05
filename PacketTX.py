#!/usr/bin/env python
#
# Serial Packet Transmitter Class
#
# Frames packets (preamble, unique word, checksum)
# and transmits them out of a serial port.
#
# Mark Jessop <vk5qi@rfhead.net>
#


import serial,Queue,sys,crcmod,struct
from time import sleep
from threading import Thread
import numpy as np

class BinaryDebug(object):
	def __init__(self):
		self.f = open("debug.bin",'wb')

	def write(self,data):
		# TODO: Add in RS232 framing
		raw_data = np.array([],dtype=np.uint8)
		for d in data:
			d_array = np.unpackbits(np.fromstring(d,dtype=np.uint8))
			raw_data = np.concatenate((raw_data,[0],d_array[::-1],[1]))

		self.f.write(raw_data.astype(np.uint8).tostring())

	def close(self):
		self.f.close()


class PacketTX(object):
	txqueue = Queue.Queue(4096) # Up to 1MB of 256 byte packets
	transmit_active = False
	debug = False

	unique_word = "\xab\xcd"
	preamble = "\x55"*16
	idle_sequence = "\x55"*256


	def __init__(self,serial_port="/dev/ttyAMA0", serial_baud=115200, payload_length=256, debug = False):

		if debug == True:
			self.s = BinaryDebug()
			self.debug = True
		else:
			self.s = serial.Serial(serial_port,serial_baud)
		self.payload_length = payload_length

		self.crc16 = crcmod.predefined.mkCrcFun('crc-ccitt-false')

	def start_tx(self):
		self.transmit_active = True
		txthread = Thread(target=self.tx_thread)
		txthread.start()

	def frame_packet(self,packet):
		# Ensure payload size is equal to the desired payload length
		if len(packet) > self.payload_length:
			packet = packet[:self.payload_length]

		if len(packet) < self.payload_length:
			packet = packet + "\x00"*(self.payload_length - len(packet))

		crc = struct.pack("<H",self.crc16(packet))
		return self.preamble + self.unique_word + packet + crc 


	def tx_thread(self):
		while self.transmit_active:
			if self.txqueue.qsize()>0:
				packet = self.txqueue.get_nowait()
				self.s.write(packet)
			else:
				if not self.debug:
					self.s.write(self.idle_sequence)
				else:
					sleep(0.05)
		
		print("Closing Thread")
		self.s.close()

	def close(self):
		self.transmit_active = False

	def wait(self):
		while not self.txqueue.empty():
			sleep(0.01)

	def tx_packet(self,packet,blocking = False):
		self.txqueue.put(self.frame_packet(packet))

		if blocking:
			while not self.txqueue.empty():
				sleep(0.01)


