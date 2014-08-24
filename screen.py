#!/usr/bin/env python
import pygame
import threading
import time

colour_list = [(255,255,255),(150,150,150),(80,80,80),(0, 0, 0)]

class screen(threading.Thread):
	
	def __init__(self, gb_memory):
		threading.Thread.__init__(self)
		pygame.init ()
		pygame.display.set_mode ((320, 288))

		self.surface		= pygame.Surface ((320, 288))
		self.tiles_bank1	= pygame.Surface ((256, 192))

		pygame.display.flip ()
		self.vram = []
		self.tilemap = []
		
		self.memory = gb_memory
		self.stopped = False

	def is_stopped(self):
		return self.stopped

	def show(self):
		screen = pygame.display.get_surface()
		screen.fill ((255, 255, 255))
		screen.blit (self.surface, (0, 0))
		#screen.blit (self.tiles_bank1, (0, 0))
		pygame.display.flip ()

	def set_pixel(self, pixmap, pos_x, pos_y, colour):
		pixmap[2*pos_x, 2*pos_y] = colour
		pixmap[2*pos_x + 1, 2*pos_y] = colour
		pixmap[2*pos_x + 1, 2*pos_y + 1] = colour
		pixmap[2*pos_x, 2*pos_y + 1] = colour
		
	def update_vram(self, vram):
		pass

	def update_tilemap(self, tilemap):
		pass

	def draw_map(self):

		for j in range(32):
			for i in range(32):
				#tile = self.tilemap[i+32*j]
				tile = self.memory[0x9800 + i+32*j]
				pos_x = (tile % 16) * 16
				pos_y = (tile >> 4) * 16
				self.surface.blit(self.tiles_bank1, (i*8*2, j*8*2), ((pos_x, pos_y),(16, 16)) )

	def draw_sprites(self):
		for i in range(40):
			sprite_pos_y = self.memory[0xFE00 + i*4] - 16
			sprite_pos_x = self.memory[0xFE00 + i*4 + 1] - 8
			sprite_pattern = self.memory[0xFE00 + i*4 + 2]
			sprite_flags = self.memory[0xFE00 + i*4 + 3]
			
			pattern_pos_x = (sprite_pattern % 16) * 16
			pattern_pos_y = (sprite_pattern >> 4) * 16

			if sprite_pos_y != -16 and sprite_pos_x != -8:
				print "pos_x=%X pos_y=%X, pattern=%X, flags=%X" % (sprite_pos_x, sprite_pos_y, sprite_pattern, sprite_flags)
				self.surface.blit(self.tiles_bank1, (sprite_pos_x*2, sprite_pos_y*2), ((pattern_pos_x, pattern_pos_y),(16, 16)) )

	def draw_tiles(self):
		
		pixmap = pygame.PixelArray (self.tiles_bank1)
		
		x_pos = 0
		y_pos = 0
		# For each 192 tiles
		for tile_number in range(0xC0):	

			# For each 16 bytes representing tile 8 pixel heigth
			for j in range(8):
				# For each 8 bits of cur 
				for i in range(8):
					
					index = tile_number * 16
					#pix_low = (self.vram[index + (2*j)] >> (7-i)) & 1
					#pix_high = (self.vram[index + (2*j) + 1] >> (7-i)) & 1
					pix_low = (self.memory[0x8000 + index + (2*j)] >> (7-i)) & 1
					pix_high = (self.memory[0x8000 + index + (2*j) + 1] >> (7-i)) & 1
					pix_colour = (pix_high << 1) | pix_low

					self.set_pixel(pixmap, x_pos + i, y_pos + j, colour_list[pix_colour])
			
			x_pos = x_pos + 8
			if x_pos == 128:
				x_pos = 0
				y_pos = y_pos + 8

		del pixmap
		self.show()
	
	def run(self):
		while True:
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					pygame.quit()
					self.stopped = True
			
			self.draw_tiles()
			self.draw_map()
			self.draw_sprites()
			time.sleep(0.2)

def main():
	GBscreen = screen()
	GBscreen.start()

if __name__ == '__main__':
    main()
