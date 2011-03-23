#! -*- coding: utf-8 -*-
"""
Set of functions and objects to retreive and parse the output of MongoDB's
"db.system.profile.find()"
"""
import pymongo
import re
_re_command_record = re.compile(
    ur'query (?P<db>[^.]+)\.\$cmd ntoreturn:(?P<ntoreturn>\d+) '
    ur'command: (?P<command>{.*}) (?P<options>.*)')
_re_query_record = re.compile(
    ur'query (?P<db>[^.]+)\.(?P<collection>[^ ]+) reslen:(?P<reslen>\d+) nscanned:(?P<nscanned>\d+)\s*\n'
    ur'query: (?P<query>{.*}) (?P<options>.*)'
)
_re_insert_record = re.compile(
    ur'insert (?P<db>[^.]+)\.(?P<collection>[^ ]+)'
)
_re_update_record = re.compile(
    ur'update (?P<db>[^.]+)\.(?P<collection>[^ ]+)  query: (?P<query>{.*})(?P<options>.*)'
)
_re_remove_record = re.compile(
    ur'remove (?P<db>[^.]+)\.(?P<collection>[^ ]+)  query: (?P<query>{.*})(?P<options>.*)'
)
class mongoprofile(object):

    def __init__(self, db):
        self.db = db

    def __enter__(self):
        self._level = self.db.profiling_level()
        self._records = self.db.system.profile.find().count()
        if self._level == pymongo.ALL:
            self._records += 2
        self.db.set_profiling_level(pymongo.ALL)
        self.log = []
        return self.log

    def __exit__(self, type, value, traceback):
        stats = self.db.system.profile.find().skip(self._records)
        for record in stats:
            self.log.append(parse_record(record))
        self.log += list(stats)
        self.db.set_profiling_level(self._level)


class dummymongoprofile(object):
    def __init__(self, db):
        pass
    def __enter__(self):
        return []
    def __exit__(self, type, value, traceback):
        pass


def parse_record(record_source):
    record_map = {
        _re_command_record: CommandRecord,
        _re_query_record: QueryRecord,
        _re_insert_record: InsertRecord,
        _re_update_record: UpdateRecord,
        _re_remove_record: RemoveRecord,
    }
    info = record_source['info']
    # find record by info
    record = None
    for regex, RecordClass in record_map.iteritems():
        match = regex.search(info)
        if match:
            results = match.groupdict()
            record = RecordClass(record_source)
            record.update(results)
            break
    if not record:
        record = UnknownRecord(record_source)
    # parse record options, if any (see regexps)
    if 'options' in record:
        options = record.pop('options')
        record.update(_parse_record_options(options))
    # convert ints to integer
    for k, v in record.iteritems():
        if isinstance(record[k], basestring):
            try: record[k] = int(record[k])
            except ValueError: pass
    return record



def _parse_record_options(options):
    ret = {}
    option_list = options.strip().split()
    for option in option_list:
        if ':' in option:
            k, v = option.split(':', 1)
        else:
            k, v = option, True
        ret[k] = v
    return ret


class BaseRecord(dict):

    def short_info(self):
        """ get short info about query results """
        # remove useless data
        record = dict(self)
        useless_fields = 'command info collection query db ts'.split()
        for field in useless_fields:
            if field in record:
                del record[field]
        # print data
        ret = []
        for items in record.iteritems():
            ret.append('%s:%s ' % items)
        return '  '.join(ret)

class CommandRecord(BaseRecord):
    def __str__(self):
        return str('%(db)s> db.runCommand(%(command)s)' % self)

class QueryRecord(BaseRecord):
    def __str__(self):
        return str('%(db)s> db.%(collection)s.find(%(query)s)' % self)

class InsertRecord(BaseRecord):
    def __str__(self):
        return str('%(db)s> db.%(collection)s.insert({...})' % self)

class UpdateRecord(BaseRecord):
    def __str__(self):
        return str('%(db)s> db.%(collection)s.update(%(query)s, {...})' % self)

class RemoveRecord(BaseRecord):
    def __str__(self):
        return str('%(db)s> db.%(collection)s.remove(%(query)s)' % self)

class UnknownRecord(BaseRecord):
    pass