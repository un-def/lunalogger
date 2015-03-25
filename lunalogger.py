#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import datetime
import urllib.parse
import cgi
import pymysql
import template
import settings

class Path:

    registered = {}

    @classmethod
    def add(self, pattern):
        """ pattern format:
            {var_name[:type][:length]}

                var_name:
                    ...

                type:
                    s (string) - any symbols except '/';
                    d (digit) - only digits;
                    default - string;

                length:
                    m - exactly m symbols;
                    m,n - from m to n symbols;
                    ,n - from 1 to n symbols;
                    m, - min m symbols, infinite upper bound;
                    default - 1,
        """
        def pattern2re(match):
            var_name = match.group(1)
            char_set = '[0-9]' if match.group(3) == 'd' else '[^/]'
            qualifier = '{' + match.group(5) + '}' if match.group(5) else '+'
            return '(?P<{0}>{1}{2})'.format(var_name, char_set, qualifier)
        def add_decorator(call_object):
            if pattern != '/':
                pattern_regexp = re.sub('\{([^:]+?)(:([sd])(:([0-9,]+))?)?\}', pattern2re, pattern) + '/?'
            else:
                pattern_regexp = '/'
            self.registered[pattern_regexp] = call_object
            return call_object
        return add_decorator

    @classmethod
    def check(self, path):
        for pattern_regexp, call_object in self.registered.items():
            match = re.fullmatch(pattern_regexp, path)
            if match:
                return (call_object, match.groupdict())
        return False


