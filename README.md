
Intro
=====

This is the software used to scrape Google Scholar for citations by a
particular author. It makes use of scolar.py which makes use of
ckreibich's [scholar.py][1], with a couple [modifications][2].

How to use
==========

Setup
-----

1. You will need Python3 installed on you computer. Ideally then you
   will want to start a [virtual environment][3] (*Note:* if you have
   to install virtualenv make sure you use pip3 instead of pip).

2. Next, you will need to clone this repo and/or download the zip.

3. Finally, make and launch a new virtualenv.
   ```bash
   $ virtualenv myvenv  # this will make a directory called myvenv
   $ source myvenv/bin/activate
   ```
4. Install dependency
   ```bash
   c$ pip3 install beautifulsoup4
   ```

Running
-------

Your first line of defence is the help menu. Run
```bash
python3 citation_scraper.py --help
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

Trouble shooting
================

Probably the only problem you will encounter is getting blocked by
Google Scholar's API. There is a workaround!

You need:

1. Mozilla Firefox

2. A Firefox extension that allows you to export cookies in the
   Netscape cookie file format such as [Cookie Exporter][4].

Then:

3. Navigate to one of the URLs that failed when requested

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
