#!/usr/bin/env python3
"""Create Solr JSON from a directory of HTML and text files.

Takes about 75 minutes to run on docs.hortonworks.com content.

For usage, run:
    python3 jsonify.py --help

Questions: Robert Crews <rcrews@hortonworks.com>

Use tar.bz2 to compress the resulting JSON:
    $ tar cfy docs.hortonworks.com-json.tar.bz2 docs.hortonworks.com-json
"""

import argparse
import json
import logging
import os
import re
import time
import urllib.parse
import lxml.html

__version__ = '0.0.7'


def mirror_dirs(src_dir: str, dest_dir: str) -> None:
    """Transform HTML and text to JSON and copy to mirrored directory.

    Args:
        src_dir  Directory containing text and HTML files.
        dest_dir  Nonexistant directory where JSON files will be written.
    """
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
                meta = text_to_json(src_path, ARGS.in_dir)
            else:
                meta = html_to_json(src_path, ARGS.in_dir)

            meta['stream_size'] = os.path.getsize(src_path)
            meta['date'] = get_datetime(src_path)
            meta['x_parsed_by'] = ('com.hortonworks.docs.' +
                                   os.path.splitext(
                                       os.path.basename(__file__))[0] +
                                   ', v' + __version__)

            # Write JSON as UTF-8
            with open(dest_path, mode='w', encoding='UTF-8') as file_handle:
                json.dump(meta, file_handle, ensure_ascii=False)


def text_to_json(text_file: str, path_prefix: str='') -> dict:
    """Parse text and return a dict that can be converted to JSON.

    Args:
        text_file  Path to a text file.
        path_prefix  String to remove from front of URL written to JSON.

    Returns:
        A dict of metadata gathered from the file path.
    """
    assert isinstance(text_file, str), (
        'text_path is not a string: %r' % text_file)
    assert isinstance(path_prefix, str), (
        'path_prefix is not a string: %r' % path_prefix)

    # Read text files as cp1252, ignoring errors
    with open(text_file, encoding='cp1252', errors='ignore') as file_h:
        content = file_h.read()

    # Convert file system path to URL syntax
    trimed_path = trim_prefix(text_file, path_prefix)
    url_escaped_path = urllib.parse.quote(trimed_path)
    url = url_escaped_path

    # Use the file name as the document title
    title = os.path.basename(text_file)

    # After compressing whitespace, take all the content of the file for indexing
    text = normalize_whitespace(content)

    meta = {'url': url, 'title': title, 'text': text}

    # Update dict with metadata from the file path
    meta.update(parse_path(text_file))

    return meta


def normalize_whitespace(text: str) -> str:
    """Collapse whitespace to single spaces, trim leading and trailing spaces.

    Args:
        text  Text from which whitespace will be removed.

    Returns:
        Text with whitespace removed.
    """
    assert isinstance(text, str), (
        'text is not a string: %r' % text)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text


def trim_prefix(original: str, prefix: str) -> str:
    """Remove prefix from string.

    Args:
        original  The original string.
        prefix  The phrase to remove from the original string.

    Returns:
        String with prefix removed, or the original string.
    """
    assert isinstance(original, str), (
        'original is not a string: %r' % original)
    assert isinstance(prefix, str), (
        'prefix is not a string: %r' % prefix)
    if original.startswith(prefix):
        return original[len(prefix):]
    else:
        return original


def trim_suffix(original: str, suffix: str) -> str:
    """Remove suffix from string.

    Args:
        original  The original string.
        suffix  The phrase to remove from the original string.

    Returns:
        String with suffix removed, or the original string.
    """
    assert isinstance(original, str), (
        'original is not a string: %r' % original)
    assert isinstance(suffix, str), (
        'suffix is not a string: %r' % suffix)
    if original.endswith(suffix):
        return original[:-len(suffix)]
    else:
        return original


