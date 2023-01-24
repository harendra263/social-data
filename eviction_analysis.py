import pandas as pd
import streamlit as st

import analysis
import queries
import utils
import visualization
from constants import STATES


def eviction_UI():
    st.title('Eviction Analysis')
    with st.expander("About"):
        st.write(
            """
            This is an analysis based on work we did with [New Story](https://newstorycharity.org/) to help them
             make decisions about how to distribute direct aid to families to help keep people in their homes. The 
             end result of this analysis is something we call 'Relative Risk.' This value is a synthesis of the 
             sociodemographic characteristics of a county that can be used to compare counties against each other. 
             It is *not* a measure of objective risk.

             This analysis uses *total population* in its current iteration, not percentage values. This is to 
             capture that counties with more people represent more potential risk than smaller counties. Values from 
             a variety of data sources are normalized and then combined to represent the Relative Risk Index. 

             In addition to the Relative Risk calculation, we've also built calculations to estimate the cost to 
             avoid evictions by providing direct aid for a subset of the community.  

             As with any analysis that relies on public data, we should acknowledge that the underlying data is not 
             perfect. Public data has the potential to continue and exacerbate the under-representation of 
             certain groups. This data should not be equated with the ground truth of the conditions in a community. 
             You can read more about how we think about public data [here](https://medium.com/swlh/digital-government-and-data-theater-a-very-real-cause-of-very-fake-news-fe23c0dfa0a2).

             You can read more about the data and calculations happening here on our [GitHub](https://github.com/arup-group/social-data).
            """
        )

    task = st.selectbox('What type of analysis are you doing?',
                        ['Single County', 'Multiple Counties', 'State', 'National'], 1)
    metro_areas, locations = queries.load_distributions()

    if task in ['Single County', '']:
        if res := st.text_input(
            'Enter the county and state (ie: Jefferson County, Colorado):'
        ):
            res = res.strip().split(',')
            county = res[0].strip()
            state = res[1].strip()
            if county and state:
                df = queries.get_county_data(state, [county])
                if st.checkbox('Show raw data'):
                    st.subheader('Raw Data')
                    st.dataframe(df)
                    st.download_button('Download raw data', utils.to_excel(df), file_name=f'{county}_data.xlsx')

                with st.expander('Cost to avoid evictions'):
                    st.write("""
                            The cost to avoid evictions is defined as the cost to a municipality or other entity if it was to pay 
                            people's rent directly. In this calculation, we assume a distribution of housing stock (0 bedroom to 4+ bedroom)
                             based on Census data. You can select which distribution to use that is most similar to the community that you're analyzing. 

                             We default to using Fair Market Rents for this calculation, but you can use the Median value as well. 

                             We also assume that only the burdened population is being considered for support, but not every burdened 
                             person will receive support. You can adjust the percentage of the burdened population to consider.

                             The reported value is the *monthly cost* to an entity to support the chosen housing distribution, rent type, and percent of the burdened population. 

                             This is only an estimate, and should not be used for detailed planning or policy making.
                            """)

                if st.checkbox('Do cost to avoid eviction analysis?'):
                    evictions_cost_df = cost_of_evictions(df, metro_areas, locations)
                    st.download_button('Download cost data', utils.to_excel(evictions_cost_df),
                                       file_name=f'{county}_cost_data.xlsx')

            else:
                st.error('Enter a valid county and state, separated by a comma')
                st.stop()

    elif task == 'Multiple Counties':
        state = st.selectbox("Select a state", STATES).strip()
        county_list = queries.all_counties_query()
        county_list = county_list[county_list['state_name'] == state]['county_name'].to_list()
        counties = st.multiselect('Please specify one or more counties', county_list)
        if counties := [_.strip().lower() for _ in counties]:
            df = queries.get_county_data(state, counties)

            if st.checkbox('Show raw data'):
                st.subheader('Raw Data')
                st.dataframe(df)
                st.download_button('Download raw data', utils.to_excel(df), file_name=f'{state}_data.xlsx')

            with st.expander('Cost to avoid evictions'):
                st.write("""
                        The cost to avoid evictions is defined as the cost to a municipality or other entity if it was to pay 
                        people's rent directly. In this calculation, we assume a distribution of housing stock (0 bedroom to 4+ bedroom)
                         based on Census data. You can select which distribution to use that is most similar to the community that you're analyzing. 

                         We default to using Fair Market Rents for this calculation, but you can use the Median value as well. 

                         We also assume that only the burdened population is being considered for support, but not every burdened 
                         person will receive support. You can adjust the percentage of the burdened population to consider.

                         The reported value is the *monthly cost* to an entity to support the chosen housing distribution, rent type, and percent of the burdened population. 

                         This is only an estimate, and should not be used for detailed planning or policy making.
                        """)

            if st.checkbox('Do cost to avoid eviction analysis?'):
                evictions_cost_df = cost_of_evictions(df, metro_areas, locations)
                st.download_button('Download cost data', utils.to_excel(evictions_cost_df),
                                   file_name=f'{state}_cost_data.xlsx')

            ranks = relative_risk_ranking(df, state)
            eviction_visualizations(ranks, state)
        else:
            st.error('Select counties to analyze')
            st.stop()
    elif task == 'State':
        state = st.selectbox("Select a state", STATES).strip()
        df = queries.get_county_data(state)

        if st.checkbox('Show raw data'):
            st.subheader('Raw Data')
            st.dataframe(df)
            st.download_button('Download raw data', utils.to_excel(df), file_name=f'{state}_data.xlsx')

        with st.expander('Cost to avoid evictions'):
            st.write("""
                    The cost to avoid evictions is defined as the cost to a municipality or other entity if it was to pay 
                    people's rent directly. In this calculation, we assume a distribution of housing stock (0 bedroom to 4+ bedroom)
                     based on Census data. You can select which distribution to use that is most similar to the community that you're analyzing. 

                     We default to using Fair Market Rents for this calculation, but you can use the Median value as well. 

                     We also assume that only the burdened population is being considered for support, but not every burdened 
                     person will receive support. You can adjust the percentage of the burdened population to consider.

                     The reported value is the *monthly cost* to an entity to support the chosen housing distribution, rent type, and percent of the burdened population. 

                     This is only an estimate, and should not be used for detailed planning or policy making.
                    """)

        if st.checkbox('Do cost to avoid eviction analysis?'):
            evictions_cost_df = cost_of_evictions(df, metro_areas, locations)
            st.download_button('Download raw data', utils.to_excel(evictions_cost_df),
                               file_name=f'{state}_cost_data.xlsx')

        ranks = relative_risk_ranking(df, state)
        eviction_visualizations(ranks, state)

    elif task == 'National':
        st.info('Analysis for every county in the US can take a while! Please wait...')
        with st.expander("Caveats"):
            st.write(
                "There are some counties that don't show up in this analysis because of how they are named or because data is missing. We are aware of this issue.")

        frames = []
        for state in STATES:
            df = queries.get_county_data(state)
            frames.append(df)
        natl_df = pd.concat(frames)
        if st.checkbox('Show raw data'):
            st.subheader('Raw Data')
            st.dataframe(natl_df)
            st.download_button(
                'Download raw data',
                utils.to_excel(natl_df),
                file_name='national_data.xlsx',
            )
        with st.expander('Cost to avoid evictions'):
            st.write("""
                    The cost to avoid evictions is defined as the cost to a municipality or other entity if it was to pay 
                    people's rent directly. In this calculation, we assume a distribution of housing stock (0 bedroom to 4+ bedroom)
                     based on Census data. You can select which distribution to use that is most similar to the community that you're analyzing. 

                     We default to using Fair Market Rents for this calculation, but you can use the Median value as well. 

                     We also assume that only the burdened population is being considered for support, but not every burdened 
                     person will receive support. You can adjust the percentage of the burdened population to consider.

                     The reported value is the *monthly cost* to an entity to support the chosen housing distribution, rent type, and percent of the burdened population. 

                     This is only an estimate, and should not be used for detailed planning or policy making.
                    """)

        if st.checkbox('Do cost to avoid eviction analysis?'):
            evictions_cost_df = cost_of_evictions(natl_df, metro_areas, locations)
            st.download_button(
                'Download cost data',
                utils.to_excel(evictions_cost_df),
                file_name='national_cost_data.xlsx',
            )

        ranks = relative_risk_ranking(natl_df, 'National')
        eviction_visualizations(ranks, 'National')


