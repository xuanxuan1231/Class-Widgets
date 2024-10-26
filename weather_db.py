import datetime
import sqlite3
import json
from loguru import logger

import conf

path = 'config/data/xiaomi_weather.db'
api_config = json.load(open('config/data/weather_api.json', encoding='utf-8'))


def update_path():
    global path
    if conf.read_conf('Weather', 'api') == 'amap_weather' or conf.read_conf('Weather', 'api') == 'qq_weather':
        path = 'config/data/amap_weather.db'
    else:
        path = 'config/data/xiaomi_weather.db'


def search_by_name(search_term):
    update_path()
    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM citys WHERE name LIKE ?', ('%' + search_term + '%',))  # 模糊查询
    citys_results = cursor.fetchall()
    conn.close()
    result_list = []
    for city in citys_results:
        result_list.append(city[2])
    # 返回两个表的搜索结果
    return result_list


def search_code_by_name(search_term):
    update_path()
    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM citys WHERE name LIKE ?', ('%' + search_term + '%',))  # 模糊查询
    citys_results = cursor.fetchall()
    conn.close()

    if citys_results:
        result = citys_results[0][3]
    else:
        result = 101010100  # 默认城市代码
    # 返回两个表的搜索结果
    return result


def search_by_num(search_term):
    update_path()
    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM citys WHERE city_num LIKE ?', ('%' + search_term + '%',))  # 模糊查询
    citys_results = cursor.fetchall()

    conn.close()

    if citys_results:
        result = citys_results[0][2]
    else:
        result = '北京'  # 默认城市
    # 返回两个表的搜索结果
    return result


def get_weather_by_code(code):
    weather_status = json.load(open(f"config/data/{conf.read_conf('Weather', 'api')}_status.json", encoding="utf-8"))
    for weather in weather_status['weatherinfo']:
        if str(weather['code']) == code:
            return weather['wea']
    return '未知'


def get_weather_icon_by_code(code):
    weather_status = json.load(open(f"config/data/{conf.read_conf('Weather', 'api')}_status.json", encoding="utf-8"))
    weather_code = None
    current_time = datetime.datetime.now()
    # 遍历获取天气代码
    for weather in weather_status['weatherinfo']:
        if str(weather['code']) == code:
            original_code = weather.get('original_code')
            if original_code is not None:
                weather_code = str(weather['original_code'])
            else:
                weather_code = str(weather['code'])
            break
    if not weather_code:
        logger.error(f'未找到天气代码 {code}')
        return 'img/weather/99.svg'
    # 根据天气和时间获取天气图标
    if weather_code in ('0', '1', '3', '13'):  # 晴、多云、阵雨、阵雪
        if current_time.hour < 6 or current_time.hour >= 18:  # 如果是夜间
            return f'img/weather/{weather_code}d.svg'
    return f'img/weather/{weather_code}.svg'


def get_weather_stylesheet(code):  # 天气样式
    current_time = datetime.datetime.now()
    weather_status = json.load(open(f"config/data/{conf.read_conf('Weather', 'api')}_status.json", encoding="utf-8"))
    weather_code = '99'
    for weather in weather_status['weatherinfo']:
        if str(weather['code']) == code:
            original_code = weather.get('original_code')
            if original_code is not None:
                weather_code = str(weather['original_code'])
            else:
                weather_code = str(weather['code'])
            break
    if weather_code in ('0', '1', '3', '99', '900'):
        if 6 <= current_time.hour < 18:  # 如果是日间
            return 'spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 rgba(40, 60, 110, 255), stop:1 rgba(75, 175, 245, 255)'
    return 'spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 rgba(20, 60, 90, 255), stop:1 rgba(10, 20, 29, 255)'


def get_weather_url():
    if conf.read_conf('Weather', 'api') in api_config['weather_api_list']:
        return api_config['weather_api'][conf.read_conf('Weather', 'api')]
    else:
        return api_config['weather_api']['xiaomi_weather']


def get_weather_code_by_description(value):
    weather_status = json.load(open(f"config/data/{conf.read_conf('Weather', 'api')}_status.json", encoding="utf-8"))
    for weather in weather_status['weatherinfo']:
        if str(weather['wea']) == value:
            return str(weather['code'])
    return '99'


def get_weather_data(key='temp', weather_data=None):
    if weather_data is None:
        logger.error('weather_data is None!')
        return None
    '''
        根据key值获取weather_data中的对应值
        key值可以为：temp、icon
    '''
    # 各个天气api的可访问值
    api_parameters = api_config['weather_api_parameters'][conf.read_conf('Weather', 'api')]
    parameter = api_parameters[key].split('.')
    # 遍历获取值
    value = weather_data
    if conf.read_conf('Weather', 'api') == 'amap_weather':
        value = weather_data['lives'][0][api_parameters[key]]
    elif conf.read_conf('Weather', 'api') == 'qq_weather':
        value = str(weather_data['result']['realtime'][0]['infos'][api_parameters[key]])
    else:
        for parameter in parameter:
            if parameter in value:
                value = value[parameter]
            else:
                logger.error(f'获取天气参数失败，{parameter}不存在于{conf.read_conf("Weather", "api")}中')
                return '错误'
    if key == 'temp':
        value += '°C'
    elif conf.read_conf('Weather', 'api') == 'amap_weather' or conf.read_conf('Weather', 'api') == 'qq_weather' and key == 'icon':  # 修复此代码影响其他天气源的问题
        value = get_weather_code_by_description(value)
    return value


if __name__ == '__main__':
    # 测试代码
    try:
        num_results = search_by_num('101310101')  # [2]城市名称
        print(num_results)
        citys_results = search_by_name('上海')  # [3]城市代码
        print(citys_results)
        citys_results = search_code_by_name('上海')  # [3]城市代码
        print(citys_results)
        get_weather_by_code(3)
    except Exception as e:
        print(e)
