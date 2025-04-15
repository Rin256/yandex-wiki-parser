﻿# Подготовка

1. Установить python (https://www.python.org/downloads/)
2. Запустить подготовку с помощью init.bat

# Использование

1. Ввести в src\config.py параметры:
- CSRF-TOKEN (необходимо авторизоваться в браузере на сайте https://wiki.yandex.ru/ и скопировать соответствующий cookie)
- YC_SESSION (необходимо авторизоваться в браузере на сайте https://wiki.yandex.ru/ и скопировать соответствующий cookie)
- DIRECTORY (каталог загрузки, если не заполнить, то будет использоваться каталог \data), подкаталог с текущей датой будет сформирован автоматический

Для просмотра cookies в браузере удобно использовать расширение EditThisCookie (https://www.editthiscookie.com/) или Cookie editor (https://www.hotcleaner.com/cookie-editor/)
Либо другой аналогичный по функционалу софт.

2. Запустить парсер с помощью run_parser.bat
