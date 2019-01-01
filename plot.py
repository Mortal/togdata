import argparse
import datetime
import glob
import re

import matplotlib.pyplot as plt
import ogr
import osr

from parse import parse_trains, classlist


def transformCoords(xs, ys, fromEPSG, toEPSG, outfile=None):
    fromSR = osr.SpatialReference()
    fromSR.ImportFromEPSGA(fromEPSG)
    toSR = osr.SpatialReference()
    toSR.ImportFromEPSGA(toEPSG)
    if not fromSR or not toSR:
        raise Exception
    p = ogr.Geometry(ogr.wkbLineString)
    p.AssignSpatialReference(fromSR)
    for (x, y) in zip(xs, ys):
        p.AddPoint(x, y)
    if p.TransformTo(toSR) != 0:
        raise Exception
    if outfile is not None:
        driver = ogr.GetDriverByName("GeoJSON")
        ds = driver.CreateDataSource(outfile)
        layer = ds.CreateLayer(outfile, toSR, geom_type=ogr.wkbLineString)
        defn = layer.GetLayerDefn()
        feature = ogr.Feature(defn)
        feature.SetGeometry(p)
        layer.CreateFeature(feature)
        del feature
        del layer
        del ds
        del driver
    xs, ys = [], []
    for i in range(0, p.GetPointCount()):
        x, y = p.GetPoint(i)[:2]
        xs.append(x)
        ys.append(y)
    return xs, ys


parser = argparse.ArgumentParser()
parser.add_argument("-o", "--geojson-output")
parser.add_argument("-c", "--classes", type=classlist, default=[1, 2])
parser.add_argument("number")
parser.add_argument("date")


def main():
    args = vars(parser.parse_args())
    outfile = args.pop("geojson_output")
    ds, xs, ys = zip(*get_data(**args))
    xs = [x / 1e6 for x in xs]
    ys = [y / 1e6 for y in ys]
    xs, ys = transformCoords(xs, ys, 4326, 25832, outfile=outfile)
    # fig, (ax1, ax2) = plt.subplots(1, 2)
    # ax1.plot(ds, xs)
    # ax2.plot(ds, ys)

    r = 1
    speeds = []
    for d1, d2, x1, x2, y1, y2 in zip(
        ds[:-r], ds[r:], xs[:-r], xs[r:], ys[:-r], ys[r:]
    ):
        dt = (d2 - d1).total_seconds()
        dx = x2 - x1
        dy = y2 - y1
        d2 = dx ** 2 + dy ** 2
        speed = d2 ** .5 / dt * 3.6
        speeds.append(speed)

    plt.figure()
    plt.plot(ds[:-r], speeds, ".-")

    plt.figure()
    plt.plot(xs, ys, ".-")

    plt.show()
    # pd = px = py = None
    # for d, x, y in get_data(number, classes, date):
    #     dt = (d - pd).total_seconds() if pd else 1
    #     print(d, x, y, '%f' % ((x - px)/dt) if px else 0, '%f' % ((y - py)/dt) if py else 0)
    #     px, py = x, y
    #     pd = d


def get_data(number, classes, date):
    filenames = sorted(glob.glob("data/%s*.json" % date))
    for filename in filenames:
        trains = parse_trains(filename)
        trains = [
            t
            for t in trains
            if t["class"] in classes and str(number) in t["name"].split()
        ]
        if not trains:
            continue
        train, = trains
        mo = re.search(
            r"(?P<year>20\d\d)(?P<month>\d\d)(?P<day>\d\d)(?P<hour>\d\d)(?P<minute>\d\d)(?P<second>\d\d)",
            filename,
        )
        dt = datetime.datetime(**{k: int(v) for k, v in mo.groupdict().items()})
        yield dt, train["x"], train["y"]


if __name__ == "__main__":
    main()
