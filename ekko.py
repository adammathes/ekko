#!/usr/bin/python

import os
import json
import time
import datetime
from datetime import datetime
import time
import getpass

from hashlib import md5, sha1
import hmac
import random
import base64

from optparse import OptionParser

from xml.etree.ElementTree import ElementTree

import pymongo
import requests


# TODO: put all this in a config/settings
data_directory = 'data'
connection = pymongo.Connection()
db = connection.ekko
collection = db.items


# This is an abstract class describing what accounts must do
class Account:
    service = 'abstract account'
    credentials = None

    def __init__(self):
        pass

    def __init__(self, credentials):        
        self.credentials = credentials

    # the json/xml etc from the service is dumped here
    def data_directory(self):
        return os.path.join(data_directory, self.service)

    # fetch and download *all* items from this account
    def mirror_all(self):
        self.mirror()

    # fetch and download the most recent PAGE of items
    # TODO: adjust this to take a date parameter
    def mirror_recent(self):
        self.mirror(1)

    # does the actual mirroring
    def mirror(self, page_limit=None):
        pass

    # put any downloaded materials into the datastore
    def ingest(self):
        pass



class TwitterAccount(Account):
    delay = 0
    service = 'twitter'
    consumer_key = None
    consumer_secret = None
    access_token = None
    access_token_secret = None

    def __init__(self, credentials):
        self.credentials = credentials
        self.username = credentials['username']
        # self.consumer_key = credentials['consumer_key']
        # self.consumer_secret = credentials['consumer_secret']
        # self.access_token = credentials['access_token']
        # self.access_token_secret = credentials['access_token_secret']

    def mirror(self, page_limit=None):
        print 'downlading data for twitter account: %s...' % self.username
        page = 1

        # oauth unnecessary for grabbing tweets, but necessary for favorites and other things
        # TODO: use oauth when those credentials are there, grab more
        #hook = OAuthHook(self.access_token, self.access_token_secret, self.consumer_key, self.consumer_secret, header_auth=True)
        #client = requests.session(hooks={'pre_request': hook})
        client = requests.session()
        page = 1
        while True:
            print 'fetching page %i' % page
            url = 'https://api.twitter.com/1/statuses/user_timeline.json?screen_name=%s&count=200&page=%i' % (self.username, page)
            print url
            response = requests.get(url)
            # TODO: twitter is creaky and we probably need to do some RETRIES here
            # For now you usually have to run ekko.py mirror twitter a few times to grab it all
            if(response.status_code != 200):
                print 'did not get a 200 response from twitter, giving up'
                break            
            print 'saving page %i' % page
            temp_file = os.path.join(self.data_directory(), self.username + str(page) + '.json')
            write_file(temp_file, response.content)
            page = page + 1
            time.sleep(self.delay)
            if page_limit:
                if page > page_limit:
                    break
            

    def ingest(self):
        page = 1
        for json_file in os.listdir(self.data_directory()):
            try:
                f = open(json_file)
                r = f.read()                
            except:
                print "could not open %s" % json_file
                
            try:
                tweets = json.loads(r)
                self.ingest_tweets(tweets)
                page = page + 1
            except:
                print 'problem ingesting tweets: %s' % json_file


    def ingest_tweets(self, tweets):
        for tweet in tweets:
            time_struct = time.strptime(tweet['created_at'], "%a %b %d %H:%M:%S +0000 %Y") #Tue Apr 26 08:57:55 +0000 2011
            d = datetime.fromtimestamp(time.mktime(time_struct))
            
            item = {'twitter_id': tweet['id'],
                    'source': 'twitter',
                    'content': tweet['text'],
                    'url': 'https://twitter.com/#!/%s/status/%s' % (tweet['user']['screen_name'], tweet['id']),
                    'date': d,
                    'original': tweet,
                    }
            if(collection.find_one({'twitter_id': tweet['id']})):
                print 'updating tweet id %s' % tweet['id']
                collection.update({'twitter_id': tweet['id']}, item)
            else:
                print 'inserting tweet id %s' % tweet['id']
                collection.insert(item)


