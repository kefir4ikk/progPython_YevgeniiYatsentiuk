"""
Лабораторна робота № 10. Варіант 2.
Комплексний конвеєр файлового введення-виведення для моніторингу серверів ЦОД:
обробка CSV (фільтр CPU > 80 %, середній обсяг вільної RAM), бінарна верифікація
образу прошивки за магічною сигнатурою 'NODE' (0x4E4F4445) та персистентна
серіалізація підсумкового стану у JSON.
Освітній компонент: Програмування на Python.
"""

import csv
import json
import os
import sys
import time
from pathlib import Path

# Каталог модуля: файли шукаються поруч зі скриптом незалежно від поточного каталогу терміналу
BASE_DIR = Path(__file__).resolve().parent

# Константа 4-байтної магічної сигнатури бінарного образу (ASCII: 'NODE')
FIRMWARE_MAGIC_HEADER = bytes([0x4E, 0x4F, 0x44, 0x45])
# Розмір заголовка: 4 байти сигнатури + 1 байт Major + 1 байт Minor
FIRMWARE_HEADER_SIZE = 6

# Критерій фільтрації варіанта 2: завантаження процесора вище 80 %
CPU_THRESHOLD_PERCENT = 80.0


def process_csv_telemetry(input_csv_path: Path, output_csv_path: Path) -> dict:
    """
    Зчитує телеметрію серверів через csv.DictReader, відбирає рядки із завантаженням
    CPU вище порога, рахує середній обсяг вільної RAM відібраних серверів та записує
    відібрані рядки у новий CSV-файл через csv.DictWriter.
    Некоректні рядки (нечислові значення, відсутні поля) пропускаються й обліковуються.
    Повертає словник агрегованих метрик.
    """
    if not input_csv_path.exists():
        raise FileNotFoundError(f"Вхідний файл '{input_csv_path.name}' не знайдено.")

    total_rows = 0
    normal_rows = 0
    malformed_rows: list[str] = []
    selected: list[dict] = []

    # Читання вхідного CSV-файлу через менеджер контексту (newline="" вимагається модулем csv)
    with open(input_csv_path, mode="r", encoding="utf-8", newline="") as in_file:
        reader = csv.DictReader(in_file)

        # Нумерація з 2: перший рядок файлу містить заголовки стовпців
        for line_no, row in enumerate(reader, start=2):
            total_rows += 1
            try:
                cpu = float(row["CPU_Usage_Percent"])
                ram_free = float(row["RAM_Free_GB"])
                temperature = float(row["Temperature_C"])
            except (KeyError, ValueError, TypeError):
                # Некоректний рядок не зупиняє конвеєр: фіксуємо номер рядка та сервер
                malformed_rows.append(f"рядок {line_no} ({row.get('Server_ID', '?')})")
                continue

            if cpu > CPU_THRESHOLD_PERCENT:
                selected.append({
                    "Timestamp": row["Timestamp"],
                    "Server_ID": row["Server_ID"],
                    "CPU_Usage_Percent": cpu,
                    "RAM_Free_GB": ram_free,
                    "Temperature_C": temperature,
                    "CPU_Excess_Percent": cpu - CPU_THRESHOLD_PERCENT,
                })
            else:
                normal_rows += 1

    # Запис відібраних даних у новий CSV-файл
    fieldnames = ["Timestamp", "Server_ID", "CPU_Usage_Percent", "RAM_Free_GB",
                  "Temperature_C", "CPU_Excess_Percent"]
    with open(output_csv_path, mode="w", encoding="utf-8", newline="") as out_file:
        writer = csv.DictWriter(out_file, fieldnames=fieldnames)
        writer.writeheader()
        for rec in selected:
            writer.writerow({key: (f"{val:.2f}" if isinstance(val, float) else val)
                             for key, val in rec.items()})

    count = len(selected)
    stats = {
        "total_read_rows": total_rows,
        "malformed_rows_skipped": len(malformed_rows),
        "normal_load_rows": normal_rows,
        "overloaded_rows_saved": count,
        "cpu_threshold_percent": CPU_THRESHOLD_PERCENT,
        "average_free_ram_gb": round(sum(r["RAM_Free_GB"] for r in selected) / count, 4) if count else 0.0,
        "average_cpu_percent": round(sum(r["CPU_Usage_Percent"] for r in selected) / count, 4) if count else 0.0,
        "overloaded_servers": [r["Server_ID"] for r in selected],
    }
    if selected:
        hottest = max(selected, key=lambda r: r["CPU_Usage_Percent"])
        stats["max_cpu_server"] = {"server_id": hottest["Server_ID"],
                                   "cpu_usage_percent": hottest["CPU_Usage_Percent"]}
    stats["malformed_details"] = malformed_rows
    return stats


