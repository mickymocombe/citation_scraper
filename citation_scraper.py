import argparse
import sys
import re

from scholar import ScholarQuerier, ScholarSettings, SearchScholarQuery, citation_export, ScholarConf
from typing import List, Dict

"""
@article{jacobs2014evolutionary,
  title={An evolutionary arms race between KRAB zinc finger genes 91/93 and SVA/L1 retrotransposons},
  author={Jacobs, Frank MJ and Greenberg, David and Nguyen, Ngan and Haeussler, Maximilian and Ewing, Adam D and Katzman, Sol and Paten, Benedict and Salama, Sofie R and Haussler, David},
  journal={Nature},
  volume={516},
  number={7530},
  pages={242},
  year={2014},
  publisher={NIH Public Access}
}
"""

Citations = Dict[str, Dict]


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
    match_dict = match.groupdict()
    bib_id = match_dict.pop('id')
    return bib_id, match_dict


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

    output_dict = {}
    num_results = 0
    while True:
        query.set_num_page_results(ScholarConf.MAX_PAGE_RESULTS)
        query.set_start(num_results)

        querier.send_query(query)
        page_dict = make_dict_from_bibtex(querier)

        if not page_dict:
            break

        output_dict.update(page_dict)
        num_results += ScholarConf.MAX_PAGE_RESULTS
    return output_dict


def get_citations_authors(authors: List[str]):
    output_dict = {}
    for author in authors:
        output_dict.update(get_citations(author))
        # TODO: possibly wait here so as not to get blocked by API
    return output_dict


def dict_to_txt_lines(cit_dict: Citations) -> List[str]:
    """
    expects the citations to be articles only. Not prepared to handle other things
    :return: an html formatted string with all of the citations from input
    """
    output = []
    for citation in cit_dict.values():
        cit_html = ('{author}; <strong>{title}</strong>. <i>{journal}</i>. <strong>{volume}-{number}'
                    '</strong>. {pages} ({year}) <i>{publisher}</i>\n'.format(**citation))
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
    options = parser.parse_args()

    if options.cookie_file:
        ScholarConf.COOKIE_JAR_FILE = options.cookie_file

    with open(options.input_file, 'r') as fh:
        authors = fh.read().splitlines()
    with open(options.output_file, 'w') as fh:
        fh.writelines(dict_to_txt_lines(get_citations_authors(authors)))


if __name__ == '__main__':
    sys.exit(main())
