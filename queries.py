import os
import sys
import psycopg2
import pandas as pd
import fiona
import geopandas as gpd
from sqlalchemy import create_engine
from shapely import wkb
import streamlit as st
from sklearn import preprocessing

import credentials
from constants import STATES

FRED_TABLES = [
    'burdened_households',
    # 'homeownership_rate',
    'income_inequality',
    'population_below_poverty',
    # 'resident_population',
    'single_parent_households',
    'snap_benefits_recipients',
    'unemployment_rate',
]

STATIC_TABLES = [
    'chmura_economic_vulnerability_index',
    'fair_market_rents'
    'median_rents',
]

STATIC_COLUMNS = {
    'chmura_economic_vulnerability_index': ['VulnerabilityIndex', 'Rank'],
    'fair_market_rents': ['fmr_0', 'fmr_1', 'fmr_2', 'fmr_3', 'fmr_4'],
    'median_rents': ['rent50_0', 'rent50_1', 'rent50_2', 'rent50_3', 'rent50_4']
}

TABLE_HEADERS = {
    'burdened_households': 'Burdened Households',
    'homeownership_rate': 'Home Ownership',
    'income_inequality': 'Income Inequality',
    'population_below_poverty': 'Population Below Poverty Line',
    'single_parent_households': 'Single Parent Households',
    'snap_benefits_recipients': 'SNAP Benefits Recipients',
    'unemployment_rate': 'Unemployment Rate',
    'resident_population': 'Resident Population',
}

EQUITY_COUNTY_HEADERS = [
    'Age 19 or Under',
    'Age 65 or Over',
    'Non-White Population (%)'
]

CENSUS_HEADERS = [
    'People of Color (%)', '200% Below Poverty Level (%)',
    'People with Disability (%)', 'Age 19 or Under (%)', 'Age 65 or Over (%)',
    'Limited English Proficiency (%)', 'Single Parent Family (%)', 'Zero-Vehicle Household (%)'
]

EQUITY_CENSUS_POC_LOW_INCOME = [
    'People of Color', "200% Below Poverty Level"
]

EQUITY_CENSUS_REMAINING_HEADERS = [
    'People with Disability', 'Age 19 or Under', 'Age 65 or Over',
    'Limited English Proficiency', 'Single Parent Family', 'Zero-Vehicle Household'
]

CLIMATE_CENSUS_HEADERS = [
    # 'coastal_flooding', 'hail','hurricane','ice_storm', 'riverine_flooding','tsunami'
    'Coastal Flooding Risk Score', 'Hail Risk Score', 'Hurricane Risk Score', 'Ice Storm Risk Score', 'Riverine Flooding Risk Score', 'Tsunami Risk Score'
]

TRANSPORT_CENSUS_HEADERS = [
    'Zero-Vehicle Households (%)',
    'Vehicle Miles Traveled',
    'No Computer Households (%)',
    'Renter Occupied Units (%)',
    'Drive Alone Commuters (%)',
    # 'Drive Alone (#)',
    'Average Commute Time (min)',
    'People of Color (%)',
    "200% Below Poverty Level (%)",
    'Age 19 or Under (%)',
    'Age 65 or Over (%)',
    'Limited English Proficiency (%)',
    'Single Parent Family (%)'
]

POSITIVE_TRANSPORT_CENSUS_HEADERS = [
    # 'Walkability Index',
    'Public Transport Commuters (%)',
    'Bicycle Commuters (%)'
]

TABLE_UNITS = {
    'burdened_households': '%',
    'homeownership_rate': '%',
    'income_inequality': 'Ratio',
    'population_below_poverty': '%',
    'single_parent_households': '%',
    'snap_benefits_recipients': 'Persons',
    'unemployment_rate': '%',
    'resident_population': 'Thousands of Persons',
    'Zero-Vehicle Households (%)': '%',
    'Vehicle Miles Traveled': ' miles',
    'No Computer Households (%)': '%',
    'Renter Occupied Units (%)': '%',
    'Drive Alone Commuters (%)': '%',
    # 'Drive Alone (#)': '',
    'Average Commute Time (min)': ' min',
    'People of Color (%)': '%',
    "200% Below Poverty Level (%)": '%',
    # 'Walkability Index': '',
    'Public Transport Commuters (%)': '%',
    'Bicycle Commuters (%)': '%',
    'Age 19 or Under (%)': '%',
    'Age 65 or Over (%)': '%',
    'Limited English Proficiency (%)': '%',
    'Single Parent Family (%)': '%',
    'Coastal Flooding Risk Score':'', 'Hail Risk Score':'', 'Hurricane Risk Score':'', 'Ice Storm Risk Score':'', 'Riverine Flooding Risk Score':'', 'Tsunami Risk Score':''
}

# @st.cache(allow_output_mutation=True, hash_funcs={"_thread.RLock": lambda _: None})
CENSUS_TABLES = [
    'commuting_characteristics',
    'disability_status',
    'educational_attainment',
    'employment_status',
    'english_proficiency',
    'family_type',
    'group_quarters_population',
    'hispanic_or_latino_origin_by_race',
    'household_job_availability',
    'household_technology_availability',
    'household_vehicle_availability',
    'housing_units_in_structure',
    'level_of_urbanicity',
    'median_household_income',
    # 'ntm_shapes',
    # 'ntm_stops',
    'occupants_per_bedroom',
    'per_capita_income',
    'population_below_poverty_double',
    'poverty_status',
    'resident_population_census_tract',
    'sex_by_age',
    'sex_of_workers_by_vehicles_available',
    'trip_miles'
    # 'walkability_index'
]

EQUITY_CENSUS_TABLES = [
    'poverty_status',
    #  'resident_population_census_tract',
    'population_below_poverty_double',
    'sex_by_age',
    'english_proficiency',
    'household_vehicle_availability',
    'hispanic_or_latino_origin_by_race',
    'disability_status',
    'family_type',
]

