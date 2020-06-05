from typing import Any, Dict
import pandas as pd
import requests
import random
from kedro.extras.datasets.pandas import CSVDataSet
import yaml

user_agent_list = [
    # Chrome
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36',
    'Mozilla/5.0 (Windows NT 5.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
    # Firefox
    'Mozilla/4.0 (compatible; MSIE 9.0; Windows NT 6.1)',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0)',
    'Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (Windows NT 6.2; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.0; Trident/5.0)',
    'Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; WOW64; Trident/6.0)',
    'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; Trident/6.0)',
    'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; .NET CLR 2.0.50727; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729)'
]


def get_proxy_credentials():
    with open(r'conf/base/credentials.yml') as file:
        credentials = yaml.full_load(file)
        LUMINATI_PASS = credentials['luminati_cred']['LUMINATI_PASS']
        LUMINATI_USER = credentials['luminati_cred']['LUMINATI_USER']
        LUMINATI_HOST = credentials['luminati_cred']['LUMINATI_HOST']
        LUMINATI_PORT = credentials['luminati_cred']['LUMINATI_PORT']
    proxy = "{}:{}@{}:{}".format(LUMINATI_USER, LUMINATI_PASS, LUMINATI_HOST, LUMINATI_PORT)
    return proxy


def proxy_server():
    proxies = {
        "http": get_proxy_credentials(),
        "https": get_proxy_credentials()
    }
    return proxies


def hktvmall_conn_node(link: str) -> dict:
    r = requests.get(link)
    cook = []
    for c in r.cookies:
        cook.append("{}".format(c.name) + "=" + "{}".format(c.value))
    user_agent = random.choice(user_agent_list)
    headers = {
        'Cookie': "; ".join(cook),
        'User-Agent': user_agent,
    }
    return headers


def request_hktvmall_catagory_code(headers: dict, category_directory_url: str) \
        -> pd.DataFrame:
    from lxml import html
    from datetime import datetime
    import time

    category_directory_html = requests.get(category_directory_url).content
    tree = html.fromstring(category_directory_html)
    category_list = tree.xpath('//div[@class="directory-navbar"]/ul/a/li/@data-zone')

    all_categories = []
    for i in category_list:
        get_categories_url = "https://www.hktvmall.com/hktv/en/ajax/getCategories?categoryCode={}".format(i)
        catalog_raw = requests.request("GET", get_categories_url, headers=headers).json()
        catalog_df = pd.DataFrame(catalog_raw['categories'])
        catalog_df['tagname'] = catalog_raw['tagname']
        all_categories.append(catalog_df)

    # catalog['scrap_date'] = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d')
    # data_set = CSVDataSet(filepath="data/01_raw/hktv_mall_category.csv")
    # data_set.save(catalog)
    # reloaded = data_set.load()
    return pd.concat(all_categories, ignore_index=True, sort=False)