def standardize_release(relnum: str) -> str:
    """Assure four-part release numbers.

    Args:
        relnum  A string. Ideally digits and dots, such as "1.1".

    Returns:
        A string with three period characters, such as "1.1.0.0".
    """
    assert isinstance(relnum, str), (
        'relnum is not a string: %r' % relnum)
    parts = relnum.split('.')
    while len(parts) < 4:
        parts.append('0')
    return '.'.join(parts)


def standardize_product(abbrev: str) -> str:
    """Convert common product abbreviations to official product names.

    Args:
        abbrev  A known abbreviation of Hortonworks product names:
                HDP, HDP-Win, HDF, SS, Cldbrk, etc.

    Returns:
        A product name better suited for customer visibility, or the
        original string.
    """
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


def standardize_booktitle(abbrev: str) -> str:
    """Convert book title abbreviations to fuller book titles.

    Args:
        abbrev  A common abbreviation for a book title.

    Returns:
        The best full title for display.
    """
    assert isinstance(abbrev, str), (
        'abbrev is not a string: %r' % abbrev)

    booktitles = {
        "About_Hortonworks_Data_Platform": 'Hortonworks Data Platform Getting Started',
        "AdminGuide": 'Hortonworks DataFlow Administrator Guide',
        "Amb_Rel_Notes": 'Hortonworks Data Platform Apache Ambari Release Notes',
        "Ambari_Admin_Guide": 'Hortonworks Data Platform Apache Ambari Administrator Guide',
        "Ambari_Admin_v170": 'Hortonworks Data Platform Apache Ambari Administrator Guide',
        "Ambari_Doc_Suite": 'Hortonworks Data Platform Apache Ambari Documentation',
        "Ambari_Install_v170": 'Hortonworks Data Platform Apache Ambari Installation Guide',
        "Ambari_Ref_Guide_v170": 'Hortonworks Data Platform Apache Ambari Reference', # ?
        "Ambari_Reference_Guide_v170": 'Hortonworks Data Platform Apache Ambari Reference', # ?
        "ambari_reference_guide": 'Hortonworks Data Platform Apache Ambari Reference',
        "ambari_reference": 'Hortonworks Data Platform Apache Ambari Reference',
        "Ambari_RelNotes_v170": 'Hortonworks Data Platform Apache Ambari Release Notes',
        "Ambari_RelNotes_v20": 'Hortonworks Data Platform Apache Ambari Release Notes',
        "Ambari_Security_Guide": 'Hortonworks Data Platform Apache Ambari Security Guide',
        "Ambari_Security_v170": 'Hortonworks Data Platform Apache Ambari Security Guide',
        "ambari_security": 'Hortonworks Data Platform Apache Ambari Security Guide',
        "Ambari_Trblshooting_v170": 'Hortonworks Data Platform Apache Ambari Troubleshooting Guide',
        "ambari_troubleshooting": 'Hortonworks Data Platform Apache Ambari Troubleshooting Guide',
        "Ambari_Upgrade_v170": 'Hortonworks Data Platform Apache Ambari Upgrade Guide',
        "Ambari_User_v170": 'Hortonworks Data Platform Apache Ambari User Guide',
        "Ambari_Users_Guide": 'Hortonworks Data Platform Apache Ambari User Guide',
        "ambari_views_guide": 'Hortonworks Data Platform Apache Ambari Views Guide',
        "Appendix": 'Hortonworks Data Platform Port Configuration Guide',
        "atlas-rest-api": 'Hortonworks Data Platform Apache Atlas REST API Reference',
        "beeline": 'Hortonworks Data Platform Apache Hive Beeline Java API Reference',
        "cldbrk_install": 'Hortonworks Cloudbreak Installation Guide',
        "Clust_Plan_Gd_Win":
            'Hortonworks Data Platform Cluster Planning Guide for Microsoft Windows',
        "cluster-planning-guide": 'Hortonworks Data Platform Cluster Planning Guide',
        "ClusterPlanningGuide": 'Hortonworks Data Platform Cluster Planning Guide',
        "data_governance": 'Hortonworks Data Platform Data Governance Guide',
        "Data_Integration_Services_With_HDP":
            'Hortonworks Data Platform Data Integration Services Guide',
        "data_movement": 'Hortonworks Data Platform Data Movement Guide',
        "dataintegration": 'Hortonworks Data Platform Data Integration Services Guide',
        "Deploying_Hortonworks_Data_Platform": 'Hortonworks Data Platform Deployment Guide',
        "DeveloperGuide": 'Hortonworks DataFlow Developer Guide',
        "ExpressionLanguageGuide": 'Hortonworks DataFlow Expression Language Guide',
        "falcon_quickstart_guide": 'Hortonworks Data Platform Apache Falcon Quick Start',
        "falcon": 'Hortonworks Data Platform Apache Falcon Guide',
        "Flume": 'Hortonworks Data Platform Apache Flume Guide',
        "getting-started-guide": 'Hortonworks Data Platform Getting Started',
        "getting-started-win": 'Hortonworks Data Platform Getting Started for Microsoft Windows',
        "GettingStartedGuide": 'Hortonworks Data Platform Getting Started',
        "gsInstaller": 'Hortonworks Data Platform Getting Started',
        "hadoop-ha": 'Hortonworks Data Platform High Availability Guide',
        "Hadoop": 'Hortonworks Data Platform Apache Hadoop Guide',
        "HAGuides": 'Hortonworks Data Platform High Availability Guide',
        "hbase_java_api": 'Hortonworks Data Platform Apache HBase Java API Reference',
        "hbase_snapshots_guide": 'Hortonworks Data Platform Apache HBase Snapshots Guide',
        "HCatalog": 'Hortonworks Data Platform Apache HCatalog Guide',
        "HDF_GettingStarted": 'Hortonworks DataFlow Getting Started',
        "HDF_InstallSetup": 'Hortonworks DataFlow Installation and Setup Guide',
        "HDF_RelNotes": 'Hortonworks DataFlow Release Notes',
        "HDF_Upgrade": 'Hortonworks DataFlow Upgrade Guide',
        "hdfs_admin_tools": 'Hortonworks Data Platform Administration Tools Guide',
        "hdfs_nfs_gateway": 'Hortonworks Data Platform HDFS NFS Gateway Guide',
        "HDP_HA": 'Hortonworks Data Platform High Availability Guide',
        "HDP_Install_Upgrade_Win":
            'Hortonworks Data Platform Installation and Upgrade Guide for Microsoft Windows',
        "HDP_Install_Win": 'Hortonworks Data Platform Installation Guide for Microsoft Windows',
        "HDP_Reference_Guide": 'Hortonworks Data Platform Reference Guide',
        "HDP_RelNotes_Win": 'Hortonworks Data Platform Release Notes for Microsoft Windows',
        "HDP_RelNotes": 'Hortonworks Data Platform Release Notes',
        "hdp_search": 'Hortonworks Data Platform Search Solutions Guide',
        "HDP_Upgrade_Win": 'Hortonworks Data Platform Upgrade Guide for Microsoft Windows',
        "hdp1-system-admin-guide": 'Hortonworks Data Platform Administrator Guide',
        "HDPSecure_Admin": 'Hortonworks Data Platform Secure Administration Guide',
        "High_Availability_Guides": 'Hortonworks Data Platform High Availability Guide',
        "hive_javadocs": 'Hortonworks Data Platform Apache Hive Java API Reference',
        "Hive": 'Hortonworks Data Platform Apache Hive Guide',
        "HortonworksConnectorForTeradata": 'Hortonworks Data Platform Terradata Connection Guide',
        "importing_data_into_hbase_guide":
            'Hortonworks Data Platform Apache HBase Data Importing Guide',
        "Installing_HDP_AMB": 'Hortonworks Data Platform Apache Ambari Installation Guide',
        "installing_hdp_for_windows":
            'Hortonworks Data Platform Installation Guide for Microsoft Windows',
        "installing_manually_book": 'Hortonworks Data Platform Manual Installation Guide',
        "kafka-guide": 'Hortonworks Data Platform Apache Kafka Guide',
        "kafka-user-guide": 'Hortonworks Data Platform Apache Kafka User Guide',
        "Knox_Admin_Guide": 'Hortonworks Data Platform Apache Knox Gateway Administrator Guide',
        "Knox_Gateway_Admin_Guide":
            'Hortonworks Data Platform Apache Knox Gateway Administrator Guide',
        "Monitoring_Hadoop_Book": 'Hortonworks Data Platform Apache Hadoop Monitoring Guide',
        "Monitoring_HDP": 'Hortonworks Data Platform Apache Hadoop Monitoring Guide',
        "Overview": 'Hortonworks DataFlow Overview',
        "performance_tuning": 'Hortonworks Data Platform Performance Tuning Guide',
        "Pig": 'Hortonworks Data Platform Apache Pig Guide',
        "QuickStart_HDPWin": 'Hortonworks Data Platform Quick Start for Microsoft Windows',
        "Ranger_Adding_New": 'Hortonworks Data Platform Apache Ranger Component Addition Guide',
        "Ranger_Install_Guide": 'Hortonworks Data Platform Apache Ranger Installation Guide',
        "Ranger_KMS_Admin_Guide":
            'Hortonworks Data Platform Apache Ranger Key Management Administrator Guide',
        "Ranger_User_Guide": 'Hortonworks Data Platform Apache Ranger User Guide',
        "readme": 'Hortonworks Data Platform Readme',
        "Reference": 'Hortonworks Data Platform Reference',
        "reference": 'Hortonworks Data Platform Reference',
        "releasenotes_ambari_1.5.0": 'Hortonworks Data Platform Apache Ambari Release Notes',
        "releasenotes_ambari_1.5.1": 'Hortonworks Data Platform Apache Ambari Release Notes',
        "releasenotes_ambari_1.6.0": 'Hortonworks Data Platform Apache Ambari Release Notes',
        "releasenotes_ambari_1.6.1": 'Hortonworks Data Platform Apache Ambari Release Notes',
        "releasenotes_ambari_2.0.0": 'Hortonworks Data Platform Apache Ambari Release Notes',
        "releasenotes_ambari_2.0.1.0": 'Hortonworks Data Platform Apache Ambari Release Notes',
        "releasenotes_ambari_2.0.2.0": 'Hortonworks Data Platform Apache Ambari Release Notes',
        "releasenotes_ambari_2.1.0.0": 'Hortonworks Data Platform Apache Ambari Release Notes',
        "releasenotes_ambari_2.1.1.0": 'Hortonworks Data Platform Apache Ambari Release Notes',
        "releasenotes_ambari_2.1.2.0": 'Hortonworks Data Platform Apache Ambari Release Notes',
        "releasenotes_ambari_2.1.2.1": 'Hortonworks Data Platform Apache Ambari Release Notes',
        "releasenotes_ambari_2.2.0.0": 'Hortonworks Data Platform Apache Ambari Release Notes',
        "releasenotes_ambari_2.2.1.0": 'Hortonworks Data Platform Apache Ambari Release Notes',
        "releasenotes_ambari_2.2.1.1": 'Hortonworks Data Platform Apache Ambari Release Notes',
        "releasenotes_ambari_2.2.2.0": 'Hortonworks Data Platform Apache Ambari Release Notes',
        "releasenotes_ambari": 'Hortonworks Data Platform Apache Ambari Release Notes',
        "releasenotes_hdp_1.x": 'Hortonworks Data Platform Release Notes',
        "releasenotes_hdp_2.0": 'Hortonworks Data Platform Release Notes',
        "releasenotes_hdp_2.1": 'Hortonworks Data Platform Release Notes',
        "releasenotes_HDP-Win": 'Hortonworks Data Platform Release Notes for Microsoft Windows',
        "rolling-upgrade": 'Hortonworks Data Platform Rolling Upgrade Guide',
        "secure-kafka-ambari":
            'Hortonworks Data Platform Apache Ambari Configuring Apache Kafka Guide',
        "secure-storm-ambari":
            'Hortonworks Data Platform Apache Ambari Configuring Apache Storm Guide',
        "Security_Guide": 'Hortonworks Data Platform Security Guide',
        "smartsense_admin": 'Hortonworks SmartSense Administrator Guide',
        "spark-guide": 'Hortonworks Data Platform Apache Spark Guide',
        "spark-quickstart": 'Hortonworks Data Platform Apache Spark Quick Start',
        "Sqoop": 'Hortonworks Data Platform Apache Sqoop Guide',
        "storm-user-guide": 'Hortonworks Data Platform Apache Spark User Guide',
        "Sys_Admin_Guides": 'Hortonworks Data Platform Administrator Guide',
        "sysadmin-guide": 'Hortonworks Data Platform Administrator Guide',
        "system-admin-guide": 'Hortonworks Data Platform Administrator Guide',
        "Templeton": 'Hortonworks Data Platform Apache Templeton Guide',
        "upgrading_Ambari": 'Hortonworks Data Platform Apache Ambari Upgrade Guide',
        "upgrading_hdp_manually": 'Hortonworks Data Platform Manual Upgrade Guide',
        "user-guide": 'Hortonworks Data Platform User Guide',
        "UserGuide": 'Hortonworks DataFlow User Guide',
        "using_Ambari_book": 'Hortonworks Data Platform Apache Ambari User Guide',
        "Using_Apache_FlumeNG": 'Hortonworks Data Platform Apache Flume NG User Guide',
        "Using_WebHDFS_REST_API": 'Hortonworks Data Platform WebHDFS REST API Reference',
        "using-apache-hadoop": 'Hortonworks Data Platform Apache Hadoop User Guide',
        "webhdfs": 'Hortonworks Data Platform WebHDFS REST API Reference',
        "whdata": 'Hortonworks Data Platform Documentation',
        "whgdata": 'Hortonworks Data Platform Documentation',
        "yarn_resource_mgt": 'Hortonworks Data Platform Apache YARN Resource Management Guide',
    }

    if abbrev in booktitles:
        abbrev = booktitles[abbrev]

    return abbrev


