import struct
import screen
import logging
import pygame
import time
import ctypes

class memory:
	def __init__(self, size, cartridge):
		self.memory = []
		for i in range(0,0x10000):
			self.memory.append(0)

		for i in range(len(cartridge)):
			self.memory[i] = ord(cartridge[i])

	def __setitem__(self, offset, value):
		if offset < 0x8000:
			logging.info("illlegal write access to address %X", offset)
			return

		self.memory[offset] = value
		if offset >= 0xFF00 and offset <= 0xFF70 and offset != 0xFF44 and offset != 0xFF00:
			logging.info("################# CALL Special Register %X = %X", offset, value)

		if offset == 0xFF46:
			source_start = value << 8
			dest_start = 0xFE00
			for i in range(0, 0xA0):
				self.memory[dest_start + i] = self.memory[source_start + i]

	def __getitem__(self, offset):
		return self.memory[offset]

class processor:
	def __init__(self, cartridge, gb_screen, gb_memory):
		self.cartridge = cartridge
		self.PC = 0x100
		#self.PC = 0x58
		self.SP = 0xDFFF
		self.flag_z = 0
		self.flag_n = 0
		self.flag_h = 0
		self.flag_c = 0
		self.reg_A = 0xAA
		self.reg_B = 0xBB
		self.reg_C = 0xCC
		self.reg_D = 0xDD
		self.reg_E = 0xEE
		self.reg_HL = 0xFF99
		self.interrupt_enabled = False

		self.gbscreen = gb_screen
		self.memory = gb_memory

		self.memory[0xFF44] = 0x94
		self.memory[0xC0C6] = 0x1

	def dumper(self):
		logging.info("Registers : A[%02X] B[%02X] C[%02X] HL[%02X] PC[%04X] SP[%04X]", self.reg_A, self.reg_B, self.reg_C, self.reg_HL, self.PC, self.SP)
		bob = "STACK : "
		for i in range (0xDFF0, 0xDFFF):
			bob = "%s - %X" % (bob, self.memory[i])
		logging.info(bob)

	def power_on(self):

		i = 0
		j = 0x0E
		#self.load_state()

		keyLoop = True
		while keyLoop:	
			for event in pygame.event.get():
				if event.type == pygame.KEYDOWN:
					if event.key == pygame.K_ESCAPE:
						logging.info ( "Escape pressed, exiting" )
						keyLoop = False
						pygame.quit()			


			time.sleep(0.001)
			for x in range(0, 1000):
				if self.interrupt_enabled:
					j = (j + 1) % 200
					if j == 0:
						self.interrupt()


				#if self.gbscreen.is_stopped():
				#	self.save_state()

				self.interpret_opcode()
				self.memory[0xFF44] = i
				i = (i + 1) % 160
				self.memory[0xFF00] = self.memory[0xFF00] | 0x06

	def interrupt(self):
		if self.interrupt_enabled:
			self.interrupt_enabled = False
			logging.info("==> INTERRUPT : PC=%X", self.PC)

			self.SP = self.SP - 1
			self.memory[self.SP] = (self.PC) & 0xFF
			self.SP = self.SP - 1
			self.memory[self.SP] = ((self.PC) >> 8) & 0xFF

			new_adress = 0x40
			self.PC = new_adress

	# NOPA
	def opcode_0x00(self, opcode):
		logging.info("%X - [%02X] NOP" , self.PC, opcode)
		self.PC = self.PC + 1

	# RST 28
	def opcode_0xEF(self, opcode):
		self.SP = self.SP - 1
		self.memory[self.SP] = (self.PC+1) & 0xFF
		self.SP = self.SP - 1
		self.memory[self.SP] = ((self.PC+1) >> 8) & 0xFF

		new_adress = 0x28
		logging.info("%X - [%02X] RST 28" , self.PC, opcode)
		self.PC = new_adress

#	# RST 38
#	def opcode_0xFF(self, opcode):
#		self.SP = self.SP - 1
#		self.memory[self.SP] = (self.PC+1) & 0xFF
#		self.SP = self.SP - 1
#		self.memory[self.SP] = ((self.PC+1) >> 8) & 0xFF
#
#		new_adress = 0x38
#		logging.info("%X - [%02X] RST 38" , self.PC, opcode)
#		self.PC = new_adress

	# JP
	def opcode_0xC3(self, opcode):
		new_adress = self.memory[self.PC+1] + ( self.memory[self.PC+2] << 8 )
		logging.info("%X - [%02X] JP %X" , self.PC, opcode, new_adress)
		self.PC = new_adress

	# JP NZ
	def opcode_0xC2(self, opcode):
		new_adress = self.memory[self.PC+1] + ( self.memory[self.PC+2] << 8 )
		logging.info("%X - [%02X] JP NZ %X" , self.PC, opcode, new_adress)

		self.PC = self.PC + 3

		if self.flag_z == 0:
			self.PC = new_adress

	# JP (HL)
	def opcode_0xE9(self, opcode):
		new_adress = self.reg_HL
		logging.info("%X - [%02X] JP (HL)	!! WARNING Hazardous Implementation	[HL=%X]" , self.PC, opcode, self.reg_HL)
		self.PC = new_adress

	# JR NZ xx
	def opcode_0x20(self, opcode):

		offset, = struct.unpack("b", chr(self.memory[self.PC+1]))

		logging.info("%X - [%02X] JR NZ %X+ %X		[=%X, flag_z=%X]", self.PC, opcode, self.PC + 2, offset, self.PC + 2 + offset, self.flag_z)

		if self.flag_z == 0:
			self.PC = self.PC + 2 + offset
                else:
                        self.PC = self.PC + 2


	# JR Z xx
	def opcode_0x28(self, opcode):

		offset, = struct.unpack("b", chr(self.memory[self.PC+1]))
		logging.info("%X - [%02X] JR Z %X+ %X		[=%X]" , self.PC, opcode, self.PC+2, offset, self.PC + 2 + offset)

		if self.flag_z == 1:
			self.PC = self.PC + 2 + offset
                else:
                        self.PC = self.PC + 2

	# JR xx
	def opcode_0x18(self, opcode):

		offset, = struct.unpack("b", chr(self.memory[self.PC+1]))
		logging.info("%X - [%02X] JR %X+ %X		[=%X]" , self.PC, opcode, self.PC+2, offset, self.PC + 2 + offset)
		self.PC = self.PC + 2 + offset

	# JP Z xx
	def opcode_0xCA(self, opcode):

		new_adress = self.memory[self.PC+1] + ( self.memory[self.PC+2] << 8 )
		logging.info("%X - [%02X] JP Z %X" , self.PC, opcode, new_adress)


		if self.flag_z == 1:
			self.PC = new_adress
                else:
                        self.PC = self.PC + 3

	# CALL aa bb
	def opcode_0xCD(self, opcode):
		self.SP = self.SP - 1
		self.memory[self.SP] = (self.PC+3) & 0xFF
		self.SP = self.SP - 1
		self.memory[self.SP] = ((self.PC+3) >> 8) & 0xFF

		new_adress = self.memory[self.PC+1] + ( self.memory[self.PC+2] << 8 )
		logging.info("%X - [%02X] --> CALL %X" , self.PC, opcode, new_adress)
		self.PC = new_adress

	# XOR A => A (A = 0)
	def opcode_0xAF(self, opcode):
		logging.info("%X - [%02X] XOR A, A" , self.PC, opcode)
		self.reg_A = 0
		self.flag_z = 1
		self.flag_n = 0
		self.flag_h = 0
		self.flag_c = 0
		self.PC = self.PC + 1

