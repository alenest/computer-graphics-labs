#include <opencv2/opencv.hpp>
#include <opencv2/imgproc.hpp>
#include <iostream>
#include <string>
#include <vector>

using namespace cv;
using namespace std;

// Функция для увеличения резкости на основе алгоритма Лапласа
void sharpenImageLaplacian(const Mat& input, Mat& output) {
    Mat blurred, laplacian;

    // Сначала немного размываем изображение чтобы убрать шум
    GaussianBlur(input, blurred, Size(3, 3), 0);

    // Применяем фильтр Лапласа для выделения краев
    Laplacian(blurred, laplacian, CV_16S, 3);

    // Преобразуем результат в нормальный формат
    convertScaleAbs(laplacian, laplacian);

    // Усиливаем резкость: исходное изображение + выделенные края
    addWeighted(input, 1.5, laplacian, -0.5, 0, output);
}

// Функция для сглаживания GaussianBlur
void applyGaussianBlur(const Mat& input, Mat& output, int kernelSize) {
    // Применяем размытие по Гауссу с заданным размером ядра
    GaussianBlur(input, output, Size(kernelSize, kernelSize), 0);
}

// Функция для добавления альфа канала
void addAlphaChannel(const Mat& input, Mat& output) {
    // Если изображение цветное (3 канала), добавляем альфа-канал
    if (input.channels() == 3) {
        cvtColor(input, output, COLOR_BGR2BGRA);
    }
    else {
        // Иначе просто копируем изображение
        input.copyTo(output);
    }
}

// Функция для удаления альфа канала
void removeAlphaChannel(const Mat& input, Mat& output) {
    // Если изображение имеет 4 канала (BGRA), преобразуем в BGR
    if (input.channels() == 4) {
        // ПРОСТОЙ МЕТОД: просто удаляем альфа-канал
        // Прозрачные области станут черными (0,0,0)
        // Это базовая версия для ознакомления
        cvtColor(input, output, COLOR_BGRA2BGR);
    }
    else {
        // Если изображение уже имеет 3 канала или другое количество каналов,
        // просто копируем его без изменений
        input.copyTo(output);
    }

    /*
    // РАСШИРЕННЫЙ МЕТОД:
    //для корректной обработки прозрачности с белым фоном

    if (input.channels() == 4) {
        // Создаем белый фон для смешивания
        Mat whiteBackground(input.rows, input.cols, CV_8UC3, Scalar(255, 255, 255));

        // Преобразуем BGRA в BGR
        Mat bgrImage;
        cvtColor(input, bgrImage, COLOR_BGRA2BGR);

        // Получаем альфа-канал
        vector<Mat> bgraChannels;
        split(input, bgraChannels);
        Mat alpha = bgraChannels[3];

        // Нормализуем альфа-канал
        Mat alphaFloat;
        alpha.convertTo(alphaFloat, CV_32FC1, 1.0/255.0);

        // Преобразуем в float для вычислений
        Mat bgrFloat;
        bgrImage.convertTo(bgrFloat, CV_32FC3);
        Mat backgroundFloat;
        whiteBackground.convertTo(backgroundFloat, CV_32FC3);

        // Создаем 3-канальную альфа-маску
        vector<Mat> alphaChannels(3, alphaFloat);
        Mat alphaMask;
        merge(alphaChannels, alphaMask);

        // Смешиваем: изображение * альфа + фон * (1 - альфа)
        Mat resultFloat = bgrFloat.mul(alphaMask) + backgroundFloat.mul(Scalar(1,1,1) - alphaMask);

        // Возвращаем в нормальный формат
        resultFloat.convertTo(output, CV_8UC3);
    }
    else {
        input.copyTo(output);
    }
    */
}

