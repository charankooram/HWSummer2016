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

__version__ = '0.0.3'

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
                # pydict = html_to_json(src_path)
                pydict = htmlTojsonConverter(src_path)

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


def htmlTojsonConverter(filepath):
    """Parse HTML and return a dictionary that can be converted to a JSON file."""
    isBody = False
    str = ''
    dumpedDict = dict()

    tree = html.parse(filepath)
    root = tree.getroot()

    if root == None:
        return dict()

    for element in root.iter():
        if isBody == False :

            # Process meta elements
            if element.tag == 'meta' :
                attribList = element.attrib
                if 'name' in attribList and 'content' in attribList:
                    dumpedDict[attribList.get('name')] = attribList.get('content')

            # Process title element
            elif element.tag == 'title':
                dumpedDict['title'] = element.text
            elif element.tag == 'body':
                isBody = True

        # Process elements in body element
        elif isBody == True :
            if(element.text):
                str = str + ' ' + element.text
                dumpedDict['text'] = str

    # Convert file system path to URL syntax
    trimed_path = trim_prefix(filepath, path_prefix)
    url_escaped_path = urllib.parse.quote(trimed_path)   
    dumpedDict['url'] = url_escaped_path

    # Get file modification date
    datetime = get_datetime(filepath)
    dumpedDict['date'] = datetime

    # Update dictionary with metadata from the file path
    path_metadata = parse_path(filepath)
    dumpedDict.update(path_metadata)

    return dumpedDict


# Command-line interface
# TODO Use https://docs.python.org/3/library/getopt.html
if __name__ == '__main__':
    mirror_dirs(sys.argv[1], sys.argv[2])
