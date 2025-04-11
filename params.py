import itertools
import subprocess
import re
import os

template_file = "luke_opti.py"
temp_strategy_file = "_temp_strategy.py"

param_grid = {
    "POSITION_LIMIT": [25, 50],
    "MAX_VOLUME": [10, 25, 40],
    "MIN_SPREAD": [0.5, 1.0, 1.5],
    "SKEW_FACTOR": [0.5, 1.0, 2.0],
    "MOMENTUM_STRENGTH": [0.0, 0.25, 0.5],
    "MOMENTUM_WINDOW": [5, 10],
    "FALLBACK_SPREAD": [2, 4],
    "DEFAULT_MIDPRICE": [10],
}

param_combinations = list(itertools.product(*param_grid.values()))
results = []

for i, values in enumerate(param_combinations):
    params = dict(zip(param_grid.keys(), values))

    with open(template_file, "r") as f:
        code = f.read()
    for key, val in params.items():
        code = code.replace(f"{{{{{key}}}}}", str(val))

    with open(temp_strategy_file, "w") as f:
        f.write(code)

    print(f"🔧 Running config {i+1}/{len(param_combinations)}: {params}")
    try:
        output = subprocess.check_output(
            ["python", "-m", "prosperity3bt", temp_strategy_file, "1-0"],
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )

        # Extract individual product PnLs
        kelp_match = re.search(r"KELP:\s*([\d\-]+)", output)
        resin_match = re.search(r"RAINFOREST_RESIN:\s*([\d\-]+)", output)
        ink_match = re.search(r"SQUID_INK:\s*([\d\-]+)", output)
        total_match = re.search(r"Total profit:\s*([\d\-]+)", output)

        def extract_number(label: str, output: str) -> int:
            match = re.search(rf"{label}:\s*([\d,\-]+)", output)
            if match:
                return int(match.group(1).replace(",", ""))
            return 0

        kelp = extract_number("KELP", output)
        resin = extract_number("RAINFOREST_RESIN", output)
        ink = extract_number("SQUID_INK", output)
        total = extract_number("Total profit", output)

        print(f"✅ Total: {total} | KELP: {kelp} | RESIN: {resin} | INK: {ink}")   

    except subprocess.CalledProcessError as e:
        print("❌ Error running backtest:", e.output)

# Clean up
if os.path.exists(temp_strategy_file):
    os.remove(temp_strategy_file)

# Sort and display top configs
results.sort(reverse=True, key=lambda x: x[0])

print("\n🔝 Top 5 parameter sets:")
for profit, kelp, resin, ink, params in results[:5]:
    print(f"PnL: {profit} | KELP: {kelp} | RESIN: {resin} | INK: {ink} — Params: {params}")