def _std_path(match: 're.match') -> dict:
    """Get product, release, and booktitle from path.

    Args:
        match  A compiled re.match object.

    Returns:
        A dict containing product, release, and booktitle values.
    """
    assert isinstance(match, type(re.match('', ''))), (
        'match is not a re.match: %r' % match)
    meta = {}
    meta['product'] = match.group('p')
    meta['release'] = match.group('r')
    meta['booktitle'] = match.group('b')
    return meta


def _hdp_23_yj_path(match: 're.match') -> dict:
    """Get product, release, and booktitle from path.

    Args:
        match  A compiled re.match object.

    Returns:
        A dict containing product, release, and booktitle values.
    """
    assert isinstance(match, type(re.match('', ''))), (
        'match is not a re.match: %r' % match)
    meta = {}
    meta['product'] = 'HDP'
    meta['release'] = '2.3.0.0-yj'
    meta['booktitle'] = match.group('b')
    return meta


def _win_new_path(match: 're.match') -> dict:
    """Get product, release, and booktitle from path.

    Args:
        match  A compiled re.match object.

    Returns:
        A dict containing product, release, and booktitle values.
    """
    assert isinstance(match, type(re.match('', ''))), (
        'match is not a re.match: %r' % match)
    meta = {}
    meta['product'] = 'HDP-Win'
    meta['release'] = match.group('r')
    meta['booktitle'] = match.group('b')
    return meta