TRANSPORT_CENSUS_TABLES = [
    'poverty_status',
    #  'resident_population_census_tract',
    'population_below_poverty_double',
    'sex_by_age',
    'english_proficiency',
    'household_vehicle_availability',
    'hispanic_or_latino_origin_by_race',
    'disability_status',
    'family_type',
    'household_vehicle_availability',
    'level_of_urbanicity',
    'trip_miles',
    # 'walkability_index',
    'housing_units_in_structure',
    'median_household_income',
    'household_technology_availability',
    'commuting_characteristics'
]

CLIMATE_CENSUS_TABLES = [
    'national_risk_index'
]


def init_engine():
    return create_engine(
        f'postgresql://{credentials.DB_USER}:{credentials.DB_PASSWORD}@{credentials.DB_HOST}:{credentials.DB_PORT}/{credentials.DB_NAME}'
    )


def init_connection():
    return (
        psycopg2.connect(**st.secrets["postgres"])
        if st.secrets
        else psycopg2.connect(
            user=credentials.DB_USER,
            password=credentials.DB_PASSWORD,
            host=credentials.DB_HOST,
            port=credentials.DB_PORT,
            dbname=credentials.DB_NAME,
        )
    )


def write_table(df: pd.DataFrame, table: str):
    engine = init_engine()
    df.to_sql(table, engine, if_exists='replace', method='multi')


def all_counties_query(where: str = None) -> pd.DataFrame:
    conn = init_connection()
    cur = conn.cursor()
    query = "SELECT DISTINCT county_name, state_name, county_id FROM id_index"
    if where:
        query += f" WHERE {where}"
    query += ";"
    cur.execute(query)
    colnames = [desc[0] for desc in cur.description]
    results = cur.fetchall()
    conn.commit()
    return pd.DataFrame(results, columns=colnames)


def table_names_query() -> list:
    conn = init_connection()
    cur = conn.cursor()
    cur.execute("""SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public'
        """)
    results = cur.fetchall()
    conn.commit()

    return [_[0] for _ in results]


@st.experimental_memo(ttl=1200)
def read_table(table: str, columns: list = None, where: str = None, order_by: str = None,
               order: str = 'ASC', fred=False) -> pd.DataFrame:
    conn = init_connection()
    if not fred:
        if columns is not None:
            cols = ', '.join(columns)
            query = f"SELECT {cols} FROM {table}"
        else:
            query = f"SELECT * FROM {table}"
        if where is not None:
            query += f" WHERE {where}"
        if order_by is not None:
            query += f"ORDER BY {order_by} {order}"
    else:
        query = f"""SELECT {table}.* FROM {table},
                    (SELECT county_id,max(date) as date
                         FROM {table}
                         GROUP BY county_id) max_county
                      WHERE {table}.{where}
                      AND {table}.county_id=max_county.county_id
                      AND {table}.date=max_county.date"""
    query += ';'
    return pd.read_sql(query, con=conn)


@st.experimental_memo(ttl=1200)
def latest_data_census_tracts(state: str, counties: list, tables: list) -> pd.DataFrame:
    conn = init_connection()
    cur = conn.cursor()
    tracts_df = census_tracts_geom_query(counties, state)
    counties_str = str(tuple(counties)).replace(',)', ')')
    where_clause = f"WHERE id_index.state_name ='{state}' AND id_index.county_name IN {counties_str}"

    for table_name in tables:
        query = f"""SELECT {table_name}.*, id_index.county_name, id_index.county_id, id_index.state_name, id_index.tract_id,
        resident_population_census_tract.tot_population_census_2010
            FROM {table_name} 
            INNER JOIN id_index ON {table_name}.tract_id = id_index.tract_id
            INNER JOIN resident_population_census_tract ON {table_name}.tract_id = resident_population_census_tract.tract_id
            {where_clause};"""
        cur.execute(query)
        results = cur.fetchall()
        conn.commit()

        colnames = [desc[0] for desc in cur.description]
        df = pd.DataFrame(results, columns=colnames)
        df = df.loc[:, ~df.columns.duplicated()]

        df.rename({'tract_id': 'Census Tract'}, axis=1, inplace=True)

        tracts_df = tracts_df.merge(df, on="Census Tract", how="inner", suffixes=('', '_y'))
        tracts_df.drop(tracts_df.filter(regex='_y$').columns.tolist(), axis=1, inplace=True)
        tracts_df = tracts_df.loc[:, ~tracts_df.columns.duplicated()]
    return tracts_df


def load_distributions() -> tuple:
    metro_areas = generic_select_query('housing_stock_distribution', [
        'location',
        '0_br_pct',
        '1_br_pct',
        '2_br_pct',
        '3_br_pct',
        '4_br_pct'
    ])
    locations = list(metro_areas['location'])
    metro_areas.set_index('location', inplace=True)

    return metro_areas, locations


def policy_query() -> pd.DataFrame:
    conn = init_connection()
    cur = conn.cursor()
    cur.execute(
        'SELECT county_id as county_id, policy_value as "Policy Value", countdown as "Countdown" '
        'FROM policy'
    )
    colnames = [desc[0] for desc in cur.description]
    results = cur.fetchall()
    conn.commit()

    return pd.DataFrame(results, columns=colnames)


def latest_data_single_table(table_name: str, require_counties: bool = True) -> pd.DataFrame:
    conn = init_connection()
    cur = conn.cursor()
    cur.execute(
        f'SELECT DISTINCT ON (county_id) county_id, date AS "{TABLE_HEADERS[table_name]} Date", value AS "{TABLE_HEADERS[table_name]} ({TABLE_UNITS[table_name]})" FROM {table_name} ORDER BY county_id , "date" DESC'
    )
    results = cur.fetchall()
    conn.commit()

    colnames = [desc[0] for desc in cur.description]

    df = pd.DataFrame(results, columns=colnames)
    if require_counties:
        counties_df = all_counties_query()
        df = counties_df.merge(df)
    return df


