# 🌟 Stellar Network Visualization

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Интерактивный инструмент визуализации и анализа связей между кошельками в блокчейне Stellar.

## 🎯 Ключевые особенности

- **Умная выборка**: Автоматический отбор топ-100 самых активных кошельков
- **Ранжирование**: Оценка кошельков по активности, объему, связям
- **Типизация**: Автоматическое определение типов кошельков (биржи, холдеры, боты)
- **Оптимизация**: Фокус на наиболее важных узлах сети для читаемой визуализации

## 📋 Описание

Данный проект представляет собой веб-приложение для визуализации и анализа транзакций в сети Stellar. Основные возможности:

- 🔍 Анализ связей между кошельками
- 📊 Интерактивная визуализация графа транзакций
- 🎯 Фильтрация по различным параметрам (валюта, тип транзакции, дата)
- 📈 Статистика и метрики для каждого кошелька
- 💾 Локальная база данных для кэширования и быстрого доступа

## 🚀 Быстрый старт

### Требования

- Python 3.10+
- pip или conda
- Git

### Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/stellar-network-viz.git
cd stellar-network-viz
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

3. Установите зависимости:
```bash
pip install -r requirements/base.txt
```

4. Настройте переменные окружения:
```bash
cp .env.example .env
# Отредактируйте .env файл с вашими настройками
```

5. Инициализируйте базу данных:
```bash
python scripts/setup_database.py
```

6. Загрузите начальные данные:
```bash
python scripts/fetch_initial_data.py
```

### Запуск приложения

```bash
streamlit run web/app.py
```

Откройте браузер и перейдите по адресу: `http://localhost:8501`

## 🏗️ Архитектура

Проект построен по модульной архитектуре с четким разделением ответственности:

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Stellar    │────>│   API        │────>│  Database   │
│  Horizon    │     │  Client      │     │  (SQLite)   │
└─────────────┘     └──────────────┘     └─────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │   Data       │
                    │  Processing  │
                    └──────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │   Analysis   │
                    │   Engine     │
                    └──────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │Visualization │
                    │   (Plotly)   │
                    └──────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │     Web      │
                    │  Interface   │
                    └──────────────┘
```

## 📦 Основные модули

### `src/api/`
Взаимодействие с Stellar Horizon API для получения данных о транзакциях и кошельках.

### `src/data_processing/`
Обработка, очистка и трансформация полученных данных.

### `src/analysis/`
Анализ сетевых метрик, вычисление статистики кошельков.

### `src/visualization/`
Построение интерактивных графов и визуализаций.

### `database/`
Модели данных и управление базой данных SQLite.

## 🎯 Функциональность

### Основные возможности

- ✅ Получение данных из Stellar Horizon API
- ✅ Сохранение данных в локальную БД
- ✅ Построение графа связей между кошельками
- ✅ Фильтрация по параметрам
- ✅ Интерактивная визуализация
- ✅ Расчет метрик и статистики

### Фильтры

- **По валюте**: XLM, USDC, и другие токены
- **По типу транзакции**: payment, path_payment, create_account
- **По дате**: выбор временного диапазона
- **По объему**: минимальная/максимальная сумма

### Метрики кошельков

- Общее количество транзакций
- Объем входящих/исходящих платежей
- Топ контрагентов
- Средний размер транзакции
- Активность по времени

## 🧪 Тестирование

Запуск тестов:

```bash
pytest tests/
```

Проверка покрытия кода:

```bash
pytest --cov=src tests/
```

## 📖 Документация

Подробная документация доступна в папке `docs/`:

- [Архитектура проекта](docs/ARCHITECTURE.md)
- [API документация](docs/API_DOCUMENTATION.md)
- [Руководство пользователя](docs/USER_GUIDE.md)

## 🤝 Вклад в проект

Приветствуются pull requests. Для больших изменений, пожалуйста, сначала откройте issue для обсуждения.

1. Fork проекта
2. Создайте feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'Add some AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

## 📝 Лицензия

Распространяется под лицензией MIT. См. `LICENSE` для дополнительной информации.

## 👤 Автор

**Ваше Имя**

- GitHub: [@yourusername](https://github.com/yourusername)
- LinkedIn: [Your Name](https://linkedin.com/in/yourname)

## 🙏 Благодарности

- [Stellar Development Foundation](https://stellar.org)
- [Plotly](https://plotly.com) за отличные инструменты визуализации
- IBM Data Analyst Professional Certificate за обучение

## 📊 Статус проекта

🚧 **В активной разработке** 🚧

### Roadmap

- [x] Базовая архитектура
- [x] Интеграция с Stellar API
- [ ] Веб-интерфейс
- [ ] Расширенная аналитика
- [ ] Docker контейнеризация
- [ ] CI/CD pipeline