def _win_old_path(match: 're.match') -> dict:
    """Get product, release, and booktitle from path.

    Args:
        match  A compiled re.match object.

    Returns:
        A dict containing product, release, and booktitle values.
    """
    assert isinstance(match, type(re.match('', ''))), (
        'match is not a re.match: %r' % match)
    meta = {}
    meta['product'] = 'HDP-Win'
    meta['release'] = match.group('r')
    meta['booktitle'] = match.group('b')
    return meta


def _ambari_path(match: 're.match') -> dict:
    """Get product, release, and booktitle from path.

    Args:
        match  A compiled re.match object.

    Returns:
        A dict containing product, release, and booktitle values.
    """
    assert isinstance(match, type(re.match('', ''))), (
        'match is not a re.match: %r' % match)
    meta = {}
    meta['product'] = 'Ambari'
    meta['release'] = match.group('r')
    meta['booktitle'] = match.group('b')
    return meta


def _std_path_index(match: 're.match') -> dict:
    """Get product, release, and booktitle from path.

    Args:
        match  A compiled re.match object.

    Returns:
        A dict containing product, release, and booktitle values.
    """
    assert isinstance(match, type(re.match('', ''))), (
        'match is not a re.match: %r' % match)
    meta = {}
    meta['product'] = match.group('p')
    meta['release'] = match.group('r')
    return meta