def eviction_visualizations(df: pd.DataFrame, state: str = None):
    if not state:
        return
    temp = df.copy()
    temp.reset_index(inplace=True)
    counties = temp['County Name'].to_list()
    if state.lower() != 'national':
        geo_df = queries.get_county_geoms(counties, state)
    else:
        frames = [queries.get_county_geoms(counties, s) for s in STATES]
        geo_df = pd.concat(frames)

    visualization.make_map(geo_df, temp, 'Relative Risk')


def relative_risk_ranking(df: pd.DataFrame, label: str) -> pd.DataFrame:
    st.subheader('Relative Risk')
    st.write('Relative Risk is a metric to compare the potential risk of eviction between multiple counties. '
             'Values are normalized and combined to create the Relative Risk index. '
             'You can add or remove features, or just use our defaults which we developed working with our partners.')
    columns_to_consider = st.multiselect('Features to consider in Relative Risk',
                                         list(set(df.columns) - {'county_id', 'state_id', 'cnty_fips', 'fips',
                                                                 'pop_sqmi', 'pop2010', 'pop2010_sqmi'}),
                                         ["burdened_households",
                                          "income_inequality",
                                          "population_below_poverty",
                                          "single_parent_households",
                                          "unemployment_rate",
                                          "VulnerabilityIndex",
                                          "Housing Units",
                                          "Vacant Units",
                                          "Renter Occupied Units",
                                          "Non-White Population (%)"]) + ['Total Population']
    ranks = analysis.rank_counties(
        df[columns_to_consider], f'{label}_selected_counties'
    ).sort_values(by='Relative Risk', ascending=False)
    ranks['county_id'] = df['county_id']
    ranks['state_id'] = df['state_id']
    st.write('Higher values correspond to more relative risk. Values can be between 0 and 1.')
    st.dataframe(ranks['Relative Risk'])
    st.download_button('Download Relative Risk ranking', utils.to_excel(ranks), file_name=f'{label}_data.xlsx')

    return ranks


