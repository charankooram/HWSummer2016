#!/usr/bin/env python3
"""Create Solr JSON from a directory of HTML and text files

Takes about 75 minutes to run on docs.hortonworks.com content.

For usage, run:
    python3 jsonify.py --help

Questions: Robert Crews <rcrews@hortonworks.com>

Use tar.bz2 to compress the resulting JSON:
    $ du -sh docs.hortonworks.com-json && \
      tar cfy docs.hortonworks.com-json.tar.bz2 docs.hortonworks.com-json && \
      zip -qDXr docs.hortonworks.com-json.zip docs.hortonworks.com-json && \
      ls -lh *-json.*
    853M	docs.hortonworks.com-json
    -rw-r--r--  1 rcrews  staff    50M Jun 11 11:13 docs.hortonworks.com-json.tar.bz2
    -rw-r--r--  1 rcrews  staff   192M Jun 11 11:13 docs.hortonworks.com-json.zip
"""

__version__ = '0.0.6'

import argparse
import codecs
import json
import logging
import os
import re
import time
import urllib.parse
import lxml.html


def mirror_dirs(src_dir, dest_dir):
    """Recurse src_dir to mirror text and HTML files in dest_dir as JSON files."""
    assert isinstance(src_dir, str), (
        'src_dir is not a string: %r' % src_dir)
    assert isinstance(dest_dir, str), (
        'path_prefix is not a string: %r' % dest_dir)

    # Fatal error if dest_dir exists. User is forced to either move or
    # delete the existing output directory before continuing.
    os.mkdir(dest_dir)
    logging.info(dest_dir)

    for item in os.listdir(src_dir):
        src_path = os.path.join(src_dir, item)

        if os.path.isdir(src_path):

            # Recurse into different directoires
            dest_path = os.path.join(dest_dir, item)
            mirror_dirs(src_path, dest_path)
        else:

            # Consider only files with these extensions for conversion to JSON
            extensions = ('.html', '.htm', '.txt')

            # If this is a file we want to process, set up JSON file path
            _, extension = os.path.splitext(item)
            if extension in extensions:
                new_item = item.replace('.', '_') + '.json'
                dest_path = os.path.join(dest_dir, new_item)
            else:
                continue

            # Use different parsers for files with different extensions
            if extension == '.txt':
                pydict = text_to_json(src_path, ARGS.in_dir)
            else:
                pydict = html_to_json(src_path, ARGS.in_dir)

            pydict['stream_size'] = os.path.getsize(src_path)
            pydict['date'] = get_datetime(src_path)
            pydict['x_parsed_by'] = ('com.hortonworks.techpubs.' +
                                     os.path.basename(__file__) +
                                     ', v' + __version__)

            # Write JSON as UTF-8
            with codecs.open(dest_path, mode='w', encoding='UTF-8') as file_handle:
                json.dump(pydict, file_handle, ensure_ascii=False)


def text_to_json(text_file, path_prefix=''):
    """Parse text and return a dictionary that can be converted to a JSON file."""
    assert isinstance(text_file, str), (
        'html_path is not a string: %r' % text_file)
    assert isinstance(path_prefix, str), (
        'path_prefix is not a string: %r' % path_prefix)

    # Read text files as cp1252, ignoring errors
    with codecs.open(text_file, mode='r', encoding='cp1252', errors='ignore') as file_h:
        content = file_h.read()

    # Convert file system path to URL syntax
    trimed_path = trim_prefix(text_file, path_prefix)
    url_escaped_path = urllib.parse.quote(trimed_path)
    url = url_escaped_path

    # Use the file name as the document title
    title = os.path.basename(text_file)

    # After compressing whitespace, take all the content of the file for indexing
    text = normalize_whitespace(content)

    dictionary = {'url': url, 'title': title, 'text': text}

    # Update dictionary with metadata from the file path
    dictionary.update(parse_path(text_file))

    return dictionary


def normalize_whitespace(text):
    """Collapses whitespace runs to a single space, trims leading and trailing spaces."""
    assert isinstance(text, str), (
        'text is not a string: %r' % text)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text


def trim_prefix(original, prefix):
    """Remove prefix from string."""
    assert isinstance(original, str), (
        'original is not a string: %r' % original)
    assert isinstance(prefix, str), (
        'prefix is not a string: %r' % prefix)
    if original.startswith(prefix):
        return original[len(prefix):]
    else:
        return original


