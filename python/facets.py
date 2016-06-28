#!/usr/bin/env python3
"""Create JSON for Solr from a directory of HTML and text

Takes 2-15 minutes to run on docs.hortonworks.com content.
Resulting file is about 23 KB.

For usage, run:
    python3 facets.py --help

Questions: Robert Crews <rcrews@hortonworks.com>

When complete, the resulting file can be pretty-printed by running this
command:
    python -m json.tool facets.json facets-pretty.json
"""

__version__ = '0.0.1'

import argparse
import codecs
import collections
import json
import logging
import os


def get_jsons(src_dir, facet):
    """Recurse src_dir to parse JSON files for product, release, and
    title data.
    """
    assert isinstance(src_dir, str), (
        'src_dir is not a string: %r' % src_dir)
    assert isinstance(facet, dict), (
        'facet is not a dict: %r' % facet)

    for item in os.listdir(src_dir):
        src_path = os.path.join(src_dir, item)

        if os.path.isdir(src_path):
            get_jsons(src_path, facet) # Recurse
        else:
            _, extension = os.path.splitext(item)
            if extension != '.json':
                continue
            with codecs.open(src_path, mode='r', encoding='UTF-8') as infile:
                try:
                    jinn = json.load(infile)
                except json.JSONDecodeError:
                    print('Error!')

            if 'product' in jinn:
                jinn['product'] = product_lookup(jinn['product'])
                if 'booktitle' in jinn:
                    jinn['booktitle'] = booktitle_lookup(jinn['booktitle'])
                    if 'release' in jinn:
                        facet[jinn['product']][jinn['release']][jinn['booktitle']] = '.'

    return facet


def product_lookup(abbr):
    """Convert product abbreviations to fuller product names."""
    assert isinstance(abbr, str), (
        'abbr is not a string: %r' % abbr)
    products = {
        'Ambari': 'Apache Ambari',
        'HDP': 'Data Platform',
        'HDP-Win': 'Data Platform for Windows',
        'HDF': 'DataFlow',
    }
    if abbr in products:
        abbr = products[abbr]
    return abbr


