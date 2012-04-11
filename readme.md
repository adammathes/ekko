# ekko readme

## About ekko

ekko is software that downloads your data from web services, normalized it, and puts it in the a flexible document store (mongodb.)

Then you can do whatever with it! Analyze it, repurpose it, or just have it around for backup purposes.

## License

Code is copyright 2012 Adam Mathes available under a BSD style license. See LICENSE 

## Install

Dependencies: requires a modern **python** and **mongodb**

Tested with python 2.7.1, mongodb 2.0.4

Python modules: requests, pymongo

MongoDB is available at http://www.mongodb.org/downloads or use Homebrew http://mxcl.github.com/homebrew/

Install python requirements:

	# pip install requests
	# pip install pymongo


## Setup

Copy **accounts.json.example** to **accounts.json** and edit the file, replacing the relevant account info, deleting accounts you don't need.

(This process will be improved.)

## Usage

Grab all your data --

	$ python ekko.py mirror

Wait a while. Grab a sandiwch. You may want a snack.

Put the data in mongo --

	$ python ekko.py ingest

Update the data (just grabs recently posted things) --

	$ python ekko.py update

Check your data in mongodb:

	$ mongo ekko
	
	
	MongoDB shell version: 2.0.4
	connecting to: ekko
	>  db.items.count()
	6607
	

### TODO

Fortchoming (maybe)

   * command line tool to setup new accounts
   * normalize the data to an established defined vocabulary (rss, dublin core)
   * noramalized json, xml, outputs
   * download attachments (photos from relevant services)
   * more account types (instagram, pinboard)
   * web interface to search, filter the data
   * example analysis scripts