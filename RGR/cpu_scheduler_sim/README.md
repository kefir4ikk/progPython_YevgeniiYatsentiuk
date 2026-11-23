# Розрахунково-графічна робота. Симуляція диспетчеризації черги завдань процесора за алгоритмами FIFO та Round Robin

### <div align="right">Виконав: Яцентюк Євгеній, група: КІ-24-1</div>
<div align="right">
  <a href="https://github.com/kefir4ikk"><b>GitHub</b></a>
</div>

---

## Швидкий старт

```bash
python cli_main.py run --input data/workload_basic.txt --algo rr --quantum 4 --gantt
python cli_main.py run --input data/workload_basic.txt --algo fifo --json out/report.json --csv out/report.csv
python cli_main.py compare --input data/workload_mixed.txt --quanta 1,2,4,8 --switch-cost 1
python cli_main.py generate --count 1000 --output data/big.txt --seed 5
python cli_main.py benchmark --sizes 100,1000,10000 --quantum 4 --repeats 3 --csv out/bench.csv
python cli_main.py --help
```

Також працює `python -m cpu_scheduler ...`.

## Формат вхідного файлу

Один рядок — один процес, коментарі після `#`, службовий заголовок `pid,arrival,burst` пропускається:

```
P1 arrival=0 burst=24
P2, 0, 3
P3; 0; 3
```

## Коди завершення

| Код | Значення |
|-----|----------|
| 0 | успішно |
| 1 | помилка аргументів командного рядка |
| 2 | помилка вхідних даних (файл, формат рядка) |
| 3 | некоректні параметри (квант, вартість перемикання) |
| 4 | збій симуляції (перевищено ліміт інтервалів) |
| 5 | помилка збереження звітів |
| 6 | інша помилка домену |
| 70 | внутрішня помилка програми |

## Тести та перевірки

```bash
python -m unittest discover -s tests -t .      # 61 тест
python tools/mutation_check.py                 # мутаційна перевірка (10 дефектів)
python tools/quantum_study.py                  # вплив кванта часу -> results/quantum_study.csv
python tools/make_figures.py                   # рисунки для записки
python tools/collect_metrics.py                # метрики коду, аварійні сценарії
```


## Структура каталогу

```
cpu_scheduler_sim/
├── .vscode/
│   └── settings.json            # Налаштування VS Code (менеджер середовищ Conda)
├── cpu_scheduler/               # Основний пакет програми
│   ├── __init__.py              # Публічний інтерфейс пакета (__all__)
│   ├── __main__.py              # Запуск пакета: python -m cpu_scheduler
│   ├── benchmark.py             # Генерація навантажень, вимірювання часу, оцінка складності
│   ├── cli.py                   # Командний інтерфейс на sys.argv (run, compare, benchmark, generate)
│   ├── exceptions.py            # Ієрархія власних винятків із кодами помилок
│   ├── models.py                # Process, Workload, Segment, ProcessResult, ScheduleResult
│   ├── parser.py                # Розбір вхідного файлу (регулярні вирази)
│   ├── reporting.py             # Текстові таблиці, зведення та діаграма Ганта
│   ├── schedulers.py            # BaseScheduler (ABC), FIFOScheduler, RoundRobinScheduler
│   └── storage.py               # Збереження звітів у JSON і CSV
├── data/                        # Приклади вхідних файлів
│   ├── bad_workload.txt         # Файл з помилкою (перевірка обробки винятків)
│   ├── workload_basic.txt       # Базове навантаження: 3 процеси
│   └── workload_mixed.txt       # Змішане навантаження з простоями: 6 процесів
├── docs/
│   └── fig/                     # Схеми та графіки для пояснювальної записки (PNG)
│       └── src/                 # Вихідні Graphviz-описи схем (.dot)
├── out/                         # Звіти, створені під час запуску (report.json, report.csv)
├── results/                     # Результати експериментів
│   ├── benchmark.csv            # Заміри часу FIFO та Round Robin
│   ├── metrics.json             # Метрики коду, тестів і покриття
│   ├── mutation.json            # Підсумок мутаційної перевірки
│   └── quantum_study.csv        # Вплив кванта часу на показники
├── tests/                       # Модульні тести (unittest)
│   ├── __init__.py
│   ├── reference_sim.py         # Незалежний покроковий еталонний симулятор
│   ├── test_benchmark.py        # Тести модуля benchmark
│   ├── test_cli.py              # Тести командного інтерфейсу та кодів завершення
│   ├── test_models.py           # Тести моделей і валідації
│   ├── test_parser.py           # Тести розбору вхідних файлів
│   ├── test_schedulers.py       # Тести планувальників і звірка з еталоном
│   └── test_storage.py          # Тести збереження JSON і CSV
├── tools/                       # Допоміжні скрипти для експериментів
│   ├── collect_metrics.py       # Збір метрик коду та аварійних сценаріїв
│   ├── make_figures.py          # Побудова рисунків для записки
│   ├── mutation_check.py        # Мутаційна перевірка тестів
│   └── quantum_study.py         # Дослідження впливу кванта часу
├── .gitignore                   # Виключення тимчасових та системних файлів
├── cli_main.py                  # Точка входу: python cli_main.py ...
└── README.md                    # Опис проєкту та інструкція запуску

```