class DeliciousAccount(Account):
    service = 'delicious'
    credentials = None
    username = None

    def __init__(self, credentials):
        self.credentials = credentials
        self.username = credentials['username']

    def bookmarks_file(self):
        return os.path.join(self.data_directory(), self.username + '.xml')

    # TODO: grab recent/all depending on mirror_all or not
    def mirror(self, page_limit=None):
        print 'downloading delicious data for %s' % self.username
        password = getpass.getpass('please enter your delicious password:')
        if page_limit:
            depth = 'recent'
        else:
            depth = 'all'
        r = requests.get('https://api.del.icio.us/v1/posts/%s' % depth, auth=(self.username, password))
        write_file(self.bookmarks_file(), r.content)

    def ingest(self):
        try:
            tree = ElementTree()
            tree.parse(self.bookmarks_file())
            bookmarks = tree.findall('post')
            self.ingest_bookmarks(bookmarks)
        except:
            print 'there was a problem parsing the delicious bookmarks files %s' % self.bookmarks_file()
        
    def ingest_bookmarks(self, bookmarks):    
        for bookmark in bookmarks:

            time_struct = time.strptime(bookmark.attrib['time'], "%Y-%m-%dT%H:%M:%SZ") # 2012-03-31T22:14:53Z
            d = datetime.fromtimestamp(time.mktime(time_struct))
            
            item = { 'delicious_id': bookmark.attrib['href'],
                     'url': bookmark.attrib['href'],
                     'source': self.service,
                     'title': bookmark.attrib['description'],
                     'date': d,
                     'content': bookmark.attrib['extended'],
                     'tags': bookmark.attrib['tag']                     
#                     'original': bookmark, // no original since we don't have json, but i think this is everything?
                     }
            if(collection.find_one({'delicious_id': item['delicious_id']})):
                print 'updating delicious id %s' % item['delicious_id']
                collection.update({'delicious_id': item['delicious_id']}, item)
            else:
                print 'inserting delicious id %s' % item['delicious_id']
                collection.insert(item)


class FlickrAccount(Account):
    service = 'flickr'
    api_key = None
    user_id = None
    username = None
    
    def __init__(self, credentials):
        self.credentials = credentials
        self.api_key = credentials['api_key']
        self.user_id = credentials['user_id']
        self.username = credentials['username']


    def mirror(self, page_limit=None):
        print 'downloading data for flickr account %s' % self.username
        page = 1
        while True:
            print 'fetching photos page %i' % page

            url = 'http://api.flickr.com/services/rest/?method=flickr.people.getPublicPhotos&api_key=%s&user_id=%s&extras=description,date_upload,url_l,url_o&per_page=500&page=%i&format=json&nojsoncallback=1' % (self.api_key, self.user_id, page)
            response = requests.get(url)
            r = json.loads(response.content)
            try:
                if(len(r['photos']['photo']) == 0):
                    break
            except:
                break
            
            print 'saving page %i' % page
            temp_file = os.path.join(self.data_directory(), self.username + str(page) + '.json')
            write_file(temp_file, response.content)
            page = page + 1
            if page_limit:
                if page > page_limit:
                    break

    def ingest(self):
        page = 1
        for json_file in os.listdir(self.data_directory()):
            try:
                f = open(json_file)
                r = f.read()                
                j = json.loads(r)
                self.ingest_photos(j['photos']['photo'])
                page = page + 1
            except:
                print "problem ingesting %s" % json_file
                break

    def ingest_photos(self, photos):
        for photo in photos:
            time_struct = time.gmtime(float(photo['dateupload']))
            d = datetime.fromtimestamp(time.mktime(time_struct))

            item = { 'flickr_id': photo['id'],
                     'url': 'http://www.flickr.com/photos/%s/%s/' % (self.username, photo['id']),
                     'title': photo['title'],
                     'source': 'flickr',
                     'date': d,
                     'original': photo }

            if(collection.find_one({'flickr_id': photo['id']})):
                print 'updating %s' % photo['id']
                collection.update({'photo_id': photo['id']}, item)
            else:
                print 'inserting %s' % photo['id']
                collection.insert(item)


class TumblrAccount(Account):
    service = 'tumblr'
    username = None
    consumer_key = None
    consumer_secret = None
    access_token = None
    access_token_secret = None
    
    def __init__(self, credentials):       
        self.credentials = credentials
        self.blog_url = credentials['blog_url']
        self.consumer_key = credentials['consumer_key']
