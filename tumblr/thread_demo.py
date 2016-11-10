import Queue
import json
import os
import sys
import threading
import urllib
import urllib2

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_FILE_DIR = ROOT_DIR + '/video'
SETTING_FILE_NAME = ROOT_DIR + '/config.json'
START_PAGE = 1
END_PAGE = 3


# @retry(urllib2.HTTPError, tries=4, delay=60, backoff=2)
def open_proxy(url):
    proxies = {'http': '127.0.0.1:8087'}
    proxy_support = urllib2.ProxyHandler(proxies)
    opener = urllib2.build_opener(proxy_support, urllib2.HTTPHandler)
    urllib2.install_opener(opener)
    a = urllib2.urlopen(url)
    return a


class Downloader(threading.Thread):
    """Threaded file downloader"""

    def __init__(self, img_queue):
        threading.Thread.__init__(self)
        self.img_queue = img_queue

    def run(self):
        while True:
            posts = self.img_queue.get()
            # download images
            for post in posts:
                for i, photo_url in enumerate(post.urls):
                    if len(post.urls) > 1:
                        base_fname = str(post.id) + '-' + str(i)  # append photo index
                    else:
                        base_fname = str(post.id)
                    print 'downloading :' + photo_url
                    try:
                        download_image(photo_url, dest, base_fname)
                    except Exception, e:
                        print e
                        post.states[photo_url] = 'failed'
                    else:
                        post.states[photo_url] = 'success'

            self.img_queue.task_done()


def get_fname_extension(ctype):
    if ctype == 'video/mp4':
        return '.mp4'
    else:
        return ''


class Config(object):
    def __init__(self):
        self.fname = SETTING_FILE_NAME
        self.consumer_key = None
        self.blogs = []

    def load(self):

        f = open(self.fname, 'r')
        sdata = f.read()
        f.close()
        data = json.loads(sdata)

        self.blogs = []
        if 'blogs' in data:
            for domain in data['blogs']:
                self.blogs.append(domain)

        if 'api' in data:
            if 'consumer_key' in data['api']:
                self.consumer_key = data['api']['consumer_key']

        return True


class SimpleTumblr(object):
    API_BASE_URL = 'http://api.tumblr.com/v2/'

    def __init__(self, consumer_key):
        self._consumer_key = consumer_key

    def api_query(self, url):
        sc = open_proxy(url)
        data = sc.read()
        sc.close()
        obj = json.loads(data)
        return obj

    def api_blog(self, host_name, method, params={}):
        url = self.API_BASE_URL + 'blog/' + host_name + '/' + method
        params['api_key'] = self._consumer_key
        param_encoded = urllib.urlencode(params)
        url = url + '?' + param_encoded
        return self.api_query(url)

    def api_blog_posts(self, host_name, posttype=None, params={}):
        method = 'posts' + ('/' + posttype if posttype else '')
        return self.api_blog(host_name, method, params)


class DownloadPost(object):
    def __init__(self):
        pass

    @staticmethod
    def create_from_apidata(postdata):
        post = DownloadPost()
        post.id = postdata['id']
        post.urls = [postdata['video_url']]
        post.states = dict.fromkeys(post.urls, 'not yet')
        return post


def download_image(src, dest_dir, base_fname):
    response = open_proxy(src)
    CHUNK = 16 * 1024
    ctype = response.info().get('content-type')
    if ctype:
        ext = get_fname_extension(ctype)
    else:
        head, ext = os.path.splitext(src)
    dest = dest_dir + '/' + base_fname + ext
    with open(dest, 'wb') as f:
        while True:
            chunk = response.read(CHUNK)
            if not chunk:
                response.close()
                break
            f.write(chunk)


if __name__ == '__main__':
    assert (START_PAGE <= END_PAGE), "START_PAGE must be less or equal to END_PAGE!"
    print '{:<20}'.format('Start Page:'), START_PAGE
    print '{:<20}'.format('End Page:'), END_PAGE
    print 'loading config'
    config = Config()
    config.load()
    consumer_key = config.consumer_key
    tumblr = SimpleTumblr(consumer_key)
    blogs = config.blogs
    img_queue = Queue.Queue()
    print 'start downloading'

    for blog_domain in blogs:
        # check the dest directory
        dest = IMG_FILE_DIR + '/' + blog_domain
        try:
            if not os.path.isdir(dest):
                os.makedirs(dest)
        except OSError:
            sys.exit('failed to make the directory for saving images')

        limit = 20  # 20 is max
        # offset = 0
        offset = (START_PAGE - 1) * limit
        do_next = True
        # repeat requesting until post_id in the api results exceeds the last_id
        while (do_next):
            do_next = False
            # get url list of photo from tumblr
            posts = []
            print 'requesting to tumblr api'
            result = tumblr.api_blog_posts(blog_domain, 'video', {'limit': limit, 'offset': offset})['response'][
                'posts']
            if result:
                for postdata in result:
                    posts.append(DownloadPost.create_from_apidata(postdata))
                else:
                    # ready for getting the next page
                    offset += limit
                    if offset <= END_PAGE * limit:
                        do_next = True
            img_queue.put(posts)
            print "****posts size is: ", len(posts)

        for i in range(10):
            d_t = Downloader(img_queue)
            d_t.daemon = True
            d_t.start()

        img_queue.join()
        print '-' * 100
        print "Done."

    print 'complete downloading'
