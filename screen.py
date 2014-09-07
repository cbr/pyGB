#!/usr/bin/env python
import sdl2
import sdl2.ext
import threading
import time
import logging

colour_list = [(255,255,255),(150,150,150),(80,80,80),(0, 0, 0)]

class screen(threading.Thread):
	
	def __init__(self, gb_memory):
		threading.Thread.__init__(self)

		#self.window = sdl2.ext.Window("pyGb", size=(320, 288))
		self.window = sdl2.ext.Window("pyGb", size=(160, 144))

		self.surface = self.window.get_surface()

		self.sprite_factory = sdl2.ext.SpriteFactory(sprite_type=sdl2.ext.SOFTWARE)
		# self.tiles_bank1_sprite = self.sprite_factory.create_sprite(size=(256, 192))
		self.tiles_bank1_sprite = self.sprite_factory.create_sprite(size=(128, 96))
		self.tiles_bank1 = self.tiles_bank1_sprite.surface

		self.window.show();
		sdl2.ext.fill(self.surface, (255,255,255))
		self.window.refresh()
		self.vram = []
		self.tilemap = []
		
		self.pixmap = sdl2.ext.PixelView(self.tiles_bank1)

		self.memory = gb_memory
		self.stopped = False


	def is_stopped(self):
		return self.stopped

	def show(self):
		self.window.refresh()

	def update_vram(self, vram):
		pass

	def update_tilemap(self, tilemap):
		pass

	def draw_map(self):

		for j in range(32):
			for i in range(32):
				#tile = self.tilemap[i+32*j]
				tile = self.memory[0x9800 + i+32*j]
				pos_x = (tile % 16) * 8
				pos_y = (tile >> 4) * 8

				src_rect = sdl2.SDL_Rect(pos_x, pos_y, 8, 8)
				dst_rect = sdl2.SDL_Rect(i*8, j*8, 8, 8)

				sdl2.SDL_BlitSurface(self.tiles_bank1, src_rect, self.surface, dst_rect)

	def draw_sprites(self):
		for i in range(40):
			sprite_pos_y = self.memory[0xFE00 + i*4] - 16
			sprite_pos_x = self.memory[0xFE00 + i*4 + 1] - 8
			sprite_pattern = self.memory[0xFE00 + i*4 + 2]
			sprite_flags = self.memory[0xFE00 + i*4 + 3]
			
			pattern_pos_x = (sprite_pattern % 16) * 8
			pattern_pos_y = (sprite_pattern >> 4) * 8

			if sprite_pos_y != -16 and sprite_pos_x != -8:
				logging.info("pos_x=%X pos_y=%X, pattern=%X, flags=%X", sprite_pos_x, sprite_pos_y, sprite_pattern, sprite_flags)
				src_rect = sdl2.SDL_Rect(pattern_pos_x, pattern_pos_y, 8, 8)
				dst_rect = sdl2.SDL_Rect(sprite_pos_x, sprite_pos_y, 8, 8)
				sdl2.SDL_BlitSurface(self.tiles_bank1, src_rect, self.surface, dst_rect)

	def draw_tiles(self):
		if self.memory.tiles_changes == True:
			self.memory.tiles_changes = False

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


						# self.set_pixel(pixmap, , , )
						self.pixmap[y_pos + j][x_pos + i] = colour_list[pix_colour]

				x_pos = x_pos + 8
				if x_pos == 128:
					x_pos = 0
					y_pos = y_pos + 8

	#		del pixmap
	
	def run(self):
		running = True
		while running:
			events = sdl2.ext.get_events()
			for event in events:
				if event.type == sdl2.SDL_QUIT or (event.type == sdl2.SDL_KEYDOWN and event.key.keysym.sym == sdl2.SDLK_ESCAPE):
					running = False
					self.stopped = True
					break
			
			self.draw_tiles()
			self.draw_map()
			self.draw_sprites()
			self.show()
			time.sleep(0.2)

def main():
	GBscreen = screen()
	GBscreen.start()

if __name__ == '__main__':
    main()
