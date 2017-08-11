import sys
import re

from scholar import ScholarQuerier, ScholarSettings, SearchScholarQuery, citation_export, ScholarConf

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


def bibtex_to_dict_key(bibtex: str):
    """
    parses a bibtex entry and translates into a python dictionary
    :param bibtex: the bibtex string
    :return: tuple with bibtex entry id and dict of other fields
    """
    rex = ('@.+?\{(?P<id>.+?),\n'
           '(?:.*title=\{(?P<title>.+?)\},?\n)?'
           '(?:.*author=\{(?P<author>.+?)\},?\n)?'
           '(?:.*[journal|book]=\{(?P<journal>.+?)\},?\n)?'
           '(?:.*volume=\{(?P<volume>.+?)\},?\n)?'
           '(?:.*number=\{(?P<number>.+?)\},?\n)?'
           '(?:.*pages=\{(?P<pages>.+?)\},?\n)?'
           '(?:.*year=\{(?P<year>.+?)\},?\n)?'
           '(?:.*publisher=\{(?P<publisher>.+?)\},?\n)?'
           # for inproceedings entries:
           '(?:.*booktitle=\{(?P<booktitle>.+?)\},?\n)?'
           '\}')
    match = re.search(rex, bibtex)
    if match is None:
        raise ValueError
    match_dict = match.groupdict()
    bib_id = match_dict.pop('id')
    return bib_id, match_dict


def make_dict_from_bibtex(querier: ScholarQuerier):
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

def main():
    d = get_citations('benedict paten')


if __name__ == '__main__':
    sys.exit(main())
