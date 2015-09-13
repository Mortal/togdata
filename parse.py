import json
import argparse


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

    for t in trains:
        if args.classes and t['class'] not in args.classes:
            continue
        if args.number and args.number not in t['name'].split():
            continue
        print('%(name)s towards %(lstopname)s' % t)
        print('Travelling from %(prevstop)s to %(nextstop)s' % t)
        print('Position: %(x)s %(y)s' % t)
        print('')

    # by_class = {}
    # for t in trains:
    #     by_class.setdefault(t['class'], []).append(t)

    # for c, ts in by_class.items():
    #     print("Class %s: %s" % (c, ', '.join(t['name'] for t in ts)))


if __name__ == "__main__":
    main()