def _win_new_index(match: 're.match') -> dict:
    """Get product, release, and booktitle from path.

    Args:
        match  A compiled re.match object.

    Returns:
        A dict containing product, release, and booktitle values.
    """
    assert isinstance(match, type(re.match('', ''))), (
        'match is not a re.match: %r' % match)
    meta = {}
    meta['product'] = 'HDP-Win'
    meta['release'] = match.group('r')
    return meta


def _win_old_index(match: 're.match') -> dict:
    """Get product, release, and booktitle from path.

    Args:
        match  A compiled re.match object.

    Returns:
        A dict containing product, release, and booktitle values.
    """
    assert isinstance(match, type(re.match('', ''))), (
        'match is not a re.match: %r' % match)
    meta = {}
    meta['product'] = 'HDP-Win'
    meta['release'] = match.group('r')
    return meta


def _ambari_path_index(match: 're.match') -> dict:
    """Get product, release, and booktitle from path.

    Args:
        match  A compiled re.match object.

    Returns:
        A dict containing product, release, and booktitle values.
    """
    assert isinstance(match, type(re.match('', ''))), (
        'match is not a re.match: %r' % match)
    meta = {}
    meta['product'] = 'Ambari'
    meta['release'] = match.group('r')
    return meta


def _product_index(match: 're.match') -> dict:
    """Get product, release, and booktitle from path.

    Args:
        match  A compiled re.match object.

    Returns:
        A dict containing product, release, and booktitle values.
    """
    assert isinstance(match, type(re.match('', ''))), (
        'match is not a re.match: %r' % match)
    meta = {}
    meta['product'] = match.group('p')
    return meta


