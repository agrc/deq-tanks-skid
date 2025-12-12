# DEQ Tanks Salesforce Palletjack Skid

[![Push Events](https://github.com/agrc/deq-tanks-skid/actions/workflows/push.yml/badge.svg)](https://github.com/agrc/skid/actions/workflows/push.yml)
[![Pull Events](https://github.com/agrc/deq-tanks-skid/actions/workflows/pull_request.yml/badge.svg)](https://github.com/agrc/skid/actions/workflows/pull_request.yml)

This skid pulls data from the DEQ Tanks Salesforce instance and loads it into DEQ AGOL hosted feature layers [for use in the interactive map](https://github.com/agrc/deq-enviro/issues/665).

## Development Setup

1. Create new environment for the project and install Python
   - `conda create --name deq-tanks-skid python=3.13`
   - `conda activate deq-tanks-skid`
1. Install the skid in your conda environment as an editable package for development
   - This will install all the normal and development dependencies (palletjack, supervisor, etc)
   - `cd c:\path\to\repo`
   - `pip install -e .[tests]`
1. Set config variables and secrets
   - `secrets.json` holds passwords, secret keys, etc, and will not (and should not) be tracked in git
   - `config.py` holds all the other configuration variables that can be publicly exposed in git
   - Copy `secrets_template.json` to `secrets.json` and change/add whatever values are needed for your skid
   - Change/add variables in `config.py` as needed

### Testing Locally

You may test this project by running `deq-tanks-skid`.

## Publishing AGOL Items

There is a `skid.publish` method in main that can be used to publish the items for the first time. Note that this method requires `arcpy`.
