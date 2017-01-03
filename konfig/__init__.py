# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
""" Configuration file reader / writer
"""
import re
import os
from configparser import ConfigParser, ExtendedInterpolation
from six import string_types, integer_types


_IS_NUMBER = re.compile('^-?[0-9]+$')
_IS_FLOAT = re.compile('^-?[0-9]+\.[0-9]*$|^-?\.[0-9]+$')


class ExtendedEnvironmentInterpolation(ExtendedInterpolation):
    def __init__(self):
        items = os.environ.items()
        self.environment = dict([(k, v.replace('$', '$$')) for k, v in items])
        self.klass = super(ExtendedEnvironmentInterpolation, self)

    def before_get(self, parser, section, option, value, defaults):
        defaults = self.environment
        defaults['HERE'] = '$${HERE}'
        if parser.filename:
            defaults['HERE'] = os.path.dirname(parser.filename)

        if defaults['HERE'] == '':
            defaults['HERE'] = os.curdir

        result = self.klass.before_get(parser, section, option, value,
                                       defaults)
        if '\n' in result:
            return [line for line in [self._unserialize(line)
                                      for line in result.split('\n')]
                    if line != '']
        return self._unserialize(result)

    def before_set(self, parser, section, option, value):
        result = self.klass.before_set(parser, section, option, value)
        return self._serialize(result)

    def _serialize(self, value):
        if isinstance(value, bool):
            value = str(value).lower()
        elif isinstance(value, integer_types):
            value = str(value)
        elif isinstance(value, (list, tuple)):
            value = '\n'.join(['    %s' % line for line in value]).strip()
        else:
            value = str(value)
        return value

    def _unserialize(self, value):
        if not isinstance(value, string_types):
            # already converted
            return value

        value = value.strip()
        if _IS_NUMBER.match(value):
            return int(value)
        elif _IS_FLOAT.match(value):
            return float(value)
        elif value.startswith('"') and value.endswith('"'):
            return value[1:-1]
        elif value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        return value


class Config(ConfigParser):

    def __init__(self, filename):
        # let's read the file
        ConfigParser.__init__(self, **self._configparser_kwargs())
        if isinstance(filename, string_types):
            self.filename = filename
            self.read(filename)
        else:
            self.filename = None
            self.read_file(filename)

    def optionxform(self, option):
        return option

    def _read(self, fp, filename):
        # first pass
        ConfigParser._read(self, fp, filename)

        # let's expand it now if needed
        defaults = self.defaults()

        def _list(name):
            if name not in defaults:
                return []
            value = defaults[name]
            if not isinstance(value, list):
                value = [value]
            return value

        if 'extends' in defaults or 'overrides' in defaults:
            interpolate = self._interpolation.before_get

            for file_ in _list('extends'):
                file_ = interpolate(self, 'defaults', 'extends', file_, {})
                self._extend(file_)

            for file_ in _list('overrides'):
                file_ = interpolate(self, 'defaults', 'overrides', file_, {})
                self._extend(file_, override=True)

    def get_map(self, section=None):
        """returns a dict representing the config set"""
        if section:
            return dict(self.items(section))

        res = {}
        for section in self:
            for option, value in self[section].items():
                option = '%s.%s' % (section, option)
                res[option] = value
        return res

    def mget(self, section, option):
        value = self.get(section, option)
        if not isinstance(value, list):
            value = [value]
        return value

    def _extend(self, filename, override=False):
        """Expand the config with another file."""
        if not os.path.isfile(filename):
            raise IOError('No such file: %s' % filename)
        parser = ConfigParser(**self._configparser_kwargs())
        parser.optionxform = lambda option: option
        parser.filename = filename
        parser.read([filename])
        serialize = self._interpolation._serialize

        for section in parser:
            if section in self:
                for option in parser[section]:
                    if option not in self[section] or override:
                        value = parser[section][option]
                        self[section][option] = serialize(value)
            else:
                self[section] = parser[section]

    def _configparser_kwargs(self):
        return {
            'interpolation': ExtendedEnvironmentInterpolation(),
            'comment_prefixes': ('#',),
        }

    def scan_args(self, parser, strip_prefixes=None):
        args = []

        # for each option in the parser we look for it in the config
        prefixes = ['DEFAULT']
        if strip_prefixes is not None:
            prefixes.extend(strip_prefixes)

        # building the list we have
        scanned = {}
        for key, value in self.get_map().items():
            # type conversion
            if isinstance(value, (list, tuple)):
                value = [str(v) for v in value]

            scanned[self._convert_key(key, prefixes)] = value

        # now trying to see if we have matches
        args = []

        for action in parser._actions:
            option = action.option_strings
            if '--help' in option or option == []:
                continue

            option = option[-1]
            if option in scanned:
                value = scanned[option]
                if not isinstance(value, list):
                    value = [value]

                for v in value:
                    # regular option
                    args.append(option)
                    if not isinstance(v, bool):
                        args.append(str(v))

        return args

    def _convert_key(self, key, prefixes=None):
        if prefixes is None:
            prefixes = []

        for prefix in prefixes:
            if key.startswith('%s.' % prefix):
                key = key[len('%s.' % prefix):]
                break

        key = key.replace('.', '-')
        key = key.replace('_', '-')
        return '--' + key

    def as_args(self, strip_prefixes=None, omit_sections=None,
                omit_options=None):
        """Returns a list that can be passed to argparse or optparse.

        Each section/option is turned into "--section-option value"

        If the value is a boolean, the value will be omited.
        If the value is a sequence, it will be converted to a comma
        separated list

        Options:

        * strip_prefixes: a list of section names that will be stripped
          so the argument coverted as --option instead of --section-option

        * omit_sections: a list of section to ignore

        * omit_options: a list of options to ignore. Each option
          is provided as a 2-tuple (section, option)
        """
        args = []

        prefixes = ['DEFAULT']
        if strip_prefixes is not None:
            prefixes.extend(strip_prefixes)

        if omit_sections is None:
            omit_sections = []

        if omit_options is None:
            omit_options = []

        omit_options = ['%s.%s' % (sec, option)
                        for sec, option in omit_options]

        def _omit(key):
            if key in omit_options:
                return True

            for sec in omit_sections:
                if key.startswith('%s.' % sec):
                    return True
            return False

        for key, value in self.get_map().items():
            if _omit(key):
                continue

            args.append(self._convert_key(key, prefixes))

            # type conversion
            if isinstance(value, bool):
                continue
            elif isinstance(value, (list, tuple)):
                value = ','.join([str(v) for v in value])

            args.append(str(value))

        return args


