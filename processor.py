import struct
import screen
import logging
import pygame
import time

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

	def interpret_opcode(self):
		opcode = self.memory[self.PC]

		# NOP
		if opcode == 0x0:
			logging.info("%X - [%02X] NOP", self.PC, opcode)
			self.PC = self.PC + 1

		# RST 28
		elif opcode == 0xEF:
			self.SP = self.SP - 1
			self.memory[self.SP] = (self.PC+1) & 0xFF
			self.SP = self.SP - 1
			self.memory[self.SP] = ((self.PC+1) >> 8) & 0xFF

			new_adress = 0x28
			logging.info("%X - [%02X] RST 28", self.PC, opcode)
			self.PC = new_adress

#		# RST 38
#		elif opcode == 0xFF:
#			self.SP = self.SP - 1
#			self.memory[self.SP] = (self.PC+1) & 0xFF
#			self.SP = self.SP - 1
#			self.memory[self.SP] = ((self.PC+1) >> 8) & 0xFF
#
#			new_adress = 0x38
#			logging.info("%X - [%02X] RST 38", self.PC, opcode)
#			self.PC = new_adress

		# JP
		elif opcode == 0xC3:
			new_adress = self.memory[self.PC+1] + ( self.memory[self.PC+2] << 8 )
			logging.info("%X - [%02X] JP %X", self.PC, opcode, new_adress)
			self.PC = new_adress

		# JP NZ
		elif opcode == 0xC2:
			new_adress = self.memory[self.PC+1] + ( self.memory[self.PC+2] << 8 )
			logging.info("%X - [%02X] JP NZ %X", self.PC, opcode, new_adress)

			self.PC = self.PC + 3

			if self.flag_z == 0:
				self.PC = new_adress

		# JP (HL)
		elif opcode == 0xE9:
			new_adress = self.reg_HL
			logging.info("%X - [%02X] JP (HL)	!! WARNING Hazardous Implementation	[HL=%X]", self.PC, opcode, self.reg_HL)
			self.PC = new_adress

		# JR NZ xx
		elif opcode == 0x20:

			offset, = struct.unpack("b", chr(self.memory[self.PC+1]))

			logging.info("%X - [%02X] JR NZ %X+ %X		[=%X, flag_z=%X]", self.PC, opcode, self.PC + 2, offset, self.PC + 2 + offset, self.flag_z)
			self.PC = self.PC + 2

			if self.flag_z == 0:
				self.PC = self.PC + offset

		# JR Z xx
		elif opcode == 0x28:

			offset, = struct.unpack("b", chr(self.memory[self.PC+1]))
			logging.info("%X - [%02X] JR Z %X+ %X		[=%X]", self.PC, opcode, self.PC+2, offset, self.PC + 2 + offset)
			self.PC = self.PC + 2

			if self.flag_z == 1:
				self.PC = self.PC + offset

		# JR xx
		elif opcode == 0x18:

			offset, = struct.unpack("b", chr(self.memory[self.PC+1]))
			logging.info("%X - [%02X] JR %X+ %X		[=%X]", self.PC, opcode, self.PC+2, offset, self.PC + 2 + offset)
			self.PC = self.PC + 2 + offset

		# JP Z xx
		elif opcode == 0xCA:

			new_adress = self.memory[self.PC+1] + ( self.memory[self.PC+2] << 8 )
			logging.info("%X - [%02X] JP Z %X", self.PC, opcode, new_adress)

			self.PC = self.PC + 3

			if self.flag_z == 1:
				self.PC = new_adress

		# CALL aa bb
		elif opcode == 0xCD:
			self.SP = self.SP - 1
			self.memory[self.SP] = (self.PC+3) & 0xFF
			self.SP = self.SP - 1
			self.memory[self.SP] = ((self.PC+3) >> 8) & 0xFF

			new_adress = self.memory[self.PC+1] + ( self.memory[self.PC+2] << 8 )
			logging.info("%X - [%02X] --> CALL %X", self.PC, opcode, new_adress)
			self.PC = new_adress

		# XOR A => A (A = 0)
		elif opcode == 0xAF:
			logging.info("%X - [%02X] XOR A, A", self.PC, opcode)
			self.reg_A = 0
			self.flag_z = 1
			self.flag_n = 0
			self.flag_h = 0
			self.flag_c = 0
			self.PC = self.PC + 1

#		# XOR B => A
#		elif opcode == 0xA8:
#			logging.info("%X - [%02X] XOR A, B", self.PC, opcode)
#
#			self.reg_A = self.reg_A ^ self.reg_B
#
#			self.flag_z = 0
#			if self.reg_A == 0:
#				self.flag_z = 1
#
#			self.flag_n = 0
#			self.flag_h = 0
#			self.flag_c = 0
#			self.PC = self.PC + 1

		# XOR C => A
		elif opcode == 0xA9:

			self.reg_A = (self.reg_A ^ self.reg_C) & 0xFF
			logging.info("%X - [%02X] XOR A, C		[A->0x%X]", self.PC, opcode, self.reg_A)

			self.flag_z = 0
			if self.reg_A == 0:
				self.flag_z = 1

			self.flag_n = 0
			self.flag_h = 0
			self.flag_c = 0
			self.PC = self.PC + 1

