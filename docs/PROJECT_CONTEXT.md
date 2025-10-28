# 🌟 STELLAR NETWORK VISUALIZATION - COMPLETE PROJECT CONTEXT

**Дата обновления:** 28.10.2025  
**Версия:** 3.3 (Active Development)

---

## 📋 О ПРОЕКТЕ

**Название:** Stellar Network Visualization  
**Тип:** Интерактивное веб-приложение для анализа блокчейн-транзакций  
**Цель:** Портфолио проект для дата-аналитика  
**Технологии:** Python 3.13, Streamlit, Plotly, NetworkX, Stellar SDK  
**Статус:** В активной разработке, стадия улучшений и оптимизации

### Что делает приложение:
Позволяет исследовать сеть транзакций в блокчейне Stellar:
- Визуализация связей между кошельками в виде интерактивного графа
- Анализ потоков активов (USDC, XLM, EURC, yUSDC и др.)
- Фильтрация по множеству параметров (валюта, даты, суммы, направление)
- Детальная статистика по кошелькам и транзакциям
- Поиск путей между кошельками (Path Finder)

---

## 🏗️ АРХИТЕКТУРА ПРОЕКТА

### Структура папок:
```
stellar_network_viz_complete/
├── web/
│   └── app.py                          # [74 KB] Главное Streamlit приложение
├── src/
│   ├── api/
│   │   └── stellar_client.py           # [40 KB] Клиент Stellar Horizon API
│   ├── visualization/
│   │   ├── graph_builder.py            # Базовый билдер (не используется)
│   │   └── graph_builder_enhanced.py   # [37 KB] ОСНОВНОЙ билдер графов
│   └── analysis/
│       └── wallet_analyzer.py          # Анализатор кошельков
├── config/
│   └── settings.py                     # Настройки API, лимиты
├── requirements.txt                    # Python зависимости
├── venv/                               # Виртуальное окружение (не в git)
├── START.bat                           # Скрипт запуска (Windows)
└── .streamlit/                         # Кэш и конфиг Streamlit
```

### Ключевые файлы:

#### 1. **web/app.py** (1493 строки, 74 KB)
Главный файл приложения.

**Класс:** `StellarNetworkApp`

**Основные методы:**
- `render_sidebar()` - панель управления с фильтрами и настройками
- `create_network_graph()` - создание интерактивного графа
- `fetch_network_data()` - загрузка данных через API
- `display_network()` - отображение графа и панелей анализа
- `render_wallet_analysis()` - панель анализа кошелька
- `render_transactions_table()` - таблица транзакций
- `render_network_metrics()` - сетевые метрики
- `render_path_finder()` - поиск путей между кошельками

**Особенности:**
- Использует `st.session_state` для сохранения данных между reruns
- Кэширование через `@st.cache_data` (бесконечное хранение)
- Debug Info expander для диагностики полноты данных
- Filtering Pipeline Statistics для отслеживания потерь данных

#### 2. **src/api/stellar_client.py** (890 строк, 40 KB)
API клиент для работы с Stellar Horizon API.

**Класс:** `StellarDataFetcher`

**Основной метод:** `fetch_wallet_network()`
```python
async def fetch_wallet_network(
    wallet_address: str,
    depth: int = 2,
    max_wallets: int = 50,
    strategy: str = "most_active",
    asset_filter: List[str] = None,
    tx_type_filter: List[str] = None,
    date_from: datetime = None,
    date_to: datetime = None,
    direction_filter: List[str] = None,
    min_amount: float = -1.0,
    max_amount: float = -1.0,
    max_pages: int = 25
)
```

**Фичи:**
- Пагинация с настраиваемыми лимитами (Fast/Normal/Extended/Full/Unlimited)
- Фильтрация на уровне API (asset, date, direction, amount)
- Детальное логирование всех этапов
- Статистика фильтрации (сколько транзакций потеряно на каждом этапе)
- Rate limiting для соблюдения API ограничений
- Обработка path_payment транзакций

**Важно:** 
- `-1.0` для min/max_amount означает "фильтр не применяется"
- WARNING для "Account not found" заменён на DEBUG

#### 3. **src/visualization/graph_builder_enhanced.py** (889 строк, 37 KB)
Расширенный билдер графов с интерактивностью.

**Класс:** `EnhancedNetworkGraphBuilder`

