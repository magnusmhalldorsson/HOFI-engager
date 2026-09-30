#!/bin/sh
# Refute F.cnf with CaDiCaL and check the refutation with cake_lpr on the fly: the binary LRAT
# proof goes through a named pipe, so it is never stored; its sha256 is recorded.
# usage: stream_verify.sh F.cnf LOGPREFIX [extra cadical options]
# Writes LOGPREFIX.cadical (solver output), LOGPREFIX.cake (checker output, ending with the
# formula's sha256) and LOGPREFIX.proof.sha256; prints both verdicts.
F=$1; LOG=$2; shift 2
ROOT=${TOOLS:-$(dirname "$0")/../../tools}
CADICAL=${CADICAL:-$ROOT/cadical/build/cadical}
CAKE=${CAKE:-$ROOT/cake_lpr/cake_lpr}
DIR=$(mktemp -d)
mkfifo "$DIR/solver" "$DIR/checker"
"$CAKE" "$F" "$DIR/checker" > "$LOG.cake" 2>&1 &
C=$!
tee "$DIR/checker" < "$DIR/solver" | sha256sum > "$LOG.proof.sha256" &
T=$!
"$CADICAL" --lrat=true --binary=true "$@" "$F" "$DIR/solver" > "$LOG.cadical" 2>&1
wait $T
wait $C
echo "formula sha256 $(sha256sum < "$F" | cut -c1-64)" >> "$LOG.cake"
grep -h "^s " "$LOG.cadical" "$LOG.cake"
rm -rf "$DIR"
