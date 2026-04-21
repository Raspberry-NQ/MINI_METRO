import pygame

pygame.init()

pygame.font.get_fonts()

# 设置窗口
screen = pygame.display.set_mode((400, 300))
pygame.display.set_caption("中文测试")

font = pygame.font.SysFont('songti', 36)

text_surface = font.render('你好，Pygame!', True, (255, 255, 255))

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill((0, 0, 0))
    screen.blit(text_surface, (50, 100))
    pygame.display.flip()

pygame.quit()