#	# XOR B => A
#	def opcode_0xA8(self, opcode):
#		logging.info("%X - [%02X] XOR A, B" , self.PC, opcode)
#
#		self.reg_A = self.reg_A ^ self.reg_B
#
#		self.flag_z = 0
#		if self.reg_A == 0:
#			self.flag_z = 1
#
#		self.flag_n = 0
#		self.flag_h = 0
#		self.flag_c = 0
#		self.PC = self.PC + 1

	# XOR C => A
	def opcode_0xA9(self, opcode):

		self.reg_A = (self.reg_A ^ self.reg_C) & 0xFF
		logging.info("%X - [%02X] XOR A, C		[A->0x%X]" , self.PC, opcode, self.reg_A)

		if self.reg_A == 0:
			self.flag_z = 1
                else:
                        self.flag_z = 0

		self.flag_n = 0
		self.flag_h = 0
		self.flag_c = 0
		self.PC = self.PC + 1

#	# XOR xx => A
#	def opcode_0xEE(self, opcode):
#		value = self.memory[self.PC+1]
#		logging.info("%X - [%02X] XOR A, 0x%X" , self.PC, opcode, value)
#
#		self.reg_A = self.reg_A ^ value
#
#		self.flag_z = 0
#		if self.reg_A == 0:
#			self.flag_z = 1
#
#		self.flag_n = 0
#		self.flag_h = 0
#		self.flag_c = 0
#		self.PC = self.PC + 2
#
#	# OR A, A => A
#	def opcode_0xB7(self, opcode):
#		logging.info("%X - [%02X] OR A, A" , self.PC, opcode)
#		if self.reg_A == 0:
#			self.flag_z = 1
#		else:
#			self.flag_z = 0
#
#		self.PC = self.PC + 1

	# OR A, xx => A
	def opcode_0xF6(self, opcode):
		value = self.memory[self.PC+1]
		logging.info("%X - [%02X] OR A, 0x%X" , self.PC, opcode, value)

		self.reg_A = self.reg_A | value
		self.flag_n = 0
		self.flag_h = 0
		self.flag_c = 0

		if self.reg_A == 0:
			self.flag_z = 1
		else:
			self.flag_z = 0

		self.PC = self.PC + 2

	# CPL A, A
	def opcode_0x2F(self, opcode):
		self.flag_n = 1
		self.flag_h = 1
		self.reg_A = (~self.reg_A) & 0xFF
		logging.info("%X - [%02X] CPL A, A		[A->0x%X]" , self.PC, opcode, self.reg_A)
		self.PC = self.PC + 1

	# OR C, A => A
	def opcode_0xB1(self, opcode):
		logging.info("%X - [%02X] OR A, C		[A=%X, C=%X]" , self.PC, opcode, self.reg_A, self.reg_C)
		self.reg_A = self.reg_A | self.reg_C

		self.flag_n = 0
		self.flag_h = 0
		self.flag_c = 0

		if self.reg_A == 0:
			self.flag_z = 1
                else:
                        self.flag_z = 0

		self.PC = self.PC + 1

	# OR B, A => A
	def opcode_0xB0(self, opcode):
		logging.info("%X - [%02X] OR A, B		[A=%X, B=%X]" , self.PC, opcode, self.reg_A, self.reg_B)
		self.reg_A = self.reg_A | self.reg_B

		self.flag_n = 0
		self.flag_h = 0
		self.flag_c = 0

		if self.reg_A == 0:
			self.flag_z = 1
                else:
                        self.flag_z = 0

		self.PC = self.PC + 1

	# AND A, xx => A
	def opcode_0xE6(self, opcode):
		logging.info("%X - [%02X] AND A, 0x%X" , self.PC, opcode, self.memory[self.PC+1])

		self.reg_A = self.reg_A & self.memory[self.PC+1]

		self.flag_n = 0
		self.flag_c = 0
		self.flag_h = 1

		if self.reg_A == 0:
			self.flag_z = 1
                else:
                        self.flag_z = 0

		self.PC = self.PC + 2

#	# AND A, B => A
#	def opcode_0xA0(self, opcode):
#		logging.info("%X - [%02X] AND A, B" , self.PC, opcode)
#
#		self.reg_A = self.reg_A & self.reg_B
#
#		if self.reg_A == 0:
#			self.flag_z = 1
#		else:
#			self.flag_z = 0
#
#		self.PC = self.PC + 2
#

	# AND A, C => A
	def opcode_0xA1(self, opcode):
		logging.info("%X - [%02X] AND A, C" , self.PC, opcode)

		self.reg_A = self.reg_A & self.reg_C

		self.flag_n = 0
		self.flag_c = 0
		self.flag_h = 1

		if self.reg_A == 0:
			self.flag_z = 1
                else:
                        self.flag_z = 0

		self.PC = self.PC + 1


	# CB prefix management
	def opcode_0xCB(self, opcode):
		real_code = self.memory[self.PC+1]

		# SWAP A
		if real_code == 0x37:
			self.reg_A = ((self.reg_A & 0xF0)>>4) + ((self.reg_A & 0xF)<<4)

			logging.info("%X - [%02X-%02X] SWAP A		[A->0x%X]" , self.PC, opcode, real_code, self.reg_A)

			self.flag_n = 0
			self.flag_h = 0
			self.flag_c = 0

			if self.reg_A == 0:
				self.flag_z = 1
                        else:
                                self.flag_z = 0

			self.PC = self.PC + 2

		# SLA A
		elif real_code == 0x27:

			temp = self.reg_A << 1
			logging.info("%X - [%02X-%02X] SLA A		[A=%X, SLA=%X, flag_c=%X]" , self.PC, opcode, real_code, self.reg_A, temp & 0xFF, temp & 0x100)

			self.reg_A = temp & 0xFF


			if self.reg_A == 0:
				self.flag_z = 1
                        else:
                                self.flag_z = 0

			if temp & 0x100 != 0:
				self.flag_c = 1
                        else:
                                self.flag_c = 0

			self.PC = self.PC + 2

		# RES 0, (HL)
		elif real_code == 0x86:
			self.memory[self.reg_HL] = self.memory[self.reg_HL] & 0xFE
			logging.info("%X - [%02X-%02X] RES 0, (HL)		[HL=0x%X, (HL)=0x%X]" , self.PC, opcode, real_code, self.reg_HL, self.memory[self.reg_HL])

			self.PC = self.PC + 2

		# RES 0, A
		elif real_code == 0x87:
			self.reg_A = self.reg_A & 0xFE
			logging.info("%X - [%02X-%02X] RES 0, A		[A->0x%X]" , self.PC, opcode, real_code, self.reg_A)

			self.PC = self.PC + 2

#		# SET 7, (HL)
#		elif real_code == 0xFE:
#			value = self.memory[self.reg_HL]
#			self.memory[self.reg_HL] = value |  0x80
#			logging.info("%X - [%02X-%02X] SET 7, (HL)		[%X -> %X]" , self.PC, opcode, real_code, value, self.memory[self.reg_HL])
#
#			self.PC = self.PC + 2
#
#		# BIT 0, B
#		elif real_code == 0x40:
#			value = self.reg_B & 0x1
#
#			self.flag_z = 0
#			if value == 0:
#				self.flag_z = 1
#
#			logging.info("%X - [%02X-%02X] BIT 0, B		[B=%X, value=%X, flag_z=%X]" , self.PC, opcode, real_code, self.reg_B, value, self.flag_z)
#
#			self.PC = self.PC + 2
#
#		# BIT 1, B
#		elif real_code == 0x48:
#			value = self.reg_B & 0x2
#
#			self.flag_z = 0
#			if value == 0:
#				self.flag_z = 1
#
#			logging.info("%X - [%02X-%02X] BIT 1, B		[B=%X, value=%X, flag_z=%X]" , self.PC, opcode, real_code, self.reg_B, value, self.flag_z)
#
#			self.PC = self.PC + 2

		# BIT 2, B
		elif real_code == 0x50:
			value = self.reg_B & 0x4

			if value == 0:
				self.flag_z = 1
                        else:
                                self.flag_z = 0

			logging.info("%X - [%02X-%02X] BIT 2, B		[B=%X, value=%X, flag_z=%X]" , self.PC, opcode, real_code, self.reg_B, value, self.flag_z)

			self.PC = self.PC + 2

		# BIT 4, B
		elif real_code == 0x60:
			value = self.reg_B & 0x10

			if value == 0:
				self.flag_z = 1
                        else:
                                self.flag_z = 0

			logging.info("%X - [%02X-%02X] BIT 4, B		[B=%X]" , self.PC, opcode, real_code, self.reg_B)

			self.PC = self.PC + 2

