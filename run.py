import os
import pandas as pd
import streamlit as st

import data_explorer
import eviction_analysis
import equity_explorer
import queries
import analysis
import utils
from constants import STATES

# Pandas options
pd.set_option('max_rows', 25)
pd.set_option('max_columns', 12)
pd.set_option('expand_frame_repr', True)
pd.set_option('large_repr', 'truncate')
pd.options.display.float_format = '{:.2f}'.format

PAGES = [
    'Data Explorer',
    'Equity Explorer',
    'Eviction Analysis'
]

def print_summary(df: pd.DataFrame, output: str):
    print('*** Results ***')
    if 'Rank' in df.columns:
        print('* Shown in order by overall priority, higher values mean higher priority.')
        df.sort_values('Rank', ascending=False, inplace=True)
        print(df['Rank'])
        print('Normalized analysis data is located at {o}'.format(o=output[:-5]) + '_overall_vulnerability.xlsx')
    elif len(df) > 1:
        print('* Shown in order by relative risk, higher values mean higher relative risk.')
        df.sort_values('Relative Risk', ascending=False, inplace=True)
        print(df['Relative Risk'])
        print('Normalized analysis data is located at {o}'.format(o=output[:-5]) + '_overall_vulnerability.xlsx')
    else:
        print('Fetched single county data')

    print('Raw fetched data is located at {o}'.format(o=output))
    print('Done!')


def run_shell() -> pd.DataFrame:
    task = input(
        'Analyze a single county (1), multiple counties (2), all the counties in a state (3), or a nation-wide analysis (4)? [default: 1]') \
        .strip()
    if task in ['1', '']:
        res = input('Enter the county and state to analyze (ie: Jefferson County, Colorado):')
        res = res.strip().split(',')
        cost_of_evictions = input(
            'Run an analysis to estimate the cost to avoid evictions? (Y/n) ')
        cost_of_evictions.strip()
        county = res[0].strip().lower()
        state = res[1].strip().lower()
        df = queries.get_county_data(state, [county])

        if cost_of_evictions in ['y', '']:
            df = analysis.calculate_cost_estimate(df, rent_type='fmr')

        utils.output_table(df, 'Output/' + county.capitalize() + '.xlsx')
        print_summary(df, 'Output/' + county.capitalize() + '.xlsx')
        return df
    elif task == '2':
        state = input("Which state are you looking for? (ie: California)").strip()
        counties = input('Please specify one or more counties, separated by commas.').strip().split(',')
        df = queries.get_county_data(state, counties)
        cost_of_evictions = input(
            'Run an analysis to estimate the cost to avoid evictions? (Y/n) ')
        if cost_of_evictions in ['y', '']:
            df = analysis.calculate_cost_estimate(df, rent_type='fmr')

        utils.output_table(df, 'Output/' + state + '_selected_counties.xlsx')
        analysis_df = analysis.rank_counties(df, state + '_selected_counties')
        print_summary(analysis_df, 'Output/' + state + '_selected_counties.xlsx')
        return df
    elif task == '3':
        state = input("Which state are you looking for? (ie: California)").strip()
        df = queries.get_county_data(state)
        cost_of_evictions = input(
            'Run an analysis to estimate the cost to avoid evictions? (Y/n) ')
        if cost_of_evictions in ['y', '']:
            df = analysis.calculate_cost_estimate(df, rent_type='fmr')

        utils.output_table(df, 'Output/' + state + '.xlsx')
        analysis_df = analysis.rank_counties(df, state)
        print_summary(analysis_df, 'Output/' + state + '.xlsx')
        temp = df.copy()
        temp.reset_index(inplace=True)
        counties = temp['County Name'].to_list()
        geom = queries.get_county_geoms(counties, state.lower())
        df = df.merge(geom, on='County Name', how='outer')
        return df
    elif task == '4':
        frames = []
        for state in STATES:
            df = queries.get_county_data(state)
            frames.append(df)
        natl_df = pd.concat(frames)
        cost_of_evictions = input(
            'Run an analysis to estimate the cost to avoid evictions (Y/n) ')
        if cost_of_evictions in ['y', '']:
            df = analysis.calculate_cost_estimate(natl_df, rent_type='fmr')

        utils.output_table(natl_df, 'Output/US_national.xlsx')
        analysis_df = analysis.rank_counties(natl_df, 'US_national')
        print_summary(analysis_df, 'Output/US_national.xlsx')
        return df
    else:
        raise Exception('INVALID INPUT! Enter a valid task number.')


