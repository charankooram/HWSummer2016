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

__version__ = '0.0.2'

import codecs, html, json, logging, os, re, sys, urllib.parse
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
                #pydict = html_to_json(src_path, path_prefix)
                pydict = htmlTojsonConverter(src_path, path_prefix)

            # Write JSON as UTF-8
            with codecs.open(dest_path, mode='w', encoding='UTF-8') as fp:
                json.dump(pydict, fp, ensure_ascii=False)


def text_to_json(text_file, path_prefix=''):
    """Parse text and return a dictionary that can be converted to a JSON file."""

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

    dictionary = {'url': url, 'title': title, 'text': text}

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


def html_to_json(html_file, path_prefix=''):
    """Parse HTML and return a dictionary that can be converted to a JSON file."""

    # TODO Make better html_to_json, using a real parser (such as lxml).
    # if //div[@id='content'], then only get that element
    # Especially, exclude //div[@class='legal'] and //div[@id='leftnavigation']

    # Read HTML well enough to get the charset value (e.g., the character encoding)
    with codecs.open(html_file, mode='r', encoding='cp1252', errors='ignore') as fp:
        content = fp.read()
    m = re.search(r"""
        <meta [^>]+ charset \s* = \s* ['"]? ([-\w]+)
        """, content, flags=re.X|re.M|re.S|re.I)
    if m and m.group(1):
        enc = m.group(1)

        # Aliases of cp1252 and ISO-8859-1 that HTML5 spec says to read as cp1252
        # https://encoding.spec.whatwg.org/#names-and-labels
        latin1 = re.compile(r"""
            (?: iso[-_]?8859[-_]?1 | 8859 | cp819 | latin | latin1 | L1 | ascii |
            us[-_]?ascii | windows[-_]?1251 | x[-_]?cp1251 | ansi[-_]?x3[.]4[-_]?1968 |
            cp819 | csisolatin1 | ibm819 | iso-ir-100 ) $
            """, flags=re.X|re.I)
        if latin1.match(enc):
            enc = 'cp1252'

        logging.debug('%s: %s', enc, html_file)
        try:

            # Open file with its identified encoding
            with codecs.open(html_file, mode='r', encoding=enc, errors='strict') as fp:
                content = fp.read()

        except UnicodeDecodeError:
            logging.exception('Rereading ignoring errors.')
            try:

                # Try again with identified encoding, ignoring errors
                with codecs.open(html_file, mode='r', encoding=enc,
                    errors='ignore') as fp:
                    content = fp.read()

            except UnicodeDecodeError:
                logging.exception('Finally reading as cp1252, ignoring errors.')

                # Try again, but as cp1252, ignoring errors
                with codecs.open(html_file, mode='r', encoding='cp1252',
                    errors='ignore') as fp:
                    content = fp.read()

    # Start dictionary with metadata from the file path
    dictionary = parse_path(html_file)

    # Convert file system path to URL syntax
    trimed_path = trim_prefix(html_file, path_prefix)
    url_escaped_path = urllib.parse.quote(trimed_path)
    dictionary['url'] = url_escaped_path

    # Use regular expressions and other tricks to get the page title
    m = re.search(r"""
        <title> (.+?) </title>
        """, content, flags=re.X|re.M|re.S|re.I)
    if m and m.group(1):
        title = m.group(1)
    else:
        title = 'no title'
    title = re.sub(r"""
        < .*? >
        """, '', title, flags=re.X|re.M|re.S) # Remove tags, if any
    title = trim_prefix(title, 'Chapter')
    title = title.lstrip(' 0123456789.') # Remove section number, if present
    title = normalize_whitespace(title)
    dictionary['title'] = title

    # Remove as much content we do NOT want to index from the file as possible
    content = re.sub(r"""
        <\? .*? \?>
        """, ' ', content, flags=re.X|re.M|re.S) # processing instructions
    content = re.sub(r"""
        <!-- .*? -->
        """, ' ', content, flags=re.X|re.M|re.S) # comments
    content = re.sub(r"""
        < (?: script | style ) .*? </ (?: script | style ) >
        """, ' ', content, flags=re.X|re.M|re.S|re.I) # script and style elements
    content = re.sub(r"""
        < .*? >
        """, ' ', content, flags=re.X|re.M|re.S) # tags

    # Convert entities such as &copy; to actual characters, e.g., ©
    content = html.unescape(content)

    # After compressing whitespace, take content for indexing
    content = normalize_whitespace(content)
    dictionary['text'] = content

    return dictionary
    
def htmlTojsonConverter(filepath , path_prefix):
	
	tree = html.parse(filepath)
	root = tree.getroot()
	isBody = False
	str = ''
	dumpedDict = dict()
	if root == None:
		return dict()
	for element in root.iter():
		if isBody == False :
			if element.tag == 'meta' :
				attribList = element.attrib
				if 'name' in attribList and 'content' in attribList:
					dumpedDict[attribList.get('name')] = attribList.get('content')
			elif element.tag == 'title':
				dumpedDict['title'] = element.text
			elif element.tag == 'body':
				isBody = True
		elif isBody == True :
			if(element.text):
				str = str + ' ' + element.text
				dumpedDict['text'] = str
    #with open('/Users/vkooram/sampledata2.json','w') as outfile :
        #json.dump(dumpedDict,outfile)
    
	metaDictionary = parse_path(filepath)
	trimed_path = trim_prefix(filepath, path_prefix)
	url_escaped_path = urllib.parse.quote(trimed_path)   
	dumpedDict.update(metaDictionary)
	dumpedDict['url'] = url_escaped_path
	return dumpedDict


# Command-line interface
# TODO Use https://docs.python.org/3/library/getopt.html
if __name__ == '__main__':
    mirror_dirs(sys.argv[1], sys.argv[2])