@st.experimental_memo(ttl=1200)
def fred_query(counties_str: str) -> pd.DataFrame:
    frames = []
    for table_name in FRED_TABLES:
        # Todo: update in database and remove new suffix
        f_df = read_table(f"{table_name}_new", where=f"county_id in {counties_str}", columns=[table_name, 'county_id'],
                          fred=True)
        f_df.drop(['date', 'state_name', 'county_name'], axis=1, inplace=True)
        frames.append(f_df)
    fred_df = pd.concat(frames, axis=1)
    fred_df = fred_df.loc[:, ~fred_df.columns.duplicated()]
    fred_df = fred_df.astype(float)
    chmura_df = static_data_single_table('chmura_economic_vulnerability_index', ['VulnerabilityIndex'])
    fred_df = fred_df.merge(chmura_df, how='outer', on='county_id', suffixes=('', '_DROP')).filter(
        regex='^(?!.*_DROP)')
    return fred_df


@st.experimental_memo(ttl=1200)
def get_all_county_data(state: str, counties: list) -> pd.DataFrame:
    if counties:
        counties_str = "(" + ",".join([f"'{str(_)}'" for _ in counties]) + ")"
        demo_df = read_table('county_demographics', where=f"county_id in {counties_str}")
        fred_df = fred_query(counties_str)
    else:
        demo_df = read_table('county_demographics', where=f"state_name='{state}';")
        counties = all_counties_query(f"state_name='{state}'")
        county_ids = counties['county_id'].to_list()
        counties_str = "(" + ",".join([f"'{str(_)}'" for _ in county_ids]) + ")"
        fred_df = fred_query(counties_str=counties_str)
    demo_df = demo_df.merge(fred_df, on='county_id', how='inner', suffixes=('', '_DROP')).filter(
        regex='^(?!.*_DROP)')

    demo_df['Non-White Population'] = (demo_df['black'] + demo_df['ameri_es'] + demo_df['asian'] + demo_df[
        'hawn_pi'] + demo_df['hispanic'] + demo_df['other'] + demo_df['mult_race'])
    demo_df['Age 19 or Under'] = (
            demo_df['age_under5'] + demo_df['age_5_9'] + demo_df['age_10_14'] + demo_df['age_15_19'])
    demo_df['Age 65 or Over'] = (demo_df['age_65_74'] + demo_df['age_75_84'] + demo_df['age_85_up'])
    demo_df['Non-White Population (%)'] = demo_df['Non-White Population'] / demo_df['population'] * 100
    demo_df['fips'] = demo_df['fips'].astype(int)

    demo_df.rename({
        'state_name': 'State',
        'county_name': 'County Name',
        'hse_units': 'Housing Units',
        'vacant': 'Vacant Units',
        'renter_occ': 'Renter Occupied Units',
        'med_age': 'Median Age',
        'white': 'White Population',
        'black': 'Black Population',
        'ameri_es': 'Native American Population',
        'asian': 'Asian Population',
        'hawn_pi': 'Pacific Islander Population',
        'hispanic': 'Hispanic Population',
        'other': 'Other Population',
        'mult_race': 'Multiple Race Population',
        'males': 'Male Population',
        'females': 'Female Population',
        'population': 'Total Population',
    }, axis=1, inplace=True)
    demo_df.drop_duplicates(inplace=True)
    demo_df.fillna(0, inplace=True)
    return demo_df


def static_data_single_table(table_name: str, columns: list) -> pd.DataFrame:
    conn = init_connection()
    cur = conn.cursor()
    str_columns = ', '.join(f'"{c}"' for c in columns)
    query = f'SELECT county_id, {str_columns} FROM {table_name} '
    cur.execute(query)
    results = cur.fetchall()
    conn.commit()

    colnames = [desc[0] for desc in cur.description]
    return pd.DataFrame(results, columns=colnames)


def generic_select_query(table_name: str, columns: list, where: str = None) -> pd.DataFrame:
    conn = init_connection()
    cur = conn.cursor()
    str_columns = ', '.join(f'"{c}"' for c in columns)
    query = f'SELECT {str_columns} FROM {table_name} '
    if where is not None:
        query += f'WHERE {where}'
    cur.execute(query)
    results = cur.fetchall()
    conn.commit()

    colnames = [desc[0] for desc in cur.description]
    return pd.DataFrame(results, columns=colnames)


@st.experimental_memo(ttl=1200)
def get_county_geoms(counties_list: list, state: str) -> pd.DataFrame:
    conn = init_connection()
    counties_list = [_.replace("'", "''") for _ in counties_list]
    counties = "(" + ",".join([f"'{str(_)}'" for _ in counties_list]) + ")"
    cur = conn.cursor()
    query = f"SELECT * FROM county_geoms WHERE state_name='{state}' AND county_name in {counties};"
    cur.execute(query)
    results = cur.fetchall()
    conn.commit()

    colnames = [desc[0] for desc in cur.description]
    df = pd.DataFrame(results, columns=colnames)
    parcels = []
    for parcel in df['geom']:
        geom = wkb.loads(parcel, hex=True)
        parcels.append(geom.simplify(tolerance=0.0001, preserve_topology=True))
    geom_df = pd.DataFrame()
    geom_df['county_id'] = df['county_id']
    geom_df['County Name'] = df['county_name']
    geom_df['State'] = df['state_name']
    geom_df['Area sqmi'] = df['sqmi']
    geom_df['geom'] = pd.Series(parcels)
    return geom_df


@st.experimental_memo(ttl=1200)
def get_county_geoms_by_id(counties_list: list) -> pd.DataFrame:
    conn = init_connection()
    counties = "(" + ",".join([f"'{str(_)}'" for _ in counties_list]) + ")"
    cur = conn.cursor()
    query = f"SELECT * FROM county_geoms WHERE county_id in {counties};"
    cur.execute(query)
    results = cur.fetchall()
    conn.commit()

    colnames = [desc[0] for desc in cur.description]
    df = pd.DataFrame(results, columns=colnames)
    parcels = []
    for parcel in df['geom']:
        geom = wkb.loads(parcel, hex=True)
        parcels.append(geom.simplify(tolerance=0.0001, preserve_topology=True))
    geom_df = pd.DataFrame()
    geom_df['county_id'] = df['county_id']
    geom_df['County Name'] = df['county_name']
    geom_df['State'] = df['state_name']
    geom_df['Area sqmi'] = df['sqmi']
    geom_df['geom'] = pd.Series(parcels)
    return geom_df