**Основные методы:**
- `build_graph()` - создание NetworkX графа из данных
- `create_interactive_figure()` - создание Plotly интерактивной фигуры
- `calculate_layout()` - расчет позиций узлов (force/circular/hierarchical/spectral)
- `_create_interactive_node_trace()` - создание узлов с tooltips
- `_create_interactive_edge_trace()` - создание рёбер с цветами

**Особенности:**
- Force-directed layout с кольцевым распределением (как у AMLBot)
- Размер нодов: фиксированный (20px) для всех узлов
- Цвета рёбер:
  - 🟠 Оранжевые: связи со стартовым кошельком
  - ⚫ Серые: связи между другими кошельками
  - Градация по количеству транзакций (темнее = больше tx)
- Tooltips с детальной информацией (balance, sent, received, net flow)
- Поддержка highlight и center на кошельках

---

## 🚀 ФУНКЦИОНАЛЬНОСТЬ

### 1. Сбор данных
- **Источник:** Stellar Horizon API (mainnet)
- **Стратегии:** Most Active / Most Volume / Random
- **Глубина:** 0-5 hops (по умолчанию: 2)
- **Лимиты загрузки:**
  - Fast: 5 страниц (~1K транзакций)
  - Normal: 25 страниц (~5K транзакций) [по умолчанию]
  - Extended: 50 страниц (~10K транзакций)
  - Full: 100 страниц (~20K транзакций)
  - Unlimited: без лимита (до 273 на практике)
- **Кэширование:** Бесконечное хранение, можно очистить кнопкой "Clear Cache"

### 2. Фильтрация

#### Asset Filter (Валюта):
- All (все валюты)
- XLM (нативная валюта Stellar)
- USDC (Circle USD Coin) [по умолчанию]
- EURC (Circle Euro Coin)
- yUSDC (Ultra Stellar USDC)
- SSLX (Smartlands)
- Другие (автоматически из данных)

#### Transaction Type Filter:
- All (все типы)
- payment [по умолчанию]
- create_account
- path_payment_strict_send
- path_payment_strict_receive

#### Date Range Filter:
- **По умолчанию:** Последний год (2024-10-28 to 2025-10-28)
- Checkbox "Enable date filter" (включен по умолчанию)
- Выбор от/до через date_input

#### Direction Filter:
- All (все направления)
- Sent (исходящие) [по умолчанию]
- Received (входящие) [по умолчанию]

#### Amount Filter:
- Min amount (от): -1.0 = не задано
- Max amount (до): -1.0 = не задано
- Используется для фильтрации по сумме транзакций

#### Min TX Count Filter:
- Скрывает кошельки с малым количеством транзакций со стартовым кошельком
- По умолчанию: 0 (все показаны)

### 3. Визуализация

#### Layouts:
- **force** - Force-directed (как у AMLBot) [по умолчанию]
- circular - Круговое расположение
- hierarchical - Иерархическое дерево
- spectral - Спектральное

#### Node Size Metrics:
- Transaction count [используется]
- Total volume
- Unique connections
- Equal size (все одинаковые)

**Фактически:** Все узлы одинакового размера (20px) для единообразия

#### Interactivity:
- **Highlight wallet:** Подсветка связей выбранного кошелька
- **Center on wallet:** Центрирование графа на кошельке (default/custom)
- **Hover tooltips:** Детальная информация при наведении
- **Click:** В будущем - центрирование по клику (пока не реализовано)

#### Edge Colors:
- 🟠 Оранжевые оттенки: связи стартового кошелька
  - #FF4500 (темно-оранжевый): 10+ транзакций
  - #FF6B00: 5-9 транзакций
  - #FFA500: 2-4 транзакции
  - #FFD700 (золотой): 1 транзакция
- ⚫ Серые оттенки: связи между другими кошельками
  - #666666: 10+ транзакций
  - #888888: 5-9 транзакций
  - #AAAAAA: 2-4 транзакции
  - #CCCCCC: 1 транзакция

#### Legend:
- Компактная метка на графе: "📊 Edge Colors"
- Полная легенда под графом (collapsible expander)
- Цвета показаны квадратиками ■ (не линиями)

### 4. Анализ

