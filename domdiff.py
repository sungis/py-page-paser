#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
#=============================================================================
#     FileName: domdiff.py
#         Desc: 比较网页之间的差异 并抽取
#       Author: Sungis
#        Email: mr.sungis@gmail.com
#     HomePage: http://sungis.github.com
#      Version: 0.0.1
#   LastChange: 2013-09-13 08:58:47
#      History:
#=============================================================================
'''

import sys
reload(sys)
sys.setdefaultencoding("utf-8")
import re
import urllib2
from htmltreediff.util import *
from htmltreediff.changes import *
from treediff.dom_tree_iface import DomTreeIface
import chardet
''''' 【编辑距离算法】 【levenshtein distance】 【字符串相似度算法】 '''  
def levenshtein(first,second):  
    if len(first) > len(second):  
        first,second = second,first  
    if len(first) == 0:  
        return len(second)  
    if len(second) == 0:  
        return len(first)  
    first_length = len(first) + 1  
    second_length = len(second) + 1  
    distance_matrix = [range(second_length) for x in range(first_length)]   
    #print distance_matrix  
    for i in range(1,first_length):  
        for j in range(1,second_length):  
            deletion = distance_matrix[i-1][j] + 1  
            insertion = distance_matrix[i][j-1] + 1  
            substitution = distance_matrix[i-1][j-1]  
            if first[i-1] != second[j-1]:  
                substitution += 1  
            distance_matrix[i][j] = min(insertion,deletion,substitution)  
    #print distance_matrix  
    return distance_matrix[first_length-1][second_length-1]  

#判断页面编码
def get_encoding(page):
    text = re.sub('</?[^>]*>\s*', ' ', page)
    enc = 'utf-8'
    if not text.strip() or len(text) < 10:
        return enc # can't guess
    try:
        diff = text.decode(enc, 'ignore').encode(enc)
        sizes = len(diff), len(text)
        if abs(len(text) - len(diff)) < max(sizes) * 0.01: # 99% of utf-8
            return enc
    except UnicodeDecodeError:
        pass
    res = chardet.detect(text)
    enc = res['encoding']
    #print '->', enc, "%.2f" % res['confidence']
    if enc == 'MacCyrillic':
        enc = 'cp1251'
    if enc == 'GB2312':
        enc = 'gbk'
    return enc

#下载网页并初步过滤 style script 并抽取 title
def parse(url):
    html=urllib2.urlopen(url)
    h=html.read()
    html.close()
    enc = get_encoding(h)
    h = h.decode(enc)
    title = re.search('<title>([^,]+)</title>',h)
    if title:
        title = title.group(1)
    else:
        title = ''
    d = parse_minidom(h)
    d.setUserData('title',title,None)
    for n in list(walk_dom(d)):
        if n.nodeName in ['style','script']:remove_node(n)
    return d


#求 两节点 的公共父节点
def get_common_parent_node(a,b):
    arr1 = a.split('/')
    arr2 = b.split('/')
    for i in range(len(arr1)):
        if (arr1[i] != arr2[i]):
            return '/'.join(arr1[0:i])
    return '/'.join(arr1)
#计算 节点 xpath 直接的 距离
def xpath_dist(a,b):
    arr1 = a.split('/')[1:-1]
    arr2 = b.split('/')[1:-1]
    if len(arr2) > len(arr1):
        arr1,arr2 = arr2,arr1
    for i in range(len(arr2)):
        if (arr1[i] != arr2[i]):
            break
    return len(arr1) - i
#dom tree [t] 根据 xpath [p] 返回对应节点的值
def get_value_by_xpath(p,t):
    text = []
    n = t.get_node_by_xpath(p)
    for i in walk_dom(n):
        if is_text(i):
            text.append(t.get_value(i))
    return ''.join(text)

#求文本 t2 与 目标文本t1 的 文本距离 = d
# k = len(t1)
#相似度公式 (k-d)/k
def text_similarity(t1,t2):
    k = float(len(t1))
    if k == 0 or len(t2)/k >= 2:
        return 0
    d = levenshtein(t1,t2)
    return (k-d)/k
#遍历节点d ，当字节点 为 text_node 且节点内文本长度>0 
#则存入 xpath_dict 并返回
def dom_tree_traversal(d,t):
    xpath_dict = {}
    for n in walk_dom(d):
        if is_text(n):
            v = t.get_value(n)
            if len(v.strip())>0:
                p = t.node_repr(n)
                if xpath_dict.has_key(p):
                    xpath_dict[p] += v
                else:
                    xpath_dict[p] = v
    return xpath_dict

#求 node_block 网页块 中 链接/文本比 > 0.4 的为 噪音节点
def is_noise(t,node_block):
    ac = 0
    tc = 0
    for i in node_block:
        if re.search('/a\[\d+\]/',i[0]):
            ac += len(i[2])
        else:
            tc += len(i[2])
    score = float(ac)/(tc+ac)
    print tc,ac,score
    if score > 0.4:
        return True
    else:
        return False
    

def extract(u1,u2):
    #过滤相同模板
    #遍历d1 xpath 与 值 存入 dict
    #遍历d2 xpath 如果存在 且 值相同 ，则移除key: xpath
    #过滤噪音
    #归并Rpath 统计 节点内 a 占比
    #计算最大公路径 ，求公共节点，计算节点内 链接/文本比 >50% 则移除
    #最终抽取正文模板

    #解析页面为 dom tree
    d1 = parse(u1)
    d2 = parse(u2)
    
    t1 = DomTreeIface(d1)
    t2 = DomTreeIface(d2)
    
    #遍历页面 ，抽取 text node 的xpath 与 value 插入xpath_dict
    xpath_dict = dom_tree_traversal(d1,t1)
    xpath_dict2 = dom_tree_traversal(d2,t2)

    #初步过滤，把相同位置、相同值的节点移除
    for n in xpath_dict2.keys():
        if xpath_dict.has_key(n) and xpath_dict[n] == xpath_dict2[n]:
            del xpath_dict[n]

    #网页分块，计算节点平均距离
    gap = []
    prex = None
    distance = 0
    dist = 0
    for x in sorted(xpath_dict.keys()):
        if prex:
            dist = xpath_dist(prex,x)
            distance += dist
            gap.append((prex,dist,xpath_dict[prex]))
        prex = x
    avg_dist = float(distance)/(len(gap) - 1)
    gap.append((prex,avg_dist+2,xpath_dict[prex]))
    
    # 求出 标题 与正文 节点 并归并求出对应的抽取路径模板
    title_score = 0
    title_xpath = ''

    content_score = 0
    content_xpath = ''

    title = d1.getUserData('title')
    node_block = []
    for n in gap:
        #网页分块
        print n[0],n[1],n[2]
        if n[1] - avg_dist >= 1:
            print '***********************'
            node_block.append((n))
            #计算公共节点，判断是否为噪音节点 
            if  is_noise(t1,node_block):
                for x in node_block:
                    if xpath_dict.has_key(x[0]):
                        del xpath_dict[x[0]]
            else:
                #非 噪音节点  判断是否为 Tilte 或 Content
                #标题 为 与 网页标题 文本类似的 节点
                #正文 为 节点中文本 比例最大的 节点
                for x in node_block:
                    v = x[2]
                    score = text_similarity(title,v)
                    if score > title_score:
                        title_score = score
                        title_xpath = x[0]
                    if len(v) > content_score:
                        content_score = len(v)
                        content_xpath = x[0]
            node_block = []
        else:
            node_block.append(n)

    # 求 title 与 Content 的公共节点 ，此节点为正文区域
    # 以此正文区域节点 Xpath 来过滤 非正文区域 节点
    main_xpath = get_common_parent_node(title_xpath,content_xpath)
    print main_xpath
    print title_xpath,title_score
    print content_xpath,content_score
    print '=================================================='
    for n in gap:
        if xpath_dict.has_key(n[0]):
            print n[0],n[2]
            if n[0] == title_xpath:
                print '********Title**********'
            if n[0] == content_xpath:
                print '********Content********'
            if n[1] - avg_dist >= 1:
                print '##############################################'


if __name__ == '__main__':
    if len(sys.argv) == 3:
        u1 = sys.argv[1]
        u2 = sys.argv[2]        
        extract(u1,u2)

