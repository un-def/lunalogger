#!/usr/bin/env python
# -*- coding: utf-8 -*-
import traceback, sys
def application(environ, start_response):
    try:
        from lunalogger import LoggerApp
        import middleware
        import settings
        app = middleware.PermCache(LoggerApp) if settings.mw_permcache['enabled'] else LoggerApp
        return app(environ, start_response)
    except:
        status = '500 Internal Server Error'
        response_headers = [('Content-type', 'text/plain; charset=utf-8')]
        start_response(status, response_headers)
        exc = traceback.format_exception(*sys.exc_info())
        return (s.encode('utf-8') for s in exc)