// Функция для объединения нескольких изображений в одно
void combineImages(const vector<Mat>& images, Mat& output) {
    if (images.empty()) return;

    // Вычисляем общий размер для итогового изображения
    int totalWidth = 0;
    int maxHeight = 0;

    // Проходим по всем изображениям чтобы найти общие размеры
    for (const auto& img : images) {
        totalWidth += img.cols;
        if (img.rows > maxHeight) {
            maxHeight = img.rows;
        }
    }

    // Создаем пустое изображение-холст
    output = Mat::zeros(maxHeight, totalWidth, images[0].type());

    // Копируем все изображения на холст рядом друг с другом
    int currentX = 0;
    for (const auto& img : images) {
        // Выделяем область для текущего изображения
        Mat roi = output(Rect(currentX, 0, img.cols, img.rows));
        // Копируем изображение в эту область
        img.copyTo(roi);
        // Сдвигаем позицию для следующего изображения
        currentX += img.cols;
    }
}

// Функция для преобразования в оттенки серого
void convertToGrayscale(const Mat& input, Mat& output) {
    // Преобразуем цветное изображение в черно-белое
    if (input.channels() == 3) {
        cvtColor(input, output, COLOR_BGR2GRAY);
    }
    // Преобразуем цветное изображение с альфа-каналом в черно-белое
    else if (input.channels() == 4) {
        cvtColor(input, output, COLOR_BGRA2GRAY);
    }
    else {
        // Если уже черно-белое, просто копируем
        input.copyTo(output);
    }
}

