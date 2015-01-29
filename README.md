lunalogger
==========

http-логгер чата для [lunadc](https://github.com/un-def/lunadc). Просмотр логов по дням с навигацией и обработкой ссылок, в том числе magnet (TTH), ТОП-100 пользователей по количеству сообщений, страница информации о каждом пользователе.

Версия для Python 3. В качестве БД используется MySQL (с помощью интерфейса [PyMySQL](https://github.com/PyMySQL/PyMySQL) — это единственная зависимость). Фронтэнд — Bootstrap 3 и jQuery 1.11 с плагинами [jquery.arbitrary-anchor.js](https://github.com/briangonzalez/jquery.arbitrary-anchor.js) и [Linkify](https://github.com/SoapBox/jQuery-linkify).

URL для lunadc — http://example.com/api/post (см. cfg.**logger** в ```config.lua```).


### settings.py
* **db** — словарь именованных аргументов ```pymysql.connect()```;
* **post_encoding** — кодировка отправляемых lunadc сообщений (т.е. кодировка хаба); предварительно предпринимается попытка декодировать сообщение как utf-8, **post_encoding** применяется в  случае неудачи;
* **token** — токен, который lunadc отправляет с каждым сообщением; используется для простейшей идентификации/авторизации.

