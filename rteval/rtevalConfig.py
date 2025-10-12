# SPDX-License-Identifier: GPL-2.0-or-later
#
#   rteval - script for evaluating platform suitability for RT Linux
#
#           This program is used to determine the suitability of
#           a system for use in a Real Time Linux environment.
#           It starts up various system loads and measures event
#           latency while the loads are running. A report is generated
#           to show the latencies encountered during the run.
#
#   Copyright 2009,2010   Clark Williams <williams@redhat.com>
#   Copyright 2009,2010   David Sommerseth <davids@redhat.com>
#
import os
import sys
import configparser
from rteval.Log import Log
from rteval.systopology import SysTopology

def get_user_name():
    name = os.getenv('SUDO_USER')
    if not name:
        name = os.getenv('USER')
    if not name:
        import pwd
        name = pwd.getpwuid(os.getuid()).pw_name
    if not name:
        name = ""
    return name

def default_config_search(relative_path, verifdef=os.path.isdir):
    ConfigDirectories = [
        os.path.join(os.path.expanduser("~" + get_user_name()), '.rteval'),
        '/etc/rteval',
        '/usr/share/rteval',
        '/usr/local/share/rteval'
    ]

    if os.path.dirname(os.path.abspath(__file__)) != '/usr/share/rteval':
        ConfigDirectories = [
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'rteval')
            ] + ConfigDirectories

        for path in ConfigDirectories:
            if verifdef(os.path.join(path, *relative_path)):
                return os.path.join(path, *relative_path)

    return None


# HACK: A temporary hack to try to figure out where the install dir is.
typical_install_paths = ('/usr/bin', '/usr/local/bin')
try:
    if typical_install_paths.index(os.path.dirname(os.path.abspath(sys.argv[0]))):
        installdir = os.path.dirname(os.path.abspath(sys.argv[0]))
    else:
        installdir = '/usr/share/rteval'

except ValueError:
    installdir = '/usr/share/rteval'

default_config = {
    'rteval': {
        'quiet'      : False,
        'verbose'    : False,
        'keepdata'   : True,
        'debugging'  : False,
        'duration'   : '60',
        'sysreport'  : False,
        'reportdir'  : None,
        'reportfile' : None,
        'workdir'    : os.getcwd(),
        'installdir' : installdir,
        'srcdir'     : default_config_search(['loadsource']),
        'xslt_report': default_config_search(['rteval_text.xsl'], os.path.isfile),
        'xslt_histogram': default_config_search(['rteval_histogram_raw.xsl'], os.path.isfile),
        'report_interval': '600',
        'logging'    : False,
        'srcdownload': None,
        }
    }


class rtevalCfgSection:
    def __init__(self, section_cfg):
        if not isinstance(section_cfg, dict):
            raise TypeError('section_cfg argument is not a dict variable')

        self.__dict__['_rtevalCfgSection__cfgdata'] = section_cfg
        self.__dict__['_rtevalCfgSection__iter_list'] = None


    def __str__(self):
        "Simple method for dumping config when object is used as a string"
        if not self.__cfgdata:
            return "# empty"
        return "\n".join([f"{k}: {v}" for k, v in list(self.__cfgdata.items())]) + "\n"


    def __setattr__(self, key, val):
        self.__cfgdata[key] = val


    def __getattr__(self, key):
        if key in list(self.__cfgdata.keys()):
            return self.__cfgdata[key]
        return None

    def __contains__(self, key):
        return key in self.__cfgdata

    def items(self):
        return list(self.__cfgdata.items())


    def __iter__(self):
        "Initialises the iterator loop"
        self.__dict__['_rtevalCfgSection__iter_list'] = list(self.__cfgdata.keys())
        return self


    def __next__(self):
        "Function used by the iterator"

        if not self.__dict__['_rtevalCfgSection__iter_list'] \
                or len(self.__dict__['_rtevalCfgSection__iter_list']) == 0:
            raise StopIteration

        elmt = self.__dict__['_rtevalCfgSection__iter_list'].pop()

        # HACK: This element shouldn't really appear here ... why!??!
        while (elmt == '_rtevalCfgSection__cfgdata') \
               and (len(self.__dict__['_rtevalCfgSection__iter_list']) > 0):
            elmt = self.__dict__['_rtevalCfgSection__iter_list'].pop()

        return (elmt, self.__cfgdata[elmt])


    def has_key(self, key):
        "has_key() wrapper for the configuration data"
        return key in self.__cfgdata


    def keys(self):
        "keys() wrapper for configuration data"
        return list(self.__cfgdata.keys())


    def setdefault(self, key, defvalue):
        if key not in self.__cfgdata:
            self.__cfgdata[key] = defvalue
        return self.__cfgdata[key]


    def update(self, newdict):
        if not isinstance(newdict, dict):
            raise TypeError('update() method expects a dict as argument')

        for key, val in list(newdict.items()):
            self.__cfgdata[key] = val


    def wipe(self):
        self.__cfgdata = {}



