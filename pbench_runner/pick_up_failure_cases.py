#!/usr/bin/env python3

# Description:
#   This script is used to pick up the failure cases.
#
# Maintainers:
#   Charles Shih <schrht@gmail.com>
#

"""pick failure cases.

This script is used to pick up the failure cases.
It analyse the benchmark report generated by perf-insight, filter out the 
failure cases, restore their parameters, and dump them into a backlog file.
"""

import argparse
import logging
import toml
import json
import os

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

ARG_PARSER = argparse.ArgumentParser(
    description="Pick up the failure cases from benchmark report.")

ARG_PARSER.add_argument(
    '--report-id',
    dest='report_id',
    action='store',
    help='The Benchmark Report ID generated by perf-insight.',
    default=None,
    required=True)
ARG_PARSER.add_argument(
    '--backlog-file',
    dest='backlog_file',
    action='store',
    help='The backlog file to store the failure cases.',
    default='backlog.toml',
    required=False)


if __name__ == '__main__':

    # Parse parameters
    ARGS = ARG_PARSER.parse_args()

    report_id = ARGS.report_id
    backlog_file = ARGS.backlog_file

    # Get the statistics from the benchmark report
    LOG.info('Getting the statistics from the benchmark report...')

    cmd = 'picli --output-format json benchmark-inspect \
        --get-statistics true --report-id {}'.format(report_id)

    try:
        with os.popen(cmd) as p:
            _output = p.readlines()
            benchmark = json.loads(''.join(_output))
    except Exception as err:
        LOG.error(
            'Failed to inspect the specified benchmark report: {}'.format(err))
        exit(1)

    statistics = benchmark.get('statistics')
    if statistics is None:
        LOG.error('This benchmark report does not enable statistics function.')
        exit(1)

    testcases = statistics.get('benchmark', {})

    LOG.info('Got {} testcase(s).'.format(len(testcases)))

    # Filter failure cases
    LOG.info('Filtering failure cases...')

    failed_cases = [x for x in testcases if x.get(
        'Conclusion') == 'Dramatic Regression']

    LOG.info('Got {} failure case(s).'.format(len(failed_cases)))

    # Restore test parameters
    LOG.info('Restoring test parameters...')

    failed_cases_args = []
    for case in failed_cases:
        if 'RW' in case:
            # pbench-fio parameters
            args = {
                'CASE_ID':  case.get('CaseID'),
                'test-types': case.get('RW'),
                'block-sizes': case.get('BS'),
                'iodepth': case.get('IOdepth'),
                'numjobs': case.get('Numjobs')
            }
        elif '' in case:
            # pbench-uperf parameters
            # TODO: implement it
            args = {}
        else:
            LOG.error('Unrecognized TestRun Type.')
            exit(1)

        LOG.debug(args)
        failed_cases_args.append(args)

    LOG.info('Restored {} failure case(s).'.format(len(failed_cases_args)))

    # Write to the backlog file
    LOG.info('Writing to the backlog file...')

    try:
        with open(ARGS.backlog_file, 'w') as f:
            toml.dump({'testcases': failed_cases_args}, f)
    except Exception as err:
        LOG.error(
            'Failed to write to the backlog file: {}'.format(err))
        exit(1)

    LOG.info('Wrote {} failure case(s) to file "{}".'.format(
        len(failed_cases_args), ARGS.backlog_file))

    exit(0)