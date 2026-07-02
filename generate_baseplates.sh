#!/usr/bin/env bash
# Generate STL files for every baseplate size in a range.
# Edit the ranges below to control which sizes get produced.
set -euo pipefail

SCAD="gridfinity-rebuilt-baseplate.scad"
OUTDIR="stl/baseplates"
STYLE_PLATE=0     # baseplate style (0:thin,1:weighted,2:skeletonized,3:screw together,4:screw together minimal)
STYLE_HOLE=0      # mounting hole style (0:none,1:countersink,2:counterbore)
ENABLE_MAGNET=false # set to true for 6mm x 2mm magnet holes

# Size ranges (inclusive)
XMIN=1; XMAX=5
YMIN=1; YMAX=5

OPENSCAD="${OPENSCAD:-openscad}"
mkdir -p "$OUTDIR"

for x in $(seq "$XMIN" "$XMAX"); do
  for y in $(seq "$YMIN" "$YMAX"); do
    out="$OUTDIR/baseplate_${x}x${y}.stl"
    echo ">> Generating $out"
    "$OPENSCAD" -o "$out" \
      -D "gridx=$x" -D "gridy=$y" \
      -D "style_plate=$STYLE_PLATE" -D "style_hole=$STYLE_HOLE" \
      -D "enable_magnet=$ENABLE_MAGNET" \
      "$SCAD"
  done
done

echo "Done. STL files are in $OUTDIR/"
