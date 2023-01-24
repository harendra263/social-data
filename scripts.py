import queries
import pandas as pd
import geopandas as gpd
from sqlalchemy import create_engine
import psycopg2
import credentials


def init_engine():
    return create_engine(
        f'postgresql://{credentials.DB_USER}:{credentials.DB_PASSWORD}@{credentials.DB_HOST}:{credentials.DB_PORT}/{credentials.DB_NAME}'
    )


def fix_chmura_counties():
    counties = queries.all_counties_query()
    counties.set_index(['State', 'County Name'], inplace=True)
    ch_df = queries.generic_select_query('chmura_economic_vulnerability_index',
                                         ['fips', 'name', 'VulnerabilityIndex', 'Rank', 'state', 'county_id'])
    for i, row in ch_df.iterrows():
        if pd.isnull(row['county_id']):
            try:
                ch_df.at[i, 'county_id'] = counties.loc[row['state'], row['name']]['county_id']
            except KeyError:
                print(row['state'], row['name'])

    queries.write_table(ch_df, 'chmura_economic_vulnerability_index')


def populate_table(path: str, name: str):
    engine = init_engine()
    df = pd.read_csv(path)
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

    # df.drop(['OBJECTID'], inplace=True, axis=1)
    # df.replace('N', None, inplace=True)
    print(df.columns)

    df.to_sql(name, engine, if_exists='replace', method='multi', index=False)
    print('write complete')


def import_geojson():
    df = gpd.read_file('temp/NTM_shapes.json')
    # df['geometry'].apply(lambda x: print(type(x)))
    df.to_csv('temp/NTM_shapes.csv')
    # df.to_sql('ntm_shapes', engine, if_exists='replace', method='multi', index=False)


FRED_TABLES = [
    # 'burdened_households',
    # 'homeownership_rate',
    # 'income_inequality',
    # 'population_below_poverty',
    # 'resident_population',
    # 'single_parent_households',
    # 'snap_benefits_recipients',
    # 'unemployment_rate',
    'fair_market_rents',
    'median_rents'
]


def update_FRED():
    engine = init_engine()
    ch_df = queries.read_table('chmura_economic_vulnerability_index')
    keep_cols = {
        'date',
        'value',
        'fips',
        'state_name',
        'county_name',
        'rent50_0',
        'rent50_1',
        'rent50_2',
        'rent50_3',
        'rent50_4',
        'hu2017',
        'fmr_0',
        'fmr_1',
        'fmr_2',
        'fmr_3',
        'fmr_4',
        'pop2017',
        'fmr_pct_chg',
        'fmr_dollar_chg',
    }
    big_df = pd.DataFrame()
    frames = []
    for table in FRED_TABLES:
        df = queries.read_table(table)
        df = df.merge(ch_df, on='county_id')
        print(df.columns)
        drop_cols = list(set(df.columns) - keep_cols)
        df.drop(drop_cols, axis=1, inplace=True)
        df.replace('.', None, inplace=True)
        df.rename({"value": table, 'fips': 'county_id'}, axis=1, inplace=True)
        # df.to_csv('temp/temp.csv')
        df.to_sql(f"{table}_new", engine, if_exists='replace', method='multi', index=False)
        print(df.head())


def map_ntm():
    conn = queries.init_connection()
    query = """
    SELECT a.route_type_text, a.route_long_name, a.route_desc,a.length, a.geom, b.tract_id
    FROM ntm_shapes a, census_tracts_geom b, id_index c
    WHERE ST_Intersects(a.geom, b.geom);
    """
    #     query="""
    # SELECT a.stop_name, a.stop_lat, a.stop_lon, a.wheelchair_boarding,a.direction, a.geom, b.tract_id
    # FROM ntm_stops a, census_tracts_geom b
    # WHERE ST_CoveredBy(a.geom, b.geom);
    #     """

    # df = pd.read_sql(query, con=conn)
    # df.to_csv('temp/new_ntm_shapes.csv')
    df=pd.read_csv('temp/new_ntm_shapes.csv',low_memory=False)
    # df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    print(df.shape)
    print(df.dtypes)
    print(df.describe())

    # df.drop(['OBJECTID'], inplace=True, axis=1)
    # df.replace('N', None, inplace=True)
    engine = init_engine()
    df.to_sql('ntm_shapes_new', engine, if_exists='replace', method='multi', index=False)
    print('write complete')

    # df=pd.read_csv('temp/new_ntm_stops.csv')
    # print(df.shape)
    # print(df.dtypes)
    # print(df.describe())


if __name__ == '__main__':
    # fix_chmura_counties()
    # import_geojson()
    # populate_table('temp/new_ntm_stops.csv', 'ntm_stops_new')
    # update_FRED()
    map_ntm()
