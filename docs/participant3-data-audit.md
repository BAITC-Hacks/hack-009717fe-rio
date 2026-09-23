# Айназ Абитай — аудит данных и чек-лист демо

Третий участник команды — **Айназ Абитай**. Этот документ фиксирует её зону ответственности и доказательства для защиты.

Айназ отвечает за качество каталога, происхождение добавленных профилей, тестовые сценарии, README и скриншоты.

## Снимок источника

- Source file: `data/contractors.csv` (66 original profiles preserved inside the expanded catalog)
- Additional file: `data/synthetic_profiles.csv` (separate audit artifact)
- Runtime profiles: 200
- Synthetic profiles in runtime: 147
- Cities: проверяются скриптом аудита из актуального CSV
- Calendar window: 2026-09-23 through 2026-12-31 (100 days)
- Categories: 30

Исходные записи сохранены. Поля `synthetic`, `city_imputed` и `price_imputed` нельзя удалять или незаметно переписывать.

## Что проверять после изменения данных

Запустить полный набор из корня репозитория:

```bash
python3 -m unittest discover -s tests -v
```

Перед демо запустить аудит каталога:

```bash
python3 tools/audit_data.py --include-synthetic --markdown
```

Код выхода `0` означает, что каталог прошёл проверку. Ненулевой код указывает на ошибку данных, которую нужно исправить или отдельно объяснить жюри.

Перед демо обязательны следующие проверки:

1. Every profile has a unique `id`.
2. Every price is positive and numeric.
3. Every `busy_dates` value is a valid date inside the 100-day window.
4. Every profile has a city, category, event format and description.
5. A profile marked `synthetic=true` is visibly labelled in the website.
6. The same request returns the same card order twice.
7. A busy profile never appears in `cards`.
8. A rare category reports fewer than three when that is the actual result.
9. A missing city/category combination returns `no_category`.
10. A category with candidates but impossible constraints returns `no_match` and reasons.

## Последовательность демо

Show these cases in order:

1. Dense category: Алматы, ведущий, корпоратив, autumn date, normal budget.
2. Same request on another date: explain which previously shown profiles became busy.
3. Rare category: флорист or инструменталист; show why fewer than three are returned.
4. Impossible budget: show `no_match` and the exclusion audit.
5. Missing city/category pair: show `no_category`.

Кнопки демо не должны быть заготовленными ответами: они вызывают тот же endpoint рекомендаций, что и форма.

## Синтетические профили

Дополнительные профили допустимы, если используют ту же схему и отмечены `synthetic: true`. Нельзя заменять исходный каталог, создавать повторяющиеся ID или настраивать занятость только под дату демо. Количество и происхождение добавленных профилей нужно указывать в README и презентации.

## Текст для защиты

> Мы проверяем не только успешные рекомендации. Для каждой заявки сохраняем причины исключения, отдельно показываем отсутствие категории и ситуацию, когда кандидаты есть, но условия не проходят. Исходный каталог сохранён; синтетические записи помечаются явно и проходят тот же фильтр.

Айназ показывает эти доказательства, объясняет происхождение данных и проводит финальную проверку воспроизводимости. Backend остаётся зоной Мирас, а изменения интерфейса согласуются с Темирланом.