#		# BIT 4, C
#		elif real_code == 0x61:
#			value = self.reg_C & 0x10
#
#			self.flag_z = 0
#			if value == 0:
#				self.flag_z = 1
#
#			logging.info("%X - [%02X-%02X] BIT 4, C		[B=%X]" , self.PC, opcode, real_code, self.reg_C)
#
#			self.PC = self.PC + 2

		# BIT 5, B
		elif real_code == 0x68:
			value = self.reg_B & 0x20

			if value == 0:
				self.flag_z = 1
                        else:
                                self.flag_z = 0

			logging.info("%X - [%02X-%02X] BIT 5, B		[B=%X]" , self.PC, opcode, real_code, self.reg_B)

			self.PC = self.PC + 2

#		# BIT 5, C
#		elif real_code == 0x69:
#			value = self.reg_C & 0x20
#
#			self.flag_z = 0
#			if value == 0:
#				self.flag_z = 1
#
#			logging.info("%X - [%02X-%02X] BIT 5, C		[B=%X]" , self.PC, opcode, real_code, self.reg_C)
#
#			self.PC = self.PC + 2

		# BIT 5, A
		elif real_code == 0x6F:
			value = self.reg_A & 0x20

			if value == 0:
				self.flag_z = 1
                        else:
                                self.flag_z = 0

			logging.info("%X - [%02X-%02X] BIT 5, A		[A=%X]" , self.PC, opcode, real_code, self.reg_A)

			self.PC = self.PC + 2

		# BIT 6, A
		elif real_code == 0x77:
			value = self.reg_A & 0x40

			if value == 0:
				self.flag_z = 1
                        else:
                                self.flag_z = 0

			logging.info("%X - [%02X-%02X] BIT 6, A		[B=%X]" , self.PC, opcode, real_code, self.reg_A)

			self.PC = self.PC + 2

		# BIT 7, A
		elif real_code == 0x7E:

			logging.info("%X - [%02X-%02X] BIT ?, ?		WARNING : Unknown opcode ???" , self.PC, opcode, real_code)

			self.PC = self.PC + 2

		# BIT 7, A
		elif real_code == 0x7F:
			value = self.reg_A & 0x80

			if value == 0:
				self.flag_z = 1
                        else:
                                self.flag_z = 0

			logging.info("%X - [%02X-%02X] BIT 7, A		[B=%X]" , self.PC, opcode, real_code, self.reg_A)

			self.PC = self.PC + 2


		# BIT 3, B
		elif real_code == 0x58:
			value = self.reg_B & 0x8

			if value == 0:
				self.flag_z = 1
                        else:
                                self.flag_z = 0

			logging.info("%X - [%02X-%02X] BIT 3, B		[B=%X]" , self.PC, opcode, real_code, self.reg_B)

			self.PC = self.PC + 2

#		# BIT 3, A
#		elif real_code == 0x5F:
#			value = self.reg_A & 0x8
#
#			self.flag_z = 0
#			if value == 0:
#				self.flag_z = 1
#
#			logging.info("%X - [%02X-%02X] BIT 3, A		[B=%X]" , self.PC, opcode, real_code, self.reg_A)
#
#			self.PC = self.PC + 2
#
		else :
			logging.info("%X - [%02X] Unsupported CB %X" , self.PC, opcode, real_code)
			sd

	# LD aabb => HL
	def opcode_0x21(self, opcode):
		self.reg_HL = self.memory[self.PC+1] + ( self.memory[self.PC+2] << 8 )
		logging.info("%X - [%02X] LD HL, %X" , self.PC, opcode, self.reg_HL)
		self.PC = self.PC + 3

#	# LD A => A
#	def opcode_0x7F(self, opcode):
#		logging.info("%X - [%02X] LD A, A" , self.PC, opcode)
#		self.PC = self.PC + 1

	# LD B => B
	def opcode_0x40(self, opcode):
		logging.info("%X - [%02X] LD B, B" , self.PC, opcode)
		self.PC = self.PC + 1

	# LD A => B
	def opcode_0x47(self, opcode):
		logging.info("%X - [%02X] LD B, A" , self.PC, opcode)
		self.reg_B = self.reg_A
		self.PC = self.PC + 1

	# LD A => C
	def opcode_0x4F(self, opcode):
		logging.info("%X - [%02X] LD C, A" , self.PC, opcode)
		self.reg_C = self.reg_A
		self.PC = self.PC + 1

	# LD A => D
	def opcode_0x57(self, opcode):
		logging.info("%X - [%02X] LD D, A" , self.PC, opcode)
		self.reg_D = self.reg_A
		self.PC = self.PC + 1

	# LD A => E
	def opcode_0x5F(self, opcode):
		logging.info("%X - [%02X] LD E, A" , self.PC, opcode)
		self.reg_E = self.reg_A
		self.PC = self.PC + 1

	# LD C => A
	def opcode_0x79(self, opcode):
		logging.info("%X - [%02X] LD A, C" , self.PC, opcode)
		self.reg_A = self.reg_C
		self.PC = self.PC + 1

	# LD C => L
	def opcode_0x69(self, opcode):
		logging.info("%X - [%02X] LD L, C" , self.PC, opcode)
		self.reg_HL = (self.reg_HL & 0xFF00) + (self.reg_C & 0xFF)
		self.PC = self.PC + 1

	# LD E => L
	def opcode_0x6B(self, opcode):
		logging.info("%X - [%02X] LD L, E" , self.PC, opcode)
		self.reg_HL = (self.reg_HL & 0xFF00) + (self.reg_E & 0xFF)
		self.PC = self.PC + 1

#	# LD xx => L
#	def opcode_0x2E(self, opcode):
#		value = self.memory[self.PC+1]
#		logging.info("%X - [%02X] LD L, 0x%X" , self.PC, opcode, value)
#		self.reg_HL = (self.reg_HL & 0xFF00) + (value & 0xFF)
#		self.PC = self.PC + 2

	# LD L => E
	def opcode_0x5D(self, opcode):
		logging.info("%X - [%02X] LD E, L		[L=%X]" , self.PC, opcode, (self.reg_HL & 0xFF))
		self.reg_E = (self.reg_HL & 0xFF)
		self.PC = self.PC + 1

	# LD L => A
	def opcode_0x7D(self, opcode):
		logging.info("%X - [%02X] LD A, L		[L=%X]" , self.PC, opcode, (self.reg_HL & 0xFF))
		self.reg_A = (self.reg_HL & 0xFF)
		self.PC = self.PC + 1

	# LD B => H
	def opcode_0x60(self, opcode):
		self.reg_HL = (self.reg_HL & 0xFF) + ((self.reg_B << 8) & 0xFF00)
		logging.info("%X - [%02X] LD H, B		[HL=0x%X, B=0x%X]" , self.PC, opcode, self.reg_HL, self.reg_B)
		self.PC = self.PC + 1

	# LD H => D
	def opcode_0x54(self, opcode):
		self.reg_D = (self.reg_HL >> 8) & 0xFF
		logging.info("%X - [%02X] LD D, H		[H=%X]" , self.PC, opcode, self.reg_D)
		self.PC = self.PC + 1

	# LD H => A
	def opcode_0x7C(self, opcode):
		self.reg_A = (self.reg_HL >> 8) & 0xFF
		logging.info("%X - [%02X] LD A, H		[H=%X]" , self.PC, opcode, self.reg_A)
		self.PC = self.PC + 1

	# LD A => L
	def opcode_0x6F(self, opcode):
		self.reg_HL = (self.reg_HL & 0xFF00) + (self.reg_A & 0xFF)
		#self.reg_HL = (self.reg_HL & 0xFF) + ((self.reg_A << 8) & 0xFF00)
		logging.info("%X - [%02X] LD L, A		[HL=%X]" , self.PC, opcode, self.reg_HL)
		self.PC = self.PC + 1

	# LD D => H
	def opcode_0x62(self, opcode):
		self.reg_HL = (self.reg_HL & 0xFF) + ((self.reg_D << 8) & 0xFF00)
		logging.info("%X - [%02X] LD H, D		[HL=%X]" , self.PC, opcode, self.reg_HL)
		self.PC = self.PC + 1

	# LD A => H
	def opcode_0x67(self, opcode):
