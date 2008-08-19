#!/usr/bin/env python

'''
FaceHack 0.1
Created by Jared Forsyth
email questions/comments to jabapyth@gmail.com

example:

import facehack
fh = facehack.FaceHack("me","secret")
print "Current status: %s"%fh.status()
fh.status("Hakkin up facebook")
fh.wall_post("Jane Doe","Heya!")
fh.message(["John Doe","Joe Schmo"],"So..","Whats chillin, folks?")

print "You have %d friends"%len(fh.friends)
'''

import urllib
import cookielib, urllib2
import re
import time
import random
import math
from HTMLParser import HTMLParser

headers = {'User-agent' : 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'}

debug = False

### stuff ###

def get_page(url,data=None,xheaders=None):
    req = urllib2.Request(url, urllib.urlencode(data), xheaders or headers)
    handle = urllib2.urlopen(req)
    return handle

def get_forms(txt):
    forms = re.findall("(<form[^>]*>)(.+?)</form>",txt,re.S|re.I)
    for head,data in forms:
        yield parse_tags(head)[0][1],get_form_data(data)

def get_form_data(txt):
    res = {}
    texts = re.findall("(<textarea[^>]*>)(.*?)</textarea>",txt,re.S|re.I)
    for head,text in texts:
        attrs = parse_tags(head)[0][1]
        attrs["value"] = text
        if attrs.has_key("name"):
            res[attrs['name']] = attrs
    
    inputs = re.findall("<input[^>]*>",txt,re.S|re.I)
    for text in inputs:
        attrs = parse_tags(text)[0][1]
        if attrs.has_key("name"):
            res[attrs['name']] = attrs
    
    buttons = re.findall("(<button[^>]*>)(.*?)</button>",txt,re.S|re.I)
    for head,text in buttons:
        attrs = parse_tags(head)[0][1]
        if text and not attrs.has_key("value"):
            attrs["value"] = text
        if attrs.has_key("name"):
            res[attrs['name']] = attrs
    return res

def parse_tags(txt):
    tags = []
    class Ps(HTMLParser):
        def handle_starttag(self,tag,attrs):
            tags.append([tag,dict(attrs)])
    Ps().feed(txt)
    return tags

### accessible functions ###

class Friend_Error(Exception):
    pass


'''
FaceHack:
    __init__(self,user=None,passw=None)
        initialize, optionally login
    
    login(self,userr,passw)
        login
    
    status(self,new=None)
        if new is given, set status
        otherwise, get status
    
    wall_post(self,name_or_id,text)
    
    send_message(self,names,subject,message)
        if names is a string, just send to one person
        if its a list, send to all in the list
    

'''


class FaceHack:
    def __init__(self,user=None,passw=None):
        self.setup()
        if user and passw:
            self.login(user,passw)
    
    def get_page(self,url,data={}):
        req = urllib2.Request(url, urllib.urlencode(data), {'User-agent' : 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'})
        handle = urllib2.urlopen(req)
        return handle
    
    def setup(self):
        cj = cookielib.CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        urllib2.install_opener(opener)
    
    def login(self,email,passw):
        dct = {}
        dct["persistent"] = "1"
        dct["login"] = "Login"
        dct["charset_test"] = "%u20AC,%uFFFD,%u20AC,%uFFFD,%u6C34,%u0414,%u0404"
        dct["email"] = email
        dct["pass"] = passw
        
        self.get_page("http://facebook.com/login.php")
        self.get_page("https://login.facebook.com/login.php", dct)
        res = self.get_page("http://www.facebook.com/home.php?").read()
        self.id = re.search('<a href="http://www.facebook.com/profile.php\\?id=(\d*)" class="profile_nav_link">Profile</a>',res).groups()[0]
        self.name = self.get_name(self.id)
        self.get_friends()
        print "Welcome to FaceHack, %s"%self.name
        ## return res
        
    def wall_post(self,name,wall_text):
        id = self.get_id(name)
        url = "http://www.facebook.com/wall.php?id=%s"%id
        text = self.get_page(url).read()
        form = list(get_forms(text))[1]
        
        url = "http://www.facebook.com/wallpost.php"
        dct={}
        for key in form[1]:
            dct[key] = form[1][key]["value"]
        dct["wall_text"] = wall_text
        res = self.get_page(url, dct)
    
    def message(self,names,subject,message):
        if type(names)==str:names = [names]
        ids = [self.get_id(name) for name in names]
        url = "http://www.facebook.com/inbox/?compose="
        text = self.get_page(url).read()
        form = list(get_forms(text))[1]
        
        url = "http://www.facebook.com/inbox/"
        dct = {}
        for key in form[1]:
            dct[key] = form[1][key]["value"]
        dct["subject"] = subject
        dct["message"] = message
        dct["rand_id"] = str(int(random.random()*100000000))
        data = dct.items()
        for id in ids:
            data.append(("ids[]",id))
            
        res = self.get_page(url, data)

    def status(self,new=None):
        url = "http://www.facebook.com/home.php"
        txt = self.get_page(url).read()
        rgf = '<span id="su_text">(.+?)</span>'
        rgx = '<input id="post_form_id" type="hidden" value="(.+?)" name="post_form_id"/>'
        if new:
            pid = re.findall('id="post_form_id" name="post_form_id" value="(.+?)"',txt)[0]
            url = "http://www.facebook.com/updatestatus.php"
            dct = {"status":new,"post_form_id":pid}
            res = self.get_page(url, dct)
            txt = res.read()
            return True
        else:
            return re.findall(rgf,txt)[0]
            
    def get_id(self,id):
        if type(id)==int or id.isdigit():return str(id)
        if id in self.friends:
            return self.friend_ids[id]
        raise Friend_Error("Friend %s not found"%id)
    
    def get_friends(self):
        url = "http://www.facebook.com/friends/ajax/friends.php?id=%s"%self.id
        text = self.get_page(url).read()
        front,main = text.split(");",1)
        main = main.replace("null","None").replace("false","False").replace("true","True")
        stuff=eval(main)
        fps = stuff["payload"]["friend_pages"]
        friends = [self.name]
        friend_ids = {self.name:self.id}
        rgx = 'id=(\d*)" class="fname">(.+?)<'
        for fpage in fps:
            for id,f in re.findall(rgx,fpage):
                friends.append(f)
                friend_ids[f] = id
        self.friends = friends
        self.friend_ids = friend_ids

    def get_name(self,id):
        res = self.get_page("http://www.facebook.com/profile.php?id=%s"%id).read()
        return re.findall("<title>Facebook \\|(.*?)</title>",res,re.I|re.S)[0]

if __name__=="__main__":
    test()
