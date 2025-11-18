// LAB2_GDI+.cpp : Определяет точку входа для приложения.
//

#include "framework.h"
#include "LAB2_GDI+.h"
#include <windowsx.h>
#include <commdlg.h>
#include <vector>

// Минимальное подключение GDI+ - только то, что нужно
#include <gdiplus.h>
#pragma comment(lib, "gdiplus.lib")
#pragma comment(lib, "comdlg32.lib")

// Используем только необходимые части GDI+
using namespace Gdiplus;

#define MAX_LOADSTRING 100

// Глобальные переменные:
HINSTANCE hInst;
WCHAR szTitle[MAX_LOADSTRING];
WCHAR szWindowClass[MAX_LOADSTRING];

// Глобальная переменная для GDI+
ULONG_PTR gdiplusToken;

// Структура для рисования
struct DrawingObject {
    int type; // 0-линия, 1-прямоугольник, 2-эллипс
    int startX, startY, endX, endY;
    int thickness;
    COLORREF color;
};

// Глобальные переменные редактора
std::vector<DrawingObject> drawings;
bool isDrawing = false;
int currentTool = 0;
int currentThickness = 2;
COLORREF currentColor = RGB(0, 0, 0);
int startX, startY, prevX, prevY;

// Прототипы функций
ATOM MyRegisterClass(HINSTANCE hInstance);
BOOL InitInstance(HINSTANCE, int);
LRESULT CALLBACK WndProc(HWND, UINT, WPARAM, LPARAM);
INT_PTR CALLBACK About(HWND, UINT, WPARAM, LPARAM);
void DrawObject(HDC hdc, const DrawingObject& obj);
void AddDrawingObject(int type, int sx, int sy, int ex, int ey);
int GetEncoderClsid(const WCHAR* format, CLSID* pClsid);

// Точка входа
int APIENTRY wWinMain(_In_ HINSTANCE hInstance,
    _In_opt_ HINSTANCE hPrevInstance,
    _In_ LPWSTR lpCmdLine,
    _In_ int nCmdShow)
{
    UNREFERENCED_PARAMETER(hPrevInstance);
    UNREFERENCED_PARAMETER(lpCmdLine);

    // Инициализация GDI+
    GdiplusStartupInput gdiplusStartupInput;
    GdiplusStartup(&gdiplusToken, &gdiplusStartupInput, NULL);

    // Загрузка строк
    LoadStringW(hInstance, IDS_APP_TITLE, szTitle, MAX_LOADSTRING);
    LoadStringW(hInstance, IDC_LAB2GDI, szWindowClass, MAX_LOADSTRING);
    MyRegisterClass(hInstance);

    // Создание окна
    if (!InitInstance(hInstance, nCmdShow))
    {
        GdiplusShutdown(gdiplusToken);
        return FALSE;
    }

    HACCEL hAccelTable = LoadAccelerators(hInstance, MAKEINTRESOURCE(IDC_LAB2GDI));
    MSG msg;

    // Главный цикл сообщений
    while (GetMessage(&msg, nullptr, 0, 0))
    {
        if (!TranslateAccelerator(msg.hwnd, hAccelTable, &msg))
        {
            TranslateMessage(&msg);
            DispatchMessage(&msg);
        }
    }

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
    wcex.hIcon = LoadIcon(hInstance, MAKEINTRESOURCE(IDI_LAB2GDI));
    wcex.hCursor = LoadCursor(nullptr, IDC_ARROW);
    wcex.hbrBackground = (HBRUSH)(COLOR_WINDOW + 1);
    wcex.lpszMenuName = MAKEINTRESOURCEW(IDC_LAB2GDI);
    wcex.lpszClassName = szWindowClass;
    wcex.hIconSm = LoadIcon(wcex.hInstance, MAKEINTRESOURCE(IDI_SMALL));

    return RegisterClassExW(&wcex);
}

// Создание окна
BOOL InitInstance(HINSTANCE hInstance, int nCmdShow)
{
    hInst = hInstance;
    HWND hWnd = CreateWindowW(szWindowClass, L"Графический редактор", WS_OVERLAPPEDWINDOW,
        CW_USEDEFAULT, 0, 800, 600, nullptr, nullptr, hInstance, nullptr);

    if (!hWnd) return FALSE;

    ShowWindow(hWnd, nCmdShow);
    UpdateWindow(hWnd);
    return TRUE;
}