#		# XOR xx => A
#		elif opcode == 0xEE:
#			value = self.memory[self.PC+1]
#			logging.info("%X - [%02X] XOR A, 0x%X", self.PC, opcode, value)
#
#			self.reg_A = self.reg_A ^ value
#
#			self.flag_z = 0
#			if self.reg_A == 0:
#				self.flag_z = 1
#
#			self.flag_n = 0
#			self.flag_h = 0
#			self.flag_c = 0
#			self.PC = self.PC + 2
#
#		# OR A, A => A
#		elif opcode == 0xB7:
#			logging.info("%X - [%02X] OR A, A", self.PC, opcode)
#			if self.reg_A == 0:
#				self.flag_z = 1
#			else:
#				self.flag_z = 0
#
#			self.PC = self.PC + 1

		# OR A, xx => A
		elif opcode == 0xF6:
			value = self.memory[self.PC+1]
			logging.info("%X - [%02X] OR A, 0x%X", self.PC, opcode, value)
			
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
		elif opcode == 0x2F:
			self.flag_n = 1
			self.flag_h = 1
			self.reg_A = (~self.reg_A) & 0xFF
			logging.info("%X - [%02X] CPL A, A		[A->0x%X]", self.PC, opcode, self.reg_A)
			self.PC = self.PC + 1

		# OR C, A => A
		elif opcode == 0xB1:
			logging.info("%X - [%02X] OR A, C		[A=%X, C=%X]", self.PC, opcode, self.reg_A, self.reg_C)
			self.reg_A = self.reg_A | self.reg_C

			self.flag_z = 0
			self.flag_n = 0
			self.flag_h = 0
			self.flag_c = 0

			if self.reg_A == 0:
				self.flag_z = 1

			self.PC = self.PC + 1

		# OR B, A => A
		elif opcode == 0xB0:
			logging.info("%X - [%02X] OR A, B		[A=%X, B=%X]", self.PC, opcode, self.reg_A, self.reg_B)
			self.reg_A = self.reg_A | self.reg_B

			self.flag_z = 0
			self.flag_n = 0
			self.flag_h = 0
			self.flag_c = 0

			if self.reg_A == 0:
				self.flag_z = 1

			self.PC = self.PC + 1

		# AND A, xx => A
		elif opcode == 0xE6:
			logging.info("%X - [%02X] AND A, 0x%X", self.PC, opcode, self.memory[self.PC+1])

			self.reg_A = self.reg_A & self.memory[self.PC+1]

			self.flag_z = 0
			self.flag_n = 0
			self.flag_c = 0
			self.flag_h = 1

			if self.reg_A == 0:
				self.flag_z = 1

			self.PC = self.PC + 2

#		# AND A, B => A
#		elif opcode == 0xA0:
#			logging.info("%X - [%02X] AND A, B", self.PC, opcode)
#
#			self.reg_A = self.reg_A & self.reg_B
#
#			if self.reg_A == 0:
#				self.flag_z = 1
#			else:
#				self.flag_z = 0
#
#			self.PC = self.PC + 2
#

		# AND A, C => A
		elif opcode == 0xA1:
			logging.info("%X - [%02X] AND A, C", self.PC, opcode)

			self.reg_A = self.reg_A & self.reg_C

			self.flag_z = 0
			self.flag_n = 0
			self.flag_c = 0
			self.flag_h = 1

			if self.reg_A == 0:
				self.flag_z = 1

			self.PC = self.PC + 1


		# CB prefix management
		elif opcode == 0xCB:
			real_code = self.memory[self.PC+1]

			# SWAP A
			if real_code == 0x37:
				self.reg_A = ((self.reg_A & 0xF0)>>4) + ((self.reg_A & 0xF)<<4)

				logging.info("%X - [%02X-%02X] SWAP A		[A->0x%X]", self.PC, opcode, real_code, self.reg_A)

				self.flag_z = 0
				self.flag_n = 0
				self.flag_h = 0
				self.flag_c = 0

				if self.reg_A == 0:
					self.flag_z = 1

				self.PC = self.PC + 2

			# SLA A
			elif real_code == 0x27:

				temp = self.reg_A << 1
				logging.info("%X - [%02X-%02X] SLA A		[A=%X, SLA=%X, flag_c=%X]", self.PC, opcode, real_code, self.reg_A, temp & 0xFF, temp & 0x100)

				self.reg_A = temp & 0xFF

				self.flag_z = 0
				self.flag_c = 0

				if self.reg_A == 0:
					self.flag_z = 1

				if temp & 0x100 != 0:
					self.flag_c = 1

				self.PC = self.PC + 2

			# RES 0, (HL)
			elif real_code == 0x86:
				self.memory[self.reg_HL] = self.memory[self.reg_HL] & 0xFE
				logging.info("%X - [%02X-%02X] RES 0, (HL)		[HL=0x%X, (HL)=0x%X]", self.PC, opcode, real_code, self.reg_HL, self.memory[self.reg_HL])

				self.PC = self.PC + 2

			# RES 0, A
			elif real_code == 0x87:
				self.reg_A = self.reg_A & 0xFE
				logging.info("%X - [%02X-%02X] RES 0, A		[A->0x%X]", self.PC, opcode, real_code, self.reg_A)

				self.PC = self.PC + 2

#			# SET 7, (HL)
#			elif real_code == 0xFE:
#				value = self.memory[self.reg_HL]
#				self.memory[self.reg_HL] = value |  0x80
#				logging.info("%X - [%02X-%02X] SET 7, (HL)		[%X -> %X]", self.PC, opcode, real_code, value, self.memory[self.reg_HL])
#
#				self.PC = self.PC + 2
#
#			# BIT 0, B
#			elif real_code == 0x40:
#				value = self.reg_B & 0x1
#
#				self.flag_z = 0
#				if value == 0:
#					self.flag_z = 1
#
#				logging.info("%X - [%02X-%02X] BIT 0, B		[B=%X, value=%X, flag_z=%X]", self.PC, opcode, real_code, self.reg_B, value, self.flag_z)
#
#				self.PC = self.PC + 2
#
#			# BIT 1, B
#			elif real_code == 0x48:
#				value = self.reg_B & 0x2
#
#				self.flag_z = 0
#				if value == 0:
#					self.flag_z = 1
#
#				logging.info("%X - [%02X-%02X] BIT 1, B		[B=%X, value=%X, flag_z=%X]", self.PC, opcode, real_code, self.reg_B, value, self.flag_z)
#
#				self.PC = self.PC + 2

			# BIT 2, B
			elif real_code == 0x50:
				value = self.reg_B & 0x4

				self.flag_z = 0
				if value == 0:
					self.flag_z = 1

				logging.info("%X - [%02X-%02X] BIT 2, B		[B=%X, value=%X, flag_z=%X]", self.PC, opcode, real_code, self.reg_B, value, self.flag_z)

				self.PC = self.PC + 2

			# BIT 4, B
			elif real_code == 0x60:
				value = self.reg_B & 0x10

				self.flag_z = 0
				if value == 0:
					self.flag_z = 1

				logging.info("%X - [%02X-%02X] BIT 4, B		[B=%X]", self.PC, opcode, real_code, self.reg_B)

				self.PC = self.PC + 2

