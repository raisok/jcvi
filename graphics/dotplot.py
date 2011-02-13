#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
%prog anchorfile --qbed query.bed --sbed subject.bed

visualize the anchorfile in a dotplot. anchorfile contains two columns
indicating gene pairs, followed by an optional column (e.g. Ks value)
"""

import os.path as op
import sys
import logging
from random import sample
from itertools import groupby
from optparse import OptionParser

from jcvi.graphics.base import plt, ticker, Rectangle, cm, _
from jcvi.formats.bed import Bed
from jcvi.algorithms.synteny import batch_scan
from jcvi.apps.base import debug
debug()


def get_breaks(bed):
    # get chromosome break positions
    simple_bed = bed.simple_bed
    for seqid, ranks in groupby(simple_bed, key=lambda x:x[0]):
        ranks = list(ranks)
        # chromosome, extent of the chromosome
        yield seqid, ranks[0][1], ranks[-1][1]


def draw_box(clusters, ax, color="b"):

    for cluster in clusters:
        xrect, yrect = zip(*cluster)
        xmin, xmax, ymin, ymax = min(xrect), max(xrect), \
                                min(yrect), max(yrect)
        ax.add_patch(Rectangle((xmin, ymin), xmax-xmin, ymax-ymin,\
                                ec=color, fc='y', alpha=.5))


def draw_cmap(ax, cmap_text, vmin, vmax, cmap=None, reverse=False):
    X = [1, 0] if reverse else [0, 1]
    Y = np.array([X, X])
    xmin, xmax = .5, .9
    ymin, ymax = .02, .04
    ax.imshow(Y, extent=(xmin,xmax,ymin,ymax), cmap=cmap)
    ax.text(xmin-.01, (ymin + ymax)*.5, _(cmap_text), ha="right", va="center",
            size=10)
    vmiddle = (vmin + vmax) * .5
    xmiddle = (xmin + xmax) * .5
    for x, v in zip((xmin, xmiddle, xmax), (vmin, vmiddle, vmax)):
        ax.text(x, ymin-.005, _("%.1f" % v), ha="center", va="top", size=10)


def dotplot(anchorfile, qbed, sbed, image_name, vmin, vmax, 
        is_self=False, synteny=False, cmap_text=None):

    fp = open(anchorfile)

    qorder = qbed.order
    sorder = sbed.order

    data = []
    logging.debug("normalize the values to [%.1f, %.1f]" % (vmin, vmax))

    for row in fp:
        atoms = row.split()
        if len(atoms) < 3: continue
        query, subject, value = row.split()[:3]
        try: value = float(value)
        except: value = vmin 

        if value < vmin: value = vmin
        if value > vmax: value = vmax

        if query not in qorder: 
            #logging.warning("ignore %s" % query)
            continue
        if subject not in sorder: 
            #logging.warning("ignore %s" % subject)
            continue

        qi, q = qorder[query]
        si, s = sorder[subject]
        data.append((qi, si, vmax-value))

    fig = plt.figure(1,(8,8))
    root = fig.add_axes([0,0,1,1]) # the whole canvas
    ax = fig.add_axes([.1,.1,.8,.8]) # the dot plot

    sample_number = 5000 # only show random subset
    if len(data) > sample_number:
        data = sample(data, sample_number)

    # the data are plotted in this order, the least value are plotted
    # last for aesthetics
    data.sort(key=lambda x: -x[2])

    default_cm = cm.copper
    x, y, c = zip(*data)
    ax.scatter(x, y, c=c, s=2, lw=0, cmap=default_cm, 
            vmin=vmin, vmax=vmax)

    if synteny:
        clusters = batch_scan(data, qbed, sbed)
        draw_box(clusters, ax)

    if cmap_text:
        draw_cmap(root, cmap_text, vmin, vmax, cmap=default_cm, reverse=True)

    xsize, ysize = len(qbed), len(sbed)
    xlim = (0, xsize)
    ylim = (ysize, 0) # invert the y-axis

    xchr_labels, ychr_labels = [], []
    ignore = True # tag to mark whether to plot chromosome name (skip small ones)
    ignore_size = 100
    # plot the chromosome breaks
    for (seqid, beg, end) in get_breaks(qbed):
        ignore = abs(end-beg) < ignore_size 
        seqid = seqid.split("_")[-1]
        try: 
            seqid = int(seqid)
            seqid = "c%d" % seqid
        except: 
            pass

        xchr_labels.append((seqid, (beg + end)/2, ignore))
        ax.plot([beg, beg], ylim, "g-", lw=1)

    for (seqid, beg, end) in get_breaks(sbed):
        ignore = abs(end-beg) < ignore_size 
        seqid = seqid.split("_")[-1]
        try: 
            seqid = int(seqid)
            seqid = "c%d" % seqid
        except:
            pass

        ychr_labels.append((seqid, (beg + end)/2, ignore))
        ax.plot(xlim, [beg, beg], "g-", lw=1)

    # plot the chromosome labels
    for label, pos, ignore in xchr_labels:
        pos = .1 + pos * .8/ xsize
        if not ignore:
            root.text(pos, .91, _(label), color="b",
                va="bottom", rotation=45)

    # remember y labels are inverted
    for label, pos, ignore in ychr_labels:
        pos = .9 - pos * .8/ ysize
        if not ignore:
            root.text(.91, pos, _(label), color="b",
                ha="left", va="center")

    # create a diagonal to separate mirror image for self comparison
    if is_self:
        ax.plot(xlim, ylim, 'm-', alpha=.5, lw=2)

    ax.set_xlim(xlim)
    ax.set_ylim(ylim)

    to_ax_label = lambda fname: _(op.basename(fname).split(".")[0])

    # add genome names
    ax.set_xlabel(to_ax_label(qbed.filename), size=15)
    ax.set_ylabel(to_ax_label(sbed.filename), size=15)

    # beautify the numeric axis
    for tick in ax.get_xticklines() + ax.get_yticklines():
        tick.set_visible(False) 

    formatter = ticker.FuncFormatter(lambda x, pos: _("%dK" % (int(x)/1000)))
    ax.xaxis.set_major_formatter(formatter)
    ax.yaxis.set_major_formatter(formatter)

    plt.setp(ax.get_xticklabels() + ax.get_yticklabels(), color='gray', size=10)

    root.set_xlim(0, 1)
    root.set_ylim(0, 1)
    root.set_axis_off()
    logging.debug("print image to %s" % image_name)
    plt.savefig(image_name, dpi=1000)


if __name__ == "__main__":

    p = OptionParser(__doc__)
    p.add_option("--qbed", dest="qbed", help="path to qbed")
    p.add_option("--sbed", dest="sbed", help="path to sbed")
    p.add_option("--synteny", dest="synteny", 
            default=False, action="store_true",
            help="run a fast synteny scan and display synteny blocks")
    p.add_option("--cmap_text", dest="cmap_text", default="Synonymous substitutions (Ks)",
            help="draw a colormap box on the bottom-left corner")
    p.add_option("--format", dest="format", default="png",
            help="generate image of format (png, pdf, ps, eps, svg, etc.)"
            "[default: %default]")
    p.add_option("--vmin", dest="vmin", type="float", default=0,
            help="minimum value (used in the colormap of dots) [default: %default]")
    p.add_option("--vmax", dest="vmax", type="float", default=1,
            help="minimum value (used in the colormap of dots) [default: %default]")

    opts, args = p.parse_args()

    qbed, sbed = opts.qbed, opts.sbed
    if not (len(args) == 1 and qbed and sbed):
        sys.exit(p.print_help())

    is_self = False
    if qbed==sbed:
        print >>sys.stderr, "Looks like this is self-self comparison"
        is_self = True

    qbed = Bed(qbed)
    sbed = Bed(sbed)
    synteny = opts.synteny
    vmin, vmax = opts.vmin, opts.vmax
    cmap_text = opts.cmap_text

    anchorfile = args[0]

    image_name = op.splitext(anchorfile)[0] + "." + opts.format
    dotplot(anchorfile, qbed, sbed, image_name, vmin, vmax, 
            is_self=is_self, synteny=synteny, cmap_text=cmap_text)

