#!/usr/bin/env python3
"""Create JSON from a directory of HTML and text for later insertion into Solr

Takes about an hour to run on docs.hortonworks.com content

usage:
    python3 mirror-dirs.py <src_dir> <dest_dir>

Questions: Robert Crews <rcrews@hortonworks.com>

Use tar.bz2 to compress resulting JSON:
    $ du -sh docs.hortonworks.com-json
    908M    docs.hortonworks.com-json
    $ tar cfy docs.hortonworks.com-json.tar.bz2 docs.hortonworks.com-json && \
      zip -qDXr docs.hortonworks.com-json.zip docs.hortonworks.com-json
    $ ls -lh *-json.*
    -rw-r--r--   1 rcrews  staff    49M Jun  6 11:20 docs.hortonworks.com-json.tar.bz2
    -rw-r--r--   1 rcrews  staff   215M Jun  6 11:24 docs.hortonworks.com-json.zip
"""

__version__ = '0.0.4'

import codecs, html, json, logging, os, re, sys, time, urllib.parse
from lxml import html

# Set up logging
# To monitor progress, tail the log file or use less in F mode
logfile, _ = os.path.splitext(os.path.basename(__file__))
logging.basicConfig(
    format='%(asctime)s %(levelname)8s %(message)s', filemode='w',
    filename=logfile + '.log')
logging.getLogger().setLevel(logging.INFO)


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

            # In JSON, include the URL only from the web root. We can add the
            # authority (e.g., the domain, i.e., docs.hortonworks.com) in
            # JavaScript when reading the JSON
            if sys.argv[1]:
                if sys.argv[1].endswith('/'):
                    path_prefix = sys.argv[1][:-1] # Remove last character
                else:
                    path_prefix = sys.argv[1]
            else:
                path_prefix = ''

            # Use different parsers for files with different extensions
            if extension == '.txt':
                pydict = text_to_json(src_path, path_prefix)
            else:
                pydict = html_to_json(src_path, path_prefix)

            # Write JSON as UTF-8
            with codecs.open(dest_path, mode='w', encoding='UTF-8') as fp:
                json.dump(pydict, fp, ensure_ascii=False)


def text_to_json(text_file, path_prefix=''):
    """Parse text and return a dictionary that can be converted to a JSON file."""

    # Get file modification date
    datetime = get_datetime(text_file)

    # Read text files as cp1252, ignoring errors
    with codecs.open(text_file, mode='r', encoding='cp1252', errors='ignore') as fp:
        content = fp.read()

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
    text = text.strip();
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
    m1 = re.search(r"""
        HDPDocuments / ([^/]+) / \w+ - ([-.\w]+) / (?: ds_ | bk_ ) ([^/]+) /
        """, path, flags=re.X)
    if m1 and m1.group(1) and m1.group(2) and m1.group(3):
        path_metadata['product'] = m1.group(1)
        path_metadata['release'] = m1.group(2)
        path_metadata['booktitle'] = m1.group(3)

    # Look for paths like HDPDocuments/HDP2/HDP-2.2.4-Win/bk_Clust_Plan_Gd_Win
    m2 = re.search(r"""
        HDPDocuments / HDP[12] / \w+ - ([.\w]+) - Win / (?: ds_ | bk_ ) ([^/]+) /
        """, path, flags=re.X)
    if m2 and m2.group(1) and m2.group(2):
        path_metadata['product'] = 'HDP-Win'
        path_metadata['release'] = m2.group(1)
        path_metadata['booktitle'] = m2.group(2)

    # Look for paths like HDPDocuments/HDP1/HDP-Win-1.1/bk_cluster-planning-guide
    m3 = re.search(r"""
        HDPDocuments / HDP[12] / HDP-Win - ([.\w]+) / (?: ds_ | bk_ ) ([^/]+) /
        """, path, flags=re.X)
    if m3 and m3.group(1) and m3.group(2):
        path_metadata['product'] = 'HDP-Win'
        path_metadata['release'] = m3.group(1)
        path_metadata['booktitle'] = m3.group(2)

    # Look for paths like HDPDocuments/Ambari-1.5.0.0/bk_ambari_security
    m4 = re.search(r"""
        HDPDocuments / Ambari - ([.\w]+) / (?: ds_ | bk_ ) ([^/]+) /
        """, path, flags=re.X)
    if m4 and m4.group(1) and m4.group(2):
        path_metadata['product'] = 'Ambari'
        path_metadata['release'] = m4.group(1)
        path_metadata['booktitle'] = m4.group(2)
    
    return path_metadata