def booktitle_lookup(abbr):
    """Convert book title abbreviations to fuller book titles."""
    assert isinstance(abbr, str), (
        'abbr is not a string: %r' % abbr)
    booktitles = {
        "About_Hortonworks_Data_Platform": 'Hortonworks Data Platform Getting Started',
        "AdminGuide": 'Hortonworks DataFlow Administrator\'s Guide',
        "Amb_Rel_Notes": 'Hortonworks Data Platform Apache Ambari Release Notes',
        "Ambari_Admin_Guide": 'Hortonworks Data Platform Apache Ambari Administrator\'s Guide',
        "Ambari_Admin_v170": 'Hortonworks Data Platform Apache Ambari Administrator\'s Guide',
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
        "Ambari_User_v170": 'Hortonworks Data Platform Apache Ambari User\'s Guide',
        "Ambari_Users_Guide": 'Hortonworks Data Platform Apache Ambari User\'s Guide',
        "ambari_views_guide": 'Hortonworks Data Platform Apache Ambari Views Guide',
        "Appendix": 'Hortonworks Data Platform Port Configuration Guide',
        "atlas-rest-api": 'Hortonworks Data Platform Apache Atlas REST API Reference',
        "beeline": 'Hortonworks Data Platform Apache Hive Beeline Java API Reference',
        "cldbrk_install": 'Hortonworks Cloudbreak Installation Guide',
        "Clust_Plan_Gd_Win": 'Hortonworks Data Platform Cluster Planning Guide for Microsoft Windows',
        "cluster-planning-guide": 'Hortonworks Data Platform Cluster Planning Guide',
        "ClusterPlanningGuide": 'Hortonworks Data Platform Cluster Planning Guide',
        "data_governance": 'Hortonworks Data Platform Data Governance Guide',
        "Data_Integration_Services_With_HDP": 'Hortonworks Data Platform Data Integration Services Guide',
        "data_movement": 'Hortonworks Data Platform Data Movement Guide',
        "dataintegration": 'Hortonworks Data Platform Data Integration Services Guide',
        "Deploying_Hortonworks_Data_Platform": 'Hortonworks Data Platform Deployment Guide',
        "DeveloperGuide": 'Hortonworks DataFlow Developer\'s Guide',
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
        "HDP_Install_Upgrade_Win": 'Hortonworks Data Platform Installation and Upgrade Guide for Microsoft Windows',
        "HDP_Install_Win": 'Hortonworks Data Platform Installation Guide for Microsoft Windows',
        "HDP_Reference_Guide": 'Hortonworks Data Platform Reference Guide',
        "HDP_RelNotes_Win": 'Hortonworks Data Platform Release Notes for Microsoft Windows',
        "HDP_RelNotes": 'Hortonworks Data Platform Release Notes',
        "hdp_search": 'Hortonworks Data Platform Search Solutions Guide',
        "HDP_Upgrade_Win": 'Hortonworks Data Platform Upgrade Guide for Microsoft Windows',
        "hdp1-system-admin-guide": 'Hortonworks Data Platform Administrator\'s Guide',
        "HDPSecure_Admin": 'Hortonworks Data Platform Secure Administration Guide',
        "High_Availability_Guides": 'Hortonworks Data Platform High Availability Guide',
        "hive_javadocs": 'Hortonworks Data Platform Apache Hive Java API Reference',
        "Hive": 'Hortonworks Data Platform Apache Hive Guide',
        "HortonworksConnectorForTeradata": 'Hortonworks Data Platform Terradata Connection Guide',
        "importing_data_into_hbase_guide": 'Hortonworks Data Platform Apache HBase Data Importing Guide',
        "Installing_HDP_AMB": 'Hortonworks Data Platform Apache Ambari Installation Guide',
        "installing_hdp_for_windows": 'Hortonworks Data Platform Installation Guide for Microsoft Windows',
        "installing_manually_book": 'Hortonworks Data Platform Manual Installation Guide',
        "kafka-guide": 'Hortonworks Data Platform Apache Kafka Guide',
        "kafka-user-guide": 'Hortonworks Data Platform Apache Kafka User\'s Guide',
        "Knox_Admin_Guide": 'Hortonworks Data Platform Apache Knox Gateway Administrator\'s Guide',
        "Knox_Gateway_Admin_Guide": 'Hortonworks Data Platform Apache Knox Gateway Administrator\'s Guide',
        "Monitoring_Hadoop_Book": 'Hortonworks Data Platform Apache Hadoop Monitoring Guide',
        "Monitoring_HDP": 'Hortonworks Data Platform Apache Hadoop Monitoring Guide',
        "Overview": 'Hortonworks DataFlow Overview',
        "performance_tuning": 'Hortonworks Data Platform Performance Tuning Guide',
        "Pig": 'Hortonworks Data Platform Apache Pig Guide',
        "QuickStart_HDPWin": 'Hortonworks Data Platform Quick Start for Microsoft Windows',
        "Ranger_Adding_New": 'Hortonworks Data Platform Apache Ranger Component Addition Guide',
        "Ranger_Install_Guide": 'Hortonworks Data Platform Apache Ranger Installation Guide',
        "Ranger_KMS_Admin_Guide": 'Hortonworks Data Platform Apache Ranger Key Management Administrator\'s Guide',
        "Ranger_User_Guide": 'Hortonworks Data Platform Apache Ranger User\'s Guide',
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
        "secure-kafka-ambari": 'Hortonworks Data Platform Apache Ambari Configuring Apache Kafka Guide',
        "secure-storm-ambari": 'Hortonworks Data Platform Apache Ambari Configuring Apache Storm Guide',
        "Security_Guide": 'Hortonworks Data Platform Security Guide',
        "smartsense_admin": 'Hortonworks SmartSense Administrator\'s Guide',
        "spark-guide": 'Hortonworks Data Platform Apache Spark Guide',
        "spark-quickstart": 'Hortonworks Data Platform Apache Spark Quick Start',
        "Sqoop": 'Hortonworks Data Platform Apache Sqoop Guide',
        "storm-user-guide": 'Hortonworks Data Platform Apache Spark User\'s Guide',
        "Sys_Admin_Guides": 'Hortonworks Data Platform Administrator\'s Guide',
        "sysadmin-guide": 'Hortonworks Data Platform Administrator\'s Guide',
        "system-admin-guide": 'Hortonworks Data Platform Administrator\'s Guide',
        "Templeton": 'Hortonworks Data Platform Apache Templeton Guide',
        "upgrading_Ambari": 'Hortonworks Data Platform Apache Ambari Upgrade Guide',
        "upgrading_hdp_manually": 'Hortonworks Data Platform Manual Upgrade Guide',
        "user-guide": 'Hortonworks Data Platform User\'s Guide',
        "UserGuide": 'Hortonworks DataFlow User\'s Guide',
        "using_Ambari_book": 'Hortonworks Data Platform Apache Ambari User\'s Guide',
        "Using_Apache_FlumeNG": 'Hortonworks Data Platform Apache Flume NG User\'s Guide',
        "Using_WebHDFS_REST_API": 'Hortonworks Data Platform WebHDFS REST API Reference',
        "using-apache-hadoop": 'Hortonworks Data Platform Apache Hadoop User\'s Guide',
        "webhdfs": 'Hortonworks Data Platform WebHDFS REST API Reference',
        "whdata": 'Hortonworks Data Platform Documentation',
        "whgdata": 'Hortonworks Data Platform Documentation',
        "yarn_resource_mgt": 'Hortonworks Data Platform Apache YARN Resource Management Guide',
    }
    if abbr in booktitles:
        abbr = booktitles[abbr]
    return abbr