#		#self.reg_HL = (self.reg_HL & 0xFF00) + (self.reg_A & 0xFF)
		self.reg_HL = (self.reg_HL & 0xFF) + ((self.reg_A << 8) & 0xFF00)
		logging.info("%X - [%02X] LD H, A		[HL=%X]" , self.PC, opcode, self.reg_HL)
		self.PC = self.PC + 1

	# LD xx => B
	def opcode_0x6(self, opcode):
		self.reg_B = self.memory[self.PC+1]
		logging.info("%X - [%02X] LD B, 0x%X" , self.PC, opcode, self.reg_B)
		self.PC = self.PC + 2

	# LD xx => D
	def opcode_0x16(self, opcode):
		self.reg_D = self.memory[self.PC+1]
		logging.info("%X - [%02X] LD D, %X" , self.PC, opcode, self.reg_D)
		self.PC = self.PC + 2

	# LD xx => E
	def opcode_0x1E(self, opcode):
		self.reg_E = self.memory[self.PC+1]
		logging.info("%X - [%02X] LD E, %X" , self.PC, opcode, self.reg_E)
		self.PC = self.PC + 2

	# LD xx => C
	def opcode_0x0E(self, opcode):
		self.reg_C = self.memory[self.PC+1]
		logging.info("%X - [%02X] LD C, %X" , self.PC, opcode, self.reg_C)
		self.PC = self.PC + 2

	# LD xx => A
	def opcode_0x3E(self, opcode):
		self.reg_A = self.memory[self.PC+1]
		logging.info("%X - [%02X] LD A, %X" , self.PC, opcode, self.reg_A)
		self.PC = self.PC + 2

	# LD xx => H
	def opcode_0x26(self, opcode):
		value = self.memory[self.PC+1]
		logging.info("%X - [%02X] LD H, 0x%X" , self.PC, opcode, value)
		self.reg_HL = (self.reg_HL & 0xFF) + ((value << 8) & 0xFF)
		self.PC = self.PC + 2

	# LDD A => mem[HL] and HL--
	def opcode_0x32(self, opcode):
		self.memory[self.reg_HL] = self.reg_A
		logging.info("%X - [%02X] LD (HL-), A		[HL=%X, A=%X]" , self.PC, opcode, self.reg_HL, self.reg_A)
		self.reg_HL = self.reg_HL - 1
		self.PC = self.PC + 1

	# LDD mem[HL] => A and HL--
	def opcode_0x3A(self, opcode):
		self.reg_A = self.memory[self.reg_HL]
		logging.info("%X - [%02X] LD A, (HL-)		[HL=%X, (HL)=%X]" , self.PC, opcode, self.reg_HL, self.reg_A)
		self.reg_HL = self.reg_HL - 1
		self.PC = self.PC + 1

	# LDI A => mem[HL] and HL++
	def opcode_0x22(self, opcode):
		self.memory[self.reg_HL] = self.reg_A
		logging.info("%X - [%02X] LD (HL+), A		[HL=%X, A=%X]" , self.PC, opcode, self.reg_HL, self.reg_A)
		self.reg_HL = self.reg_HL + 1
		self.PC = self.PC + 1

	# LDD mem[HL] => A and HL++
	def opcode_0x2A(self, opcode):
		self.reg_A = self.memory[self.reg_HL]
		self.reg_HL = self.reg_HL + 1
		logging.info("%X - [%02X] LD A, (HL+)" , self.PC, opcode)
		self.PC = self.PC + 1

	# LDD A => mem[HL]
	def opcode_0x77(self, opcode):
		self.memory[self.reg_HL] = self.reg_A 
		logging.info("%X - [%02X] LD (HL), A		[HL=0x%X, A=0x%X]" , self.PC, opcode, self.reg_HL, self.reg_A)
		self.PC = self.PC + 1

	# LDH A => mem[FF00 + xx]
	def opcode_0xE0(self, opcode):
		self.memory[0xFF00 + self.memory[self.PC+1]] = self.reg_A
		logging.info("%X - [%02X] LDH (0xFF00 + %X), A		[@=%X, A=%X]" , self.PC, opcode, self.memory[self.PC+1], 0xFF00 + self.memory[self.PC+1], self.reg_A)
		self.PC = self.PC + 2

