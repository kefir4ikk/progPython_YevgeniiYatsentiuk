"""
Лабораторна робота № 11. Модуль 2. Варіант 2.
Тестовий стенд верифікації інкапсуляції, поліморфізму та перевантаження
dunder-операторів ієрархії CPUKernel -> SIMDKernel.
Освітній компонент: Програмування на Python.
"""

import math
import sys
import time

from hardware_entities import CPUKernel, SIMDKernel

WIDTH = 90


def section(title: str) -> None:
    """Виводить роздільник і заголовок розділу тестового стенду."""
    print("-" * WIDTH)
    print(f"{title:^{WIDTH}}")
    print("-" * WIDTH)


def run_oop_testbench() -> list:
    """Виконує функціональне тестування моделі. Повертає журнал перевірок (опис, результат)."""
    checks: list = []

    def check(description: str, condition: bool) -> None:
        """Реєструє перевірку інваріанта в журналі."""
        checks.append((description, bool(condition)))

    print("=" * WIDTH)
    print(f"{'ТЕСТОВИЙ СТЕНД ООП-МОДЕЛІ ПРОЦЕСОРНИХ ЯДЕР ТА DUNDER-МЕТОДІВ':^{WIDTH}}")
    print("=" * WIDTH)

    # Початкові об'єкти базового та похідного класів
    core_a = CPUKernel("CORE-0", 3.2, 2.5, [35.0, 42.5, 38.0])
    core_b = CPUKernel("CORE-1", 2.8, 3.0, [60.0, 55.5])
    simd_a = SIMDKernel("SIMD-0", 3.0, 2.0, 256, [88.0, 91.5, 95.0, 90.5])
    simd_b = SIMDKernel("SIMD-1", 2.4, 1.5, 512, [70.0, 72.5])

    # 1. __str__ та __repr__
    section("1. СТРОКОВЕ ВІДОБРАЖЕННЯ (__str__ ТА __repr__)")
    for name, obj in (("core_a", core_a), ("core_b", core_b), ("simd_a", simd_a), ("simd_b", simd_b)):
        print(f"  print({name}): {obj}")
    print(f"  repr(core_a): {core_a!r}")
    print(f"  repr(simd_a): {simd_a!r}")
    rebuilt = eval(repr(simd_a))     # repr містить усе потрібне для відтворення об'єкта
    check("eval(repr(obj)) відтворює рівний об'єкт", rebuilt == simd_a)

    # 2. Інкапсуляція, name mangling, валідація сетерів
    section("2. ІНКАПСУЛЯЦІЯ: NAME MANGLING ТА ВАЛІДАЦІЯ (@property)")
    print(f"  Атрибути core_a:  {sorted(vars(core_a))}")
    print(f"  Атрибути simd_a:  {sorted(vars(simd_a))}")
    print(f"  core_a._CPUKernel__ipc = {core_a._CPUKernel__ipc}  (доступ через змінене ім'я)")
    try:
        _ = core_a.__ipc
    except AttributeError as err:
        print(f"  core_a.__ipc -> AttributeError: {err}")
        check("прямий доступ до __ipc заборонений", True)

    core_a.clock_frequency_ghz = 3.6
    print(f"  Частоту core_a змінено на {core_a.clock_frequency_ghz} ГГц через сетер")
    core_a.clock_frequency_ghz = 3.2          # повертаємо початкове значення
    for label, action in (
        ("частота 12.5 ГГц", lambda: setattr(core_a, "clock_frequency_ghz", 12.5)),
        ("частота 'fast'", lambda: setattr(core_a, "clock_frequency_ghz", "fast")),
        ("IPC = -1", lambda: setattr(core_a, "ipc", -1)),
        ("SIMD 192 біт", lambda: setattr(simd_a, "simd_width_bits", 192)),
        ("навантаження 120 %", lambda: core_a.record_load(120.0)),
    ):
        try:
            action()
            check(f"сетер відхилив {label}", False)
        except (ValueError, TypeError) as err:
            print(f"  [ЗАХИСТ СЕТЕРА] {label}: {type(err).__name__}: {err}")
            check(f"сетер відхилив {label}", True)
    try:
        core_a.kernel_id = "HACKED"
    except AttributeError as err:
        print(f"  kernel_id доступний лише для читання: {type(err).__name__}")
        check("kernel_id незмінний (немає сетера)", core_a.kernel_id == "CORE-0")

    # 3. Протокол послідовностей
    section("3. ПРОТОКОЛ ПОСЛІДОВНОСТЕЙ (__len__, __getitem__)")
    print(f"  len(simd_a) = {len(simd_a)}")
    print(f"  simd_a[0] = {simd_a[0]} %,  simd_a[-1] = {simd_a[-1]} %")
    print(f"  Зріз simd_a[1:3] = {simd_a[1:3]}")
    print(f"  Ітерація циклом for: {[load for load in simd_a]}")
    print(f"  Середнє навантаження simd_a: {simd_a.average_load_percent:.2f} %")
    simd_a.record_load(99.0)
    print(f"  Після record_load(99.0): len = {len(simd_a)}, simd_a[-1] = {simd_a[-1]} %")
    try:
        _ = simd_a[10]
    except IndexError as err:
        print(f"  simd_a[10] -> IndexError: {err}")
        check("індекс поза межами дає IndexError", True)
    check("len() збігається з кількістю відліків", len(simd_a) == 5)

    # 4. __add__ та __radd__
    section("4. ПЕРЕВАНТАЖЕННЯ АРИФМЕТИКИ (__add__, __radd__)")
    print(f"  P(core_a) = {core_a.performance_mflops:.0f} MFLOPS,  P(core_b) = {core_b.performance_mflops:.0f} MFLOPS")
    sum_cpu = core_a + core_b
    print(f"  core_a + core_b: {sum_cpu}")
    check("P(a + b) = P(a) + P(b) для скалярних ядер",
          math.isclose(sum_cpu.performance_mflops, core_a.performance_mflops + core_b.performance_mflops))
    print(f"  P(simd_a) = {simd_a.performance_mflops:.0f} MFLOPS,  P(simd_b) = {simd_b.performance_mflops:.0f} MFLOPS")
    sum_simd = simd_a + simd_b
    print(f"  simd_a + simd_b: {sum_simd}")
    check("P(simd_a + simd_b) = P(simd_a) + P(simd_b)",
          math.isclose(sum_simd.performance_mflops, simd_a.performance_mflops + simd_b.performance_mflops))
    mixed = core_a + simd_a
    print(f"  core_a + simd_a: {mixed}")
    cluster_sum = sum([core_a, core_b, simd_a])      # sum() починає з 0: працює __radd__
    print(f"  sum([core_a, core_b, simd_a]): {cluster_sum}")
    check("sum() дає сумарну продуктивність через __radd__",
          math.isclose(cluster_sum.performance_mflops,
                       core_a.performance_mflops + core_b.performance_mflops + simd_a.performance_mflops))
    check("операнди після додавання не змінились", len(core_a) == 3 and core_a.kernel_id == "CORE-0")
    try:
        _ = core_a + 5
    except TypeError as err:
        print(f"  core_a + 5 -> TypeError: {err}")
        check("непідтримуваний операнд дає TypeError", True)

    # 5. __eq__ та __lt__
    section("5. ОПЕРАТОРИ ПОРІВНЯННЯ (__eq__, __lt__)")
    twin = CPUKernel("CORE-0", 3.2, 2.5)
    fake_simd = SIMDKernel("CORE-0", 3.2, 2.5, 128)
    wide_twin = SIMDKernel("SIMD-0", 3.0, 2.0, 512)
    print(f"  core_a == twin (ті самі id, f, IPC):        {core_a == twin}")
    print(f"  core_a == core_b:                           {core_a == core_b}")
    print(f"  core_a != core_b:                           {core_a != core_b}")
    print(f"  core_a == SIMDKernel з тими ж id, f, IPC:   {core_a == fake_simd}")
    print(f"  simd_a == SIMD з іншою розрядністю:         {simd_a == wide_twin}")
    print(f"  core_a == 'CORE-0' (чужий тип):             {core_a == 'CORE-0'}")
    check("рівні за параметрами ядра рівні", core_a == twin)
    check("CPUKernel != SIMDKernel за типом", not (core_a == fake_simd))
    check("SIMD з різною розрядністю не рівні", not (simd_a == wide_twin))
    print(f"  Частоти, ГГц: core_a {core_a.clock_frequency_ghz}, core_b {core_b.clock_frequency_ghz}, "
          f"simd_a {simd_a.clock_frequency_ghz}, simd_b {simd_b.clock_frequency_ghz}")
    print(f"  core_b < core_a ?  {core_b < core_a}")
    print(f"  core_a < core_b ?  {core_a < core_b}")
    print(f"  simd_b < core_b ?  {simd_b < core_b}   (порівняння різних класів ієрархії)")
    print(f"  core_a > core_b ?  {core_a > core_b}   (працює через відображення __lt__)")
    check("__lt__ порівнює за частотою", core_b < core_a and not (core_a < core_b))

    # 6. Поліморфізм та сортування
    section("6. ПОЛІМОРФІЗМ ТА СОРТУВАННЯ КЛАСТЕРА (sorted за тактовою частотою)")
    cluster = [core_a, simd_a, core_b, simd_b]
    for rank, node in enumerate(sorted(cluster), start=1):
        print(f"  Ранг {rank}: {node}")
    print(f"  min(cluster) = {min(cluster).kernel_id},  max(cluster) = {max(cluster).kernel_id}")
    best = max(cluster, key=lambda k: k.performance_mflops)
    print(f"  Найвища продуктивність (а не частота): {best.kernel_id} - {best.performance_mflops:.0f} MFLOPS")
    check("порядок за частотою не збігається з порядком за продуктивністю",
          max(cluster) is not best)
    check("sorted() сортує за зростанням частоти",
          [k.clock_frequency_ghz for k in sorted(cluster)] == [2.4, 2.8, 3.0, 3.2])
    print("  Поліморфний виклик performance_mflops (різні реалізації в класах):")
    for node in cluster:
        print(f"    {type(node).__name__:<10} {node.kernel_id:<7} {node.performance_mflops:>9.0f} MFLOPS")
    check("isinstance(simd_a, CPUKernel) істинне", isinstance(simd_a, CPUKernel))

    # 7. Хешованість
    section("7. ХЕШОВАНІСТЬ ПРИ ПЕРЕВИЗНАЧЕНОМУ __eq__")
    try:
        hash(core_a)
    except TypeError as err:
        print(f"  hash(core_a) -> TypeError: {err}")
        print("  Клас із власним __eq__ без __hash__ стає нехешованим: об'єкти змінні.")
        check("об'єкт із __eq__ без __hash__ нехешований", True)

    # Підсумок перевірок
    passed = sum(1 for _, ok in checks if ok)
    print("=" * WIDTH)
    print(f"{'ПІДСУМОК ПЕРЕВІРОК ІНВАРІАНТІВ':^{WIDTH}}")
    print("-" * WIDTH)
    for description, ok in checks:
        print(f"  [{'OK' if ok else 'ПОМИЛКА'}] {description}")
    print("-" * WIDTH)
    print(f"  Пройдено перевірок: {passed} із {len(checks)}")
    print("=" * WIDTH + "\n")
    return checks


def main() -> None:
    """Головна точка входу лабораторної роботи."""
    t_start = time.perf_counter()
    checks = run_oop_testbench()
    t_elapsed = time.perf_counter() - t_start
    print(f"Час виконання об'єктно-орієнтованого тестування: {t_elapsed * 1000:.3f} мс\n")
    sys.exit(0 if all(ok for _, ok in checks) else 1)


if __name__ == "__main__":
    main()
