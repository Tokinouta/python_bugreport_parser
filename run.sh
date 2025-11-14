#!/bin/bash

source .venv/bin/activate

ids=(1 2 3 4 5)
for id in "${ids[@]}"; do
    python main.py --analyse --id $id --download --idsubdir feedback
done
