#!/usr/bin/python
#
# test/run.py load unit test suits and run them
#
# (C) Copyright 2013 Red Hat Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License, Version 2,
# as published by the Free Software Foundation
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

import unittest

import os.path
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir))

import converter_test
import redhat_converter_test
import debian_converter_test
import db
import rpm_package

suite = unittest.TestSuite()
suite.addTest(unittest.makeSuite(converter_test.ConverterTest))
suite.addTest(unittest.makeSuite(redhat_converter_test.GrubTest))
suite.addTest(unittest.makeSuite(debian_converter_test.GrubTest))
suite.addTest(unittest.makeSuite(db.DBLookupTestCase))
suite.addTest(unittest.makeSuite(rpm_package.RpmPackageTest))
suite.addTest(unittest.makeSuite(redhat_converter_test.RHEL52_64_LocalInstallTest))
suite.addTest(unittest.makeSuite(redhat_converter_test.RHEL52_64_YumInstallTest))

unittest.TextTestRunner(verbosity=2).run(suite)
