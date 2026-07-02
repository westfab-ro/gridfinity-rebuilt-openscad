#!/usr/bin/env bash
# Generate STL files for every bin size in a range.
# Edit the ranges below to control which sizes get produced.
set -euo pipefail

SCAD="gridfinity-rebuilt-bins.scad"
OUTDIR="stl/bins"
GRIDZ=5           # height in 7mm units (gridz)
INCLUDE_LIP=true # set to false to remove the stacking lip
SCOOP=0           # scoop weight (0 disables the scoop, 1 is regular)
STYLE_TAB=5       # tab style (0:Full,1:Auto,2:Left,3:Center,4:Right,5:None)

# Base hole options
REFINED_HOLES=false   # gridfinity-refined holes (not compatible with magnet holes)
MAGNET_HOLES=false   # holes for 6mm dia x 2mm high magnets
SCREW_HOLES=false    # holes for M3 screws
ONLY_CORNERS=false   # only cut holes at the corners to save print time

# Size ranges (inclusive)
XMIN=1; XMAX=5
YMIN=1; YMAX=5

OPENSCAD="${OPENSCAD:-openscad}"
mkdir -p "$OUTDIR"

for x in $(seq "$XMIN" "$XMAX"); do
  for y in $(seq "$YMIN" "$YMAX"); do
    out="$OUTDIR/bin_${x}x${y}x${GRIDZ}.stl"
    echo ">> Generating $out"
    "$OPENSCAD" -o "$out" \
      -D "gridx=$x" -D "gridy=$y" -D "gridz=$GRIDZ" \
      -D "include_lip=$INCLUDE_LIP" -D "scoop=$SCOOP" -D "style_tab=$STYLE_TAB" \
      -D "refined_holes=$REFINED_HOLES" -D "magnet_holes=$MAGNET_HOLES" \
      -D "screw_holes=$SCREW_HOLES" -D "only_corners=$ONLY_CORNERS" \
      "$SCAD"
  done
done

echo "Done. STL files are in $OUTDIR/"
