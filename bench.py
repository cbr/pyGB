import timeit
import array

class memory_class:
	def __init__(self, size):
		self.memory = [0]*size

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

class memory_inherit_list(list):
	def __setitem__(self, offset, value):
		if offset < 0x8000:
			logging.info("illlegal write access to address %X", offset)
			return

		list.__setitem__(self, offset, value)
		if offset >= 0xFF00 and offset <= 0xFF70 and offset != 0xFF44 and offset != 0xFF00:
			logging.info("################# CALL Special Register %X = %X", offset, value)

		if offset == 0xFF46:
			source_start = value << 8
			dest_start = 0xFE00
			for i in range(0, 0xA0):
				list.__setitem__(self, dest_start + i, __getitem__(self, source_start + i))


class memory_array_class:
	def __init__(self, size):
		self.memory = array.array('i', [0] * size)

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

class MyList(list):
    def __getitem__(self, key):
        return self[key-1]
    def __setitem__(self, key, item):
        self[key-1] = item

var_memory_list=[0, 1, 252, 2, 3]

file = open('Tetris.gb', 'r')
tetris = file.read()
ob_memory = memory_class(0xFFFF)
ob_memory_array = memory_array_class(0xFFFF)

ob_memory_inherit = memory_inherit_list([0] * 0xFFFF)


print "*** memory class"
print "read list", timeit.timeit('PC=var_memory_list[3]', setup='from __main__ import var_memory_list', number=10000000)
print "read class list", timeit.timeit('PC=ob_memory[3]', setup='from __main__ import ob_memory', number=10000000)
print "read class array", timeit.timeit('PC=ob_memory_array[3]', setup='from __main__ import ob_memory_array', number=10000000)
print "read class list inherit", timeit.timeit('PC=ob_memory_inherit[3]', setup='from __main__ import ob_memory_inherit', number=10000000)
print "write list", timeit.timeit('var_memory_list[3]=5', setup='from __main__ import var_memory_list', number=10000000)
print "write class list", timeit.timeit('ob_memory[0x8001]=5', setup='from __main__ import ob_memory', number=10000000)
print "write class array", timeit.timeit('ob_memory_array[0x8001]=5', setup='from __main__ import ob_memory_array', number=10000000)
print "write class inherit", timeit.timeit('ob_memory_inherit[0x8001]=5', setup='from __main__ import ob_memory_inherit', number=10000000)

print "*** if_ternary"
print "if else", timeit.timeit('if C==0:\n	PC=4\nelse:	PC=3', setup='C=0', number=10000000)
print "if ternary", timeit.timeit('PC=4 if C==0 else 3', setup='C=0', number=10000000)
print "if else not", timeit.timeit('if C==0:\n	PC=4\nelse:	PC=3', setup='C=1', number=10000000)
print "if ternary not", timeit.timeit('PC=4 if C==0 else 3', setup='C=1', number=10000000)

print "*** if_else"
print "if", timeit.timeit('PC=3\nif C==0:\n	PC=4', setup='C=0', number=10000000)
print "if not", timeit.timeit('PC=3\nif C==0:\n	PC=4', setup='C=1', number=10000000)
print "if else", timeit.timeit('if C==0:\n	PC=4\nelse:	PC=3', setup='C=0', number=10000000)
print "if not else", timeit.timeit('if C==0:\n	PC=4\nelse:	PC=3', setup='C=1', number=10000000)

print "*** signed char extract"
print "ctypes", timeit.timeit('offset = ctypes.c_int8(var_memory_list[2])', setup='from __main__ import var_memory_list; import ctypes', number=1000000)
print "struct", timeit.timeit('offset, = struct.unpack("b", chr(var_memory_list[2]))', setup='from __main__ import var_memory_list; import struct', number=1000000)
print "numpy", timeit.timeit('offset = numpy.int8(var_memory_list[2])', setup='from __main__ import var_memory_list; import numpy', number=1000000)

print "*** add"
print "python", timeit.timeit('c=a+b', setup='a=5; b=34', number=10000000)
print "ctypes", timeit.timeit('c=a+b', setup='import ctypes; a=5; b=34', number=10000000)
