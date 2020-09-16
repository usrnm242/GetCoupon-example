from collections import namedtuple
from math import sqrt
import random
try:
    import Image
except ImportError:
    from PIL import Image


Point = namedtuple('Point', ('coords', 'n', 'ct'))
Cluster = namedtuple('Cluster', ('points', 'center', 'n'))


def get_points(img):
    points = []
    w, h = img.size
    for count, color in img.getcolors(w * h):
        points.append(Point(color, 3, count))
    return points


rtoh = lambda rgb: '#%s' % ''.join(('%02x' % p for p in rgb))


def colorz(filename, n=3) -> 'list | str':
    if not filename:
        return ["#ffffff"]
    img = Image.open(filename)
    img.thumbnail((200, 200))
    w, h = img.size

    points = get_points(img)
    clusters = kmeans(points, n, 1)

    clusters.sort(key=lambda cluster: len(cluster[0]), reverse=True)
    # cluster[0] are points

    rgbs = [list(map(int, c.center.coords)) for c in clusters]

    color = None
    for index, (r, g, b) in enumerate(rgbs):
        # if r == g == b and 50 < r < 210  and index < len(rgbs) - 1:
        #     # if r=g=b then it is white/black/gray
        #     # if 50 < any < 210 then it is gray
        #     # if after gray is a color then skip gray
        #     continue
        # OPTIMIZE: do not return gray
        if 50 < r + g + b < 720:
            # 720 == 240 * 3  means light gray or white color
            color = [[r, g, b]]
            break
    else:
        color = [rgbs[0]]

    return list(map(rtoh, color))  # OPTIMIZE: without nested lists


def euclidean(p1, p2):
    return sqrt(sum([
        (p1.coords[i] - p2.coords[i]) ** 2 for i in range(p1.n)
    ]))


def calculate_center(points, n):
    vals = [0.0 for i in range(n)]
    plen = 0
    for p in points:
        plen += p.ct
        for i in range(n):
            vals[i] += (p.coords[i] * p.ct)
    return Point([(v / plen) for v in vals], n, 1)


def kmeans(points, k, min_diff):
    clusters = [Cluster([p], p, p.n) for p in random.sample(points, k)]

    while True:
        plists = [[] for i in range(k)]

        for p in points:
            smallest_distance = float('Inf')
            for i in range(k):
                distance = euclidean(p, clusters[i].center)
                if distance < smallest_distance:
                    smallest_distance = distance
                    idx = i
            plists[idx].append(p)

        diff = 0
        for i in range(k):
            old = clusters[i]
            center = calculate_center(plists[i], old.n)
            new = Cluster(plists[i], center, old.n)
            clusters[i] = new
            diff = max(diff, euclidean(old.center, new.center))

        if diff < min_diff:
            break

    return clusters


if __name__ == '__main__':
    photo = ""
    colors = colorz(photo, 3)[0]
    # a = colorz(argv[1], int(argv[2]))
    print(colors)
