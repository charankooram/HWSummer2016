#!/usr/bin/env python3
"""
Create JSON files from a directory of HTML and text files for later insertion into Solr

usage:
    python3 mirror-dirs.py <src_dir> <dest_dir>

Questions: Robert Crews <rcrews@hortonworks.com>

To do:
 * Add try-catch blocks for operations that can fail
   - open, close, permission, not found, already exists, encoding error, etc.
 * Make better html_to_json, using a real parser (such as lxml). 
"""

__version__ = "0.0.1"

import codecs, html, json, os, re, sys, urllib.parse
from lxml import html

extensions = ['.html', '.htm', '.txt']
url_prefix = '//docs.hortonworks.com/'

def mirror_dirs(src_dir, dest_dir):
    """Recurse src_dir to mirror text and HTML files in dest_dir as JSON files."""
    if not os.path.exists(dest_dir):
        os.mkdir(dest_dir)

    for item in os.listdir(src_dir):
        src_path = os.path.join(src_dir, item)

        if not os.path.isdir(src_path):
            _, extension = os.path.splitext(item)

            if not extension in extensions:
                continue
            else:
                new_item = item.replace('.', '_') + '.json'
                dest_path = os.path.join(dest_dir, new_item)
                print(dest_path)

            if extension == '.txt':
                pydict = text_to_json(src_path)
            else:
                #pydict = html_to_json(src_path)
                pydict = htmlTojsonConverter(src_path)

            #with codecs.open(dest_path, mode='w', encoding='UTF-8') as fp:
                #json.dump(pydict, fp, ensure_ascii=False)
                # return here again later. Just a temporary fix.
            with open(dest_path, mode='w') as fp :
                json.dump(pydict,fp)

        else:
            dest_path = os.path.join(dest_dir, item)
            mirror_dirs(src_path, dest_path)

def text_to_json(text_file):
    """Parse text and return a dictionary that can be converted to a JSON file."""
    with codecs.open(text_file, mode='r', encoding='iso-8859-1') as fp:
        content = fp.read()

    url_escaped_path = urllib.parse.quote(text_file)
    url = url_prefix + url_escaped_path

    filename = os.path.basename(text_file)

    content = normalize_whitespace(content)

    dictionary = {'url': url, 'title': filename, 'text': content}

    return dictionary

def normalize_whitespace(text):
    """Collapses whitespace runs to a single space, trims leading and trailing spaces."""
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'^ ', '', text)
    text = re.sub(r' $', '', text)
    return text

def html_to_json(html_file):
    """Parse HTML and return a dictionary that can be converted to a JSON file."""
    dictionary = {}

    url_escaped_path = urllib.parse.quote(html_file)
    dictionary['url'] = url_prefix + url_escaped_path

    with codecs.open(html_file, mode='r') as fp:
        content = fp.read()

    m = re.search(r'<title>(.+?)</title>', content, flags=re.X|re.M|re.S|re.I)
    if m and m.group(1):
        title = m.group(1)
    else:
        title = 'no title'
    title = normalize_whitespace(title)
    dictionary['title'] = title

    content = re.sub(r'<\?.*?\?>', ' ', content, flags=re.X|re.M|re.S) # PIs
    content = re.sub(r'<!--.*?-->', ' ', content, flags=re.X|re.M|re.S) # comments
    content = re.sub(r'<.*?>', ' ', content, flags=re.X|re.M|re.S) # elements
    content = html.unescape(content)
    content = normalize_whitespace(content)
    dictionary['text'] = content

    return dictionary

def htmlTojsonConverter(filepath):
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
    return dumpedDict

if __name__ == '__main__':
    mirror_dirs(sys.argv[1], sys.argv[2])
