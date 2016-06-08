#! /usr/bin/env python
"""Scraping Knife
"""
import os
import sys
import logging
import argparse
import tempfile

import pycurl
import progressbar
import fake_useragent

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

logger = logging.getLogger(__name__)


class OutputFileError(Exception):
    """There is problem in the output of the file"""


class URLSearchError(Exception):
    """"""


class BrowserFactory(object):
    """Create WebDriver instance"""
    def __init__(self, ua=None):
        if ua is None:
            ua_obj = fake_useragent.UserAgent()
            ua = ua_obj.chrome
        self.ua = ua

    def __call__(self):
        dcap = dict(DesiredCapabilities.PHANTOMJS)
        dcap['phantomjs.page.settings.userAgent'] = self.ua
        return webdriver.PhantomJS(desired_capabilities=dcap)


class PluggableProgress:
    def __init__(self, progress_plugin):
        self.progress_plugin = progress_plugin

    def __call__(self, total_to_download, total_downloaded, total_to_upload, total_uploaded):
        if total_to_download:
            percent = int(total_downloaded / total_to_download * 100)
            self.progress_plugin.update(percent)


class ContentDownload(object):
    """Download content"""
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.progress = progressbar.ProgressBar()
        self.refresh()

    def __call__(self, url, path, continue_=None):
        self.curl.setopt(pycurl.URL, url)
        if continue_:
            self.set_resume(continue_)

        self.start()
        try:
            with open(path, 'w+b') as fp:
                self.curl.setopt(pycurl.WRITEDATA, fp)
                self.curl.perform()
        finally:
            self.finish()

    def refresh(self):
        """Recreate pycurl object"""
        ua = fake_useragent.UserAgent()
        self.curl = pycurl.Curl()
        self.curl.setopt(pycurl.SSL_VERIFYPEER, 1)
        self.curl.setopt(pycurl.SSL_VERIFYHOST, 2)
        self.curl.setopt(pycurl.AUTOREFERER, 1)
        self.curl.setopt(pycurl.FOLLOWLOCATION, 1)
        self.curl.setopt(pycurl.USERAGENT, ua.chrome)
        self.curl.setopt(pycurl.NOPROGRESS, 0)
        self.curl.setopt(pycurl.PROGRESSFUNCTION, PluggableProgress(self.progress))
        self.set_verbose(self.verbose)

    def set_verbose(self, verbose):
        """Set verbose level of pycurl object"""
        self.curl.setopt(pycurl.VERBOSE, verbose)

    def set_resume(self, target):
        """Set to download  position of remote file"""
        point = os.path.getsize(target)
        self.curl.setopt(pycurl.RESUME_FROM, point)

    def reset_resume(self):
        """Set zero to download  position of remote file"""
        self.curl.setopt(pycurl.RESUME_FROM, 0)

    def start(self):
        self.progress.start()

    def finish(self):
        self.progress.finish()
        self.refresh()


class SearchURL:
    def __call__(self, browser):
        return browser.url


class Downloader:
    """Download content"""
    def __init__(self, verbose=None):
        create_browser = BrowserFactory()
        self.browser = create_browser()
        self.download = ContentDownload(verbose=verbose)
        self.search_url = SearchURL()

    def __enter__(self):
        return self

    def __exit__(self):
        self.close()

    def close(self):
        self.browser.close()

    def can_output_to_file(self, path, force, raise_exception=False):
        """Whether the file can be output"""
        output_directory = os.path.dirname(os.path.abspath(path))
        if not os.path.isdir(output_directory):
            if raise_exception:
                raise OutputFileError('No output directory: %s', output_directory)
            return False

        if not force and os.path.exists(path):
            if raise_exception:
                raise OutputFileError('Output file already exists: %s', path)
            return False

        return True

    def create_tempfile(self, path):
        """Create download content temporary file"""
        return os.path.abspath(path) + '.downloading'

    def create_tempfile_strict(self, path):
        """Create download content temporary file"""
        prefix = os.path.abspath(path) + '.'
        fd, temp_file_path = tempfile.mkstemp(prefix=prefix)
        os.close(fd)
        return temp_file_path

    def __call__(self, url, path, force=False, continue_at=None):
        self.can_output_to_file(path, force, raise_exception=True)
        self.browser.get(url)
        content_url = self.search_url(self.browser) if self.search_url else url
        print(content_url)
        if content_url is None:
            raise URLSearchError('Content URL not found: %s', url)

        temp_file_path = continue_at or self.create_tempfile(path)
        print('temporary file: {}'.format(temp_file_path))
        self.download(content_url, temp_file_path)

        self.can_output_to_file(path, force, raise_exception=True)
        os.rename(temp_file_path, path)


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser = argparse.ArgumentParser()
    parser.add_argument('url')
    parser.add_argument('output')
    parser.add_argument('--force', default=False, action='store_true')
    parser.add_argument('-C', '--continue-at', default=None)
    parser.add_argument('--verbose', default=False, action='store_true')
    args = parser.parse_args(argv)

    url = args.url
    output = args.output
    force = args.force
    continue_at = args.continue_at
    verbose = args.verbose

    downalod = Downloader(verbose=verbose)
    downalod(url, output, force=force, continue_at=continue_at)


if __name__ == '__main__':
    sys.exit(main())