#			# BIT 4, C
#			elif real_code == 0x61:
#				value = self.reg_C & 0x10
#
#				self.flag_z = 0
#				if value == 0:
#					self.flag_z = 1
#
#				logging.info("%X - [%02X-%02X] BIT 4, C		[B=%X]", self.PC, opcode, real_code, self.reg_C)
#
#				self.PC = self.PC + 2

			# BIT 5, B
			elif real_code == 0x68:
				value = self.reg_B & 0x20

				self.flag_z = 0
				if value == 0:
					self.flag_z = 1

				logging.info("%X - [%02X-%02X] BIT 5, B		[B=%X]", self.PC, opcode, real_code, self.reg_B)

				self.PC = self.PC + 2

#			# BIT 5, C
#			elif real_code == 0x69:
#				value = self.reg_C & 0x20
#
#				self.flag_z = 0
#				if value == 0:
#					self.flag_z = 1
#
#				logging.info("%X - [%02X-%02X] BIT 5, C		[B=%X]", self.PC, opcode, real_code, self.reg_C)
#
#				self.PC = self.PC + 2

			# BIT 5, A
			elif real_code == 0x6F:
				value = self.reg_A & 0x20

				self.flag_z = 0
				if value == 0:
					self.flag_z = 1

				logging.info("%X - [%02X-%02X] BIT 5, A		[A=%X]", self.PC, opcode, real_code, self.reg_A)

				self.PC = self.PC + 2

			# BIT 6, A
			elif real_code == 0x77:
				value = self.reg_A & 0x40

				self.flag_z = 0
				if value == 0:
					self.flag_z = 1

				logging.info("%X - [%02X-%02X] BIT 6, A		[B=%X]", self.PC, opcode, real_code, self.reg_A)

				self.PC = self.PC + 2

			# BIT 7, A
			elif real_code == 0x7E:

				logging.info("%X - [%02X-%02X] BIT ?, ?		WARNING : Unknown opcode ???", self.PC, opcode, real_code)

				self.PC = self.PC + 2

			# BIT 7, A
			elif real_code == 0x7F:
				value = self.reg_A & 0x80

				self.flag_z = 0
				if value == 0:
					self.flag_z = 1

				logging.info("%X - [%02X-%02X] BIT 7, A		[B=%X]", self.PC, opcode, real_code, self.reg_A)

				self.PC = self.PC + 2


			# BIT 3, B
			elif real_code == 0x58:
				value = self.reg_B & 0x8

				self.flag_z = 0
				if value == 0:
					self.flag_z = 1

				logging.info("%X - [%02X-%02X] BIT 3, B		[B=%X]", self.PC, opcode, real_code, self.reg_B)

				self.PC = self.PC + 2

#			# BIT 3, A
#			elif real_code == 0x5F:
#				value = self.reg_A & 0x8
#
#				self.flag_z = 0
#				if value == 0:
#					self.flag_z = 1
#
#				logging.info("%X - [%02X-%02X] BIT 3, A		[B=%X]", self.PC, opcode, real_code, self.reg_A)
#
#				self.PC = self.PC + 2
#
			else :
				logging.info("%X - [%02X] Unsupported CB %X", self.PC, opcode, real_code)
				sd

		# LD aabb => HL
		elif opcode == 0x21:
			self.reg_HL = self.memory[self.PC+1] + ( self.memory[self.PC+2] << 8 )
			logging.info("%X - [%02X] LD HL, %X", self.PC, opcode, self.reg_HL)
			self.PC = self.PC + 3

#		# LD A => A
#		elif opcode == 0x7F:
#			logging.info("%X - [%02X] LD A, A", self.PC, opcode)
#			self.PC = self.PC + 1

		# LD B => B
		elif opcode == 0x40:
			logging.info("%X - [%02X] LD B, B", self.PC, opcode)
			self.PC = self.PC + 1

		# LD A => B
		elif opcode == 0x47:
			logging.info("%X - [%02X] LD B, A", self.PC, opcode)
			self.reg_B = self.reg_A
			self.PC = self.PC + 1

		# LD A => C
		elif opcode == 0x4F:
			logging.info("%X - [%02X] LD C, A", self.PC, opcode)
			self.reg_C = self.reg_A
			self.PC = self.PC + 1

		# LD A => D
		elif opcode == 0x57:
			logging.info("%X - [%02X] LD D, A", self.PC, opcode)
			self.reg_D = self.reg_A
			self.PC = self.PC + 1

		# LD A => E
		elif opcode == 0x5F:
			logging.info("%X - [%02X] LD E, A", self.PC, opcode)
			self.reg_E = self.reg_A
			self.PC = self.PC + 1

		# LD C => A
		elif opcode == 0x79:
			logging.info("%X - [%02X] LD A, C", self.PC, opcode)
			self.reg_A = self.reg_C
			self.PC = self.PC + 1

		# LD C => L
		elif opcode == 0x69:
			logging.info("%X - [%02X] LD L, C", self.PC, opcode)
			self.reg_HL = (self.reg_HL & 0xFF00) + (self.reg_C & 0xFF)
			self.PC = self.PC + 1

		# LD E => L
		elif opcode == 0x6B:
			logging.info("%X - [%02X] LD L, E", self.PC, opcode)
			self.reg_HL = (self.reg_HL & 0xFF00) + (self.reg_E & 0xFF)
			self.PC = self.PC + 1

