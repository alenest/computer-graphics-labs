import pygame
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *
from PIL import Image

class GraphicsEditor:
    def __init__(self):
        self.width, self.height = 1200, 800
        self.background_color = [0.0, 0.0, 0.0, 1.0]
        self.cone_color = [1.0, 1.0, 1.0, 1.0]  # Отдельный цвет для конуса
        self.current_primitive_color = [1.0, 1.0, 1.0, 1.0]  # Текущий цвет для новых примитивов
        self.line_width = 2.0
        self.line_style = 0xFFFF  # Сплошная линия по умолчанию
        self.line_stipple_factor = 1
        self.drawing_mode = None
        self.primitives = []  # Список всех примитивов
        self.light_sources = []  # Список источников света
        self.scale = 1.0
        self.cone_rotation = [0, 0, 0]
        self.render_modes = [GL_FILL, GL_LINE, GL_POINT]
        self.current_render_mode = 0  # Индекс текущего режима
        self.light_enabled = False
        self.texture_id = None
        self.camera_distance = -5
        self.camera_rotation_x = 0
        self.camera_rotation_y = 0
        self.last_mouse_pos = None
        self.is_rotating = False
        
        # Переменные для ввода координат
        self.input_active = False
        self.input_text = ""
        self.input_prompt = ""
        self.input_type = None  # 'primitive' или 'light'
        self.input_coords = []
        
        # Переменные для выбора цвета
        self.color_picker_active = False
        self.color_picker_type = None  # 'background', 'cone', 'primitive'
        
        # Инициализация интерфейса
        pygame.init()
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.DOUBLEBUF | pygame.OPENGL)
        pygame.display.set_caption("3D Graphics Editor")
        
        # Шрифт для текста (поддерживающий кириллицу)
        self.font = pygame.font.SysFont('Arial', 14)
        self.input_font = pygame.font.SysFont('Arial', 16)
        
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
        
        # Базовый источник света
        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_POSITION, [2.0, 2.0, 2.0, 1.0])
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.8, 0.8, 0.8, 1.0])
        glLightfv(GL_LIGHT0, GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])
        
        # Дополнительные источники света
        light_ids = [GL_LIGHT1, GL_LIGHT2, GL_LIGHT3, GL_LIGHT4, GL_LIGHT5, GL_LIGHT6, GL_LIGHT7]
        for i, light_pos in enumerate(self.light_sources):
            if i < len(light_ids):
                glEnable(light_ids[i])
                glLightfv(light_ids[i], GL_POSITION, light_pos + [1.0])
                glLightfv(light_ids[i], GL_AMBIENT, [0.1, 0.1, 0.1, 1.0])
                glLightfv(light_ids[i], GL_DIFFUSE, [0.7, 0.7, 0.7, 1.0])
                glLightfv(light_ids[i], GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])
        
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
            {"rect": pygame.Rect(10, 50, 180, 30), "text": "Цвет конуса", "action": "cone_color"},
            {"rect": pygame.Rect(10, 90, 180, 30), "text": "Цвет фигур", "action": "primitive_color"},
            {"rect": pygame.Rect(10, 130, 180, 30), "text": "Толщина линии +", "action": "line_width_up"},
            {"rect": pygame.Rect(10, 170, 180, 30), "text": "Толщина линии -", "action": "line_width_down"},
            {"rect": pygame.Rect(10, 210, 180, 30), "text": "Ввести координаты линии", "action": "input_line"},
            {"rect": pygame.Rect(10, 250, 180, 30), "text": "Ввести координаты треугольника", "action": "input_triangle"},
            {"rect": pygame.Rect(10, 290, 180, 30), "text": "Ввести координаты прямоугольника", "action": "input_rect"},
            {"rect": pygame.Rect(10, 330, 180, 30), "text": "Ввести координаты полигона", "action": "input_polygon"},
            {"rect": pygame.Rect(10, 370, 180, 30), "text": "Приблизить", "action": "zoom_in"},
            {"rect": pygame.Rect(10, 410, 180, 30), "text": "Отдалить", "action": "zoom_out"},
            {"rect": pygame.Rect(10, 450, 180, 30), "text": "Сменить режим отрисовки", "action": "change_render_mode"},
            {"rect": pygame.Rect(10, 490, 180, 30), "text": "Сплошная линия", "action": "solid_line"},
            {"rect": pygame.Rect(10, 530, 180, 30), "text": "Пунктирная линия", "action": "dashed_line"},
            {"rect": pygame.Rect(10, 570, 180, 30), "text": "Точечная линия", "action": "dotted_line"},
            {"rect": pygame.Rect(10, 610, 180, 30), "text": "Вкл/Выкл свет", "action": "toggle_light"},
            {"rect": pygame.Rect(10, 650, 180, 30), "text": "Добавить источник света", "action": "add_light"},
            {"rect": pygame.Rect(10, 690, 180, 30), "text": "Вращать конус", "action": "rotate_cone"},
            {"rect": pygame.Rect(10, 730, 180, 30), "text": "Очистить объекты", "action": "clear_objects"}
        ]

    def handle_events(self):
        """Обработка событий"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Левая кнопка мыши
                    if self.color_picker_active:
                        self.handle_color_picker_click(event.pos)
                    else:
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
                if self.input_active:
                    if event.key == pygame.K_RETURN:
                        self.process_input()
                    elif event.key == pygame.K_ESCAPE:
                        self.input_active = False
                        self.input_text = ""
                    elif event.key == pygame.K_BACKSPACE:
                        self.input_text = self.input_text[:-1]
                    else:
                        self.input_text += event.unicode
                else:
                    if event.key == pygame.K_r:
                        self.cone_rotation = [0, 0, 0]  # Сброс вращения
                    elif event.key == pygame.K_l:
                        self.light_enabled = not self.light_enabled
                    elif event.key == pygame.K_c:
                        self.clear_objects()
                    elif event.key == pygame.K_SPACE:
                        # Сброс камеры
                        self.camera_rotation_x = 0
                        self.camera_rotation_y = 0
                        self.camera_distance = -5
                    elif event.key == pygame.K_m:
                        self.change_render_mode()  # Смена режима отрисовки по клавише M
        return True

    def handle_click(self, pos):
        """Обработка кликов по интерфейсу"""
        for button in self.buttons:
            if button["rect"].collidepoint(pos):
                self.execute_action(button["action"])
                return

    def handle_color_picker_click(self, pos):
        """Обработка кликов в палитре цветов"""
        # Проверяем, был ли клик в области палитры
        palette_rect = pygame.Rect(self.width // 2 - 150, self.height // 2 - 150, 300, 300)
        if palette_rect.collidepoint(pos):
            # Получаем цвет из позиции клика
            x, y = pos
            rel_x = x - palette_rect.left
            rel_y = y - palette_rect.top
            
            # Вычисляем цвет на основе позиции в палитре
            hue = rel_x / palette_rect.width
            saturation = 1.0
            value = 1.0 - (rel_y / palette_rect.height)
            
            # Преобразуем HSV в RGB
            color = self.hsv_to_rgb(hue, saturation, value)
            
            # Применяем выбранный цвет
            if self.color_picker_type == 'background':
                self.background_color = color + [1.0]
                print(f"Цвет фона изменен на {color}")
            elif self.color_picker_type == 'cone':
                self.cone_color = color + [1.0]
                print(f"Цвет конуса изменен на {color}")
            elif self.color_picker_type == 'primitive':
                self.current_primitive_color = color + [1.0]
                print(f"Цвет фигур изменен на {color}")
            
            # Закрываем палитру
            self.color_picker_active = False

    def hsv_to_rgb(self, h, s, v):
        """Преобразование HSV в RGB"""
        if s == 0.0:
            return [v, v, v]
        
        i = int(h * 6.0)
        f = (h * 6.0) - i
        p = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))
        
        i = i % 6
        
        if i == 0:
            return [v, t, p]
        elif i == 1:
            return [q, v, p]
        elif i == 2:
            return [p, v, t]
        elif i == 3:
            return [p, q, v]
        elif i == 4:
            return [t, p, v]
        else:  # i == 5
            return [v, p, q]

    def execute_action(self, action):
        """Выполнение действий интерфейса"""
        if action == "bg_color":
            self.color_picker_active = True
            self.color_picker_type = 'background'
            print("Выберите цвет фона из палитры")
        elif action == "cone_color":
            self.color_picker_active = True
            self.color_picker_type = 'cone'
            print("Выберите цвет конуса из палитры")
        elif action == "primitive_color":
            self.color_picker_active = True
            self.color_picker_type = 'primitive'
            print("Выберите цвет фигур из палитры")
        elif action == "line_width_up":
            self.line_width = min(10.0, self.line_width + 0.5)
            print(f"Толщина линии: {self.line_width}")
        elif action == "line_width_down":
            self.line_width = max(0.5, self.line_width - 0.5)
            print(f"Толщина линии: {self.line_width}")
        elif action == "input_line":
            self.start_input("Введите координаты линии (x1,y1,z1,x2,y2,z2):", "line")
        elif action == "input_triangle":
            self.start_input("Введите координаты треугольника (x1,y1,z1,x2,y2,z2,x3,y3,z3):", "triangle")
        elif action == "input_rect":
            self.start_input("Введите координаты прямоугольника (x1,y1,z1,x2,y2,z2):", "rectangle")
        elif action == "input_polygon":
            self.start_input("Введите координаты полигона (x1,y1,z1,x2,y2,z2,...):", "polygon")
        elif action == "zoom_in":
            self.camera_distance = min(-1, self.camera_distance + 0.5)
            print(f"Масштаб: {self.camera_distance}")
        elif action == "zoom_out":
            self.camera_distance = max(-20, self.camera_distance - 0.5)
            print(f"Масштаб: {self.camera_distance}")
        elif action == "change_render_mode":
            self.change_render_mode()
        elif action == "solid_line":
            self.line_style = 0xFFFF  # Сплошная линия
            self.line_stipple_factor = 1
            print("Тип линии: Сплошная")
        elif action == "dashed_line":
            self.line_style = 0xF0F0  # Пунктирная линия
            self.line_stipple_factor = 1
            print("Тип линии: Пунктирная")
        elif action == "dotted_line":
            self.line_style = 0xAAAA  # Точечная линия
            self.line_stipple_factor = 1
            print("Тип линии: Точечная")
        elif action == "toggle_light":
            self.light_enabled = not self.light_enabled
            print(f"Освещение: {'ВКЛ' if self.light_enabled else 'ВЫКЛ'}")
        elif action == "add_light":
            self.start_input("Введите координаты источника света (x,y,z):", "light")
        elif action == "rotate_cone":
            self.cone_rotation[1] += 15  # Вращение вокруг оси Y
            print(f"Вращение конуса: {self.cone_rotation}")
        elif action == "clear_objects":
            self.clear_objects()

    def start_input(self, prompt, input_type):
        """Начинает ввод координат"""
        self.input_active = True
        self.input_text = ""
        self.input_prompt = prompt
        self.input_type = input_type
        print(prompt)

    def process_input(self):
        """Обрабатывает введенные координаты"""
        try:
            coords = [float(x.strip()) for x in self.input_text.split(',')]
            
            if self.input_type == "line" and len(coords) == 6:
                self.primitives.append({
                    "type": "line", 
                    "coords": coords,
                    "color": self.current_primitive_color.copy()  # Сохраняем цвет при создании
                })
                print("Линия добавлена")
            elif self.input_type == "triangle" and len(coords) == 9:
                self.primitives.append({
                    "type": "triangle", 
                    "coords": coords,
                    "color": self.current_primitive_color.copy()  # Сохраняем цвет при создании
                })
                print("Треугольник добавлен")
            elif self.input_type == "rectangle" and len(coords) == 6:
                self.primitives.append({
                    "type": "rectangle", 
                    "coords": coords,
                    "color": self.current_primitive_color.copy()  # Сохраняем цвет при создании
                })
                print("Прямоугольник добавлен")
            elif self.input_type == "polygon" and len(coords) >= 9 and len(coords) % 3 == 0:
                self.primitives.append({
                    "type": "polygon", 
                    "coords": coords,
                    "color": self.current_primitive_color.copy()  # Сохраняем цвет при создании
                })
                print("Полигон добавлен")
            elif self.input_type == "light" and len(coords) == 3:
                self.light_sources.append(coords)
                self.setup_lighting()  # Обновляем освещение
                print(f"Источник света добавлен в позиции {coords}")
            else:
                print("Ошибка: неверное количество координат")
                return
                
            self.input_active = False
            self.input_text = ""
            
        except ValueError:
            print("Ошибка: неверный формат координат")

    def clear_objects(self):
        """Очищает все объекты, кроме конуса"""
        self.primitives = []
        self.light_sources = []
        self.setup_lighting()  # Обновляем освещение
        print("Все объекты очищены")

    def change_render_mode(self):
        """Циклическое переключение режимов отрисовки"""
        self.current_render_mode = (self.current_render_mode + 1) % len(self.render_modes)
        mode_names = ["Заливка", "Каркас", "Точки"]
        print(f"Режим отрисовки: {mode_names[self.current_render_mode]}")

    def setup_camera(self):
        """Настройка камеры с вращением"""
        glLoadIdentity()
        glTranslatef(0, 0, self.camera_distance)
        glRotatef(self.camera_rotation_x, 1, 0, 0)
        glRotatef(self.camera_rotation_y, 0, 1, 0)

    def apply_render_mode(self):
        """Применяет текущий режим отрисовки ко всем объектам"""
        # Устанавливаем режим отрисовки
        glPolygonMode(GL_FRONT_AND_BACK, self.render_modes[self.current_render_mode])
        
        # Устанавливаем толщину линии для каркасного режима
        if self.render_modes[self.current_render_mode] == GL_LINE:
            glLineWidth(self.line_width)
            # Устанавливаем тип линии
            if self.line_style != 0xFFFF:
                glEnable(GL_LINE_STIPPLE)
                glLineStipple(self.line_stipple_factor, self.line_style)
        
        # Устанавливаем размер точек для точечного режима
        if self.render_modes[self.current_render_mode] == GL_POINT:
            glPointSize(self.line_width)

    def draw_coordinate_system(self):
        """Рисование системы координат с подписями"""
        # Сохраняем состояние OpenGL
        glPushAttrib(GL_ALL_ATTRIB_BITS)
        glDisable(GL_LIGHTING)
        
        # Рисуем оси координат
        glLineWidth(3.0)
        
        # Ось X (красная)
        glColor3f(1.0, 0.0, 0.0)
        glBegin(GL_LINES)
        glVertex3f(-10.0, 0.0, 0.0)
        glVertex3f(10.0, 0.0, 0.0)
        glEnd()
        
        # Ось Y (зеленая)
        glColor3f(0.0, 1.0, 0.0)
        glBegin(GL_LINES)
        glVertex3f(0.0, -10.0, 0.0)
        glVertex3f(0.0, 10.0, 0.0)
        glEnd()
        
        # Ось Z (синяя)
        glColor3f(0.0, 0.0, 1.0)
        glBegin(GL_LINES)
        glVertex3f(0.0, 0.0, -10.0)
        glVertex3f(0.0, 0.0, 10.0)
        glEnd()
        
        # Рисуем метки на осях (точки)
        glPointSize(6.0)
        glBegin(GL_POINTS)
        
        # Метки на оси X
        for i in range(-10, 11, 2):
            if i != 0:
                glVertex3f(i, 0.0, 0.0)
        
        # Метки на оси Y
        for i in range(-10, 11, 2):
            if i != 0:
                glVertex3f(0.0, i, 0.0)
        
        # Метки на оси Z
        for i in range(-10, 11, 2):
            if i != 0:
                glVertex3f(0.0, 0.0, i)
        
        glEnd()
        
        # Восстанавливаем состояние OpenGL
        glPopAttrib()

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
        
        # Сохраняем текущий режим полигона
        glPushAttrib(GL_POLYGON_BIT)
        
        # Применяем текущий режим отрисовки
        self.apply_render_mode()
        
        # Используем цвет конуса
        glColor4f(*self.cone_color)
        
        # Рисуем конус
        quadric = gluNewQuadric()
        gluQuadricTexture(quadric, GL_TRUE)
        gluCylinder(quadric, 1, 0, 2, 32, 32)  # Конус = цилиндр с верхним радиусом 0
        gluDeleteQuadric(quadric)
        
        # Отключаем пунктир, если был включен
        if self.render_modes[self.current_render_mode] == GL_LINE and self.line_style != 0xFFFF:
            glDisable(GL_LINE_STIPPLE)
        
        # Восстанавливаем режим полигона
        glPopAttrib()
        
        glDisable(GL_TEXTURE_2D)
        glPopMatrix()

    def draw_primitives(self):
        """Рисование всех примитивов с учетом текущего режима отрисовки"""
        if not self.primitives:
            return
        
        # Сохраняем текущий режим полигона
        glPushAttrib(GL_POLYGON_BIT)
            
        glDisable(GL_LIGHTING)  # Отключаем освещение для примитивов
        
        # Применяем текущий режим отрисовки к примитивам
        self.apply_render_mode()
        
        # Рисуем все примитивы
        for primitive in self.primitives:
            coords = primitive["coords"]
            color = primitive["color"]  # Используем цвет, сохраненный в примитиве
            
            # Устанавливаем цвет примитива
            glColor4f(*color)
            
            if primitive["type"] == "line" and len(coords) == 6:
                glBegin(GL_LINES)
                glVertex3f(coords[0], coords[1], coords[2])
                glVertex3f(coords[3], coords[4], coords[5])
                glEnd()
                
            elif primitive["type"] == "triangle" and len(coords) == 9:
                glBegin(GL_TRIANGLES)
                glVertex3f(coords[0], coords[1], coords[2])
                glVertex3f(coords[3], coords[4], coords[5])
                glVertex3f(coords[6], coords[7], coords[8])
                glEnd()
                
            elif primitive["type"] == "rectangle" and len(coords) == 6:
                x1, y1, z1, x2, y2, z2 = coords
                glBegin(GL_QUADS)
                glVertex3f(x1, y1, z1)
                glVertex3f(x2, y1, z1)
                glVertex3f(x2, y2, z1)
                glVertex3f(x1, y2, z1)
                glEnd()
                
            elif primitive["type"] == "polygon" and len(coords) >= 9 and len(coords) % 3 == 0:
                glBegin(GL_POLYGON)
                for i in range(0, len(coords), 3):
                    glVertex3f(coords[i], coords[i+1], coords[i+2])
                glEnd()
        
        # Отключаем пунктир, если был включен
        if self.render_modes[self.current_render_mode] == GL_LINE and self.line_style != 0xFFFF:
            glDisable(GL_LINE_STIPPLE)
            
        if self.light_enabled:
            glEnable(GL_LIGHTING)
            
        # Восстанавливаем режим полигона
        glPopAttrib()

    def draw_light_sources(self):
        """Рисование источников света"""
        if not self.light_sources:
            return
            
        glDisable(GL_LIGHTING)
        glColor3f(1.0, 1.0, 0.0)  # Желтый цвет для источников света
        glPointSize(10.0)
        
        glBegin(GL_POINTS)
        for light_pos in self.light_sources:
            glVertex3f(light_pos[0], light_pos[1], light_pos[2])
        glEnd()
        
        if self.light_enabled:
            glEnable(GL_LIGHTING)

    def draw_color_picker(self):
        """Отрисовка палитры цветов"""
        # Создаем поверхность для палитры
        palette_surface = pygame.Surface((300, 300), pygame.SRCALPHA)
        
        # Рисуем палитру цветов (спектр HSV)
        for y in range(300):
            for x in range(300):
                hue = x / 300
                saturation = 1.0
                value = 1.0 - (y / 300)
                
                color = self.hsv_to_rgb(hue, saturation, value)
                color_int = [int(c * 255) for c in color]
                
                palette_surface.set_at((x, y), color_int)
        
        # Рамка палитры
        pygame.draw.rect(palette_surface, (255, 255, 255), (0, 0, 300, 300), 2)
        
        # Конвертируем поверхность в текстуру OpenGL
        palette_data = pygame.image.tostring(palette_surface, "RGBA", True)
        
        glEnable(GL_TEXTURE_2D)
        palette_texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, palette_texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 300, 300, 0, GL_RGBA, GL_UNSIGNED_BYTE, palette_data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        
        # Сохраняем атрибуты OpenGL
        glPushAttrib(GL_ALL_ATTRIB_BITS)
        
        # Рисуем палитру поверх всего
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
        
        # Фон для палитры
        glColor4f(0.2, 0.2, 0.2, 0.8)
        glBegin(GL_QUADS)
        glVertex2f(0, 0)
        glVertex2f(self.width, 0)
        glVertex2f(self.width, self.height)
        glVertex2f(0, self.height)
        glEnd()
        
        # Сама палитра
        glColor4f(1, 1, 1, 1)
        x_pos = self.width // 2 - 150
        y_pos = self.height // 2 - 150
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(x_pos, y_pos)
        glTexCoord2f(1, 0); glVertex2f(x_pos + 300, y_pos)
        glTexCoord2f(1, 1); glVertex2f(x_pos + 300, y_pos + 300)
        glTexCoord2f(0, 1); glVertex2f(x_pos, y_pos + 300)
        glEnd()
        
        # Подпись
        text_surface = pygame.Surface((300, 30), pygame.SRCALPHA)
        text_surface.fill((0, 0, 0, 0))
        
        if self.color_picker_type == 'background':
            text = self.font.render("Выберите цвет фона", True, (255, 255, 255))
        elif self.color_picker_type == 'cone':
            text = self.font.render("Выберите цвет конуса", True, (255, 255, 255))
        else:  # primitive
            text = self.font.render("Выберите цвет фигур", True, (255, 255, 255))
        
        text_rect = text.get_rect(center=(150, 15))
        text_surface.blit(text, text_rect)
        
        # Конвертируем текст в текстуру
        text_data = pygame.image.tostring(text_surface, "RGBA", True)
        glBindTexture(GL_TEXTURE_2D, palette_texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 300, 30, 0, GL_RGBA, GL_UNSIGNED_BYTE, text_data)
        
        # Рисуем текст
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(x_pos, y_pos + 310)
        glTexCoord2f(1, 0); glVertex2f(x_pos + 300, y_pos + 310)
        glTexCoord2f(1, 1); glVertex2f(x_pos + 300, y_pos + 340)
        glTexCoord2f(0, 1); glVertex2f(x_pos, y_pos + 340)
        glEnd()
        
        glDisable(GL_BLEND)
        glEnable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        glDisable(GL_TEXTURE_2D)
        glDeleteTextures([palette_texture])
        
        # Восстанавливаем атрибуты OpenGL
        glPopAttrib()

    def draw_ui(self):
        """Отрисовка интерфейса с помощью PyGame"""
        # Сохраняем все атрибуты OpenGL
        glPushAttrib(GL_ALL_ATTRIB_BITS)
        
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
        
        # Принудительно устанавливаем режим заливки для кнопок
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        
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
        
        # Восстанавливаем атрибуты OpenGL
        glPopAttrib()
        
        # Отрисовка текста с помощью PyGame (поверх OpenGL)
        self.draw_text_with_pygame()
        
        # Отрисовка палитры, если активна
        if self.color_picker_active:
            self.draw_color_picker()

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
        mode_names = ["Заливка", "Каркас", "Точки"]
        line_style_names = {0xFFFF: "Сплошная", 0xF0F0: "Пунктир", 0xAAAA: "Точечная"}
        
        status_text = [
            f"Режим: {mode_names[self.current_render_mode]}",
            f"Примитивов: {len(self.primitives)}",
            f"Источников света: {len(self.light_sources)}",
            f"Свет: {'ВКЛ' if self.light_enabled else 'ВЫКЛ'}",
            f"Толщина: {self.line_width}",
            f"Тип линии: {line_style_names.get(self.line_style, 'Сплошная')}"
        ]
        
        for i, text in enumerate(status_text):
            text_surf = self.font.render(text, True, (255, 255, 255))
            text_surface.blit(text_surf, (self.width - 200, 20 + i * 25))
        
        # Легенда системы координат
        legend_text = [
            "Система координат:",
            "X - Красная ось",
            "Y - Зеленая ось", 
            "Z - Синяя ось",
            "Метки: каждые 2 единицы"
        ]
        
        for i, text in enumerate(legend_text):
            color = (255, 255, 255) if i == 0 else (255, 0, 0) if i == 1 else (0, 255, 0) if i == 2 else (0, 0, 255) if i == 3 else (200, 200, 200)
            text_surf = self.font.render(text, True, color)
            text_surface.blit(text_surf, (self.width - 250, self.height - 150 + i * 20))
        
        # Инструкции по управлению
        instructions = [
            "Управление камерой:",
            "ЛКМ + движение - вращение",
            "Колесико - приближение/отдаление",
            "Пробел - сброс камеры",
            "R - сброс вращения конуса",
            "L - переключение света",
            "M - смена режима отрисовки",
            "C - очистка объектов"
        ]
        
        for i, text in enumerate(instructions):
            text_surf = self.font.render(text, True, (200, 200, 255))
            text_surface.blit(text_surf, (10, self.height - 180 + i * 20))
        
        # Отрисовка поля ввода, если активно
        if self.input_active:
            input_rect = pygame.Rect(200, self.height - 50, self.width - 400, 30)
            pygame.draw.rect(text_surface, (255, 255, 255), input_rect)
            pygame.draw.rect(text_surface, (0, 0, 0), input_rect, 2)
            
            prompt_text = self.input_font.render(self.input_prompt, True, (255, 255, 255))
            text_surface.blit(prompt_text, (10, self.height - 80))
            
            input_text = self.input_font.render(self.input_text, True, (0, 0, 0))
            text_surface.blit(input_text, (input_rect.x + 5, input_rect.y + 5))
        
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
        
        # Сохраняем атрибуты OpenGL
        glPushAttrib(GL_ALL_ATTRIB_BITS)
        
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
        
        # Восстанавливаем атрибуты OpenGL
        glPopAttrib()

    def run(self):
        """Основной цикл программы"""
        clock = pygame.time.Clock()
        running = True
        
        print("3D Graphics Editor Started!")
        print("Controls:")
        print("- Click buttons on the left for actions")
        print("- Left mouse button + drag: Rotate camera")
        print("- Mouse wheel: Zoom in/out")
        print("- Space: Reset camera")
        print("- R key: Reset cone rotation")
        print("- L key: Toggle lighting")
        print("- M key: Change render mode")
        print("- C key: Clear objects")
        
        while running:
            running = self.handle_events()
            
            # Очистка экрана
            glClearColor(*self.background_color)
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            
            # Настройка камеры
            self.setup_camera()
            
            # Отрисовка объектов
            self.draw_coordinate_system()
            self.draw_cone()
            self.draw_primitives()
            self.draw_light_sources()
            self.draw_ui()
            
            pygame.display.flip()
            clock.tick(60)

if __name__ == "__main__":
    editor = GraphicsEditor()
    editor.run()