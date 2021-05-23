import numpy
import tools
import numpy.fft as fft
import matplotlib.pyplot as plt

class GaussianModPlaneWave:
    ''' Класс с уравнением плоской волны для модулированного гауссова сигнала в дискретном виде
    d - определяет задержку сигнала.
    w - определяет ширину сигнала.
    Nl - количество ячеек на длину волны.
    Sc - число Куранта.
    eps - относительная диэлектрическая проницаемость среды, в которой расположен источник.
    mu - относительная магнитная проницаемость среды, в которой расположен источник.
    '''

    def __init__(self, d, w, Nl, eps=1.0, mu=1.0, Sc=1.0):
        self.d = d
        self.w = w
        self.Nl = Nl
        self.Sc = Sc
        self.eps = eps
        self.mu = mu

    def getField(self, m, q):
        '''
        Расчет поля E в дискретной точке пространства m
        в дискретный момент времени q
        '''
        return (numpy.sin(2 * numpy.pi / self.Nl * (q * self.Sc - m * numpy.sqrt(self.eps * self.mu))) *
                numpy.exp(-(((q - m * numpy.sqrt(self.eps * self.mu) / self.Sc) - self.d) / self.w) ** 2))

if __name__ == '__main__':
    # Волновое сопротивление свободного пространства
    W0 = 120.0 * numpy.pi

    # Число Куранта
    Sc = 1.0

    #Скорость света
    c = 3e8

    # Время расчета в отсчетах
    maxTime = 2000

    #Размер области моделирования в метрах
    X = 0.5

    #Размер ячейки разбиения
    dx = 0.5e-3

    # Размер области моделирования в отсчетах
    maxSize = int(X / dx)

    #Шаг дискретизации по времени
    dt = Sc * dx / c

    # Положение источника в отсчетах
    sourcePos = 50

    # Датчики для регистрации поля
    probesPos = [25,75]
    probes = [tools.Probe(pos, maxTime) for pos in probesPos]

    #1й слой диэлектрика
    eps1 = 3.5
    d1 = 0.01
    layer_1 = int(maxSize / 2) + int(d1 / dx)

    #2й слой диэлектрика
    eps2 = 4.8
    d2 = 0.03
    layer_2 = layer_1 + int(d2 / dx)

    #3й слой диэлектрика
    eps3 = 6.5

    # Параметры среды
    # Диэлектрическая проницаемость
    eps = numpy.ones(maxSize)
    eps[int(maxSize/2):layer_1] = eps1
    eps[layer_1:layer_2] = eps2
    eps[layer_2:] = eps3
    
    # Магнитная проницаемость
    mu = numpy.ones(maxSize - 1)

    Ez = numpy.zeros(maxSize)
    Hy = numpy.zeros(maxSize - 1)

    source = GaussianModPlaneWave(100.0, 30.0, 25.0, eps[sourcePos], mu[sourcePos])
    
    # Параметры отображения поля E
    display_field = Ez
    display_ylabel = 'Ez, В/м'
    display_ymin = -1.1
    display_ymax = 1.1

    # Создание экземпляра класса для отображения
    # распределения поля в пространстве
    display = tools.AnimateFieldDisplay(maxSize,
                                        display_ymin, display_ymax,
                                        display_ylabel,dx)

    display.activate()
    display.drawProbes(probesPos)
    display.drawSources([sourcePos])
    display.drawBoundary(int(maxSize / 2))
    display.drawBoundary(layer_1)
    display.drawBoundary(layer_2)

    for q in range(maxTime):
        # Расчет компоненты поля H
        Hy = Hy + (Ez[1:] - Ez[:-1]) * Sc / (W0 * mu)

        # Источник возбуждения с использованием метода
        # Total Field / Scattered Field
        Hy[sourcePos - 1] -= Sc / (W0 * mu[sourcePos - 1]) * source.getField(0, q)

        # Граничные условия для поля E
        Ez[0] = Ez[1]
        Ez[-1] = Ez[-2]

        # Расчет компоненты поля E
        Hy_shift = Hy[:-1]
        Ez[1:-1] = Ez[1:-1] + (Hy[1:] - Hy_shift) * Sc * W0 / eps[1:-1]

        # Источник возбуждения с использованием метода
        # Total Field / Scattered Field
        Ez[sourcePos] += (Sc / (numpy.sqrt(eps[sourcePos] * mu[sourcePos])) *
                          source.getField(-0.5, q + 0.5))

        # Регистрация поля в датчиках
        for probe in probes:
            probe.addData(Ez, Hy)

        if q % 5 == 0:
            display.updateData(display_field, q)

    display.stop()
    

    # Отображение сигнала, сохраненного в датчиках
    tools.showProbeSignals(probes, -1.1, 1.1, dt)

    # Максимальная и манимальная частоты для отображения
    # графика зависимости коэффициента отражения от частоты
    Fmin = 5e9
    Fmax = 30e9
    
    # Размер массива для ПФ
    size = 2 ** 16

    # Выдедение падающего поля 
    FallField = numpy.zeros(maxTime)
    FallField[:300] = probes[1].E[:300]

    # Нахождение БПФ падающего поля
    FallSpectr = abs(fft.fft(FallField, size))
    FallSpectr = fft.fftshift(FallSpectr)

    # Нахождение БПФ отраженного поля
    ScatteredSpectr = abs(fft.fft(probes[0].E, size))
    ScatteredSpectr = fft.fftshift(ScatteredSpectr)

    # шаг по частоте и определение частотной оси
    df = 1 / (size * dt)
    f = numpy.arange(-(size / 2) * df, (size / 2) * df, df)

    # Построение спектра падающего и рассеянного поля
    plt.figure()
    plt.plot(f * 1e-9, FallSpectr / numpy.max(FallSpectr))
    plt.plot(f * 1e-9, ScatteredSpectr / numpy.max(ScatteredSpectr))
    plt.grid()
    plt.xlim(0, 50e9 * 1e-9)
    plt.xlabel('f, ГГц')
    plt.ylabel('|S/Smax|')
    plt.legend(['Спектр падающего поля', 'Спектр отраженного поля'])

    # Определение коэффициента отражения и построения графика
    plt.figure()
    plt.plot(f * 1e-9, (ScatteredSpectr / FallSpectr))
    plt.xlim(Fmin * 1e-9, Fmax * 1e-9)
    plt.ylim(0, 1)
    plt.grid()
    plt.xlabel('f, ГГц')
    plt.ylabel('|Г|')
    plt.show()

    