#		# LD xx => L
#		elif opcode == 0x2E:
#			value = self.memory[self.PC+1]
#			logging.info("%X - [%02X] LD L, 0x%X", self.PC, opcode, value)
#			self.reg_HL = (self.reg_HL & 0xFF00) + (value & 0xFF)
#			self.PC = self.PC + 2

		# LD L => E
		elif opcode == 0x5D:
			logging.info("%X - [%02X] LD E, L		[L=%X]", self.PC, opcode, (self.reg_HL & 0xFF))
			self.reg_E = (self.reg_HL & 0xFF)
			self.PC = self.PC + 1

		# LD L => A
		elif opcode == 0x7D:
			logging.info("%X - [%02X] LD A, L		[L=%X]", self.PC, opcode, (self.reg_HL & 0xFF))
			self.reg_A = (self.reg_HL & 0xFF)
			self.PC = self.PC + 1

		# LD B => H
		elif opcode == 0x60:
			self.reg_HL = (self.reg_HL & 0xFF) + ((self.reg_B << 8) & 0xFF00)
			logging.info("%X - [%02X] LD H, B		[HL=0x%X, B=0x%X]", self.PC, opcode, self.reg_HL, self.reg_B)
			self.PC = self.PC + 1

		# LD H => D
		elif opcode == 0x54:
			self.reg_D = (self.reg_HL >> 8) & 0xFF
			logging.info("%X - [%02X] LD D, H		[H=%X]", self.PC, opcode, self.reg_D)
			self.PC = self.PC + 1

		# LD H => A
		elif opcode == 0x7C:
			self.reg_A = (self.reg_HL >> 8) & 0xFF
			logging.info("%X - [%02X] LD A, H		[H=%X]", self.PC, opcode, self.reg_A)
			self.PC = self.PC + 1

		# LD A => L
		elif opcode == 0x6F:
			self.reg_HL = (self.reg_HL & 0xFF00) + (self.reg_A & 0xFF)
			#self.reg_HL = (self.reg_HL & 0xFF) + ((self.reg_A << 8) & 0xFF00)
			logging.info("%X - [%02X] LD L, A		[HL=%X]", self.PC, opcode, self.reg_HL)
			self.PC = self.PC + 1

		# LD D => H
		elif opcode == 0x62:
			self.reg_HL = (self.reg_HL & 0xFF) + ((self.reg_D << 8) & 0xFF00)
			logging.info("%X - [%02X] LD H, D		[HL=%X]", self.PC, opcode, self.reg_HL)
			self.PC = self.PC + 1

		# LD A => H
		elif opcode == 0x67:
#			#self.reg_HL = (self.reg_HL & 0xFF00) + (self.reg_A & 0xFF)
			self.reg_HL = (self.reg_HL & 0xFF) + ((self.reg_A << 8) & 0xFF00)
			logging.info("%X - [%02X] LD H, A		[HL=%X]", self.PC, opcode, self.reg_HL)
			self.PC = self.PC + 1

		# LD xx => B
		elif opcode == 0x6:
			self.reg_B = self.memory[self.PC+1]
			logging.info("%X - [%02X] LD B, 0x%X", self.PC, opcode, self.reg_B)
			self.PC = self.PC + 2

		# LD xx => D
		elif opcode == 0x16:
			self.reg_D = self.memory[self.PC+1]
			logging.info("%X - [%02X] LD D, %X", self.PC, opcode, self.reg_D)
			self.PC = self.PC + 2

		# LD xx => E
		elif opcode == 0x1E:
			self.reg_E = self.memory[self.PC+1]
			logging.info("%X - [%02X] LD E, %X", self.PC, opcode, self.reg_E)
			self.PC = self.PC + 2

		# LD xx => C
		elif opcode == 0x0E:
			self.reg_C = self.memory[self.PC+1]
			logging.info("%X - [%02X] LD C, %X", self.PC, opcode, self.reg_C)
			self.PC = self.PC + 2

		# LD xx => A
		elif opcode == 0x3E:
			self.reg_A = self.memory[self.PC+1]
			logging.info("%X - [%02X] LD A, %X", self.PC, opcode, self.reg_A)
			self.PC = self.PC + 2

		# LD xx => H
		elif opcode == 0x26:
			value = self.memory[self.PC+1]
			logging.info("%X - [%02X] LD H, 0x%X", self.PC, opcode, value)
			self.reg_HL = (self.reg_HL & 0xFF) + ((value << 8) & 0xFF)
			self.PC = self.PC + 2

		# LDD A => mem[HL] and HL--
		elif opcode == 0x32:
			self.memory[self.reg_HL] = self.reg_A
			logging.info("%X - [%02X] LD (HL-), A		[HL=%X, A=%X]", self.PC, opcode, self.reg_HL, self.reg_A)
			self.reg_HL = self.reg_HL - 1
			self.PC = self.PC + 1

		# LDD mem[HL] => A and HL--
		elif opcode == 0x3A:
			self.reg_A = self.memory[self.reg_HL]
			logging.info("%X - [%02X] LD A, (HL-)		[HL=%X, (HL)=%X]", self.PC, opcode, self.reg_HL, self.reg_A)
			self.reg_HL = self.reg_HL - 1
			self.PC = self.PC + 1

		# LDI A => mem[HL] and HL++
		elif opcode == 0x22:
			self.memory[self.reg_HL] = self.reg_A
			logging.info("%X - [%02X] LD (HL+), A		[HL=%X, A=%X]", self.PC, opcode, self.reg_HL, self.reg_A)
			self.reg_HL = self.reg_HL + 1
			self.PC = self.PC + 1

		# LDD mem[HL] => A and HL++
		elif opcode == 0x2A:
			self.reg_A = self.memory[self.reg_HL]
			self.reg_HL = self.reg_HL + 1
			logging.info("%X - [%02X] LD A, (HL+)", self.PC, opcode)
			self.PC = self.PC + 1

		# LDD A => mem[HL]
		elif opcode == 0x77:
			self.memory[self.reg_HL] = self.reg_A 
			logging.info("%X - [%02X] LD (HL), A		[HL=0x%X, A=0x%X]", self.PC, opcode, self.reg_HL, self.reg_A)
			self.PC = self.PC + 1

		# LDH A => mem[FF00 + xx]
		elif opcode == 0xE0:
			self.memory[0xFF00 + self.memory[self.PC+1]] = self.reg_A
			logging.info("%X - [%02X] LDH (0xFF00 + %X), A		[@=%X, A=%X]", self.PC, opcode, self.memory[self.PC+1], 0xFF00 + self.memory[self.PC+1], self.reg_A)
			self.PC = self.PC + 2

