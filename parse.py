import json
import argparse
import requests
import html5lib


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--classes', type=classlist, default=[1, 2])
    parser.add_argument('-n', '--number')
    parser.add_argument('filename')
    args = parser.parse_args()

    with open(args.filename, encoding='latin1') as fp:
        o = json.load(fp)

    data_trains = o[0]
    train_array = data_trains[:-1]
    meta = data_trains[-1]
    # numtrains is only a guess
    META_KEYS = 'timestamp numtrains interval step version'.split()
    meta = dict(zip(META_KEYS, meta))

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
        print_traininfo(parse_traininfo(fetch_traininfo(last)))

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


def fetch_traininfo(train):
    id = train['id']
    base = 'http://www.dsb.dk/Rejseplan/bin/traininfo.exe/mn/'
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
        tag_names = [cell.tag for cell in row]
        assert all(tag == '{%s}td' % NS['h'] for tag in tag_names), (row.tag, tag_names)
        _1, planned, name, _2, prognosis = map(element_text_content, row)
        if planned:
            yield planned, name, prognosis


def print_traininfo(plan):
    for parts in plan:
        print('\t'.join(s.replace('\n', '-') for s in parts))


if __name__ == "__main__":
    main()
