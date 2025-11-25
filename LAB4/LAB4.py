import pygame
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *
from PIL import Image
import os

class GraphicsEditor:
    def __init__(self):
        # Увеличиваем ширину окна для размещения кнопок по бокам
        self.width, self.height = 1400, 800
        self.background_color = [0.0, 0.0, 0.0, 1.0]
        self.cone_color = [1.0, 1.0, 1.0, 1.0]
        self.cone_texture_mode = 'color'
        self.current_primitive_color = [1.0, 1.0, 1.0, 1.0]
        self.line_width = 2.0
        self.line_style = 0xFFFF
        self.line_stipple_factor = 1
        self.drawing_mode = None
        self.primitives = []
        self.light_sources = []
        self.scale = 1.0
        self.cone_rotation = [0, 0, 0]
        self.render_modes = [GL_FILL, GL_LINE, GL_POINT]
        self.current_render_mode = 0
        self.light_enabled = False
        self.texture_id = None
        self.custom_texture_id = None
        self.camera_distance = -5
        self.camera_rotation_x = 0
        self.camera_rotation_y = 0
        self.last_mouse_pos = None
        self.is_rotating = False
        
        # Переменные для ввода координат
        self.input_active = False
        self.input_text = ""
        self.input_prompt = ""
        self.input_type = None
        self.input_coords = []
        
        # Переменные для выбора цвета
        self.color_picker_active = False
        self.color_picker_type = None
        self.temp_selected_color = None
        self.pending_primitive_type = None
        
        # Кэшированные текстуры для оптимизации
        self.palette_texture = None
        
        # Текстуры для конуса
        self.cone_checker_texture_id = None
        self.checker_color1 = [1.0, 0.0, 0.0, 1.0]
        self.checker_color2 = [1.0, 1.0, 0.0, 1.0]
        
        # НАСТРОЙКИ ОСВЕЩЕНИЯ
        self.light_intensity = 1.0
        
        # НОВАЯ ПЕРЕМЕННАЯ: видимость информационных панелей
        self.info_panels_visible = True
        
        # Инициализация интерфейса
        pygame.init()
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.DOUBLEBUF | pygame.OPENGL)
        pygame.display.set_caption("3D Graphics Editor")
        
        # Шрифты
        self.font = pygame.font.SysFont('Arial', 14)
        self.input_font = pygame.font.SysFont('Arial', 16)
        self.title_font = pygame.font.SysFont('Arial', 16, bold=True)
        
        # Настройка OpenGL
        glEnable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION)
        gluPerspective(45, self.width/self.height, 0.1, 50.0)
        glMatrixMode(GL_MODELVIEW)
        
        self.create_texture()
        self.create_cone_checker_texture()
        self.setup_ui()
        self.setup_lighting()
        
        self.create_palette_texture()

    def create_palette_texture(self):
        """Создание текстуры палитры один раз для оптимизации"""
        palette_surface = pygame.Surface((300, 300), pygame.SRCALPHA)
        
        for y in range(300):
            for x in range(300):
                hue = x / 300
                saturation = 1.0
                value = 1.0 - (y / 300)
                
                color = self.hsv_to_rgb(hue, saturation, value)
                color_int = [int(c * 255) for c in color]
                
                palette_surface.set_at((x, y), color_int)
        
        pygame.draw.rect(palette_surface, (255, 255, 255), (0, 0, 300, 300), 2)
        
        palette_data = pygame.image.tostring(palette_surface, "RGBA", True)
        
        self.palette_texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.palette_texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 300, 300, 0, GL_RGBA, GL_UNSIGNED_BYTE, palette_data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    def setup_lighting(self):
        """Настройка освещения"""
        glEnable(GL_LIGHTING)
        
        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_POSITION, [2.0, 2.0, 2.0, 1.0])
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.2 * self.light_intensity, 0.2 * self.light_intensity, 0.2 * self.light_intensity, 1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.8 * self.light_intensity, 0.8 * self.light_intensity, 0.8 * self.light_intensity, 1.0])
        glLightfv(GL_LIGHT0, GL_SPECULAR, [1.0 * self.light_intensity, 1.0 * self.light_intensity, 1.0 * self.light_intensity, 1.0])
        
        light_ids = [GL_LIGHT1, GL_LIGHT2, GL_LIGHT3, GL_LIGHT4, GL_LIGHT5, GL_LIGHT6, GL_LIGHT7]
        for i, light_pos in enumerate(self.light_sources):
            if i < len(light_ids):
                glEnable(light_ids[i])
                glLightfv(light_ids[i], GL_POSITION, light_pos + [1.0])
                glLightfv(light_ids[i], GL_AMBIENT, [0.1 * self.light_intensity, 0.1 * self.light_intensity, 0.1 * self.light_intensity, 1.0])
                glLightfv(light_ids[i], GL_DIFFUSE, [0.7 * self.light_intensity, 0.7 * self.light_intensity, 0.7 * self.light_intensity, 1.0])
                glLightfv(light_ids[i], GL_SPECULAR, [1.0 * self.light_intensity, 1.0 * self.light_intensity, 1.0 * self.light_intensity, 1.0])
        
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT, GL_AMBIENT_AND_DIFFUSE)

    def create_texture(self):
        """Создание пользовательской текстуры"""
        width, height = 256, 256
        texture_data = np.zeros((height, width, 3), dtype=np.uint8)
        
        for y in range(height):
            for x in range(width):
                if (x // 32 + y // 32) % 2 == 0:
                    texture_data[y, x] = [255, 0, 0]
                else:
                    texture_data[y, x] = [255, 255, 0]
        
        self.texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, texture_data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    def create_cone_checker_texture(self):
        """Создание шахматной текстуры для конуса"""
        width, height = 256, 256
        texture_data = np.zeros((height, width, 3), dtype=np.uint8)
        
        for y in range(height):
            for x in range(width):
                if (x // 32 + y // 32) % 2 == 0:
                    texture_data[y, x] = [int(self.checker_color1[0] * 255), 
                                         int(self.checker_color1[1] * 255), 
                                         int(self.checker_color1[2] * 255)]
                else:
                    texture_data[y, x] = [int(self.checker_color2[0] * 255), 
                                         int(self.checker_color2[1] * 255), 
                                         int(self.checker_color2[2] * 255)]
        
        if self.cone_checker_texture_id is not None:
            glDeleteTextures([self.cone_checker_texture_id])
            
        self.cone_checker_texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.cone_checker_texture_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, texture_data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    def load_custom_texture(self, filename):
        """Загрузка текстуры из файла"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            filepath = os.path.join(current_dir, filename)
            
            if not os.path.exists(filepath):
                print(f"Файл {filename} не найден в директории программы")
                return False
            
            img = Image.open(filepath)
            
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            img = img.resize((256, 256), Image.Resampling.LANCZOS)
            
            img_data = np.array(img)
            
            if self.custom_texture_id is not None:
                glDeleteTextures([self.custom_texture_id])
                
            self.custom_texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.custom_texture_id)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, 256, 256, 0, GL_RGB, GL_UNSIGNED_BYTE, img_data)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            
            print(f"Текстура загружена из {filename}")
            return True
            
        except Exception as e:
            print(f"Ошибка загрузки текстуры: {e}")
            return False

    def setup_ui(self):
        """Создание элементов интерфейса - ПОЛНОСТЬЮ ПЕРЕРАБОТАНО"""
        button_width = 200
        button_height = 35
        button_margin = 8
        
        # Сдвигаем все элементы вниз, чтобы освободить место под заголовок окна
        vertical_offset = 40
        
        # Левая колонка кнопок
        left_x = 10
        left_y_start = 10 + vertical_offset
        
        # Правая колонка кнопок  
        right_x = self.width - button_width - 10
        right_y_start = 10 + vertical_offset
        
        # СЕКЦИЯ: Управление сценой (левая колонка)
        self.scene_buttons = [
            {"rect": pygame.Rect(left_x, left_y_start, button_width, button_height), "text": "Цвет фона", "action": "bg_color"},
            {"rect": pygame.Rect(left_x, left_y_start + button_height + button_margin, button_width, button_height), "text": "Приблизить", "action": "zoom_in"},
            {"rect": pygame.Rect(left_x, left_y_start + 2*(button_height + button_margin), button_width, button_height), "text": "Отдалить", "action": "zoom_out"},
            {"rect": pygame.Rect(left_x, left_y_start + 3*(button_height + button_margin), button_width, button_height), "text": "Сброс камеры", "action": "reset_camera"},
            {"rect": pygame.Rect(left_x, left_y_start + 4*(button_height + button_margin), button_width, button_height), "text": "Очистить объекты", "action": "clear_objects"},
        ]
        
        # СЕКЦИЯ: Примитивы (левая колонка, продолжение)
        primitives_y = left_y_start + 5*(button_height + button_margin) + 20
        self.primitives_buttons = [
            {"rect": pygame.Rect(left_x, primitives_y, button_width, button_height), "text": "Цвет фигур", "action": "primitive_color"},
            {"rect": pygame.Rect(left_x, primitives_y + button_height + button_margin, button_width, button_height), "text": "Ввести координаты линии", "action": "input_line"},
            {"rect": pygame.Rect(left_x, primitives_y + 2*(button_height + button_margin), button_width, button_height), "text": "Ввести координаты треугольника", "action": "input_triangle"},
            {"rect": pygame.Rect(left_x, primitives_y + 3*(button_height + button_margin), button_width, button_height), "text": "Ввести координаты прямоугольника", "action": "input_rect"},
            {"rect": pygame.Rect(left_x, primitives_y + 4*(button_height + button_margin), button_width, button_height), "text": "Ввести координаты многоугольника", "action": "input_polygon"},
        ]
        
        # СЕКЦИЯ: Настройки отрисовки (правая колонка)
        self.rendering_buttons = [
            {"rect": pygame.Rect(right_x, right_y_start, button_width, button_height), "text": "Толщина линии +", "action": "line_width_up"},
            {"rect": pygame.Rect(right_x, right_y_start + button_height + button_margin, button_width, button_height), "text": "Толщина линии -", "action": "line_width_down"},
            {"rect": pygame.Rect(right_x, right_y_start + 2*(button_height + button_margin), button_width, button_height), "text": "Сплошная линия", "action": "solid_line"},
            {"rect": pygame.Rect(right_x, right_y_start + 3*(button_height + button_margin), button_width, button_height), "text": "Пунктирная линия", "action": "dashed_line"},
            {"rect": pygame.Rect(right_x, right_y_start + 4*(button_height + button_margin), button_width, button_height), "text": "Точечная линия", "action": "dotted_line"},
            {"rect": pygame.Rect(right_x, right_y_start + 5*(button_height + button_margin), button_width, button_height), "text": "Сменить режим отрисовки", "action": "change_render_mode"},
        ]
        
        # СЕКЦИЯ: Конус и освещение (правая колонка, продолжение)
        cone_light_y = right_y_start + 6*(button_height + button_margin) + 20
        self.cone_light_buttons = [
            {"rect": pygame.Rect(right_x, cone_light_y, button_width, button_height), "text": "Цвет конуса", "action": "cone_color"},
            {"rect": pygame.Rect(right_x, cone_light_y + button_height + button_margin, button_width, button_height), "text": "Шахматная текстура", "action": "cone_checker_texture"},
            {"rect": pygame.Rect(right_x, cone_light_y + 2*(button_height + button_margin), button_width, button_height), "text": "Пользовательская текстура", "action": "cone_custom_texture"},
            {"rect": pygame.Rect(right_x, cone_light_y + 3*(button_height + button_margin), button_width, button_height), "text": "Загрузить текстуру", "action": "load_texture"},
            {"rect": pygame.Rect(right_x, cone_light_y + 4*(button_height + button_margin), button_width, button_height), "text": "Вращать конус", "action": "rotate_cone"},
            {"rect": pygame.Rect(right_x, cone_light_y + 5*(button_height + button_margin), button_width, button_height), "text": "Вкл/Выкл свет", "action": "toggle_light"},
            {"rect": pygame.Rect(right_x, cone_light_y + 6*(button_height + button_margin), button_width, button_height), "text": "Добавить источник света", "action": "add_light"},
            {"rect": pygame.Rect(right_x, cone_light_y + 7*(button_height + button_margin), button_width, button_height), "text": "Увеличить интенсивность", "action": "increase_light_intensity"},
            {"rect": pygame.Rect(right_x, cone_light_y + 8*(button_height + button_margin), button_width, button_height), "text": "Уменьшить интенсивность", "action": "decrease_light_intensity"},
        ]
        
        # Объединяем все кнопки
        self.all_buttons = (self.scene_buttons + self.primitives_buttons + 
                           self.rendering_buttons + self.cone_light_buttons)
        
        # Области для информационных панелей (теперь они располагаются справа от левых кнопок)
        panel_width = 350  # Увеличиваем ширину для лучшего отображения текста
        panel_x = left_x + button_width + 20  # Располагаем справа от левых кнопок
        
        self.info_panels = {
            "status": pygame.Rect(panel_x, 10 + vertical_offset, panel_width, 160),  # Увеличиваем высоту
            "coords": pygame.Rect(panel_x, 180 + vertical_offset, panel_width, 120),
            "controls": pygame.Rect(panel_x, 310 + vertical_offset, panel_width, 220)  # Увеличиваем высоту
        }

    def handle_events(self):
        """Обработка событий"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if self.color_picker_active:
                        self.handle_color_picker_click(event.pos)
                    else:
                        self.handle_click(event.pos)
                        if not any(button["rect"].collidepoint(event.pos) for button in self.all_buttons):
                            self.is_rotating = True
                            self.last_mouse_pos = event.pos
                elif event.button == 4:
                    self.camera_distance = min(-1, self.camera_distance + 0.5)
                elif event.button == 5:
                    self.camera_distance = max(-20, self.camera_distance - 0.5)
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.is_rotating = False
            elif event.type == pygame.MOUSEMOTION:
                if self.is_rotating and self.last_mouse_pos:
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
                        self.cone_rotation = [0, 0, 0]
                    elif event.key == pygame.K_l:
                        self.toggle_lighting()
                    elif event.key == pygame.K_c:
                        self.clear_objects()
                    elif event.key == pygame.K_SPACE:
                        self.camera_rotation_x = 0
                        self.camera_rotation_y = 0
                        self.camera_distance = -5
                    elif event.key == pygame.K_m:
                        self.change_render_mode()
                    elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                        self.increase_light_intensity()
                    elif event.key == pygame.K_MINUS:
                        self.decrease_light_intensity()
                    # НОВАЯ КЛАВИША: переключение видимости информационных панелей
                    elif event.key == pygame.K_i:
                        self.info_panels_visible = not self.info_panels_visible
                        print(f"Информационные панели: {'ВКЛ' if self.info_panels_visible else 'ВЫКЛ'}")
        return True

    def handle_click(self, pos):
        """Обработка кликов по интерфейсу"""
        for button in self.all_buttons:
            if button["rect"].collidepoint(pos):
                self.execute_action(button["action"])
                return

    def handle_color_picker_click(self, pos):
        """Обработка кликов в палитре цветов"""
        palette_rect = pygame.Rect(self.width // 2 - 150, self.height // 2 - 150, 300, 300)
        action_button_rect = pygame.Rect(self.width // 2 + 160, self.height // 2 - 150, 30, 30)
        
        if palette_rect.collidepoint(pos):
            x, y = pos
            rel_x = x - palette_rect.left
            rel_y = y - palette_rect.top
            
            hue = rel_x / palette_rect.width
            saturation = 1.0
            value = 1.0 - (rel_y / palette_rect.height)
            
            color = self.hsv_to_rgb(hue, saturation, value)
            self.temp_selected_color = color + [1.0]
            
            if self.color_picker_type in ['background', 'cone', 'primitive', 'cone_checker_color']:
                if self.color_picker_type == 'background':
                    self.background_color = self.temp_selected_color
                    print(f"Цвет фона изменен на {self.temp_selected_color}")
                elif self.color_picker_type == 'cone':
                    self.cone_color = self.temp_selected_color
                    self.cone_texture_mode = 'color'
                    print(f"Цвет конуса изменен на {self.temp_selected_color}")
                elif self.color_picker_type == 'cone_checker_color':
                    self.checker_color1 = self.temp_selected_color
                    self.checker_color2 = [1.0 - self.temp_selected_color[0], 
                                          1.0 - self.temp_selected_color[1], 
                                          1.0 - self.temp_selected_color[2], 
                                          1.0]
                    self.create_cone_checker_texture()
                    self.cone_texture_mode = 'checker'
                    print(f"Шахматная текстура конуса обновлена. Цвета: {self.checker_color1}, {self.checker_color2}")
                elif self.color_picker_type == 'primitive':
                    self.current_primitive_color = self.temp_selected_color
                    print(f"Цвет фигур изменен на {self.temp_selected_color}")
            
        elif action_button_rect.collidepoint(pos):
            if self.color_picker_type == 'input_color':
                if self.temp_selected_color is not None:
                    self.current_primitive_color = self.temp_selected_color.copy()
                    print(f"Цвет для {self.pending_primitive_type} установлен на {self.current_primitive_color}")
                
                self.color_picker_active = False
                self.start_input_for_primitive()
            else:
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
        else:
            return [v, p, q]

    def execute_action(self, action):
        """Выполнение действий интерфейса"""
        if action == "bg_color":
            self.color_picker_active = True
            self.color_picker_type = 'background'
            self.temp_selected_color = self.background_color.copy()
            print("Выберите цвет фона из палитры")
        elif action == "cone_color":
            self.color_picker_active = True
            self.color_picker_type = 'cone'
            self.temp_selected_color = self.cone_color.copy()
            print("Выберите цвет конуса из палитры")
        elif action == "cone_checker_texture":
            self.color_picker_active = True
            self.color_picker_type = 'cone_checker_color'
            self.temp_selected_color = self.checker_color1.copy()
            print("Выберите основной цвет для шахматной текстуры конуса")
        elif action == "cone_custom_texture":
            if self.custom_texture_id is not None:
                self.cone_texture_mode = 'custom'
                print("Режим текстуры конуса: пользовательская текстура")
            else:
                print("Сначала загрузите текстуру")
        elif action == "primitive_color":
            self.color_picker_active = True
            self.color_picker_type = 'primitive'
            self.temp_selected_color = self.current_primitive_color.copy()
            print("Выберите цвет фигур из палитры")
        elif action == "input_line":
            self.pending_primitive_type = "line"
            self.color_picker_active = True
            self.color_picker_type = 'input_color'
            self.temp_selected_color = self.current_primitive_color.copy()
            print("Выберите цвет для линии")
        elif action == "input_triangle":
            self.pending_primitive_type = "triangle"
            self.color_picker_active = True
            self.color_picker_type = 'input_color'
            self.temp_selected_color = self.current_primitive_color.copy()
            print("Выберите цвет для треугольника")
        elif action == "input_rect":
            self.pending_primitive_type = "rectangle"
            self.color_picker_active = True
            self.color_picker_type = 'input_color'
            self.temp_selected_color = self.current_primitive_color.copy()
            print("Выберите цвет для прямоугольника")
        elif action == "input_polygon":
            self.pending_primitive_type = "polygon"
            self.color_picker_active = True
            self.color_picker_type = 'input_color'
            self.temp_selected_color = self.current_primitive_color.copy()
            print("Выберите цвет для многоугольника")
        elif action == "line_width_up":
            self.line_width = min(10.0, self.line_width + 0.5)
            print(f"Толщина линии: {self.line_width}")
        elif action == "line_width_down":
            self.line_width = max(0.5, self.line_width - 0.5)
            print(f"Толщина линии: {self.line_width}")
        elif action == "zoom_in":
            self.camera_distance = min(-1, self.camera_distance + 0.5)
            print(f"Масштаб: {self.camera_distance}")
        elif action == "zoom_out":
            self.camera_distance = max(-20, self.camera_distance - 0.5)
            print(f"Масштаб: {self.camera_distance}")
        elif action == "reset_camera":
            self.camera_rotation_x = 0
            self.camera_rotation_y = 0
            self.camera_distance = -5
            print("Камера сброшена")
        elif action == "change_render_mode":
            self.change_render_mode()
        elif action == "solid_line":
            self.line_style = 0xFFFF
            self.line_stipple_factor = 1
            print("Тип линии: Сплошная")
        elif action == "dashed_line":
            self.line_style = 0xF0F0
            self.line_stipple_factor = 1
            print("Тип линии: Пунктирная")
        elif action == "dotted_line":
            self.line_style = 0xAAAA
            self.line_stipple_factor = 1
            print("Тип линии: Точечная")
        elif action == "toggle_light":
            self.toggle_lighting()
        elif action == "add_light":
            self.start_input("Введите координаты источника света (x,y,z):", "light")
        elif action == "rotate_cone":
            self.cone_rotation[1] += 15
            print(f"Вращение конуса: {self.cone_rotation}")
        elif action == "clear_objects":
            self.clear_objects()
        elif action == "load_texture":
            self.start_input("Введите имя файла текстуры (в папке с программой):", "texture")
        elif action == "increase_light_intensity":
            self.increase_light_intensity()
        elif action == "decrease_light_intensity":
            self.decrease_light_intensity()

    def toggle_lighting(self):
        """Включает/выключает освещение"""
        self.light_enabled = not self.light_enabled
        print(f"Освещение: {'ВКЛ' if self.light_enabled else 'ВЫКЛ'}")

    def increase_light_intensity(self):
        """Увеличивает интенсивность освещения"""
        self.light_intensity = min(10.0, self.light_intensity + 0.1)
        self.setup_lighting()
        print(f"Интенсивность освещения увеличена до: {self.light_intensity:.1f}")

    def decrease_light_intensity(self):
        """Уменьшает интенсивность освещения"""
        self.light_intensity = max(0.1, self.light_intensity - 0.1)
        self.setup_lighting()
        print(f"Интенсивность освещения уменьшена до: {self.light_intensity:.1f}")

    def start_input_for_primitive(self):
        """Запускает ввод координат для выбранного примитива"""
        prompts = {
            "line": "Введите координаты линии (x1,y1,z1,x2,y2,z2):",
            "triangle": "Введите координаты треугольника (x1,y1,z1,x2,y2,z2,x3,y3,z3):",
            "rectangle": "Введите координаты прямоугольника (x1,y1,z1,x2,y2,z2):",
            "polygon": "Введите координаты многоугольника (x1,y1,z1,x2,y2,z2,...):"
        }
        
        if self.pending_primitive_type in prompts:
            self.start_input(prompts[self.pending_primitive_type], self.pending_primitive_type)

    def start_input(self, prompt, input_type):
        """Начинает ввод координат"""
        self.input_active = True
        self.input_text = ""
        self.input_prompt = prompt
        self.input_type = input_type
        print(prompt)

    def process_input(self):
        """Обрабатывает введенные данные"""
        try:
            if self.input_type == "texture":
                filename = self.input_text.strip()
                if filename:
                    if self.load_custom_texture(filename):
                        print("Текстура успешно загружена")
                    else:
                        print("Ошибка загрузки текстуры")
                else:
                    print("Имя файла не может быть пустым")
                    
            else:
                coords = [float(x.strip()) for x in self.input_text.split(',')]
                
                if self.input_type == "line" and len(coords) == 6:
                    self.primitives.append({
                        "type": "line", 
                        "coords": coords,
                        "color": self.current_primitive_color.copy()
                    })
                    print("Линия добавлена")
                elif self.input_type == "triangle" and len(coords) == 9:
                    self.primitives.append({
                        "type": "triangle", 
                        "coords": coords,
                        "color": self.current_primitive_color.copy()
                    })
                    print("Треугольник добавлен")
                elif self.input_type == "rectangle" and len(coords) == 6:
                    self.primitives.append({
                        "type": "rectangle", 
                        "coords": coords,
                        "color": self.current_primitive_color.copy()
                    })
                    print("Прямоугольник добавлен")
                elif self.input_type == "polygon" and len(coords) >= 9 and len(coords) % 3 == 0:
                    self.primitives.append({
                        "type": "polygon", 
                        "coords": coords,
                        "color": self.current_primitive_color.copy()
                    })
                    print("Многоугольник добавлен")
                elif self.input_type == "light" and len(coords) == 3:
                    self.light_sources.append(coords)
                    self.setup_lighting()
                    print(f"Источник света добавлен в позиции {coords}")
                else:
                    print("Ошибка: неверное количество координат")
                    return
                
            self.input_active = False
            self.input_text = ""
            
        except ValueError:
            print("Ошибка: неверный формат данных")

    def clear_objects(self):
        """Очищает все объекты, кроме конуса"""
        self.primitives = []
        self.light_sources = []
        self.setup_lighting()
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
        glPolygonMode(GL_FRONT_AND_BACK, self.render_modes[self.current_render_mode])
        
        if self.render_modes[self.current_render_mode] == GL_LINE:
            glLineWidth(self.line_width)
            if self.line_style != 0xFFFF:
                glEnable(GL_LINE_STIPPLE)
                glLineStipple(self.line_stipple_factor, self.line_style)
        
        if self.render_modes[self.current_render_mode] == GL_POINT:
            glPointSize(self.line_width)

    def draw_coordinate_system(self):
        """Рисование системы координат с подписями"""
        glPushAttrib(GL_ALL_ATTRIB_BITS)
        glDisable(GL_LIGHTING)
        
        glLineWidth(3.0)
        
        glColor3f(1.0, 0.0, 0.0)
        glBegin(GL_LINES)
        glVertex3f(-10.0, 0.0, 0.0)
        glVertex3f(10.0, 0.0, 0.0)
        glEnd()
        
        glColor3f(0.0, 1.0, 0.0)
        glBegin(GL_LINES)
        glVertex3f(0.0, -10.0, 0.0)
        glVertex3f(0.0, 10.0, 0.0)
        glEnd()
        
        glColor3f(0.0, 0.0, 1.0)
        glBegin(GL_LINES)
        glVertex3f(0.0, 0.0, -10.0)
        glVertex3f(0.0, 0.0, 10.0)
        glEnd()
        
        glPointSize(6.0)
        glBegin(GL_POINTS)
        
        for i in range(-10, 11, 2):
            if i != 0:
                glVertex3f(i, 0.0, 0.0)
        
        for i in range(-10, 11, 2):
            if i != 0:
                glVertex3f(0.0, i, 0.0)
        
        for i in range(-10, 11, 2):
            if i != 0:
                glVertex3f(0.0, 0.0, i)
        
        glEnd()
        
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
        
        glPushAttrib(GL_POLYGON_BIT)
        
        self.apply_render_mode()
        
        if self.cone_texture_mode == 'color':
            glDisable(GL_TEXTURE_2D)
            glColor4f(*self.cone_color)
        elif self.cone_texture_mode == 'checker':
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, self.cone_checker_texture_id)
            glColor4f(1.0, 1.0, 1.0, 1.0)
        elif self.cone_texture_mode == 'custom':
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, self.custom_texture_id)
            glColor4f(1.0, 1.0, 1.0, 1.0)
        
        quadric = gluNewQuadric()
        gluQuadricTexture(quadric, GL_TRUE)
        gluCylinder(quadric, 1, 0, 2, 32, 32)
        gluDeleteQuadric(quadric)
        
        if self.render_modes[self.current_render_mode] == GL_LINE and self.line_style != 0xFFFF:
            glDisable(GL_LINE_STIPPLE)
        
        glPopAttrib()
        
        glDisable(GL_TEXTURE_2D)
        glPopMatrix()

    def draw_primitives(self):
        """Рисование всех примитивов"""
        if not self.primitives:
            return
        
        glPushAttrib(GL_POLYGON_BIT)
            
        glDisable(GL_LIGHTING)
        
        self.apply_render_mode()
        
        for primitive in self.primitives:
            coords = primitive["coords"]
            color = primitive["color"]
            
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
        
        if self.render_modes[self.current_render_mode] == GL_LINE and self.line_style != 0xFFFF:
            glDisable(GL_LINE_STIPPLE)
            
        if self.light_enabled:
            glEnable(GL_LIGHTING)
            
        glPopAttrib()

    def draw_light_sources(self):
        """Рисование источников света"""
        if not self.light_sources:
            return
            
        glDisable(GL_LIGHTING)
        glColor3f(1.0, 1.0, 0.0)
        glPointSize(10.0)
        
        glBegin(GL_POINTS)
        for light_pos in self.light_sources:
            glVertex3f(light_pos[0], light_pos[1], light_pos[2])
        glEnd()
        
        if self.light_enabled:
            glEnable(GL_LIGHTING)

    def draw_color_picker(self):
        """Отрисовка палитры цветов"""
        glPushAttrib(GL_ALL_ATTRIB_BITS)
        
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        glDisable(GL_LIGHTING)
        glDisable(GL_COLOR_MATERIAL)
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        glColor4f(0.2, 0.2, 0.2, 0.8)
        glBegin(GL_QUADS)
        glVertex2f(0, 0)
        glVertex2f(self.width, 0)
        glVertex2f(self.width, self.height)
        glVertex2f(0, self.height)
        glEnd()
        
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.palette_texture)
        glColor4f(1, 1, 1, 1)
        x_pos = self.width // 2 - 150
        y_pos = self.height // 2 - 150
        glBegin(GL_QUADS)
        glTexCoord2f(0, 1); glVertex2f(x_pos, y_pos)
        glTexCoord2f(1, 1); glVertex2f(x_pos + 300, y_pos)
        glTexCoord2f(1, 0); glVertex2f(x_pos + 300, y_pos + 300)
        glTexCoord2f(0, 0); glVertex2f(x_pos, y_pos + 300)
        glEnd()
        glDisable(GL_TEXTURE_2D)
        
        action_button_x = x_pos + 320
        action_button_y = y_pos
        action_button_size = 30
        
        if self.temp_selected_color is not None:
            button_color = self.temp_selected_color
        elif self.color_picker_type == 'background':
            button_color = self.background_color
        elif self.color_picker_type == 'cone':
            button_color = self.cone_color
        elif self.color_picker_type == 'cone_checker_color':
            button_color = self.checker_color1
        else:
            button_color = self.current_primitive_color
        
        glColor4f(*button_color)
        glBegin(GL_QUADS)
        glVertex2f(action_button_x, action_button_y)
        glVertex2f(action_button_x + action_button_size, action_button_y)
        glVertex2f(action_button_x + action_button_size, action_button_y + action_button_size)
        glVertex2f(action_button_x, action_button_y + action_button_size)
        glEnd()
        
        glColor4f(1, 1, 1, 1)
        glLineWidth(2.0)
        glBegin(GL_LINE_LOOP)
        glVertex2f(action_button_x, action_button_y)
        glVertex2f(action_button_x + action_button_size, action_button_y)
        glVertex2f(action_button_x + action_button_size, action_button_y + action_button_size)
        glVertex2f(action_button_x, action_button_y + action_button_size)
        glEnd()
        
        symbol_margin = 8
        glColor4f(1, 1, 1, 1)
        
        if self.color_picker_type == 'input_color':
            glLineWidth(2.0)
            glBegin(GL_LINES)
            glVertex2f(action_button_x + symbol_margin, action_button_y + action_button_size // 2)
            glVertex2f(action_button_x + action_button_size // 2, action_button_y + action_button_size - symbol_margin)
            glVertex2f(action_button_x + action_button_size // 2, action_button_y + action_button_size - symbol_margin)
            glVertex2f(action_button_x + action_button_size - symbol_margin, action_button_y + symbol_margin)
            glEnd()
        else:
            glLineWidth(2.0)
            glBegin(GL_LINES)
            glVertex2f(action_button_x + symbol_margin, action_button_y + symbol_margin)
            glVertex2f(action_button_x + action_button_size - symbol_margin, action_button_y + action_button_size - symbol_margin)
            glVertex2f(action_button_x + action_button_size - symbol_margin, action_button_y + symbol_margin)
            glVertex2f(action_button_x + symbol_margin, action_button_y + action_button_size - symbol_margin)
            glEnd()
        
        glDisable(GL_BLEND)
        glEnable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        
        glPopAttrib()

    def draw_ui(self):
        """Отрисовка интерфейса"""
        glPushAttrib(GL_ALL_ATTRIB_BITS)
        
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        glDisable(GL_LIGHTING)
        glDisable(GL_COLOR_MATERIAL)
        glDisable(GL_DEPTH_TEST)
        
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        
        # Отрисовка кнопок по бокам
        self.draw_button_group(self.scene_buttons, "Управление сценой", (70, 130, 200))
        self.draw_button_group(self.primitives_buttons, "Примитивы", (200, 70, 120))
        self.draw_button_group(self.rendering_buttons, "Настройки отрисовки", (120, 180, 70))
        self.draw_button_group(self.cone_light_buttons, "Конус и освещение", (180, 70, 180))
        
        glEnable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        
        glPopAttrib()
        
        # Отрисовка текста и информационных панелей
        self.draw_text_with_pygame()
        
        if self.color_picker_active:
            self.draw_color_picker()

    def draw_button_group(self, buttons, title, color):
        """Отрисовка группы кнопок с заголовком"""
        if buttons:
            group_rect = buttons[0]["rect"].unionall([b["rect"] for b in buttons])
            group_rect = pygame.Rect(group_rect.left - 5, group_rect.top - 25, 
                                    group_rect.width + 10, group_rect.height + 30)
            
            # Фон группы (полупрозрачный темный)
            glColor4f(0.1, 0.1, 0.1, 0.7)
            glBegin(GL_QUADS)
            glVertex2f(group_rect.left, group_rect.top)
            glVertex2f(group_rect.right, group_rect.top)
            glVertex2f(group_rect.right, group_rect.bottom)
            glVertex2f(group_rect.left, group_rect.bottom)
            glEnd()
            
            # Рамка группы с цветом темы
            glColor4f(color[0]/255.0, color[1]/255.0, color[2]/255.0, 1.0)
            glLineWidth(2.0)
            glBegin(GL_LINE_LOOP)
            glVertex2f(group_rect.left, group_rect.top)
            glVertex2f(group_rect.right, group_rect.top)
            glVertex2f(group_rect.right, group_rect.bottom)
            glVertex2f(group_rect.left, group_rect.bottom)
            glEnd()
        
        # Рисуем кнопки с современным стилем
        for button in buttons:
            # Основной фон кнопки (современный плоский стиль)
            glColor4f(0.95, 0.95, 0.95, 1.0)
            glBegin(GL_QUADS)
            glVertex2f(button["rect"].left, button["rect"].top)
            glVertex2f(button["rect"].right, button["rect"].top)
            glVertex2f(button["rect"].right, button["rect"].bottom)
            glVertex2f(button["rect"].left, button["rect"].bottom)
            glEnd()
            
            # Тонкая рамка кнопки
            glColor4f(0.7, 0.7, 0.7, 1.0)
            glLineWidth(1.0)
            glBegin(GL_LINE_LOOP)
            glVertex2f(button["rect"].left, button["rect"].top)
            glVertex2f(button["rect"].right, button["rect"].top)
            glVertex2f(button["rect"].right, button["rect"].bottom)
            glVertex2f(button["rect"].left, button["rect"].bottom)
            glEnd()
            
            # Акцентная линия сверху кнопки
            glColor4f(color[0]/255.0, color[1]/255.0, color[2]/255.0, 1.0)
            glLineWidth(3.0)
            glBegin(GL_LINES)
            glVertex2f(button["rect"].left, button["rect"].top)
            glVertex2f(button["rect"].right, button["rect"].top)
            glEnd()

    def draw_text_with_pygame(self):
        """Отрисовка текста интерфейса"""
        text_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        text_surface.fill((0, 0, 0, 0))
        
        # Отрисовка заголовков групп кнопок
        group_titles = [
            (self.scene_buttons, "Управление сценой", (70, 130, 200)),
            (self.primitives_buttons, "Примитивы", (200, 70, 120)),
            (self.rendering_buttons, "Настройки отрисовки", (120, 180, 70)),
            (self.cone_light_buttons, "Конус и освещение", (180, 70, 180))
        ]
        
        for buttons, title, color in group_titles:
            if buttons:
                group_rect = buttons[0]["rect"].unionall([b["rect"] for b in buttons])
                title_rect = pygame.Rect(group_rect.left, group_rect.top - 22, group_rect.width, 20)
                title_text = self.title_font.render(title, True, color)
                text_surface.blit(title_text, (title_rect.left, title_rect.top))
        
        # Отрисовка текста на кнопках
        for button in self.all_buttons:
            text = self.font.render(button["text"], True, (40, 40, 40))
            text_rect = text.get_rect(center=button["rect"].center)
            text_surface.blit(text, text_rect)
        
        # Отрисовка информационных панелей (только если они видимы)
        if self.info_panels_visible:
            self.draw_info_panel(text_surface, "status", "Статус сцены", [
                f"Режим: {['Заливка', 'Каркас', 'Точки'][self.current_render_mode]}",
                f"Примитивов: {len(self.primitives)}",
                f"Источников света: {len(self.light_sources)}",
                f"Свет: {'ВКЛ' if self.light_enabled else 'ВЫКЛ'}",
                f"Толщина: {self.line_width}",
                f"Тип линии: {'Сплошная' if self.line_style == 0xFFFF else 'Пунктирная' if self.line_style == 0xF0F0 else 'Точечная'}",
                f"Текстура конуса: {'Цвет' if self.cone_texture_mode == 'color' else 'Шахматная' if self.cone_texture_mode == 'checker' else 'Пользовательская'}",
                f"Интенсивность света: {self.light_intensity:.1f}"
            ])
            
            self.draw_info_panel(text_surface, "coords", "Система координат", [
                "X - Красная ось",
                "Y - Зеленая ось", 
                "Z - Синяя ось",
                "Метки: каждые 2 единицы"
            ])
            
            self.draw_info_panel(text_surface, "controls", "Управление", [
                "Управление камерой:",
                "ЛКМ + движение - вращение",
                "Колесико - приближение/отдаление",
                "Пробел - сброс камеры",
                "R - сброс вращения конуса",
                "L - переключение света",
                "M - смена режима отрисовки",
                "C - очистка объектов",
                "+/- - интенсивность света",
                "I - скрыть/показать информацию"
            ])
        
        # Отрисовка поля ввода (всегда внизу)
        if self.input_active:
            input_rect = pygame.Rect(200, self.height - 50, self.width - 400, 35)
            # Подложка для поля ввода
            pygame.draw.rect(text_surface, (30, 30, 30, 240), input_rect.inflate(10, 10))
            pygame.draw.rect(text_surface, (255, 255, 255), input_rect)
            pygame.draw.rect(text_surface, (100, 100, 100), input_rect, 2)
            
            prompt_rect = pygame.Rect(10, self.height - 85, self.width - 20, 25)
            pygame.draw.rect(text_surface, (30, 30, 30, 240), prompt_rect.inflate(10, 5))
            
            prompt_text = self.input_font.render(self.input_prompt, True, (255, 255, 255))
            text_surface.blit(prompt_text, (prompt_rect.x + 5, prompt_rect.y + 5))
            
            input_text = self.input_font.render(self.input_text, True, (0, 0, 0))
            text_surface.blit(input_text, (input_rect.x + 5, input_rect.y + 5))
        
        # Конвертируем поверхность PyGame в текстуру OpenGL
        text_surface = pygame.transform.flip(text_surface, False, True)
        
        texture_data = pygame.image.tostring(text_surface, "RGBA", True)
        glEnable(GL_TEXTURE_2D)
        text_texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, text_texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.width, self.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, texture_data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        
        glPushAttrib(GL_ALL_ATTRIB_BITS)
        
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        glDisable(GL_LIGHTING)
        glDisable(GL_COLOR_MATERIAL)
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
        
        glPopAttrib()

    def draw_info_panel(self, surface, panel_key, title, lines):
        """Отрисовка информационной панели"""
        panel = self.info_panels[panel_key]
        
        # Полупрозрачная темная подложка
        pygame.draw.rect(surface, (30, 30, 30, 220), panel)
        pygame.draw.rect(surface, (80, 80, 80, 255), panel, 2)
        
        # Заголовок
        title_text = self.title_font.render(title, True, (255, 255, 255))
        surface.blit(title_text, (panel.x + 5, panel.y + 5))
        
        # Разделительная линия
        pygame.draw.line(surface, (100, 100, 100), 
                        (panel.x, panel.y + 25), 
                        (panel.x + panel.width, panel.y + 25), 1)
        
        # Содержимое
        for i, line in enumerate(lines):
            color = (255, 255, 255)
            if panel_key == "coords":
                if i == 1: color = (255, 100, 100)    # X - красный
                elif i == 2: color = (100, 255, 100)  # Y - зеленый
                elif i == 3: color = (100, 100, 255)  # Z - синий
            elif panel_key == "controls":
                if i == 0: color = (200, 200, 255)  # Заголовок управления
            
            text = self.font.render(line, True, color)
            surface.blit(text, (panel.x + 10, panel.y + 30 + i * 18))

    def run(self):
        """Основной цикл программы"""
        clock = pygame.time.Clock()
        running = True
        
        print("3D Graphics Editor Started!")
        print("Controls:")
        print("- Click buttons on the left/right for actions")
        print("- Left mouse button + drag: Rotate camera")
        print("- Mouse wheel: Zoom in/out")
        print("- Space: Reset camera")
        print("- R key: Reset cone rotation")
        print("- L key: Toggle lighting")
        print("- M key: Change render mode")
        print("- C key: Clear objects")
        print("- +/- keys: Adjust light intensity")
        print("- I key: Toggle info panels visibility")
        
        while running:
            running = self.handle_events()
            
            glClearColor(*self.background_color)
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            
            self.setup_camera()
            
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