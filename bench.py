import timeit

memory=[0, 1, 252, 2, 3]
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
print "ctypes", timeit.timeit('offset = ctypes.c_int8(memory[2])', setup='from __main__ import memory; import ctypes', number=1000000)
print "struct", timeit.timeit('offset, = struct.unpack("b", chr(memory[2]))', setup='from __main__ import memory; import struct', number=1000000)
print "numpy", timeit.timeit('offset = numpy.int8(memory[2])', setup='from __main__ import memory; import numpy', number=1000000)

print "*** add"
print "python", timeit.timeit('c=a+b', setup='a=5; b=34', number=10000000)
print "ctypes", timeit.timeit('c=a+b', setup='import ctypes; a=5; b=34', number=10000000)


