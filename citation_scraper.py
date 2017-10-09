# This program scrapes citations for specified authors and outputs all of the citations in
# HTML.
#
# outstanding issues/possible improvements:
#   - The pickled cache isn't used at all other than to save stuff.
#   - Maybe we could try and find links for the articles and embed that in the html output
#
# Author: Jesse Brennan


import argparse
import pickle
import sys
import re

import time

from scholar import ScholarQuerier, ScholarSettings, SearchScholarQuery, ScholarConf, ScholarUtils, ScholarArticle
from typing import List, Dict, Optional

Citations = Dict[str, Dict]

PIK = "./.pickle_cache.dat"


def bibtex_to_dict_key(bibtex: str):
    """
    parses a bibtex entry and translates into a python dictionary
    :param bibtex: the bibtex string
    :return: tuple with bibtex entry id and dict of other fields
    """
    rex = ('@.+?\{(?P<id>.+?),\n'
           '(?:.*title=\{(?P<title>.+?)\},?\n)?'
           '(?:.*author=\{(?P<author>.+?)\},?\n)?'
           '(?:.*journal=\{(?P<journal>.+?)\},?\n)?'
           # for inproceedings entries:
           '(?:.*booktitle=\{(?P<booktitle>.+?)\},?\n)?'
           '(?:.*volume=\{(?P<volume>.+?)\},?\n)?'
           '(?:.*number=\{(?P<number>.+?)\},?\n)?'
           '(?:.*pages=\{(?P<pages>.+?)\},?\n)?'
           '(?:.*year=\{(?P<year>.+?)\},?\n)?'
           '(?:.*publisher=\{(?P<publisher>.+?)\},?\n)?'
           '\}')
    match = re.search(rex, bibtex)
    if match is None:
        raise ValueError
    match_dict = {}
    match_dict.update(match.groupdict())
    bib_id = match_dict.pop('id')
    match_dict['sort_year'] = match_dict['year'] or '0'
    return bib_id, match_dict


def url_from_article(article: ScholarArticle) -> Optional[str]:
    """
    Tries a few different possible urls. If all fail, then url is None
    """
    url = article.attrs['url'][0]
    if url:
        # sometimes url comes back with prefix that makes it invalid
        prefix = 'http://scholar.google.com/'
        url = url[len(prefix):] if url.startswith(prefix) else url
    else:
        url = article.attrs['url_citations'][0]
    return url


def make_dict_from_bibtex(querier: ScholarQuerier) -> Citations:
    """
    turns all articles from query into a dictionary
    :param querier: the querier object
    :return: dict where keys are article ids, and val is dict of title, author, etc
    """
    out_dict = {}
    for article in querier.articles:
        try:
            bib_id, bib_dict = bibtex_to_dict_key(article.as_citation().decode('utf-8'))
        except ValueError:
            continue
        bib_dict['url'] = url_from_article(article)
        out_dict[bib_id] = bib_dict
    return out_dict


def get_citations(author: str):
    """
    gets all citations for author
    :param author: author's full name (e.g. 'benedict paten')
    :return: the dict format described in :func:`make_dict_from_bibtex`
    """
    settings = ScholarSettings()
    settings.set_citation_format(ScholarSettings.CITFORM_BIBTEX)

    querier = ScholarQuerier()
    querier.apply_settings(settings)

    query = SearchScholarQuery()
    query.set_author('"' + author + '"')
    query.set_num_page_results(ScholarConf.MAX_PAGE_RESULTS)

    # iterate through pages of queries
    output_dict = {}
    num_results = 0
    while True:
        query.set_start(num_results)

        querier.send_query(query)
        page_dict = make_dict_from_bibtex(querier)

        # save the data read into a pickle file. will contain dicts of articles
        with open(PIK, "wb") as fh:
            pickle.dump(page_dict, fh)

        if not page_dict or len(querier.articles) < ScholarConf.MAX_PAGE_RESULTS:
            break

        output_dict.update(page_dict)
        num_results += ScholarConf.MAX_PAGE_RESULTS
    return output_dict


def get_citations_authors(authors: List[str], wait_time):
    output_dict = {}
    first = True
    for author in authors:
        # wait, hopefully to prevent getting blocked by the API
        if not first and wait_time:
            time.sleep(wait_time)

        ScholarUtils.log('info', 'getting citations for {}...'.format(author))
        new_citations = get_citations(author)
        ScholarUtils.log('info', '... {} citations found (some may be duplicates from other authors)'
                         .format(len(new_citations)))
        output_dict.update(new_citations)
    return output_dict


def dict_to_txt_lines(cit_dict: Citations) -> List[str]:
    """
    expects the citations to be articles only. Not prepared to handle other things
    :return: an html formatted string with all of the citations from input
    """
    output = []
    for key in sorted(cit_dict, key=lambda k: cit_dict[k]['sort_year'], reverse=True):
        curr = cit_dict[key]
        cit_html = ''
        split_string = ['{author}; ',
                        '<strong><a href="{url}">{title}</a></strong>. ' if curr['url']
                        else '<strong>{title}</strong>. ',
                        '<i>{journal}</i>. ',
                        '<strong>',
                        '{volume}',
                        '-{number}',
                        '</strong>. ' if curr['volume'] or curr['number'] else '</strong> ',
                        '{pages} ',
                        '({year}) ',
                        '{publisher}',
                        '\n\n']
        # we want to filter out fields if they are empty
        for s in split_string:
            s = s.format(**curr)
            if 'None' not in s:
                cit_html += s

        output.append(cit_html)
    return output


def main():
    """
    expects first argument to be path to text file containing author names
    and second argument to be path to output file location
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file', metavar='input-file',
                        help='input file which contains author\'s names separated by newline characters')
    parser.add_argument('output_file', metavar='output-file',
                        help='output file which will contain formatted html of citations')
    parser.add_argument('-c', '--cookie-file', metavar='cookie-file',
                        help='cookie file used to avoid getting blocked by API. If shit isn\'t working '
                             'then open firefox, install extension to download cookie file (make sure it '
                             'is in netscape format). Make a google scholar advanced search, click '
                             'cite -> bibtex, fill out captcha. download cookie for this page and '
                             'specify the cookie file as this argument.')
    parser.add_argument('-w', '--wait',
                        help='specify how long to wait between each API request. Default is not to wait.')
    parser.add_argument('-d', '--debug', action='count', default=3,
                        help='Enable verbose logging to stderr. Repeated options increase detail of debug '
                             'output.')
    options = parser.parse_args()

    if options.cookie_file:
        ScholarConf.COOKIE_JAR_FILE = options.cookie_file

    if options.debug > 0:
        options.debug = min(options.debug, ScholarUtils.LOG_LEVELS['debug'])
        ScholarConf.LOG_LEVEL = options.debug
        ScholarUtils.log('info', 'using log level %d' % ScholarConf.LOG_LEVEL)

    with open(options.input_file, 'r') as fh:
        authors = fh.read().splitlines()
    with open(options.output_file, 'w') as fh:
        fh.writelines(dict_to_txt_lines(get_citations_authors(authors, options.wait)))


if __name__ == '__main__':
    sys.exit(main())