#	# LDD [HL] => A
#	def opcode_0x32(self, opcode):
#		self.reg_A = self.memory[self.reg_HL]
#		logging.info("%X - [%02X] LD A,(HL-), A" , self.PC, opcode)
#		self.PC = self.PC + 1

	# LDH mem[FF00+xx] => A
	def opcode_0xF0(self, opcode):
		offset = self.memory[self.PC+1]
		self.reg_A = self.memory[0xFF00 + offset]
		logging.info("%X - [%02X] LD A, (0xFF00+%X)		[(%X)=%X]" , self.PC, opcode, offset, 0xFF00+offset, self.reg_A)
		self.PC = self.PC + 2

	# LD xx => mem[HL]
	def opcode_0x36(self, opcode):
		self.memory[self.reg_HL] = self.memory[self.PC+1]
		logging.info("%X - [%02X] LD (HL), %X		[HL=%X]" , self.PC, opcode, self.memory[self.PC+1], self.reg_HL)
		self.PC = self.PC + 2

	# LD  A => mem[aabb]
	def opcode_0xEA(self, opcode):
		adress = self.memory[self.PC+1] + ( self.memory[self.PC+2] << 8 )
		self.memory[adress] = self.reg_A
		logging.info("%X - [%02X] LD (%X), A" , self.PC, opcode, adress)
		self.PC = self.PC + 3

	# LD  aabb => SP
	def opcode_0x31(self, opcode):
		adress = self.memory[self.PC+1] + ( self.memory[self.PC+2] << 8 )
		self.SP = adress
		logging.info("%X - [%02X] LD SP, %X" , self.PC, opcode, adress)
		self.PC = self.PC + 3

	# LD  mem[aabb] => A
	def opcode_0xFA(self, opcode):
		adress = self.memory[self.PC+1] + ( self.memory[self.PC+2] << 8 )
		self.reg_A = self.memory[adress]
		logging.info("%X - [%02X] LD A, (%X)" , self.PC, opcode, adress)
		self.PC = self.PC + 3

	# LD  mem[HL] => A
	def opcode_0x7E(self, opcode):
		self.reg_A = self.memory[self.reg_HL]
		logging.info("%X - [%02X] LD A, (HL)		[HL=%X, (HL)=%X]" , self.PC, opcode, self.reg_HL, self.reg_A)
		self.PC = self.PC + 1

	# LD  mem[DE] => A
	def opcode_0x1A(self, opcode):
		adress = (self.reg_D << 8) + self.reg_E
		self.reg_A = self.memory[adress] & 0xFF
		logging.info("%X - [%02X] LD A, (DE)		[DE=%X, (DE)=%X]" , self.PC, opcode, adress, self.reg_A)
		self.PC = self.PC + 1

	# LD  A => mem[DE]
	def opcode_0x12(self, opcode):
		adress = (self.reg_D << 8) + self.reg_E
		self.memory[adress] = self.reg_A
		logging.info("%X - [%02X] LD (DE), A		[DE=%X, A=%X]" , self.PC, opcode, adress, self.reg_A)
		self.PC = self.PC + 1

	# LD  mem[HL] => B
	def opcode_0x46(self, opcode):
		self.reg_B = self.memory[self.reg_HL]
		logging.info("%X - [%02X] LD B,(HL)		[HL=0x%X, (HL)=0x%X]" , self.PC, opcode, self.reg_HL, self.reg_B)
		self.PC = self.PC + 1

	# LD  mem[HL] => C
	def opcode_0x4E(self, opcode):
		self.reg_C = self.memory[self.reg_HL]
		logging.info("%X - [%02X] LD C,(HL)		[HL=0x%X, (HL)=0x%X]" , self.PC, opcode, self.reg_HL, self.reg_C)
		self.PC = self.PC + 1

	# LD  mem[HL] => E
	def opcode_0x5E(self, opcode):
		self.reg_E = self.memory[self.reg_HL]
		logging.info("%X - [%02X] LD E, (HL)		[HL=%X (HL)=%X]" , self.PC, opcode, self.reg_HL, self.reg_E)
		self.PC = self.PC + 1

	# LD  C => mem[HL]
	def opcode_0x71(self, opcode):
		self.memory[self.reg_HL] = self.reg_C
		logging.info("%X - [%02X] LD (HL), C		[HL=%X C=%X]" , self.PC, opcode, self.reg_HL, self.reg_C)
		self.PC = self.PC + 1

	# LD  D => mem[HL]
	def opcode_0x72(self, opcode):
		self.memory[self.reg_HL] = self.reg_D
		logging.info("%X - [%02X] LD (HL), D		[HL=%X D=%X]" , self.PC, opcode, self.reg_HL, self.reg_D)
		self.PC = self.PC + 1

	# LD  E => mem[HL]
	def opcode_0x73(self, opcode):
		self.memory[self.reg_HL] = self.reg_E
		logging.info("%X - [%02X] LD (HL), E		[HL=%X E=%X]" , self.PC, opcode, self.reg_HL, self.reg_E)
		self.PC = self.PC + 1

	# LD  mem[HL] => D
	def opcode_0x56(self, opcode):
		self.reg_D = self.memory[self.reg_HL]
		logging.info("%X - [%02X] LD D, (HL)		[HL=%X, (HL)=%X]" , self.PC, opcode, self.reg_HL,self.reg_D)
		self.PC = self.PC + 1

	# LD  aa bb => BC
	def opcode_0x01(self, opcode):
		self.reg_B = self.memory[self.PC+2]
		self.reg_C = self.memory[self.PC+1]
		logging.info("%X - [%02X] LD BC, %X" , self.PC, opcode, (self.reg_B << 8) + self.reg_C)
		self.PC = self.PC + 3

	# LD  aa bb => DE
	def opcode_0x11(self, opcode):
		self.reg_D = self.memory[self.PC+2]
		self.reg_E = self.memory[self.PC+1]
		logging.info("%X - [%02X] LD DE, %X" , self.PC, opcode, (self.memory[self.PC+2]<<8) + self.memory[self.PC+1])
		self.PC = self.PC + 3

	# LD  (BC) => A
	def opcode_0x0A(self, opcode):
		BC = (self.reg_B << 8) + self.reg_C
		self.reg_A = self.memory[BC]
		logging.info("%X - [%02X] LD A, (BC)		[BC=%X (BC)=%X]" , self.PC, opcode, BC, self.reg_A)
		self.PC = self.PC + 1

	# LD  A => 0xFF00 + C
	def opcode_0xE2(self, opcode):
		self.memory[0xFF00 + self.reg_C] = self.reg_A
		logging.info("%X - [%02X] LD (0xFF00+C), A		[C=%X, A=%X]" , self.PC, opcode, self.reg_C, self.reg_A)
		self.PC = self.PC + 1

	# LD  B => A
	def opcode_0x78(self, opcode):
		self.reg_A = self.reg_B
		logging.info("%X - [%02X] LD A, B		[A=0x%X]" , self.PC, opcode, self.reg_A)
		self.PC = self.PC + 1

	# LD  D => A
	def opcode_0x7A(self, opcode):
		self.reg_A = self.reg_D
		logging.info("%X - [%02X] LD A, D" , self.PC, opcode)
		self.PC = self.PC + 1

	# LD  E => A
	def opcode_0x7B(self, opcode):
		self.reg_A = self.reg_E
		logging.info("%X - [%02X] LD A, E" , self.PC, opcode)
		self.PC = self.PC + 1

	# DEC A
	def opcode_0x3D(self, opcode):
		self.flag_z = 0

		if self.reg_A == 0:
			self.reg_A = 255
		else:
			self.reg_A = self.reg_A - 1
			if self.reg_A == 0:
				self.flag_z = 1

		self.flag_n = 1
		self.flag_h = 1

		logging.info("%X - [%02X] DEC A		[A=0x%X]" , self.PC, opcode, self.reg_A)
		self.PC = self.PC + 1

	# DEC B
	def opcode_0x05(self, opcode):
		self.flag_z = 0

		if self.reg_B == 0:
			self.reg_B = 255
		else:
			self.reg_B = self.reg_B - 1
			if self.reg_B == 0:
				self.flag_z = 1

		self.flag_n = 1
		self.flag_h = 1

		logging.info("%X - [%02X] DEC B		[B=0x%X]" , self.PC, opcode, self.reg_B)
		self.PC = self.PC + 1

	# DEC C
	def opcode_0x0D(self, opcode):
		self.flag_z = 0
		if self.reg_C == 0:
			self.reg_C = 255
		else:
			self.reg_C = self.reg_C - 1
			if self.reg_C == 0:
				self.flag_z = 1

		self.flag_n = 1
		self.flag_h = 1

		logging.info("%X - [%02X] DEC C" , self.PC, opcode)
		self.PC = self.PC + 1

	# INC HL
	def opcode_0x34(self, opcode):
		value = self.memory[self.reg_HL]

		self.flag_z = 0
		self.flag_c = 0
		self.flag_n = 0

		if value == 0xFF:
			self.memory[self.reg_HL] = 0x0
			self.flag_z = 1
			self.flag_c = 1
		else:
			self.memory[self.reg_HL] = value + 1


		logging.info("%X - [%02X] INC (HL)		[(HL)=%X->%X]" , self.PC, opcode, value, self.memory[self.reg_HL])
		self.PC = self.PC + 1

	# DEC (HL)
	def opcode_0x35(self, opcode):
		value = self.memory[self.reg_HL]

		self.flag_z = 0
		if value == 0x0:
			self.memory[self.reg_HL] = 0xFF
		else:
			self.memory[self.reg_HL] = value - 1
			if value == 1:
				self.flag_z = 1

		self.flag_n = 1

		logging.info("%X - [%02X] DEC (HL)		[(HL)=%X]" , self.PC, opcode, value-1)
		self.PC = self.PC + 1

	# DEC BC
	def opcode_0xB(self, opcode):
		BC = (self.reg_B << 8) + (self.reg_C)
		if BC == 0:
			BC = 0XFFFF
		else:
			BC = BC - 1

		self.reg_B = (BC >> 8) & 0xFF
		self.reg_C = (BC) & 0xFF

		logging.info("%X - [%02X] DEC BC		[BC=0x%X, B=0x%X, C=0x%X]" , self.PC, opcode, BC, self.reg_B, self.reg_C)
		self.PC = self.PC + 1

	# INC BC
	def opcode_0x3(self, opcode):
		BC = (self.reg_B << 8) + (self.reg_C)
		if BC == 0xFFFF:
			BC = 0
		else:
			BC = BC + 1

		self.reg_B = (BC >> 8) & 0xFF
		self.reg_C = (BC) & 0xFF

		logging.info("%X - [%02X] INC BC		[BC=%X]" , self.PC, opcode, BC)
		self.PC = self.PC + 1

	# INC C
	def opcode_0x0C(self, opcode):
		if self.reg_C == 255:
			self.reg_C = 0
			self.flag_z = 1
		else:
			self.reg_C = self.reg_C + 1
			self.flag_z = 0

		self.flag_n = 0

		logging.info("%X - [%02X] INC C		[C=0x%X]" , self.PC, opcode, self.reg_C)
		self.PC = self.PC + 1

	# INC E
	def opcode_0x1C(self, opcode):
		if self.reg_E == 255:
			self.reg_E = 0
			self.flag_z = 1
		else:
			self.reg_E = self.reg_E + 1
			self.flag_z = 0

		self.flag_n = 0

		logging.info("%X - [%02X] INC E		[E=0x%X]" , self.PC, opcode, self.reg_E)
		self.PC = self.PC + 1

	# INC A
	def opcode_0x3C(self, opcode):
		if self.reg_A == 255:
			self.reg_A = 0
			self.flag_z = 1
		else:
			self.reg_A = self.reg_A + 1
			self.flag_z = 0

		self.flag_n = 0

		logging.info("%X - [%02X] INC A		[A=0x%X]" , self.PC, opcode, self.reg_A)
		self.PC = self.PC + 1


	# INC HL
	def opcode_0x23(self, opcode):
		if self.reg_HL == 0xFFFF:
			self.reg_HL = 0
			self.flag_c = 1
			self.flag_z = 1
		else:
			self.reg_HL = self.reg_HL + 1
			self.flag_z = 0

		self.flag_n = 0

		logging.info("%X - [%02X] INC HL		[HL=%X]" , self.PC, opcode, self.reg_HL)
		self.PC = self.PC + 1

	# INC L
	def opcode_0x2C(self, opcode):
		L = self.reg_HL & 0xFF

		if L == 0xFF:
			L = 0
			self.flag_z = 1
			self.flag_h = 1
		else:
			L = L + 1
			self.flag_z = 0

		self.flag_n = 0
		self.reg_HL = (self.reg_HL & 0xFF00) + L

		logging.info("%X - [%02X] INC L		[HL=%X]" , self.PC, opcode, self.reg_HL)
		self.PC = self.PC + 1

	# DEC L
	def opcode_0x2D(self, opcode):
		L = self.reg_HL & 0xFF

		if L == 0x0:
			L = 0xFF
			self.flag_z = 1
			self.flag_h = 1
		else:
			L = L - 1
			self.flag_z = 0

		self.flag_n = 0
		self.reg_HL = (self.reg_HL & 0xFF00) + L

		logging.info("%X - [%02X] DEC L		[HL=%X]" , self.PC, opcode, self.reg_HL)
		self.PC = self.PC + 1

	# INC DE
	def opcode_0x13(self, opcode):
		DE = (self.reg_D << 8) + (self.reg_E)

		if DE == 0xFFFF:
			DE = 0
			self.flag_z = 1
			self.flag_c = 1
		else:
			DE = DE + 1
			self.flag_c = 0
			self.flag_z = 0

		self.flag_n = 0

		self.reg_D = (DE >> 8) & 0xFF
		self.reg_E = (DE) & 0xFF

		logging.info("%X - [%02X] INC DE		[D=0x%X, E=0x%X]" , self.PC, opcode, self.reg_D, self.reg_E)
		self.PC = self.PC + 1

	# ADD A, B
	def opcode_0x80(self, opcode):
		self.reg_A = self.reg_A + self.reg_B

		self.flag_z = 0
		self.flag_n = 0
		self.flag_c = 0

		if self.reg_A > 255:
			self.reg_A = self.reg_A - 256
			self.flag_c = 1

		if self.reg_A == 0:
			self.flag_z = 1

		logging.info("%X - [%02X] ADD A, B" , self.PC, opcode)
		self.PC = self.PC + 1

