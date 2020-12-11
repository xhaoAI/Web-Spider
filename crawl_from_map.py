# -*- coding: utf-8 -*-
# @author: Kevin Zhang
# @date: 2020-11
'''
    This file help you get infomation you need from baidu map or amap by official API
    - Baidu: http://lbsyun.baidu.com/index.php?title=webapi
    - Amap: https://lbs.amap.com/api/webservice/summary

    Continuing updating.....
'''
import osmnx as ox
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import argparse
import requests
import math
import json
import time
import numpy as np
import re
import seaborn as sns
import os
import matplotlib.pyplot as plt
from logging import warning
pd.set_option('display.max_columns', None)
pd.set_option('display.max_columns', None)
plt.rcParams['font.sans-serif']=['Arial Unicode MS']
plt.rcParams['axes.unicode_minus']=False
import warnings
warnings.filterwarnings("ignore")


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--map_type', type=str, default='baidu') # amap
    parser.add_argument('--baidu_ak', type=str, default='kwMba8CpPpUVRoo1V3THXRuHzZVxSLLI')
    parser.add_argument('--amap_ak', type=str, default='a2e1307eb761e7ac6f3a87b7e95f234c')
    parser.add_argument('--location', type=tuple, default=(31.221613,121.419054)) # 爬取POI的区域
    parser.add_argument('--poi_names', type=tuple, default=('酒店','学校','美食','银行','电影院','KTV'))
    parser.add_argument('--capitals', type=tuple, default=('成都市','哈尔滨市','重庆市','长春市','北京市','天津市','石家庄市'
                                                        ,'济南市','沈阳市','上海市','呼和浩特市','南京市','杭州市','广州市',
                                                        '长沙市','昆明市','南宁市','太原市','南昌市','郑州市','兰州市',
                                                        '合肥市','武汉市','贵阳市','西宁市','乌鲁木齐市','银川市','福州市',
                                                        '海口市','拉萨市','台北市'))
    args = parser.parse_known_args()[0]
    return args

