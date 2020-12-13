# -*- coding: utf-8 -*-
# @author: Kevin Zhang
# @date: 2020-11
'''
    This file will help you crawl city's stations and plan route by Dijkstra algorithm
    - Baidu: http://lbsyun.baidu.com/index.php?title=webapi
    - Amap: https://lbs.amap.com/api/webservice/summary
'''
import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import tqdm

def spyder():
    #获得武汉的地铁信息
    print('正在爬取武汉地铁信息...')
    url='http://wh.bendibao.com/ditie/linemap.shtml'
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
            longitude,latitude=get_location(station_name,'武汉')
            temp={'name':station_name,'site':title,'longitude':longitude,'latitude':latitude}
            df =df.append(temp,ignore_index=True)
    df.to_excel('./subway.xlsx',index=False)

def get_location(keyword,city):
    #获得经纬度
    user_agent='Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_8; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50'
    headers = {'User-Agent': user_agent}
    url='http://restapi.amap.com/v3/place/text?key='+keynum+'&keywords='+keyword+'&types=&city='+city+'&children=1&offset=1&page=1&extensions=all'
    data = requests.get(url, headers=headers)
    data.encoding='utf-8'
    data=json.loads(data.text)
    result=data['pois'][0]['location'].split(',')
    return result[0],result[1]

def compute_distance(longitude1,latitude1,longitude2,latitude2):
    #计算2点之间的距离
    user_agent='Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_8; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50'
    headers = {'User-Agent': user_agent}
    url='http://restapi.amap.com/v3/distance?key='+keynum+'&origins='+str(longitude1)+','+str(latitude1)+'&destination='+str(longitude2)+','+str(latitude2)+'&type=1'
    data=requests.get(url,headers=headers)
    data.encoding='utf-8'
    data=json.loads(data.text)
    result=data['results'][0]['distance']
    return result

def get_graph():
    print('正在创建pickle文件...')
    data=pd.read_excel('./subway.xlsx')
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
                distance=compute_distance(longitude1,latitude1,longitude2,latitude2)
                graph[name1][name2]=distance
                graph[name2][name1]=distance
    output=open('graph.pkl','wb')
    pickle.dump(graph,output)