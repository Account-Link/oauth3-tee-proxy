# plugins/twitter/patches.py
"""
Patches for the Twitter library
"""

import re

from twitter.account import Account
from twitter.scraper import Scraper


# Fix invalid escape sequences in Account class
def patch_account():
    Account._get_user_id = lambda self: int(
        re.findall(r"u=(\d+)", self.session.cookies.get("twid"))[0]
    )
    Account.get_user_id = lambda self: int(
        re.findall(r"u=(\d+)", self.session.cookies.get("twid"))[0]
    )
    Account._get_authenticated_user_id = lambda self: int(
        re.findall(r"u=(\d+)", self.session.cookies.get("twid"))[0]
    )


# Fix invalid escape sequences in Scraper class
def patch_scraper():
    def _sort_streams(self, streams):
        for k, v in streams.items():
            streams[k] = sorted(
                v, key=lambda x: int(re.findall(r"_(\d+)_\w\.aac$", x.url.path)[0])
            )
        return streams

    Scraper._sort_streams = _sort_streams
    Scraper.chunk_idx = staticmethod(
        lambda chunk: re.findall(r"_(\d+)_\w\.aac", chunk)[0]
    )
    Scraper.get_user_id = lambda self: int(
        re.findall(r"u=(\d+)", self.session.cookies.get("twid"))[0]
    )


def apply_patches():
    patch_account()
    patch_scraper()