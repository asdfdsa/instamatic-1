import glob
from xcore import UnitCell
from xcore.formats import write_shelx_ins, write_focus_inp, write_superflip_inp, read_hkl, read_cif
from xcore.scattering.dt1968 import table, keys
from xcore.scattering.atomic_radii import table as radii_table
from xcore.diffraction import calc_structure_factors

from scipy.interpolate import interp1d                                       

from instamatic.processing.indexer import read_ycsv
from instamatic.processing.serialmerge import serialmerge_fns

import numpy as np
import argparse

import os, sys

__version__ = "2017-06-04"


def make_sfac_for_electrons(composition):
    sfac = {}
    for key in composition.keys():
        t = dict(zip(keys, table[key]))
        newkey = "{key:2s} {a1:7.4f} {b1:7.4f} {a2:7.4f} {b2:7.4f}         =\n        {a3:7.4f} {b3:7.4f} {a4:7.4f} {b4:7.4f} {c:7.4f} =\n".format(key=key, **t)
        newkey += "         0.0000  0.0000  0.0000 {covrad:7.4f} {wght:7.4f}".format(wght=radii_table[key][1], covrad=radii_table[key][2])
        sfac[newkey] = composition[key]
    return sfac


def kleinify_intensities(intensities, thresh_strong=0.5, thresh_weak=0.2):
    """
    Apply algorithm defined in Klein (2011) for grouping intensities as large/medium/weak
    dx.doi.org/10.1524/zkri.2012.1568
    """
    if thresh_strong > 1:
        thresh_strong = np.percentile(intensities, thresh_strong)
    else:
        thresh_strong = thresh_strong * intensities.max()

    if thresh_weak > 1:
        thresh_weak   = np.percentile(intensities, thresh_weak)
    else:
        thresh_weak = thresh_weak * intensities.max()

    sel_strong = intensities > thresh_strong
    sel_weak   = intensities < thresh_weak
    sel_medium = ~(sel_strong ^ sel_weak)

    print "N(strong/medium/weak): {} / {} / {}".format(sel_strong.sum(), sel_medium.sum(), sel_weak.sum())
    print "thresh(strong/weak): {} / {}".format(thresh_strong, thresh_weak)
    
    intensities[sel_strong] = intensities[sel_strong].mean()
    intensities[sel_medium] = intensities[sel_medium].mean()
    intensities[sel_weak]   = intensities[sel_weak].mean()

    return intensities


def match_histogram(intensities, histogram):
    """Prepare function to match histogram"""
    if isinstance(histogram, str):
        if os.path.exists(histogram):
            root, ext = os.path.splitext(histogram)
            if ext.lower() == ".cif":
                cell, atoms = read_cif(histogram, verbose=False)
                df = calc_structure_factors(cell, atoms, table="xray")
                histogram = np.array(df["amplitude"]**2)
                histogram = 9999 * histogram  / histogram.max()
            else:
                raise IOError("Unsupported format '{}' for file '{}'".format(ext, histogram))
        elif histogram in ["MFI"]:
            histogram = np.loadtxt(os.path.join(os.path.dirname(__file__), histogram+".data"))[:,5]
    
    histogram.sort()
    histogram = histogram[::-1]

    x  = np.linspace(0, 100, len(histogram))
    f = interp1d(x, histogram)

    xi = np.linspace(0, 100, len(intensities))
    yi = f(xi)

    return yi
    

