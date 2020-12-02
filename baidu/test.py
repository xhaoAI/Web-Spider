import pymongo
import pandas as pd
import requests
import re
from concurrent import futures
from logging import warning

class GaodeLocation(object):
    # 初始化连接到Mongo数据库
    def __init__(self, key, city):
        '''
        初始化连接到数据库
            :param key: 高德开放平台提供的KEY，需携带才能访问
            :param db: 数据库名
            :param collectin: 存放小区数据的表名
            :param loc_collection: 存放位置信息的新表名
        '''
        self.CITY = city
        self.gaode_api_url = "https://restapi.amap.com/v3/geocode/geo?address={}&output=XML&key=" + key

        self.client = pymongo.MongoClient("localhost", 27017)
        self.db = self.client["ershoufang"]
        self.collection = self.db["lianjia_solded"]
        self.loc_collection = self.db['locations']

    # 将经纬度信息存入数据库
    def to_database(self,result):
        return  self.loc_collection.insert_one(result)
    # 传入位置字符串，通过高德API获取经纬度信息
    def request_info(self,loc):
        detail_loc = CITY + loc
        parse_adress_url = self.gaode_api_url.format(detail_loc)
        response = requests.get(parse_adress_url).text
        # 加入判断防止空白信息返回
        if re.search(r"<count>1</count>", response, re.S):
            # 提取api反馈的地理信息
            detail_info = re.findall(r"_address>(.*?)</.*?<district>(.*?)</district>.*?<location>(.*?)</location>", response,re.S)[0]
            result = {
                'house_name': loc,
                'adress': detail_info[0],
                'district': detail_info[1],
                'location': detail_info[2],
                'longitude': detail_info[2].split(",")[0],
                'latitude': detail_info[2].split(",")[1]
            }
            print(result)
            self.to_database(result)
        else:
            warning("{}位置信息未成功获取".format(loc))
            return None

    def main(self):
        # 从数据库中获取源小区名
        data = pd.DataFrame(list(self.collection.find())).drop(['elevator', 'url', 'village_id'], axis='columns')
        # 小区名字段
        locs = data["village_name"]
        # 按小区名出现频率排序
        locs_num = pd.value_counts(locs, sort=True)
        # 高德开放平台一天只允许免费用户使用API接口6000次......
        available_loc_list = locs_num.index[:6000]

        with futures.ThreadPoolExecutor(max_workers=20) as excutor:
            excutor.map(self.request_info, available_loc_list)

if __name__ == '__main__':
    KEY = "a2e1307eb761e7ac6f3a87b7e95f234c"  # 你的KEY
    CITY = "成都市"    # 你的城市
    s = GaodeLocation(KEY, city=CITY)
    s.main()