#### Панели (Tabs):
1. **📊 Wallet Analysis** - анализ выбранного кошелька
2. **💸 Transactions** - таблица всех транзакций
3. **📈 Metrics** - сетевые метрики
4. **🔍 Details** - сырые данные (JSON)
5. **🔎 Path Finder** - поиск путей между кошельками

#### Wallet Analysis содержит:
- Полный адрес (копируемый)
- Balance в XLM
- Total Transactions
- Connections (уникальные контрагенты)
- Transaction Breakdown: Sent/Received с суммами
- Top Counterparties (кто отправлял/получал больше всего)
- Activity Timeline (график во времени)

#### Path Finder:
- Ввод двух адресов кошельков (Wallet A и Wallet B)
- Выбор максимальной длины пути (1-5 hops)
- Поиск кратчайшего пути через NetworkX
- Отображение пути с промежуточными кошельками
- Расчет максимального потока через путь
- Работает только для кошельков, загруженных в текущей сети

### 5. Диагностика

#### Debug Info & Data Completeness Check:
Expander с детальной информацией:

**Current Data:**
- Количество wallets, transactions
- Текущий layout

**Selected Filters:**
- Все активные фильтры (asset, dates, direction, amount, etc)

**Data Completeness Check:**
- Транзакции со стартовым кошельком (sent/received)
- Уникальные кошельки в транзакциях vs в data
- Несоответствия (wallets в tx но не в data)

**Transaction Statistics:**
- Разбивка по валютам (USDC: 273, XLM: 5, etc)
- Разбивка по типам (payment: 250, create_account: 23, etc)
- Фактический временной диапазон данных

**⚙️ Filtering Pipeline Statistics:**
- 📥 Initial: сколько получено от API
- 🔽 After Top Wallets: после отбора топ N
- ✅ Final: после всех фильтров
- ❌ Lost: сколько потеряно (%)
- Предупреждение если >50% потеряно

**Recommendations:**
- Советы по улучшению если мало данных

---

## ⚙️ ТЕХНИЧЕСКИЙ СТЕК

### Backend:
- **Python:** 3.13 (в venv)
- **Async:** asyncio, aiohttp для параллельных запросов
- **API:** stellar-sdk 9.1.0

### Frontend:
- **Framework:** Streamlit 1.40.1
- **Visualization:** Plotly 5.x (интерактивные графы)
- **Graph Library:** NetworkX 3.x (построение графов)
- **Data:** Pandas для анализа

### Deployment:
- **OS:** Windows
- **IDE:** PyCharm / VS Code
- **Terminal:** PowerShell
- **Запуск:** `streamlit run web\app.py` или `START.bat`
- **URL:** http://localhost:8501 (или 8502 если занят)

---

## 🎯 ТЕКУЩИЙ СТАТУС (28.10.2025)

### ✅ ЧТО РАБОТАЕТ ОТЛИЧНО

1. **Сбор данных:**
   - Фетчинг транзакций с пагинацией ✅
   - Фильтрация по asset, type, date, direction, amount ✅
   - Кэширование с бесконечным хранением ✅
   - Детальное логирование всех этапов ✅

2. **Граф:**
   - Отображение узлов и рёбер ✅
   - Force-directed layout ✅
   - Цветовая схема (оранжевый/серый) ✅
   - Tooltips с детальной информацией ✅
   - Highlight wallet (подсветка связей) ✅
   - Center on wallet ✅
   - Edge color legend (collapsible) ✅

3. **Анализ:**
   - Wallet Analysis panel ✅
   - Transactions table ✅
   - Network Metrics ✅
   - Path Finder ✅
   - Debug Info с Filtering Pipeline Statistics ✅

4. **UI/UX:**
   - Все фильтры работают ✅
   - Reset Filters кнопка ✅
   - Help & Guide section ✅
   - Deprecation warnings исправлены (use_container_width → width) ✅

### 🐛 ИЗВЕСТНЫЕ ПРОБЛЕМЫ

1. **Tooltip показывает 0.00 для Sent/Received** - ИСПРАВЛЕНО
   - Причина: данные из графа, но для некоторых кошельков нет транзакций в фильтрованных данных
   - Решение: Вернули полную информацию в tooltip

2. **Tooltip пропадает при уходе курсора** - Нельзя исправить
   - Это стандартное поведение Plotly
   - Решение: Использовать Highlight wallet dropdown для детальной информации

