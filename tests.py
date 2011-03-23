# -* coding: utf-8 -*-
"""
We use db "test" and collection "people" for testing purposes
"""
from unittest import TestCase
from mongoprofile import parse_record, mongoprofile


class ParserTest(TestCase):
    command_cmd = "query test.$cmd ntoreturn:1 command: { drop: \"people\" } reslen:134 bytes:118"
    insert_cmd = "insert test.people"
    update_cmd = "update test.people  query: { name: \"John\" } nscanned:1 fastmod "
    remove_cmd = "remove test.people  query: { name: \"Mary\" }"
    query_cmd = "query test.people reslen:86 nscanned:1  \nquery: { age: { $gt: 20.0 } }  nreturned:1 bytes:70"

    def testCommandCmd(self):
        record_source = dict(info=self.command_cmd)
        record = parse_record(record_source)
        self.assertEquals(str(record), 'test> db.runCommand({ drop: "people" })')
        self.assertEquals(record['ntoreturn'], 1)
        self.assertEquals(record['reslen'], 134)
        self.assertEquals(record['bytes'], 118)

    def testInsertCmd(self):
        record_source = dict(info=self.insert_cmd)
        record = parse_record(record_source)
        self.assertEquals(str(record), 'test> db.people.insert({...})')

    def testUpdateCmd(self):
        record_source = dict(info=self.update_cmd)
        record = parse_record(record_source)
        self.assertEquals(str(record), 'test> db.people.update({ name: "John" }, {...})')
        self.assertEquals(record['nscanned'], 1)
        self.assertEquals(record['fastmod'], True)

    def testRemoveCmd(self):
        record_source = dict(info=self.remove_cmd)
        record = parse_record(record_source)
        self.assertEquals(str(record), 'test> db.people.remove({ name: "Mary" })')

    def testQueryCmd(self):
        record_source = dict(info=self.query_cmd)
        record = parse_record(record_source)
        self.assertEquals(str(record), 'test> db.people.find({ age: { $gt: 20.0 } })')


from pymongo import Connection
class MongoProfile(TestCase):

    expected_records = [
        'test> db.people.insert({...})',
        'test> db.people.insert({...})',
        'test> db.people.update({ name: "John" }, {...})',
        'test> db.people.remove({ name: "Mary" })',
        'test> db.people.find({ $query: { age: { $gt: 20.0 } } })',
        'test> db.runCommand({ count: "people", query: { age: { $gt: 20.0 } }, fields: null })',
    ]

    def setUp(self):
        self.db = Connection().test

    def testMongoProfile(self):
        with mongoprofile(self.db) as profile:
            self.db.people.insert(dict(name='John', age=20))
            self.db.people.insert(dict(name='Mary', age=30))
            self.db.people.update({'name': 'John'}, {'age': 21})
            self.db.people.remove({'name': 'Mary'})
            list(self.db.people.find({'age': {'$gt': 20.0}}))
            self.db.people.find({'age': {'$gt': 20.0}}).count()
        record_info = [str(record) for record in profile]
        self.assertEquals(self.expected_records, record_info)

    def tearDown(self):
        self.db.drop_collection('people')