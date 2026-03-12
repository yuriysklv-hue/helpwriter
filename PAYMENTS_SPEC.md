# Техническое задание: Оплата подписки через Telegram Stars

**Проект:** HelpWriter Bot
**Версия ТЗ:** 1.0
**Дата:** 9 марта 2026

---

## 1. Цель

Добавить платную подписку в бота через Telegram Stars. Пользователи без активного кода доступа платят подписку, чтобы пользоваться ботом. Реккурентность — ручная: бот сам напоминает об оплате и блокирует доступ при просрочке.

> **Примечание по нативным подпискам:** Telegram в 2024 добавил нативные Stars-подписки для каналов/групп, но для ботов рекуррентный биллинг пока реализуется вручную. Отслеживаем обновления API.

---

## 2. Ценообразование

| Период | Звёзд | ~Рублей | Комментарий |
|---|---|---|---|
| 1 месяц | 150 XTR | ~200 руб | Основной тариф |
| 3 месяца | 400 XTR | ~530 руб | Скидка ~11% |

**Обоснование:** 1 звезда ≈ $0.02, доллар ≈ 90 руб. Telegram берёт ~30% комиссии.
150 звёзд × $0.02 × 0.7 (после комиссии) × 90 руб ≈ **189 руб чистыми.**

---

## 3. Логика доступа

```
Пользователь пишет боту
    → Проверка: активна ли подписка?
        → Да → обработать сообщение
        → Нет → показать кнопку оплаты
```

**Исключения:**
- Пользователи с ручным кодом доступа (`access_codes`) — платить не должны (legacy)
- ADMIN_ID — полный доступ без оплаты
- Новые пользователи — бесплатный trial (опционально, см. п. 7)

---

## 4. Изменения в базе данных

### Новая таблица `subscriptions`

```sql
CREATE TABLE subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_user_id INTEGER NOT NULL,
    stars_payment_id TEXT NOT NULL,       -- telegram payment_charge_id
    stars_amount INTEGER NOT NULL,        -- сколько звёзд заплатил
    period_days INTEGER NOT NULL,         -- 30 или 90
    started_at DATETIME NOT NULL,
    expires_at DATETIME NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sub_user ON subscriptions(telegram_user_id);
CREATE INDEX idx_sub_expires ON subscriptions(expires_at);
```

### Изменения в `access_codes`

Добавить поле `is_paid_user` (boolean) — чтобы отличать ручные коды от платных пользователей при аналитике.

---

## 5. Новые функции в `database.py`

```python
def get_active_subscription(user_id: int) -> dict | None:
    """Возвращает активную подписку или None."""

def create_subscription(user_id, payment_id, stars_amount, period_days) -> int:
    """Создаёт запись о подписке, возвращает ID."""

def get_expiring_subscriptions(days_before: int = 3) -> list[dict]:
    """Возвращает подписки, истекающие через N дней (для напоминаний)."""

def deactivate_expired_subscriptions():
    """Деактивирует просроченные подписки (запускать по крону или при каждом запросе)."""
```

---

## 6. Изменения в `bot_v2.py`

### 6.1 Middleware проверки доступа

Перед обработкой любого сообщения/голоса:

```python
async def check_access(user_id: int) -> bool:
    if user_id == ADMIN_ID:
        return True
    if has_manual_access_code(user_id):   # legacy коды
        return True
    if get_active_subscription(user_id):
        return True
    return False
```

### 6.2 Новые хэндлеры

| Хэндлер | Триггер | Действие |
|---|---|---|
| `handle_subscribe` | Кнопка "Оформить подписку" | Отправляет инвойс на 150 XTR |
| `handle_precheckout` | `PreCheckoutQueryHandler` | Подтверждает платёж (`answer_pre_checkout_query`) |
| `handle_payment` | `MessageHandler(filters.SUCCESSFUL_PAYMENT)` | Создаёт запись в `subscriptions` |
| `handle_subscription_status` | `/subscription` | Показывает статус и дату окончания |

### 6.3 Отправка инвойса

```python
await context.bot.send_invoice(
    chat_id=user_id,
    title="Подписка HelpWriter — 1 месяц",
    description="30 дней доступа ко всем режимам обработки текста",
    payload="subscription_30d",
    provider_token="",          # пустая строка для Telegram Stars
    currency="XTR",
    prices=[LabeledPrice("1 месяц", 150)],
    protect_content=False,
)
```

### 6.4 Сообщение при заблокированном доступе

```
⭐ Для использования бота нужна подписка.

Стоимость: 150 звёзд / месяц (~200 ₽)

[Оформить подписку — 150 ⭐]   [Узнать подробнее]
```

---

## 7. Напоминания об истечении (рекуррентность)

Так как Telegram Stars не делают автосписание, имитируем рекуррентность через напоминания:

| За сколько до конца | Сообщение |
|---|---|
| 3 дня | "⚡ Подписка истекает через 3 дня. Продлите, чтобы не потерять доступ." + кнопка оплаты |
| 1 день | "⏳ Завтра истекает подписка." + кнопка |
| День X (истекла) | "❌ Подписка закончилась. Продлите доступ." |

**Реализация:** планировщик через `job_queue` в python-telegram-bot (APScheduler встроен):

```python
application.job_queue.run_daily(
    send_expiry_reminders,
    time=datetime.time(hour=10, tzinfo=pytz.timezone("Europe/Moscow"))
)
```

---

## 8. Команды бота (обновление)

| Команда | Описание |
|---|---|
| `/start` | Меню режимов (если есть доступ) или экран оплаты |
| `/subscription` | Статус подписки, дата окончания, кнопка продления |
| `/enter_code <код>` | Активировать ручной код (legacy) |
| `/admin_stats` | Статистика + доходы от Stars |

---

## 9. Аналитика для `/admin_stats`

Добавить в статистику:
- Количество активных платных подписок
- Выручка за последние 30 дней (в звёздах и ~рублях)
- Количество продлений
- Churn rate (не продлили после истечения)

---

## 10. Бесплатный trial (опционально)

Можно дать новым пользователям **3 дня бесплатно** при первом `/start`:

- Автоматически создаётся запись в `subscriptions` с `stars_amount=0`, `period_days=3`
- После окончания — стандартный экран оплаты
- Trial только один раз (проверка по `telegram_user_id`)

---

## 11. Что не входит в этот этап

- Нативные автоподписки (ждём обновления Telegram Bot API)
- Веб-сайт / лендинг с оплатой
- Другие способы оплаты (карты, ЮKassa и т.д.)
- Реферальная система

---

## 12. Порядок разработки

1. `database.py` — новая таблица и функции
2. Middleware проверки доступа в `bot_v2.py`
3. Хэндлеры инвойса и successful_payment
4. Экран "нет доступа" с кнопкой оплаты
5. `/subscription` команда
6. Напоминания (job_queue)
7. Обновление `/admin_stats`
8. Тест на тестовом боте
9. Деплой на сервер
