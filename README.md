# Инструкция по работе с приложением

1. Установить зависимости для python согласно файлу `requirements.txt`
```python
pip install -r requirements.txt
```

2. Ввести в config.py параметры:
- CSRF-TOKEN (необходимо авторизоваться в браузере на сайте https://wiki.yandex.ru/ и скопировать соответствующий cookie)
- YC_SESSION (необходимо авторизоваться в браузере на сайте https://wiki.yandex.ru/ и скопировать соответствующий cookie)
- DIRECTORY (каталог загрузки, если не заполнить, то будет использоваться каталог \data), подкаталог с текущей датой будет сформирован автоматический

Для просмотра cookies в браузере удобно использовать расширение EditThisCookie (https://www.editthiscookie.com/)

3. Запустить парсер
```python
python YandexWikiParser.py
```