#        self.consumer_secret = credentials['consumer_secret']

   
    def mirror(self, page_limit=None):
        print 'mirroring tumblr'
        page = 1
        while True:
            print 'fetching tumblr page %i' % page

            client = requests.session()
            response = client.get('http://api.tumblr.com/v2/blog/%s/posts?api_key=%s&offset=%i' % (self.blog_url, self.consumer_key, 20*(page-1)))

            r = json.loads(response.content)
            if(r['meta']['status'] != 200):
                print 'did not get a 200, quitting'
                print response.status_code
                print response.headers
                print response.content
                break
            if(len(r['response']['posts']) == 0):
               break
               
            temp_file = os.path.join(self.data_directory(), self.blog_url + str(page) + '.json')
            print temp_file
            write_file(temp_file, response.content)
            page = page + 1
            if page_limit:
                if page > page_limit:
                    break
                

    def ingest(self):
        page = 1
        while True:
            json_file = os.path.join(self.data_directory(), self.blog_url + str(page) + '.json')

            try:
                print json_file
                f = open(json_file)
                r = f.read()                
            except:
                print "could not open file"
                break
            
            tumblr_posts = json.loads(r)['response']['posts']
            self.ingest_posts(tumblr_posts)
            page = page + 1


    def ingest_posts(self, tumblr_posts):
        for post in tumblr_posts:
            time_struct = time.strptime(post['date'], "%Y-%m-%d %H:%M:%S GMT") #2012-03-26 19:34:00 GMT
            d = datetime.fromtimestamp(time.mktime(time_struct))
            # this is the basic crosswalk
            item = {'tumblr_id': post['id'],
                    'source': 'tumblr',
                    'date': d,
                    'url': post['post_url'],
                    'original': post,
                    }
            if(collection.find_one({'tumblr_id': post['id']})):
                print 'updating %s' % post['post_url']
                collection.update({'tumblr_id': post['id']}, item)
            else:
                print 'inserting %s' % post['post_url']
                collection.insert(item)



class MlkshkAccount(Account):
    service = 'mlkshk'
    credentials = None

    def __init__(self, credentials):
        self.credentials = credentials
        pass

    # Because of BUGS in the MLKSHK API we can't use the nice existing
    # libraries and have to make our own requests
    # this assumes you've already stored your access tokens
    def mlk_request(self, url_fragment):
        timestamp = int(time.mktime(datetime.utcnow().timetuple()))
        nonce = md5("%s" % random.random()).hexdigest()
        normalized_string = "%s\n" % (self.credentials['access_token'])
        normalized_string += "%s\n" % (timestamp)
        normalized_string += "%s\n" % (nonce)
        normalized_string += "GET\n" #request method
        normalized_string += "mlkshk.com\n" #host
        normalized_string += "80\n" # THIS IS A BUG! port should be 443 but it's not recognizing it, so leave this at 80. 
        normalized_string += url_fragment
        normalized_string += "\n"
    
        digest = hmac.new(self.credentials['access_token_secret'].encode('ascii'), normalized_string, sha1).digest()
        signature = base64.encodestring(digest).strip() #we strip the end off because it gives us a \n at the end
        authorization_string = 'MAC token="%s", timestamp="%s", nonce="%s", signature="%s"' % (self.credentials['access_token'], str(timestamp), nonce, signature)

        url = 'https://mlkshk.com' + url_fragment
        r = requests.get(url,  headers={ 'Authorization' : authorization_string })
        return r
    
    def mirror(self, page_limit=None):
        print 'page limit', page_limit
        print 'mirroring mlkshk'
        page = 1
        pivot_id = None
        while True:
            print 'fetching mlkshk page %i' % page
            
            if pivot_id:
                response = self.mlk_request('/api/shakes/%s/before/%s' % (self.credentials['shake_id'], pivot_id))
            else:
                response = self.mlk_request('/api/shakes/%s' % self.credentials['shake_id'])        

            if(response.status_code != 200):
                print 'did not get a 200, quitting'
                break            

            temp_file = os.path.join(self.data_directory(), str(page) + '.json')
            write_file(temp_file, response.content)
            images = json.loads(response.content)['sharedfiles']
            if len(images) == 0:
                print 'no more images'
                break
            
            pivot_id = images[len(images)-1]['pivot_id']
            page = page + 1
            if page_limit:
                if page>page_limit:
                    break
            

    def ingest(self):
        page = 1
        for json_file in os.listdir(self.data_directory()):
            try:
                f = open(json_file)
                r = f.read()                
            except:
                print "could not open file"
                break
            
            images = json.loads(r)['sharedfiles']
            self.ingest_images(images)
            page = page + 1

    def ingest_images(self, images):
        for image in images:
            
            time_struct = time.strptime(image['posted_at'], "%Y-%m-%dT%H:%M:%SZ") #2010-12-18T23:24:31Z
            d = datetime.fromtimestamp(time.mktime(time_struct))
            
            item = {'mlkshk_id': image['sharekey'],
                    'source': 'mlkshk',
                    'title': image['title'],
                    'description': image['description'],
                    'url': image['permalink_page'],
                    'date': d,
                    'original': image,
                    }
            if(collection.find_one({'mlkshk_id': image['sharekey']})):
                print 'updating %s' % image['sharekey']
                collection.update({'mlkshk_id': image['sharekey']}, item)
            else:
                print 'inserting %s' % image['sharekey']
                collection.insert(item)




