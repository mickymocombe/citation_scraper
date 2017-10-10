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
from urllib.error import HTTPError

import re

import time

from scholar import ScholarQuerier, ScholarSettings, SearchScholarQuery, ScholarConf, ScholarUtils, ScholarArticle
from typing import List, Dict, Optional, Tuple, Set

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


def get_citations(author: str, options):
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
    if options.words:
        query.set_words(options.words)
    query.set_num_page_results(ScholarConf.MAX_PAGE_RESULTS)

    # iterate through pages of queries
    output_dict = {}
    num_results = 0
    while True:
        query.set_start(num_results)

        querier.send_query(query)
        page_dict = make_dict_from_bibtex(querier)

        if not page_dict or len(querier.articles) < ScholarConf.MAX_PAGE_RESULTS:
            break

        output_dict.update(page_dict)
        num_results += ScholarConf.MAX_PAGE_RESULTS
    return output_dict


def load_progress() -> Tuple[Set[str], Citations]:
    """
    Uses the cache file PIK to try and load any progress from a previous run of
    the program that may have failed

    :return: tuple of set of completed authors and
    """
    try:
        # find out which authors have been completed already (load set from file)
        with open(PIK, 'rb') as fd:
            # assume that first thing pickled was set of authors
            completed_authors = pickle.load(fd)
            # initialize output_dict with already completed author dicts
            output_dict = pickle.load(fd)
            ScholarUtils.log('info', 'Successfully loaded {} author{} from cache file'
                             .format(len(completed_authors),
                                     '' if len(completed_authors) == 1 else 's'))
    except FileNotFoundError:
        # nothing to load... start from scratch
        ScholarUtils.log('info', 'No cache file found. Expected file called {}'.format(PIK))
        completed_authors = set()
        output_dict = {}
    return completed_authors, output_dict


def save_progress(completed_authors: Set[str], output_dict: Citations):
    """
    over writes any current PIK cache file with any new authors and their citations
    """
    with open(PIK, 'wb') as fd:
        pickle.dump(completed_authors, fd)
        pickle.dump(output_dict, fd)
    # exit with warning explaining what happened
    ScholarUtils.log('info', 'Google blocked us, progress saved to {}'.format(PIK))


def get_citations_authors(authors: List[str], options):
    completed_authors, output_dict = load_progress()
    try:
        # iterate through authors and get citations
        first = True
        for author in [x for x in authors if x not in completed_authors]:
            # wait, hopefully to prevent getting blocked by the API
            if not first and options.wait:
                time.sleep(options.wait)
            else:
                first = False

            ScholarUtils.log('info', 'getting citations for {}...'.format(author))
            new_citations = get_citations(author, options)
            ScholarUtils.log('info', '... {} citations found (some may be duplicates from other authors)'
                             .format(len(new_citations)))
            output_dict.update(new_citations)
            # add a completed author to the set of completed authors
            completed_authors.add(author)
        return output_dict

    except HTTPError as err:
        assert err.code == 503
        save_progress(completed_authors, output_dict)
        print('Google API blocked us. Progress was saved. To get around this use the '
              '--cookie-file option. More info with --help.')
        exit(1)
    except KeyboardInterrupt:
        save_progress(completed_authors, output_dict)
        print('User forced quit. Progress was saved.')
        exit(1)


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
    parser.add_argument('-w', '--wait', metavar='SECONDS',
                        help='specify how long to wait between each API request. Default is not to wait.')
    parser.add_argument('-d', '--debug', action='count', default=3,
                        help='Enable verbose logging to stderr. Repeated options increase detail of debug '
                             'output.')
    parser.add_argument('--words', metavar='"extra search criteria"',
                        help='words are included in the search for each author which can help refine a '
                             'search to a particular university or institution.')
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
        fh.writelines(dict_to_txt_lines(get_citations_authors(authors, options)))


if __name__ == '__main__':
    sys.exit(main())