@st.experimental_memo(ttl=1200)
def census_tracts_geom_query(counties, state) -> pd.DataFrame:
    conn = init_connection()
    cur = conn.cursor()
    if len(counties) > 1:
        where_clause = 'WHERE id_index.state_name = ' + "'" + state + "'" + ' ' + 'AND id_index.county_name IN ' + str(
            tuple(counties))
    if len(counties) == 1:
        where_clause = 'WHERE id_index.state_name = ' + "'" + state + "'" + ' ' + 'AND id_index.county_name IN (' + "'" + \
                       counties[0] + "'" + ')'
    query = f"""
        SELECT id_index.county_name, id_index.state_name, census_tracts_geom.tract_id, census_tracts_geom.geom
        FROM id_index
        INNER JOIN census_tracts_geom ON census_tracts_geom.tract_id=id_index.tract_id
        {where_clause};
    """
    cur.execute(query)
    colnames = [desc[0] for desc in cur.description]
    results = cur.fetchall()
    conn.commit()

    df = pd.DataFrame(results, columns=colnames)
    parcels = []
    for parcel in df['geom']:
        geom = wkb.loads(parcel, hex=True)
        parcels.append(geom.simplify(tolerance=0.00005, preserve_topology=False))
    geom_df = pd.DataFrame()
    geom_df['Census Tract'] = df['tract_id']
    geom_df['geom'] = pd.Series(parcels)
    return geom_df


@st.experimental_memo(ttl=1200)
def get_transit_stops_geoms(columns: list = [], where: str = None) -> pd.DataFrame:
    conn = init_connection()
    if columns:
        cols = ', '.join(columns)
        query = f"SELECT {cols} FROM ntm_stops"
    else:
        query = """SELECT * FROM ntm_stops"""
    if where is not None:
        query += f" WHERE {where}"
    query += ';'
    return gpd.read_postgis(query, conn)


@st.experimental_memo(ttl=1200)
def get_transit_shapes_geoms(columns: list = [], where: str = None) -> pd.DataFrame:
    conn = init_connection()
    if columns:
        cols = ', '.join(columns)
        query = f"SELECT {cols} FROM ntm_shapes"
    else:
        query = """SELECT * FROM ntm_shapes"""
    if where is not None:
        query += f" WHERE {where}"
    query += ';'
    df = gpd.read_postgis(query, conn)
    df.drop_duplicates(subset=['geom'], inplace=True)
    return df


@st.experimental_memo(ttl=1200)
def static_data_all_table() -> pd.DataFrame:
    counties_df = all_counties_query()
    for table_name in STATIC_TABLES:
        table_output = static_data_single_table(table_name, STATIC_COLUMNS[table_name])
        counties_df = counties_df.merge(table_output)
    return counties_df


def output_data(df: pd.DataFrame, table_name: str = 'fred_tables', ext: str = 'xlsx') -> str:
    path = f'Output/{table_name}.{ext}'
    if ext == 'pk':
        df.to_pickle(path)
    elif ext == 'xlsx':
        df.to_excel(path)
    elif ext == 'csv':
        df.to_csv(path)
    else:
        print('Only .pk, .csv, and .xlsx outputs are currently supported.')
        sys.exit()
    return path


def fmr_data():
    conn = init_connection()
    cur = conn.cursor()
    cur.execute('SELECT state_full as "State", countyname as "County Name" FROM fair_market_rents;')
    colnames = [desc[0] for desc in cur.description]
    results = cur.fetchall()
    conn.commit()

    return pd.DataFrame(results, columns=colnames)


def filter_state(data: pd.DataFrame, state: str) -> pd.DataFrame:
    return data[data['State'].str.lower() == state.lower()]


def filter_counties(data: pd.DataFrame, counties: list) -> pd.DataFrame:
    counties = [_.lower() for _ in counties]
    return data[data['County Name'].str.lower().isin(counties)]


@st.experimental_memo(ttl=1200)
def load_all_data() -> pd.DataFrame:
    if os.path.exists("Output/all_tables.xlsx"):
        try:
            res = input('Previous data found. Use data from local `all_tables.xlsx`? [y/N]')
            if res.lower() in ['y', 'yes']:
                df = pd.read_excel('Output/all_tables.xlsx')
            else:
                df = get_all_county_data()
        except:
            print('Something went wrong with the Excel file. Falling back to database query.')
            df = get_all_county_data()
    else:
        df = get_all_county_data()

    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df.set_index(['State', 'County Name'], drop=True, inplace=True)

    df.rename({'Vulnerability Index': 'COVID Vulnerability Index'}, axis=1, inplace=True)

    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    df = df.loc[:, ~df.columns.duplicated()]

    return df


# def clean_equity_data(data: pd.DataFrame) -> pd.DataFrame:
#     data['Age 19 or Under'] = (
#             data['female_under_5'] + data['female_5_to_9'] + data['female_10_to_14'] +
#             data['female_15_to_17'] + data['female_18_and_19'] +
#             data['male_under_5'] + data['male_5_to_9'] + data['male_10_to_14'] +
#             data['male_15_to_17'] + data['male_18_and_19']
#     )
#     data['Age 65 or Over'] = (
#             data['female_65_and_66'] + data['female_67_to_69'] + data['female_70_to_74'] +
#             data['female_75_to_79'] + data['female_80_to_84'] + data['female_85_and_over'] +
#             data['male_65_and_66'] + data['male_67_to_69'] + data['male_70_to_74'] +
#             data['male_75_to_79'] + data['male_80_to_84'] + data['male_85_and_over']
#     )

#     data.rename({'below_pov_level': 'Below Poverty Level', '200_below_pov_level': '200% Below Poverty Level'}, axis=1,
#                 inplace=True)