def verify_binary_firmware(bin_path: Path) -> dict:
    """
    Низькорівневий аналіз бінарного образу: верифікація магічної сигнатури,
    вилучення версії, визначення розміру образу через seek()/tell() та вилучення
    блоку корисних даних двома способами (від початку й від кінця файлу).
    """
    if not bin_path.exists():
        raise FileNotFoundError(f"Файл бінарного образу '{bin_path.name}' не знайдено.")

    with open(bin_path, mode="rb") as b_file:
        # 1. Зчитування перших 4 байтів заголовка та порівняння з еталонною сигнатурою
        header = b_file.read(4)
        if header != FIRMWARE_MAGIC_HEADER:
            raise ValueError(
                f"Невідомий формат образу: сигнатура {header.hex().upper() or '(порожньо)'} "
                f"!= {FIRMWARE_MAGIC_HEADER.hex().upper()}"
            )

        # 2. Зчитування версії (байти 4 та 5); обірваний файл вважається пошкодженим
        version_bytes = b_file.read(2)
        if len(version_bytes) != 2:
            raise ValueError("Образ обірваний: заголовок містить менше 6 байтів.")
        major_ver, minor_ver = version_bytes[0], version_bytes[1]

        # 3. tell() повертає поточну позицію курсору: кінець заголовка (6-й байт)
        header_end = b_file.tell()

        # 4. seek(0, SEEK_END) переміщує курсор у кінець файлу й повертає розмір у байтах
        file_size_bytes = b_file.seek(0, os.SEEK_END)
        payload_size = file_size_bytes - header_end

        # 5. Вилучення корисного блоку: абсолютне позиціонування від початку файлу
        b_file.seek(header_end, os.SEEK_SET)
        payload = b_file.read(payload_size)

        # 6. Контрольне вилучення: відносне позиціонування від кінця файлу
        b_file.seek(-payload_size, os.SEEK_END)
        payload_from_end = b_file.read()

    return {
        "magic_signature_hex": f"0x{header.hex().upper()}",
        "magic_signature_ascii": header.decode("ascii"),
        "firmware_version": f"v{major_ver}.{minor_ver}",
        "total_image_size_bytes": file_size_bytes,
        "header_size_bytes": header_end,
        "payload_size_bytes": payload_size,
        "payload_hex": " ".join(f"{byte:02X}" for byte in payload),
        "is_signature_valid": True,
        "payload_seek_consistent": payload == payload_from_end,
    }


def export_system_snapshot(output_json_path: Path, csv_stats: dict, bin_stats: dict) -> None:
    """Серіалізує підсумковий стан системи у структурований JSON-документ."""
    snapshot_payload = {
        "station_metadata": {
            "facility_name": "Data Center Server Cluster DC-1",
            "snapshot_generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "pipeline_version": "1.0.0",
        },
        "server_telemetry_summary": csv_stats,
        "node_firmware_audit": bin_stats,
    }

    with open(output_json_path, mode="w", encoding="utf-8") as j_file:
        json.dump(snapshot_payload, j_file, indent=4, ensure_ascii=False)


def main() -> None:
    """Головна точка входу лабораторної роботи."""
    print("=" * 80)
    print(f"{'КОНВЕЄР ФАЙЛОВОГО ВВЕДЕННЯ-ВИВЕДЕННЯ ТА ЗБЕРЕЖЕННЯ СТАНУ (ЦОД)':^80}")
    print("=" * 80)

    input_csv = BASE_DIR / "servers.csv"
    cleaned_csv = BASE_DIR / "cleaned_servers.csv"
    input_bin = BASE_DIR / "firmware_sample.bin"
    output_json = BASE_DIR / "station_snapshot.json"

    t_start = time.perf_counter()

    try:
        # 1. Обробка CSV телеметрії
        csv_metrics = process_csv_telemetry(input_csv, cleaned_csv)
        print("Обробка CSV успішна:")
        print(f"  {'Зчитано рядків:':<30}{csv_metrics['total_read_rows']:>5d}")
        print(f"  {'Некоректних (пропущено):':<30}{csv_metrics['malformed_rows_skipped']:>5d}")
        print(f"  {'Серверів із CPU <= 80%:':<30}{csv_metrics['normal_load_rows']:>5d}")
        print(f"  {'Серверів із CPU > 80%:':<30}{csv_metrics['overloaded_rows_saved']:>5d}")
        print(f"  {'Середня вільна RAM:':<30}{csv_metrics['average_free_ram_gb']:>5.2f} ГБ")
        print(f"  {'Файл збережено:':<30}{cleaned_csv.name}")
        print("-" * 80)

        # 2. Бінарний аудит прошивки
        bin_metrics = verify_binary_firmware(input_bin)
        print("Аудит бінарного образу успішний:")
        print(f"  Магічна сигнатура:     {bin_metrics['magic_signature_hex']} ('{bin_metrics['magic_signature_ascii']}')")
        print(f"  Версія прошивки:       {bin_metrics['firmware_version']}")
        print(f"  Загальний розмір:      {bin_metrics['total_image_size_bytes']} байтів")
        print(f"  Розмір корисних даних: {bin_metrics['payload_size_bytes']} байтів")
        print(f"  Корисний блок (HEX):   {bin_metrics['payload_hex']}")
        print(f"  Узгодженість seek():   {bin_metrics['payload_seek_consistent']}")
        print("-" * 80)

        # 3. Серіалізація підсумкового стану у JSON
        export_system_snapshot(output_json, csv_metrics, bin_metrics)
        print("Підсумковий знімок стану збережено у JSON:")
        print(f"  Цільовий файл:         {output_json.name}")
        print("=" * 80)

    except FileNotFoundError as err:        # має стояти перед OSError (є його підкласом)
        print(f"Помилка файлу: {err}")
        sys.exit(1)
    except ValueError as err:
        print(f"Помилка формату даних: {err}")
        sys.exit(2)
    except (OSError, csv.Error) as err:
        print(f"Системна помилка введення-виведення: {err}")
        sys.exit(3)

    t_elapsed = time.perf_counter() - t_start
    print(f"Час виконання повного конвеєра: {t_elapsed * 1000:.3f} мс\n")


if __name__ == "__main__":
    main()
