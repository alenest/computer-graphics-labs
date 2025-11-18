// Подключение необходимых заголовочных файлов Windows API
#include <windows.h>
#include <windowsx.h>
#include <commdlg.h>
#include <commctrl.h>
#include <vector>
#include <algorithm>
#include <string>
#include <queue>

// Определения идентификаторов элементов управления
#define ID_TOOLBAR              1000
#define ID_COLOR_BUTTON         1001
#define ID_THICKNESS_TRACKBAR   1002
#define ID_CLEAR_BUTTON         1003
#define ID_BRUSH_SHAPE_COMBO    1004
#define ID_PENCIL_BUTTON        1101
#define ID_BRUSH_BUTTON         1102
#define ID_ERASER_BUTTON        1103
#define ID_FILL_BUTTON          1104
#define ID_RECTANGLE_BUTTON     1105
#define ID_ELLIPSE_BUTTON       1106
#define ID_CIRCLE_BUTTON        1107
#define ID_SAVE_BUTTON          1108
#define ID_SELECTION_BUTTON     1109
#define ID_ZOOM_BUTTON          1110

// Подключаем GDI+ для расширенной графики
#include <gdiplus.h>
#pragma comment(lib, "gdiplus.lib")
#pragma comment(lib, "comdlg32.lib")
#pragma comment(lib, "comctl32.lib")

using namespace Gdiplus;

// Глобальные переменные
HINSTANCE hInst;
WCHAR szTitle[100] = L"Графический редактор - Улучшенная версия";
WCHAR szWindowClass[100] = L"PaintClass";
ULONG_PTR gdiplusToken;

// Константы
const COLORREF BACKGROUND_COLOR = RGB(255, 255, 255);
const int TOOLBAR_HEIGHT = 80;
const int SIDEBAR_WIDTH = 100;

// Перечисление форм кисти
enum BrushShape {
    BRUSH_CIRCLE = 0,
    BRUSH_SQUARE = 1,
    BRUSH_ELLIPSE = 2,
    BRUSH_RECTANGLE = 3,
    BRUSH_TRIANGLE = 4
};

// Перечисление режимов выделения
enum SelectionMode {
    SELECTION_NONE = 0,
    SELECTION_CREATING = 1,
    SELECTION_MOVING = 2,
    SELECTION_RESIZING = 3
};

// Структура для объектов рисования
struct DrawingObject {
    int type;
    int startX, startY, endX, endY;
    int thickness;
    COLORREF color;
    bool isSelected;
    int brushShape;
    bool wasDrawnWithSelection;
    RECT selectionRect;
};

// Структура для выделения
struct Selection {
    RECT rect;
    bool active;
    SelectionMode mode;
    int resizeHandle;
    int originalStartX, originalStartY, originalEndX, originalEndY;
};

// Глобальные переменные для рисования
std::vector<DrawingObject> drawings;
bool isDrawing = false;
bool isResizing = false;
int currentTool = 0;
int currentThickness = 2;
int currentBrushShape = BRUSH_CIRCLE;
COLORREF currentColor = RGB(0, 0, 0);
int startX, startY, prevX, prevY;

// Переменные для выделения и редактирования
int selectedObjectIndex = -1;
const int HANDLE_SIZE = 6;

// Режимы изменения размера
enum ResizeMode { NONE, TOP_LEFT, TOP_RIGHT, BOTTOM_LEFT, BOTTOM_RIGHT, MOVE };
ResizeMode resizeMode = NONE;

// Переменные для двойной буферизации
HBITMAP hBufferBitmap = NULL;
HDC hBufferDC = NULL;
size_t bufferWidth = 0, bufferHeight = 0;

// Временный объект для предпросмотра
DrawingObject tempObject;
bool hasTempObject = false;

// Переменные выделения
Selection selection;
const int SELECTION_HANDLE_SIZE = 8;

// Переменная для предотвращения мигания
bool toolbarNeedsRedraw = true;

// Переменные для лупы
bool zoomMode = false;
RECT zoomRect;
float zoomFactor = 2.5f;
int zoomOffsetX = 0, zoomOffsetY = 0;
bool zoomDrawingMode = false; // Режим рисования в увеличенной области

// Прототипы функций
ATOM MyRegisterClass(HINSTANCE hInstance);
BOOL InitInstance(HINSTANCE, int);
LRESULT CALLBACK WndProc(HWND, UINT, WPARAM, LPARAM);
void DrawObject(HDC hdc, const DrawingObject& obj);
void AddDrawingObject(int type, int sx, int sy, int ex, int ey);
void RedrawBuffer(HWND hWnd);
void ResizeBuffer(HWND hWnd);
int GetEncoderClsid(const WCHAR* format, CLSID* pClsid);
void DrawSelection(HDC hdc, const DrawingObject& obj);
ResizeMode GetResizeHandle(const DrawingObject& obj, int x, int y);
void UpdateObjectHandles(DrawingObject& obj, ResizeMode handle, int newX, int newY);
void CreateToolbar(HWND hWnd);
void UpdateToolbarState(HWND hWnd);
void DrawBrush(HDC hdc, int x1, int y1, int x2, int y2, int thickness, COLORREF color, int shape);
void CustomFloodFill(HDC hdc, int x, int y, COLORREF newColor);
void SaveFile(HWND hWnd);
void StartSelection(int x, int y);
void UpdateSelection(int x, int y);
void EndSelection();
void DrawSelectionArea(HDC hdc);
int GetSelectionHandle(int x, int y);
void UpdateSelectionHandles(int x, int y);
void ApplyClipping(HDC hdc);
void RemoveClipping(HDC hdc);
bool IsPointInDrawingArea(int x, int y);
void ClearSelection();

// Функции для лупы
void ApplyZoom(HWND hWnd, int x, int y);
void ResetZoom(HWND hWnd = NULL);
void ScreenToZoomCoords(int& x, int& y);
void ZoomToScreenCoords(int& x, int& y);
void FloodFillWithClipping(HDC hdc, int x, int y, COLORREF color);
void DrawToolWithClipping(HDC hdc, int tool, int thickness, COLORREF color, int brushShape,
    int prevX, int prevY, int currentX, int currentY);

