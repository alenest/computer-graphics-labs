import pygame
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *
from PIL import Image

class GraphicsEditor:
    def __init__(self):
        self.width, self.height = 1200, 800
        self.background_color = [0.0, 0.0, 0.0, 1.0]
        self.object_color = [1.0, 1.0, 1.0, 1.0]
        self.line_width = 1.0
        self.drawing_mode = None
        self.points = []
        self.scale = 1.0
        self.cone_rotation = [0, 0, 0]
        self.render_mode = GL_FILL
        self.light_enabled = False
        self.texture_id = None
        self.camera_distance = -5
        self.camera_rotation_x = 0
        self.camera_rotation_y = 0
        self.last_mouse_pos = None
        self.is_rotating = False
        
        # Инициализация интерфейса
        pygame.init()
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.DOUBLEBUF | pygame.OPENGL)
        pygame.display.set_caption("3D Graphics Editor")
        
        # Шрифт для текста (поддерживающий кириллицу)
        self.font = pygame.font.SysFont('Arial', 14)
        
        # Настройка OpenGL
        glEnable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION)
        gluPerspective(45, self.width/self.height, 0.1, 50.0)
        glMatrixMode(GL_MODELVIEW)
        
        self.create_texture()
        self.setup_ui()
        self.setup_lighting()

    def setup_lighting(self):
        """Настройка освещения"""
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_POSITION, [2.0, 2.0, 2.0, 1.0])
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.8, 0.8, 0.8, 1.0])
        glLightfv(GL_LIGHT0, GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT, GL_AMBIENT_AND_DIFFUSE)

    def create_texture(self):
        """Создание пользовательской текстуры"""
        width, height = 256, 256
        texture_data = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Создание шахматной текстуры
        for y in range(height):
            for x in range(width):
                if (x // 32 + y // 32) % 2 == 0:
                    texture_data[y, x] = [255, 0, 0]  # Красный
                else:
                    texture_data[y, x] = [255, 255, 0]  # Желтый
        
        self.texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, texture_data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    def setup_ui(self):
        """Создание элементов интерфейса"""
        self.buttons = [
            {"rect": pygame.Rect(10, 10, 180, 30), "text": "Цвет фона", "action": "bg_color"},
            {"rect": pygame.Rect(10, 50, 180, 30), "text": "Цвет объектов", "action": "obj_color"},
            {"rect": pygame.Rect(10, 90, 180, 30), "text": "Толщина линии +", "action": "line_width_up"},
            {"rect": pygame.Rect(10, 130, 180, 30), "text": "Толщина линии -", "action": "line_width_down"},
            {"rect": pygame.Rect(10, 170, 180, 30), "text": "Рисовать линию", "action": "draw_line"},
            {"rect": pygame.Rect(10, 210, 180, 30), "text": "Рисовать треугольник", "action": "draw_triangle"},
            {"rect": pygame.Rect(10, 250, 180, 30), "text": "Рисовать прямоугольник", "action": "draw_rect"},
            {"rect": pygame.Rect(10, 290, 180, 30), "text": "Рисовать полигон", "action": "draw_polygon"},
            {"rect": pygame.Rect(10, 330, 180, 30), "text": "Приблизить", "action": "zoom_in"},
            {"rect": pygame.Rect(10, 370, 180, 30), "text": "Отдалить", "action": "zoom_out"},
            {"rect": pygame.Rect(10, 410, 180, 30), "text": "Режим точек", "action": "render_points"},
            {"rect": pygame.Rect(10, 450, 180, 30), "text": "Режим каркаса", "action": "render_wire"},
            {"rect": pygame.Rect(10, 490, 180, 30), "text": "Режим заливки", "action": "render_solid"},
            {"rect": pygame.Rect(10, 530, 180, 30), "text": "Вкл/Выкл свет", "action": "toggle_light"},
            {"rect": pygame.Rect(10, 570, 180, 30), "text": "Вращать конус", "action": "rotate_cone"},
            {"rect": pygame.Rect(10, 610, 180, 30), "text": "Очистить точки", "action": "clear_points"}
        ]

    def handle_events(self):
        """Обработка событий"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Левая кнопка мыши
                    self.handle_click(event.pos)
                    # Начало вращения камеры
                    if not any(button["rect"].collidepoint(event.pos) for button in self.buttons):
                        self.is_rotating = True
                        self.last_mouse_pos = event.pos
                elif event.button == 4:  # Колесо мыши вверх
                    self.camera_distance = min(-1, self.camera_distance + 0.5)
                elif event.button == 5:  # Колесо мыши вниз
                    self.camera_distance = max(-20, self.camera_distance - 0.5)
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:  # Левая кнопка мыши
                    self.is_rotating = False
            elif event.type == pygame.MOUSEMOTION:
                if self.is_rotating and self.last_mouse_pos:
                    # Вращение камеры
                    dx = event.pos[0] - self.last_mouse_pos[0]
                    dy = event.pos[1] - self.last_mouse_pos[1]
                    self.camera_rotation_y += dx * 0.5
                    self.camera_rotation_x += dy * 0.5
                    self.last_mouse_pos = event.pos
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.cone_rotation = [0, 0, 0]  # Сброс вращения
                elif event.key == pygame.K_l:
                    self.light_enabled = not self.light_enabled
                elif event.key == pygame.K_c:
                    self.points = []  # Очистка точек
                elif event.key == pygame.K_SPACE:
                    # Сброс камеры
                    self.camera_rotation_x = 0
                    self.camera_rotation_y = 0
                    self.camera_distance = -5
        return True

    def handle_click(self, pos):
        """Обработка кликов по интерфейсу"""
        for button in self.buttons:
            if button["rect"].collidepoint(pos):
                self.execute_action(button["action"])
                return
        
        # Если клик не по кнопке, добавляем точку для рисования
        if self.drawing_mode and self.drawing_mode.startswith("draw_"):
            # Преобразование координат экрана в координаты OpenGL
            x = (pos[0] - self.width / 2) / (self.width / 2) * 3
            y = -(pos[1] - self.height / 2) / (self.height / 2) * 2
            self.points.append((x, y))
            print(f"Добавлена точка: ({x:.2f}, {y:.2f}), всего точек: {len(self.points)}")

    def execute_action(self, action):
        """Выполнение действий интерфейса"""
        if action == "bg_color":
            self.background_color = np.random.rand(3).tolist() + [1.0]
            print("Изменен цвет фона")
        elif action == "obj_color":
            self.object_color = np.random.rand(3).tolist() + [1.0]
            print("Изменен цвет объектов")
        elif action == "line_width_up":
            self.line_width = min(10.0, self.line_width + 0.5)
            print(f"Толщина линии: {self.line_width}")
        elif action == "line_width_down":
            self.line_width = max(0.5, self.line_width - 0.5)
            print(f"Толщина линии: {self.line_width}")
        elif action.startswith("draw_"):
            self.drawing_mode = action
            self.points = []
            print(f"Режим рисования: {action}, кликните на экране для добавления точек")
        elif action == "zoom_in":
            self.camera_distance = min(-1, self.camera_distance + 0.5)
            print(f"Масштаб: {self.camera_distance}")
        elif action == "zoom_out":
            self.camera_distance = max(-20, self.camera_distance - 0.5)
            print(f"Масштаб: {self.camera_distance}")
        elif action == "render_points":
            self.render_mode = GL_POINT
            print("Режим отрисовки: Точки")
        elif action == "render_wire":
            self.render_mode = GL_LINE
            print("Режим отрисовки: Каркас")
        elif action == "render_solid":
            self.render_mode = GL_FILL
            print("Режим отрисовки: Заливка")
        elif action == "toggle_light":
            self.light_enabled = not self.light_enabled
            print(f"Освещение: {'ВКЛ' if self.light_enabled else 'ВЫКЛ'}")
        elif action == "rotate_cone":
            self.cone_rotation[1] += 15  # Вращение вокруг оси Y
            print(f"Вращение конуса: {self.cone_rotation}")
        elif action == "clear_points":
            self.points = []
            print("Очищены все точки")

    def setup_camera(self):
        """Настройка камеры с вращением"""
        glLoadIdentity()
        glTranslatef(0, 0, self.camera_distance)
        glRotatef(self.camera_rotation_x, 1, 0, 0)
        glRotatef(self.camera_rotation_y, 0, 1, 0)

    def draw_cone(self):
        """Рисование конуса с текстурой и освещением"""
        glPushMatrix()
        glTranslatef(0, 0, -2)
        glRotatef(self.cone_rotation[0], 1, 0, 0)
        glRotatef(self.cone_rotation[1], 0, 1, 0)
        glRotatef(self.cone_rotation[2], 0, 0, 1)
        
        if self.light_enabled:
            glEnable(GL_LIGHTING)
        else:
            glDisable(GL_LIGHTING)
        
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        
        glPolygonMode(GL_FRONT_AND_BACK, self.render_mode)
        glColor4f(*self.object_color)
        
        # Рисуем конус
        quadric = gluNewQuadric()
        gluQuadricTexture(quadric, GL_TRUE)
        gluCylinder(quadric, 1, 0, 2, 32, 32)  # Конус = цилиндр с верхним радиусом 0
        gluDeleteQuadric(quadric)
        
        glDisable(GL_TEXTURE_2D)
        glPopMatrix()

    def draw_primitive(self):
        """Рисование выбранного примитива"""
        if len(self.points) < 2:
            return
            
        glColor4f(*self.object_color)
        glLineWidth(self.line_width)
        glDisable(GL_LIGHTING)  # Отключаем освещение для 2D примитивов
        
        if self.drawing_mode == "draw_line" and len(self.points) >= 2:
            glBegin(GL_LINES)
            for i in range(0, len(self.points), 2):
                if i+1 < len(self.points):
                    x1, y1 = self.points[i]
                    x2, y2 = self.points[i+1]
                    glVertex3f(x1, y1, 0)
                    glVertex3f(x2, y2, 0)
            glEnd()
            
        elif self.drawing_mode == "draw_triangle" and len(self.points) >= 3:
            glBegin(GL_TRIANGLES)
            for i in range(0, len(self.points), 3):
                if i+2 < len(self.points):
                    for j in range(3):
                        x, y = self.points[i+j]
                        glVertex3f(x, y, 0)
            glEnd()
            
        elif self.drawing_mode == "draw_rect" and len(self.points) >= 2:
            for i in range(0, len(self.points), 2):
                if i+1 < len(self.points):
                    x1, y1 = self.points[i]
                    x2, y2 = self.points[i+1]
                    glBegin(GL_QUADS)
                    glVertex3f(x1, y1, 0)
                    glVertex3f(x2, y1, 0)
                    glVertex3f(x2, y2, 0)
                    glVertex3f(x1, y2, 0)
                    glEnd()
            
        elif self.drawing_mode == "draw_polygon" and len(self.points) > 2:
            glBegin(GL_POLYGON)
            for x, y in self.points:
                glVertex3f(x, y, 0)
            glEnd()
        
        # Рисуем точки для визуализации
        glPointSize(5.0)
        glBegin(GL_POINTS)
        glColor3f(1.0, 0.0, 0.0)  # Красные точки
        for x, y in self.points:
            glVertex3f(x, y, 0)
        glEnd()
        
        if self.light_enabled:
            glEnable(GL_LIGHTING)

    def draw_ui(self):
        """Отрисовка интерфейса с помощью PyGame"""
        # Переключаемся на 2D режим для отрисовки UI
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        
        # Отрисовка кнопок
        for button in self.buttons:
            # Рисуем прямоугольник кнопки
            glColor3f(0.8, 0.8, 0.8)
            glBegin(GL_QUADS)
            glVertex2f(button["rect"].left, button["rect"].top)
            glVertex2f(button["rect"].right, button["rect"].top)
            glVertex2f(button["rect"].right, button["rect"].bottom)
            glVertex2f(button["rect"].left, button["rect"].bottom)
            glEnd()
            
            # Рамка кнопки
            glColor3f(0.3, 0.3, 0.3)
            glLineWidth(2.0)
            glBegin(GL_LINE_LOOP)
            glVertex2f(button["rect"].left, button["rect"].top)
            glVertex2f(button["rect"].right, button["rect"].top)
            glVertex2f(button["rect"].right, button["rect"].bottom)
            glVertex2f(button["rect"].left, button["rect"].bottom)
            glEnd()
        
        # Возвращаемся к 3D режиму
        glEnable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        
        # Отрисовка текста с помощью PyGame (поверх OpenGL)
        self.draw_text_with_pygame()

    def draw_text_with_pygame(self):
        """Отрисовка текста интерфейса с помощью PyGame"""
        # Создаем поверхность для текста
        text_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        text_surface.fill((0, 0, 0, 0))  # Прозрачный фон
        
        # Отрисовка текста кнопок
        for button in self.buttons:
            text = self.font.render(button["text"], True, (0, 0, 0))
            text_rect = text.get_rect(center=button["rect"].center)
            text_surface.blit(text, text_rect)
        
        # Отображаем информацию о состоянии
        status_text = [
            f"Рисование: {self.drawing_mode}",
            f"Точек: {len(self.points)}",
            f"Свет: {'ВКЛ' if self.light_enabled else 'ВЫКЛ'}",
            f"Вращение: {self.camera_rotation_y:.1f}°",
            f"Масштаб: {self.camera_distance:.1f}"
        ]
        
        for i, text in enumerate(status_text):
            text_surf = self.font.render(text, True, (255, 255, 255))
            text_surface.blit(text_surf, (self.width - 200, 20 + i * 25))
        
        # Инструкции по управлению
        instructions = [
            "Управление камерой:",
            "ЛКМ + движение - вращение",
            "Колесико - приближение/отдаление",
            "Пробел - сброс камеры",
            "R - сброс вращения конуса",
            "L - переключение света",
            "C - очистка точек"
        ]
        
        for i, text in enumerate(instructions):
            text_surf = self.font.render(text, True, (200, 200, 255))
            text_surface.blit(text_surf, (10, self.height - 150 + i * 20))
        
        # Конвертируем поверхность PyGame в текстуру OpenGL
        # Переворачиваем поверхность, чтобы исправить перевернутый текст
        text_surface = pygame.transform.flip(text_surface, False, True)
        
        texture_data = pygame.image.tostring(text_surface, "RGBA", True)
        glEnable(GL_TEXTURE_2D)
        text_texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, text_texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.width, self.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, texture_data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        
        # Рисуем текстуру поверх всего
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        glColor4f(1, 1, 1, 1)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(0, 0)
        glTexCoord2f(1, 0); glVertex2f(self.width, 0)
        glTexCoord2f(1, 1); glVertex2f(self.width, self.height)
        glTexCoord2f(0, 1); glVertex2f(0, self.height)
        glEnd()
        
        glDisable(GL_BLEND)
        glEnable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        glDisable(GL_TEXTURE_2D)
        glDeleteTextures([text_texture])

    def run(self):
        """Основной цикл программы"""
        clock = pygame.time.Clock()
        running = True
        
        print("3D Graphics Editor Started!")
        print("Controls:")
        print("- Click buttons on the left for actions")
        print("- Click on screen to add points for drawing")
        print("- Left mouse button + drag: Rotate camera")
        print("- Mouse wheel: Zoom in/out")
        print("- Space: Reset camera")
        print("- R key: Reset cone rotation")
        print("- L key: Toggle lighting")
        print("- C key: Clear points")
        
        while running:
            running = self.handle_events()
            
            # Очистка экрана
            glClearColor(*self.background_color)
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            
            # Настройка камеры
            self.setup_camera()
            
            # Отрисовка объектов
            self.draw_cone()
            self.draw_primitive()
            self.draw_ui()
            
            pygame.display.flip()
            clock.tick(60)

if __name__ == "__main__":
    editor = GraphicsEditor()
    editor.run()