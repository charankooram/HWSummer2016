#!/usr/bin/env python3
"""Create JSON from a directory of HTML and text for later insertion into Solr

Takes about 75 minutes to run on docs.hortonworks.com content

For usage, run:
    python3 mirror-dirs.py --help

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

import argparse
import codecs
import json
import logging
import os
import re
import time
import urllib.parse
import lxml.html

__version__ = '0.0.5'

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
    ARGS.in_dir = ARGS.in_dir[:-1] # Remove last character

# https://docs.python.org/3/library/logging.html#levels
ARGS.verbosity *= 10 # debug, info, warning, error, critical

# Set up logging
# To monitor progress, tail the log file or use /usr/bin/less in F mode
logging.basicConfig(
    format='%(asctime)s %(levelname)8s %(message)s', filemode='w',
    filename=ARGS.logfile)
logging.getLogger().setLevel(ARGS.verbosity)


def mirror_dirs(src_dir, dest_dir):
    """Recurse src_dir to mirror text and HTML files in dest_dir as JSON files."""

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
            extensions = ['.html', '.htm', '.txt']

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

            # Write JSON as UTF-8
            with codecs.open(dest_path, mode='w', encoding='UTF-8') as file_handle:
                json.dump(pydict, file_handle, ensure_ascii=False)


def text_to_json(text_file, path_prefix=''):
    """Parse text and return a dictionary that can be converted to a JSON file."""

    # Get file modification date
    datetime = get_datetime(text_file)

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

    dictionary = {'url': url, 'title': title, 'text': text, 'date': datetime}

    # Update dictionary with metadata from the file path
    path_dictionary = parse_path(text_file)
    dictionary.update(path_dictionary)

    return dictionary


def normalize_whitespace(text):
    """Collapses whitespace runs to a single space, trims leading and trailing spaces."""
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text


def trim_prefix(string, prefix):
    """Remove prefix from string."""
    if string.startswith(prefix):
        return string[len(prefix):]
    else:
        return string


def parse_path(path):
    """Get product, release, and book name from path"""

    path_metadata = {}

    # Look for paths like HDPDocuments/SS1/SmartSense-1.2.2/bk_smartsense_admin
    # and HDPDocuments/HDP2/HDP-2.3-yj/bk_cluster-planning-guide
    std_path = re.search(r"""
        HDPDocuments / ([^/]+) / \w+ - ([-.\w]+) / (?: ds_ | bk_ ) ([^/]+) /
        """, path, flags=re.X)
    if std_path and std_path.group(1) and std_path.group(2) and std_path.group(3):
        path_metadata['product'] = std_path.group(1)
        path_metadata['release'] = std_path.group(2)
        path_metadata['booktitle'] = std_path.group(3)

    # Look for paths like HDPDocuments/HDP2/HDP-2.2.4-Win/bk_Clust_Plan_Gd_Win
    win_new_path = re.search(r"""
        HDPDocuments / HDP[12] / \w+ - ([.\w]+) - Win / (?: ds_ | bk_ ) ([^/]+) /
        """, path, flags=re.X)
    if win_new_path and win_new_path.group(1) and win_new_path.group(2):
        path_metadata['product'] = 'HDP-Win'
        path_metadata['release'] = win_new_path.group(1)
        path_metadata['booktitle'] = win_new_path.group(2)

    # Look for paths like HDPDocuments/HDP1/HDP-Win-1.1/bk_cluster-planning-guide
    win_old_path = re.search(r"""
        HDPDocuments / HDP[12] / HDP-Win - ([.\w]+) / (?: ds_ | bk_ ) ([^/]+) /
        """, path, flags=re.X)
    if win_old_path and win_old_path.group(1) and win_old_path.group(2):
        path_metadata['product'] = 'HDP-Win'
        path_metadata['release'] = win_old_path.group(1)
        path_metadata['booktitle'] = win_old_path.group(2)

    # Look for paths like HDPDocuments/Ambari-1.5.0.0/bk_ambari_security
    ambari_path = re.search(r"""
        HDPDocuments / Ambari - ([.\w]+) / (?: ds_ | bk_ ) ([^/]+) /
        """, path, flags=re.X)
    if ambari_path and ambari_path.group(1) and ambari_path.group(2):
        path_metadata['product'] = 'Ambari'
        path_metadata['release'] = ambari_path.group(1)
        path_metadata['booktitle'] = ambari_path.group(2)

    return path_metadata


def get_datetime(path):
    """Return UTC file modification date in datetime format."""
    since_epoch = os.path.getmtime(path)
    utc_time = time.gmtime(since_epoch)
    datetime = time.strftime('%Y-%m-%dT%H:%M:%S', utc_time)
    return datetime


def get_text(element):
    """Gets text from elements, especially the text after child elements (tails)."""

    if (not isinstance(element, lxml.html.HtmlElement) and
            not isinstance(element, lxml.html.FormElement) and
            not isinstance(element, lxml.html.InputElement)):
        return ''
    if element.tag == 'script' or element.tag == 'style':
        return ''
    text = ''

    # Combination of 'caption', 'tbody', and 'thead' plus
    # https://www.w3.org/TR/CSS21/sample.html#q22.0 and
    # https://developer.mozilla.org/en-US/docs/Web/HTML/Block-level_elements
    html_blocks = ['address', 'article', 'aside', 'blockquote', 'body',
                   'canvas', 'center', 'dd', 'dir', 'div', 'dl', 'dt',
                   'fieldset', 'figcaption', 'figure', 'footer', 'form',
                   'frame', 'frameset', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                   'header', 'hgroup', 'hr', 'html', 'li', 'main', 'menu',
                   'nav', 'noframes', 'noscript', 'ol', 'output', 'p',
                   'pre', 'section', 'table', 'tfoot', 'ul', 'video',
                   'caption', 'tbody', 'thead']

    if element.text:
        text += element.text

    for child in element.iterchildren():
        text += get_text(child)

    if element.tail:
        text += element.tail

    if element.tag in html_blocks:
        text = ' ' + text + ' '

    return text


def html_to_json(html_path, path_prefix):
    """Parse HTML and return a dictionary that can be converted to a JSON file."""

    dictionary = {}
    section_numbering_characters = '0123456789.  ' # nonbreaking space included

    # Parse page
    etree = lxml.html.parse(html_path)

    # Process meta elements
    for meta in etree.xpath("//meta"):
        attribs = meta.attrib
        if 'name' in attribs and 'content' in attribs:
            meta_name = attribs.get('name').lower().strip()
            meta_content = attribs.get('content')
            meta_content = normalize_whitespace(meta_content)
            dictionary[meta_name] = meta_content

    # Get page title
    title = etree.xpath("//title")
    if title:
        title = get_text(title[0])
    else:
        title = 'no title'
    title = normalize_whitespace(title)
    title = trim_prefix(title, 'Chapter')
    title = title.lstrip(section_numbering_characters)
    dictionary['title'] = title

    # Get text from areas representing priority content
    # Matches in this content should cause the document to rank higher
    priority_content = ['//h1', '//h2', '//h3', '//h4', '//h5', '//h6',
                        '//title', "//caption", "//figcaption"]
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

    # Get page content
    content = etree.xpath("/html/body/div[@id='content']")
    if content:
        text = get_text(content[0])
    else:
        text = get_text(etree.getroot())
    text = normalize_whitespace(text)
    dictionary['text'] = text

    # Convert file system path to URL syntax
    trimed_path = trim_prefix(html_path, path_prefix)
    url_escaped_path = urllib.parse.quote(trimed_path)
    dictionary['url'] = url_escaped_path

    # Get file modification date
    datetime = get_datetime(html_path)
    dictionary['date'] = datetime

    # Update dictionary with metadata from the file path
    path_metadata = parse_path(html_path)
    dictionary.update(path_metadata)

    return dictionary


# Command-line interface
if __name__ == '__main__':
    mirror_dirs(ARGS.in_dir, ARGS.out_dir)