def trim_suffix(original, suffix):
    """Remove suffix from string."""
    assert isinstance(original, str), (
        'original is not a string: %r' % original)
    assert isinstance(suffix, str), (
        'suffix is not a string: %r' % suffix)
    if original.endswith(suffix):
        return original[:-len(suffix)]
    else:
        return original


def standardize_release(relnum):
    """Assure all release numbers have four parts, by appending zeros if necessary"""
    assert isinstance(relnum, str), (
        'relnum is not a string: %r' % relnum)
    parts = relnum.split('.')
    while len(parts) < 4:
        parts.append('0')
    return '.'.join(parts)


def standardize_product(abbrev):
    """Use best product names"""
    assert isinstance(abbrev, str), (
        'abbrev is not a string: %r' % abbrev)
    if abbrev.startswith('HDP'):
        abbrev = 'Data Platform'
    if abbrev.startswith('HDP-Win'):
        abbrev = 'Data Platform for Windows'
    if abbrev.startswith('HDF'):
        abbrev = 'DataFlow'
    if abbrev.startswith('SS'):
        abbrev = 'SmartSense'
    if abbrev.startswith('Cldbrk'):
        abbrev = 'Cloudbreak'
    return abbrev


def std_path(match):
    """Get product, version, and book title from path, where possible"""
    assert isinstance(match, type(re.match('', ''))), (
        'match is not a re.match: %r' % match)
    metadata = {}
    metadata['product'] = match.group('p')
    metadata['release'] = match.group('r')
    metadata['booktitle'] = match.group('b')
    return metadata


def hdp_23_yj_path(match):
    """Get product, version, and book title from path, where possible"""
    assert isinstance(match, type(re.match('', ''))), (
        'match is not a re.match: %r' % match)
    metadata = {}
    metadata['product'] = 'HDP'
    metadata['release'] = '2.3.0.0-yj'
    metadata['booktitle'] = match.group('b')
    return metadata


def win_new_path(match):
    """Get product, version, and book title from path, where possible"""
    assert isinstance(match, type(re.match('', ''))), (
        'match is not a re.match: %r' % match)
    metadata = {}
    metadata['product'] = 'HDP-Win'
    metadata['release'] = match.group('r')
    metadata['booktitle'] = match.group('b')
    return metadata


def win_old_path(match):
    """Get product, version, and book title from path, where possible"""
    assert isinstance(match, type(re.match('', ''))), (
        'match is not a re.match: %r' % match)
    metadata = {}
    metadata['product'] = 'HDP-Win'
    metadata['release'] = match.group('r')
    metadata['booktitle'] = match.group('b')
    return metadata


def ambari_path(match):
    """Get product, version, and book title from path, where possible"""
    assert isinstance(match, type(re.match('', ''))), (
        'match is not a re.match: %r' % match)
    metadata = {}
    metadata['product'] = 'Ambari'
    metadata['release'] = match.group('r')
    metadata['booktitle'] = match.group('b')
    return metadata


def std_path_index(match):
    """Get product, version, and book title from path, where possible"""
    assert isinstance(match, type(re.match('', ''))), (
        'match is not a re.match: %r' % match)
    metadata = {}
    metadata['product'] = match.group('p')
    metadata['release'] = match.group('r')
    return metadata


def win_new_index(match):
    """Get product, version, and book title from path, where possible"""
    assert isinstance(match, type(re.match('', ''))), (
        'match is not a re.match: %r' % match)
    metadata = {}
    metadata['product'] = 'HDP-Win'
    metadata['release'] = match.group('r')
    return metadata


def win_old_index(match):
    """Get product, version, and book title from path, where possible"""
    assert isinstance(match, type(re.match('', ''))), (
        'match is not a re.match: %r' % match)
    metadata = {}
    metadata['product'] = 'HDP-Win'
    metadata['release'] = match.group('r')
    return metadata


def ambari_path_index(match):
    """Get product, version, and book title from path, where possible"""
    assert isinstance(match, type(re.match('', ''))), (
        'match is not a re.match: %r' % match)
    metadata = {}
    metadata['product'] = 'Ambari'
    metadata['release'] = match.group('r')
    return metadata


def product_index(match):
    """Get product, version, and book title from path, where possible"""
    assert isinstance(match, type(re.match('', ''))), (
        'match is not a re.match: %r' % match)
    metadata = {}
    metadata['product'] = match.group('p')
    return metadata


