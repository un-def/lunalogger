# -*- coding: utf-8 -*-

# general
db = {  #'host': 'localhost',
        'unix_socket': '/var/run/mysqld/mysqld.sock',
        'user': 'user',
        'passwd': 'password',
        'database': 'dc_test',
        'charset': 'utf8'
}
append_slash = True   # редиректить при отсутствии конечного / на url с /
title_sitename = 'lunalogger'
title_separator = ' :: '
post_encoding = 'windows-1251'
post_token = 'verysecrettoken'

# middleware
mw_permcache = {'enabled': True,
                'cache_dir': 'cache',
                'chunk_size': 8192
}