#     data['total_w_a_disability'] = (data['male_under_5_w_a_disability'] + data['male_5_to_17_w_a_disability'] + data[
#         'male_18_to_34_w_a_disability'] +
#                                     data['male_35_to_64_w_a_disability'] + data['male_65_to_74_w_a_disability'] + data[
#                                         'male_75_and_over_w_a_disability'] +
#                                     data['female_under_5_w_a_disability'] + data['female_5_to_17_w_a_disability'] +
#                                     data['female_18_to_34_w_a_disability'] +
#                                     data['female_35_to_64_w_a_disability'] + data['female_65_to_74_w_a_disability'] +
#                                     data['female_75_and_over_w_a_disability']
#                                     )

#     data['speak_eng_not_well'] = (
#             data['foreign_speak_spanish_speak_eng_not_well'] + data['foreign_speak_spanish_speak_eng_not_at_all'] +
#             data['foreign_speak_other_indo-euro_speak_eng_not_well'] + data[
#                 'foreign_speak_other_indo-euro_speak_eng_not_at_all'] +
#             data['foreign_speak_asian_or_pac_isl_lang_speak_eng_not_well'] + data[
#                 'foreign_speak_asian_or_pac_isl_lang_speak_eng_not_at_all'] +
#             data['foreign_speak_other_speak_eng_not_well'] + data['foreign_speak_other_speak_eng_not_at_all']
#     )

#     data['single_parent'] = data['other_male_householder_no_spouse_w_kids'] + data[
#         'other_female_householder_no_spouse_w_kids']

#     data['non-white'] = data['total_population'] - data['not_hisp_or_latino_white']

#     data['People with Disability (%)'] = data['total_w_a_disability'] / (data['male'] + data['female'])
#     data['200% Below Poverty Level (%)'] = data['200% Below Poverty Level'] / data[
#         'population_for_whom_poverty_status_is_determined']
#     data['Age 19 or Under (%)'] = data['Age 19 or Under'] / data['total_population']
#     data['Age 65 or Over (%)'] = data['Age 65 or Over'] / data['total_population']
#     data['Limited English Proficiency (%)'] = data['speak_eng_not_well'] / (data['native'] + data['foreign_born'])
#     data['Single Parent Family (%)'] = data['single_parent'] / data['total_families']
#     data['Zero-Vehicle Household (%)'] = data['percent_hh_0_veh'] / 100
#     data['People of Color (%)'] = data['non-white'] / data['total_population']

#     for header in (EQUITY_CENSUS_POC_LOW_INCOME + EQUITY_CENSUS_REMAINING_HEADERS):
#         data[header + ' (%)'] = round(data[header + ' (%)'] * 100)

#     data['criteria_A'] = 0
#     data['criteria_B'] = 0

#     data['Criteria A'] = False
#     data['Criteria B'] = False

#     return data

def clean_climate_data(data: pd.DataFrame, epc: pd.DataFrame) -> pd.DataFrame:
    hazards = ['coastal_flooding', 'hail','hurricane','ice_storm', 'riverine_flooding','tsunami']
        # 'avalanche', 'coastal_flooding', 'cold_wave', 'drought', 'earthquake', 'hail', 'heat_wave', 'hurricane',
        #        'ice_storm', 'landslide', 'lightning', 'riverine_flooding', 'strong_wind', 'tornado', 'tsunami',
        #        'volcanic_activity', 'wildfire', 'winter_weather'
    risk_score = ['Census Tract', 'geom', 'county_name', 'state_name']+[hazard+ '_risk_score' for hazard in hazards]

    data.fillna(0.0, inplace=True)
    data = data[risk_score].copy()
    new_column_names = [" ".join([word.capitalize() for word in x]) for x in data.columns.str.split('_')]
    data.columns = new_column_names
    data.rename(columns={'Census tract':'Census Tract', 'Geom':'geom', 'County Name':'county_name', 'State Name':'state_name'}, inplace=True)
    # st.table(epc.columns)
    # st.table(data.columns)
    averages = {}
    epc_averages = {}

    for x in data.columns[4:]:
        averages[x] = data[x].mean()
        epc_averages[x] = data.loc[data['Census Tract'].isin(epc['Census Tract'])][x].mean()
    climate_epc = data.loc[data['Census Tract'].isin(epc['Census Tract'])]

    normalized_data = data.copy()
    normalized_data[data.columns[4:]] = preprocessing.MinMaxScaler().fit_transform(
        normalized_data[data.columns[4:]])

    return climate_epc, data, normalized_data, averages, epc_averages


# def clean_transport_data(data: pd.DataFrame, epc: pd.DataFrame) -> pd.DataFrame:
#     data['walkability_index'] = round(data['walkability_index'])
#     data['number_drive_alone'] = data['percent_drive_alone'] * data['total_workers_commute']
#     data.drop(['total_workers_commute'], axis=1, inplace=True)

#     data['non-white'] = data['total_population'] - data['not_hisp_or_latino_white']
#     data['People of Color (%)'] = 100 * (data['non-white'] / data['total_population'])
#     data['No Computer Households (%)'] = 100 * (data['household_no_computing_device'] / (
#             data['household_no_computing_device'] + data['household_computer'] + data[
#         'household_smartphone_no_computer'] + data['household_no_internet'] + data['household_broadband']))
#     data['200% Below Poverty Level (%)'] = 100 * (
#             data['200_below_pov_level'] / data['population_for_whom_poverty_status_is_determined'])
#     data['Renter Occupied Units (%)'] = 100 * (data['renter-occ_units'] / data['occupied_housing_units'])

#     data.rename({
#         'percent_hh_0_veh': 'Zero-Vehicle Households (%)',
#         'vehicle_miles_traveled': 'Vehicle Miles Traveled',
#         # 'household_no_computing_device': 'No Computer Households',
#         # 'household_no_internet': 'No Internet Households',
#         'percent_drive_alone': 'Drive Alone Commuters (%)',
#         # 'number_drive_alone': 'Drive Alone (#)',
#         'mean_travel_time': "Average Commute Time (min)",
#         'walkability_index': "Walkability Index",
#         'percent_public_transport': 'Public Transport Commuters (%)',
#         'percent_bicycle': 'Bicycle Commuters (%)'
#     },
#         axis=1, inplace=True)

#     averages = {}
#     epc_averages = {}