def parse_path(path):
    """Get product, release, and book name from path"""
    assert isinstance(path, str), (
        'path is not a string: %r' % path)

    regex = {}

    # Paths like HDPDocuments/SS1/SmartSense-1.2.2/bk_smartsense_admin/
    regex['std_path'] = re.compile(r"""
        HDPDocuments/[^/]+/ (?P<p>\w+) - (?P<r>[.\w]+) /(?:ds_|bk_)? (?P<b>[^/]+) /
        """, flags=re.X)

    # Paths like HDPDocuments/HDP2/HDP-2.3-yj/bk_hadoop-ha/
    regex['hdp_23_yj_path'] = re.compile(r"""
        HDPDocuments/HDP2/HDP-2.3-yj/(?:ds_|bk_)? (?P<b>[^/]+) /
        """, flags=re.X)

    # Paths like HDPDocuments/HDP2/HDP-2.2.4-Win/bk_Clust_Plan_Gd_Win/
    regex['win_new_path'] = re.compile(r"""
        HDPDocuments/[^/]+/HDP- (?P<r>[.\w]+) -Win /(?:ds_|bk_)? (?P<b>[^/]+) /
        """, flags=re.X)

    # Paths like HDPDocuments/HDP1/HDP-Win-1.1/bk_cluster-planning-guide/
    regex['win_old_path'] = re.compile(r"""
        HDPDocuments/[^/]+/HDP-Win- (?P<r>[.\w]+) / (?:ds_|bk_)? (?P<b>[^/]+) /
        """, flags=re.X)

    # Paths like HDPDocuments/Ambari-1.5.0.0/bk_ambari_security/
    regex['ambari_path'] = re.compile(r"""
        HDPDocuments/Ambari- (?P<r>[.\w]+) / (?:ds_|bk_)? (?P<b>[^/]+) /
        """, flags=re.X)

    # Paths like HDPDocuments/Ambari/Ambari-2.2.2.0/index.html
    regex['std_path_index'] = re.compile(r"""
        HDPDocuments/[^/]+/ (?P<p>\w+) - (?P<r>[.\w]+) /[^/]+(?:[.]html?|[.]txt)\Z
        """, flags=re.X)

    # Paths like HDPDocuments/HDP2/HDP-2.1.15-Win/index.html
    regex['win_new_index'] = re.compile(r"""
        HDPDocuments/[^/]+/HDP- (?P<r>[.\w]+) -Win/[^/]+(?:[.]html?|[.]txt)\Z
        """, flags=re.X)

    # Paths like HDPDocuments/HDP1/HDP-Win-1.3.0/index.html
    regex['win_old_index'] = re.compile(r"""
        HDPDocuments/[^/]+/HDP-Win - (?P<r>[.\w]+) /[^/]+(?:[.]html?|[.]txt)\Z
        """, flags=re.X)

    # Paths like HDPDocuments/Ambari-1.7.0.0/index.html
    regex['ambari_path_index'] = re.compile(r"""
        HDPDocuments/Ambari- (?P<r>[.\w]+) /[^/]+(?:[.]html?|[.]txt)\Z
        """, flags=re.X)

    # Paths like HDPDocuments/SS1/index.html
    regex['product_index'] = re.compile(r"""
        HDPDocuments/(?P<p>[a-zA-Z]+) [^/]*/[^/]+(?:[.]html?|[.]txt)\Z
        """, flags=re.X)

    # Associate the complied regex keys with function names
    # (which happen to have the same name)
    process = {
        'std_path': std_path,
        'hdp_23_yj_path': hdp_23_yj_path,
        'win_new_path': win_new_path,
        'win_old_path': win_old_path,
        'ambari_path': ambari_path,
        'std_path_index': std_path_index,
        'win_new_index': win_new_index,
        'win_old_index': win_old_index,
        'ambari_path_index': ambari_path_index,
        'product_index': product_index,
    }

    path_metadata = {}

    # Call the appropriate subroutine using the "process" lookup table, above
    for key in regex:
        match = regex[key].search(path)
        if match:
            path_metadata = process[key](match)

    if 'product' in path_metadata:
        path_metadata['product'] = standardize_product(path_metadata['product'])
    if 'release' in path_metadata:
        path_metadata['release'] = standardize_release(path_metadata['release'])

    if not path_metadata:
        logging.warning('No path metadata from ' + path)
    return path_metadata


