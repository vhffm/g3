"""
Plot Peri- vs. Apocenter.
"""

import matplotlib as mpl; mpl.use('agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import kepler_helpers as kh
import other_helpers as oh
import io_helpers as ioh
import constants as C
import brewer2mpl as b2m
import argparse
import os
import sys
from time import gmtime, strftime
from glob import glob

# Load Colors
c3 = b2m.get_map('Dark2', 'Qualitative', 3)

# Parse Arguments
parser = argparse.ArgumentParser()
parser.add_argument("--count_in", type=int, \
                    help='Determine Output Range from This Line In Dirlist')
parser.add_argument("--tag", \
                    help="Title Tag. Defaults Current Working Dir.")
group1 = parser.add_mutually_exclusive_group(required=True)
group1.add_argument("--all", action="store_true", \
                   help="Use All Snapshots.")
group1.add_argument("--custom", type=int, nargs="+", \
                   help="Use Custom Snapshot Range.")
args = parser.parse_args()

# List of Directories.
# Format:
# run_tag_01,/path/to/director/01
# run_tag_02,/path/to/director/02
# ...
if sys.stdin.isatty():
    print "!! No Directory List (Use Stdin)."
    sys.exit()
else:
    lines = sys.stdin.read().rstrip("\n").split("\n")
    dirs = []
    run_tags = []
    for line in lines:
        dirs.append(line.split(",")[1])
        run_tags.append(line.split(",")[0])
    print "// Reading %i Directories" % len(dirs)

# Sanity Check
if args.custom:
    if not len(args.custom) == 3:
        print "!! Output set must be defined by three numbers."
        sys.exit()

# Full Set. Based On First/Count_In Directory.
if args.all:
    nsteps = []
    if args.count_in:
        idir = args.count_in - 1
    else:
        idir = 0
    globs = glob("%s/Out*.dat" % dirs[idir])
    globs = sorted(globs)
    for g in globs:
        nstep = int(g.split(".")[0].split("_")[-1])
        nsteps.append(nstep)
    print "// Scanned %s For Output Range" % dirs[idir]
    print "// Reading %i Outputs Per Directory" % len(nsteps)

# Custom Set
if args.custom:
    # Build Output Number Array (From Input)
    nsteps = \
        np.mgrid[args.custom[0]:args.custom[1]+args.custom[2]:args.custom[2]]
    print "// Using Outputs %012d:%012d:%012d (%i Total)" % \
        ( args.custom[0], args.custom[1], args.custom[2], len(nsteps) )

# Set Unset Tag
if not args.tag:
    args.tag = os.getcwd()

# Determine Run Names
# Magic: Glob all ouputs, pick first, split off path,
#        extract filename, strip snap/#, strip "Out", et voila.
# Cf. http://www.webmasterwords.com/python-split-and-join-examples
run_names = []
for idir, cdir in enumerate(dirs):
    globs = glob("%s/Out*.dat" % cdir)
    globs = sorted(globs)
    fname = globs[0].split("/")[-1]
    run_name = "_".join(fname.split("_")[:-1])[3:]
    run_names.append(run_name)

# Read Collisions
cfnames = []
for idir, cdir in enumerate(dirs):
    cfnames.append("%s/Collisions%s.dat" % (cdir, run_names[idir]))
dfcoll = ioh.read_collisions_and_stack(cfnames)

# Loop Steps
for istep, nstep in enumerate(nsteps):
    print "// (%s UTC) Processing Snapshot %012d/%012d" % \
        (strftime("%H:%M:%S", gmtime()), nstep, nsteps[-1])

    # Load
    fnames = []
    for idir, cdir in enumerate(dirs):
        fnames.append("%s/Out%s_%012d.dat" % \
                      (cdir, run_names[idir], nstep))
    df = ioh.read_output_and_stack(fnames)

    # Revert Mass Scaling
    df.mass *= C.mearth/C.msun

    # Plot
    fig, ax = plt.subplots(1,1)

    # Inner Solar System
    ax.fill_between([1.0e-1, 1.0e6], [1.0e-1, 1.0e-1], [1.7, 1.7], \
                    facecolor=c3.mpl_colors[1], alpha=0.05, lw=0.5)
    ax.fill_between([1.0e-1, 1.0e6], [1.0e-1, 1.0e-1], [1.1, 1.1], \
                    facecolor=c3.mpl_colors[1], alpha=0.05, lw=0.5)
    ax.fill_between([1.0e-1, 1.7], [1.0e-1, 1.0e-1], [1.0e2, 1.0e2], \
                    facecolor=c3.mpl_colors[1], alpha=0.05, lw=0.5)
    ax.fill_between([1.0e-1, 1.1], [1.0e-1, 1.0e-1], [1.0e2, 1.0e2], \
                    facecolor=c3.mpl_colors[1], alpha=0.05, lw=0.5)

    # Massive
    ax.scatter(df.Q[df.mass>0], df[df.mass>0].q, \
               s=(df.mass[df.mass>0]/(C.mmercury/C.msun)+30)**(2./3.), \
               c=c3.mpl_colors[1], alpha=0.8, lw=0.5)

    # Hex Density
    ax.hexbin(df[(df.mass==0.0) & (df.e>=0.0) & (df.e<1.0)].Q, \
              df[(df.mass==0.0) & (df.e>=0.0) & (df.e<1.0)].q, \
              cmap=mpl.cm.bone_r, \
              mincnt=1, \
              bins="log", \
              gridsize=256, \
              xscale="log", \
              yscale="log", \
              extent=[-1, 6, -1, 2], \
              edgecolors="grey", \
              linewidths=0.0, \
              alpha=1.0, \
              vmin=-0.5)

    # Test Particles Counts
    ax.text(0.7, 0.38, r"$N = %i$" % \
            len(df[df.mass==0.0]), \
            horizontalalignment='left', color='black', \
            transform=ax.transAxes, \
            fontsize="large")
    ax.text(0.7, 0.30, r"$N(q<1.1,i<5) = %i$" % \
            len(df[(df.mass==0.0) & \
                (df.e>=0.0) & (df.e<1.0) & \
                (df.i<5.0*C.d2r) & \
                (df.q<1.1)]), \
            horizontalalignment='left', color='black', \
            transform=ax.transAxes, \
            fontsize="large")
    ax.text(0.7, 0.22, r"$N(q<1.7,i<5) = %i$" % \
            len(df[(df.mass==0.0) & \
                (df.e>=0.0) & (df.e<1.0) & \
                (df.i<5.0*C.d2r) & \
                (df.q<1.7)]), \
            horizontalalignment='left', color='black', \
            transform=ax.transAxes, \
            fontsize="large")
    ax.text(0.7, 0.14, r"$N(q<1.7) = %i$" % \
            len(df[(df.mass==0.0) & \
                (df.e>=0.0) & (df.e<1.0) & \
                (df.q<1.7)]), \
            horizontalalignment='left', color='black', \
            transform=ax.transAxes, \
            fontsize="large")
    ax.text(0.7, 0.06, r"$N(q<1.1) = %i$" % \
            len(df[(df.mass==0.0) & \
                (df.e>=0.0) & (df.e<1.0) & \
                (df.q<1.1)]), \
            horizontalalignment='left', color='black', \
            transform=ax.transAxes, \
            fontsize="large")

    # Inner Planet Collisions
    ax.text(0.5, 0.92, r"$N_\mathrm{Impacts}(M,V,E,M) = (%i,%i,%i,%i)$" % \
            (np.sum(np.logical_and(dfcoll.time<df.iloc[0].loc["time"], np.logical_or(dfcoll.indexi==0, dfcoll.indexj==0))), \
             np.sum(np.logical_and(dfcoll.time<df.iloc[0].loc["time"], np.logical_or(dfcoll.indexi==1, dfcoll.indexj==1))), \
             np.sum(np.logical_and(dfcoll.time<df.iloc[0].loc["time"], np.logical_or(dfcoll.indexi==2, dfcoll.indexj==2))), \
             np.sum(np.logical_and(dfcoll.time<df.iloc[0].loc["time"], np.logical_or(dfcoll.indexi==3, dfcoll.indexj==3)))), \
            horizontalalignment='left', color='black', \
            transform=ax.transAxes, \
            fontsize="large")

    # Reference Circular Orbit Line
    ax.plot([0.1,1,10,100], [0.1,1,10,100], c='k', alpha=0.2, lw=0.5)

    # Style
    ax.set_xlim([1.0e-1,1.0e6])
    ax.set_ylim([1.0e-1,1.0e2])
    ax.set_xlabel("Aphelion (AU)")
    ax.set_ylabel("Perihelion (AU)")
    ax.set_xscale("log")
    ax.set_yscale("log")

    # Titles
    # ax.set_title("%s" % args.tag)
    ax.set_title("%s *** %.2e yr *** %012d steps" % \
                 (args.tag, df.head(1).time, nstep))

    # # Save Figure
    fig.savefig("qQ_%012d.png" % nstep)

    # Clean Up
    plt.close(fig)
    del df
