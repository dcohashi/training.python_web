from bs4 import BeautifulSoup
import geocoder
import json
import pathlib
import re
import requests
import operator
import argparse

INSPECTION_DOMAIN = 'http://info.kingcounty.gov'
INSPECTION_PATH = '/health/ehs/foodsafety/inspections/Results.aspx'
INSPECTION_PARAMS = {
    'Output': 'W',
    'Business_Name': '',
    'Business_Address': '',
    'Longitude': '',
    'Latitude': '',
    'City': '',
    'Zip_Code': '',
    'Inspection_Type': 'All',
    'Inspection_Start': '',
    'Inspection_End': '',
    'Inspection_Closed_Business': 'A',
    'Violation_Points': '',
    'Violation_Red_Points': '',
    'Violation_Descr': '',
    'Fuzzy_Search': 'N',
    'Sort': 'H'
}

SORTING_TYPES = {
    "avg": "Average Score",
    "total": "Total Inspections",
    "high": "High Score"}

def get_inspection_page(**kwargs):
    url = INSPECTION_DOMAIN + INSPECTION_PATH
    params = INSPECTION_PARAMS.copy()
    for key, val in kwargs.items():
        if key in INSPECTION_PARAMS:
            params[key] = val
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.text


def parse_source(html):
    parsed = BeautifulSoup(html)
    return parsed


def load_inspection_page(name):
    file_path = pathlib.Path(name)
    with file_path.open('r') as fh:
        return fh.read()


def restaurant_data_generator(html):
    id_finder = re.compile(r'PR[\d]+~')
    return html.find_all('div', id=id_finder)


def has_two_tds(elem):
    is_tr = elem.name == 'tr'
    td_children = elem.find_all('td', recursive=False)
    has_two = len(td_children) == 2
    return is_tr and has_two


def clean_data(td):
    return td.text.strip(" \n:-")


def extract_restaurant_metadata(elem):
    restaurant_data_rows = elem.find('table').find_all(
        has_two_tds, recursive=False
    )
    rdata = {}
    current_label = ''
    for data_row in restaurant_data_rows:
        key_cell, val_cell = data_row.find_all('td', recursive=False)
        new_label = clean_data(key_cell)
        current_label = new_label if new_label else current_label
        rdata.setdefault(current_label, []).append(clean_data(val_cell))
    return rdata


def is_inspection_data_row(elem):
    is_tr = elem.name == 'tr'
    if not is_tr:
        return False
    td_children = elem.find_all('td', recursive=False)
    has_four = len(td_children) == 4
    this_text = clean_data(td_children[0]).lower()
    contains_word = 'inspection' in this_text
    does_not_start = not this_text.startswith('inspection')
    return is_tr and has_four and contains_word and does_not_start


def get_score_data(elem):
    inspection_rows = elem.find_all(is_inspection_data_row)
    samples = len(inspection_rows)
    total = 0
    high_score = 0
    average = 0
    for row in inspection_rows:
        strval = clean_data(row.find_all('td')[2])
        try:
            intval = int(strval)
        except (ValueError, TypeError):
            samples -= 1
        else:
            total += intval
            high_score = intval if intval > high_score else high_score

    if samples:
        average = total/float(samples)
    data = {
        u'Average Score': average,
        u'High Score': high_score,
        u'Total Inspections': samples
    }
    return data

def add_color(inspection_data):
    '''
    Add color and symbols for high scores
    '''
    if inspection_data[u'Average Score'] > 50:
        color = 'ff0000'
    elif inspection_data[u'Average Score'] > 30:
        color = 'ffff00'
    else:
        color = '33cc33'
    if inspection_data[u'High Score'] > 80:
        size = 'large'
    else:
        size = 'medium'
    return({u'marker-color': color,
            u'marker-size': size})

    
def sorted_results(sort_type, count, reverse_flag):
    '''
    Return list of dictionaries sorted in order of average score.
    sort_type - field to sort on
    count - number of entries returned
    reverse - boolean to indicate results are returned in reverse sorted order.
    '''
    result=[]
    use_params = {
        'Inspection_Start': '2/1/2013',
        'Inspection_End': '2/1/2015',
        'Zip_Code': '98101'
    }
    # html = get_inspection_page(**use_params)
    html = load_inspection_page('inspection_page.html')
    parsed = parse_source(html)
    content_col = parsed.find("td", id="contentcol")
    data_list = restaurant_data_generator(content_col)
    for data_div in data_list[:count]:
        metadata = extract_restaurant_metadata(data_div)
        inspection_data = get_score_data(data_div)
        metadata.update(inspection_data)
      #  result.append(metadata)
        color_data = add_color(inspection_data)
        metadata.update(color_data)
        result.append(metadata)
    result.sort(key=operator.itemgetter(SORTING_TYPES[sort_type]),
            reverse=not reverse_flag)
    return(result)


def get_geojson(result):
    address = " ".join(result.get('Address', ''))
    if not address:
        return None
    geocoded = geocoder.google(address)
    geojson = geocoded.geojson
    inspection_data = {}
    use_keys = (
        'Business Name', 'Average Score', 'Total Inspections', 'High Score',
        'marker-color', 'marker-size')
    for key, val in result.items():
        if key not in use_keys:
            continue
        if isinstance(val, list):
            val = " ".join(val)
        inspection_data[key] = val
    geojson['properties'] = inspection_data
    return geojson


if __name__ == '__main__':
    # Parse the input arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--sort_type", 
            help="field to sort on", 
            choices=['avg', 'high','total'],
            default='avg'
            )
    parser.add_argument("-c", "--count", type=int,
            help="number of properties", default=20)
    parser.add_argument("-r", "--reverse", action="store_true", 
            help="display in reverse order", default=False)
    args = parser.parse_args()
    print("{}".format(args))
    total_result = {'type': 'FeatureCollection', 'features': []}
    for result in sorted_results(args.sort_type, args.count,
            args.reverse):
        geojson = get_geojson(result)
        total_result['features'].append(geojson)
    with open('my_map.json', 'w') as fh:
        json.dump(total_result, fh)