def prepare_shelx(inp, score_threshold=100, table="electron", kleinify=False, histogram=False, drc=".", focus=False, superflip=False):
    """Simple function to prepare input files for shelx
    Reads the cell/experimental parameters from the input file"""

    if not os.path.exists(drc):
        os.mkdir(drc)

    fout_template = os.path.join(drc, "{phase}.{ext}")
    klein_params = 90, 60

    df, d = read_ycsv(inp)

    phases = {}
    if isinstance(d["cell"], (tuple, list)):
        for cell in d["cell"]:
            phases[cell["name"]] = UnitCell.from_dict(cell)
    else:
        cell = d["cell"]
        phases[cell["name"]] = UnitCell.from_dict(cell)

    drc = d["data"]["drc_out"]

    gb = df.groupby("phase")

    wavelength = d["projections"]["wavelength"]

    print "Score threshold:", score_threshold

    for phase, g in gb:
        cell = phases[phase]
        composition = cell.composition

        if score_threshold:
            fns = g[g.score > score_threshold].index
            fns = [fn.replace("h5", "hkl").replace("processed", drc) for fn in fns]
        else:
            fns = glob.glob(drc + "\\*.hkl")

        if len(fns) < 10:
            print "\nNot enough frames to merge for phase: '{}'".format(phase)
            continue
        else:
            print "\nNow merging phase: '{}' ({} frames)\n".format(phase, len(fns))
        
        fout = fout_template.format(phase=phase, ext="hkl")
        serialmerge_fns(fns, fout=fout, verbose=True)
    
        if kleinify:
            arr = np.loadtxt(fout)
            arr[:,3] = kleinify_intensities(arr[:,3], *klein_params)
            np.savetxt(fout, arr, fmt="%4d%4d%4d%8.1f%8.2f")

        if histogram:
            arr = np.loadtxt(fout)
            arr[:,3] = match_histogram(arr[:,3], histogram)
            np.savetxt(fout, arr, fmt="%4d%4d%4d%8.1f%8.2f")
            
        if table == "electron":
            composition = make_sfac_for_electrons(composition)
    
        write_shelx_ins(cell, wavelength=0.0251, composition=composition, out=fout_template.format(phase=phase, ext="ins"))

        if focus:
           foc_out = fout_template.format(phase=phase, ext="inp")
           df = read_hkl(fout)
           write_focus_inp(cell, df=df, out=foc_out)

        if superflip:
           sf_out = fout_template.format(phase=phase, ext="inflip")
           write_superflip_inp(cell, wavelength=wavelength, composition=composition, datafile=os.path.basename(fout), dataformat="intensity dummy", filename=sf_out)


def main():
    usage = """instamatic.mergeprep results.ycsv
Enter 'instamatic.mergeprep -h' to access help
    """

    description = """
Program for merging serial electron diffraction data and preparing input files for shelx

""" 
    
    epilog = 'Updated: {}'.format(__version__)
    
    parser = argparse.ArgumentParser(usage=usage,
                                    description=description,
                                    epilog=epilog, 
                                    formatter_class=argparse.RawDescriptionHelpFormatter,
                                    version=__version__)
    
    parser.add_argument("args", 
                        type=str, metavar="FILE",
                        help="Path to results file (results.ycsv)")

    parser.add_argument("-t", "--threshold", metavar='T',
                        action="store", type=float, dest="score_threshold",
                        help="Minimum value for the score.")

    parser.add_argument("-e", "--electron",
                        action="store_true", dest="electron_sfac",
                        help="Print electron scattering factors to shelx input file.")

    parser.add_argument("-k", "--kleinify",
                        action="store_true", dest="kleinify",
                        help="Kleinify reflection intensities, i.e. rank them as strong/medium/weak.")

    parser.add_argument("-d", "--destination", metavar='drc',
                        action="store", type=str, dest="destination",
                        help="Directory to save output to.")

    parser.add_argument("-m", "--histogram", metavar='ftc',
                        action="store", type=str, dest="histogram",
                        help="Match intensities to histogram")

    parser.add_argument("-f", "--focus",
                        action="store_true", dest="focus",
                        help="Additionally prepare a FOCUS input file.")

    parser.add_argument("-s", "--superflip",
                        action="store_true", dest="superflip",
                        help="Additionally prepare a SUPERFLIP input file.")


    parser.set_defaults(score_threshold=100,
                        electron_sfac=False,
                        kleinify=False,
                        destination=".",
                        histogram=None,
                        focus=False,
                        superflip=False
                        )
    
    options = parser.parse_args()
    arg = options.args

    if not arg:
        parser.print_help()
        sys.exit()

    table = "electron" if options.electron_sfac else None

    prepare_shelx(arg,
                    score_threshold=options.score_threshold,
                    table=table,
                    kleinify=options.kleinify,
                    drc=options.destination,
                    histogram=options.histogram,
                    focus=options.focus,
                    superflip=options.superflip
                    )


if __name__ == '__main__':
    main()