class CrawlBase(object):
    '''基类'''
    x_pi = 3.14159265358979324 * 3000.0 / 180.0
    pi = 3.1415926535897932384626
    a = 6378245.0
    ee = 0.00669342162296594323

    def __init__(self,args=get_args()):
        self.map_type=args.map_type
        self.location=args.location
        self.baidu_ak=args.baidu_ak
        self.amap_ak = args.amap_ak
        self.poi_names = args.poi_names

    @classmethod
    def _lat(cls,lng, lat):
        ret = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat + \
              0.1 * lng * lat + 0.2 * math.sqrt(math.fabs(lng))
        ret += (20.0 * math.sin(6.0 * lng * cls.pi) + 20.0 *
                math.sin(2.0 * lng * cls.pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(lat * cls.pi) + 40.0 *
                math.sin(lat / 3.0 * cls.pi)) * 2.0 / 3.0
        ret += (160.0 * math.sin(lat / 12.0 * cls.pi) + 320 *
                math.sin(lat * cls.pi / 30.0)) * 2.0 / 3.0
        return ret

    @classmethod
    def _lng(cls, lng, lat):
        ret = 300.0 + lng + 2.0 * lat + 0.1 * lng * lng + \
              0.1 * lng * lat + 0.1 * math.sqrt(math.fabs(lng))
        ret += (20.0 * math.sin(6.0 * lng * cls.pi) + 20.0 *
                math.sin(2.0 * lng * cls.pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(lng * cls.pi) + 40.0 *
                math.sin(lng / 3.0 * cls.pi)) * 2.0 / 3.0
        ret += (150.0 * math.sin(lng / 12.0 * cls.pi) + 300.0 *
                math.sin(lng / 30.0 * cls.pi)) * 2.0 / 3.0
        return ret

    @classmethod
    def out_of_china(cls,lng, lat):
        return not (lng > 73.66 and lng < 135.05 and lat > 3.86 and lat < 53.55)

    @classmethod
    def bd09_to_gcj02(cls,bd_lon, bd_lat):
        x = bd_lon - 0.0065
        y = bd_lat - 0.006
        z = math.sqrt(x * x + y * y) - 0.00002 * math.sin(y * cls.x_pi)
        theta = math.atan2(y, x) - 0.000003 * math.cos(x * cls.x_pi)
        gg_lng = z * math.cos(theta)
        gg_lat = z * math.sin(theta)
        return [gg_lng, gg_lat]

    @classmethod
    def gcj02_to_wgs84(cls,lng, lat):
        dlat = CrawlBase._lat(lng - 105.0, lat - 35.0)
        dlng = CrawlBase._lng(lng - 105.0, lat - 35.0)
        radlat = lat / 180.0 * cls.pi
        magic = math.sin(radlat)
        magic = 1 - cls.ee * magic * magic
        sqrtmagic = math.sqrt(magic)
        dlat = (dlat * 180.0) / ((cls.a * (1 - cls.ee)) / (magic * sqrtmagic) * cls.pi)
        dlng = (dlng * 180.0) / (cls.a / sqrtmagic * math.cos(radlat) * cls.pi)
        mglat = lat + dlat
        mglng = lng + dlng
        return [lng * 2 - mglng, lat * 2 - mglat]

    @classmethod
    def bd09_to_wgs84(cls,bd_lon, bd_lat):
        lon, lat = CrawlBase.bd09_to_gcj02(bd_lon, bd_lat)
        return CrawlBase.gcj02_to_wgs84(lon, lat)

    @classmethod
    def point(cls,arr):
        return Point(arr['wgs_lng'],arr['wgs_lat'])

    def target_map(self,target_poi):
        # ditie = gpd.read_file('./成都地铁/成都地铁/成都地铁_busstops.shp')
        # route = gpd.read_file('./成都地铁/成都地铁/成都地铁_buslines.shp')
        place = gpd.GeoDataFrame([Point(self.location[1], self.location[0])])
        place.columns = ['geometry']
        G = ox.graph_from_point(center_point=(self.location[0], self.location[1]), dist=2000, network_type='drive') # dist
        G_gdf = ox.graph_to_gdfs(G)
        ###### 读爬虫数据 ######
        df=pd.read_csv(os.path.join('.',self.map_type,'POI',target_poi+'.csv'),encoding='utf-8',engine='python')
        ## 百度坐标系 纠正为 WGS1984
        for i in df.index:
            df.loc[i, 'wgs_lng'] = CrawlBase.bd09_to_wgs84(df.loc[i, 'lng'], df.loc[i, 'lat'])[0]
            df.loc[i, 'wgs_lat'] = CrawlBase.bd09_to_wgs84(df.loc[i, 'lng'], df.loc[i, 'lat'])[1]
        df['geometry'] = df.apply(CrawlBase.point, axis=1)
        df = gpd.GeoDataFrame(df)
        #############################
        base = G_gdf[1].plot(figsize=(10, 10), edgecolor='grey') # 道路
        west, east = base.get_xlim()
        south, north = base.get_ylim()
        G_gdf[0].plot(ax=base, color='blue')  # 点
        plt.scatter(df['wgs_lng'],df['wgs_lat'],s=8,c='r',label=target_poi) # cmap='Paired'
        plt.legend()
        #############################
        base = G_gdf[1].plot(figsize=(10, 10), edgecolor='blue', alpha=0.3) # 道路
        sns.kdeplot(df['wgs_lng'], df['wgs_lat'], shade=True, shade_lowest=False, cmap='Greys', n_levels=5,
                    alpha=0.8, legend=False)
        df.plot(ax=base, color='red', markersize=5)
        plt.xlim(west, east)
        plt.ylim(south, north)
        plt.title('{}POI空间分布核密度图'.format(target_poi), fontsize=20)
        plt.show()

    def get_area_poi_infos(self):
        pass

    def get_route_infos(self):
        pass

    def get_weather_infos(self):
        pass

    def get_road_infos(self):
        pass

    def get_migrat_index(self):
        pass


class CrawlBaidu(CrawlBase):
    '''
    调用百度地图web服务API爬取相关信息
    url：http://lbsyun.baidu.com/index.php?title=webapi/guide/webservice-placeapi
    '''
    def __init__(self, *args, **kwargs):
        super(CrawlBaidu, self).__init__()
        self.save_dir = './baidu/POI'

    def __getattr__(self, item):
        pass

    def get_area_poi_infos(self,*args):
        '''
        :param args: 如果不传参，默认爬取所有POI，否则只爬指定的POI
        :return:
        '''
        if args:
            names=args
        else:
            names=self.poi_names
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
        for name in names:
            print('正在获取{}信息...'.format(name))
            place_names, lats, lons, address = [], [], [], []
            for i in range(0,20):
                _url = 'http://api.map.baidu.com/place/v2/search?query={}&' \
                            'location={},{}&coord_type=1&radius=5000&' \
                       'page_size=20&page_num={}&output=json&ak={}'.format(name,self.location[0],self.location[1],i,self.baidu_ak)
                data = requests.get(_url).json()
                items = data['results']
                for item in items:
                    place_names.append(item['name'])
                    lats.append(item['location']['lat'])
                    lons.append(item['location']['lng'])
                    address.append(item['address'])
                time.sleep(2) # 休眠2s
            data = pd.DataFrame({'name': place_names, 'address': address, 'lat': lats, 'lng': lons})
            data.to_csv(os.path.join(self.save_dir,'{}.csv'.format(name)))

    def get_route_infos(self):
        pass

    def traj_revise(self,filedir):
        '''
        轨迹纠偏
          用于纠正一段或多段轨迹的漂移，通过去除噪点、绑路、补充道路形状点、抽稀等方式，还原真实轨迹
        限制：
        - 一次请求支持对2000个轨迹点（轨迹里程不超过500公里）进行批量纠偏处理
        - 针对驾车、骑行和步行不同出行模式执行对应的轨迹纠偏策略，并针对停留点漂移进行了单独识别与处理
        - 支持返回轨迹点对应的道路等级、道路限速信息，开发者可利用此信息进行报警提醒和驾驶监控分析
        '''
        _url='http://api.map.baidu.com/rectify/v1/track?point_list={}&' \
             'rectify_option={}&supplement_mode={}&extensions={}&ak={}'
        df_tra=pd.read_csv(filedir,engine='python')
        points=[]
        for line in range(len(df_tra)):
            _dict={'coord_type_input':'wgs84','loc_time':df_tra.loc[line,'time'],'latitude':df_tra.loc[line,'lat'],
                   'longitude':df_tra.loc[line,'lng']}
            points.append(_dict)
        # point_list = json.dumps(points)
        rectify_option = 'need_mapmatch:1|transport_mode:driving|denoise_grade:1|vacuate_grade:1'
        supplement_mode = 'no_supplement'
        extensions = 'road_info'
        _url = _url.format(points,rectify_option,supplement_mode,extensions,self.baidu_ak)
        data = requests.get(_url).json()
        items = data['points']
        total_dis = data['distance']
        lats,lngs,speed,directions,road_grades,road_name,car_limit_speed=[],[],[],[],[],[],[]
        for item in items:
            lats.append(item['latitude'])
            lngs.append(item['longitude'])
            speed.append(item['speed'])
            directions.append(item['direction'])
            car_limit_speed.append(item['car_limit_speed'])
            road_name.append(item['road_name'])
            road_grades.append(item['road_grade'])
        df_revised = pd.DataFrame({'lat':lats,'lng':lngs,'direction':directions,'road_name':road_name})
        df_revised.to_csv('revised_gps.csv')

    def route_plan(self,**kwargs):
        '''
        轻量级路径规划：分为驾车、骑行、步行路径规划
            输入: 起始点位置坐标
            返回值：方案距离，线路耗时，路线的过路费预估，路线的整体路况评价
        '''
        o_lat = kwargs['origin'][0]
        o_lng = kwargs['origin'][1]
        d_lat = kwargs['destination'][0]
        d_lng = kwargs['destination'][1]
        _url = 'http://api.map.baidu.com/directionlite/v1/driving?origin={},{}&' \
               'destination={},{}&ak={}'.format(o_lat,o_lng,d_lat,d_lng,self.baidu_ak) # 骑行的url
        data = requests.get(_url).json()
        items = data['result']['routes'][0]
        distance=round(items['distance']/1000,2)
        dur=round(items['duration']/3600,1)
        traffic_cond=items['traffic_condition']
        toll=items['toll']
        if traffic_cond==0:
            _traffic='无数据'
        elif traffic_cond==1:
            _traffic = '畅通'
        elif traffic_cond==2:
            _traffic = '缓行'
        elif traffic_cond==3:
            _traffic = '拥挤'
        else:
            _traffic = '严重拥堵'
        print('总里程：',distance)
        print('总时长：',dur)
        print('整体路况：',_traffic)
        print('所需费用：',toll)

    def realtime_road_status(self,road='曹安公路',city='上海市'):
        '''
        查询城市道路的实时通行状况
            输入：道路名称，城市
            返回值：交通描述，拥堵区段长度，拥堵区段平均速度，拥堵趋势
        '''
        _url='http://api.map.baidu.com/traffic/v1/road?road_name={}&city={}&ak={}'.format(road,city,self.baidu_ak)
        data = requests.get(_url).json()
        result={}
        result['description']=data['description']
        result['road_traffic']={}
        result['road_traffic']['cong_dis']=[]
        result['road_traffic']['speed']=[]
        result['road_traffic']['congestion_trend']=[]
        result['road_traffic']['status'] = []
        for part in data['road_traffic'][0]['congestion_sections']:
            result['road_traffic']['cong_dis'].append(part['congestion_distance'])
            result['road_traffic']['speed'].append(part['speed'])
            result['road_traffic']['congestion_trend'].append(part['congestion_trend'])
            result['road_traffic']['status'].append(part['status'])
        print(result)
        return result

    def get_road_info(self,loc_time=1606873469,coord_type_input='bd09ll',lat=31.247036,lng=121.42692,range=1000):
        '''
        道路路况查询
            输入：时间，经纬度，查询半径
            返回：道路基础属性，前方路口信息
        WARNING
            APP APPLICATION IS BANNED
        '''
        his=[{"height":1,
              "loc_time":loc_time,
              "coord_type_input":coord_type_input,
              "latitude":lat,
              "longitude":lng}]
        jsonstr = json.dumps(his)
        _url='http://api.map.baidu.com/api_roadinfo/v1/track?point_list={}&range={}&ak={}'.format(jsonstr,range,self.baidu_ak)

        return

class CrawlAmap(CrawlBase):
    '''
    调用高德地图web服务API爬取相关信息
    url：https://lbs.amap.com/api/webservice/guide/api/staticmaps/
    '''
    def __init__(self, *args, **kwargs):
        super(CrawlAmap, self).__init__()
        self.save_dir = './amap/POI'

    def get_area_poi_infos(self,*args):
        if args:
            names=args
        else:
            names=self.poi_names
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
        for name in names:
            print('正在获取{}信息...'.format(name))

    def get_citys_loc(self,CITYs):
        cities, lons, lats = [], [], []
        gaode_api_url = "https://restapi.amap.com/v3/geocode/geo?address={}&output=XML&key=" + self.amap_ak
        for city in CITYs:
            address = gaode_api_url.format(city)
            response = requests.get(address).text
            # 加入判断防止空白信息返回
            if re.search(r"<status>1</status>", response, re.S):
                # 提取api反馈的地理信息
                detail_info = re.findall(r"<location>(.*?)</location>", response, re.S)[0]
                lat = detail_info.split(',')[1]
                lon = detail_info.split(',')[0]
                lons.append(lon)
                lats.append(lat)
                cities.append(city)
            else:
                warning("{}位置信息未成功获取".format(city))
                return None
        data = pd.DataFrame({'city': cities, 'lons': lons, 'lats': lats})
        data.to_csv('City_locs.csv')


if __name__=='__main__':
    cb = CrawlBaidu()
    # cc.get_poi_infos('酒店','美食')
    # cb.target_map('美食')
    # cb.traj_revise('nds_gps.csv')
    #cb.route_plan(origin=(40.01116,116.339303),destination=(39.936404,116.452562))
    # cb.realtime_road_status(road='曹安公路',city='上海市')

    #######################################
    #ca=CrawlAmap()
    #ca.get_citys_loc(CITYs=['襄阳市','武汉市'])

