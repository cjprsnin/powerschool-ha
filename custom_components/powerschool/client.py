#!/usr/bin/env python3
import argparse, getpass, html, json, os, re, sys, time
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from urllib.parse import urlencode, urljoin, urlparse, parse_qs
from urllib.request import Request, build_opener, HTTPCookieProcessor
from urllib.error import HTTPError, URLError

# NOTE: Full client is being uploaded in sequential commits due to size.
# Temporary incomplete file - will be replaced.
raise ImportError('PowerSchool client upload incomplete - wait for full commit')