def cost_of_evictions(df: pd.DataFrame, metro_areas, locations):
    st.write('You can use either the Fair Market or Median rents in a county for this analysis.')
    rent_type = st.selectbox('Rent Type', ['Fair Market', 'Median'], 0)
    st.write('This calculation is based on the combined rent for 0 bedroom to 4+ bedroom units. The distribution of '
             'housing stock changes around the US, so you can pick a distribution similar to your location or just use '
             'the national average. You can then select a proportion of the rent-burdened population to support.')
    location = st.selectbox('Select a location to assume a housing distribution:', locations)
    distribution = {
        0: float(metro_areas.loc[location, '0_br_pct']),
        1: float(metro_areas.loc[location, '1_br_pct']),
        2: float(metro_areas.loc[location, '2_br_pct']),
        3: float(metro_areas.loc[location, '3_br_pct']),
        4: float(metro_areas.loc[location, '4_br_pct']),
    }
    if st.checkbox('Show distribution (decimal values)'):
        st.write(distribution)

    pct_burdened = st.slider('Percent of Burdened Population to Support', 0, 100, value=50, step=1)

    if rent_type in ['', 'Fair Market']:
        df = analysis.calculate_cost_estimate(df, pct_burdened, rent_type='fmr', distribution=distribution)
    elif rent_type == 'Median':
        df = analysis.calculate_cost_estimate(df, pct_burdened, rent_type='rent50', distribution=distribution)

    cost_df = df.reset_index()
    cost_df.drop(columns=['State'], inplace=True)
    cost_df.set_index('County Name', inplace=True)
    cost_df = cost_df.round(0)
    cost_cols = ['rent50_0', 'rent50_1', 'rent50_2', 'rent50_3', 'rent50_4', 'fmr_0', 'fmr_1', 'fmr_2', 'fmr_3',
                 'fmr_4', 'br_cost_0', 'br_cost_1', 'br_cost_2', 'br_cost_3', 'br_cost_4', 'total_cost',
                 'Renter Occupied Units', 'burdened_households']
    cost_df.drop(list(set(df.columns) - set(cost_cols)), axis=1, inplace=True)
    st.bar_chart(cost_df['total_cost'])
    if st.checkbox('Show cost data'):
        st.write('`fmr_*` represents the fair market rent per unit and `rent_50_*` represents the median rent per unit.'
                 '`br_cost_*` is the total cost for the chosen housing stock distribution and percentage of the'
                 ' burdened population for each type of unit. `total_cost` is sum of the `br_cost_` for each type of'
                 ' housing unit.')
        st.dataframe(cost_df)
    return cost_df
