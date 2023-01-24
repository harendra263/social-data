import pandas as pd
import api


class DataSet(object):
    data = pd.DataFrame()

    def __init__(self, dir: str, name: str, data_format: str, sheet_name: str = 'Sheet1'):
        self.directory = dir
        self.name = name
        self.data_format = data_format
        self.path = self.directory + self.name + '.' + self.data_format
        self.sheet_name = sheet_name

    def get_data(self):
        if self.data_format == 'xlsx':
            self.data = api.get_from_excel(path=self.path, sheet_name=self.sheet_name)
        elif self.data_format == 'json':
            self.data = api.get_from_json(path=self.path)
        elif self.data_format == 'csv':
            self.data = api.get_from_csv(path=self.path)

        return self.data

    @property
    def head(self):
        return print(self.data.head())

    @property
    def describe(self):
        return print(self.data.describe())

    def unique_values(self, column: str):
        return list(self.data[column].unique())

    def drop_blank_feature_values(self, feature_columns: list):
        self.data = self.data.dropna(subset=feature_columns)

        return self.data

    def drop_non_feature_columns(self, feature_columns: list) -> pd.DataFrame:
        orig_columns = set(self.data.columns)
        columns_to_drop = list(orig_columns - set(feature_columns))
        self.data = self.data.drop(columns_to_drop, axis=1)

        return self.data

    def filter_counties(self, counties: list, column_to_filter) -> pd.DataFrame:
        pattern = '|'.join(counties)
        self.data = self.data[self.data[column_to_filter].str.contains(pattern)]

        return self.data

    def save(self):
        save_file = self.directory + self.name + ' clean' + '.' + self.data_format
        if self.data_format == 'xlsx':
            self.data.to_excel(save_file)
        elif self.data_format == 'json':
            self.data.to_json(save_file)
        elif self.data_format == 'csv':
            self.data.to_csv(save_file)
