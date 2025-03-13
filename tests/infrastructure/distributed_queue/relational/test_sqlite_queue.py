"""Test that the sqlite queue works"""
import concurrent.futures
import json
import os
import queue
import traceback

import pytest

import pyantz.infrastructure.distributed_queue.relational.sqlite_queue as sq
from pyantz.infrastructure.core.status import Status


@pytest.fixture(scope='function')
def sqlite_queue(tmpdir) -> sq.SqliteQueue:
    """Convience code to make the sqlite queue"""
    
    file_db = os.path.join(tmpdir, 'queue.db')
    q = sq.SqliteQueue(file_db)
    return q

def test_sqlite_queue_simple(sqlite_queue) -> None:
    """Test simple put / get with the sqlite"""
    sqlite_queue.put('{"hello":"there"}', '1')
    assert sqlite_queue.get() == '{"hello":"there"}'

    with pytest.raises(queue.Empty):
        sqlite_queue.get()

def test_sqlite_queue_dependency(sqlite_queue) -> None:
    """Test making jobs that depends on each other"""

    job_ids = list('abcdefg')

    dependency_graph = {
        'f': ['d', 'e'],
        'd': ['a', 'b']
    }

    for jid in job_ids:
        depends_on = None
        if jid in dependency_graph:
            depends_on = dependency_graph[jid]
        sqlite_queue.put(f"""{{"{jid}":"{jid}"}}""", jid, depends_on=depends_on)

    assert sqlite_queue.get() == """{"a":"a"}"""
    assert sqlite_queue.get() == """{"b":"b"}"""
    assert sqlite_queue.get() == """{"c":"c"}"""
    assert sqlite_queue.get() == """{"e":"e"}"""
    assert sqlite_queue.get() == """{"g":"g"}"""

    with pytest.raises(queue.Empty):
        sqlite_queue.get()

    sqlite_queue.set_status('a', Status.SUCCESS)
    with pytest.raises(queue.Empty):
        sqlite_queue.get()
    sqlite_queue.set_status('e', Status.FINAL)
    with pytest.raises(queue.Empty):
        sqlite_queue.get()
    sqlite_queue.set_status('b', Status.FINAL)
    assert sqlite_queue.get() == """{"d":"d"}"""
    with pytest.raises(queue.Empty):
        sqlite_queue.get()
    sqlite_queue.set_status('d', Status.SUCCESS)
    assert sqlite_queue.get() == """{"f":"f"}"""

def test_sqlite_depends_on_error(sqlite_queue) -> None:
    """Test that errors propagate and disallow future jobs to error out"""
    
    job_ids = list('abcdefg')

    dependency_graph = {
        'f': ['d', 'e'],
        'd': ['a', 'b']
    }

    for jid in job_ids:
        depends_on = None
        if jid in dependency_graph:
            depends_on = dependency_graph[jid]
        sqlite_queue.put(f"""{{"{jid}":"{jid}"}}""", jid, depends_on=depends_on)

    assert sqlite_queue.qsize() == 7
    assert sqlite_queue.get() == """{"a":"a"}"""
    assert sqlite_queue.qsize() == 6
    assert sqlite_queue.get() == """{"b":"b"}"""
    assert sqlite_queue.qsize() == 5
    assert sqlite_queue.get() == """{"c":"c"}"""
    assert sqlite_queue.qsize() == 4
    assert sqlite_queue.get() == """{"e":"e"}"""
    assert sqlite_queue.qsize() == 3
    assert sqlite_queue.get() == """{"g":"g"}"""
    assert sqlite_queue.qsize() == 2

    with pytest.raises(queue.Empty):
        sqlite_queue.get()

    sqlite_queue.set_status('a', Status.SUCCESS)
    with pytest.raises(queue.Empty):
        sqlite_queue.get()
    sqlite_queue.set_status('b', Status.FINAL)
    assert sqlite_queue.qsize() == 2
    assert sqlite_queue.get() == """{"d":"d"}"""
    assert sqlite_queue.qsize() == 1
    with pytest.raises(queue.Empty):
        sqlite_queue.get()
    sqlite_queue.set_status('d', Status.SUCCESS)
    sqlite_queue.set_status('e', Status.ERROR) # F can never happen now
    assert sqlite_queue.qsize() == 0

    for _ in range(10):
        # run multiple times because .get calls the error resolver
        # and we need to verify it's stable
        with pytest.raises(queue.Empty):
            sqlite_queue.get()

def test_sqlite_queue_qsize(sqlite_queue) -> None:
    """Test that qsize works"""

    some_content = """{"some_field": ["some_valud"]}"""

    for i in range(100):
        sqlite_queue.put(some_content, str(i))
        assert sqlite_queue.qsize() == (i+1)


def test_large_chunks(sqlite_queue) -> None:
    """Test that very large jsons are allowed"""

    large_json = json.dumps({
        k: 'a'*100
        for k in range(4000)
    })

    sqlite_queue.put(large_json, '1')
    assert sqlite_queue.get() == large_json

def test_multiproducer_multi_consumer(tmpdir) -> None:
    """Test multiprocess access to the queue"""

    file_db = os.fspath(os.path.join(tmpdir, 'queue.db'))
    some_content = """{"some_field": ["some_valud"]}"""
        
    with concurrent.futures.ThreadPoolExecutor() as executor:

        submit_result = {
            executor.submit(
                _submit_to_q, i, file_db
            )
            for i in range(2000)
        }

        for submit_future in concurrent.futures.as_completed(submit_result):
            assert submit_future.result()

        get_result = {
            executor.submit(
                _get_from_q, file_db
            )
        }
        for get_future in concurrent.futures.as_completed(get_result):
            assert get_future.result() == some_content


def _submit_to_q(i, file_db) -> bool:
    """Submit to the queue"""
    some_content = """{"some_field": ["some_valud"]}"""
    try:
        q = sq.SqliteQueue(file_db)
        q.put(
            some_content,
            str(i)
        )
        return True
    except Exception as exc:
        traceback.print_exc()
        print(exc)
        return False
    
def _get_from_q(file_db) -> str:
    try:
        q = sq.SqliteQueue(file_db)
        return q.get()
    except Exception as _:
        return ''