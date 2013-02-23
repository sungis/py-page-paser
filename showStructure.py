#!/usr/bin/env python 
#coding=utf-8 

import sys
reload(sys)
sys.setdefaultencoding("utf-8")
import urllib2
import HTMLParser,os,string  
  
tagstack = []  
class ShowStructure(HTMLParser.HTMLParser):  
    def handle_starttag(self, tag, attrs): tagstack.append(tag)  
    def handle_endtag(self, tag): tagstack.pop()  
    def handle_data(self, data):  
        if data.strip(): 
           xpath='' 
           for tag in tagstack: xpath+=('/'+tag)  
           print xpath,encodeGBK(data),'\r\n===================='

def encodeGBK(s):
	return s.decode('gbk')


print sys.getdefaultencoding()
url='http://news.qq.com/newsgn/rss_newsgn.xml'
html=urllib2.urlopen(url)
s=html.read()

ShowStructure().feed(s)
