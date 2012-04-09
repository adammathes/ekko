# ekko readme

## About ekko

Ekko is a thing that downloads your data from webservices and puts it in mongodb.

Then you can do whatever with it!

## Install

Dependencies: python, mongo

Python modules: requests, pymongo

## Setup

Copy accounts.json.example to accounts.json and edit the file, replacing the relevant account info.

## Usage

Grab all your data --

python ekko.py mirror

Wait a while. Grab a sandiwch. You may want a snack.

Put the data in mongo --

python ekko.py ingest

Update the data (only grab recent things) --

python ekko.py update