#	# ADD A, C
#	def opcode_0x81(self, opcode):
#		self.reg_A = self.reg_A + self.reg_C
#
#		self.flag_z = 0
#		self.flag_n = 0
#		self.flag_c = 0
#
#		if self.reg_A > 255:
#			self.reg_A = self.reg_A - 256
#			self.flag_c = 1
#
#		if self.reg_A == 0:
#			self.flag_z = 1
#
#		logging.info("%X - [%02X] ADD A, C" , self.PC, opcode)
#		self.PC = self.PC + 1

	# ADD A, xx
	def opcode_0xC6(self, opcode):
		value = self.memory[self.PC+1]
		self.reg_A = self.reg_A + value

		self.flag_z = 0
		self.flag_n = 0
		self.flag_c = 0

		if self.reg_A > 255:
			self.reg_A = self.reg_A - 256
			self.flag_c = 1

		if self.reg_A == 0:
			self.flag_z = 1

		logging.info("%X - [%02X] ADD A, 0x%X" , self.PC, opcode, value)
		self.PC = self.PC + 2

	# ADD A, A
	def opcode_0x87(self, opcode):
		logging.info("%X - [%02X] ADD A, A		[A=%X, A,A=%X]" , self.PC, opcode, self.reg_A, (self.reg_A + self.reg_A) % 255)

		self.reg_A = self.reg_A + self.reg_A

		self.flag_z = 0
		self.flag_n = 0
		self.flag_c = 0

		if self.reg_A > 255:
			self.flag_c = 1
			self.reg_A = self.reg_A - 256

		if self.reg_A == 0:
			self.flag_z = 1

		self.PC = self.PC + 1

	# ADD A, L
	def opcode_0x85(self, opcode):
		L = self.reg_HL & 0xFF
		self.reg_A = (self.reg_A + L) % 255

		self.flag_z = 0
		self.flag_n = 0
		if self.reg_A == 0:
			self.flag_z = 1

		logging.info("%X - [%02X] ADD A, L		[L=%X, A=%X]" , self.PC, opcode, L, self.reg_A)
		self.PC = self.PC + 1

	# ADD HL, DE
	def opcode_0x19(self, opcode):
		DE = (self.reg_D << 8) + self.reg_E
		logging.info("%X - [%02X] ADD HL, DE		[HL=%X DE=%X => HL=%X]" , self.PC, opcode, self.reg_HL, DE, self.reg_HL + DE)

		self.reg_HL = self.reg_HL + DE

		self.flag_n = 0
		self.flag_c = 0

		if self.reg_HL > 0xFFFF:
			self.reg_HL = self.reg_HL - 0x10000
			self.flag_c = 1

		self.PC = self.PC + 1

	# ADD HL, BC
	def opcode_0x09(self, opcode):
		BC = (self.reg_B << 8) + self.reg_C
		logging.info("%X - [%02X] ADD HL, BC		[HL=%X BC=%X => HL=%X]" , self.PC, opcode, self.reg_HL, BC, self.reg_HL + BC)
		self.reg_HL = self.reg_HL + BC

		self.flag_n = 0

		self.PC = self.PC + 1

	# ADC A, C
	def opcode_0x89(self, opcode):
		self.reg_A = self.reg_A + self.reg_C + self.flag_c

		self.flag_z = 0
		self.flag_n = 0
		self.flag_c = 0

		if self.reg_A > 255:
			self.reg_A = self.reg_A - 256
			self.flag_c = 1

		if self.reg_A == 0:
			self.flag_z = 1

		logging.info("%X - [%02X] ADC A, C" , self.PC, opcode)
		self.PC = self.PC + 1

	# SUB A, B
	def opcode_0x90(self, opcode):
		self.reg_A = self.reg_A - self.reg_B

		self.flag_z = 0
		self.flag_n = 0
		if self.reg_A == 0:
			self.flag_z = 1

		if self.reg_A < 0:
			self.reg_A = 256 + self.reg_A
			self.flag_c = 1

		logging.info("%X - [%02X] SUB A, B		[A=%X]" , self.PC, opcode, self.reg_A)
		self.PC = self.PC + 1

	# SBC A, C
	def opcode_0x99(self, opcode):
		self.reg_A = self.reg_A - self.reg_C - self.flag_c

		self.flag_z = 0
		self.flag_n = 0
		if self.reg_A == 0:
			self.flag_z = 1

		if self.reg_A < 0:
			self.reg_A = 256 + self.reg_A
			self.flag_c = 1

		logging.info("%X - [%02X] SBC A, C		[A=%X]" , self.PC, opcode, self.reg_A)
		self.PC = self.PC + 1

	# SBC A, xx
	def opcode_0xDE(self, opcode):
		value = self.memory[self.PC+1]
		self.reg_A = self.reg_A - value - self.flag_c

		self.flag_z = 0
		self.flag_n = 0
		if self.reg_A == 0:
			self.flag_z = 1

		if self.reg_A < 0:
			self.reg_A = 256 + self.reg_A
			self.flag_c = 1

		logging.info("%X - [%02X] SBC A, 0x%X		[A=%X]" , self.PC, opcode, value, self.reg_A)
		self.PC = self.PC + 2

	# RLCA
	def opcode_0x07(self, opcode):
		value = self.reg_A << 1
		self.flag_c = 0

		if value & 0x100 != 0:
			self.flag_c = 1

		value = (value & 0xFF) | 1
		logging.info("%X - [%02X] RLCA		[oldA=%X, A=%X]" , self.PC, opcode, self.reg_A, value)
		self.reg_A = value


		self.flag_n = 0

		self.PC = self.PC + 1

	# DI
	def opcode_0xF3(self, opcode):
		logging.info("%X - [%02X] DI - Disable Interrupt management" , self.PC, opcode)
		self.interrupt_enabled = False
		self.PC = self.PC + 1

	# EI
	def opcode_0xFB(self, opcode):
		logging.info("%X - [%02X] EI - Enable Interrupt management" , self.PC, opcode)
		self.interrupt_enabled = True
		self.PC = self.PC + 1

	# CP x
	def opcode_0xFE(self, opcode):
		dummy = self.reg_A - self.memory[self.PC+1]
		logging.info("%X - [%02X] CP A, 0x%X" , self.PC, opcode, self.memory[self.PC+1])
		self.flag_z = 0
		self.flag_n = 1
		self.flag_c = 0

		if dummy == 0:
			self.flag_z = 1
		elif dummy < 0:
			self.flag_c = 1

		self.PC = self.PC + 2