// Точка входа в приложение
int APIENTRY wWinMain(_In_ HINSTANCE hInstance, _In_opt_ HINSTANCE hPrevInstance,
    _In_ LPWSTR lpCmdLine, _In_ int nCmdShow)
{
    UNREFERENCED_PARAMETER(hPrevInstance);
    UNREFERENCED_PARAMETER(lpCmdLine);

    INITCOMMONCONTROLSEX icex;
    icex.dwSize = sizeof(INITCOMMONCONTROLSEX);
    icex.dwICC = ICC_BAR_CLASSES | ICC_STANDARD_CLASSES;
    InitCommonControlsEx(&icex);

    GdiplusStartupInput gdiplusStartupInput;
    GdiplusStartup(&gdiplusToken, &gdiplusStartupInput, NULL);

    selection.active = false;
    selection.mode = SELECTION_NONE;
    selection.resizeHandle = -1;

    zoomMode = false;
    zoomDrawingMode = false;
    zoomRect = { 0, 0, 0, 0 };
    zoomFactor = 2.5f;
    zoomOffsetX = 0;
    zoomOffsetY = 0;

    MyRegisterClass(hInstance);

    if (!InitInstance(hInstance, nCmdShow)) {
        GdiplusShutdown(gdiplusToken);
        return FALSE;
    }

    MSG msg;
    while (GetMessage(&msg, nullptr, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }

    if (hBufferBitmap) DeleteObject(hBufferBitmap);
    if (hBufferDC) DeleteDC(hBufferDC);

    GdiplusShutdown(gdiplusToken);
    return (int)msg.wParam;
}

// Регистрация класса окна
ATOM MyRegisterClass(HINSTANCE hInstance)
{
    WNDCLASSEXW wcex;
    wcex.cbSize = sizeof(WNDCLASSEX);
    wcex.style = CS_HREDRAW | CS_VREDRAW;
    wcex.lpfnWndProc = WndProc;
    wcex.cbClsExtra = 0;
    wcex.cbWndExtra = 0;
    wcex.hInstance = hInstance;
    wcex.hIcon = LoadIcon(nullptr, IDI_APPLICATION);
    wcex.hCursor = LoadCursor(nullptr, IDC_ARROW);
    wcex.hbrBackground = (HBRUSH)(COLOR_WINDOW + 1);
    wcex.lpszMenuName = nullptr;
    wcex.lpszClassName = szWindowClass;
    wcex.hIconSm = LoadIcon(nullptr, IDI_APPLICATION);

    return RegisterClassExW(&wcex);
}

// Создание окна приложения
BOOL InitInstance(HINSTANCE hInstance, int nCmdShow)
{
    hInst = hInstance;

    HWND hWnd = CreateWindowW(szWindowClass, L"Графический редактор - Улучшенная версия",
        WS_OVERLAPPEDWINDOW, CW_USEDEFAULT, 0, 800, 600,
        nullptr, nullptr, hInstance, nullptr);

    if (!hWnd) return FALSE;

    ShowWindow(hWnd, nCmdShow);
    UpdateWindow(hWnd);
    return TRUE;
}

// Функция изменения размера буфера
void ResizeBuffer(HWND hWnd)
{
    RECT rect;
    GetClientRect(hWnd, &rect);

    rect.left += SIDEBAR_WIDTH;
    rect.top += TOOLBAR_HEIGHT;

    size_t newWidth = static_cast<size_t>(rect.right - rect.left);
    size_t newHeight = static_cast<size_t>(rect.bottom - rect.top);

    if (newWidth == bufferWidth && newHeight == bufferHeight) return;

    if (hBufferBitmap) DeleteObject(hBufferBitmap);
    if (hBufferDC) DeleteDC(hBufferDC);

    HDC hdc = GetDC(hWnd);
    hBufferDC = CreateCompatibleDC(hdc);
    hBufferBitmap = CreateCompatibleBitmap(hdc, static_cast<int>(newWidth), static_cast<int>(newHeight));
    SelectObject(hBufferDC, hBufferBitmap);

    bufferWidth = newWidth;
    bufferHeight = newHeight;

    ReleaseDC(hWnd, hdc);

    RedrawBuffer(hWnd);
}

// Функция перерисовки буфера
void RedrawBuffer(HWND hWnd)
{
    if (!hBufferDC) return;

    Graphics graphics(hBufferDC);
    graphics.SetSmoothingMode(SmoothingModeAntiAlias);

    SolidBrush whiteBrush(Color(255, 255, 255, 255));
    graphics.FillRectangle(&whiteBrush, 0, 0, static_cast<int>(bufferWidth), static_cast<int>(bufferHeight));

    // Если активен режим рисования в увеличенной области, применяем обрезку
    if (zoomDrawingMode && zoomMode) {
        HRGN clipRegion = CreateRectRgn(zoomRect.left, zoomRect.top, zoomRect.right, zoomRect.bottom);
        SelectClipRgn(hBufferDC, clipRegion);

        for (const auto& obj : drawings) {
            DrawObject(hBufferDC, obj);
        }

        SelectClipRgn(hBufferDC, NULL);
        DeleteObject(clipRegion);
    }
    else {
        for (const auto& obj : drawings) {
            if (obj.wasDrawnWithSelection) {
                HRGN oldClipRegion = CreateRectRgn(0, 0, 0, 0);
                GetClipRgn(hBufferDC, oldClipRegion);

                HRGN clipRegion = CreateRectRgn(obj.selectionRect.left, obj.selectionRect.top,
                    obj.selectionRect.right, obj.selectionRect.bottom);
                SelectClipRgn(hBufferDC, clipRegion);

                DrawObject(hBufferDC, obj);

                SelectClipRgn(hBufferDC, oldClipRegion);
                DeleteObject(clipRegion);
                DeleteObject(oldClipRegion);
            }
            else {
                DrawObject(hBufferDC, obj);
            }
        }
    }
}

// Функция рисования выделения объекта
void DrawSelection(HDC hdc, const DrawingObject& obj)
{
    int left = min(obj.startX, obj.endX);
    int top = min(obj.startY, obj.endY);
    int right = max(obj.startX, obj.endX);
    int bottom = max(obj.startY, obj.endY);

    HPEN hPen = CreatePen(PS_DOT, 1, RGB(0, 0, 0));
    HPEN hOldPen = (HPEN)SelectObject(hdc, hPen);
    SelectObject(hdc, GetStockObject(NULL_BRUSH));

    Rectangle(hdc, left, top, right, bottom);

    HBRUSH hBrush = CreateSolidBrush(RGB(255, 255, 255));
    HBRUSH hOldBrush = (HBRUSH)SelectObject(hdc, hBrush);

    Rectangle(hdc, left - HANDLE_SIZE, top - HANDLE_SIZE, left + HANDLE_SIZE, top + HANDLE_SIZE);
    Rectangle(hdc, right - HANDLE_SIZE, top - HANDLE_SIZE, right + HANDLE_SIZE, top + HANDLE_SIZE);
    Rectangle(hdc, left - HANDLE_SIZE, bottom - HANDLE_SIZE, left + HANDLE_SIZE, bottom + HANDLE_SIZE);
    Rectangle(hdc, right - HANDLE_SIZE, bottom - HANDLE_SIZE, right + HANDLE_SIZE, bottom + HANDLE_SIZE);

    SelectObject(hdc, hOldBrush);
    SelectObject(hdc, hOldPen);
    DeleteObject(hPen);
    DeleteObject(hBrush);
}

// Функция определения, в какой маркер попал курсор
ResizeMode GetResizeHandle(const DrawingObject& obj, int x, int y)
{
    int left = min(obj.startX, obj.endX);
    int top = min(obj.startY, obj.endY);
    int right = max(obj.startX, obj.endX);
    int bottom = max(obj.startY, obj.endY);

    if (x >= left - HANDLE_SIZE && x <= left + HANDLE_SIZE &&
        y >= top - HANDLE_SIZE && y <= top + HANDLE_SIZE)
        return TOP_LEFT;

    if (x >= right - HANDLE_SIZE && x <= right + HANDLE_SIZE &&
        y >= top - HANDLE_SIZE && y <= top + HANDLE_SIZE)
        return TOP_RIGHT;

    if (x >= left - HANDLE_SIZE && x <= left + HANDLE_SIZE &&
        y >= bottom - HANDLE_SIZE && y <= bottom + HANDLE_SIZE)
        return BOTTOM_LEFT;

    if (x >= right - HANDLE_SIZE && x <= right + HANDLE_SIZE &&
        y >= bottom - HANDLE_SIZE && y <= bottom + HANDLE_SIZE)
        return BOTTOM_RIGHT;

    if (x >= left && x <= right && y >= top && y <= bottom)
        return MOVE;

    return NONE;
}

// Функция обновления объекта при изменении размера
void UpdateObjectHandles(DrawingObject& obj, ResizeMode handle, int newX, int newY)
{
    switch (handle) {
    case TOP_LEFT:
        obj.startX = newX;
        obj.startY = newY;
        break;
    case TOP_RIGHT:
        obj.endX = newX;
        obj.startY = newY;
        break;
    case BOTTOM_LEFT:
        obj.startX = newX;
        obj.endY = newY;
        break;
    case BOTTOM_RIGHT:
        obj.endX = newX;
        obj.endY = newY;
        break;
    case MOVE:
        int deltaX = newX - (obj.startX + (obj.endX - obj.startX) / 2);
        int deltaY = newY - (obj.startY + (obj.endY - obj.startY) / 2);
        obj.startX += deltaX;
        obj.endX += deltaX;
        obj.startY += deltaY;
        obj.endY += deltaY;
        break;
    }
}

// Функция рисования кисти
void DrawBrush(HDC hdc, int x1, int y1, int x2, int y2, int thickness, COLORREF color, int shape)
{
    HBRUSH hBrush = CreateSolidBrush(color);
    HBRUSH hOldBrush = (HBRUSH)SelectObject(hdc, hBrush);
    HPEN hPen = CreatePen(PS_SOLID, 1, color);
    HPEN hOldPen = (HPEN)SelectObject(hdc, hPen);

    int brushSize = thickness * 2;
    int left = min(x1, x2) - brushSize / 2;
    int top = min(y1, y2) - brushSize / 2;
    int right = max(x1, x2) + brushSize / 2;
    int bottom = max(y1, y2) + brushSize / 2;
    int width = right - left;
    int height = bottom - top;

    switch (shape) {
    case BRUSH_CIRCLE:
    {
        int size = min(width, height);
        Ellipse(hdc, left, top, left + size, top + size);
    }
    break;

    case BRUSH_SQUARE:
    {
        int size = min(width, height);
        Rectangle(hdc, left, top, left + size, top + size);
    }
    break;

    case BRUSH_ELLIPSE:
        Ellipse(hdc, left, top, right, bottom);
        break;

    case BRUSH_RECTANGLE:
        Rectangle(hdc, left, top, right, bottom);
        break;

    case BRUSH_TRIANGLE:
    {
        POINT points[3];
        points[0].x = (left + right) / 2;
        points[0].y = top;
        points[1].x = left;
        points[1].y = bottom;
        points[2].x = right;
        points[2].y = bottom;
        Polygon(hdc, points, 3);
    }
    break;
    }

    SelectObject(hdc, hOldBrush);
    SelectObject(hdc, hOldPen);
    DeleteObject(hBrush);
    DeleteObject(hPen);
}

// Функция заливки области (алгоритм заливки с затравкой)
void CustomFloodFill(HDC hdc, int x, int y, COLORREF newColor)
{
    COLORREF targetColor = GetPixel(hdc, x, y);

    if (targetColor == newColor) return;

    std::queue<POINT> pixels;
    pixels.push({ x, y });

    while (!pixels.empty()) {
        POINT p = pixels.front();
        pixels.pop();

        int currentX = p.x;
        int currentY = p.y;

        if (currentX < 0 || currentX >= static_cast<int>(bufferWidth) ||
            currentY < 0 || currentY >= static_cast<int>(bufferHeight))
            continue;

        COLORREF currentColor = GetPixel(hdc, currentX, currentY);
        if (currentColor != targetColor) continue;

        SetPixel(hdc, currentX, currentY, newColor);

        pixels.push({ currentX + 1, currentY });
        pixels.push({ currentX - 1, currentY });
        pixels.push({ currentX, currentY + 1 });
        pixels.push({ currentX, currentY - 1 });
    }
}

// Функции для работы с выделением
bool IsPointInDrawingArea(int x, int y) {
    return x >= 0 && x < static_cast<int>(bufferWidth) &&
        y >= 0 && y < static_cast<int>(bufferHeight);
}

void StartSelection(int x, int y)
{
    selection.rect.left = x;
    selection.rect.top = y;
    selection.rect.right = x;
    selection.rect.bottom = y;
    selection.active = true;
    selection.mode = SELECTION_CREATING;
}

void UpdateSelection(int x, int y)
{
    if (!selection.active) return;

    if (selection.mode == SELECTION_CREATING) {
        selection.rect.right = x;
        selection.rect.bottom = y;

        selection.rect.left = max(0, min(selection.rect.left, static_cast<int>(bufferWidth)));
        selection.rect.top = max(0, min(selection.rect.top, static_cast<int>(bufferHeight)));
        selection.rect.right = max(0, min(selection.rect.right, static_cast<int>(bufferWidth)));
        selection.rect.bottom = max(0, min(selection.rect.bottom, static_cast<int>(bufferHeight)));
    }
    else if (selection.mode == SELECTION_RESIZING) {
        UpdateSelectionHandles(x, y);
    }
    else if (selection.mode == SELECTION_MOVING) {
        int deltaX = x - selection.originalStartX;
        int deltaY = y - selection.originalStartY;

        int newLeft = selection.rect.left + deltaX;
        int newTop = selection.rect.top + deltaY;
        int newRight = selection.rect.right + deltaX;
        int newBottom = selection.rect.bottom + deltaY;

        if (newLeft >= 0 && newRight < static_cast<int>(bufferWidth) &&
            newTop >= 0 && newBottom < static_cast<int>(bufferHeight)) {
            selection.rect.left = newLeft;
            selection.rect.top = newTop;
            selection.rect.right = newRight;
            selection.rect.bottom = newBottom;
        }
    }
}

void EndSelection()
{
    selection.mode = SELECTION_NONE;
    selection.resizeHandle = -1;
}

void ClearSelection()
{
    selection.active = false;
    selection.mode = SELECTION_NONE;
    selection.resizeHandle = -1;
}

// Рисование области выделения
void DrawSelectionArea(HDC hdc)
{
    if (!selection.active) return;

    HPEN hPen = CreatePen(PS_DOT, 1, RGB(0, 0, 255));
    HPEN hOldPen = (HPEN)SelectObject(hdc, hPen);
    SelectObject(hdc, GetStockObject(NULL_BRUSH));

    Rectangle(hdc, selection.rect.left, selection.rect.top,
        selection.rect.right, selection.rect.bottom);

    HBRUSH hBrush = CreateSolidBrush(RGB(0, 0, 255));
    HBRUSH hOldBrush = (HBRUSH)SelectObject(hdc, hBrush);

    Rectangle(hdc, selection.rect.left - SELECTION_HANDLE_SIZE,
        selection.rect.top - SELECTION_HANDLE_SIZE,
        selection.rect.left + SELECTION_HANDLE_SIZE,
        selection.rect.top + SELECTION_HANDLE_SIZE);

    Rectangle(hdc, selection.rect.right - SELECTION_HANDLE_SIZE,
        selection.rect.top - SELECTION_HANDLE_SIZE,
        selection.rect.right + SELECTION_HANDLE_SIZE,
        selection.rect.top + SELECTION_HANDLE_SIZE);

    Rectangle(hdc, selection.rect.left - SELECTION_HANDLE_SIZE,
        selection.rect.bottom - SELECTION_HANDLE_SIZE,
        selection.rect.left + SELECTION_HANDLE_SIZE,
        selection.rect.bottom + SELECTION_HANDLE_SIZE);

    Rectangle(hdc, selection.rect.right - SELECTION_HANDLE_SIZE,
        selection.rect.bottom - SELECTION_HANDLE_SIZE,
        selection.rect.right + SELECTION_HANDLE_SIZE,
        selection.rect.bottom + SELECTION_HANDLE_SIZE);

    SelectObject(hdc, hOldBrush);
    SelectObject(hdc, hOldPen);
    DeleteObject(hPen);
    DeleteObject(hBrush);
}

// Получение маркера выделения по координатам
int GetSelectionHandle(int x, int y)
{
    if (!selection.active) return -1;

    if (x >= selection.rect.left - SELECTION_HANDLE_SIZE && x <= selection.rect.left + SELECTION_HANDLE_SIZE &&
        y >= selection.rect.top - SELECTION_HANDLE_SIZE && y <= selection.rect.top + SELECTION_HANDLE_SIZE)
        return 0;

    if (x >= selection.rect.right - SELECTION_HANDLE_SIZE && x <= selection.rect.right + SELECTION_HANDLE_SIZE &&
        y >= selection.rect.top - SELECTION_HANDLE_SIZE && y <= selection.rect.top + SELECTION_HANDLE_SIZE)
        return 1;

    if (x >= selection.rect.left - SELECTION_HANDLE_SIZE && x <= selection.rect.left + SELECTION_HANDLE_SIZE &&
        y >= selection.rect.bottom - SELECTION_HANDLE_SIZE && y <= selection.rect.bottom + SELECTION_HANDLE_SIZE)
        return 2;

    if (x >= selection.rect.right - SELECTION_HANDLE_SIZE && x <= selection.rect.right + SELECTION_HANDLE_SIZE &&
        y >= selection.rect.bottom - SELECTION_HANDLE_SIZE && y <= selection.rect.bottom + SELECTION_HANDLE_SIZE)
        return 3;

    if (x >= selection.rect.left && x <= selection.rect.right &&
        y >= selection.rect.top && y <= selection.rect.bottom)
        return 6;

    return -1;
}

// Обновление маркеров выделения
void UpdateSelectionHandles(int x, int y)
{
    if (!selection.active) return;

    x = max(0, min(x, static_cast<int>(bufferWidth)));
    y = max(0, min(y, static_cast<int>(bufferHeight)));

    switch (selection.resizeHandle) {
    case 0:
        selection.rect.left = x;
        selection.rect.top = y;
        break;
    case 1:
        selection.rect.right = x;
        selection.rect.top = y;
        break;
    case 2:
        selection.rect.left = x;
        selection.rect.bottom = y;
        break;
    case 3:
        selection.rect.right = x;
        selection.rect.bottom = y;
        break;
    }

    if (selection.rect.left > selection.rect.right) {
        int temp = selection.rect.left;
        selection.rect.left = selection.rect.right;
        selection.rect.right = temp;
    }
    if (selection.rect.top > selection.rect.bottom) {
        int temp = selection.rect.top;
        selection.rect.top = selection.rect.bottom;
        selection.rect.bottom = temp;
    }
}

// Применение обрезки по области выделения
void ApplyClipping(HDC hdc)
{
    if (selection.active) {
        HRGN clipRegion = CreateRectRgn(selection.rect.left, selection.rect.top,
            selection.rect.right, selection.rect.bottom);
        SelectClipRgn(hdc, clipRegion);
        DeleteObject(clipRegion);
    }
}

// Удаление обрезки
void RemoveClipping(HDC hdc)
{
    SelectClipRgn(hdc, NULL);
}

// Функция для заливки с обрезкой
void FloodFillWithClipping(HDC hdc, int x, int y, COLORREF color)
{
    if (selection.active) {
        ApplyClipping(hdc);
    }

    CustomFloodFill(hdc, x, y, color);

    if (selection.active) {
        RemoveClipping(hdc);
    }
}

// Функция для рисования инструментами с обрезкой
void DrawToolWithClipping(HDC hdc, int tool, int thickness, COLORREF color, int brushShape,
    int prevX, int prevY, int currentX, int currentY)
{
    // Если активен режим рисования в увеличенной области, применяем обрезку к zoomRect
    if (zoomDrawingMode && zoomMode) {
        HRGN clipRegion = CreateRectRgn(zoomRect.left, zoomRect.top, zoomRect.right, zoomRect.bottom);
        SelectClipRgn(hdc, clipRegion);
    }
    else if (selection.active) {
        ApplyClipping(hdc);
    }

    if (tool == 0) {
        HPEN hPen = CreatePen(PS_SOLID, thickness, color);
        HPEN hOldPen = (HPEN)SelectObject(hdc, hPen);

        MoveToEx(hdc, prevX, prevY, NULL);
        LineTo(hdc, currentX, currentY);

        SelectObject(hdc, hOldPen);
        DeleteObject(hPen);
    }
    else if (tool == 3) {
        DrawBrush(hdc, prevX, prevY, currentX, currentY, thickness, color, brushShape);
    }
    else if (tool == 4) {
        HPEN hPen = CreatePen(PS_SOLID, thickness, BACKGROUND_COLOR);
        HPEN hOldPen = (HPEN)SelectObject(hdc, hPen);

        MoveToEx(hdc, prevX, prevY, NULL);
        LineTo(hdc, currentX, currentY);

        SelectObject(hdc, hOldPen);
        DeleteObject(hPen);
    }

    // Убираем обрезку
    if (zoomDrawingMode && zoomMode) {
        SelectClipRgn(hdc, NULL);
    }
    else if (selection.active) {
        RemoveClipping(hdc);
    }
}

// Функции для лупы

// Применение увеличения области
void ApplyZoom(HWND hWnd, int x, int y)
{
    if (!hBufferDC) return;

    // Определяем область для увеличения (размер зависит от коэффициента увеличения)
    int zoomWidth = static_cast<int>(bufferWidth / zoomFactor);
    int zoomHeight = static_cast<int>(bufferHeight / zoomFactor);

    zoomRect.left = max(0, x - zoomWidth / 2);
    zoomRect.top = max(0, y - zoomHeight / 2);
    zoomRect.right = min(static_cast<int>(bufferWidth), zoomRect.left + zoomWidth);
    zoomRect.bottom = min(static_cast<int>(bufferHeight), zoomRect.top + zoomHeight);

    // Включаем режим лупы и режим рисования в увеличенной области
    zoomMode = true;
    zoomDrawingMode = true;

    // Обновляем отображение
    RECT drawingRect;
    GetClientRect(hWnd, &drawingRect);
    drawingRect.left = SIDEBAR_WIDTH;
    drawingRect.top = TOOLBAR_HEIGHT;
    InvalidateRect(hWnd, &drawingRect, TRUE);

    // Обновляем текст кнопки лупы
    SetWindowText(GetDlgItem(hWnd, ID_ZOOM_BUTTON), L"Лупа [активна]");
}

// Сброс увеличения
void ResetZoom(HWND hWnd)
{
    zoomMode = false;
    zoomDrawingMode = false;
    zoomRect = { 0, 0, 0, 0 };
    zoomOffsetX = 0;
    zoomOffsetY = 0;

    if (hWnd) {
        SetWindowText(GetDlgItem(hWnd, ID_ZOOM_BUTTON), L"Лупа");
    }
}

// Преобразование координат из экранных в координаты увеличенной области
void ScreenToZoomCoords(int& x, int& y)
{
    if (!zoomMode) return;

    // Вычисляем коэффициенты масштабирования
    float scaleX = static_cast<float>(zoomRect.right - zoomRect.left) / bufferWidth;
    float scaleY = static_cast<float>(zoomRect.bottom - zoomRect.top) / bufferHeight;

    // Преобразуем координаты
    x = zoomRect.left + static_cast<int>((x - SIDEBAR_WIDTH) * scaleX);
    y = zoomRect.top + static_cast<int>((y - TOOLBAR_HEIGHT) * scaleY);
}

// Преобразование координат из увеличенной области в экранные
void ZoomToScreenCoords(int& x, int& y)
{
    if (!zoomMode) return;

    // Вычисляем коэффициенты масштабирования
    float scaleX = static_cast<float>(bufferWidth) / (zoomRect.right - zoomRect.left);
    float scaleY = static_cast<float>(bufferHeight) / (zoomRect.bottom - zoomRect.top);

    // Преобразуем координаты
    x = SIDEBAR_WIDTH + static_cast<int>((x - zoomRect.left) * scaleX);
    y = TOOLBAR_HEIGHT + static_cast<int>((y - zoomRect.top) * scaleY);
}

// Создание панели инструментов
void CreateToolbar(HWND hWnd)
{
    // ВЕРХНЯЯ ПАНЕЛЬ (горизонтальная) - кнопки управления
    CreateWindowW(L"BUTTON", L"Сохранить", WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
        SIDEBAR_WIDTH + 10, 10, 80, 30, hWnd, (HMENU)ID_SAVE_BUTTON, hInst, NULL);

    CreateWindowW(L"BUTTON", L"Очистить", WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
        SIDEBAR_WIDTH + 100, 10, 80, 30, hWnd, (HMENU)ID_CLEAR_BUTTON, hInst, NULL);

    CreateWindowW(L"BUTTON", L"Цвет", WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
        SIDEBAR_WIDTH + 190, 10, 60, 30, hWnd, (HMENU)ID_COLOR_BUTTON, hInst, NULL);

    CreateWindowW(L"STATIC", L"Толщина:", WS_VISIBLE | WS_CHILD,
        SIDEBAR_WIDTH + 260, 15, 60, 20, hWnd, NULL, hInst, NULL);

    HWND hTrackbar = CreateWindowW(TRACKBAR_CLASS, L"Толщина",
        WS_VISIBLE | WS_CHILD | TBS_AUTOTICKS | TBS_ENABLESELRANGE,
        SIDEBAR_WIDTH + 320, 10, 150, 30, hWnd, (HMENU)ID_THICKNESS_TRACKBAR, hInst, NULL);

    SendMessage(hTrackbar, TBM_SETRANGE, TRUE, MAKELONG(1, 50));
    SendMessage(hTrackbar, TBM_SETPOS, TRUE, currentThickness);
    SendMessage(hTrackbar, TBM_SETTICFREQ, 5, 0);

    CreateWindowW(L"STATIC", L"Форма кисти:", WS_VISIBLE | WS_CHILD,
        SIDEBAR_WIDTH + 480, 15, 80, 20, hWnd, NULL, hInst, NULL);

    HWND hCombo = CreateWindowW(L"COMBOBOX", L"",
        WS_VISIBLE | WS_CHILD | CBS_DROPDOWNLIST | CBS_HASSTRINGS,
        SIDEBAR_WIDTH + 570, 10, 120, 200, hWnd, (HMENU)ID_BRUSH_SHAPE_COMBO, hInst, NULL);

    SendMessageW(hCombo, CB_ADDSTRING, 0, (LPARAM)L"Круг");
    SendMessageW(hCombo, CB_ADDSTRING, 0, (LPARAM)L"Квадрат");
    SendMessageW(hCombo, CB_ADDSTRING, 0, (LPARAM)L"Эллипс");
    SendMessageW(hCombo, CB_ADDSTRING, 0, (LPARAM)L"Прямоугольник");
    SendMessageW(hCombo, CB_ADDSTRING, 0, (LPARAM)L"Треугольник");
    SendMessageW(hCombo, CB_SETCURSEL, currentBrushShape, 0);

    // БОКОВАЯ ПАНЕЛЬ (вертикальная) - инструменты рисования
    CreateWindowW(L"BUTTON", L"Карандаш", WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
        10, TOOLBAR_HEIGHT + 10, 80, 30, hWnd, (HMENU)ID_PENCIL_BUTTON, hInst, NULL);

    CreateWindowW(L"BUTTON", L"Кисть", WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
        10, TOOLBAR_HEIGHT + 50, 80, 30, hWnd, (HMENU)ID_BRUSH_BUTTON, hInst, NULL);

    CreateWindowW(L"BUTTON", L"Ластик", WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
        10, TOOLBAR_HEIGHT + 90, 80, 30, hWnd, (HMENU)ID_ERASER_BUTTON, hInst, NULL);

    CreateWindowW(L"BUTTON", L"Заливка", WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
        10, TOOLBAR_HEIGHT + 130, 80, 30, hWnd, (HMENU)ID_FILL_BUTTON, hInst, NULL);

    CreateWindowW(L"BUTTON", L"Прямоуг.", WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
        10, TOOLBAR_HEIGHT + 170, 80, 30, hWnd, (HMENU)ID_RECTANGLE_BUTTON, hInst, NULL);

    CreateWindowW(L"BUTTON", L"Окружность", WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
        10, TOOLBAR_HEIGHT + 210, 80, 30, hWnd, (HMENU)ID_CIRCLE_BUTTON, hInst, NULL);

    CreateWindowW(L"BUTTON", L"Выделение", WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
        10, TOOLBAR_HEIGHT + 250, 80, 30, hWnd, (HMENU)ID_SELECTION_BUTTON, hInst, NULL);

    CreateWindowW(L"BUTTON", L"Лупа", WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
        10, TOOLBAR_HEIGHT + 290, 80, 30, hWnd, (HMENU)ID_ZOOM_BUTTON, hInst, NULL);
}

// Обновление состояния панели инструментов
void UpdateToolbarState(HWND hWnd)
{
    HWND hTrackbar = GetDlgItem(hWnd, ID_THICKNESS_TRACKBAR);
    if (hTrackbar) {
        SendMessage(hTrackbar, TBM_SETPOS, TRUE, currentThickness);
    }

    HWND hCombo = GetDlgItem(hWnd, ID_BRUSH_SHAPE_COMBO);
    if (hCombo) {
        SendMessageW(hCombo, CB_SETCURSEL, currentBrushShape, 0);
    }
}

// Функция сохранения файла
void SaveFile(HWND hWnd)
{
    OPENFILENAME ofn = {};
    WCHAR filename[MAX_PATH] = L"рисунок.bmp";

    ofn.lStructSize = sizeof(ofn);
    ofn.hwndOwner = hWnd;
    ofn.lpstrFilter = L"BMP Files\0*.bmp\0WMF Files\0*.wmf\0ICO Files\0*.ico\0All Files\0*.*\0";
    ofn.lpstrFile = filename;
    ofn.nMaxFile = MAX_PATH;
    ofn.Flags = OFN_EXPLORER | OFN_OVERWRITEPROMPT;
    ofn.lpstrDefExt = L"bmp";

    if (GetSaveFileName(&ofn)) {
        Bitmap bitmap(hBufferBitmap, NULL);

        std::wstring fileExt = ofn.lpstrFile;
        if (fileExt.find(L".wmf") != std::wstring::npos) {
            CLSID clsidWmf;
            if (GetEncoderClsid(L"image/wmf", &clsidWmf) != -1) {
                bitmap.Save(filename, &clsidWmf, NULL);
            }
        }
        else if (fileExt.find(L".ico") != std::wstring::npos) {
            CLSID clsidIco;
            if (GetEncoderClsid(L"image/x-icon", &clsidIco) != -1) {
                bitmap.Save(filename, &clsidIco, NULL);
            }
        }
        else {
            CLSID clsidBmp;
            if (GetEncoderClsid(L"image/bmp", &clsidBmp) != -1) {
                bitmap.Save(filename, &clsidBmp, NULL);
            }
        }
    }
}

// Главная оконная процедура
LRESULT CALLBACK WndProc(HWND hWnd, UINT message, WPARAM wParam, LPARAM lParam)
{
    static int dragStartX, dragStartY;
    static int originalStartX, originalStartY, originalEndX, originalEndY;

    switch (message) {

    case WM_SIZE:
        ResizeBuffer(hWnd);
        toolbarNeedsRedraw = true;
        break;

    case WM_COMMAND:
    {
        int wmId = LOWORD(wParam);
        int wmEvent = HIWORD(wParam);

        switch (wmId) {
        case ID_PENCIL_BUTTON:
            currentTool = 0;
            selectedObjectIndex = -1;
            toolbarNeedsRedraw = true;
            break;
        case ID_BRUSH_BUTTON:
            currentTool = 3;
            selectedObjectIndex = -1;
            toolbarNeedsRedraw = true;
            break;
        case ID_ERASER_BUTTON:
            currentTool = 4;
            selectedObjectIndex = -1;
            toolbarNeedsRedraw = true;
            break;
        case ID_FILL_BUTTON:
            currentTool = 6;
            selectedObjectIndex = -1;
            toolbarNeedsRedraw = true;
            break;
        case ID_RECTANGLE_BUTTON:
            currentTool = 1;
            selectedObjectIndex = -1;
            toolbarNeedsRedraw = true;
            break;
        case ID_CIRCLE_BUTTON:
            currentTool = 5;
            selectedObjectIndex = -1;
            toolbarNeedsRedraw = true;
            break;
        case ID_SELECTION_BUTTON:
            if (selection.active) {
                ClearSelection();
                currentTool = 0;
            }
            else {
                currentTool = 7;
            }
            selectedObjectIndex = -1;
            toolbarNeedsRedraw = true;
            break;

        case ID_ZOOM_BUTTON:
            if (zoomMode) {
                ResetZoom(hWnd);
                currentTool = 0;
            }
            else {
                currentTool = 8;
                SetWindowText(GetDlgItem(hWnd, ID_ZOOM_BUTTON), L"Лупа [режим]");
            }
            selectedObjectIndex = -1;
            toolbarNeedsRedraw = true;
            break;

        case ID_COLOR_BUTTON:
        {
            CHOOSECOLOR cc = {};
            static COLORREF customColors[16] = {};
            cc.lStructSize = sizeof(cc);
            cc.hwndOwner = hWnd;
            cc.lpCustColors = customColors;
            cc.rgbResult = currentColor;
            cc.Flags = CC_FULLOPEN | CC_RGBINIT;

            if (ChooseColor(&cc)) {
                currentColor = cc.rgbResult;
            }
            toolbarNeedsRedraw = true;
        }
        break;

        case ID_SAVE_BUTTON:
            SaveFile(hWnd);
            break;

        case ID_CLEAR_BUTTON:
            drawings.clear();
            ClearSelection();
            ResetZoom(hWnd);
            RedrawBuffer(hWnd);
            toolbarNeedsRedraw = true;
            InvalidateRect(hWnd, NULL, TRUE);
            break;

        case ID_BRUSH_SHAPE_COMBO:
            if (wmEvent == CBN_SELCHANGE) {
                HWND hCombo = GetDlgItem(hWnd, ID_BRUSH_SHAPE_COMBO);
                currentBrushShape = (int)SendMessage(hCombo, CB_GETCURSEL, 0, 0);
                UpdateToolbarState(hWnd);
                toolbarNeedsRedraw = true;
            }
            break;
        }

        RECT drawingRect;
        GetClientRect(hWnd, &drawingRect);
        drawingRect.left = SIDEBAR_WIDTH;
        drawingRect.top = TOOLBAR_HEIGHT;
        InvalidateRect(hWnd, &drawingRect, FALSE);
    }
    break;

    case WM_HSCROLL:
    {
        HWND hTrackbar = (HWND)lParam;
        if (hTrackbar == GetDlgItem(hWnd, ID_THICKNESS_TRACKBAR)) {
            currentThickness = (int)SendMessage(hTrackbar, TBM_GETPOS, 0, 0);
        }
    }
    break;

    case WM_KEYDOWN:
        if (wParam == VK_ESCAPE) {
            if (selection.active) {
                ClearSelection();
                RECT drawingRect;
                GetClientRect(hWnd, &drawingRect);
                drawingRect.left = SIDEBAR_WIDTH;
                drawingRect.top = TOOLBAR_HEIGHT;
                InvalidateRect(hWnd, &drawingRect, TRUE);
            }
            else if (zoomMode) {
                ResetZoom(hWnd);
                RECT drawingRect;
                GetClientRect(hWnd, &drawingRect);
                drawingRect.left = SIDEBAR_WIDTH;
                drawingRect.top = TOOLBAR_HEIGHT;
                InvalidateRect(hWnd, &drawingRect, TRUE);
            }
        }
        break;

    case WM_LBUTTONDOWN:
    {
        int x = GET_X_LPARAM(lParam);
        int y = GET_Y_LPARAM(lParam);

        // Проверяем, не кликнули ли по панелям инструментов
        if (y < TOOLBAR_HEIGHT || x < SIDEBAR_WIDTH) {
            break;
        }

        // Корректируем координаты для области рисования
        x -= SIDEBAR_WIDTH;
        y -= TOOLBAR_HEIGHT;

        // Обработка режима лупы
        if (currentTool == 8) {
            ApplyZoom(hWnd, x, y);
            break;
        }

        // ПРЕОБРАЗУЕМ КООРДИНАТЫ ЕСЛИ РЕЖИМ РИСОВАНИЯ В УВЕЛИЧЕННОЙ ОБЛАСТИ АКТИВЕН
        if (zoomDrawingMode && zoomMode) {
            ScreenToZoomCoords(x, y);

            // Проверяем, что клик внутри увеличенной области
            if (x < zoomRect.left || x >= zoomRect.right || y < zoomRect.top || y >= zoomRect.bottom) {
                break; // Игнорируем клики вне увеличенной области
            }
        }

        if (currentTool == 7) {
            int handle = GetSelectionHandle(x, y);

            if (handle >= 0 && handle <= 3) {
                selection.mode = SELECTION_RESIZING;
                selection.resizeHandle = handle;
                selection.originalStartX = x;
                selection.originalStartY = y;
            }
            else if (handle == 6) {
                selection.mode = SELECTION_MOVING;
                selection.originalStartX = x;
                selection.originalStartY = y;
                selection.originalStartX = selection.rect.left;
                selection.originalStartY = selection.rect.top;
                selection.originalEndX = selection.rect.right;
                selection.originalEndY = selection.rect.bottom;
            }
            else {
                StartSelection(x, y);
            }
        }
        else {
            if (selectedObjectIndex != -1) {
                resizeMode = GetResizeHandle(drawings[selectedObjectIndex], x, y);
                if (resizeMode != NONE) {
                    isResizing = true;
                    dragStartX = x;
                    dragStartY = y;

                    originalStartX = drawings[selectedObjectIndex].startX;
                    originalStartY = drawings[selectedObjectIndex].startY;
                    originalEndX = drawings[selectedObjectIndex].endX;
                    originalEndY = drawings[selectedObjectIndex].endY;

                    break;
                }
            }

            isDrawing = true;
            startX = x;
            startY = y;
            prevX = startX;
            prevY = startY;
            selectedObjectIndex = -1;

            if (currentTool == 6) {
                FloodFillWithClipping(hBufferDC, x, y, currentColor);
                AddDrawingObject(currentTool, x, y, x, y);
                isDrawing = false;
                RECT drawingRect;
                GetClientRect(hWnd, &drawingRect);
                drawingRect.left = SIDEBAR_WIDTH;
                drawingRect.top = TOOLBAR_HEIGHT;
                InvalidateRect(hWnd, &drawingRect, TRUE);
                break;
            }

            if (currentTool == 1 || currentTool == 5) {
                tempObject.type = currentTool;
                tempObject.startX = startX;
                tempObject.startY = startY;
                tempObject.endX = startX;
                tempObject.endY = startY;
                tempObject.thickness = currentThickness;
                tempObject.color = currentColor;
                hasTempObject = true;
            }
        }
    }
    break;

    case WM_MOUSEMOVE:
    {
        int currentX = GET_X_LPARAM(lParam);
        int currentY = GET_Y_LPARAM(lParam);

        // Корректируем координаты для области рисования
        if (currentY >= TOOLBAR_HEIGHT && currentX >= SIDEBAR_WIDTH) {
            currentX -= SIDEBAR_WIDTH;
            currentY -= TOOLBAR_HEIGHT;

            // ПРЕОБРАЗУЕМ КООРДИНАТЫ ЕСЛИ РЕЖИМ РИСОВАНИЯ В УВЕЛИЧЕННОЙ ОБЛАСТИ АКТИВЕН
            if (zoomDrawingMode && zoomMode) {
                ScreenToZoomCoords(currentX, currentY);

                // Проверяем, что движение внутри увеличенной области
                if (currentX < zoomRect.left || currentX >= zoomRect.right ||
                    currentY < zoomRect.top || currentY >= zoomRect.bottom) {
                    break; // Игнорируем движение вне увеличенной области
                }
            }
        }
        else {
            break;
        }

        if (currentTool == 7 && selection.active) {
            if (selection.mode != SELECTION_NONE && (wParam & MK_LBUTTON)) {
                UpdateSelection(currentX, currentY);
                RECT drawingRect;
                GetClientRect(hWnd, &drawingRect);
                drawingRect.left = SIDEBAR_WIDTH;
                drawingRect.top = TOOLBAR_HEIGHT;
                InvalidateRect(hWnd, &drawingRect, FALSE);
            }
        }
        else if (isResizing && selectedObjectIndex != -1) {
            if (resizeMode == MOVE) {
                int deltaX = currentX - dragStartX;
                int deltaY = currentY - dragStartY;
                drawings[selectedObjectIndex].startX = originalStartX + deltaX;
                drawings[selectedObjectIndex].startY = originalStartY + deltaY;
                drawings[selectedObjectIndex].endX = originalEndX + deltaX;
                drawings[selectedObjectIndex].endY = originalEndY + deltaY;
            }
            else {
                UpdateObjectHandles(drawings[selectedObjectIndex], resizeMode, currentX, currentY);
            }

            RedrawBuffer(hWnd);

            RECT updateRect;
            GetClientRect(hWnd, &updateRect);
            updateRect.left = SIDEBAR_WIDTH;
            updateRect.top = TOOLBAR_HEIGHT;
            InvalidateRect(hWnd, &updateRect, FALSE);
            UpdateWindow(hWnd);
        }
        else if (isDrawing && (wParam & MK_LBUTTON)) {
            if (currentTool == 0 || currentTool == 3 || currentTool == 4) {
                DrawToolWithClipping(hBufferDC, currentTool, currentThickness, currentColor,
                    currentBrushShape, prevX, prevY, currentX, currentY);

                AddDrawingObject(currentTool, prevX, prevY, currentX, currentY);

                prevX = currentX;
                prevY = currentY;

                RECT updateRect;
                updateRect.left = min(prevX, currentX) - currentThickness - 5 + SIDEBAR_WIDTH;
                updateRect.top = min(prevY, currentY) - currentThickness - 5 + TOOLBAR_HEIGHT;
                updateRect.right = max(prevX, currentX) + currentThickness + 5 + SIDEBAR_WIDTH;
                updateRect.bottom = max(prevY, currentY) + currentThickness + 5 + TOOLBAR_HEIGHT;

                InvalidateRect(hWnd, &updateRect, FALSE);
                UpdateWindow(hWnd);
            }
            else if (currentTool == 1 || currentTool == 5) {
                tempObject.endX = currentX;
                tempObject.endY = currentY;

                RECT updateRect;
                updateRect.left = min(startX, currentX) - currentThickness - 5 + SIDEBAR_WIDTH;
                updateRect.top = min(startY, currentY) - currentThickness - 5 + TOOLBAR_HEIGHT;
                updateRect.right = max(startX, currentX) + currentThickness + 5 + SIDEBAR_WIDTH;
                updateRect.bottom = max(startY, currentY) + currentThickness + 5 + TOOLBAR_HEIGHT;

                InvalidateRect(hWnd, &updateRect, FALSE);
                UpdateWindow(hWnd);
            }
        }
        else if (!isDrawing && !isResizing) {
            for (int i = static_cast<int>(drawings.size()) - 1; i >= 0; i--) {
                if (GetResizeHandle(drawings[i], currentX, currentY) != NONE) {
                    SetCursor(LoadCursor(NULL, IDC_SIZEALL));
                    break;
                }
            }
        }
    }
    break;

    case WM_LBUTTONUP:
        if (currentTool == 7 && selection.active) {
            EndSelection();
        }
        else if (isResizing) {
            isResizing = false;
            resizeMode = NONE;
            RedrawBuffer(hWnd);
            RECT drawingRect;
            GetClientRect(hWnd, &drawingRect);
            drawingRect.left = SIDEBAR_WIDTH;
            drawingRect.top = TOOLBAR_HEIGHT;
            InvalidateRect(hWnd, &drawingRect, TRUE);
        }
        else if (isDrawing) {
            isDrawing = false;
            int endX = GET_X_LPARAM(lParam) - SIDEBAR_WIDTH;
            int endY = GET_Y_LPARAM(lParam) - TOOLBAR_HEIGHT;

            // ПРЕОБРАЗУЕМ КООРДИНАТЫ ЕСЛИ РЕЖИМ РИСОВАНИЯ В УВЕЛИЧЕННОЙ ОБЛАСТИ АКТИВЕН
            if (zoomDrawingMode && zoomMode) {
                ScreenToZoomCoords(endX, endY);
            }

            if (currentTool == 1 || currentTool == 5) {
                AddDrawingObject(currentTool, startX, startY, endX, endY);
                hasTempObject = false;
                selectedObjectIndex = static_cast<int>(drawings.size()) - 1;
            }

            RedrawBuffer(hWnd);
            RECT drawingRect;
            GetClientRect(hWnd, &drawingRect);
            drawingRect.left = SIDEBAR_WIDTH;
            drawingRect.top = TOOLBAR_HEIGHT;
            InvalidateRect(hWnd, &drawingRect, TRUE);
        }
        else {
            int x = GET_X_LPARAM(lParam) - SIDEBAR_WIDTH;
            int y = GET_Y_LPARAM(lParam) - TOOLBAR_HEIGHT;

            // ПРЕОБРАЗУЕМ КООРДИНАТЫ ЕСЛИ РЕЖИМ РИСОВАНИЯ В УВЕЛИЧЕННОЙ ОБЛАСТИ АКТИВЕН
            if (zoomDrawingMode && zoomMode) {
                ScreenToZoomCoords(x, y);
            }

            selectedObjectIndex = -1;

            for (int i = static_cast<int>(drawings.size()) - 1; i >= 0; i--) {
                if (GetResizeHandle(drawings[i], x, y) != NONE) {
                    selectedObjectIndex = i;
                    break;
                }
            }
            RECT drawingRect;
            GetClientRect(hWnd, &drawingRect);
            drawingRect.left = SIDEBAR_WIDTH;
            drawingRect.top = TOOLBAR_HEIGHT;
            InvalidateRect(hWnd, &drawingRect, TRUE);
        }
        break;

    case WM_PAINT:
    {
        PAINTSTRUCT ps;
        HDC hdc = BeginPaint(hWnd, &ps);

        // Рисуем верхнюю панель инструментов
        if (toolbarNeedsRedraw || ps.rcPaint.top < TOOLBAR_HEIGHT) {
            RECT toolbarRect;
            GetClientRect(hWnd, &toolbarRect);
            toolbarRect.bottom = TOOLBAR_HEIGHT;
            FillRect(hdc, &toolbarRect, (HBRUSH)(COLOR_BTNFACE + 1));

            HPEN hPen = CreatePen(PS_SOLID, 1, GetSysColor(COLOR_3DSHADOW));
            HPEN hOldPen = (HPEN)SelectObject(hdc, hPen);
            MoveToEx(hdc, 0, TOOLBAR_HEIGHT - 1, NULL);
            LineTo(hdc, toolbarRect.right, TOOLBAR_HEIGHT - 1);
            SelectObject(hdc, hOldPen);
            DeleteObject(hPen);
        }

        // Рисуем боковую панель инструментов
        if (toolbarNeedsRedraw || ps.rcPaint.left < SIDEBAR_WIDTH) {
            RECT sidebarRect;
            GetClientRect(hWnd, &sidebarRect);
            sidebarRect.right = SIDEBAR_WIDTH;
            sidebarRect.top = TOOLBAR_HEIGHT;
            FillRect(hdc, &sidebarRect, (HBRUSH)(COLOR_BTNFACE + 1));

            HPEN hPen = CreatePen(PS_SOLID, 1, GetSysColor(COLOR_3DSHADOW));
            HPEN hOldPen = (HPEN)SelectObject(hdc, hPen);
            MoveToEx(hdc, SIDEBAR_WIDTH - 1, TOOLBAR_HEIGHT, NULL);
            LineTo(hdc, SIDEBAR_WIDTH - 1, sidebarRect.bottom);
            SelectObject(hdc, hOldPen);
            DeleteObject(hPen);
        }

        toolbarNeedsRedraw = false;

        if (hBufferDC) {
            if (zoomMode) {
                // РЕЖИМ ЛУПЫ: рисуем увеличенную область из буфера
                HDC hZoomDC = CreateCompatibleDC(hdc);
                HBITMAP hZoomBitmap = CreateCompatibleBitmap(hdc, static_cast<int>(bufferWidth), static_cast<int>(bufferHeight));
                SelectObject(hZoomDC, hZoomBitmap);

                // Копируем содержимое основного буфера во временный буфер
                BitBlt(hZoomDC, 0, 0, static_cast<int>(bufferWidth), static_cast<int>(bufferHeight),
                    hBufferDC, 0, 0, SRCCOPY);

                // Масштабируем область увеличения на весь холст
                int srcWidth = zoomRect.right - zoomRect.left;
                int srcHeight = zoomRect.bottom - zoomRect.top;

                StretchBlt(hdc, SIDEBAR_WIDTH, TOOLBAR_HEIGHT, static_cast<int>(bufferWidth), static_cast<int>(bufferHeight),
                    hZoomDC, zoomRect.left, zoomRect.top, srcWidth, srcHeight, SRCCOPY);

                // Рисуем красную рамку вокруг увеличенной области
                HPEN hPen = CreatePen(PS_SOLID, 2, RGB(255, 0, 0));
                HPEN hOldPen = (HPEN)SelectObject(hdc, hPen);
                SelectObject(hdc, GetStockObject(NULL_BRUSH));

                int frameLeft = SIDEBAR_WIDTH;
                int frameTop = TOOLBAR_HEIGHT;
                int frameRight = SIDEBAR_WIDTH + static_cast<int>(bufferWidth);
                int frameBottom = TOOLBAR_HEIGHT + static_cast<int>(bufferHeight);

                Rectangle(hdc, frameLeft, frameTop, frameRight, frameBottom);
                SelectObject(hdc, hOldPen);
                DeleteObject(hPen);

                DeleteObject(hZoomBitmap);
                DeleteDC(hZoomDC);
            }
            else {
                // НОРМАЛЬНЫЙ РЕЖИМ: рисуем буфер как есть
                BitBlt(hdc, SIDEBAR_WIDTH, TOOLBAR_HEIGHT, static_cast<int>(bufferWidth), static_cast<int>(bufferHeight),
                    hBufferDC, 0, 0, SRCCOPY);
            }

            // Рисуем временный объект поверх с обрезкой
            if (hasTempObject) {
                HDC hTempDC = CreateCompatibleDC(hdc);
                HBITMAP hTempBmp = CreateCompatibleBitmap(hdc, static_cast<int>(bufferWidth), static_cast<int>(bufferHeight));
                SelectObject(hTempDC, hTempBmp);

                BitBlt(hTempDC, 0, 0, static_cast<int>(bufferWidth), static_cast<int>(bufferHeight),
                    hBufferDC, 0, 0, SRCCOPY);

                if (selection.active) {
                    ApplyClipping(hTempDC);
                }
                DrawObject(hTempDC, tempObject);
                if (selection.active) {
                    RemoveClipping(hTempDC);
                }

                if (zoomMode) {
                    int srcWidth = zoomRect.right - zoomRect.left;
                    int srcHeight = zoomRect.bottom - zoomRect.top;
                    StretchBlt(hdc, SIDEBAR_WIDTH, TOOLBAR_HEIGHT, static_cast<int>(bufferWidth), static_cast<int>(bufferHeight),
                        hTempDC, zoomRect.left, zoomRect.top, srcWidth, srcHeight, SRCCOPY);
                }
                else {
                    BitBlt(hdc, SIDEBAR_WIDTH, TOOLBAR_HEIGHT, static_cast<int>(bufferWidth), static_cast<int>(bufferHeight),
                        hTempDC, 0, 0, SRCCOPY);
                }

                DeleteObject(hTempBmp);
                DeleteDC(hTempDC);
            }

            // Рисуем выделение выбранного объекта
            if (selectedObjectIndex != -1 && selectedObjectIndex < static_cast<int>(drawings.size())) {
                HDC hTempDC = CreateCompatibleDC(hdc);
                HBITMAP hTempBmp = CreateCompatibleBitmap(hdc, static_cast<int>(bufferWidth), static_cast<int>(bufferHeight));
                SelectObject(hTempDC, hTempBmp);

                BitBlt(hTempDC, 0, 0, static_cast<int>(bufferWidth), static_cast<int>(bufferHeight),
                    hBufferDC, 0, 0, SRCCOPY);

                DrawSelection(hTempDC, drawings[selectedObjectIndex]);

                if (zoomMode) {
                    int srcWidth = zoomRect.right - zoomRect.left;
                    int srcHeight = zoomRect.bottom - zoomRect.top;
                    StretchBlt(hdc, SIDEBAR_WIDTH, TOOLBAR_HEIGHT, static_cast<int>(bufferWidth), static_cast<int>(bufferHeight),
                        hTempDC, zoomRect.left, zoomRect.top, srcWidth, srcHeight, SRCCOPY);
                }
                else {
                    BitBlt(hdc, SIDEBAR_WIDTH, TOOLBAR_HEIGHT, static_cast<int>(bufferWidth), static_cast<int>(bufferHeight),
                        hTempDC, 0, 0, SRCCOPY);
                }

                DeleteObject(hTempBmp);
                DeleteDC(hTempDC);
            }

            // Рисуем область выделения
            if (selection.active) {
                HDC hTempDC = CreateCompatibleDC(hdc);
                HBITMAP hTempBmp = CreateCompatibleBitmap(hdc, static_cast<int>(bufferWidth), static_cast<int>(bufferHeight));
                SelectObject(hTempDC, hTempBmp);

                BitBlt(hTempDC, 0, 0, static_cast<int>(bufferWidth), static_cast<int>(bufferHeight),
                    hBufferDC, 0, 0, SRCCOPY);

                DrawSelectionArea(hTempDC);

                if (zoomMode) {
                    int srcWidth = zoomRect.right - zoomRect.left;
                    int srcHeight = zoomRect.bottom - zoomRect.top;
                    StretchBlt(hdc, SIDEBAR_WIDTH, TOOLBAR_HEIGHT, static_cast<int>(bufferWidth), static_cast<int>(bufferHeight),
                        hTempDC, zoomRect.left, zoomRect.top, srcWidth, srcHeight, SRCCOPY);
                }
                else {
                    BitBlt(hdc, SIDEBAR_WIDTH, TOOLBAR_HEIGHT, static_cast<int>(bufferWidth), static_cast<int>(bufferHeight),
                        hTempDC, 0, 0, SRCCOPY);
                }

                DeleteObject(hTempBmp);
                DeleteDC(hTempDC);
            }
        }
        else {
            RECT rect;
            GetClientRect(hWnd, &rect);
            rect.left = SIDEBAR_WIDTH;
            rect.top = TOOLBAR_HEIGHT;
            FillRect(hdc, &rect, (HBRUSH)GetStockObject(WHITE_BRUSH));
        }

        EndPaint(hWnd, &ps);
    }
    break;

    case WM_CREATE:
        CreateToolbar(hWnd);
        ResizeBuffer(hWnd);
        break;

    case WM_DESTROY:
        PostQuitMessage(0);
        break;

    default:
        return DefWindowProc(hWnd, message, wParam, lParam);
    }
    return 0;
}

// Функция рисования объекта
void DrawObject(HDC hdc, const DrawingObject& obj)
{
    Graphics graphics(hdc);
    graphics.SetSmoothingMode(SmoothingModeAntiAlias);

    COLORREF drawColor = (obj.type == 4) ? BACKGROUND_COLOR : obj.color;
    Color penColor(GetRValue(drawColor), GetGValue(drawColor), GetBValue(drawColor));
    Pen pen(penColor, (REAL)obj.thickness);

    if (obj.type == 0 || obj.type == 4) {
        pen.SetLineCap(LineCapRound, LineCapRound, DashCapRound);
        pen.SetLineJoin(LineJoinRound);
    }

    int left = min(obj.startX, obj.endX);
    int top = min(obj.startY, obj.endY);
    int right = max(obj.startX, obj.endX);
    int bottom = max(obj.startY, obj.endY);
    int width = right - left;
    int height = bottom - top;

    switch (obj.type) {
    case 0:
    case 4:
        graphics.DrawLine(&pen, obj.startX, obj.startY, obj.endX, obj.endY);
        break;

    case 1:
        graphics.DrawRectangle(&pen, left, top, width, height);
        break;

    case 3:
        DrawBrush(hdc, obj.startX, obj.startY, obj.endX, obj.endY, obj.thickness, obj.color, obj.brushShape);
        break;

    case 5:
    {
        int size = min(width, height);
        graphics.DrawEllipse(&pen, left, top, size, size);
    }
    break;

    case 6:
        break;
    }
}

// Функция добавления объекта в историю
void AddDrawingObject(int type, int sx, int sy, int ex, int ey)
{
    DrawingObject newObj;
    newObj.type = type;
    newObj.startX = sx;
    newObj.startY = sy;
    newObj.endX = ex;
    newObj.endY = ey;
    newObj.thickness = currentThickness;
    newObj.color = (type == 4) ? BACKGROUND_COLOR : currentColor;
    newObj.isSelected = false;
    newObj.brushShape = currentBrushShape;

    newObj.wasDrawnWithSelection = selection.active;
    if (selection.active) {
        newObj.selectionRect = selection.rect;
    }
    else {
        newObj.selectionRect = { 0, 0, 0, 0 };
    }

    drawings.push_back(newObj);
}

// Функция для получения CLSID кодера
int GetEncoderClsid(const WCHAR* format, CLSID* pClsid)
{
    UINT num = 0;
    UINT size = 0;

    Gdiplus::Status status = Gdiplus::GetImageEncodersSize(&num, &size);
    if (status != Gdiplus::Ok || size == 0) {
        return -1;
    }

    Gdiplus::ImageCodecInfo* pImageCodecInfo = (Gdiplus::ImageCodecInfo*)malloc(size);
    if (pImageCodecInfo == NULL) {
        return -1;
    }

    status = Gdiplus::GetImageEncoders(num, size, pImageCodecInfo);
    if (status != Gdiplus::Ok) {
        free(pImageCodecInfo);
        return -1;
    }

    int result = -1;
    for (UINT j = 0; j < num; ++j) {
        if (wcscmp(pImageCodecInfo[j].MimeType, format) == 0) {
            *pClsid = pImageCodecInfo[j].Clsid;
            result = (int)j;
            break;
        }
    }

    free(pImageCodecInfo);
    return result;
}