#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <gdiplus.h>
#include <iostream>

using namespace Gdiplus;
#pragma comment(lib, "gdiplus.lib")

int main()
{
    // Инициализация GDI+
    GdiplusStartupInput gdiplusStartupInput;
    ULONG_PTR gdiplusToken;
    GdiplusStartup(&gdiplusToken, &gdiplusStartupInput, NULL);

    std::cout << "GDI+ успешно инициализирован!" << std::endl;

    // Здесь можно тестировать функции GDI+

    GdiplusShutdown(gdiplusToken);
    return 0;
}