#		# LDD [HL] => A
#		elif opcode == 0x32:
#			self.reg_A = self.memory[self.reg_HL]
#			logging.info("%X - [%02X] LD A,(HL-), A", self.PC, opcode)
#			self.PC = self.PC + 1

		# LDH mem[FF00+xx] => A
		elif opcode == 0xF0:
			offset = self.memory[self.PC+1]
			self.reg_A = self.memory[0xFF00 + offset]
			logging.info("%X - [%02X] LD A, (0xFF00+%X)		[(%X)=%X]", self.PC, opcode, offset, 0xFF00+offset, self.reg_A)
			self.PC = self.PC + 2

		# LD xx => mem[HL]
		elif opcode == 0x36:
			self.memory[self.reg_HL] = self.memory[self.PC+1]
			logging.info("%X - [%02X] LD (HL), %X		[HL=%X]", self.PC, opcode, self.memory[self.PC+1], self.reg_HL)
			self.PC = self.PC + 2

		# LD  A => mem[aabb]
		elif opcode == 0xEA:
			adress = self.memory[self.PC+1] + ( self.memory[self.PC+2] << 8 )
			self.memory[adress] = self.reg_A
			logging.info("%X - [%02X] LD (%X), A", self.PC, opcode, adress)
			self.PC = self.PC + 3

		# LD  aabb => SP
		elif opcode == 0x31:
			adress = self.memory[self.PC+1] + ( self.memory[self.PC+2] << 8 )
			self.SP = adress
			logging.info("%X - [%02X] LD SP, %X", self.PC, opcode, adress)
			self.PC = self.PC + 3

		# LD  mem[aabb] => A
		elif opcode == 0xFA:
			adress = self.memory[self.PC+1] + ( self.memory[self.PC+2] << 8 )
			self.reg_A = self.memory[adress]
			logging.info("%X - [%02X] LD A, (%X)", self.PC, opcode, adress)
			self.PC = self.PC + 3

		# LD  mem[HL] => A
		elif opcode == 0x7E:
			self.reg_A = self.memory[self.reg_HL]
			logging.info("%X - [%02X] LD A, (HL)		[HL=%X, (HL)=%X]", self.PC, opcode, self.reg_HL, self.reg_A)
			self.PC = self.PC + 1

		# LD  mem[DE] => A
		elif opcode == 0x1A:
			adress = (self.reg_D << 8) + self.reg_E
			self.reg_A = self.memory[adress] & 0xFF
			logging.info("%X - [%02X] LD A, (DE)		[DE=%X, (DE)=%X]", self.PC, opcode, adress, self.reg_A)
			self.PC = self.PC + 1

		# LD  A => mem[DE]
		elif opcode == 0x12:
			adress = (self.reg_D << 8) + self.reg_E
			self.memory[adress] = self.reg_A
			logging.info("%X - [%02X] LD (DE), A		[DE=%X, A=%X]", self.PC, opcode, adress, self.reg_A)
			self.PC = self.PC + 1

		# LD  mem[HL] => B
		elif opcode == 0x46:
			self.reg_B = self.memory[self.reg_HL]
			logging.info("%X - [%02X] LD B,(HL)		[HL=0x%X, (HL)=0x%X]", self.PC, opcode, self.reg_HL, self.reg_B)
			self.PC = self.PC + 1

		# LD  mem[HL] => C
		elif opcode == 0x4E:
			self.reg_C = self.memory[self.reg_HL]
			logging.info("%X - [%02X] LD C,(HL)		[HL=0x%X, (HL)=0x%X]", self.PC, opcode, self.reg_HL, self.reg_C)
			self.PC = self.PC + 1

		# LD  mem[HL] => E
		elif opcode == 0x5E:
			self.reg_E = self.memory[self.reg_HL]
			logging.info("%X - [%02X] LD E, (HL)		[HL=%X (HL)=%X]", self.PC, opcode, self.reg_HL, self.reg_E)
			self.PC = self.PC + 1

		# LD  C => mem[HL]
		elif opcode == 0x71:
			self.memory[self.reg_HL] = self.reg_C
			logging.info("%X - [%02X] LD (HL), C		[HL=%X C=%X]", self.PC, opcode, self.reg_HL, self.reg_C)
			self.PC = self.PC + 1

		# LD  D => mem[HL]
		elif opcode == 0x72:
			self.memory[self.reg_HL] = self.reg_D
			logging.info("%X - [%02X] LD (HL), D		[HL=%X D=%X]", self.PC, opcode, self.reg_HL, self.reg_D)
			self.PC = self.PC + 1

		# LD  E => mem[HL]
		elif opcode == 0x73:
			self.memory[self.reg_HL] = self.reg_E
			logging.info("%X - [%02X] LD (HL), E		[HL=%X E=%X]", self.PC, opcode, self.reg_HL, self.reg_E)
			self.PC = self.PC + 1

		# LD  mem[HL] => D
		elif opcode == 0x56:
			self.reg_D = self.memory[self.reg_HL]
			logging.info("%X - [%02X] LD D, (HL)		[HL=%X, (HL)=%X]", self.PC, opcode, self.reg_HL,self.reg_D)
			self.PC = self.PC + 1

		# LD  aa bb => BC
		elif opcode == 0x01:
			self.reg_B = self.memory[self.PC+2]
			self.reg_C = self.memory[self.PC+1]
			logging.info("%X - [%02X] LD BC, %X", self.PC, opcode, (self.reg_B << 8) + self.reg_C)
			self.PC = self.PC + 3

		# LD  aa bb => DE
		elif opcode == 0x11:
			self.reg_D = self.memory[self.PC+2]
			self.reg_E = self.memory[self.PC+1]
			logging.info("%X - [%02X] LD DE, %X", self.PC, opcode, (self.memory[self.PC+2]<<8) + self.memory[self.PC+1])
			self.PC = self.PC + 3

		# LD  (BC) => A
		elif opcode == 0x0A:
			BC = (self.reg_B << 8) + self.reg_C
			self.reg_A = self.memory[BC]
			logging.info("%X - [%02X] LD A, (BC)		[BC=%X (BC)=%X]", self.PC, opcode, BC, self.reg_A)
			self.PC = self.PC + 1

		# LD  A => 0xFF00 + C
		elif opcode == 0xE2:
			self.memory[0xFF00 + self.reg_C] = self.reg_A
			logging.info("%X - [%02X] LD (0xFF00+C), A		[C=%X, A=%X]", self.PC, opcode, self.reg_C, self.reg_A)
			self.PC = self.PC + 1

		# LD  B => A
		elif opcode == 0x78:
			self.reg_A = self.reg_B
			logging.info("%X - [%02X] LD A, B		[A=0x%X]", self.PC, opcode, self.reg_A)
			self.PC = self.PC + 1

		# LD  D => A
		elif opcode == 0x7A:
			self.reg_A = self.reg_D
			logging.info("%X - [%02X] LD A, D", self.PC, opcode)
			self.PC = self.PC + 1

		# LD  E => A
		elif opcode == 0x7B:
			self.reg_A = self.reg_E
			logging.info("%X - [%02X] LD A, E", self.PC, opcode)
			self.PC = self.PC + 1

		# DEC A
		elif opcode == 0x3D:
			self.flag_z = 0

			if self.reg_A == 0:
				self.reg_A = 255
			else:
				self.reg_A = self.reg_A - 1
				if self.reg_A == 0:
					self.flag_z = 1

			self.flag_n = 1
			self.flag_h = 1

			logging.info("%X - [%02X] DEC A		[A=0x%X]", self.PC, opcode, self.reg_A)
			self.PC = self.PC + 1

		# DEC B
		elif opcode == 0x05:
			self.flag_z = 0

			if self.reg_B == 0:
				self.reg_B = 255
			else:
				self.reg_B = self.reg_B - 1
				if self.reg_B == 0:
					self.flag_z = 1

			self.flag_n = 1
			self.flag_h = 1

			logging.info("%X - [%02X] DEC B		[B=0x%X]", self.PC, opcode, self.reg_B)
			self.PC = self.PC + 1

		# DEC C
		elif opcode == 0x0D:
			self.flag_z = 0
			if self.reg_C == 0:
				self.reg_C = 255
			else:
				self.reg_C = self.reg_C - 1
				if self.reg_C == 0:
					self.flag_z = 1

			self.flag_n = 1
			self.flag_h = 1

			logging.info("%X - [%02X] DEC C", self.PC, opcode)
			self.PC = self.PC + 1

		# INC HL
		elif opcode == 0x34:
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


			logging.info("%X - [%02X] INC (HL)		[(HL)=%X->%X]", self.PC, opcode, value, self.memory[self.reg_HL])
			self.PC = self.PC + 1

		# DEC (HL)
		elif opcode == 0x35:
			value = self.memory[self.reg_HL]

			self.flag_z = 0
			if value == 0x0:
				self.memory[self.reg_HL] = 0xFF
			else:
				self.memory[self.reg_HL] = value - 1
				if value == 1:
					self.flag_z = 1

			self.flag_n = 1

			logging.info("%X - [%02X] DEC (HL)		[(HL)=%X]", self.PC, opcode, value-1)
			self.PC = self.PC + 1

		# DEC BC
		elif opcode == 0xB:
			BC = (self.reg_B << 8) + (self.reg_C)
			if BC == 0:
				BC = 0XFFFF
			else:
				BC = BC - 1

			self.reg_B = (BC >> 8) & 0xFF
			self.reg_C = (BC) & 0xFF

			logging.info("%X - [%02X] DEC BC		[BC=0x%X, B=0x%X, C=0x%X]", self.PC, opcode, BC, self.reg_B, self.reg_C)
			self.PC = self.PC + 1

		# INC BC
		elif opcode == 0x3:
			BC = (self.reg_B << 8) + (self.reg_C)
			if BC == 0xFFFF:
				BC = 0
			else:
				BC = BC + 1

			self.reg_B = (BC >> 8) & 0xFF
			self.reg_C = (BC) & 0xFF

			logging.info("%X - [%02X] INC BC		[BC=%X]", self.PC, opcode, BC)
			self.PC = self.PC + 1

		# INC C
		elif opcode == 0x0C:
			if self.reg_C == 255:
				self.reg_C = 0
				self.flag_z = 1
			else:
				self.reg_C = self.reg_C + 1
				self.flag_z = 0

			self.flag_n = 0

			logging.info("%X - [%02X] INC C		[C=0x%X]", self.PC, opcode, self.reg_C)
			self.PC = self.PC + 1

		# INC E
		elif opcode == 0x1C:
			if self.reg_E == 255:
				self.reg_E = 0
				self.flag_z = 1
			else:
				self.reg_E = self.reg_E + 1
				self.flag_z = 0

			self.flag_n = 0

			logging.info("%X - [%02X] INC E		[E=0x%X]", self.PC, opcode, self.reg_E)
			self.PC = self.PC + 1

		# INC A
		elif opcode == 0x3C:
			if self.reg_A == 255:
				self.reg_A = 0
				self.flag_z = 1
			else:
				self.reg_A = self.reg_A + 1
				self.flag_z = 0

			self.flag_n = 0

			logging.info("%X - [%02X] INC A		[A=0x%X]", self.PC, opcode, self.reg_A)
			self.PC = self.PC + 1


		# INC HL
		elif opcode == 0x23:
			if self.reg_HL == 0xFFFF:
				self.reg_HL = 0
				self.flag_c = 1
				self.flag_z = 1
			else:
				self.reg_HL = self.reg_HL + 1
				self.flag_z = 0

			self.flag_n = 0

			logging.info("%X - [%02X] INC HL		[HL=%X]", self.PC, opcode, self.reg_HL)
			self.PC = self.PC + 1

		# INC L
		elif opcode == 0x2C:
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

			logging.info("%X - [%02X] INC L		[HL=%X]", self.PC, opcode, self.reg_HL)
			self.PC = self.PC + 1

		# DEC L
		elif opcode == 0x2D:
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

			logging.info("%X - [%02X] DEC L		[HL=%X]", self.PC, opcode, self.reg_HL)
			self.PC = self.PC + 1

		# INC DE
		elif opcode == 0x13:
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

			logging.info("%X - [%02X] INC DE		[D=0x%X, E=0x%X]", self.PC, opcode, self.reg_D, self.reg_E)
			self.PC = self.PC + 1

		# ADD A, B
		elif opcode == 0x80:
			self.reg_A = self.reg_A + self.reg_B

			self.flag_z = 0
			self.flag_n = 0
			self.flag_c = 0

			if self.reg_A > 255:
				self.reg_A = self.reg_A - 256
				self.flag_c = 1

			if self.reg_A == 0:
				self.flag_z = 1

			logging.info("%X - [%02X] ADD A, B", self.PC, opcode)
			self.PC = self.PC + 1