def parse_path(path: str) -> dict:
    """Get product, release, and booktitle from path.

    Args:
        path  A URL path.

    Returns:
        A dict containing product, release, and booktitle values.
    """
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
    process = {
        'std_path': _std_path,
        'hdp_23_yj_path': _hdp_23_yj_path,
        'win_new_path': _win_new_path,
        'win_old_path': _win_old_path,
        'ambari_path': _ambari_path,
        'std_path_index': _std_path_index,
        'win_new_index': _win_new_index,
        'win_old_index': _win_old_index,
        'ambari_path_index': _ambari_path_index,
        'product_index': _product_index,
    }

    meta = {}

    # Call the appropriate subroutine using the "process" lookup table, above
    for key in regex:
        match = regex[key].search(path)
        if match:
            meta = process[key](match)

    if 'product' in meta:
        meta['product'] = standardize_product(meta['product'])
    if 'release' in meta:
        meta['release'] = standardize_release(meta['release'])
    if 'booktitle' in meta:
        meta['booktitle'] = standardize_booktitle(meta['booktitle'])

    if not meta:
        logging.warning('No path metadata from ' + path)
    return meta


def get_datetime(path: str) -> str:
    """Return UTC file modification date in datetime format.

    See https://www.w3.org/TR/NOTE-datetime

    Args:
        path  A path to a file.

    Returns:
        A string of the modification time in datetime format.
    """
    assert isinstance(path, str), (
        'path is not a string: %r' % path)
    since_epoch = os.path.getmtime(path)
    utc_time = time.gmtime(since_epoch)
    datetime = time.strftime('%Y-%m-%dT%H:%M:%SZ', utc_time)
    return datetime


