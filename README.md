
Intro
=====

This is software used to scrape Google Scholar for citations by a
particular author. It makes use of ckreibich's [scholar.py][1], with
a couple of [modifications][2].

How to use
==========

Setup
-----

1. You will need Python3 installed on you computer. Ideally then you
   will want [virtual environment][3] installed (*Note:* if you have
   to install virtualenv make sure you use pip3 instead of pip).

2. Next, you will need to clone this repo and/or download the zip.

3. Finally, make and launch a new virtualenv.
   ```bash
   $ virtualenv myvenv  # this will make a directory called myvenv
   $ source myvenv/bin/activate
   ```
4. Install dependency
   ```bash
   $ pip3 install beautifulsoup4
   ```

Running
-------

Your first line of defence is the help menu. Run
```bash
$ python3 citation_scraper.py --help
```
for details.

In general you need input. The program takes in a file of author's
names which would look something like this file `zeppelin.txt`:
```
Jimmy Page
John Bonham
Robert Plant
John Paul Jones
```

You must also specify where you want the output to go. Using the
example file from above we could run the program as
```bash
$ python3 citation_scraper zeppelin.txt output.txt
```

Features
========

Caching
-------

Google blocking the program mid-run used to be a show stopper. All
of the citations already scraped would be lost and the program would
crash. Until... **CACHING!**

Every time all of the citations for a particular author are scraped
they are added to a cache file called `.pickle_cache.dat` which is 
created in the directory where the program is run. If the program
crashes due to a KeyboardInterrupt (^C) or from a 503 from Google's
servers, the progress so far is saved to this file so that on the next
run the scraping can resume from where it left off.

Refined Search
--------------

Sometimes you want to limit your search only to authors that are part
of a particular institute or university. By using the `--words` option
one can specify that so that it's reflected in the results. For example
`--words "UC Santa Cruz Genomics Institute"` will give only results
from authors within that institute.

Waiting
-------

the `--wait` option can be used to wait for a specified number of
seconds between each query with the hopes that this won't upset Google.
The effectiveness of this solution has not been verified.

Trouble shooting
================

Probably the only problem you will encounter is getting blocked by
Google Scholar's API. There is a workaround!

You need:

1. Mozilla Firefox

2. A Firefox extension that allows you to export cookies in the
   Netscape cookie file format such as [Cookie Exporter][4].

Then:

3. Navigate to one of the URLs that failed when requested (using
   Firefox)

4. Fill out the captcha

5. Export the the cookies from the page (as `cookies.txt`)

6. Save the file and run again but specify the `-c` option. For example
   ```bash
   $ python3 citation_scraper zeppelin.txt output.txt -c cookies.txt
   ```

If problems persist, contact Jesse: brennan@ucsc.edu

[1]: https://github.com/ckreibich/scholar.py
[2]: https://github.com/ckreibich/scholar.py/pull/96
[3]: https://virtualenv.pypa.io/en/stable/
[4]: https://addons.mozilla.org/en-US/firefox/addon/cookie-exporter/