#		# ADD A, C
#		elif opcode == 0x81:
#			self.reg_A = self.reg_A + self.reg_C
#
#			self.flag_z = 0
#			self.flag_n = 0
#			self.flag_c = 0
#
#			if self.reg_A > 255:
#				self.reg_A = self.reg_A - 256
#				self.flag_c = 1
#
#			if self.reg_A == 0:
#				self.flag_z = 1
#
#			logging.info("%X - [%02X] ADD A, C", self.PC, opcode)
#			self.PC = self.PC + 1

		# ADD A, xx
		elif opcode == 0xC6:
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

			logging.info("%X - [%02X] ADD A, 0x%X", self.PC, opcode, value)
			self.PC = self.PC + 2

		# ADD A, A
		elif opcode == 0x87:
			logging.info("%X - [%02X] ADD A, A		[A=%X, A,A=%X]", self.PC, opcode, self.reg_A, (self.reg_A + self.reg_A) % 255)

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
		elif opcode == 0x85:
			L = self.reg_HL & 0xFF
			self.reg_A = (self.reg_A + L) % 255

			self.flag_z = 0
			self.flag_n = 0
			if self.reg_A == 0:
				self.flag_z = 1

			logging.info("%X - [%02X] ADD A, L		[L=%X, A=%X]", self.PC, opcode, L, self.reg_A)
			self.PC = self.PC + 1

		# ADD HL, DE
		elif opcode == 0x19:
			DE = (self.reg_D << 8) + self.reg_E
			logging.info("%X - [%02X] ADD HL, DE		[HL=%X DE=%X => HL=%X]", self.PC, opcode, self.reg_HL, DE, self.reg_HL + DE)

			self.reg_HL = self.reg_HL + DE

			self.flag_n = 0
			self.flag_c = 0
			
			if self.reg_HL > 0xFFFF:
				self.reg_HL = self.reg_HL - 0x10000
				self.flag_c = 1

			self.PC = self.PC + 1

		# ADD HL, BC
		elif opcode == 0x09:
			BC = (self.reg_B << 8) + self.reg_C
			logging.info("%X - [%02X] ADD HL, BC		[HL=%X BC=%X => HL=%X]", self.PC, opcode, self.reg_HL, BC, self.reg_HL + BC)
			self.reg_HL = self.reg_HL + BC

			self.flag_n = 0

			self.PC = self.PC + 1

		# ADC A, C
		elif opcode == 0x89:
			self.reg_A = self.reg_A + self.reg_C + self.flag_c

			self.flag_z = 0
			self.flag_n = 0
			self.flag_c = 0

			if self.reg_A > 255:
				self.reg_A = self.reg_A - 256
				self.flag_c = 1

			if self.reg_A == 0:
				self.flag_z = 1

			logging.info("%X - [%02X] ADC A, C", self.PC, opcode)
			self.PC = self.PC + 1

		# SUB A, B
		elif opcode == 0x90:
			self.reg_A = self.reg_A - self.reg_B

			self.flag_z = 0
			self.flag_n = 0
			if self.reg_A == 0:
				self.flag_z = 1

			if self.reg_A < 0:
				self.reg_A = 256 + self.reg_A
				self.flag_c = 1

			logging.info("%X - [%02X] SUB A, B		[A=%X]", self.PC, opcode, self.reg_A)
			self.PC = self.PC + 1

		# SBC A, C
		elif opcode == 0x99:
			self.reg_A = self.reg_A - self.reg_C - self.flag_c

			self.flag_z = 0
			self.flag_n = 0
			if self.reg_A == 0:
				self.flag_z = 1

			if self.reg_A < 0:
				self.reg_A = 256 + self.reg_A
				self.flag_c = 1

			logging.info("%X - [%02X] SBC A, C		[A=%X]", self.PC, opcode, self.reg_A)
			self.PC = self.PC + 1

		# SBC A, xx
		elif opcode == 0xDE:
			value = self.memory[self.PC+1]
			self.reg_A = self.reg_A - value - self.flag_c

			self.flag_z = 0
			self.flag_n = 0
			if self.reg_A == 0:
				self.flag_z = 1

			if self.reg_A < 0:
				self.reg_A = 256 + self.reg_A
				self.flag_c = 1

			logging.info("%X - [%02X] SBC A, 0x%X		[A=%X]", self.PC, opcode, value, self.reg_A)
			self.PC = self.PC + 2

		# RLCA
		elif opcode == 0x07:
			value = self.reg_A << 1
			self.flag_c = 0

			if value & 0x100 != 0:
				self.flag_c = 1

			value = (value & 0xFF) | 1
			logging.info("%X - [%02X] RLCA		[oldA=%X, A=%X]", self.PC, opcode, self.reg_A, value)
			self.reg_A = value


			self.flag_n = 0

			self.PC = self.PC + 1

		# DI
		elif opcode == 0xF3:
			logging.info("%X - [%02X] DI - Disable Interrupt management", self.PC, opcode)
			self.interrupt_enabled = False
			self.PC = self.PC + 1

		# EI
		elif opcode == 0xFB:
			logging.info("%X - [%02X] EI - Enable Interrupt management", self.PC, opcode)
			self.interrupt_enabled = True
			self.PC = self.PC + 1

		# CP x
		elif opcode == 0xFE:
			dummy = self.reg_A - self.memory[self.PC+1]
			logging.info("%X - [%02X] CP A, 0x%X", self.PC, opcode, self.memory[self.PC+1])
			self.flag_z = 0
			self.flag_n = 1
			self.flag_c = 0

			if dummy == 0:
				self.flag_z = 1
			elif dummy < 0:
				self.flag_c = 1

			self.PC = self.PC + 2