class rtevalConfig:
    "Config parser for rteval"

    def __init__(self, initvars=None, logger=None):
        self.__config_data = {}
        self.__config_files = []
        self.__logger = logger

        # get our system topology info
        self.__systopology = SysTopology()
        print(f"got system topology: {self.__systopology}")

        # Import the default config first
        for sect, vals in list(default_config.items()):
            self.__update_section(sect, vals)

        # Set the runtime provided init variables
        if initvars:
            if not isinstance(newdict, dict):
                raise TypeError('initvars argument is not a dict variable')

            for sect, vals in list(initvars.items()):
                self.__update_section(sect, vals)


    def __update_section(self, section, newvars):
        if not section or not newvars:
            return

        if section not in self.__config_data:
            self.__config_data[section] = rtevalCfgSection(newvars)
        else:
            self.__config_data[section].update(newvars)


    def __str__(self):
        "Simple method for dumping config when object is used as a string"
        ret = ""
        for sect in list(self.__config_data.keys()):
            ret += f"[{sect}]\n{str(self.__config_data[sect])}\n"
        return ret


    def __info(self, str):
        if self.__logger:
            self.__logger.log(Log.INFO, str)


    def __find_config(self):
        "locate a config file"

        for f in ('rteval.conf', '/etc/rteval.conf'):
            p = os.path.abspath(f)
            if os.path.exists(p):
                self.__info(f"found config file {p}")
                return p
        raise RuntimeError("Unable to find configfile")


    def Load(self, fname=None, append=False):
        "read and parse the configfile"

        try:
            cfgfile = fname or self.__find_config()
        except:
            self.__info("no config file")
            return

        if self.ConfigParsed(cfgfile):
            # Don't try to reread this file if it's already been parsed
            return

        self.__info(f"reading config file {cfgfile}")
        ini = configparser.ConfigParser()
        ini.optionxform = str
        ini.read(cfgfile)

        # wipe any previously read config info
        if not append:
            for s in list(self.__config_data.keys()):
                self.__config_data[s].wipe()

        # copy the section data into the __config_data dictionary
        for s in ini.sections():
            cfg = {}
            for (k, v) in ini.items(s):
                cfg[k] = v.split('#')[0].strip()

            self.__update_section(s, cfg)

        # Register the file as read
        self.__config_files.append(cfgfile)
        return cfgfile


    def ConfigParsed(self, fname):
        "Returns True if the config file given by name has already been parsed"
        return self.__config_files.__contains__(fname)


    def UpdateFromOptionParser(self, cmd_opts):
        "Parse through the command line options and update the appropriate config settings"

        last_sect = None
        for sk, v in sorted(vars(cmd_opts).items()):
            # argparse key template: {sectionname}___{key}
            k = sk.split('___')
            if k[0] != last_sect:
                # If the section name changed, retrieve the section variables
                try:
                    sect = self.GetSection(k[0])
                except KeyError:
                    # If section does not exist, create it
                    self.AppendConfig(k[0], {k[1]: v})
                    sect = self.GetSection(k[0])

                last_sect = k[0]

            setattr(sect, k[1], v)


    def AppendConfig(self, section, cfgvars):
        "Add more config parameters to a section.  cfgvars must be a dictionary of parameters"
        self.__update_section(section, cfgvars)


    def HasSection(self, section):
        return section in self.__config_data


    def GetSection(self, section):
        try:
            # Return a new object with config settings of a given section
            return self.__config_data[section]
        except KeyError:
            raise KeyError(f"The section '{section}' does not exist in the config file")


def unit_test(rootdir):
    try:
        l = Log()
        l.SetLogVerbosity(Log.INFO)
        cfg = rtevalConfig(logger=l)
        cfg.Load(os.path.join(rootdir, 'rteval.conf'))
        print(cfg)
        return 0
    except Exception as e:
        print("** EXCEPTION %s", str(e))
        return 1


if __name__ == '__main__':
    sys.exit(unit_test('..'))