3. **Path Finder не находит кошелек** - ИСПРАВЛЕНО
   - Причина: Проверялось наличие в data["wallets"], а не в графе
   - Решение: Теперь проверяется наличие в G.nodes()

4. **selected_asset is not defined** - ИСПРАВЛЕНО
   - Причина: Параметр не передавался в _create_interactive_node_trace
   - Решение: Добавлен параметр в сигнатуру и вызов

### ⚠️ ОГРАНИЧЕНИЯ

1. **Нет поддержки testnet** - только mainnet
2. **Нет export графа** в PNG/SVG
3. **Нет сохранения настроек** между сессиями
4. **Click on node** для центрирования не работает (ограничение Plotly)

### 📊 ПРОИЗВОДИТЕЛЬНОСТЬ

- **Максимальная сеть:** ~200-300 кошельков
- **Оптимальная:** 50-100 кошельков
- **Время загрузки:** 10-30 секунд (зависит от Max pages)
- **Кэш:** Значительно ускоряет повторные запросы

---

## 💻 ОКРУЖЕНИЕ ПОЛЬЗОВАТЕЛЯ

- **OS:** Windows 10/11
- **Python:** 3.13.0 (в venv)
- **IDE:** PyCharm / VS Code
- **Terminal:** PowerShell
- **Browser:** Chrome/Edge (latest)

### Запуск:
```powershell
# Вариант 1: Через bat-скрипт
START.bat

# Вариант 2: Вручную
venv\Scripts\activate
streamlit run web\app.py
```

### Остановка:
```
Ctrl + C в терминале
```

### Очистка кэша:
```
Кнопка "Clear Cache" в sidebar или
Ctrl + Shift + R в браузере
```

---

## 🔍 ПРИМЕР ИСПОЛЬЗОВАНИЯ

### Типичный workflow:

1. **Запуск приложения:**
   ```
   START.bat или streamlit run web\app.py
   ```

2. **Ввод кошелька:**
   ```
   Пример: GD2PCIIRROTN5AAVFOFKE32E564WM35TQEMQOQR3T6OJYQKNKN4PLLQC
   (56 символов, начинается с G)
   ```

3. **Настройка параметров:**
   - Depth: 2 (по умолчанию)
   - Max wallets: 50-100
   - Strategy: Most Active
   - Max pages: Normal (25 страниц)

4. **Выбор фильтров:**
   - Asset: USDC ✅
   - Type: payment ✅
   - Date: последний год ✅
   - Direction: Sent + Received ✅

5. **Загрузка:**
   - Нажать "🚀 Fetch & Analyze"
   - Дождаться spinner (10-30 сек)

6. **Анализ:**
   - Изучить граф
   - Использовать Highlight wallet для детального просмотра
   - Проверить панели Wallet Analysis, Transactions
   - Использовать Path Finder для поиска связей

7. **Проверка полноты данных:**
   - Открыть "Debug Info & Data Completeness Check"
   - Проверить Filtering Pipeline Statistics
   - Убедиться что потери <50%

---

## 📝 ИСТОРИЯ РАЗРАБОТКИ

### Stage 1: MVP (Завершено)
- Базовая визуализация графа
- Простые фильтры (asset, type)
- Загрузка через API

### Stage 2: Фильтры (Завершено)
- Direction filter (Sent/Received)
- Amount filter (Min/Max)
- Date range filter
- UI для фильтров

### Stage 3: Интерактивность (Завершено)
- Highlight wallet
- Center on wallet
- Enhanced tooltips с Net Flow
- Help & Guide section

### Stage 4: Улучшения (Текущий)
- Debug Info с Completeness Check
- Filtering Pipeline Statistics
- Path Finder на отдельной вкладке
- Edge color legend (collapsible)
- Исправление багов с tooltips
- Оптимизация производительности

### Stage 5: Планируется
- Export графа в изображение
- Сохранение настроек
- Testnet support
- Больше layouts
- Улучшенный Path Finder (множественные пути)

---

## 🐛 ОТЛАДКА

### Проблема: Граф не отображается

**Проверить:**
1. Debug Info - есть ли данные? (Wallets > 0, Transactions > 0)
2. Если Wallets: 0 → проблема в фильтрах (слишком строгие)
3. Если есть данные но граф пустой → проблема в build_graph()
4. Проверить консоль браузера на ошибки