# reads in from a json archive
class ReaderAccount(Account):
    source = 'reader'
    credentials = None
    json_archive_url = None
    json_archive_file = None
    
    def __init__(self, credentials):
        self.credentials = credentials
        self.json_archive_file = credentials['archive_file']

    def mirror_all(self):
        # download?
        pass

    def ingest(self):
        try:
           f = open(self.json_archive_file)
           r = f.read()                
           posts = json.loads(r)['items']
           self.ingest_posts(posts)
        except:
            print 'could not open archive file'

    def ingest_posts(self, posts):
        for post in posts:
            # crosswalk
            time_struct = time.gmtime(post['updated'])
            d = datetime.fromtimestamp(time.mktime(time_struct))

            item = {
                'original': post,
                'source': self.source,
                'date': d
                }
            try:
                item['title'] = post['title']
            except:
                pass

            try:
                item['url'] = post['alternate'][0]['href']
                if(collection.find_one({'url': item['url']})):
                    print 'updating %s' % item['title']
                    collection.update({'url': item['url']}, item)
                else:
                    print 'inserting %s' % item['url']
                    collection.insert(item)
            except:
                pass

# reads in from a json archive
# TODO: use a more standard format? RSS/XML? RSS in JSON?
# OR just do a JSONBlog/RSSBlog account?
class BlogAccount(Account):
    credentials = None
    archive_url = None
    recent_url = None
    source = 'blog'
    service = 'blog'
    
    def __init__(self, credentials):
        self.credentials = credentials
        self.archive_url = credentials['archive_url']
        self.recent_url = credentials['recent_url']
        self.source = credentials['source_name']


    def mirror(self, page_limit=None):
        print 'mirroring %s' % self.source
        if page_limit:
            print 'fetching %s' % self.recent_url
            response = requests.get(self.recent_url)
            temp_file = self.recent_file()
        else:
            print 'fetching %s' % self.archive_url
            response = requests.get(self.archive_url)
            temp_file = self.archive_file()
        write_file(temp_file, response.content)


    def archive_file(self):
        return os.path.join(self.data_directory(), 'archive.json')

    def recent_file(self):
        return os.path.join(self.data_directory(), 'recent.json')


    def ingest(self):
        print self.data_directory()
        for file_name in os.listdir(self.data_directory()):
           f = open(os.path.join(self.data_directory(), file_name))
           r = f.read()                
           posts = json.loads(r)
           self.ingest_posts(posts)

    def ingest_posts(self, posts):
        for post in posts:
            # crosswalk
            time_struct = time.strptime(post['date'], "%Y-%m-%d") # 2011-05-03
            d = datetime.fromtimestamp(time.mktime(time_struct))
            item = {
                'title': post['title'],
                'url': post['url'],
                'date': d,
                'content': post['content'],
                'original': post,
                'source': self.source,
                }
            if(collection.find_one({'url': post['url']})):
                print 'updating %s' % post['title']
                collection.update({'url': post['url']}, item)
            else:
                print 'inserting %s' % post['title']
                collection.insert(item)


def write_file(outfile, output):
    try:
        outdir = os.path.dirname(outfile)
        if not os.path.exists(outdir):
            os.makedirs(outdir)

        f = open(outfile, 'w')
        f.write(output) #.encode('utf-8', 'ignore'))
        f.close()
    except IOError:
        print 'NO!!! could not write to %s' % outfile






accounts = []
def read_accounts():
    accounts_file_name = 'accounts.json'
    f = open(accounts_file_name)
    accounts_json = json.loads(f.read())
    for a in accounts_json:
        service_class_name = a['service'].title() + 'Account'
        service_class = eval(service_class_name)
        account = service_class(a)
        accounts.append(account)

def main():

    read_accounts()

    usage ='ekko.py [mirror|update|ingest|print]'
    parser = OptionParser(usage)
    (options, args) = parser.parse_args()

    command = None
    try:
        command = args[0]
    except:
        print usage
              
    if command == 'mirror':
        if(len(args) > 1):
            service = args[1]
            for a in accounts:
                if a.service == service:
                    a.mirror_all()
        else:
            for account in accounts:
                account.mirror_all()

    if command == 'ingest':
        for account in accounts:
            account.ingest()

    if command == 'update':
        for account in accounts:
            account.mirror_recent()

if __name__ == "__main__":
    main()

