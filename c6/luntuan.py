#!/usr/bin/env python
# coding: utf-8
 
import os, sys
import re
import urllib2
import threading
import Queue
 
host = 'http://wuniutu.com/'
base_url = 'http://wuniutu.com/thread0806.php?fid=7&page='
 
START_PAGE = 1
END_PAGE = 3
LEAST_REPLIES = 1
PAGE_PATTERN = re.compile(r'<tr.+?<h3>.+?href="(.+?)".+?>([^<.+?>].+?)<.+? f10 y-style">(\d+)<', re.DOTALL)
IMG_URL_PATTERN = re.compile(r"<img src='(.+?\.jpg|gif|png)' ")
 
class ImgThread(threading.Thread):
    """Threaded image url grabs"""
    def __init__(self, img_pattern, page_queue, img_queue):
        threading.Thread.__init__(self)
        self.img_pattern = img_pattern
        self.page_queue = page_queue
        self.img_queue = img_queue
 
    def run(self):
        while True:
            url_tuple = self.page_queue.get()
            url, title = url_tuple
            try:
                html = open_proxy(url).read()#urllib2.urlopen(url).read()
                
            except Exception, e:
                print u'**ERROR**: %s : %s\t--IGNORE--' % (url, e)
 
            img_urls = self.img_pattern.findall(html)
            if img_urls:
                self.img_queue.put((img_urls, title))
 
            self.page_queue.task_done()
 
class Downloader(threading.Thread):
    """Threaded file downloader"""
    def __init__(self, img_queue):
        threading.Thread.__init__(self)
        self.img_queue = img_queue
 
    def run(self):
        while True:
            url_tuple = self.img_queue.get()
            urls, title = url_tuple
            title = title.decode('gb2312', 'ignore')
            title = '.'.join(title.split('/'))
            try:
                os.makedirs(title)
            except OSError:
                print '**Can not create directory: %s\t--IGNORE--' % title
                self.img_queue.task_done()
                continue
            for url in urls:
                try:
                    handle = open_proxy(url)
                except Exception, e:
                    print u'**ERROR**: %s : %s\t--IGNORE--' % (url, e)
                    continue
                fname = os.path.basename(url)
                print 'Downloading %s, Saving to %s' % (url, title)
                with open('%s/%s' % (title, fname), 'wb') as f:
                    while True:
                        chunk = handle.read(1024)
                        if not chunk:
                            break
                        f.write(chunk)
 
            self.img_queue.task_done()
 
def put_page(page_queue, pattern, url):
    """Parse the given url by given pattern, put matched pages in page_queue."""
    try:
        html = open_proxy(url).read()
    except Exception, e:
        print u'**ERROR**: %s : %s\t--IGNORE--' % (url, e)
    values = pattern.findall(html)
    if values:
        # this line gets pages we want :)
        filtered = [i[:2] for i in values if int(i[2]) >= LEAST_REPLIES]
        for url, title in filtered:
            if not url.startswith('http://'):
                url = host + url
            page_queue.put((url, title))

def open_proxy(url):
    proxies={'http':'127.0.0.1:8087'}
    proxy_support=urllib2.ProxyHandler(proxies)
    opener=urllib2.build_opener(proxy_support,urllib2.HTTPHandler)
    urllib2.install_opener(opener)
    a=urllib2.urlopen(url)
    return a
def work():
    """main function."""
    assert(START_PAGE <= END_PAGE), "START_PAGE must be less or equal to END_PAGE!"
 
    print '{:<20}'.format('Start page:'), START_PAGE
    print '{:<20}'.format('End page:'), END_PAGE
    print '{:<20}'.format('Least replies:'), LEAST_REPLIES
    print '-'*100
 
    page_queue = Queue.Queue()
    img_queue = Queue.Queue()
 
    for i in range(START_PAGE, END_PAGE+1):
        url = base_url + str(i)
        put_page(page_queue, PAGE_PATTERN, url)
 
    for i in range(10):
        img_t = ImgThread(IMG_URL_PATTERN, page_queue, img_queue)
        img_t.daemon = True
        img_t.start()
 
    for i in range(10):
        d_t = Downloader(img_queue)
        d_t.daemon = True
        d_t.start()
 
    page_queue.join()
    img_queue.join()
    print '-'*100
    print "Done."
    
def delete_gap_dir():
        for root,dirs,files in os.walk(os.getcwd()):  
                if dirs == [] and files ==[]:  
                        #os.system('rd /S /Q %s' %root)
                        os.rmdir(root)

if __name__ == '__main__':
    work()
    delete_gap_dir()
