"""Evaluator-only persistence API. Feature exporters must not import this module."""
import csv

def initialize(connection):
    connection.executescript("CREATE TABLE membership_rows(org TEXT,alert TEXT,incident TEXT,source_row_ordinal INTEGER); CREATE TABLE row_digests(digest TEXT,ordinal INTEGER); CREATE TABLE queue_labels(org TEXT,incident TEXT,queue_rank TEXT);")

def add_membership(connection,org,alert,incident,ordinal):
    connection.execute("INSERT INTO membership_rows VALUES(?,?,?,?)",(org,alert,incident,ordinal))

def add_full_row_digest(connection,digest,ordinal):
    connection.execute("INSERT INTO row_digests VALUES(?,?)",(digest,ordinal))

def add_queue_label(connection,org,incident,queue_rank):
    connection.execute("INSERT INTO queue_labels VALUES(?,?,?)",(org,incident,queue_rank))

def export_queue_labels(connection,path,headers):
    with open(path,"w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(headers)
        for row in connection.execute("SELECT org,incident,queue_rank FROM queue_labels"):
            w.writerow(row)