#	# CP E
#	def opcode_0xBB(self, opcode):
#		dummy = self.reg_A - self.reg_E
#		logging.info("%X - [%02X] CP A, E" , self.PC, opcode)
#		self.flag_z = 0
#		self.flag_n = 0
#		self.flag_c = 0
#
#		if dummy == 0:
#			self.flag_z = 1
#		elif dummy < 0:
#			self.flag_c = 1
#
#		self.PC = self.PC + 1
#
#	# CP B
#	def opcode_0xB8(self, opcode):
#		dummy = self.reg_A - self.reg_B
#		logging.info("%X - [%02X] CP A, B" , self.PC, opcode)
#		self.flag_z = 0
#		self.flag_n = 0
#		self.flag_c = 0
#
#		if dummy == 0:
#			self.flag_z = 1
#		elif dummy < 0:
#			self.flag_c = 1
#
#		self.PC = self.PC + 1

	# PUSH AF
	def opcode_0xF5(self, opcode):
		F = (self.flag_c << 4) | (self.flag_h << 5) | (self.flag_n << 6) | (self.flag_z << 7)
		self.SP = self.SP - 1
		self.memory[self.SP] = F
		self.SP = self.SP - 1
		self.memory[self.SP] = self.reg_A

		logging.info("%X - [%02X]	PUSH AF	[A=%X, z=%X, n=%X, h=%X, c=%X, F=%X]" , self.PC, opcode, self.reg_A, self.flag_z, self.flag_n, self.flag_h, self.flag_c, F)

		self.PC = self.PC + 1

	# PUSH BC
	def opcode_0xC5(self, opcode):
		self.SP = self.SP - 1
		self.memory[self.SP] = self.reg_B
		self.SP = self.SP - 1
		self.memory[self.SP] = self.reg_C

		logging.info("%X - [%02X] PUSH BC" , self.PC, opcode)

		self.PC = self.PC + 1

	# PUSH DE
	def opcode_0xD5(self, opcode):
		self.SP = self.SP - 1
		self.memory[self.SP] = self.reg_E
		self.SP = self.SP - 1
		self.memory[self.SP] = self.reg_D

		logging.info("%X - [%02X] PUSH DE		[D=%X, E=%X]" , self.PC, opcode, self.reg_D, self.reg_E)

		self.PC = self.PC + 1

	# PUSH HL
	def opcode_0xE5(self, opcode):
		self.SP = self.SP - 1
		self.memory[self.SP] = self.reg_HL & 0xFF
		self.SP = self.SP - 1
		self.memory[self.SP] = (self.reg_HL & 0xFF00)>>8

		logging.info("%X - [%02X] PUSH HL" , self.PC, opcode)

		self.PC = self.PC + 1

	# POP DE
	def opcode_0xD1(self, opcode):
		self.reg_D = self.memory[self.SP]
		self.SP = self.SP + 1
		self.reg_E = self.memory[self.SP]
		self.SP = self.SP + 1

		logging.info("%X - [%02X] POP DE		[D=%X, E=%X]" , self.PC, opcode, self.reg_D, self.reg_E)

		self.PC = self.PC + 1

	# POP BC
	def opcode_0xC1(self, opcode):
		self.reg_C = self.memory[self.SP]
		self.SP = self.SP + 1
		self.reg_B = self.memory[self.SP]
		self.SP = self.SP + 1

		logging.info("%X - [%02X] POP BC		[B=%X, C=%X]" , self.PC, opcode, self.reg_B, self.reg_C)

		self.PC = self.PC + 1

	# POP AF
	def opcode_0xF1(self, opcode):
		self.reg_A = self.memory[self.SP]
		self.SP = self.SP + 1
		F = self.memory[self.SP]
		self.SP = self.SP + 1

		self.flag_z = 0
		self.flag_n = 0
		self.flag_h = 0
		self.flag_c = 0

		if F & 0x80 != 0:
			self.flag_z = 1

		if F & 0x40 != 0:
			self.flag_n = 1

		if F & 0x20 != 0:
			self.flag_h = 1

		if F & 0x10 != 0:
			self.flag_c = 1

		#logging.info("%X - [%02X] POP AF		[A=%X, A=%X]" , self.PC, opcode, self.reg_A, self.reg_A)
		logging.info("%X - [%02X]	POP AF	[A=%X, z=%X, n=%X, h=%X, c=%X, F=%X]" , self.PC, opcode, self.reg_A, self.flag_z, self.flag_n, self.flag_h, self.flag_c, F)

		self.PC = self.PC + 1

	# POP HL
	def opcode_0xE1(self, opcode):
		HL_High = self.memory[self.SP]
		self.SP = self.SP + 1
		HL_Low = self.memory[self.SP]
		self.SP = self.SP + 1

		self.reg_HL = (HL_High << 8) + HL_Low

		logging.info("%X - [%02X] POP HL		[HL=%X]" , self.PC, opcode, self.reg_HL)

		self.PC = self.PC + 1

	# AND A, A
	def opcode_0xA7(self, opcode):
		self.flag_z = 0
		self.flag_n = 0
		self.flag_h = 1
		self.flag_c = 0

		if self.reg_A == 0:
			self.flag_z = 1

		logging.info("%X - [%02X] AND A, A" , self.PC, opcode)

		self.PC = self.PC + 1

	# RET
	def opcode_0xC9(self, opcode):

		logging.info("%X - [%02X] <-- RET" , self.PC, opcode)
		PC_High = self.memory[self.SP] & 0xFF
		self.SP = self.SP + 1
		PC_Low = self.memory[self.SP] & 0xFF
		self.SP = self.SP + 1

		self.PC = (PC_High << 8) + PC_Low

	# RETI
	def opcode_0xD9(self, opcode):
		self.interrupt_enabled = True

		PC_High = self.memory[self.SP] & 0xFF
		self.SP = self.SP + 1
		PC_Low = self.memory[self.SP] & 0xFF
		self.SP = self.SP + 1

		old_PC = self.PC
		self.PC = (PC_High << 8) + PC_Low

		logging.info("%X - [%02X] <---------- RETI		[Back to %X]" , old_PC, opcode, self.PC)

	# RET NZ
	def opcode_0xC0(self, opcode):

		logging.info("%X - [%02X] RET NZ" , self.PC, opcode)

		if self.flag_z == 0:
			PC_High = self.memory[self.SP] & 0xFF
			self.SP = self.SP + 1
			PC_Low = self.memory[self.SP] & 0xFF
			self.SP = self.SP + 1

			self.PC = (PC_High << 8) + PC_Low
		else:
			self.PC = self.PC + 1

	# RET Z
	def opcode_0xC8(self, opcode):

		logging.info("%X - [%02X] RET Z" , self.PC, opcode)

		if self.flag_z == 1:
			PC_High = self.memory[self.SP] & 0xFF
			self.SP = self.SP + 1
			PC_Low = self.memory[self.SP] & 0xFF
			self.SP = self.SP + 1

			self.PC = (PC_High << 8) + PC_Low
		else:
			self.PC = self.PC + 1

        opcodes_function = {
		0x00 : opcode_0x00,
		0xEF : opcode_0xEF,
#		0xFF : opcode_0xFF,
		0xC3 : opcode_0xC3,
		0xC2 : opcode_0xC2,
		0xE9 : opcode_0xE9,
		0x20 : opcode_0x20,
		0x28 : opcode_0x28,
		0x18 : opcode_0x18,
		0xCA : opcode_0xCA,
		0xCD : opcode_0xCD,
		0xAF : opcode_0xAF,
#		0xA8 : opcode_0xA8,
		0xA9 : opcode_0xA9,
#		0xEE : opcode_0xEE,
#		0xB7 : opcode_0xB7,
		0xF6 : opcode_0xF6,
		0x2F : opcode_0x2F,
		0xB1 : opcode_0xB1,
		0xB0 : opcode_0xB0,
		0xE6 : opcode_0xE6,
#		0xA0 : opcode_0xA0,
		0xA1 : opcode_0xA1,
		0xCB : opcode_0xCB,
		0x21 : opcode_0x21,
#		0x7F : opcode_0x7F,
		0x40 : opcode_0x40,
		0x47 : opcode_0x47,
		0x4F : opcode_0x4F,
		0x57 : opcode_0x57,
		0x5F : opcode_0x5F,
		0x79 : opcode_0x79,
		0x69 : opcode_0x69,
		0x6B : opcode_0x6B,
#		0x2E : opcode_0x2E,
		0x5D : opcode_0x5D,
		0x7D : opcode_0x7D,
		0x60 : opcode_0x60,
		0x54 : opcode_0x54,
		0x7C : opcode_0x7C,
		0x6F : opcode_0x6F,
		0x62 : opcode_0x62,
		0x67 : opcode_0x67,
		0x6 : opcode_0x6,
		0x16 : opcode_0x16,
		0x1E : opcode_0x1E,
		0x0E : opcode_0x0E,
		0x3E : opcode_0x3E,
		0x26 : opcode_0x26,
		0x32 : opcode_0x32,
		0x3A : opcode_0x3A,
		0x22 : opcode_0x22,
		0x2A : opcode_0x2A,
		0x77 : opcode_0x77,
		0xE0 : opcode_0xE0,
#		0x32 : opcode_0x32,
		0xF0 : opcode_0xF0,
		0x36 : opcode_0x36,
		0xEA : opcode_0xEA,
		0x31 : opcode_0x31,
		0xFA : opcode_0xFA,
		0x7E : opcode_0x7E,
		0x1A : opcode_0x1A,
		0x12 : opcode_0x12,
		0x46 : opcode_0x46,
		0x4E : opcode_0x4E,
		0x5E : opcode_0x5E,
		0x71 : opcode_0x71,
		0x72 : opcode_0x72,
		0x73 : opcode_0x73,
		0x56 : opcode_0x56,
		0x01 : opcode_0x01,
		0x11 : opcode_0x11,
		0x0A : opcode_0x0A,
		0xE2 : opcode_0xE2,
		0x78 : opcode_0x78,
		0x7A : opcode_0x7A,
		0x7B : opcode_0x7B,
		0x3D : opcode_0x3D,
		0x05 : opcode_0x05,
		0x0D : opcode_0x0D,
		0x34 : opcode_0x34,
		0x35 : opcode_0x35,
		0xB : opcode_0xB,
		0x3 : opcode_0x3,
		0x0C : opcode_0x0C,
		0x1C : opcode_0x1C,
		0x3C : opcode_0x3C,
		0x23 : opcode_0x23,
		0x2C : opcode_0x2C,
		0x2D : opcode_0x2D,
		0x13 : opcode_0x13,
		0x80 : opcode_0x80,
#		0x81 : opcode_0x81,
		0xC6 : opcode_0xC6,
		0x87 : opcode_0x87,
		0x85 : opcode_0x85,
		0x19 : opcode_0x19,
		0x09 : opcode_0x09,
		0x89 : opcode_0x89,
		0x90 : opcode_0x90,
		0x99 : opcode_0x99,
		0xDE : opcode_0xDE,
		0x07 : opcode_0x07,
		0xF3 : opcode_0xF3,
		0xFB : opcode_0xFB,
		0xFE : opcode_0xFE,
#		0xBB : opcode_0xBB,
#		0xB8 : opcode_0xB8,
		0xF5 : opcode_0xF5,
		0xC5 : opcode_0xC5,
		0xD5 : opcode_0xD5,
		0xE5 : opcode_0xE5,
		0xD1 : opcode_0xD1,
		0xC1 : opcode_0xC1,
		0xF1 : opcode_0xF1,
		0xE1 : opcode_0xE1,
		0xA7 : opcode_0xA7,
		0xC9 : opcode_0xC9,
		0xD9 : opcode_0xD9,
		0xC0 : opcode_0xC0,
		0xC8 : opcode_0xC8 }

	def interpret_opcode(self):
		opcode = self.memory[self.PC]
                self.opcodes_function[opcode](self, opcode)
	# else:
	# 	logging.info("%X - [%02X] Unsupported opcode" , self.PC, opcode)
	# 	#self.save_state(filename="state_crash.sav")
	# 	sd


	def save_state(self, filename="state_1.sav"):
		save_file = open(filename, "w")
		save_file.write("%X\n" % (self.reg_A))
		save_file.write("%X\n" % (self.reg_B))
		save_file.write("%X\n" % (self.reg_C))
		save_file.write("%X\n" % (self.reg_D))
		save_file.write("%X\n" % (self.reg_E))
		save_file.write("%X\n" % (self.reg_HL))
		save_file.write("%X\n" % (self.SP))
		save_file.write("%X\n" % (self.PC))
		save_file.write("%X\n" % (self.flag_z))
		save_file.write("%X\n" % (self.flag_n))
		save_file.write("%X\n" % (self.flag_h))
		save_file.write("%X\n" % (self.flag_c))

		for i in range(0xFFFF):
			save_file.write("%X\n" % (self.memory[i]))

		sdf

	def load_state(self):
		save_file = open("state_crash.sav", "r")
		self.reg_A =  int(save_file.readline(), 16)
		self.reg_B =  int(save_file.readline(), 16)
		self.reg_C =  int(save_file.readline(), 16)
		self.reg_D =  int(save_file.readline(), 16)
		self.reg_E =  int(save_file.readline(), 16)
		self.reg_HL =  int(save_file.readline(), 16)
		self.SP =  int(save_file.readline(), 16)
		self.PC =  int(save_file.readline(), 16)
		self.flag_z =  int(save_file.readline(), 16)
		self.flag_n =  int(save_file.readline(), 16)
		self.flag_h =  int(save_file.readline(), 16)
		self.flag_c =  int(save_file.readline(), 16)

		for i in range(0xFFFF):
			self.memory[i] = int(save_file.readline(), 16)

def main():
	file = open('Tetris.gb', 'r')
	tetris = file.read()

	gameboy = processor(tetris)
	gameboy.power_on()

if __name__ == '__main__':
    main()



