from fredapi import Fred
fred = Fred(api_key='471be0178bfc20ce10bb93e3fcceee3b')
data = fred.get_series_latest_release('DTB3')
print(data.tail())
