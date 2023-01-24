import streamlit as st

import queries
import utils
import visualization
from constants import STATES


def county_data_explorer():
    task = st.selectbox('How much data do you want to look at?', ['Counties', 'State', 'National'], 0)
    state, counties, name, df = None, None, None, None
    if task == 'Counties':
        state = st.selectbox("Select a state", STATES).strip()
        county_df = queries.all_counties_query()
        county_df = county_df[county_df['state_name'] == state]
        county_list = county_df['county_name'].to_list()
        county_list.sort()
        counties = st.multiselect('Please specify one or more counties', county_list)
        # counties = [_.strip().lower() for _ in counties]
        if len(counties) > 0:
            county_ids = county_df.query(f'county_name in {counties}')['county_id'].to_list()
            df = queries.get_county_data(state, county_ids)
            name = f"{state}_county_data"
    elif task == 'State':
        state = st.selectbox("Select a state", STATES).strip()
        df = queries.get_county_data(state)
        name = f"{state}_data"
    elif task == 'National':
        st.info('National analysis can take some time and be difficult to visualize at the moment.')
        df = queries.get_national_county_data()
        name = "national_data"

    if df is not None:
        if st.checkbox('Show raw data'):
            st.subheader('Raw Data')
            tmp_df = df.copy()
            st.caption(str(tmp_df.shape))
            st.dataframe(tmp_df)
            st.download_button('Download raw data', utils.to_excel(df), file_name=f'{name}.xlsx')

        st.write('''### View Feature''')
        temp = df.copy()
        temp.reset_index(inplace=True)
        feature_labels = sorted(
            set(temp.columns)
            - {
                'County Name',
                'State',
                'county_id',
                'state_id',
                'pop10_sqmi',
                'pop2010',
                'fips',
                'cnty_fips',
                'state_fips',
            }
        )
        single_feature = st.selectbox('Feature', feature_labels, 0)

        visualization.make_chart(temp, single_feature, st.session_state.data_format)
        counties = temp['County Name'].to_list()
        if task != 'National':
            geo_df = queries.get_county_geoms(counties, state)
        else:
            county_ids = temp['county_id'].to_list()
            geo_df = queries.get_county_geoms_by_id(county_ids)
        visualization.make_map(geo_df, temp, single_feature, st.session_state.data_format)
        st.write('''
            ### Compare Features
            Select two features to compare on the X and Y axes. Only numerical data can be compared.
            ''')
        col1, col2, col3 = st.columns(3)
        with col1:
            feature_1 = st.selectbox('X Feature', feature_labels, 0)
        with col2:
            feature_2 = st.selectbox('Y Feature', feature_labels, 1)
        with col3:
            scaling_feature = st.selectbox('Scaling Feature', feature_labels, len(feature_labels) - 1)
        if feature_1 and feature_2 and scaling_feature:
            visualization.make_scatter_plot_counties(temp, feature_1, feature_2, scaling_feature, st.session_state.data_format)
        temp.drop(['State', 'County Name', 'county_id'], inplace=True, axis=1)
        visualization.make_correlation_plot(temp, feature_labels)


def census_data_explorer():
    state = st.selectbox("Select a state", STATES).strip()
    county_list = queries.all_counties_query()
    county_list = county_list[county_list['state_name'] == state]['county_name'].to_list()
    county_list.sort()
    counties = st.multiselect('Please a county', ['All'] + county_list)
    tables = st.multiselect('Please specify one or more datasets to view', queries.CENSUS_TABLES)
    tables = [_.strip().lower() for _ in tables]
    tables.sort()

    if tables and len(counties) > 0:
        if 'All' in counties:
            df = queries.latest_data_census_tracts(state, county_list, tables)
        else:
            df = queries.latest_data_census_tracts(state, counties, tables)

        if st.checkbox('Show raw data'):
            st.subheader('Raw Data')
            tmp_df = df.copy()
            st.caption(str(tmp_df.shape))
            tmp_df['geom'] = tmp_df['geom'].astype(str)
            st.dataframe(tmp_df)
            st.download_button('Download raw data', utils.to_excel(df), file_name=f'{state}_data.xlsx')
        if 'state_name' in df.columns:
            df = df.loc[:, ~df.columns.duplicated()]
            df['State'] = df['state_name']
        if 'county_name' in df.columns:
            df = df.loc[:, ~df.columns.duplicated()]
            df['County Name'] = df['county_name']
        df.set_index(['State', 'County Name'], drop=True, inplace=True)
        feature_labels = sorted(
            set(df.columns)
            - {
                'County Name',
                'county_id',
                'index',
                'county_name',
                'Census Tract',
                'geom',
                'state_id',
                'state_name',
                'tract',
            }
        )
        st.write('''
                ### View Feature
                Select a feature to view for each county
                ''')
        single_feature = st.selectbox('Feature', feature_labels, 0)
        geo_df = df.copy()
        df.drop(['geom'], inplace=True, axis=1)
        visualization.make_census_chart(df, single_feature)

        geo_df = geo_df[['geom', 'Census Tract']]
        show_transit=st.checkbox('Show transit lines and stops')
        visualization.make_map(geo_df, df, single_feature, show_transit=show_transit)
        if len(feature_labels) > 2:
            st.write('''
                ### Compare Features
                Select two features to compare on the X and Y axes
                ''')
            col1, col2, col3 = st.columns(3)
            with col1:
                feature_1 = st.selectbox('X Feature', feature_labels, 0)
            with col2:
                feature_2 = st.selectbox('Y Feature', feature_labels, 1)
                with col3:
                    scaling_feature = st.selectbox('Scaling Feature', feature_labels, len(feature_labels) - 1)
            if feature_1 and feature_2:
                visualization.make_scatter_plot_census_tracts(df, feature_1, feature_2, scaling_feature)

        df.drop(list(set(df.columns) - set(feature_labels)), axis=1, inplace=True)
        display_columns = sorted(df.columns)
        visualization.make_correlation_plot(df, display_columns)