def get_datetime(path):
    """Return UTC file modification date in datetime format. See
    https://www.w3.org/TR/NOTE-datetime
    """
    assert isinstance(path, str), (
        'path is not a string: %r' % path)
    since_epoch = os.path.getmtime(path)
    utc_time = time.gmtime(since_epoch)
    datetime = time.strftime('%Y-%m-%dT%H:%M:%SZ', utc_time)
    return datetime


def get_text(element):
    """Get text from HTML elements, even text after child elements (tails)."""

    if (not isinstance(element, lxml.html.HtmlElement) and
            not isinstance(element, lxml.html.FormElement) and
            not isinstance(element, lxml.html.InputElement)):
        return ''
    if element.tag == 'script' or element.tag == 'style':
        return ''
    text = []

    # Combination of 'caption', 'tbody', and 'thead' plus
    # https://www.w3.org/TR/CSS21/sample.html#q22.0 and
    # https://developer.mozilla.org/en-US/docs/Web/HTML/Block-level_elements
    html_blocks = ('address', 'article', 'aside', 'blockquote', 'body',
                   'canvas', 'center', 'dd', 'dir', 'div', 'dl', 'dt',
                   'fieldset', 'figcaption', 'figure', 'footer', 'form',
                   'frame', 'frameset', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                   'header', 'hgroup', 'hr', 'html', 'li', 'main', 'menu',
                   'nav', 'noframes', 'noscript', 'ol', 'output', 'p',
                   'pre', 'section', 'table', 'tfoot', 'ul', 'video',
                   'caption', 'tbody', 'thead')

    if element.text:
        text.append(element.text)

    for child in element.iterchildren():
        text.append(get_text(child))  # recurse

    if element.tail:
        text.append(element.tail)

    if element.tag in html_blocks:
        return ' {0} '.format(''.join(text))
    else:
        return ''.join(text)


def get_html_metas(etree, dictionary):
    """Get name values and content values from HTML meta elements."""
    assert isinstance(dictionary, dict), (
        'dictionary is not a dictionary: %r' % dictionary)

    if etree.getroot() is None:
        logging.error('No root in etree passed to get_html_metas()')
        return {}

    for meta in etree.xpath("//meta"):
        attribs = meta.attrib
        if 'name' in attribs and 'content' in attribs:
            dictionary[attribs.get('name').lower().strip()] = (
                normalize_whitespace(attribs.get('content')))

    return dictionary


def get_html_lang(etree, dictionary):
    """Get list of explicit lang and xml:lang values from all HTML elements."""
    assert isinstance(dictionary, dict), (
        'dictionary is not a dictionary: %r' % dictionary)

    if etree.getroot() is None:
        logging.error('No root in etree passed to get_html_lang()')
        return {}

    lang_attributes = ('string(//*/@lang)', 'string(//*/@xml:lang)')
    lang_list = []
    for xpath in lang_attributes:
        lang = etree.xpath(xpath)
        lang_list.append(lang)
    dictionary['lang'] = ' '.join(lang_list)
    dictionary['lang'] = dictionary['lang'].replace('_', '-')
    dictionary['lang'] = normalize_whitespace(dictionary['lang'])
    if not dictionary['lang']:
        dictionary['lang'] = 'en'

    return dictionary


def get_html_title(etree, dictionary, section_numbering_characters):
    """Get title from HTML document."""
    assert isinstance(dictionary, dict), (
        'dictionary is not a dictionary: %r' % dictionary)

    if etree.getroot() is None:
        logging.error('No root in etree passed to get_html_title()')
        return {}

    titles = etree.xpath("//title")
    if titles:
        dictionary['title'] = get_text(titles[0])
        dictionary['title'] = normalize_whitespace(dictionary['title'])
        dictionary['title'] = trim_prefix(dictionary['title'], 'Chapter')
        dictionary['title'] = dictionary['title'].lstrip(section_numbering_characters)

    return dictionary


