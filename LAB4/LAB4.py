import pygame
from OpenGL.GL import *
from OpenGL.GLU import *

pygame.init()
screen = pygame.display.set_mode((800, 600), pygame.DOUBLEBUF | pygame.OPENGL)

gluPerspective(45, 800/600, 0.1, 50.0)
glClearColor(0.0, 0.0, 0.0, 1.0)

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    pygame.display.flip()

pygame.quit()
print("OpenGL работает корректно!")