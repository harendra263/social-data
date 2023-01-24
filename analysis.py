import math
import itertools
import pandas as pd
import numpy as np
import sklearn.preprocessing as pre
import streamlit as st

import queries


def percent_to_population(feature: str, name: str, df: pd.DataFrame) -> pd.DataFrame:
    pd.set_option('mode.chained_assignment', None)
    df[name] = (df.loc[:, feature].astype(float) / 100) * df.loc[:, 'Total Population'].astype(float) * 1000
    return df


def cross_features(df: pd.DataFrame) -> pd.DataFrame:
    cols = ['Pop Below Poverty Level', 'Pop Unemployed', 'Income Inequality (Ratio)', 'Non-Home Ownership Pop',
            'Num Burdened Households', 'Num Single Parent Households']
    all_combinations = []
    for r in range(2, 3):
        combinations_list = list(itertools.combinations(cols, r))
        all_combinations += combinations_list
    new_cols = [cross(combo, df) for combo in all_combinations]
    crossed_df = pd.DataFrame(new_cols)
    crossed_df = crossed_df.T
    crossed_df['Mean'] = crossed_df.mean(axis=1)

    return crossed_df


def prepare_analysis_data(df: pd.DataFrame) -> pd.DataFrame:
    temp_df=df.copy()
    cols_to_drop = ['Population Below Poverty Line (%)',
                    'Unemployment Rate (%)',
                    'Burdened Households (%)',
                    'Single Parent Households (%)',
                    'Non-White Population (%)',
                    ]
    for col in list(temp_df.columns):
        if '(%)' in col:
            if col == 'Unemployment Rate (%)':
                temp_df = percent_to_population('Unemployment Rate (%)', 'Population Unemployed', temp_df)
            else:
                temp_df = percent_to_population(col, col.replace(' (%)', ''), temp_df)

    if 'Policy Value' in list(temp_df.columns) or 'Countdown' in list(temp_df.columns):
        temp_df = temp_df.drop(['Policy Value', 'Countdown'], axis=1)

    for col in cols_to_drop:
        try:
            temp_df.drop([col], axis=1, inplace=True)
        except:
            pass
    return temp_df


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    scaler = pre.MaxAbsScaler()
    return pd.DataFrame(
        scaler.fit_transform(df), index=df.index, columns=df.columns
    )


def normalize_column(df: pd.DataFrame, col: str) -> pd.DataFrame:
    scaler = pre.MaxAbsScaler()
    df[col] = scaler.fit_transform(df[col].values.reshape(-1, 1))

    return df


def normalize_percent(percent: float) -> float:
    return percent / 100


def cross(columns: tuple, df: pd.DataFrame) -> pd.Series:
    columns = list(columns)
    new_col = '_X_'.join(columns)
    return pd.Series(df[columns].product(axis=1), name=new_col).abs()


def priority_indicator(socioeconomic_index: float, policy_index: float, time_left: int = 1) -> float:
    time_left = max(time_left, 1)
    return socioeconomic_index * (1 - policy_index) / math.sqrt(time_left)


def rank_counties(df: pd.DataFrame, label: str) -> pd.DataFrame:
    analysis_df = prepare_analysis_data(df)
    analysis_df = normalize(analysis_df)

    # crossed = cross_features(analysis_df)
    # analysis_df['Crossed'] = crossed['Mean']
    # analysis_df = normalize_column(analysis_df, 'Crossed')

    analysis_df['Relative Risk'] = analysis_df.sum(axis=1)
    max_sum = analysis_df['Relative Risk'].max()
    analysis_df['Relative Risk'] = (analysis_df['Relative Risk'] / max_sum)

    if 'Policy Value' in list(df.columns):
        analysis_df['Policy Value'] = df['Policy Value']
        analysis_df['Countdown'] = df['Countdown']
        analysis_df['Rank'] = analysis_df.apply(
            lambda x: priority_indicator(x['Relative Risk'], x['Policy Value'], x['Countdown']), axis=1
        )

    analysis_df.to_excel(f'Output/{label}_overall_vulnerability.xlsx')

    return analysis_df


def calculate_cost_estimate(df: pd.DataFrame, pct_burdened: float, distribution: dict,
                            rent_type: str = 'fmr') -> pd.DataFrame:
    if rent_type == 'fmr':
        cost_df = queries.static_data_single_table('fair_market_rents_new', queries.STATIC_COLUMNS['fair_market_rents'])
    elif rent_type == 'rent50':
        cost_df = queries.static_data_single_table('median_rents_new', queries.STATIC_COLUMNS['median_rents'])


    df = df.reset_index().merge(cost_df, how="left", on='county_id').set_index(['State', 'County Name'])

    df['br_cost_0'] = distribution[0] * df[f'{rent_type}_0'] * (df['Renter Occupied Units']) * (df['burdened_households'] / 100) * (pct_burdened / 100)
    df['br_cost_1'] = distribution[1] * df[f'{rent_type}_1'] * (df['Renter Occupied Units']) * (df['burdened_households'] / 100) * (pct_burdened / 100)
    df['br_cost_2'] = distribution[2] * df[f'{rent_type}_2'] * (df['Renter Occupied Units']) * (df['burdened_households'] / 100) * (pct_burdened / 100)
    df['br_cost_3'] = distribution[3] * df[f'{rent_type}_3'] * (df['Renter Occupied Units']) * (df['burdened_households'] / 100) * (pct_burdened / 100)
    df['br_cost_4'] = distribution[4] * df[f'{rent_type}_4'] * (df['Renter Occupied Units']) * (df['burdened_households'] / 100) * (pct_burdened / 100)
    df['total_cost'] = np.sum([df['br_cost_0'], df['br_cost_1'], df['br_cost_2'], df['br_cost_3'], df['br_cost_4']], axis=0)
    return df


def cost_of_evictions(df, metro_areas, locations):
    rent_type = st.selectbox('Rent Type', ['Fair Market', 'Median'])
    location = st.selectbox('Select a location to assume a housing distribution:', locations)
    distribution = {
        0: float(metro_areas.loc[location, '0_br_pct']),
        1: float(metro_areas.loc[location, '1_br_pct']),
        2: float(metro_areas.loc[location, '2_br_pct']),
        3: float(metro_areas.loc[location, '3_br_pct']),
        4: float(metro_areas.loc[location, '4_br_pct']),
    }

    pct_burdened = st.slider('Percent of Burdened Population to Support', 0, 100, value=50, step=1)

    if rent_type in ['', 'Fair Market']:
        df = calculate_cost_estimate(df, pct_burdened, rent_type='fmr', distribution=distribution)
    elif rent_type == 'Median':
        df = calculate_cost_estimate(df, pct_burdened, rent_type='rent50', distribution=distribution)

    cost_df = df.reset_index()
    cost_df.drop(columns=['State'], inplace=True)
    cost_df.set_index('County Name', inplace=True)

    st.bar_chart(cost_df['total_cost'])
    return cost_df