class LoggerApp:

    status = '200 OK'
    plain = False
    title = ''
    linkify = None   # селектор, для которого применяется linkify
    js_for_logpage = False   # подключает jquery-штуки для страницы лога (плавная прокрутка, модальные окна)
    conn = None
    navbar = None
    default_navbar = (
        # (внутреннее имя, url, текст ссылки)
        ('main', '/', 'главная'),
        ('log', '/log/', 'лог'),
        ('users', '/users/', 'пользователи')
    )

    def __init__(self, environ, start_response):
        self.environ = environ
        self.start = start_response

    def __iter__(self):
        self.headers = []
        self.response = []
        path = self.environ['PATH_INFO'].encode('iso-8859-1').decode('utf-8')   # https://code.djangoproject.com/ticket/19468
        make_content = Path.check(path)
        if make_content:
            if settings.append_slash and not path.endswith('/'):
                self.redirect(urllib.parse.quote(path, safe='/') + '/', perm=True)
            else:
                make_content[0](self, **make_content[1])
                if self.conn:
                    self.db_close()
        else:
            self.error_404()
        if self.plain:
            self.headers.append(('Content-type', 'text/plain; charset=utf-8'))
        else:
            self.headers.append(('Content-type', 'text/html; charset=utf-8'))
        self.start(self.status, self.headers)
        if not self.plain:
            if self.title != '':
                title = self.title + settings.title_separator + settings.title_sitename
            else:
                title = settings.title_sitename
            yield template.head.format(title).encode('utf-8')
            if self.navbar:
                yield template.make_navbar(*self.navbar).encode('utf-8')
        for el in self.response:
            yield el.encode('utf-8')
        if not self.plain:
            yield template.make_foot(self.linkify, self.js_for_logpage).encode('utf-8')

    def db_connect(self):
        self.conn = pymysql.connect(**settings.db)
        self.cur = self.conn.cursor()

    def db_close(self):
        self.cur.close()
        self.conn.close()

    def error_404(self):
        self.status = '404 Not Found'
        self.title = template.error_404_title
        self.navbar = (__class__.default_navbar, )
        self.response.append(template.error_404)

    def redirect(self, url, perm=False):
        self.status = '301 Moved Permanently' if perm else '302 Found'
        self.plain = True
        self.headers.append(('Location', url))

    def get_user(self, nick):
        if not self.conn:
            self.db_connect()
        user = self.cur.execute('SELECT `user_id`, `nick`, `message_count` FROM `users` WHERE `nick`=%s;', nick)
        if user:
            return self.cur.fetchone()
        else:
            return False

    def user_not_found(self, nick):
        self.status = '404 Not Found'
        self.title = template.users_user_not_found_title
        self.navbar = (__class__.default_navbar, 'users')
        self.response.append(template.users_user_not_found.format(cgi.escape(nick)))

    def check_user(self, nick):
        ''' shortcut function:
            user found: return user's info tuple
            user not found: return False and create user_not_found response
        '''
        user = self.get_user(nick)
        if not user:
            self.user_not_found(nick)
        return user

    def make_log(self, log_date, nick=None, user_id=None):
        log_from = int(log_date.timestamp())
        log_to = log_from + 86399
        if nick:
            query, params = 'SELECT `time`, `message`, `me` FROM `chat` WHERE `user`=%s AND `time` BETWEEN %s AND %s ORDER BY `message_id` ASC;', (user_id, log_from, log_to)
        else:
            query, params = 'SELECT `time`, `message`, `me`, `nick` FROM `chat` INNER JOIN `users` ON `chat`.`user`=`users`.`user_id` WHERE `chat`.`time` BETWEEN %s AND %s ORDER BY `chat`.`message_id` ASC;', (log_from, log_to)
        self.cur.execute(query, params);
        log = []
        for numb, message_tuple in enumerate(self.cur.fetchall(), 1):   # message_tuple = (time, message, me[, nick])
            current_nick = nick if nick else message_tuple[3]
            nick_formatted = (template.log_nick_me if message_tuple[2] else template.log_nick_normal).format('/users/{}/'.format(urllib.parse.quote(current_nick)), cgi.escape(current_nick))
            log.append(template.log_line.format(numb, datetime.datetime.fromtimestamp(message_tuple[0]), nick_formatted, cgi.escape(message_tuple[1])))
        return ''.join(log)

    def make_log_navbar(self, log_date, link_format):
        prev_day = log_date - datetime.timedelta(days=1)
        next_day = log_date + datetime.timedelta(days=1)
        return (    ('#;log-bottom', template.nav_down),
                    ('#;log-top', template.nav_up),
                    (link_format.format(prev_day), template.nav_left),
                    (link_format.format(next_day), template.nav_right)
        )

    def make_datetime(self, year, month, day):
        try:
            return datetime.datetime(int(year), int(month), int(day))
        except ValueError:
            return False

    @Path.add('/')
    def main(self):
        self.title = template.main_title
        self.navbar = (__class__.default_navbar, 'main')
        self.response.append(template.main)

    @Path.add('/log')
    def log_redirect(self):
        self.redirect(datetime.date.today().strftime('/log/%Y/%m/%d/'))

    @Path.add('/log/{year:d:4}/{month:d:2}/{day:d:2}')
    def log(self, year, month, day):
        log_date = self.make_datetime(year, month, day)
        if not log_date:
            self.error_404()
            return
        self.title = template.log_title.format(log_date)
        self.linkify = '.log-message'
        self.js_for_logpage = True
        self.db_connect()
        log_navbar = self.make_log_navbar(log_date, '/log/{:%Y/%m/%d}/')
        self.navbar = (__class__.default_navbar, 'log', log_navbar)
        log = self.make_log(log_date)
        self.response.append(template.log.format(log_date, log))

    @Path.add('/users')
    def users_list(self):
        self.title = template.users_title
        self.db_connect()
        self.cur.execute('SELECT COUNT(*) FROM `users`;')
        total_users = self.cur.fetchone()[0]
        self.cur.execute('SELECT COUNT(*) FROM `chat`;')
        total_messages = self.cur.fetchone()[0]
        self.cur.execute('SELECT `nick`, `message_count` FROM `users` ORDER BY `message_count` DESC LIMIT 100;');
        top_users = []
        for position, top_user in enumerate(self.cur.fetchall(), 1):
            top_users.append(template.users_row.format(position, '/users/{}/'.format(urllib.parse.quote(top_user[0])), cgi.escape(top_user[0]), top_user[1], top_user[1]/total_messages))
        self.navbar = (__class__.default_navbar, 'users')
        self.response.append(template.users.format(total_users, total_messages, ''.join(top_users)))

    @Path.add('/users/{nick}')
    def user_info(self, nick):
        user = self.check_user(nick)
        if user:
            user_id, nick, message_count = user
            self.title = template.users_user_title.format(cgi.escape(nick))
            self.linkify = '.bg-info'
            self.cur.execute('SELECT @first := MIN(`message_id`), @last := MAX(`message_id`) FROM `chat` WHERE `user`=%s;', user_id)
            self.cur.execute('SELECT `time`, `message` FROM `chat` WHERE `message_id`=@first or `message_id`=@last;')
            result = self.cur.fetchone()
            fst_time = datetime.datetime.fromtimestamp(result[0])
            fst_text = result[1]
            fst_message = template.users_user_info_message.format('/log/{0:%Y/%m/%d}/'.format(fst_time), fst_time, fst_text)
            if message_count > 1:
                result = self.cur.fetchone()
                lst_time = datetime.datetime.fromtimestamp(result[0])
                lst_text = result[1]
                lst_message = template.users_user_info_message.format('/log/{0:%Y/%m/%d}/'.format(lst_time), lst_time, lst_text)
                messages = template.users_user_info_fst + fst_message + template.users_user_info_lst + lst_message
            else:
                messages = fst_message
            user_navbar = (('user', '/users/{}/'.format(urllib.parse.quote(nick)), cgi.escape(nick)),)
            self.navbar = (__class__.default_navbar + user_navbar, 'user')
            user_info = template.users_user_info.format(cgi.escape(nick), message_count, messages)
            self.response.append(user_info)

    @Path.add('/users/{nick}/log')
    def user_log_redirect(self, nick):
        user = self.check_user(nick)
        if user:
            self.redirect('/users/{0}/log/{1:%Y/%m/%d}/'.format(urllib.parse.quote(nick), datetime.date.today()))

    @Path.add('/users/{nick}/log/{year:d:4}/{month:d:2}/{day:d:2}')
    def user_log(self, nick, year, month, day):
        user = self.check_user(nick)
        if user:
            log_date = self.make_datetime(year, month, day)
            if not log_date:
                self.error_404()
                return
            user_id, nick, message_count = user
            self.title = template.users_user_log_title.format(nick, log_date)
            self.linkify = '.log-message'
            self.js_for_logpage = True
            log_navbar = self.make_log_navbar(log_date, '/users/'+urllib.parse.quote(nick)+'/log/{:%Y/%m/%d}/')
            user_navbar = (('user', '/users/{}/'.format(urllib.parse.quote(nick)), cgi.escape(nick)),)
            self.navbar = (__class__.default_navbar + user_navbar, 'user', log_navbar)
            user_log = self.make_log(log_date, nick, user_id)
            self.response.append(template.users_user_log.format(nick, log_date, user_log))

    @Path.add('/api')
    def api(self):
        self.plain = True
        self.response.append('API. Just API.')

    @Path.add('/api/{method}')
    def api_method(self, method):
        if method == 'post':
            self.plain = True
            if self.environ['REQUEST_METHOD'] == 'POST':
                try:
                    req_body_size = int(self.environ.get('CONTENT_LENGTH', 0)) # может быть пустой строкой, не существовать вообще или == '0'
                except ValueError:
                    req_body_size = 0
                req_body = self.environ['wsgi.input'].read(req_body_size).decode()
                try:   # отлавливаем сообщения в юникоде
                    post_data = urllib.parse.parse_qs(req_body, encoding='utf-8', errors='strict')
                except UnicodeDecodeError:
                    post_data = urllib.parse.parse_qs(req_body, encoding=settings.post_encoding, errors='replace')
                try:
                    time = int(post_data['time'][0])
                    me = int(post_data['me'][0])
                    if post_data['token'][0] != settings.post_token: raise ValueError
                    user = post_data['user'][0]
                    message = post_data['message'][0]
                except (KeyError, ValueError):
                    self.response.append('error')
                else:
                    self.db_connect()
                    self.cur.execute('INSERT INTO `users` SET `nick`=%s, `message_count`=1 ON DUPLICATE KEY UPDATE `user_id`=LAST_INSERT_ID(`user_id`), `message_count`=`message_count`+1;', user);
                    self.cur.execute('INSERT INTO `chat` (`time`, `user`, `message`, `me`) VALUES (%s, LAST_INSERT_ID(), %s, %s);', (time, message, me))
                    self.response.append('OK')
        else:
            self.error_404()
