#!/bin/bash
# sweep_spp.sh — Build multiple SPP binaries with different parameters,
# run all traces, and collect results for sensitivity analysis.

set -e

PROJ_DIR="/home/veeresh/Downloads/pa2-main"
PREF_FILE="$PROJ_DIR/prefetcher/spp.l1d_pref"
PREF_BACKUP="$PROJ_DIR/prefetcher/spp.l1d_pref.backup"
TRACES_DIR="$PROJ_DIR/traces"
RESULTS_DIR="$PROJ_DIR/sweep_results"

# Traces to test
TRACES=(Trace1.gz Trace2.gz Trace3.gz)

# Binary name produced by build_champsim.sh spp lru baseline
BIN_NAME="hashed_perceptron-no-spp-no-no-no-no-no-lru-lru-lru-lru-lru-lru-lru-lru-1core-baseline"

# =============================================
# Define parameter combinations to sweep
# Format: "DEGREE_MAX HIGH_ACC LOW_ACC CONF_THRESH"
# =============================================
CONFIGS=(
    "3 70 40 2"
    "4 70 40 2"
    "5 70 40 2"
    "4 60 30 2"
    "4 80 50 2"
    "4 70 40 1"
    "4 70 40 3"
    "4 50 20 2"
)

# Backup original
cp "$PREF_FILE" "$PREF_BACKUP"
mkdir -p "$RESULTS_DIR"

echo "=== SPP Parameter Sweep ==="
echo "Building ${#CONFIGS[@]} configurations..."
echo ""

# Step 1: Build all binaries
for i in "${!CONFIGS[@]}"; do
    read -r DEG HIGH LOW CONF <<< "${CONFIGS[$i]}"
    TAG="d${DEG}_h${HIGH}_l${LOW}_c${CONF}"
    BIN_OUT="$PROJ_DIR/bin/spp_${TAG}"

    echo "[$((i+1))/${#CONFIGS[@]}] Building config: DEGREE=$DEG HIGH=$HIGH LOW=$LOW CONF=$CONF"

    # Patch the #defines in the prefetcher file
    cp "$PREF_BACKUP" "$PREF_FILE"
    sed -i "s/#define PREFETCH_DEGREE_MAX.*/#define PREFETCH_DEGREE_MAX    $DEG/" "$PREF_FILE"
    sed -i "s/#define HIGH_ACCURACY_THRESH.*/#define HIGH_ACCURACY_THRESH   $HIGH/" "$PREF_FILE"
    sed -i "s/#define LOW_ACCURACY_THRESH.*/#define LOW_ACCURACY_THRESH    $LOW/" "$PREF_FILE"
    sed -i "s/#define UNIFORM_CONF_THRESH.*/#define UNIFORM_CONF_THRESH    $CONF/" "$PREF_FILE"

    # Build
    cd "$PROJ_DIR"
    ./build_champsim.sh spp lru baseline > /dev/null 2>&1

    # Copy binary with unique name
    cp "$PROJ_DIR/bin/$BIN_NAME" "$BIN_OUT"
    echo "  -> Saved as spp_${TAG}"
done

# Restore original
cp "$PREF_BACKUP" "$PREF_FILE"
echo ""
echo "=== All binaries built. Running traces... ==="
echo ""

# Step 2: Run all configs x all traces in parallel
PIDS=()
for i in "${!CONFIGS[@]}"; do
    read -r DEG HIGH LOW CONF <<< "${CONFIGS[$i]}"
    TAG="d${DEG}_h${HIGH}_l${LOW}_c${CONF}"
    BIN_OUT="$PROJ_DIR/bin/spp_${TAG}"

    for trace in "${TRACES[@]}"; do
        TRACE_NAME="${trace%.gz}"
        OUT_FILE="$RESULTS_DIR/${TAG}_${TRACE_NAME}.txt"

        echo "  Running $TAG on $TRACE_NAME ..."
        "$BIN_OUT" -warmup_instructions 25000000 -simulation_instructions 25000000 \
            -traces "$TRACES_DIR/$trace" > "$OUT_FILE" 2>&1 &
        PIDS+=($!)
    done
done

echo ""
echo "Launched ${#PIDS[@]} simulations in parallel. Waiting..."
echo ""

# Wait for all to finish
FAIL=0
for pid in "${PIDS[@]}"; do
    wait "$pid" || FAIL=$((FAIL+1))
done

if [ $FAIL -gt 0 ]; then
    echo "WARNING: $FAIL simulation(s) failed!"
else
    echo "All simulations completed successfully!"
fi

echo ""
echo "Results are in: $RESULTS_DIR/"
echo "Run 'python3 plot_results.py' (after updating it for sweep) to analyze."