class SettingsDict(dict):
    """A dict subclass with some extra helpers for dealing with app settings.

    This class extends the standard dictionary interface with some extra helper
    methods that are handy when dealing with application settings.  It expects
    the keys to be dotted setting names, where each component indicates one
    section in the settings heirarchy.  You get the following extras:

        * setdefaults:  copy any unset settings from another dict
        * getsection:   return a dict of settings for just one subsection

    """

    separator = "."

    def copy(self):
        """D.copy() -> a shallow copy of D.

        This overrides the default dict.copy method to ensure that the
        copy is also an instance of SettingsDict.
        """
        new_items = self.__class__()
        for k, v in self.items():
            new_items[k] = v
        return new_items

    def getsection(self, section):
        """Get a dict for just one sub-section of the config.

        This method extracts all the keys belonging to the name section and
        returns those values in a dict.  The section name is removed from
        each key.  For example::

            >>> c = SettingsDict({"a.one": 1, "a.two": 2, "b.three": 3})
            >>> c.getsection("a")
            {"one": 1, "two", 2}
            >>>
            >>> c.getsection("b")
            {"three": 3}
            >>>
            >>> c.getsection("c")
            {}

        """
        section_items = self.__class__()
        # If the section is "" then get keys without a section.
        if not section:
            for key, value in self.items():
                if self.separator not in key:
                    section_items[key] = value
        # Otherwise, get keys prefixed with that section name.
        else:
            prefix = section + self.separator
            for key, value in self.items():
                if key.startswith(prefix):
                    section_items[key[len(prefix):]] = value
        return section_items

    def setdefaults(self, *args, **kwds):
        """Import unset keys from another dict.

        This method lets you update the dict using defaults from another
        dict and/or using keyword arguments.  It's like the standard update()
        method except that it doesn't overwrite existing keys.
        """
        for arg in args:
            if hasattr(arg, "keys"):
                for k in arg:
                    self.setdefault(k, arg[k])
            else:
                for k, v in arg:
                    self.setdefault(k, v)
        for k, v in kwds.items():
            self.setdefault(k, v)
