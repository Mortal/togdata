import argparse
import collections
import json
import re
from typing import TypedDict

import html5lib
import requests


CLASSES = {
    1: 'IC',
    2: 'ICL',
    4: 'regional',
    8: 'other',  # cross-country, VLTJ/lokalbane, togbus
    16: 'S',
}
CLASS_DICT = {v: k for k, v in CLASSES.items()}


def classlist(s):
    res = []
    for v in s.split(','):
        try:
            res.append(int(v))
        except ValueError:
            res.append(CLASS_DICT[v])
    return res


class Meta(TypedDict):
    timestamp: str
    interval: int
    step: int


def parse_trains(filename):
    with open(filename, encoding='latin1') as fp:
        response = json.load(fp)

    if isinstance(response, dict) and "error" in response:
        raise Exception(f"Response is an error response: {response!r}")
    assert isinstance(response, list)
    train_array, stop_array = response
    train_array = train_array[:-1]
    # numtrains is only a guess; it's not used by the official frontend.
    # The official frontend claims that train_array[-1][5] is a date,
    # but this is also unused, and the server only returns 5 values.
    meta: Meta = {
        "timestamp": train_array[-1][0],
        # "numtrains": train_array[-1][1],
        "interval": train_array[-1][2],
        "step": train_array[-1][3],
        # "version": train_array[-1][4],
        # "date": train_array[-1][5],
    }

    trains = []

    for t_vals in train_array:
        KEYS = ('name x y id direction class delay lstopname poly prevstop ' +
                'prevstopno nextstop nextstopno refdate').split()
        t = dict(zip(KEYS, t_vals))
        # hash_train_id = t['id'].replace('/', 'x')
        # unsure if [4] is speed, but seems probable, maybe km/h?
        POLY_KEYS = 'x y time direction speed'.split()
        t['name'] = ' '.join(t['name'].split())
        t['poly'] = dict(zip(POLY_KEYS, t['poly']))

        trains.append(t)
    return trains


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--classes', type=classlist, default=[1, 2])
    parser.add_argument('-n', '--number')
    parser.add_argument('filename')
    args = parser.parse_args()

    trains = parse_trains(args.filename)

    n_printed = 0
    last = None
    for t in trains:
        if args.classes and t['class'] not in args.classes:
            continue
        if args.number and args.number not in t['name'].split():
            continue
        last = t
        n_printed += 1
        print('%(name)s towards %(lstopname)s' % t)
        print('Travelling from %(prevstop)s to %(nextstop)s' % t)
        print('Position: %(x)s %(y)s' % t)
        print('')

    if n_printed == 1:
        fetch_and_print_traininfo(last)

    # by_class = {}
    # for t in trains:
    #     by_class.setdefault(t['class'], []).append(t)

    # for c, ts in by_class.items():
    #     print("Class %s: %s" % (c, ', '.join(t['name'] for t in ts)))


NS = {'h': 'http://www.w3.org/1999/xhtml'}


def element_text_content(element):
    r"""
    >>> s = '''
    ... <td>
    ... 07:51 (ank.)
    ... <br/>
    ... 08:00 (afg.)
    ... </td>
    ... '''
    >>> from xml.etree.ElementTree import fromstring
    >>> element_text_content(fromstring(s))
    '07:51 (ank.)\n08:00 (afg.)'
    """

    def visit(e):
        if e.tag == '{%s}br' % NS['h']:
            yield '\n'
            yield ' '.join((e.tail or '').split())
            return
        yield ' '.join((e.text or '').split())
        for c in e:
            yield ''.join(visit(c))
        yield ' '.join((e.tail or '').split())

    return ''.join(visit(element))


TrainInfo = collections.namedtuple(
    'TrainInfo',
    'name planned_arrival actual_arrival planned_departure actual_departure')


def fetch_and_print_traininfo(train):
    print_traininfo(parse_traininfo(fetch_traininfo(train)))


def fetch_traininfo(train):
    base = 'https://www.rejseplanen.dk/bin/traininfo.exe/mn/'
    url = (base + train['id'] +
           '?L=vs_livemap.vs_dsb&date=%s' % train['refdate'] +
           '&showWithoutHeader=yes&compactView=yes' +
           '&prodclass=%s&' % train['class'])
    with requests.get(url) as response:
        document = html5lib.parse(response.content,
                                  transport_encoding=response.encoding)
    return document


def parse_traininfo(document):
    for row in document.findall('.//h:tr', NS):
        _1, planned, name, _2, prognosis = map(element_text_content, row)
        if prognosis in ("delvist aflyst", "delvist aflystdelvist aflyst"):
            yield TrainInfo(name, "XX:XX", "XX:XX",
                            "XX:XX", "XX:XX")
            continue
        if not planned:
            continue
        pattern = r'^(?:(\d+:\d+) \(ank\.\))?\n?(?:(\d+:\d+) \(afg\.\))?\Z'
        mo = re.match(pattern, planned)
        if not mo:
            raise ValueError(planned)
        planned_arrival, planned_departure = mo.groups()
        pattern = r'^(?:(?:ca\. (\d+:\d+))?\n(?:ca\. (\d+:\d+))?)?\Z'
        mo = re.match(pattern, prognosis)
        if not mo:
            raise ValueError(prognosis)
        actual_arrival, actual_departure = mo.groups()
        yield TrainInfo(name, planned_arrival, actual_arrival,
                        planned_departure, actual_departure)


def format_time(planned, actual):
    time_width = 5
    if not planned:
        return ' ' * (2*time_width+1)
    if not actual:
        return planned.rjust(time_width) + ' ' * (time_width + 1)
    strikethrough = '\x1B[9m'
    # red = '\x1B[31m'
    bold = '\x1B[1m'
    return '{delete}{planned:>5}{reset} {em}{actual:>5}{reset}'.format(
        delete=strikethrough,
        reset='\x1B[0m',
        em=bold,
        planned=planned,
        actual=actual)


def abbreviate_name(name):
    name = re.sub(r' St\.', '', name)
    name = re.sub(r' \(Jylland\)', ' J', name)
    return name


def name_and_delay(name, planned, actual):
    if planned == actual or not planned or not actual:
        return abbreviate_name(name)
    h1, m1 = planned.split(":")
    h2, m2 = actual.split(":")
    delay = (int(h2) - int(h1)) * 60 + (int(m2) - int(m1))
    return "%s (+%s)" % (abbreviate_name(name), delay)


def print_traininfo(plan):
    print(' STA   ETA   STD   ETD')
    for t in plan:
        print(' '.join(
            (format_time(t.planned_arrival, t.actual_arrival),
             format_time(t.planned_departure, t.actual_departure),
             name_and_delay(t.name, t.planned_arrival, t.actual_arrival),
            )))


if __name__ == "__main__":
    main()
