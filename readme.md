# ekko readme

## About ekko

Ekko is a thing that downloads your data from webservices and puts it in mongodb.

Then you can do whatever with it!

## Install

Dependencies: python, mongo

Tested with python 2.7.1, mongo 2.0.4

Python modules: requests, pymongo

## Setup

Copy accounts.json.example to accounts.json and edit the file, replacing the relevant account info. (This process could use some work.)

You'll need API keys for flickr

## Usage

Grab all your data --

python ekko.py mirror

Wait a while. Grab a sandiwch. You may want a snack.

Put the data in mongo --

python ekko.py ingest

Update the data (just grabs recently posted things) --

python ekko.py update