// Главная оконная процедура
LRESULT CALLBACK WndProc(HWND hWnd, UINT message, WPARAM wParam, LPARAM lParam)
{
    switch (message)
    {
    case WM_COMMAND:
    {
        int wmId = LOWORD(wParam);
        switch (wmId)
        {
        case IDM_ABOUT:
            DialogBox(hInst, MAKEINTRESOURCE(IDD_ABOUTBOX), hWnd, About);
            break;
        case IDM_EXIT:
            DestroyWindow(hWnd);
            break;

            // Команды инструментов
        case 1001: currentTool = 0; break; // Карандаш
        case 1002: currentTool = 1; break; // Прямоугольник  
        case 1003: currentTool = 2; break; // Эллипс
        case 1004: currentTool = 3; break; // Ластик

            // Команды толщины
        case 1011: currentThickness = 1; break;
        case 1012: currentThickness = 3; break;
        case 1013: currentThickness = 5; break;

            // Выбор цвета
        case 1021:
        {
            CHOOSECOLOR cc = {};
            static COLORREF customColors[16] = {};
            cc.lStructSize = sizeof(cc);
            cc.hwndOwner = hWnd;
            cc.lpCustColors = customColors;
            cc.rgbResult = currentColor;
            cc.Flags = CC_FULLOPEN | CC_RGBINIT;

            if (ChooseColor(&cc))
            {
                currentColor = cc.rgbResult;
            }
        }
        break;

        // Сохранение
        case 1031:
        {
            OPENFILENAME ofn = {};
            WCHAR filename[MAX_PATH] = L"";

            ofn.lStructSize = sizeof(ofn);
            ofn.hwndOwner = hWnd;
            ofn.lpstrFilter = L"BMP Files\0*.bmp\0All Files\0*.*\0";
            ofn.lpstrFile = filename;
            ofn.nMaxFile = MAX_PATH;
            ofn.Flags = OFN_EXPLORER | OFN_PATHMUSTEXIST | OFN_HIDEREADONLY | OFN_OVERWRITEPROMPT;
            ofn.lpstrDefExt = L"bmp";

            if (GetSaveFileName(&ofn))
            {
                // Получаем контекст устройства
                HDC hdc = GetDC(hWnd);
                RECT rect;
                GetClientRect(hWnd, &rect);

                // Создаем bitmap в памяти
                HDC memDC = CreateCompatibleDC(hdc);
                HBITMAP hBitmap = CreateCompatibleBitmap(hdc, rect.right, rect.bottom);
                HBITMAP hOldBitmap = (HBITMAP)SelectObject(memDC, hBitmap);

                // Заливаем белым
                HBRUSH whiteBrush = CreateSolidBrush(RGB(255, 255, 255));
                FillRect(memDC, &rect, whiteBrush);
                DeleteObject(whiteBrush);

                // Рисуем все объекты
                for (const auto& obj : drawings)
                {
                    DrawObject(memDC, obj);
                }

                // Сохраняем через GDI+
                Gdiplus::Bitmap bitmap(hBitmap, NULL);
                CLSID clsidBmp;
                if (GetEncoderClsid(L"image/bmp", &clsidBmp) != -1)
                {
                    bitmap.Save(filename, &clsidBmp, NULL);
                }

                // Очистка
                SelectObject(memDC, hOldBitmap);
                DeleteObject(hBitmap);
                DeleteDC(memDC);
                ReleaseDC(hWnd, hdc);
            }
        }
        break;

        default:
            return DefWindowProc(hWnd, message, wParam, lParam);
        }
    }
    break;

    case WM_LBUTTONDOWN:
        isDrawing = true;
        startX = GET_X_LPARAM(lParam);
        startY = GET_Y_LPARAM(lParam);
        prevX = startX;
        prevY = startY;

        if (currentTool == 3) // Ластик
        {
            AddDrawingObject(0, startX, startY, startX, startY);
        }
        break;

    case WM_MOUSEMOVE:
        if (isDrawing && (wParam & MK_LBUTTON))
        {
            int currentX = GET_X_LPARAM(lParam);
            int currentY = GET_Y_LPARAM(lParam);

            switch (currentTool)
            {
            case 0: // Карандаш
                AddDrawingObject(0, prevX, prevY, currentX, currentY);
                prevX = currentX;
                prevY = currentY;
                break;

            case 3: // Ластик
            {
                DrawingObject eraser = { 0, prevX, prevY, currentX, currentY, currentThickness * 2, RGB(255, 255, 255) };
                drawings.push_back(eraser);
                prevX = currentX;
                prevY = currentY;
            }
            break;

            case 1: // Прямоугольник
            case 2: // Эллипс
                if (!drawings.empty() && drawings.back().type == currentTool)
                {
                    drawings.back().endX = currentX;
                    drawings.back().endY = currentY;
                }
                else
                {
                    AddDrawingObject(currentTool, startX, startY, currentX, currentY);
                }
                break;
            }

            InvalidateRect(hWnd, NULL, TRUE);
        }
        break;

    case WM_LBUTTONUP:
        isDrawing = false;
        if (currentTool == 1 || currentTool == 2)
        {
            int endX = GET_X_LPARAM(lParam);
            int endY = GET_Y_LPARAM(lParam);

            if (!drawings.empty() && drawings.back().type == currentTool)
            {
                drawings.pop_back();
            }
            AddDrawingObject(currentTool, startX, startY, endX, endY);
        }
        break;

    case WM_PAINT:
    {
        PAINTSTRUCT ps;
        HDC hdc = BeginPaint(hWnd, &ps);

        // Создаем Graphics объект
        Gdiplus::Graphics graphics(hdc);

        // Белый фон
        Gdiplus::SolidBrush whiteBrush(Gdiplus::Color(255, 255, 255, 255));
        RECT rect;
        GetClientRect(hWnd, &rect);
        graphics.FillRectangle(&whiteBrush, rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top);

        // Рисуем все объекты
        for (const auto& obj : drawings)
        {
            DrawObject(hdc, obj);
        }

        EndPaint(hWnd, &ps);
    }
    break;

    case WM_CREATE:
    {
        // Создаем меню
        HMENU hMenu = CreateMenu();

        // Меню Инструменты
        HMENU hToolsMenu = CreatePopupMenu();
        AppendMenuW(hToolsMenu, MF_STRING, 1001, L"Карандаш");
        AppendMenuW(hToolsMenu, MF_STRING, 1002, L"Прямоугольник");
        AppendMenuW(hToolsMenu, MF_STRING, 1003, L"Эллипс");
        AppendMenuW(hToolsMenu, MF_STRING, 1004, L"Ластик");
        AppendMenuW(hMenu, MF_POPUP, (UINT_PTR)hToolsMenu, L"Инструменты");

        // Меню Толщина
        HMENU hThicknessMenu = CreatePopupMenu();
        AppendMenuW(hThicknessMenu, MF_STRING, 1011, L"Тонкий (1px)");
        AppendMenuW(hThicknessMenu, MF_STRING, 1012, L"Средний (3px)");
        AppendMenuW(hThicknessMenu, MF_STRING, 1013, L"Толстый (5px)");
        AppendMenuW(hMenu, MF_POPUP, (UINT_PTR)hThicknessMenu, L"Толщина");

        // Меню Цвет
        HMENU hColorMenu = CreatePopupMenu();
        AppendMenuW(hColorMenu, MF_STRING, 1021, L"Выбрать цвет...");
        AppendMenuW(hMenu, MF_POPUP, (UINT_PTR)hColorMenu, L"Цвет");

        // Меню Файл
        HMENU hFileMenu = CreatePopupMenu();
        AppendMenuW(hFileMenu, MF_STRING, 1031, L"Сохранить как BMP...");
        AppendMenuW(hFileMenu, MF_SEPARATOR, 0, NULL);
        AppendMenuW(hFileMenu, MF_STRING, IDM_EXIT, L"Выход");
        AppendMenuW(hMenu, MF_POPUP, (UINT_PTR)hFileMenu, L"Файл");

        SetMenu(hWnd, hMenu);
    }
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
    Gdiplus::Graphics graphics(hdc);

    // Создаем перо
    Gdiplus::Color penColor(obj.color);
    Gdiplus::Pen pen(penColor, (Gdiplus::REAL)obj.thickness);

    switch (obj.type)
    {
    case 0: // Линия
        graphics.DrawLine(&pen, obj.startX, obj.startY, obj.endX, obj.endY);
        break;

    case 1: // Прямоугольник
    {
        int x = min(obj.startX, obj.endX);
        int y = min(obj.startY, obj.endY);
        int width = abs(obj.endX - obj.startX);
        int height = abs(obj.endY - obj.startY);
        graphics.DrawRectangle(&pen, x, y, width, height);
    }
    break;

    case 2: // Эллипс
    {
        int x = min(obj.startX, obj.endX);
        int y = min(obj.startY, obj.startY);
        int width = abs(obj.endX - obj.startX);
        int height = abs(obj.endY - obj.startY);
        graphics.DrawEllipse(&pen, x, y, width, height);
    }
    break;
    }
}

// Добавление объекта в историю
void AddDrawingObject(int type, int sx, int sy, int ex, int ey)
{
    DrawingObject newObj = { type, sx, sy, ex, ey, currentThickness,
                           (type == 3) ? RGB(255, 255, 255) : currentColor };
    drawings.push_back(newObj);
}

// Функция для получения CLSID кодера
int GetEncoderClsid(const WCHAR* format, CLSID* pClsid)
{
    UINT num = 0;
    UINT size = 0;

    Gdiplus::GetImageEncodersSize(&num, &size);
    if (size == 0) return -1;

    Gdiplus::ImageCodecInfo* pImageCodecInfo = (Gdiplus::ImageCodecInfo*)malloc(size);
    if (pImageCodecInfo == NULL) return -1;

    Gdiplus::GetImageEncoders(num, size, pImageCodecInfo);

    for (UINT j = 0; j < num; ++j)
    {
        if (wcscmp(pImageCodecInfo[j].MimeType, format) == 0)
        {
            *pClsid = pImageCodecInfo[j].Clsid;
            free(pImageCodecInfo);
            return j;
        }
    }

    free(pImageCodecInfo);
    return -1;
}

// Окно "О программе"
INT_PTR CALLBACK About(HWND hDlg, UINT message, WPARAM wParam, LPARAM lParam)
{
    UNREFERENCED_PARAMETER(lParam);
    switch (message)
    {
    case WM_INITDIALOG:
        return (INT_PTR)TRUE;

    case WM_COMMAND:
        if (LOWORD(wParam) == IDOK || LOWORD(wParam) == IDCANCEL)
        {
            EndDialog(hDlg, LOWORD(wParam));
            return (INT_PTR)TRUE;
        }
        break;
    }
    return (INT_PTR)FALSE;
}