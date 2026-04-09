#ifndef PLANT_H
#define PLANT_H

#ifdef _WIN32
    #define EXPORT_API __declspec(dllexport)
#else
    #define EXPORT_API
#endif

#ifdef __cplusplus
extern "C" {
#endif

/** @brief Описание состояния объекта управления или исследования. */
typedef double Plant[53];

/** @brief Инициализирует состояние объекта управления или исследования. */
EXPORT_API void plant_init(Plant plant);

/**
 * @brief Считывает показатели объекта исследования.
 * @param kanal Канал измерений.
 * @return Значение показателя.
 */
EXPORT_API double plant_measure(int kanal, Plant plant);

/**
 * @brief Подает управляющее воздействие на объект.
 * @param kanal Канал управления (7..10).
 * @param upr Величина управляющего воздействия.
 * @param plant Массив данных, описывающий состояние объекта.
 */
EXPORT_API void plant_control(int kanal, double upr, Plant plant);

#ifdef __cplusplus
}  /* extern "C" */
#endif

#endif
