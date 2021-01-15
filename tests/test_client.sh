#!/bin/bash

echo
echo "************** START: test_client.sh **********************"

# Create temporary testing directory
echo "Creating temporary directory to work in."
here="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

. $here/helpers.sh

# Make sure it's installed
if which caliper >/dev/null; then
    printf "caliper is installed\n"
else
    printf "caliper is not installed\n"
    exit 1
fi

# Create temporary testing directory
tmpdir=$(mktemp -d)
output=$(mktemp ${tmpdir:-/tmp}/caliper_test.XXXXXX)
printf "Created temporary directory to work in. ${tmpdir}\n"

echo
echo "#### Testing caliper metrics"
runTest 0 $output caliper metrics
runTest 0 $output caliper metrics total

echo
echo "#### Testing caliper extract"
runTest 0 $output caliper extract --metric changedlines --outdir $tmpdir pypi:sif
runTest 0 $output caliper extract --metric functiondb --fmt zip --outdir $tmpdir pypi:sif
runTest 0 $output caliper extract --metric all --outdir $tmpdir pypi:sif

echo
echo "#### Testing caliper view"
runTest 0 $output caliper view --outdir $tmpdir $here/changedlines-pokemon-results.json
runTest 1 $output caliper view --outdir $tmpdir $here/changedlines-pokemon-results.json
runTest 0 $output caliper view --outdir $tmpdir $here/changedlines-pokemon-results.json --force

rm -rf ${tmpdir}