def get_datetime(path):
    """Return UTC file modification date in datetime format."""
    since_epoch = os.path.getmtime(path)
    utc_time = time.gmtime(since_epoch)
    datetime = time.strftime('%Y-%m-%dT%H:%M:%S', utc_time)
    return datetime


def html_to_json(filepath, path_prefix):
    """Parse HTML and return a dictionary that can be converted to a JSON file."""
    
    # Python style notes:
    # Never use tabs. Always use 4 space indents
    # Never put a space before a colon or a comma
    # Use python_style variable names. Don't use javaStyle variable names.
    #  See http://pep8.org/#prescriptive-naming-conventions
    # Make sure there are no spaces or tabs after a line.
    # Two returns before each def
    # Separate related commands by single returns
    # See http://pep8.org/  

    is_body = False
    str = ''
    dumped_dict = dict()

    # Combination of
    # https://www.w3.org/TR/CSS21/sample.html#q22.0 and
    # https://developer.mozilla.org/en-US/docs/Web/HTML/Block-level_elements
    html_blocks = ['address', 'article', 'aside', 'blockquote', 'body',
        'canvas', 'center', 'dd', 'dir', 'div', 'dl', 'dt', 'fieldset',
        'figcaption', 'figure', 'footer', 'form', 'frame', 'frameset', 'h1',
        'h2', 'h3', 'h4', 'h5', 'h6', 'header', 'hgroup', 'hr', 'html',
        'li', 'main', 'menu', 'nav', 'noframes', 'noscript', 'ol', 'output',
        'p', 'pre', 'section', 'table', 'tfoot', 'ul', 'video']

    tree = html.parse(filepath)
    root = tree.getroot()

    if root == None:
        return dict()

    for element in root.iter():
        if is_body == False:

            # Process meta elements
            if element.tag == 'meta':
                attrib_list = element.attrib
                if 'name' in attrib_list and 'content' in attrib_list:
                    dumped_dict[attrib_list.get('name')] = attrib_list.get('content')

            # Process title element
            # TODO: Need to account for bad HTML that has elements inside title
            elif element.tag == 'title':
                title = element.text
                title = normalize_whitespace(title)
                title = trim_prefix(title, 'Chapter')
                title = title.lstrip(' 0123456789.') # Remove section number, if present
                dumped_dict['title'] = title

            elif element.tag == 'body':
                is_body = True

        # Process elements in body element
        elif is_body == True:
            if element.tag in html_blocks:
                element_separator = ' '
            else:
                element_separator = ''
            str = str + element_separator

            # TODO Problem: The code as written only gets the first text node in an
            # element. Needs to be updated to get all text nodes. For example:
            # <p>For <span class="bold"><strong>Oracle</strong></span>:</p>
            # should return   For Oracle:
            # but currently returns    ForOracle
            # The colon -- the second text node in the p element -- is missing.
            # Also, need to check to see why the space after For is missing.
            # docs.hortonworks.com/HDPDocuments/Ambari-1.5.0.0/bk_ambari_reference/content/ambari-chaplast-1.html
            # docs.hortonworks.com-json/HDPDocuments/Ambari-1.5.0.0/bk_ambari_reference/content/ambari-chaplast-1_html.json

            # TODO: Need to account for text directly in body, text not an element in body
    
            # TODO If /html/body/div[@id='content'], then only get that element
            # Especially, exclude //div[@class='legal'] and //div[@id='leftnavigation']
    
            # TODO Exclude comments. Not sure why <!--jQuery plugin for glossary popups. -->
            # is appearing in the JSON. I think the parser should automatically remove
            # comments.

            if element.text:
                str = str + element.text
                str = normalize_whitespace(str)
                dumped_dict['text'] = str

    # Convert file system path to URL syntax
    trimed_path = trim_prefix(filepath, path_prefix)
    url_escaped_path = urllib.parse.quote(trimed_path)   
    dumped_dict['url'] = url_escaped_path

    # Get file modification date
    datetime = get_datetime(filepath)
    dumped_dict['date'] = datetime

    # Update dictionary with metadata from the file path
    path_metadata = parse_path(filepath)
    dumped_dict.update(path_metadata)

    return dumped_dict


# Command-line interface
# TODO Use https://docs.python.org/3/library/getopt.html
if __name__ == '__main__':
    mirror_dirs(sys.argv[1], sys.argv[2])