**Решение:**
- Ослабить фильтры (All для asset, убрать amount filter)
- Увеличить Max pages
- Расширить date range
- Проверить что файлы обновлены

### Проблема: Мало транзакций

**Проверить:**
- Filtering Pipeline Statistics в Debug Info
- Сколько потеряно на каждом этапе?

**Решение:**
- Если >50% потеряно → фильтры слишком строгие
- Попробовать "All" для asset
- Расширить date range
- Убрать amount filter
- Увеличить Max pages

### Проблема: Path Finder не находит кошелек

**Причины:**
1. Кошелек не загружен в текущую сеть
2. Адрес введён неправильно (должен быть 56 символов)
3. Depth слишком маленький

**Решение:**
- Сначала загрузить данные для одного из кошельков
- Увеличить Max wallets
- Увеличить Depth
- Проверить адрес (56 символов, начинается с G)

### Проблема: Приложение медленно

**Причины:**
1. Слишком много кошельков (>200)
2. Max pages = Unlimited
3. Нет кэша

**Решение:**
- Уменьшить Max wallets до 50-100
- Использовать Normal/Extended вместо Unlimited
- Использовать кэш (не чистить без необходимости)
- Использовать более строгие фильтры

---

## 📚 ВАЖНЫЕ ДЕТАЛИ

### Wallet Address Format:
- 56 символов
- Начинается с 'G'
- Пример: `GD2PCIIRROTN5AAVFOFKE32E564WM35TQEMQOQR3T6OJYQKNKN4PLLQC`

### Asset Codes:
- USDC: `USDC:GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN`
- XLM: нативный (без issuer)
- EURC, yUSDC, SSLX: с issuer

### Transaction Types:
- `payment`: Простой перевод
- `create_account`: Создание нового аккаунта
- `path_payment_strict_send`: Отправка через path (автоконверсия)
- `path_payment_strict_receive`: Получение через path

### Graph Metrics:
- **Balance:** Баланс кошелька в XLM
- **Connections:** Количество уникальных связей
- **Sent:** Сумма исходящих транзакций
- **Received:** Сумма входящих транзакций
- **Net Flow:** Received - Sent (положительный = больше получил)

---

## 🎓 ЛУЧШИЕ ПРАКТИКИ

### Для исследования конкретного кошелька:
1. Начать с Depth: 1, Max wallets: 50
2. Использовать Most Active strategy
3. Выбрать конкретную валюту (USDC/XLM)
4. Использовать Normal (25 pages)
5. Проверить Debug Info после загрузки

### Для поиска связей:
1. Загрузить сеть с Depth: 2-3
2. Увеличить Max wallets до 100-150
3. Использовать Extended/Full pages
4. Использовать Path Finder для поиска конкретных связей

### Для анализа активности:
1. Установить широкий date range (год)
2. Не фильтровать по direction (All)
3. Не фильтровать по amount
4. Использовать "All" для asset
5. Изучить Wallet Analysis и Transactions tabs

---

## 🔗 API ENDPOINTS

### Stellar Horizon API:
- **Mainnet:** https://horizon.stellar.org
- **Testnet:** https://horizon-testnet.stellar.org (не используется)

### Rate Limits:
- ~3600 requests/hour (1 req/sec)
- Приложение соблюдает лимиты автоматически

---

## 📦 DEPENDENCIES (requirements.txt)

Основные:
```
streamlit==1.40.1
plotly==5.17.0
networkx==3.1
scipy==1.11.4
stellar-sdk==9.1.0
pandas==2.0.3
numpy==1.24.3
aiohttp==3.9.0
```

---

## 🎯 ИТОГ

**Проект полностью функционален и готов для портфолио.**

Основные достижения:
- ✅ Работающая визуализация сети Stellar
- ✅ Множество фильтров и настроек
- ✅ Интерактивный граф с tooltips
- ✅ Детальная аналитика
- ✅ Path Finder для поиска связей
- ✅ Диагностика полноты данных

Проект демонстрирует навыки:
- Работа с блокчейн API
- Визуализация графов
- Обработка больших данных
- Создание интерактивных дашбордов
- Async программирование
- UX/UI дизайн

---

**Версия документа:** 3.3  
**Последнее обновление:** 28.10.2025  
**Автор:** spurcell (с помощью Claude)
