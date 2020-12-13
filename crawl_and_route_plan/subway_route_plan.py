#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Date    : 2020-12
# @Author  : Kevin Zhang
'''
This file will help you crawl city's stations and plan route by Dijkstra algorithm
    - Amap: https://lbs.amap.com/api/webservice/summary
    - 本地宝：http://sh.bendibao.com/ditie/linemap.shtml
'''

import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import os
from tqdm import tqdm
from collections import defaultdict
import pickle
import itertools
from selenium import webdriver
from geopy.distance import geodesic

class Scrapy_and_Plan:
    '''请修改参数'''
    def __init__(self,city='上海',city_code='sh',site1='昌吉东路',site2='迪士尼'):
        self.city = city
        self.city_code= city_code
        self.keynum='a2e1307eb761e7ac6f3a87b7e95f234c' # 你的ak
        self.site1 = site1
        self.site2 = site2
        self.user_agent='Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_8; en-us) AppleWebKit/534.50 ' \
                   '(KHTML, like Gecko) Version/5.1 Safari/534.50'
        self.headers = {'User-Agent': self.user_agent}
        self.chrome=r'D:\Anaconda\Scripts\chromedriver.exe'

    def spyder_by_selenium(self):
        print('正在爬取{}地铁信息...'.format(self.city))
        url='http://{}.bendibao.com/ditie/linemap.shtml'.format(self.city_code)
        driver = webdriver.Chrome(self.chrome)
        driver.implicitly_wait(5)
        driver.get(url)
        ele_totals = driver.find_elements_by_css_selector('.s-main .line-list')
        df = pd.DataFrame(columns=['name', 'site'])
        for ele_line in tqdm(ele_totals):
            line_name = ele_line.find_element_by_css_selector('.line-list a').text.replace('线路图', '')
            # line_names = driver.find_elements_by_css_selector('div[class="wrap"]')
            stations = ele_line.find_elements_by_css_selector('a[class="link"]')
            for station in stations:
                longitude, latitude = self.get_location(station.text)
                temp = {'name': station.text, 'site': line_name, 'longitude': longitude, 'latitude': latitude}
                df = df.append(temp, ignore_index=True)
        driver.quit()
        df.to_excel('./data/{}_subway.xlsx'.format(self.city_code), index=False)

    def spyder_by_bs4(self):
        print('正在爬取{}地铁信息...'.format(self.city))
        url='http://{}.bendibao.com/ditie/linemap.shtml'.format(self.city_code)
        user_agent='Opera/9.80 (Macintosh; Intel Mac OS X 10.6.8; U; en) Presto/2.8.131 Version/11.11'
        headers = {'User-Agent': user_agent}
        r = requests.get(url, headers=headers)
        r.encoding = r.apparent_encoding
        soup = BeautifulSoup(r.text, 'lxml')
        all_info = soup.find_all('div', class_='line-list')
        df=pd.DataFrame(columns=['name','site'])
        for info in tqdm(all_info):
            title=info.find_all('div',class_='wrap')[0].get_text().split()[0].replace('线路图','')
            station_all=info.find_all('a',class_='link')
            for station in station_all:
                station_name=station.get_text()
                longitude,latitude = self.get_location(station_name)
                temp={'name':station_name,'site':title,'longitude':longitude,'latitude':latitude}
                df =df.append(temp,ignore_index=True)
        df.to_excel('./data/{}_subway.xlsx'.format(self.city_code),index=False)

    def get_location(self,keyword):
        #获得经纬度
        url='http://restapi.amap.com/v3/place/text?key='+self.keynum+'&keywords='+keyword+'&types=&city='\
            +self.city+'&children=1&offset=1&page=1&extensions=all'
        data = requests.get(url, headers=self.headers)
        data.encoding='utf-8'
        data=json.loads(data.text)
        result=data['pois'][0]['location'].split(',')
        return result[0],result[1]

    def compute_distance(self,longitude1,latitude1,longitude2,latitude2):
        #计算2点之间的距离
        url='http://restapi.amap.com/v3/distance?key='+self.keynum+'&origins='+str(longitude1)+','+str(latitude1)+'&destination='+str(longitude2)+','+str(latitude2)+'&type=1'
        data=requests.get(url,headers=self.headers)
        data.encoding='utf-8'
        data=json.loads(data.text)
        result=data['results'][0]['distance']
        return result

    def get_graph(self):
        print('正在创建pickle文件...')
        data=pd.read_excel('./data/{}_subway.xlsx'.format(self.city_code))
        #创建点之间的距离
        graph=defaultdict(dict)
        for i in range(data.shape[0]):
            site1=data.iloc[i]['site']
            if i<data.shape[0]-1:
                site2=data.iloc[i+1]['site']
                #如果是共一条线
                if site1==site2:
                    longitude1,latitude1=data.iloc[i]['longitude'],data.iloc[i]['latitude']
                    longitude2,latitude2=data.iloc[i+1]['longitude'],data.iloc[i+1]['latitude']
                    name1=data.iloc[i]['name']
                    name2=data.iloc[i+1]['name']
                    distance = self.compute_distance(longitude1,latitude1,longitude2,latitude2)
                    graph[name1][name2]=distance
                    graph[name2][name1]=distance
        output=open('./data/{}_graph.pkl'.format(self.city_code),'wb')
        pickle.dump(graph,output)

    #找到开销最小的节点
    def find_lowest_cost_node(self,costs,processed):
        #初始化数据
        lowest_cost=float('inf') #初始化最小值为无穷大
        lowest_cost_node=None
        #遍历所有节点
        for node in costs:
            #如果该节点没有被处理
            if not node in processed:
                #如果当前的节点的开销比已经存在的开销小，那么久更新该节点为最小开销的节点
                if costs[node]<lowest_cost:
                    lowest_cost=costs[node]
                    lowest_cost_node=node
        return lowest_cost_node

    #找到最短路径
    def find_shortest_path(self,start,end,parents):
        node=end
        shortest_path=[end]
        #最终的根节点为start
        while parents[node] !=start:
            shortest_path.append(parents[node])
            node=parents[node]
        shortest_path.append(start)
        return shortest_path

    #计算图中从start到end的最短路径
    def dijkstra(self,start,end,graph,costs,processed,parents):
        #查询到目前开销最小的节点
        node=self.find_lowest_cost_node(costs,processed)
        #使用找到的开销最小节点，计算它的邻居是否可以通过它进行更新
        #如果所有的节点都在processed里面 就结束
        while node is not None:
            #获取节点的cost
            cost=costs[node]  #cost 是从node 到start的距离
            #获取节点的邻居
            neighbors=graph[node]
            #遍历所有的邻居，看是否可以通过它进行更新
            for neighbor in neighbors.keys():
                #计算邻居到当前节点+当前节点的开销
                new_cost=cost+float(neighbors[neighbor])
                if neighbor not in costs or new_cost<costs[neighbor]:
                    costs[neighbor]=new_cost
                    #经过node到邻居的节点，cost最少
                    parents[neighbor]=node
            #将当前节点标记为已处理
            processed.append(node)
            #下一步继续找U中最短距离的节点  costs=U,processed=S
            node=self.find_lowest_cost_node(costs,processed)
        #循环完成 说明所有节点已经处理完
        shortest_path=self.find_shortest_path(start,end,parents)
        shortest_path.reverse()
        return shortest_path

    def subway_line(self,start,end):
        file=open('./data/{}_graph.pkl'.format(self.city_code),'rb')
        graph=pickle.load(file)
        #创建点之间的距离
        #现在我们有了各个地铁站之间的距离存储在graph
        #创建节点的开销表，cost是指从start到该节点的距离
        costs={}
        parents={}
        parents[end]=None
        for node in graph[start].keys():
            costs[node]=float(graph[start][node])
            parents[node]=start
        #终点到起始点距离为无穷大
        costs[end]=float('inf')
        #记录处理过的节点list
        processed=[]
        shortest_path=self.dijkstra(start,end,graph,costs,processed,parents)
        return shortest_path

    def get_nearest_subway(self,data,longitude1,latitude1):
        #找最近的地铁站
        longitude1=float(longitude1)
        latitude1=float(latitude1)
        distance=float('inf')
        nearest_subway=None
        for i in range(data.shape[0]):
            site1=data.iloc[i]['name']
            longitude=float(data.iloc[i]['longitude'])
            latitude=float(data.iloc[i]['latitude'])
            temp=geodesic((latitude1,longitude1), (latitude,longitude)).m
            if temp<distance:
                distance=temp
                nearest_subway=site1
        return nearest_subway


if __name__ == '__main__':
    sp=Scrapy_and_Plan(city='杭州',city_code='hz',site1='湘湖',site2='下沙江滨') # 请修改
    if not os.path.exists('./data/{}_subway.xlsx'.format(sp.city_code)):
        sp.spyder_by_selenium()
    if not os.path.exists('./data/{}_graph.pkl'.format(sp.city_code)):
        sp.get_graph()
    longitude1, latitude1 = sp.get_location(sp.site1)
    longitude2, latitude2 = sp.get_location(sp.site2)
    data = pd.read_excel('./data/{}_subway.xlsx'.format(sp.city_code))
    # 求最近的地铁站
    start = sp.get_nearest_subway(data, longitude1, latitude1)
    end = sp.get_nearest_subway(data, longitude2, latitude2)
    shortest_path = sp.subway_line(start, end)
    if sp.site1 != start:
        shortest_path.insert(0, sp.site1)
    if sp.site2 != end:
        shortest_path.append(sp.site2)
    print('路线规划为：', '-->'.join(shortest_path))