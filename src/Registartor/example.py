from Plant_API import Plant

if __name__ == '__main__':
    plant = Plant()
    channel = 3
    values = []

    for i in range(100):
        values.append(plant.measure(channel))

    print(values)