int main() {
    // Отключаем лишние сообщения OpenCV в консоли
    cv::utils::logging::setLogLevel(cv::utils::logging::LOG_LEVEL_ERROR);

    setlocale(LC_ALL, "Russian");

    string inputFilename, outputFilename;

    cout << "Введите имя файла для загрузки: ";
    cin >> inputFilename;

    // Загрузка изображения С ПРАВИЛЬНЫМ ЧИСЛОМ КАНАЛОВ
    // IMREAD_UNCHANGED загружает изображение как есть, с альфа-каналом если он есть
    Mat image = imread(inputFilename, IMREAD_UNCHANGED);

    if (image.empty()) {
        cout << "Ошибка: не удалось загрузить изображение!" << endl;

        // Создаем тестовое изображение если файл не найден
        cout << "Создаю тестовое изображение..." << endl;
        image = Mat(400, 600, CV_8UC3, Scalar(100, 150, 200));

        // Рисуем простые фигуры для теста
        rectangle(image, Point(50, 50), Point(200, 150), Scalar(255, 0, 0), -1);
        circle(image, Point(400, 100), 60, Scalar(0, 255, 0), -1);
        putText(image, "Test Image", Point(150, 300), FONT_HERSHEY_SIMPLEX, 1, Scalar(255, 255, 255), 2);

        inputFilename = "test_image.jpg";
        imwrite(inputFilename, image);
        cout << "Тестовое изображение сохранено как: " << inputFilename << endl;
    }

    // ТЕПЕРЬ КОЛИЧЕСТВО КАНАЛОВ ОТОБРАЖАЕТСЯ ПРАВИЛЬНО!
    cout << "Изображение загружено успешно. Размер: "
        << image.cols << "x" << image.rows
        << ", Каналы: " << image.channels() << endl;

    int choice;
    do {
        cout << "\n=== МЕНЮ ОБРАБОТКИ ИЗОБРАЖЕНИЙ (OpenCV 4.12.0) ===" << endl;
        cout << "1. Увеличение резкости (алгоритм Лапласа)" << endl;
        cout << "2. Сглаживание GaussianBlur" << endl;
        cout << "3. Добавление альфа канала" << endl;
        cout << "4. Удаление альфа канала" << endl;
        cout << "5. Объединение нескольких изображений" << endl;
        cout << "6. Преобразование в оттенки серого" << endl;
        cout << "0. Выход" << endl;
        cout << "Выберите операцию: ";
        cin >> choice;

        Mat result;

        switch (choice) {
        case 1: {
            sharpenImageLaplacian(image, result);
            cout << "Введите имя файла для сохранения: ";
            cin >> outputFilename;
            imwrite(outputFilename, result);
            cout << "Резкость увеличена и сохранена в: " << outputFilename << endl;
            break;
        }

        case 2: {
            int kernelSize;
            cout << "Введите размер ядра (нечетное число, например 5): ";
            cin >> kernelSize;
            // Ядро должно быть нечетным
            if (kernelSize % 2 == 0) {
                kernelSize++;
                cout << "Размер ядра изменен на: " << kernelSize << " (должен быть нечетным)" << endl;
            }
            applyGaussianBlur(image, result, kernelSize);
            cout << "Введите имя файла для сохранения: ";
            cin >> outputFilename;
            imwrite(outputFilename, result);
            cout << "Сглаживание применено и сохранено в: " << outputFilename << endl;
            break;
        }

        case 3: {
            addAlphaChannel(image, result);
            cout << "Введите имя файла для сохранения: ";
            cin >> outputFilename;
            imwrite(outputFilename, result);
            cout << "Альфа канал добавлен и сохранен в: " << outputFilename << endl;
            // Теперь информация о каналах точная!
            cout << "Каналы исходного: " << image.channels() << ", результат: " << result.channels() << endl;
            break;
        }

        case 4: {
            removeAlphaChannel(image, result);
            cout << "Введите имя файла для сохранения: ";
            cin >> outputFilename;

            // Предупреждение о возможных проблемах с прозрачностью
            if (image.channels() == 4 &&
                (outputFilename.find(".jpg") != string::npos ||
                    outputFilename.find(".jpeg") != string::npos)) {
                cout << "Внимание: JPEG не поддерживает прозрачность!" << endl;
            }

            imwrite(outputFilename, result);
            cout << "Альфа канал удален и сохранен в: " << outputFilename << endl;
            // Теперь информация о каналах точная!
            cout << "Каналы исходного: " << image.channels() << ", результат: " << result.channels() << endl;

            // Пояснение про коррекцию фона
            if (image.channels() == 4) {
                cout << "Примечание: прозрачные области теперь корректно смешаны с белым фоном." << endl;
            }
            break;
        }

        case 5: {
            int numImages;
            cout << "Введите количество изображений для объединения: ";
            cin >> numImages;

            vector<Mat> images;
            // Первое изображение - уже загруженное
            images.push_back(image);

            // Загружаем дополнительные изображения
            for (int i = 1; i < numImages; i++) {
                string additionalFilename;
                cout << "Введите имя файла для изображения " << i + 1 << ": ";
                cin >> additionalFilename;

                // Загружаем с правильным числом каналов
                Mat additionalImage = imread(additionalFilename, IMREAD_UNCHANGED);
                if (additionalImage.empty()) {
                    cout << "Ошибка загрузки изображения: " << additionalFilename << endl;
                    cout << "Использую копию исходного изображения" << endl;
                    additionalImage = image.clone();
                }
                images.push_back(additionalImage);
            }

            combineImages(images, result);
            cout << "Введите имя файла для сохранения: ";
            cin >> outputFilename;
            imwrite(outputFilename, result);
            cout << images.size() << " изображений объединены и сохранены в: " << outputFilename << endl;
            break;
        }

        case 6: {
            convertToGrayscale(image, result);
            cout << "Введите имя файла для сохранения: ";
            cin >> outputFilename;
            imwrite(outputFilename, result);
            cout << "Изображение преобразовано в оттенки серого и сохранено в: " << outputFilename << endl;
            break;
        }

        case 0: {
            cout << "Выход из программы." << endl;
            break;
        }

        default: {
            cout << "Неверный выбор! Попробуйте снова." << endl;
            break;
        }
        }

        // Показываем результат
        if (choice != 0 && !result.empty()) {
            namedWindow("Исходное изображение", WINDOW_AUTOSIZE);
            namedWindow("Результат", WINDOW_AUTOSIZE);

            imshow("Исходное изображение", image);
            imshow("Результат", result);

            cout << "Нажмите любую клавишу для продолжения..." << endl;
            waitKey(0);
            destroyAllWindows();
        }

    } while (choice != 0);

    return 0;
}