def make_dict():
    """Quickly make nested dictionaries in Python."""
    # http://stackoverflow.com/questions/635483/what-is-the-best-way-to-implement-nested-dictionaries-in-python
    return collections.defaultdict(make_dict)


def process(src_dir, dest_file):
    """Set up JSON struct, delegate its creation, then write the JSON
    file to disk.
    """
    assert isinstance(src_dir, str), (
        'src_dir is not a string: %r' % src_dir)
    assert isinstance(dest_file, str), (
        'dest_file is not a string: %r' % dest_file)

    facet = collections.defaultdict(make_dict)
    facet = get_jsons(src_dir, facet)

    # Convert the booktitle dictionary to a list
    for product in facet:
        for release in facet[product]:
            booktitles = sorted(facet[product][release].keys())
            facet[product][release] = booktitles

    with codecs.open(dest_file, mode='w', encoding='UTF-8') as file_handle:
        json.dump(facet, file_handle, ensure_ascii=False)


# Command-line interface
if __name__ == '__main__':

    # Get command-line arguments
    ARGPARSER = argparse.ArgumentParser()
    BASENAME, _ = os.path.splitext(os.path.basename(__file__))
    ARGPARSER.add_argument('-l', '--logfile', default=BASENAME + '.log',
                           help='the log file, defaults to ./' + BASENAME + '.log')
    ARGPARSER.add_argument('-v', '--verbosity', type=int, default=2,
                           help='message level for log', choices=[1, 2, 3, 4, 5])
    ARGPARSER.add_argument('in_dir',
                           help='directory containing text and HTML files')
    ARGPARSER.add_argument('-o', '--out', nargs='?', default=BASENAME + '.json',
                           help='filename where JSON facet data will be written')
    ARGS = ARGPARSER.parse_args()

    # https://docs.python.org/3/library/logging.html#levels
    ARGS.verbosity *= 10 # debug, info, warning, error, critical

    # Set up logging
    # To monitor progress, tail the log file or use /usr/bin/less in F mode
    logging.basicConfig(
        format='%(asctime)s %(levelname)8s %(message)s', filemode='w',
        filename=ARGS.logfile)
    logging.getLogger().setLevel(ARGS.verbosity)

    process(ARGS.in_dir, ARGS.out)