def get_html_priority_text(etree, dictionary, section_numbering_characters):
    """Get important text from HTML document."""
    assert isinstance(dictionary, dict), (
        'dictionary is not a dictionary: %r' % dictionary)

    if etree.getroot() is None:
        logging.error('No root in etree passed to get_html_priority_text()')
        return {}

    priority_content = ('//h1', '//h2', '//h3', '//h4', '//h5', '//h6',
                        '//title', '//caption', '//figcaption')
    priority_text_list = []
    for xpath in priority_content:
        for elem in etree.xpath(xpath):
            if isinstance(elem, lxml.html.HtmlElement):
                p_text = get_text(elem)
                p_text = p_text.lstrip(section_numbering_characters)
                priority_text_list.append(p_text)
    if 'description' in dictionary:
        priority_text_list.append(dictionary['description'])
    if 'keywords' in dictionary:
        priority_text_list.append(dictionary['keywords'])
    priority_text = ' '.join(priority_text_list)
    priority_text = normalize_whitespace(priority_text)
    dictionary['ptext'] = priority_text

    return dictionary


def get_html_text(etree, dictionary):
    """Get text from HTML document."""
    assert isinstance(dictionary, dict), (
        'dictionary is not a dictionary: %r' % dictionary)

    if etree.getroot() is None:
        logging.error('No root in etree passed to get_html_text()')
        return {}

    content = etree.xpath("/html/body/div[@id='content']")
    if content:
        dictionary['text'] = get_text(content[0])
    else:
        dictionary['text'] = get_text(etree.getroot())
    dictionary['text'] = normalize_whitespace(dictionary['text'])
    dictionary['text'] = trim_suffix(dictionary['text'], ' Legal notices')

    return dictionary


def html_to_json(html_path, path_prefix=''):
    """Parse HTML and return a dictionary that can be converted to a JSON file."""
    assert isinstance(html_path, str), (
        'html_path is not a string: %r' % html_path)
    assert isinstance(path_prefix, str), (
        'path_prefix is not a string: %r' % path_prefix)

    dictionary = {}
    section_numbering_characters = ('-.0123456789'
                                    "\N{SPACE}\N{NO-BREAK SPACE}\N{EN DASH}")
    # Parse page
    etree = lxml.html.parse(html_path)
    if etree.getroot() is None:
        logging.error('No root: ' + html_path)
        return {}

    # Get meta element values
    get_html_metas(etree, dictionary)

    # Get page languages
    get_html_lang(etree, dictionary)

    # Get page title
    get_html_title(etree, dictionary, section_numbering_characters)
    if 'title' not in dictionary:
        logging.error('No title: ' + html_path)

    # Get text from areas representing priority content
    # Matches in this content should cause the document to rank higher
    get_html_priority_text(etree, dictionary, section_numbering_characters)

    # Get page content
    get_html_text(etree, dictionary)

    # Convert file system path to URL syntax
    dictionary['url'] = trim_prefix(html_path, path_prefix)
    dictionary['url'] = urllib.parse.quote(dictionary['url'])

    # Update dictionary with metadata from the file path
    dictionary.update(parse_path(html_path))

    return dictionary


# Command-line interface
if __name__ == '__main__':

    # Get command-line arguments
    ARGPARSER = argparse.ArgumentParser()
    LOGFILE, _ = os.path.splitext(os.path.basename(__file__))
    LOGFILE += '.log'
    ARGPARSER.add_argument('-l', '--logfile', default=LOGFILE,
                           help='the log file, defaults to ./' + LOGFILE)
    ARGPARSER.add_argument('-v', '--verbosity', type=int, default=2,
                           help='message level for log', choices=[1, 2, 3, 4, 5])
    ARGPARSER.add_argument('in_dir',
                           help='directory containing text and HTML files')
    ARGPARSER.add_argument('out_dir',
                           help='nonexisting directory where JSON files will be written')
    ARGS = ARGPARSER.parse_args()

    # In JSON, include the URL only from the web root. We can add the
    # authority (e.g., the domain, i.e., docs.hortonworks.com) in
    # JavaScript when reading the JSON
    if ARGS.in_dir.endswith('/'):
        ARGS.in_dir = ARGS.in_dir[:-1]  # Remove last character

    # https://docs.python.org/3/library/logging.html#levels
    ARGS.verbosity *= 10  # debug, info, warning, error, critical

    # Set up logging
    # To monitor progress, tail the log file or use /usr/bin/less in F mode
    logging.basicConfig(
        format='%(asctime)s %(levelname)8s %(message)s', filemode='w',
        filename=ARGS.logfile)
    logging.getLogger().setLevel(ARGS.verbosity)

    mirror_dirs(ARGS.in_dir, ARGS.out_dir)