def run_UI():
    st.set_page_config(
        page_title="Arup Social Data",
        page_icon="🏠",
        initial_sidebar_state="expanded",
        menu_items={
            'Report a bug': "https://github.com/arup-group/social-data/issues/new/choose",
            'About': """            
         If you're seeing this, we would love your contribution! If you find bugs, please reach out or create an issue on our 
         [GitHub](https://github.com/arup-group/social-data) repository. If you find that this interface doesn't do what you need it to, you can create an feature request 
         at our repository or better yet, contribute a pull request of your own. You can reach out to the team on LinkedIn or 
         Twitter if you have questions or feedback.
    
        More documentation and contribution details are at our [GitHub Repository](https://github.com/arup-group/social-data).
        
         This app is the result of hard work by our team:
        - [Jared Stock 🐦](https://twitter.com/jaredstock) 
        - [Angela Wilson 🐦](https://twitter.com/AngelaWilson925) (alum)
        - Sam Lustado
        - Lingyi Chen
        - Kevin McGee (alum)
        - Jen Combs
        - Zoe Temco
        - Prashuk Jain (alum)
        - Sanket Shah (alum)


        Special thanks to Julieta Moradei and Kamini Ayer from New Story, Kristin Maun from the city of Tulsa, 
        Emily Walport, Irene Gleeson, and Elizabeth Joyce with Arup's Community Engagment team, and everyone else who has given feedback 
        and helped support this work. Also thanks to the team at Streamlit for their support of this work.

        The analysis and underlying data are provided as-is as an open source project under an [MIT license](https://github.com/arup-group/social-data/blob/master/LICENSE). 

        Made by [Arup](https://www.arup.com/).
        """
        }
    )
    st.sidebar.title('Arup Social Data')
    if st.session_state.page:
        page=st.sidebar.radio('Navigation', PAGES, index=st.session_state.page)
    else:
        page=st.sidebar.radio('Navigation', PAGES, index=1)

    st.experimental_set_query_params(page=page)

    if page == 'Eviction Analysis':
        st.sidebar.write("""
            ## About
            
            The Eviction Analysis tool is targeted at providing data and and context around evictions at the county level. It provides a _Relative Risk Index_, which represents the varying relative risk of eviction in the selected counties. You can also estimate the cost to avoid evictions per month based on the number of people at risk and the cost of rent in the counties selected.  
        """)
        eviction_analysis.eviction_UI()

    elif page == 'Equity Explorer':
        st.sidebar.write("""
            ## About

            The Equity Explorer is a set of Arup-designed analyses to identify vulnerable and historically under-served geographies at the census tract level. The tool provides a transparent, Arup-approved framework for approaching equity and allows users to compare indicators and explore the data for census tracts across the US. Users can also customize a transportation vulnerability index for their specific planning purposes to best understand which areas have the biggest gaps in accessibility and demand. Keep in mind that much of the data comes from the 2019 US Census which has limitations with response rates. 
            
            Please note that this tool is a work in progress. Contact us [here](mailto:shannon.nakamura@arup.com) or consider contributing to our [GitHub](https://github.com/arup-group/social-data) repository with any suggestions or questions.     
        """)
        equity_explorer.census_equity_explorer()
    else:
        st.sidebar.write("""
            ## About

            The Data Explorer is an interface to allow you to explore the data available in our database and do some initial analysis. In total we have over 2 million rows and over 400 unique features with coverage across the 50 US states and expanding to the District of Columbia and Puerto Rico. You can use this interface to combine multiple datasets and export raw data as an Excel file. 
            
            Datasets vary between county and census tract resolution and data may not exist for all counties or tracts. Some features may not work for all states/territories. 
        """)
        st.title("Data Explorer")
        subcol_1, subcol_2 = st.columns(2)
        with subcol_1:
            st.session_state.data_type = st.radio("Data resolution:", ('County Level', 'Census Tracts'), index=0)
        with subcol_2:
            # Todo: implement for census level too
            if st.session_state.data_type =='County Level':
                st.session_state.data_format = st.radio('Data format', ['Raw Values', 'Per Capita', 'Per Square Mile'], 0)

        if st.session_state.data_type == 'County Level':
            data_explorer.county_data_explorer()
        else:
            data_explorer.census_data_explorer()


if __name__ == '__main__':

    if not os.path.exists('Output'):
        os.makedirs('Output')
    if st._is_running_with_streamlit:
        url_params = st.experimental_get_query_params()
        if 'loaded' not in st.session_state:
            if len(url_params.keys()) == 0:
                st.experimental_set_query_params(page='Data Explorer')
                url_params = st.experimental_get_query_params()

            st.session_state.page = PAGES.index(url_params['page'][0])
            st.session_state['data_type'] = 'County Level'
            st.session_state['data_format'] = 'Raw Values'
            st.session_state['loaded'] = False

        run_UI()
    else:
        run_shell()