def get_text(element: 'lxml.html.HtmlElement') -> str:
    """Get text from HTML elements, even text after child elements (tails).

    Args:
        element  An lxml.html.HtmlElement object.

    Returns:
        The text from the elment and all its decendent elements in
        document order. Does not return contents of script or style
        elements.
    """
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


def get_html_metas(etree: 'lxml.html.parse', meta: dict) -> dict:
    """Add name and content values from HTML meta elements to passed dict.

    Args:
        etree  An element tree representing a parsed HTML document.
        meta  A dict of metadata relating to the same HTML document.

    Returns:
        The dict of metadata.
    """
    assert isinstance(meta, dict), (
        'meta is not a dict: %r' % meta)

    if etree.getroot() is None:
        logging.error('No root in etree passed to get_html_metas()')
        return {}

    for html_meta in etree.xpath("//meta"):
        attribs = html_meta.attrib
        if 'name' in attribs and 'content' in attribs:
            meta[attribs.get('name').lower().strip()] = (
                normalize_whitespace(attribs.get('content')))

    return meta


def get_html_lang(etree: 'lxml.html.parse', meta: dict) -> dict:
    """Get list of explicit lang and xml:lang values from all HTML elements.

    Args:
        etree  An element tree representing a parsed HTML document.
        meta  A dict of metadata relating to the same HTML document.

    Returns:
        The dict of metadata. Note the lang value is a space-separated
        list of lang values, not a single value.
    """
    assert isinstance(meta, dict), (
        'meta is not a dict: %r' % meta)

    if etree.getroot() is None:
        logging.error('No root in etree passed to get_html_lang()')
        return {}

    lang_attributes = ('string(//*/@lang)', 'string(//*/@xml:lang)')
    lang_list = []
    for xpath in lang_attributes:
        lang = etree.xpath(xpath)
        lang_list.append(lang)
    meta['lang'] = ' '.join(lang_list)
    meta['lang'] = meta['lang'].replace('_', '-')
    meta['lang'] = normalize_whitespace(meta['lang'])
    if not meta['lang']:
        meta['lang'] = 'en'

    return meta


def _process_title(title: str, section_numbering_characters: str) -> str:
    """Make better display title.

    Args:
        title  A title from an HTML page.
        section_numbering_characters  Characters to strip from the
            beginning of titles to remove section numbering.

    Returns:
        The title processed for display.
    """
    assert isinstance(title, str), (
        'title is not a string: %r' % title)

    title = normalize_whitespace(title)
    title = trim_prefix(title, 'Chapter')
    title = title.lstrip(section_numbering_characters)

    return title