#		# CP E
#		elif opcode == 0xBB:
#			dummy = self.reg_A - self.reg_E
#			logging.info("%X - [%02X] CP A, E", self.PC, opcode)
#			self.flag_z = 0
#			self.flag_n = 0
#			self.flag_c = 0
#
#			if dummy == 0:
#				self.flag_z = 1
#			elif dummy < 0:
#				self.flag_c = 1
#
#			self.PC = self.PC + 1
#
#		# CP B
#		elif opcode == 0xB8:
#			dummy = self.reg_A - self.reg_B
#			logging.info("%X - [%02X] CP A, B", self.PC, opcode)
#			self.flag_z = 0
#			self.flag_n = 0
#			self.flag_c = 0
#
#			if dummy == 0:
#				self.flag_z = 1
#			elif dummy < 0:
#				self.flag_c = 1
#
#			self.PC = self.PC + 1

		# PUSH AF
		elif opcode == 0xF5:
			F = (self.flag_c << 4) | (self.flag_h << 5) | (self.flag_n << 6) | (self.flag_z << 7)
			self.SP = self.SP - 1
			self.memory[self.SP] = F
			self.SP = self.SP - 1
			self.memory[self.SP] = self.reg_A

			logging.info("%X - [%02X]	PUSH AF	[A=%X, z=%X, n=%X, h=%X, c=%X, F=%X]", self.PC, opcode, self.reg_A, self.flag_z, self.flag_n, self.flag_h, self.flag_c, F)

			self.PC = self.PC + 1

		# PUSH BC
		elif opcode == 0xC5:
			self.SP = self.SP - 1
			self.memory[self.SP] = self.reg_B
			self.SP = self.SP - 1
			self.memory[self.SP] = self.reg_C

			logging.info("%X - [%02X] PUSH BC", self.PC, opcode)

			self.PC = self.PC + 1

		# PUSH DE
		elif opcode == 0xD5:
			self.SP = self.SP - 1
			self.memory[self.SP] = self.reg_E
			self.SP = self.SP - 1
			self.memory[self.SP] = self.reg_D

			logging.info("%X - [%02X] PUSH DE		[D=%X, E=%X]", self.PC, opcode, self.reg_D, self.reg_E)

			self.PC = self.PC + 1

		# PUSH HL
		elif opcode == 0xE5:
			self.SP = self.SP - 1
			self.memory[self.SP] = self.reg_HL & 0xFF
			self.SP = self.SP - 1
			self.memory[self.SP] = (self.reg_HL & 0xFF00)>>8

			logging.info("%X - [%02X] PUSH HL", self.PC, opcode)

			self.PC = self.PC + 1

		# POP DE
		elif opcode == 0xD1:
			self.reg_D = self.memory[self.SP]
			self.SP = self.SP + 1
			self.reg_E = self.memory[self.SP]
			self.SP = self.SP + 1

			logging.info("%X - [%02X] POP DE		[D=%X, E=%X]", self.PC, opcode, self.reg_D, self.reg_E)

			self.PC = self.PC + 1

		# POP BC
		elif opcode == 0xC1:
			self.reg_C = self.memory[self.SP]
			self.SP = self.SP + 1
			self.reg_B = self.memory[self.SP]
			self.SP = self.SP + 1

			logging.info("%X - [%02X] POP BC		[B=%X, C=%X]", self.PC, opcode, self.reg_B, self.reg_C)

			self.PC = self.PC + 1

		# POP AF
		elif opcode == 0xF1:
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

			#logging.info("%X - [%02X] POP AF		[A=%X, A=%X]", self.PC, opcode, self.reg_A, self.reg_A)
			logging.info("%X - [%02X]	POP AF	[A=%X, z=%X, n=%X, h=%X, c=%X, F=%X]", self.PC, opcode, self.reg_A, self.flag_z, self.flag_n, self.flag_h, self.flag_c, F)

			self.PC = self.PC + 1

		# POP HL
		elif opcode == 0xE1:
			HL_High = self.memory[self.SP]
			self.SP = self.SP + 1
			HL_Low = self.memory[self.SP]
			self.SP = self.SP + 1

			self.reg_HL = (HL_High << 8) + HL_Low

			logging.info("%X - [%02X] POP HL		[HL=%X]", self.PC, opcode, self.reg_HL)

			self.PC = self.PC + 1

		# AND A, A
		elif opcode == 0xA7:
			self.flag_z = 0
			self.flag_n = 0
			self.flag_h = 1
			self.flag_c = 0

			if self.reg_A == 0:
				self.flag_z = 1

			logging.info("%X - [%02X] AND A, A", self.PC, opcode)

			self.PC = self.PC + 1

		# RET
		elif opcode == 0xC9:

			logging.info("%X - [%02X] <-- RET", self.PC, opcode)
			PC_High = self.memory[self.SP] & 0xFF
			self.SP = self.SP + 1
			PC_Low = self.memory[self.SP] & 0xFF
			self.SP = self.SP + 1

			self.PC = (PC_High << 8) + PC_Low

		# RETI
		elif opcode == 0xD9:
			self.interrupt_enabled = True

			PC_High = self.memory[self.SP] & 0xFF
			self.SP = self.SP + 1
			PC_Low = self.memory[self.SP] & 0xFF
			self.SP = self.SP + 1

			old_PC = self.PC
			self.PC = (PC_High << 8) + PC_Low

			logging.info("%X - [%02X] <---------- RETI		[Back to %X]", old_PC, opcode, self.PC)

		# RET NZ
		elif opcode == 0xC0:

			logging.info("%X - [%02X] RET NZ", self.PC, opcode)

			if self.flag_z == 0:
				PC_High = self.memory[self.SP] & 0xFF
				self.SP = self.SP + 1
				PC_Low = self.memory[self.SP] & 0xFF
				self.SP = self.SP + 1

				self.PC = (PC_High << 8) + PC_Low
			else:
				self.PC = self.PC + 1

		# RET Z
		elif opcode == 0xC8:

			logging.info("%X - [%02X] RET Z", self.PC, opcode)

			if self.flag_z == 1:
				PC_High = self.memory[self.SP] & 0xFF
				self.SP = self.SP + 1
				PC_Low = self.memory[self.SP] & 0xFF
				self.SP = self.SP + 1

				self.PC = (PC_High << 8) + PC_Low
			else:
				self.PC = self.PC + 1


		else:
			logging.info("%X - [%02X] Unsupported opcode", self.PC, opcode)
			#self.save_state(filename="state_crash.sav")
			sd

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



