# Практична робота. Утиліта аналізу телеметрії сенсорів комп'ютерної мережі

### <div align="right"> *Варіант 1*</div>

### <div align="right">Виконав: Яцентюк Євгеній, група: КІ-24-1</div>
<div align="right">
  <a href="https://github.com/kefir4ikk"><b>GitHub</b></a>
</div>

---

Консольна утиліта мовою Python читає текстовий журнал телеметрії, перевіряє
кожен запис, розшифровує 16-бітний регістр стану побітовою арифметикою та
формує підсумковий звіт. Зовнішніх залежностей немає: лише стандартна
бібліотека (Python 3.9+; перевірено на 3.9, 3.10, 3.11, 3.12, 3.13).

## Параметри варіанта 1

| Параметр | Значення |
|---|---|
| Формат запису | `ВУЗОЛ;0xRRRR;значення;РРРР-ММ-ДДTГГ:ХХ:СС` |
| Типи сенсорів | `TMP` температура (°C), `FAN` вентилятор (об/хв), `VLT` напруга (В) |
| Регістр стану | біти 0–7 прапорці, 8–11 зарезервовано (=0), 12–15 якість |
| Критичні прапорці | OVER_TEMP, UNDER_VOLTAGE, OVER_VOLTAGE, FAN_FAILURE, SENSOR_FAULT |
| Попередження | LINK_DOWN, CRC_ERROR, WATCHDOG_RESET |

## Підготовка середовища (PowerShell, VS Code)

```powershell
# 1. відкрити в VS Code корінь проєкту (папка, де лежать telemetry_monitor/, data/, tests/)
#    назва самої папки може бути будь-якою
cd "шлях\до\кореня\проєкту"

# 2. активувати середовище (підійде Python 3.9 або новіший)
conda activate ce_lab_env
python --version

# 3. лише для перевірки стилю (за потреби)
python -m pip install flake8
```

> **Кирилиця в PowerShell.** Якщо вивід передають по конвеєру (`| Select-Object ...`,
> `| more`) або читають файл звіту, Windows може показати «кракозябри».
> Один раз у сеансі виконайте:
>
> ```powershell
> $env:PYTHONUTF8 = "1"
> [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
> ```
>
> Звіт у файлі завжди записується в UTF-8; читати його: `Get-Content out/report.txt -Encoding UTF8`.

> Модуль запускається за назвою **пакета** `telemetry_monitor`, а не за назвою
> папки проєкту: `python -m telemetry_monitor ...`, а не за назвою папки проєкту.
> Команди виконуються з кореня проєкту, інакше Python не знайде пакет.

## Швидкий старт

```powershell
# звіт у консоль
python -m telemetry_monitor data/sample_telemetry.log

# звіт у файл (записується атомарно)
python -m telemetry_monitor data/sample_telemetry.log -o out/report.txt

# фільтри: лише напруга, лише критичні показання
python -m telemetry_monitor data/sample_telemetry.log --kind VLT --critical-only

# суворий режим: зупинитися на першому пошкодженому записі
python -m telemetry_monitor data/sample_telemetry.log --strict
echo $LASTEXITCODE
```

Параметри: `-o ФАЙЛ`, `--kind ТИП...`, `--node ВУЗОЛ...`, `--critical-only`,
`--strict`, `--max-error-ratio ЧАСТКА` (за замовчуванням 0.5), `-v`.

## Коди завершення

| Код | Значення |
|---|---|
| 0 | успіх |
| 2 | помилка аргументів |
| 3 | помилка файлової системи (немає журналу, немає прав, звіт не записано) |
| 4 | пошкоджені дані (суворий режим або перевищено `--max-error-ratio`) |
| 70 | внутрішня помилка |

## Тести та перевірки

```powershell
python -m unittest discover -s tests -v
python tools/mutation_check.py     # ручні мутанти: кожен має завалити тести
python -m flake8 .                 # PEP 8
python tools/measure.py            # виміри для теоретичної частини
python tools/generate_sample_log.py   # перегенерувати демонстраційний журнал
```

## Структура каталогу

```text
telemetry_monitor/                      # корінь проєкту
├── .gitignore                          # Правила виключення тимчасових файлів (__pycache__, out/, .vscode/)
├── README.md                           # Короткий опис роботи, параметри варіанта, команди запуску
├── telemetry_monitor/                  # Пакет утиліти
│   ├── __init__.py                     # Публічний інтерфейс пакета та версія
│   ├── __main__.py                     # Точка входу: python -m telemetry_monitor
│   ├── exceptions.py                   # Ієрархія винятків із кодами E1000–E4000
│   ├── flags.py                        # StatusFlags, побітове розшифрування регістра стану
│   ├── sensors.py                      # BaseSensor, TemperatureSensor, FanSensor, VoltageSensor, домішки
│   ├── parser.py                       # RECORD_PATTERN, parse_line, parse_stream
│   ├── storage.py                      # Менеджери контексту LogReader, AtomicWriter, open_report
│   ├── analytics.py                    # Генератор-фільтр filter_records і агрегація aggregate
│   ├── report.py                       # Формування підсумкового звіту
│   └── cli.py                          # Аргументи командного рядка, process_log, main
├── tests/
│   ├── __init__.py                     # Позначає каталог тестів як пакет
│   ├── test_core.py                    # Тести ядра: прапорці, сенсори, шаблон, розбір, аналітика
│   └── test_io.py                      # Тести файлового вводу-виводу, CLI та наскрізний сценарій
├── tools/
│   ├── generate_sample_log.py          # Генератор демонстраційного журналу (seed = 1)
│   ├── measure.py                      # Виміри часу й пам'яті для теоретичної частини
│   └── mutation_check.py               # Ручна мутаційна перевірка тестів
├── data/
│   └── sample_telemetry.log            # Демонстраційний журнал (66 коректних + 8 пошкоджених записів)
└── docs/
    ├── ПР Яцентюк Євгеній КІ 24-1.PDF  # Звіт до практичної роботи
    └── fig/
        ├── modules.png                 # Рис. 1 — модулі пакета та залежності
        ├── classes.png                 # Рис. 2 — ієрархія класів сенсорів
        ├── exc.png                     # Рис. 3 — ієрархія винятків
        ├── dfa.png                     # Рис. 4 — скінченний автомат поля регістра
        └── src/                        # Вихідні файли діаграм Graphviz (.dot)
            ├── modules.dot
            ├── classes.dot
            ├── exc.dot
            └── dfa.dot
```

Каталог `out/` зі звітами створюється під час запуску з `-o out/report.txt` і в репозиторій
не потрапляє (`.gitignore`).
