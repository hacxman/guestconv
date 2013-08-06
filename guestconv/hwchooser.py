# coding: utf-8
# vim: tabstop=4 shiftwidth=4 softtabstop=4
# guestconv
#
# Copyright (C) 2013 Red Hat Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

import guestfs
import lxml.etree as ET

import guestconv.converters
import guestconv.exception
import guestconv.db
import guestconv.log

class HwChooser(object):
    """Map DB info to particular HW/SW profile configuration
    suitable for running on target. It's all about transforming
    XML coming from converter's inspect phase.
    """

    def __init_(self):
        # the *less* of shared mutable state, the *better*
        pass

    def transform(self, db, xml):
        """Transform XML with choices to XML with devices

        :param db: Capability DB
        :param xml: XML from Converter
        :returns: XML filled with devices instead of options
        """

        dom = ET.fromstring(desc)
        for root in dom.xpath(u'/guestconv/root'):
            name = root.get(u'name')
            print name
            for opts in root.xpath(u'options'):
                for opt in opts.xpath(u'option'):
                    print opt

        return ET.tostring(dom, xml, encoding='utf8')