#     for x in TRANSPORT_CENSUS_HEADERS:
#         averages[x] = data[x].mean()
#         epc_averages[x] = data.loc[data['Census Tract'].isin(epc['Census Tract'])][x].mean()
#     transport_epc = data.loc[data['Census Tract'].isin(epc['Census Tract'])]

#     normalized_data = data.copy()
#     normalized_data[TRANSPORT_CENSUS_HEADERS] = preprocessing.MinMaxScaler().fit_transform(
#         normalized_data[TRANSPORT_CENSUS_HEADERS])

#     return transport_epc, data, normalized_data, averages, epc_averages


def get_equity_geographies(epc: pd.DataFrame, coeff: float) -> pd.DataFrame:
    concentration_thresholds = {}
    averages = {}

    for header in (EQUITY_CENSUS_POC_LOW_INCOME + EQUITY_CENSUS_REMAINING_HEADERS):
        averages[header+ ' (%)'] = epc[header + ' (%)'].mean()
        concentration_thresholds[header+ ' (%)'] = averages[header+ ' (%)'] + coeff * epc[header + ' (%)'].std()
        epc[header + '_check'] = epc[header + ' (%)'].apply(lambda x: x > concentration_thresholds[header+ ' (%)'])
        epc[header + '_check'] = epc[header + '_check'].astype(int)

    epc['criteria_A'] = epc[[x + '_check' for x in EQUITY_CENSUS_POC_LOW_INCOME]].sum(axis=1, numeric_only=True)
    epc['Criteria A'] = epc['criteria_A'].apply(lambda x: x == 2)

    epc['criteria_B'] = epc[[x + '_check' for x in EQUITY_CENSUS_REMAINING_HEADERS]].sum(axis=1, numeric_only=True)
    temp = epc['200% Below Poverty Level (%)'].apply(lambda x: x > concentration_thresholds['200% Below Poverty Level (%)'])
    epc['Criteria B'] = (
        epc['criteria_B'].apply(lambda x: x >= 3) + temp.astype(int) == 2
    )

    df = epc

    epc['Criteria'] = epc[['Criteria A', 'Criteria B']].apply(
        lambda x: 'Equity Geography (Meets Both Criteria)' if (x['Criteria A'] & x['Criteria B']) else
        ('Equity Geography (Meets Criteria A)' if x['Criteria A'] else
         ('Equity Geography (Meets Criteria B)' if x['Criteria B'] else 'Not selected as an Equity Geography')),
        axis=1)
    # epc['Criteria'] = epc.apply(lambda x: 'Both' if (x['Criteria A'] | x['Criteria B']) else 'Other')
    epc = epc.loc[(epc['Criteria A'] | epc['Criteria B'])]
    df['Category'] = (df['Criteria A'].apply(lambda x: bool(x)) | df['Criteria B'].apply(lambda x: bool(x)))
    df['Category'] = df['Category'].apply(lambda x: 'Equity Geography' if x is True else 'Other')

    epc_averages = {
        header + ' (%)': epc[header + ' (%)'].mean()
        for header in (
            EQUITY_CENSUS_POC_LOW_INCOME + EQUITY_CENSUS_REMAINING_HEADERS
        )
    }
    return epc, df, concentration_thresholds, averages, epc_averages


def clean_equity_data(data: pd.DataFrame) -> pd.DataFrame:
    data['Age 19 or Under'] = (
            data['female_under_5'] + data['female_5_to_9'] + data['female_10_to_14'] +
            data['female_15_to_17'] + data['female_18_and_19'] +
            data['male_under_5'] + data['male_5_to_9'] + data['male_10_to_14'] +
            data['male_15_to_17'] + data['male_18_and_19']
    )
    data['Age 65 or Over'] = (
            data['female_65_and_66'] + data['female_67_to_69'] + data['female_70_to_74'] +
            data['female_75_to_79'] + data['female_80_to_84'] + data['female_85_and_over'] +
            data['male_65_and_66'] + data['male_67_to_69'] + data['male_70_to_74'] +
            data['male_75_to_79'] + data['male_80_to_84'] + data['male_85_and_over']
    )

    data.rename({'below_pov_level': 'Below Poverty Level', '200_below_pov_level': '200% Below Poverty Level'}, axis=1,
                inplace=True)

    data['total_w_a_disability'] = (data['male_under_5_w_a_disability'] + data['male_5_to_17_w_a_disability'] + data[
        'male_18_to_34_w_a_disability'] +
                                    data['male_35_to_64_w_a_disability'] + data['male_65_to_74_w_a_disability'] + data[
                                        'male_75_and_over_w_a_disability'] +
                                    data['female_under_5_w_a_disability'] + data['female_5_to_17_w_a_disability'] +
                                    data['female_18_to_34_w_a_disability'] +
                                    data['female_35_to_64_w_a_disability'] + data['female_65_to_74_w_a_disability'] +
                                    data['female_75_and_over_w_a_disability']
                                    )

    data['speak_eng_not_well'] = (
            data['foreign_speak_spanish_speak_eng_not_well'] + data['foreign_speak_spanish_speak_eng_not_at_all'] +
            data['foreign_speak_other_indo-euro_speak_eng_not_well'] + data[
                'foreign_speak_other_indo-euro_speak_eng_not_at_all'] +
            data['foreign_speak_asian_or_pac_isl_lang_speak_eng_not_well'] + data[
                'foreign_speak_asian_or_pac_isl_lang_speak_eng_not_at_all'] +
            data['foreign_speak_other_speak_eng_not_well'] + data['foreign_speak_other_speak_eng_not_at_all']
    )

    data['single_parent'] = data['other_male_householder_no_spouse_w_kids'] + data[
        'other_female_householder_no_spouse_w_kids']

    data['non-white'] = data['total_population'] - data['not_hisp_or_latino_white']

    data['People with Disability (%)'] = data['total_w_a_disability'] / (data['male'] + data['female'])
    data['200% Below Poverty Level (%)'] = data['200% Below Poverty Level'] / data[
        'population_for_whom_poverty_status_is_determined']
    data['Age 19 or Under (%)'] = data['Age 19 or Under'] / data['total_population']
    data['Age 65 or Over (%)'] = data['Age 65 or Over'] / data['total_population']
    data['Limited English Proficiency (%)'] = data['speak_eng_not_well'] / (data['native'] + data['foreign_born'])
    data['Single Parent Family (%)'] = data['single_parent'] / data['total_families']
    data['Zero-Vehicle Household (%)'] = data['percent_hh_0_veh']
    data['People of Color (%)'] = data['non-white'] / data['total_population']

    for header in (EQUITY_CENSUS_POC_LOW_INCOME + EQUITY_CENSUS_REMAINING_HEADERS):
        data[header + ' (%)'] = round(data[header + ' (%)'] * 100)

    data['criteria_A'] = 0
    data['criteria_B'] = 0

    data['Criteria A'] = False
    data['Criteria B'] = False

    return data


