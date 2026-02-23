#include "plant.h"

//#include <discpp.h>

#include <cmath>
#include <vector>
#include <iostream>
using namespace std;
using std::vector;

int
main() {
    // Инициализация ОУ.
    Plant plant;
    plant_init(plant);

    // Получение экспериментальных данных.
    const int channel = 64;
    const size_t steps = 100;

    vector<double> xs(steps);
    vector<double> ys(steps);

    for (size_t i = 0; i < steps; i++) {
        xs[i] = i;
        ys[i] = plant_measure(channel, plant);
        cout << ys[i]<< '\t'; //Вывод результатов измерений в консоль
    }
}
