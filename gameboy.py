import processor
import screen


def main():

	file = open('/home/werner/projets/test_1/Tetris.gb', 'r')
	tetris = file.read()

	gb_memory = processor.memory(0xFFFF, tetris)
	
	gb_screen = screen.screen(gb_memory)
	gb_processor = processor.processor(tetris, gb_screen, gb_memory)
	
	gb_screen.start()
	gb_processor.power_on()

if __name__ == '__main__':
    main()