def clean_transport_data(data: pd.DataFrame, epc: pd.DataFrame) -> pd.DataFrame:
    # data['walkability_index'] = round(data['walkability_index'])
    data['number_drive_alone'] = data['percent_drive_alone'] * data['total_workers_commute']
    data.drop(['total_workers_commute'], axis=1, inplace=True)

    data['non-white'] = data['total_population'] - data['not_hisp_or_latino_white']
    data['People of Color (%)'] = 100 * (data['non-white'] / data['total_population'])
    data['No Computer Households (%)'] = 100 * (data['household_no_computing_device'] / (
                data['household_no_computing_device'] + data['household_computer'] + data[
            'household_smartphone_no_computer'] + data['household_no_internet'] + data['household_broadband']))
    data['200% Below Poverty Level (%)'] = 100 * (
                data['200_below_pov_level'] / data['population_for_whom_poverty_status_is_determined'])
    data['Renter Occupied Units (%)'] = 100 * (data['renter-occ_units'] / data['occupied_housing_units'])
    data['Age 19 or Under'] = (
            data['female_under_5'] + data['female_5_to_9'] + data['female_10_to_14'] +
            data['female_15_to_17'] + data['female_18_and_19'] +
            data['male_under_5'] + data['male_5_to_9'] + data['male_10_to_14'] +
            data['male_15_to_17'] + data['male_18_and_19']
    )
    data['Age 19 or Under (%)'] = 100 * (data['Age 19 or Under'] / data['total_population'])
    data['Age 65 or Over'] = (
            data['female_65_and_66'] + data['female_67_to_69'] + data['female_70_to_74'] +
            data['female_75_to_79'] + data['female_80_to_84'] + data['female_85_and_over'] +
            data['male_65_and_66'] + data['male_67_to_69'] + data['male_70_to_74'] +
            data['male_75_to_79'] + data['male_80_to_84'] + data['male_85_and_over']
    )
    data['Age 65 or Over (%)'] = 100 * (data['Age 65 or Over'] / data['total_population'])
    data['speak_eng_not_well'] = (
            data['foreign_speak_spanish_speak_eng_not_well'] + data['foreign_speak_spanish_speak_eng_not_at_all'] +
            data['foreign_speak_other_indo-euro_speak_eng_not_well'] + data[
                'foreign_speak_other_indo-euro_speak_eng_not_at_all'] +
            data['foreign_speak_asian_or_pac_isl_lang_speak_eng_not_well'] + data[
                'foreign_speak_asian_or_pac_isl_lang_speak_eng_not_at_all'] +
            data['foreign_speak_other_speak_eng_not_well'] + data['foreign_speak_other_speak_eng_not_at_all']
    )
    data['Limited English Proficiency (%)'] = 100 * (
                data['speak_eng_not_well'] / (data['native'] + data['foreign_born']))
    data['single_parent'] = data['other_male_householder_no_spouse_w_kids'] + data[
        'other_female_householder_no_spouse_w_kids']
    data['Single Parent Family (%)'] = 100 * (data['single_parent'] / data['total_families'])

    data.rename({
        'percent_hh_0_veh': 'Zero-Vehicle Households (%)',
        'vehicle_miles_traveled': 'Vehicle Miles Traveled',
        # 'household_no_computing_device': 'No Computer Households',
        # 'household_no_internet': 'No Internet Households',
        'percent_drive_alone': 'Drive Alone Commuters (%)',
        # 'number_drive_alone': 'Drive Alone (#)',
        'mean_travel_time': "Average Commute Time (min)",
        # 'walkability_index': "Walkability Index",
        'percent_public_transport': 'Public Transport Commuters (%)',
        'percent_bicycle': 'Bicycle Commuters (%)'
    },
        axis=1, inplace=True)

    averages = {}
    epc_averages = {}

    for x in TRANSPORT_CENSUS_HEADERS:
        averages[x] = data[x].mean()
        epc_averages[x] = data.loc[data['Census Tract'].isin(epc['Census Tract'])][x].mean()
    transport_epc = data.loc[data['Census Tract'].isin(epc['Census Tract'])]

    normalized_data = data.copy()
    normalized_data[TRANSPORT_CENSUS_HEADERS] = preprocessing.MinMaxScaler().fit_transform(
        normalized_data[TRANSPORT_CENSUS_HEADERS])

    return transport_epc, data, normalized_data, averages, epc_averages


# def get_equity_geographies(epc: pd.DataFrame, coeff: float) -> pd.DataFrame:
#     concentration_thresholds = dict()
#     averages = dict()

#     for header in (EQUITY_CENSUS_POC_LOW_INCOME + EQUITY_CENSUS_REMAINING_HEADERS):
#         averages[header] = epc[header + ' (%)'].mean()
#         concentration_thresholds[header] = averages[header] + coeff * epc[header + ' (%)'].std()
#         epc[header + '_check'] = epc[header + ' (%)'].apply(lambda x: x > concentration_thresholds[header])
#         epc[header + '_check'] = epc[header + '_check'].astype(int)

#     epc['criteria_A'] = epc[[x + '_check' for x in EQUITY_CENSUS_POC_LOW_INCOME]].sum(axis=1, numeric_only=True)
#     epc['Criteria A'] = epc['criteria_A'].apply(lambda x: bool(x == 2))

