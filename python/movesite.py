#!/usr/bin/env python3
'''
'''

import textwrap

def redirect_html(new_url='//docs.hortonworks.com'):
    """Set up JSON struct, delegate its creation, then write the JSON file to disk."""
    assert isinstance(url, str), (
        'new_url is not a string: %r' % new_url)

    print(textwrap.dedent('''\
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
          "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
        <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <meta http-equiv="refresh" content="0;URL={url}" />
        <title>File Moved</title>
        </head>
        <body>
        <h1>File Moved</h1>
        <p>Moved to <a href="{url}">{url}</a>.</p>
        </html>'''.format(**locals())))

if __name__ == '__main__':
    redirect_html()