def request_full_site(headers: dict, catalog_df: pd.DataFrame, url: str, page_size_list: list) -> pd.DataFrame:
    for catalog in catalog_df.iterrows():
        proxies = proxy_server()
        rand_page_size = random.choice(page_size_list)
        Cat_url = url.format(catalog, str(rand_page_size), catalog)+"&currentPage={}"
        for i in range(0, int(catalog['Count'])//rand_page_size+1):
            subCat_raw = requests.request("GET", Cat_url.format(i), headers=headers, proxies=proxies).json()['products']

    pass


def gen_hktvmall_product_link(categories: dict, methods: dict, url: str) -> Dict[str, Any]:
    method1_list, method2list = [], []
    for code in categories.values():
        method1_list.append(str(url.format(code, list(methods.values())[0], code, code) + "&pageSize={}"))
        method2list.append(str(url.format(code, list(methods.values())[1], code, code) + "&pageSize={}"))

    return dict(method1=method1_list, method2=method2list)


def request_hktvmall_product_raw(headers: dict, links: list, page_size_list: list) \
        -> pd.DataFrame:
    proxies = proxy_server()
    total_df = []
    for link in links:
        url = link.format(random.choice(page_size_list))
        product_raw = requests.request("GET", url, headers=headers, proxies=proxies).json()['products']
        try:
            assert all(len(i.keys()) for i in product_raw), "HKTV Mall raw data each products' dictionary key not the same"
            total_df.append(pd.DataFrame(product_raw))
        except AssertionError:
            pass
    data = pd.concat(total_df, ignore_index=True, sort=False)

    return data


def promotion_difference_raw_to_kedro_csvdataset(df: pd.DataFrame) -> CSVDataSet:
    data_set = CSVDataSet(filepath="data/02_intermediate/PromotionDifference_raw.csv")
    data_set.save(df)
    reloaded = data_set.load()

    return reloaded


def hot_pick_order_raw_to_kedro_csvdataset(df: pd.DataFrame) -> CSVDataSet:
    data_set = CSVDataSet(filepath="data/02_intermediate/HotPickOrder_raw.csv")
    data_set.save(df)
    reloaded = data_set.load()

    return reloaded


def concat_data_sets(df_discounted: pd.DataFrame, df_top100: pd.DataFrame) -> pd.DataFrame:
    assert all(i.columns for i in [df_discounted, df_top100])

    from functools import reduce
    df = reduce(lambda x, y: pd.merge(x, y, on='code', how='inner'), [df_discounted, df_top100])

    return df


def get_product_comment(headers: dict, product_code: list, comment_url: str, page_size_list: list) -> pd.DataFrame:
    concatted__comment_raw = []
    for code in product_code:
        url = comment_url.format(code, random.choice(page_size_list))
        comment_raw = requests.request("GET", url, headers=headers).json()['reviews']
        assert all(i.keys() for i in comment_raw)
        concatted__comment_raw.append(pd.DataFrame(comment_raw))

    return pd.concat(concatted__comment_raw, ignore_index=True)


def make_scatter_plot(df: pd.DataFrame):
    import matplotlib.pyplot as plt
    fg, ax = plt.subplots()
    for idx, item in enumerate(list(df.species.unique())):
        df[df["species"] == item].plot.scatter(
            x='petal_width',
            y='petal_length',
            label=item,
            color=f"C{idx}",
            ax=ax)
    fg.set_size_inches(12, 12)

    return fg


def split_data(data: pd.DataFrame, example_test_data_ratio: float) -> Dict[str, Any]:
    """Node for splitting the classical Iris data set into training and test
    sets, each split into features and labels.
    The split ratio parameter is taken from conf/project/parameters.yml.
    The data and the parameters will be loaded and provided to your function
    automatically when the pipeline is executed and it is time to run this node.
    """
    data.columns = [
        "sepal_length",
        "sepal_width",
        "petal_length",
        "petal_width",
        "target",
    ]
    classes = sorted(data["target"].unique())
    # One-hot encoding for the target variable
    data = pd.get_dummies(data, columns=["target"], prefix="", prefix_sep="")

    # Shuffle all the data
    data = data.sample(frac=1).reset_index(drop=True)

    # Split to training and testing data
    n = data.shape[0]
    n_test = int(n * example_test_data_ratio)
    training_data = data.iloc[n_test:, :].reset_index(drop=True)
    test_data = data.iloc[:n_test, :].reset_index(drop=True)

    # Split the data to features and labels
    train_data_x = training_data.loc[:, "sepal_length":"petal_width"]
    train_data_y = training_data[classes]
    test_data_x = test_data.loc[:, "sepal_length":"petal_width"]
    test_data_y = test_data[classes]

    # When returning many variables, it is a good practice to give them names:
    return dict(
        train_x=train_data_x,
        train_y=train_data_y,
        test_x=test_data_x,
        test_y=test_data_y,
    )