#     epc['criteria_B'] = epc[[x + '_check' for x in EQUITY_CENSUS_REMAINING_HEADERS]].sum(axis=1, numeric_only=True)
#     temp = epc['200% Below Poverty Level (%)'].apply(lambda x: x > concentration_thresholds['200% Below Poverty Level'])
#     epc['Criteria B'] = (epc['criteria_B'].apply(lambda x: bool(x >= 3)) + temp.astype(int)) == 2

#     df = epc

#     epc['Criteria'] = epc[['Criteria A', 'Criteria B']].apply(
#         lambda x: 'Equity Geography (Meets Both Criteria)' if (x['Criteria A'] & x['Criteria B']) else
#         ('Equity Geography (Meets Criteria A)' if x['Criteria A'] else
#          ('Equity Geography (Meets Criteria B)' if x['Criteria B'] else 'Not selected as an Equity Geography')),
#         axis=1)
#     # epc['Criteria'] = epc.apply(lambda x: 'Both' if (x['Criteria A'] | x['Criteria B']) else 'Other')
#     epc = epc.loc[(epc['Criteria A'] | epc['Criteria B'])]
#     df['Category'] = (df['Criteria A'].apply(lambda x: bool(x)) | df['Criteria B'].apply(lambda x: bool(x)))
#     df['Category'] = df['Category'].apply(lambda x: 'Equity Geography' if x is True else 'Other')

#     epc_averages = {}
#     for header in (EQUITY_CENSUS_POC_LOW_INCOME + EQUITY_CENSUS_REMAINING_HEADERS):
#         epc_averages[header] = epc[header + ' (%)'].mean()

#     return epc, df, concentration_thresholds, averages, epc_averages


def get_existing_policies(df: pd.DataFrame) -> pd.DataFrame:
    policy_df = policy_query()
    temp_df = df.merge(policy_df, on='county_id')
    if not temp_df.empty and len(df) == len(temp_df):
        if st._is_running_with_streamlit:
            if st.checkbox('Use existing policy data?'):
                return temp_df
        else:
            res = input('Policy data found in database. Use this data? [Y/n]').strip()
            if res.lower() == 'y' or res.lower() == 'yes' or res == '':
                return temp_df

    else:
        policy_df = pd.read_excel('Policy Workbook.xlsx', sheet_name='Analysis Data')
        temp_df = df.merge(policy_df, on='County Name')
        if not temp_df.empty and len(df) == len(temp_df):
            return temp_df
        else:
            print(
                "INFO: Policy data not found. Check that you've properly filled in the Analysis Data page in `Policy Workbook.xlsx` with the counties you're analyzing.")

    return df


@st.experimental_memo(ttl=1200)
def get_county_data(state: str, county_ids: list = None, policy: bool = False):
    df = get_all_county_data(state, county_ids)

    df = clean_data(df)
    return df


@st.experimental_memo(ttl=3600)
def get_national_county_data() -> pd.DataFrame:
    frames = []
    for s in STATES:
        tmp_df = get_county_data(s)
        frames.append(tmp_df)
    return pd.concat(frames)


@st.experimental_memo(ttl=3600)
def get_national_county_geom_data(counties: list) -> pd.DataFrame:
    frames = []
    for _ in counties:
        tmp_df = get_county_geoms()
        frames.append(tmp_df)
    return pd.concat(frames)


def test_new_counties():
    conn = init_connection()
    cur = conn.cursor()
    query = "SELECT * FROM esri_counties;"
    cur.execute(query)
    results = cur.fetchall()
    conn.commit()
    colnames = [desc[0] for desc in cur.description]
    esri_df = pd.DataFrame(results, columns=colnames)

    query = "SELECT * FROM id_index;"
    cur.execute(query)
    results = cur.fetchall()
    conn.commit()
    colnames = [desc[0] for desc in cur.description]
    idx_df = pd.DataFrame(results, columns=colnames)
    idx_df.drop(['index', 'tract_id', 'state_id', 'state_name'], axis=1, inplace=True)

    new_df = esri_df.copy()
    # new_df = new_df[['state_name', 'name', 'state_fips', 'fips', 'wkb_geometry', 'sqmi']]
    new_df.rename({"state_fips": "state_id"}, axis=1, inplace=True)
    new_df['county_id'] = new_df['fips'].astype(int)
    new_df.drop(['wkb_geometry', 'shape_area', 'shape_length', 'name'], inplace=True, axis=1)
    print(new_df.shape)
    print(new_df.head(n=200))

    # new_df.to_csv('Output/new_county_geoms.csv')
    # new_df.drop(['county_name'], axis=1, inplace=True)

    merge_df = pd.merge(new_df, idx_df, on='county_id', how='left', validate='one_to_many')
    merge_df.drop_duplicates(inplace=True)
    # merge_df.drop(['state_name_y','name'], axis=1, inplace=True)
    print(merge_df.shape)
    # col5, col6 = st.columns(2)
    # with col5:
    print(merge_df.head(n=150))
    merge_df.to_csv('Output/demographics.csv')
    # with col6:
    #     st.write(merge_df.tail(n=150))


if __name__ == '__main__':
    # latest_data_census_tracts('California', ['Contra Costa County'],
    #                           ['household_technology_availability', 'disability_status'])
    # args = {k: v for k, v in [i.split('=') for i in sys.argv[1:] if '=' in i]}
    # table = args.get('--table', None)
    # output_format = args.get('--output', None)
    #
    # if table:
    #     df = latest_data_single_table(table)
    # else:
    #     df = latest_data_all_tables()
    #
    # if output_format:
    #     if table:
    #         path = output_data(df, table_name=table, ext=output_format)
    #     else:
    #         path = output_data(df, ext=output_format)
    # else:
    #     if table:
    #         path = output_data(df, table_name=table)
    #     else:
    #         path = output_data(df)
    #
    # print('Successful query returned. Output at {}.'.format(path))
    test_new_counties()
    # df=pd.read_csv('Output/clean_counties.csv')
    # print('writing....')
    # write_table(df,'county_geoms')
    # df=pd.read_csv('Output/demographics.csv')
    # print('writing....')
    # write_table(df,'county_demographics')
