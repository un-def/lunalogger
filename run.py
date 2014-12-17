#!/usr/bin/env python
# -*- coding: utf-8 -*-
import traceback, sys
def application(environ, start_response):
    try:
        import lunalogger
        return lunalogger.LoggerApp(environ, start_response)
    except:
        status = '500 Internal Server Error'
        response_headers = [('Content-type', 'text/plain; charset=utf-8')]
        start_response(status, response_headers)
        exc = traceback.format_exception(*sys.exc_info())
        return (s.encode('utf-8') for s in exc)
