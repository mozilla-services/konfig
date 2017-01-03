# coding: utf8
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
import argparse
import unittest
import tempfile
import os
from six import StringIO

from konfig import Config, SettingsDict


_FILE_ONE = """\
[DEFAULT]
extends = ${TEMPFILE}

[one]
foo = bar
num = -12
not_a_num = 12abc
st = "o=k"
lines = 1
        two
        3

env = some ${__STUFF__}
location = ${HERE}

[two]
a = b
"""

_FILE_TWO = """\
[one]
foo = baz
bee = 1
two = "a"

[three]
more = stuff
location = ${HERE}
"""

_FILE_THREE = """\
[DEFAULT]
extends = no-no,no-no-no-no,no-no-no-no,theresnolimit

[one]
foo = bar
"""

_FILE_FOUR = """\
[global]
foo = bar
baz = bawlp

[auth]
a = b
c = d

[storage]
e = f
g = h

[multi:once]
storage.i = j
storage.k = l

[multi:thrice]
storage.i = jjj
storage.k = lll
"""

_EXTRA = """\
[some]
stuff = True

[other]
thing = ok
"""


_FILE_OVERRIDE = """\
[DEFAULT]
overrides = ${TEMPFILE}

[one]
foo = bar
"""

_FILE_ARGS = """\
[circus]
httpd = True
zmq_endpoint = http://ok

[other]
stuff = 10.3
thing = bleh

[floats]
stuff = 10.3
float = 9.
again = .3
digits = 10.34
digits2 = .34

[bleh]
mew = 10

[mi]
log_level = DEBUG
log_output = stdout
daemon = True
pidfile = pid
multi = one
        two
        three
"""


class ConfigTestCase(unittest.TestCase):

    def setUp(self):
        os.environ['__STUFF__'] = 'stuff'
        fp, filename = tempfile.mkstemp()
        f = os.fdopen(fp, 'w')
        f.write(_FILE_TWO)
        f.close()
        os.environ['TEMPFILE'] = filename
        self.file_one = StringIO(_FILE_ONE)
        self.file_two = filename
        self.file_three = StringIO(_FILE_THREE)
        self.file_override = StringIO(_FILE_OVERRIDE)
        self.file_args = StringIO(_FILE_ARGS)
        fp, filename = tempfile.mkstemp()
        f = os.fdopen(fp, 'w')
        f.write(_FILE_FOUR)
        f.close()
        self.file_four = filename

    def tearDown(self):
        if '__STUFF__' in os.environ:
            del os.environ['__STUFF__']
        os.remove(self.file_two)

    def test_reader(self):
        config = Config(self.file_one)

        # values conversion
        self.assertEquals(config.get('one', 'foo'), 'bar')
        self.assertEquals(config.get('one', 'num'), -12)
        self.assertEquals(config.get('one', 'not_a_num'), "12abc")
        self.assertEquals(config.get('one', 'st'), 'o=k')
        self.assertEquals(config.get('one', 'lines'), [1, 'two', 3])
        self.assertEquals(config.get('one', 'env'), 'some stuff')

        # getting a map
        map = config.get_map()
        self.assertEquals(map['one.foo'], 'bar')

        map = config.get_map('one')
        self.assertEquals(map['foo'], 'bar')

        del os.environ['__STUFF__']
        self.assertEquals(config.get('one', 'env'), 'some stuff')

        # extends
        self.assertEquals(config.get('three', 'more'), 'stuff')
        self.assertEquals(config.get('one', 'two'), 'a')

    def test_nofile(self):
        # if a user tries to use an inexistant file in extensions,
        # pops an error
        self.assertRaises(IOError, Config, self.file_three)

    def test_settings_dict_copy(self):
        settings = SettingsDict({"a.one": 1,
                                 "a.two": 2,
                                 "b.three": 3,
                                 "four": 4})
        new_settings = settings.copy()
        self.assertEqual(settings, new_settings)
        self.assertTrue(isinstance(new_settings, SettingsDict))

    def test_settings_dict_getsection(self):
        settings = SettingsDict({"a.one": 1,
                                 "a.two": 2,
                                 "b.three": 3,
                                 "four": 4})

        self.assertEquals(settings.getsection("a"), {"one": 1, "two": 2})
        self.assertEquals(settings.getsection("b"), {"three": 3})
        self.assertEquals(settings.getsection("c"), {})
        self.assertEquals(settings.getsection(""), {"four": 4})

    def test_settings_dict_setdefaults(self):
        settings = SettingsDict({"a.one": 1,
                                 "a.two": 2,
                                 "b.three": 3,
                                 "four": 4})

        settings.setdefaults({"a.two": "TWO", "a.five": 5, "new": "key"})
        self.assertEquals(settings.getsection("a"),
                          {"one": 1, "two": 2, "five": 5})
        self.assertEquals(settings.getsection("b"), {"three": 3})
        self.assertEquals(settings.getsection("c"), {})
        self.assertEquals(settings.getsection(""), {"four": 4, "new": "key"})

    def test_location_interpolation(self):
        config = Config(self.file_one)
        # file_one is a StringIO, so it has no location.
        self.assertEquals(config.get('one', 'location'), '${HERE}')
        # file_two is a real file, so it has a location.
        file_two_loc = os.path.dirname(self.file_two)
        self.assertEquals(config.get('three', 'location'), file_two_loc)

    def test_override_mode(self):
        config = Config(self.file_override)
        self.assertEquals(config.get('one', 'foo'), 'baz')
        self.assertEquals(config.get('three', 'more'), 'stuff')

    def test_convert_float(self):
        config = Config(self.file_args)
        self.assertEqual(config['floats']['stuff'], 10.3)
        self.assertEqual(config['floats']['float'], 9.0)
        self.assertEqual(config['floats']['again'], .3)
        self.assertEqual(config['floats']['digits'], 10.34)
        self.assertEqual(config['floats']['digits2'], .34)

    def test_as_args(self):
        config = Config(self.file_args)
        args = config.as_args(strip_prefixes=['circus'],
                              omit_sections=['bleh', 'mi', 'floats'],
                              omit_options=[('other', 'thing')])

        wanted = ['--other-stuff', '10.3', '--httpd',
                  '--zmq-endpoint', 'http://ok']
        wanted.sort()
        args.sort()
        self.assertEqual(args, wanted)

        args = config.as_args(omit_sections=['bleh', 'mi', 'floats'])
        wanted = ['--circus-zmq-endpoint', 'http://ok', '--other-thing',
                  'bleh', '--other-stuff', '10.3', '--circus-httpd']
        wanted.sort()
        args.sort()
        self.assertEqual(args, wanted)

        # it also works with an argparse parser
        parser = argparse.ArgumentParser(description='Run some watchers.')
        parser.add_argument('config', help='configuration file', nargs='?')

        parser.add_argument('-L', '--log-level', dest='loglevel')
        parser.add_argument('--log-output', dest='logoutput')
        parser.add_argument('--daemon', dest='daemonize', action='store_true')
        parser.add_argument('--pidfile', dest='pidfile')
        parser.add_argument('--multi', action='append')

        args = config.scan_args(parser, strip_prefixes=['mi'])
        args.sort()

        wanted = ['--log-level', u'DEBUG', '--log-output', u'stdout',
                  '--daemon', '--pidfile', u'pid', '--multi',
                  'one', '--multi', 'two', '--multi', 'three']
        wanted.sort()

        self.assertEqual(wanted, args)

    def test_utf8(self):
        utf8 = os.path.join(os.path.dirname(__file__), 'utf8.ini')
        config = Config(utf8)
        self.assertEqual(config.get('ok', 'yeah'), u'é')