def get_html_title(etree: 'lxml.html.parse', meta: dict,
                   section_numbering_characters: str) -> dict:
    """Add title key and associated value to passed dict.

    Args:
        etree  An element tree representing a parsed HTML document.
        meta  A dict of metadata relating to the same HTML document.
        section_numbering_characters  Characters to strip from the
            beginning of titles to remove section numbering.

    Returns:
        The dict of metadata.
    """
    assert isinstance(meta, dict), (
        'meta is not a dict: %r' % meta)

    if etree.getroot() is None:
        logging.error('No root in etree passed to get_html_title()')
        return {}

    h1s = etree.xpath("//h1")
    if h1s:
        meta['title'] = get_text(h1s[0])
        meta['title'] = _process_title(meta['title'], section_numbering_characters)

    if 'title' not in meta:
        titles = etree.xpath("//title")
        if titles:
            meta['title'] = get_text(titles[0])
            meta['title'] = _process_title(meta['title'], section_numbering_characters)

    return meta


def get_html_priority_text(etree: 'lxml.html.parse', meta: dict,
                           section_numbering_characters: str) -> dict:
    """Add priority text from HTML document to ptext key in passed dict.

    Args:
        etree  An element tree representing a parsed HTML document.
        meta  A dict of metadata relating to the same HTML document.
        section_numbering_characters  Characters to strip from the
            beginning of titles to remove section numbering.

    Returns:
        The dict of metadata.
    """
    assert isinstance(meta, dict), (
        'meta is not a dict: %r' % meta)

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
    if 'description' in meta:
        priority_text_list.append(meta['description'])
    if 'keywords' in meta:
        priority_text_list.append(meta['keywords'])
    priority_text = ' '.join(priority_text_list)
    priority_text = normalize_whitespace(priority_text)
    meta['ptext'] = priority_text

    return meta


def get_html_text(etree: 'lxml.html.parse', meta: dict) -> dict:
    """Add text from HTML document to text key in passed dict.

    Args:
        etree  An element tree representing a parsed HTML document.
        meta  A dict of metadata relating to the same HTML document.

    Returns:
        The dict of metadata.
    """
    assert isinstance(meta, dict), (
        'meta is not a dict: %r' % meta)

    if etree.getroot() is None:
        logging.error('No root in etree passed to get_html_text()')
        return {}

    content = etree.xpath("/html/body/div[@id='content']")
    if content:
        meta['text'] = get_text(content[0])
    else:
        meta['text'] = get_text(etree.getroot())
    meta['text'] = normalize_whitespace(meta['text'])
    meta['text'] = trim_suffix(meta['text'], ' Legal notices')

    return meta


def html_to_json(html_path: str, path_prefix: str='') -> dict:
    """Parse HTML and return a dict that can be converted to JSON.

    Args:
        html_path  Path to a directory containing HTML and text files.
        path_prefix  Text to be removed from the beginning of URLs.

    Returns:
        A dict of metadata suitable for conversion to a JSON file.
    """
    assert isinstance(html_path, str), (
        'html_path is not a string: %r' % html_path)
    assert isinstance(path_prefix, str), (
        'path_prefix is not a string: %r' % path_prefix)

    meta = {}
    section_numbering_characters = ('-.0123456789'
                                    "\N{SPACE}\N{NO-BREAK SPACE}\N{EN DASH}")
    # Parse page
    etree = lxml.html.parse(html_path)
    if etree.getroot() is None:
        logging.error('No root: ' + html_path)
        return {}

    # Get meta element values
    get_html_metas(etree, meta)

    # Get page languages
    get_html_lang(etree, meta)

    # Get page title
    get_html_title(etree, meta, section_numbering_characters)
    if 'title' not in meta:
        logging.error('No title: ' + html_path)

    # Get text from areas representing priority content
    # Matches in this content should cause the document to rank higher
    get_html_priority_text(etree, meta, section_numbering_characters)

    # Get page content
    get_html_text(etree, meta)

    # Convert file system path to URL syntax
    meta['url'] = trim_prefix(html_path, path_prefix)
    meta['url'] = urllib.parse.quote(meta['url'])
    meta['id'] = meta['url']

    # Update dict with metadata from the file path
    meta.update(parse_path(html_path))

    return meta


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
