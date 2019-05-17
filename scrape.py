#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2019, Joey Espinosa <jlouis.espinosa@gmail.com>
# Copyright: (c) 2019, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = r'''
---
module: scrape
author: "Joey Espinosa (@particledecay)"
short_description: Scrape websites for data
requirements:
    - BeautifulSoup
version_added: "2.9"
description:
    - Perform web scraping against a URL
options:
    url:
        description:
            - The URL to fetch HTML data from
        required: True
    xpath:
        description:
            - The XPath to the data
        required: True
    timeout:
        description:
            - How long to wait before request times out
        required: False
'''

EXAMPLES = r'''
- name: Get latest circlecli version on GitHub
  scrape:
    url: https://github.com/particledecay/circlecli/releases/latest
    xpath: '//div[@class="release-header"]//a/@href'
  register: circlecli_url
'''

RETURN = r'''
content:
    description: the contents of the element(s) matched
    returned: always
    type: list
matched:
    description: whether an element was found at the given XPath
    returned: always
    type: bool
'''


import datetime
from six import string_types

from ansible.module_utils import basic
from ansible.module_utils.urls import fetch_url
from lxml.html import HtmlElement, fromstring


class PageScraper(object):
    """Scrape web elements and data."""

    def __init__(self, module):
        self.module = module

        self.url = self.module.params['url']
        self.xpath = self.module.params['xpath']
        self.timeout = self.module.params.get('timeout', 10)

        # this will hold page content
        self._content = ""

    def _get_content(self):
        if self._content:
            return self._content

        if self.module.check_mode:
            method = 'HEAD'
        else:
            method = 'GET'

        start = datetime.datetime.utcnow()
        resp, info = fetch_url(self.module, self.url, method=method, timeout=self.timeout)
        elapsed = (datetime.datetime.utcnow() - start).seconds

        if info['status'] == 304:
            self.module.exit_json(url=self.url, changed=False, msg=info.get('msg', ''), elapsed=elapsed)

        if info['status'] == -1:
            self.module.fail_json(url=self.url, msg=info['msg'], elapsed=elapsed)

        if info['status'] != 200:
            self.module.fail_json(url=self.url, msg="Request failed", response=info['msg'], status_code=info['status'], elapsed=elapsed)

        return resp.read()

    def _get_element_text(self, element):
        if isinstance(element, HtmlElement):
            return element.text_content()

        if isinstance(element, list):
            if not element:
                return None  # an empty list means we didn't match anything
            return [self._get_element_text(e) for e in element]

        return element

    def scrape(self):
        """Returns an element's contents at `xpath`."""
        content = self._get_content()

        doc = fromstring(content)
        elem = doc.xpath(self.xpath)
        content = self._get_element_text(elem)

        return {'matched': content is not None, 'content': content}


def main():
    module = basic.AnsibleModule(
        argument_spec=dict(
            url=dict(required=True, type='str'),
            xpath=dict(required=True, type='str'),
            timeout=dict(required=False, type='int'),
        ),
        supports_check_mode=True
    )

    scraper = PageScraper(module)
    result = scraper.scrape()
    if result['matched']:
        result['changed'] = True

    module.exit_json(**result)


if __name__ == "__main__":
    main()
