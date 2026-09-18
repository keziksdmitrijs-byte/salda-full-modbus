# Salda MCB Modbus (AHU) — интеграция для Home Assistant

## Версия 1.2.0 — что исправлено

1. **"Detected blocking call to import_module ... inside the event loop"** —
   исправлено. `registers.py` — большой файл (~150 КБ, ~940 записей), и его импорт
   внутри `sensor.py`/`number.py`/... занимал заметное время прямо в момент вызова
   `hass.config_entries.async_forward_entry_setups()`, что Home Assistant отмечал
   как блокирующий вызов внутри event loop. Теперь `__init__.py` "прогревает"
   импорт всех платформенных модулей в отдельном потоке (`hass.async_add_executor_job`)
   **до** вызова `async_forward_entry_setups`, поэтому сам форвардинг становится
   мгновенным (модуль уже в `sys.modules`).

2. **"Error setting up entry Salda AHU (...) for salda_mcb_modbus"** — было
   следствием проблемы №1; после фикса setup должен завершаться штатно.

3. **"Some Modbus ranges failed to read (32/38)"** при **slave id = 0** — это
   ожидаемо: адрес **0 в Modbus зарезервирован под broadcast**, и по спецификации
   устройство не обязано на него отвечать вообще. То, что часть диапазонов всё
   же прочиталась — особенность конкретного шлюза (некоторые TCP-гейтвеи
   игнорируют unit id для отдельных функций). Рекомендация: **попробуйте slave id
   = 1** — это заводское значение адреса Modbus для контроллеров Salda MCB
   (регистр `HR_SERVICE_Comunication_1_ADDRESS`, адрес 672, по умолчанию = 1).
   Если с id=1 связь надёжнее — используйте его. Если конкретно ваш шлюз
   действительно требует 0 и большинство регистров при этом читается стабильно —
   можно оставить 0, слайдер теперь снизу показывает предупреждение в логе, но
   не блокирует выбор.

## Форма настройки подключения

- **Host / IP address**, **TCP port** (обычно 502).
- **Modbus slave (unit) id** — слайдер 0–247. Рекомендуется **1**, а не 0.
- **Modbus framing** — `Modbus TCP` (обычный MBAP) или `Modbus RTU over TCP`
  (для RS-485→Ethernet шлюзов, которые туннелируют "сырые" RTU-кадры с CRC).
- **Address mode (1/0)** — 1 = адрес как в документации Salda, 0 = строгая
  0-based адресация протокола Modbus.
- **Polling interval, s**.
- **Add without connection test** — сохранить подключение без пробного чтения,
  если устройство отвечает только на часть регистров.

## Диагностика "не подключается" / "часть регистров не читается"

1. Проверьте **Slave id = 1** сначала (не 0) — самая частая причина частичного
   ответа именно в этом.
2. Если с id=1 совсем не отвечает — попробуйте переключить **Modbus framing**
   на "RTU over TCP", особенно если у вас дешёвый RS-485↔Ethernet конвертер.
3. Переключите **Address mode** между 1 и 0, если показания выглядят сдвинутыми
   на один регистр.
4. Смотрите **Настройки → Система → Журналы**, записи от
   `custom_components.salda_mcb_modbus` — там указывается точный диапазон
   регистров, который не отвечает, и настоящая причина от pymodbus.
5. Параметры меняются позже через **Настройки → Устройства и службы → Salda AHU
   → Настроить**, без переустановки интеграции.

## Установка через HACS

1. HACS → Integrations → меню (три точки) → **Custom repositories**.
2. Добавьте URL этого репозитория, категория **Integration**.
3. Установите "Salda MCB Modbus (AHU)", перезапустите Home Assistant.
4. **Настройки → Устройства и службы → Добавить интеграцию** → «Salda MCB Modbus (AHU)».

## Установка вручную

Скопируйте `custom_components/salda_mcb_modbus` в `config/custom_components/`,
перезапустите HA, добавьте интеграцию через UI.

## Сущности

| Тип регистра | Кол-во | Платформа HA | Поведение |
|---|---|---|---|
| Holding Register (диапазон) | 489 | `number` | Слайдер/поле уставки |
| Holding Register (перечисление) | 108 | `select` | Выпадающий список режимов |
| Coil | 80 | `switch` | Переключатель on/off |
| Discrete Input | 157 | `binary_sensor` | Статус/авария |
| Input Register | 104 | `sensor` | Измеряемая величина |

## Структура файлов

```
custom_components/salda_mcb_modbus/
├── __init__.py       # <- фикс blocking import здесь (_preload_platform_modules)
├── config_flow.py     # форма настройки + предупреждение про slave_id=0
├── const.py
├── coordinator.py
├── modbus_hub.py        # framing TCP/RTU-over-TCP + address offset
├── registers.py
├── sensor.py / binary_sensor.py / number.py / select.py / switch.py
├── manifest.json / strings.json / translations/
```
