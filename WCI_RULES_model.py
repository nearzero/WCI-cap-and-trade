#!/usr/bin/env python
# coding: utf-8

# # <span style="color:DarkBlue">WCI-RULES: An open-source model of the Western Climate Initiative cap-and-trade program</span>
# <img src="https://storage.googleapis.com/wci_model_online_file_hosting/Near_Zero_logo_tiny.jpg" alt="[Near Zero logo]" align="right" style="width: 200px; padding:20px"/>
# 
# ## Developed by [Near Zero](http://nearzero.org)
# 
# This model simulates the supply-demand balance of the Western Climate Initiative cap-and-trade program, jointly operated by California and Québec.
# 
# ---
# 
# © Copyright 2019 by [Near Zero](http://nearzero.org). This work is licensed under a [Creative Commons Attribution-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-sa/4.0/).
# 
# Mason Inman (minman@nearzero.org) is the project manager and technical lead for the development of this model.
# 
# The model is open source, released under the Creative Commons license above, and is written in Python, including use of the library [Pandas](https://pandas.pydata.org/). The online user interface is built using [Jupyter](https://jupyter.org/), with figures using [Bokeh](http://bokeh.pydata.org/), and hosted online through [Binder](https://mybinder.org/).
# 
# On Github, see the [model code](https://github.com/nearzero/WCI-cap-and-trade) and [release notes](https://github.com/nearzero/WCI-cap-and-trade/releases), and [model documentation](https://github.com/nearzero/WCI-cap-and-trade/blob/master/documentation.docx?raw=true).
# 
# Near Zero gratefully acknowledges support for this work from the Energy Foundation, grant number G-1804-27647. Near Zero is solely responsible for the content. The model, its results, and its documentation are for informational purposes only and do not constitute investment advice.
# 
# **About Near Zero**: Near Zero is a non-profit environmental research organization based at the Carnegie Institution for Science on the Stanford University campus. Near Zero provides credible, impartial, and actionable assessment with the goal of cutting greenhouse gas emissions to near zero.

# # IMPORT LIBRARIES

# In[ ]:


import ipywidgets as widgets
from IPython.core.display import display # display used for widgets and for hiding code cells
from IPython.display import clear_output, Javascript # Javascript is for csv save


# In[ ]:


# define class Progress_bar
class Progress_bar_loading:
    bar = ""    

    def __init__(self, wid):
        self.wid = wid # object will be instantiated using iPython widget as wid

    def create_progress_bar(wid):
        progress_bar = Progress_bar_loading(wid)
        return progress_bar

# create object
progress_bar_loading = Progress_bar_loading.create_progress_bar(
    widgets.IntProgress(
        value=0, # initialize
        min=0,
        max=4, # from 0 to 3 is 4 steps
        step=1,
        description='Initializing:',
        bar_style='', # 'success', 'info', 'warning', 'danger' or ''
        orientation='horizontal',
    ))

display(progress_bar_loading.wid)


# In[ ]:


progress_bar_loading.wid.value += 1
# print("Importing libraries... ", end='') # potential for progress_bar_loading

import pandas as pd
from pandas.tseries.offsets import *
import numpy as np

import time
import datetime as dt
from datetime import datetime

import os
import inspect # for getting name of current function
import logging


# In[ ]:


import bokeh

from bokeh.plotting import figure, show, output_notebook

from bokeh.models import Legend, Label, Span, Whisker, ColumnDataSource
# Label: used for annotating graphs with "historical" and "projection"
# Span: used for vertical line between historical and projection
# ColumnDataSource: used for formatting data to specify whiskers
# Whisker: used for showing uncertainty range on emissions estimate

from bokeh.layouts import gridplot
from bokeh.palettes import Viridis # note: Viridis is a dict; viridis is a function

# use INLINE if working offline; also might help with Binder loading
from bokeh.resources import INLINE

output_notebook(resources=INLINE, hide_banner=True)
# hide_banner gets rid of message "BokehJS ... successfully loaded"


# ## KEY TO MODEL METADATA
# 
# **Account name (acct_name):**
# * 'alloc_hold': Allocation Holding Accounts (jurisdiction)
#   * government accounts in which all allowances are initially created from the annual budgets (aka allocations)
# * 'ann_alloc_hold': Annual Allocation Holding Accounts (private)
#   * account in which allocations for entities are placed temporarily
# * 'APCR_acct': Allowance Price Containment Reserve Accounts (jurisdiction)
#   * account that holds reserve allowances set aside by regulations, or later transferred into this account (e.g., CA allowances that remain unsold > 24 months)
# * 'auct_hold': Auction Holding Account (jurisdiction)
#   * account that holds allowances slated to become available at auction, or that have been available at auction and went unsold
# * 'gen_acct': General Account, aka General Holding Account (private)
#   * private entities' accounts in which allowances purchased at auction, or distributed for allocations
# * 'limited_use': Limited Use Holding Account (private)
#   * account that holds allowances to be consigned to auction, prior to when they are available at auction
# * 'retirement': Retirement Account (jurisdiction)
#   * holds allowances retired for compliance or other purposes (e.g., to compensate for EIM Outstanding Emissions, for unfulfilled obligations due to bankruptcy, or for net flow of allowances from ON)
# * 'VRE_acct': Voluntary Renewable Electricity Account (jurisdiction)
#   * holds allowances set aside for Voluntary Renewable Electricity program
#   
# **Jurisdiction (juris):**
# * 'CA': allowances created by CA from the annual budgets (aka caps)
# * 'QC': allowances created by QC from the annual budgets (aka caps), or in addition to the caps (Early Action allowances)
# * 'ON': used for tracking the net flow of allowances to CA-QC entities, after ON withdrawal
# 
# **Auction type (auct_type):**
# * 'current': allowances for current auctions
#   * this includes allowances of "current vintage," with vintage equal to the calendar year
#   * also includes redesignated and reintroduced allowances, which may have vintages earlier than the calendar year
# * 'advance': allowances for advance auctions, with vintages 3 years later than the calendar year
# * 'reserve': allowances set aside for APCR
# * 'n/a': default setting, when no other auction type applies
# 
# **Instrument category (inst_cat):**
# * 'alloc_[YEAR]': allocated allowances for QC in the stated year
# * 'alloc_[YEAR]_APCR': allocated allowances for QC in the stated year, from APCR account
# * 'QC_alloc_set_aside': allowances set aside for QC allocation true-ups (25% of the initial estimated total)
# * 'APCR': allowances placed into the Allowance Price Containment Reserve (APCR) account
#   * APCR allowances may be sold in reserve sales or, for QC, distributed in limited quantities for allocations
# * 'bankruptcy': allowances retired to compensate for unfufilled obligations due to bankruptcy
# * 'CA': allowances that originate as CA state-owned, and later can be either allocated or sold at auction
#   * used to distinguish from consignment allowances (which have juris 'CA', and inst_cat 'consign')
# * 'CA_alloc': allowances allocated to CA entities
# * 'cap': state-owned allowances created initially with this inst_cat; later assigned other values for inst_cat
# * 'consign': allowances consiged to auction by utilities (either electricity or natural gas)
# * 'early_action': QC Early Action Allowances, distributed in addition to the allowances created under the cap
# * 'EIM_retire': allowances retired to compensate for Energy Imbalance Market Outstanding Emissions
# * 'elec_POU_not_consign': allocations to electricity distribution POUs that they opted to not consign to auction
# * 'industrial_etc_alloc': allowances allocated to industrial emitters, and other smaller, miscellaneous allocations
# * 'nat_gas_not_consign': allocations to natural gas distribution utilities that they opted to not consign to auction
# * 'net_flow_ON_to_CA': allowances in addition to those from the CA & QC budgets, which were left in WCI after ON withdrawal, and which CA took responsibility for
# * 'net_flow_ON_to_QC': same as 'net_flow_ON_to_CA,' but which QC took responsibility for
# * 'retired_for_ON': allowances retired in 2019 to compensate for net flow after ON withdrawal
# * 'QC': allowances that originate as QC state-owned, and later can be either allocated or sold at auction
# * 'VRE_account': allowances set aside from caps for Voluntary Renewable Electricity (VRE) program
# 
# **Vintage (vintage):**
# * years 2013-2030: normal allowances are each assigned a vintage in this range on creation
# * year 2199: used in the model to indicate Early Action allowances (a type of non-vintage allowance)
# * year 2200: used in the model to indicate Allowance Price Containment Reserve (APCR) allowances, a type of non-vintage allowance
# 
# **Newness (newness):**
# * 'n/a': default value, when other values don't apply
# * 'new': allowances never before available at auction
# * 'redes': allowances redesignated to later auction, excluding those reintroduced (see below)
#   * can be consignment allowances unsold in one quarterly auction, redesignated to next quarterly auction
#   * can be state-owned allowances unsold in one quarterly advance auction, redesignated to a later advance auction
# * 'reintro': state-owned that previously went unsold in current auction and are "reintroduced" to later auctions
# 
# **Status (status):**
# * 'available' (available for sale at auction)
# * 'deficit': used to record allowances that are required to be auctioned to match historical records, but when there are insufficient allowances of the specified vintage remaining in government holding accounts
# * 'n/a': default setting, when none of the other settings for status apply
# * 'not_avail': not available through auction
#   * includes allowances in government holding accounts that may be available in the future
# * 'sold': allowances sold at auction
# * 'unsold': allowances available at auction, but did not sell
# 
# **Date (date_level):**
# * for allowances to be auctioned:
#   * date_level is the future date in which they are scheduled to be auctioned
# * for allowances being auctioned, or already available at auction:
#   * date_level is the latest date in which they were available at auction
# * for allocations:
#   * date_level is the date in which they were distributed
# * for deficits: 
# * for retirements (i.e., VRE):
#   * date_level is the date in which they were retired
#   
# **Unsold date initial (unsold_di):**
# * dates between 2012Q4 and 2030Q4: used to indicate the first date in which allowances went unsold at auction
# * 2200Q1: default value; used to indicate that allowances never went unsold at auction
# 
# **Unsold date latest (unsold_dl):**
# * dates between 2012Q4 and 2030Q4: used to indicate the latest date in which allowances went unsold at auction
# * 2200Q1: default value; used to indicate that allowances never went unsold at auction
# 
# **Units (units):**
# * MMTCO2e: million metric tons of CO2-equivalent

# # Create objects
# * Prmt
# * Cq

# In[ ]:


class Prmt():
    """
    Class to create object prmt that has parameters used throughout the model as its attributes.
    """
    
    def __init__(self):
        
        self.model_version = '1.1'
        
        self.run_online_GCP = True # to run model using online version of data input file & CIR, set to True
        
        self.years_not_sold_out = () # initialization; value set by user interface
        self.fract_not_sold = float(0) # initialization; value set by user interface
        
        self.run_tests = True
        self.verbose_log = True
        self.test_failed_msg = 'Test failed!: '   
        
        self.model_results = '/Users/masoninman/Dropbox/cap_and_trade_active_dev_model_results/'

        self.neg_cut_off = 10/1e6 # units MMTCO2e; enter number of allowances (tons CO2e) in numerator
        # doesn't matter whether negative or positive entered here; used with -abs(neg_cut_off)
        self.show_neg_msg = False # if False, fn test_for_negative_values won't print any messages    
        
        self.CA_start_date = pd.to_datetime('2012Q4').to_period('Q') # default
        self.QC_start_date = pd.to_datetime('2013Q4').to_period('Q') # default
        self.CA_end_date = pd.to_datetime('2030Q4').to_period('Q') # default
        self.QC_end_date = pd.to_datetime('2030Q4').to_period('Q') # default
        self.model_end_date = pd.to_datetime('2030Q4').to_period('Q') # default
        
        # generate list of quarters to iterate over (inclusive)
        # range has DateOffset(months=3) at the end, because end of range is not included in the range generated
        self.CA_quarters = pd.date_range(start=self.CA_start_date.to_timestamp(),
                                         end=self.CA_end_date.to_timestamp() + DateOffset(months=3), 
                                         freq='Q').to_period('Q')

        # generate list of quarters to iterate over (inclusive)
        # range has DateOffset(months=3) at the end, because end of range is not included in the range generated
        self.QC_quarters = pd.date_range(start=self.QC_start_date.to_timestamp(),
                                         end=self.QC_end_date.to_timestamp() + DateOffset(months=3), 
                                         freq='Q').to_period('Q')
        
        self.CA_cur_sell_out_counter = pd.Series()
        self.QC_cur_sell_out_counter = pd.Series()
        
        self.NaT_proxy = pd.to_datetime('2200Q1').to_period('Q')
        
        self.standard_MI_names = ['acct_name', 'juris', 'auct_type', 'inst_cat', 'vintage', 'newness', 'status', 
                                  'date_level', 'unsold_di', 'unsold_dl', 'units']
        
        # create empty index; can be used for initializing all dfs
        self.standard_MI_index = pd.MultiIndex(levels=[[]]*len(self.standard_MI_names),
                                               codes=[[]]*len(self.standard_MI_names),
                                               names=self.standard_MI_names)
        
        self.standard_MI_empty = pd.DataFrame(index=self.standard_MI_index, columns=['quant'])
        
        self.CIR_columns = ['gen_comp', 'limited_use', 'VRE_acct', 'A_I_A', 'retirement', 'APCR_acct', 
                            'env_integrity', 'subtotal']
        
        # default based on ARB assumption in Post-2020 Caps report; see func offsets_projection for more information
        self.offset_rate_fract_of_limit_default = 0.75
        
        # to track whether there was a saved auction run
        # initialize as False, and change after initialization run has completed
        self.saved_auction_run_default = False # initialize
        
        # 2019Q2 CIR notes at bottom:                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
        # On June 27, 2019, California retired an equal amount of vintages 2021 through 2030 for a total of 11,340,792 
        # allowances. Québec retired 1,846,175 vintage 2017 allowances from the Auction Account on July 10, 2019.
        self.CA_cap_adj_for_ON_net_flow = 11.340792 # units MMTCO2e
        self.QC_cap_adj_for_ON_net_flow =  1.846175 # units MMTCO2e
        
        # ~~~~~~~~~~~~~~~~~        
        
        # set other variables to be blank; new values will be set below by functions    
        
        self.progress_bar_CA_count = 0 # initialize
        self.progress_bar_QC_count = 0 # initialize
        
        self.input_file = ''
        self.CIR_excel = ''
        
        self.qauct_hist = ''
        self.qauct_new_avail = ''
        self.auction_sales_pcts_all = ''
        
        self.CA_cap_data = ''
        self.EIM_and_bankruptcy = ''
        self.CA_cap = ''
        self.CA_cap_adjustment_factor = '' # value filled in by fn load_input_files
        self.CA_APCR_2013_2020_MI = ''
        self.CA_APCR_2021_2030_Oct2017_MI = ''
        self.CA_APCR_2021_2030_Apr2019_add_MI = ''
        
        self.CA_advance_MI = ''
        self.VRE_reserve_MI = ''

        self.CA_alloc_MI_all = ''
        self.consign_ann_hist = ''
        self.consign_hist_proj_new_avail = ''
        self.bankruptcy_hist_proj = ''
        self.EIM_outstanding = ''

        self.latest_hist_alloc_yr = 0 # placeholder int
        self.latest_hist_consign_yr = 0 # placeholder int
        self.latest_hist_qauct_date = ''
        self.supply_last_hist_yr = 0 # placeholder int
        self.emissions_last_hist_yr = 0 # placeholder int
        self.CA_latest_year_allocated = 0 # placeholder intt
        self.off_proj_first_date = ''
        
        # prmt.latest_hist_aauct_yr is the latest year for which annual auction data can be completely inferred,
        # given allocation data and consignment data above (and known quantities for budgets and reserves)
        # it is set to be the minimum of the years for CA consign, CA alloc, and QC alloc data
        self.latest_hist_aauct_yr = 0 # placeholder int
        
        self.QC_cap = ''
        self.QC_advance_MI = ''
        self.QC_APCR_MI = ''
        self.APCR_alloc_distrib = ''
        self.QC_alloc_hist = ''
        self.QC_alloc_initial = ''
        self.QC_alloc_trueups = ''
        self.QC_alloc_trueups_neg = ''
        self.QC_alloc_full_proj = ''
        
        self.emissions_and_obligations = ''
        self.CA_surrendered = ''
        self.QC_surrendered = ''
        self.CA_QC_obligations_fulfilled_hist = ''
        self.CA_QC_obligations_fulfilled_hist_proj = ''

        self.compliance_events = ''
        self.VRE_retired = ''
        self.CIR_historical = ''
        self.CIR_offsets_q_sums = ''
        
        self.emissions_ann = ''
        self.emissions_ann_CA = ''
        self.emissions_ann_QC = ''
        self.compliance_oblig = '' # becomes df with CA & QC data
        self.supply_ann = ''
        self.offsets_supply_q = ''
        self.offsets_supply_ann = ''
        self.bank_cumul_pos = ''
        self.unsold_auct_hold_cur_sum = ''
        self.gov_holding = ''
        self.gov_plus_private = '' # government holdings + private bank
        self.reserve_PCU_sales_q_hist = '' # # PCU: Price Ceiling Units; set in fn read_reserve_sales_historical
        self.reserve_sales_excl_PCU = '' # PCU: Price Ceiling Units
        self.reserve_accts = ''
        self.PCU_sales_cumul = '' # PCU: Price Ceiling Units
        
        self.net_flow_from_ON = ''
        
        self.fig_em_bank = ''
        self.js_download_of_csv = ''
        self.export_df = ''
        
        self.CA_snaps_end_default_run_end = [] # initialize
        self.QC_snaps_end_default_run_end = [] # initialize
        self.CA_snaps_end_default_run_CIR = [] # initialize
        self.QC_snaps_end_default_run_CIR = [] # initialize
        
        self.snaps_end_Q4 = '' # value filled in by fn load_input_files
        self.snaps_end_Q4_sum = '' # value filled in by fn load_input_files
        
        self.loading_msg_pre_refresh = []
        self.error_msg_post_refresh = []
        
        self.data_input_file_version = '' # value set by fn load_input_files
        
        self.save_timestamp = ''

# ~~~~~~~~~~~~~~~~~~
# create object prmt (instance of class Prmt), after which it can be filled with more entries below
prmt = Prmt()


# In[ ]:


class Cq():
    """
    Create class for tracking the current quarter during a model run.
    
    The current quarter (cq) is an object (instance of class Cq).
    """
    def __init__(self, date):
        self.date = date
        
    def step_to_next_quarter(self):
        if self.date < prmt.model_end_date:
            self.date = (pd.to_datetime(f'{self.date.year}Q{self.date.quarter}') + DateOffset(months=3)
                        ).to_period('Q')
        else:
            pass
        
# create new object qc
cq = Cq(pd.to_datetime('2012Q4').to_period('Q'))


# # LOGGING

# In[ ]:


# start logging
# to save logs, need to update below with the correct strings and selection for the desired directory
# need to make sure the folder already exists, or else logs won't be saved

try:
    if os.getcwd().split('/')[1] == 'Users':
        # then model is running on developer's local computer
        # create logging timestamp
        prmt.save_timestamp = time.strftime('%Y-%m-%d_%H%M', time.localtime())
        
        LOG_PATH = os.getcwd().rsplit('/', 1)[0] + '/WCI model logs'

        logging.basicConfig(filename=f"{LOG_PATH}/WCI-RULES_log_{prmt.save_timestamp}.txt", 
                            filemode='a',  # choices: 'w' or 'a'
                            level=logging.INFO)
    else:
        # don't save log       
        pass
except:
    # don't save log
    pass


# # START OF FUNCTIONS

# ## Functions: Housekeeping
# * multiindex_change
# * convert_ser_to_df_MI
# * convert_ser_to_df_MI_CA_alloc
# * convert_ser_to_df_MI_QC_alloc
# * quarter_period

# In[ ]:


def multiindex_change(df, mapping_dict):    
    """
    Housekeeping function: updates an index level, even when repeated values in the index.
    
    Reason for this:
    Pandas .index.set_levels is limited in how it works, and when there are repeated values in the index level,
    it runs, but with spurious results.
    
    Note: This function does not work on Series, because Pandas doesn't include Series.set_index.

    mapping_dict is dictionary with each key = level_name & each value = ''
    """
    
    if prmt.verbose_log == True:
        try:
            logging.info(f"{inspect.currentframe().f_code.co_name}")
        except:
            logging.info(f"initialization: {inspect.currentframe().f_code.co_name}")

    # get index names before changing anything
    df_index_names = df.index.names
            
    # create empty list (initialization) in which all changed data will be put
    df_level_changed_all = []
    
    for level_name in mapping_dict.keys():
        df_level_changed = df.index.get_level_values(level_name).map(lambda i: mapping_dict[level_name])    
        df.index = df.index.droplevel(level_name)
        
        df_level_changed_all += [df_level_changed]

    # after making changes to all levels in dict
    df = df.set_index(df_level_changed_all, append=True)
    df = df.reorder_levels(df_index_names)
    
    return(df)


# In[ ]:


def convert_ser_to_df_MI(ser):
    """
    Converts certain Series into MultiIndex df. Works for cap, APCR, advance, VRE.
    
    (Now used only in initialization for CA and QC auctions.)
    
    Housekeeping function.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start), for {ser.name}")
    
    df = pd.DataFrame(ser)
    
    if len(df.columns) == 1:
        df.columns = ['quant']
    else:
        print("Error" + "! In convert_cap_to_MI, len(df.columns==1) was False.")
    
    if ser.name.split('_')[0] in ['CA', 'VRE']:
        juris = 'CA'
    elif ser.name.split('_')[0] == 'QC':
        juris = 'QC'
        
    df.index.name = 'vintage'
    df = df.reset_index()

    # default metadata values are for cap
    df['acct_name'] = 'alloc_hold'
    df['juris'] = juris # established above
    df['inst_cat'] = 'cap'
    # vintage already assigned above
    df['auct_type'] = 'n/a'
    df['newness'] = 'n/a'
    df['status'] = 'n/a'
    df['date_level'] = prmt.NaT_proxy
    df['unsold_di'] = prmt.NaT_proxy
    df['unsold_dl'] = prmt.NaT_proxy
    df['units'] = 'MMTCO2e'

    # overwrite metadata for other sets of instruments
    if 'CA_APCR_2013_2020' in ser.name:
        df['acct_name'] = 'APCR_acct'
        df['inst_cat'] = 'APCR'
        df['auct_type'] = 'reserve'    
    elif 'CA_APCR_2021_2030_Oct2017' in ser.name:
        # retain in alloc_hold
        df['inst_cat'] = 'APCR'
        # retain as auct_type = 'reserve', since these allowances can't be sold until put in reserve account
    elif 'CA_APCR_2021_2030_Apr2019_add_MI' in ser.name:
        df['acct_name'] = 'APCR_acct'
        df['inst_cat'] = 'APCR'
        df['auct_type'] = 'reserve'
    elif 'QC_APCR' in ser.name:
        df['acct_name'] = 'APCR_acct'
        df['inst_cat'] = 'APCR'
        df['auct_type'] = 'reserve'
    elif 'advance' in ser.name:
        df['acct_name'] = 'auct_hold'
        df['inst_cat'] = ser.name.split('_')[0] # same as juris
        df['auct_type'] = 'advance'
        df['newness'] = 'new'
        df['status'] = 'not_avail'
    elif 'VRE' in ser.name:
        df['acct_name'] = 'VRE_acct'
        # df['juris'] = 'CA'
        df['inst_cat'] = 'VRE_reserve'
        df['status'] = 'n/a'
    else:
        pass
    
    df = df.set_index(prmt.standard_MI_names)
    return(df)


# In[ ]:


def convert_ser_to_df_MI_CA_alloc(ser):
    """
    Converts certain Series into MultiIndex df. Works for CA allocations.
    
    Housekeeping function.
    """
    
    if prmt.verbose_log == True:
        logging.info(f"{inspect.currentframe().f_code.co_name} (start), for series {ser.name}")
    
    df = pd.DataFrame(ser)
    df.index.name = 'vintage'
    df = df.reset_index()
    
    not_consign_list = ['elec_POU_not_consign', 'nat_gas_not_consign', 'industrial_etc_alloc']

    if ser.name in not_consign_list:
        df['acct_name'] = 'ann_alloc_hold'
        df['auct_type'] = 'n/a'
        df['juris'] = 'CA'
        df = df.rename(columns={'alloc': 'quant'})

    elif ser.name in ['consign_elec_IOU', 'consign_elec_POU', 'consign_nat_gas']:
        df['acct_name'] = 'limited_use'
        df['auct_type'] = 'current'
        df['juris'] = 'CA'
        df = df.rename(columns={'alloc': 'quant'})
        # don't change newness to new, nor status to not_avail, until consign are in auct_hold
        
    else: # closing 'if alloc.name in not_consign_list:'
        print("Error" + "!: Series name is not in either list above.")
        
    # acct_name set above
    df['date_level'] = prmt.NaT_proxy
    # juris set above
    # vintage set above
    df['inst_cat'] = ser.name
    # auct_type set above
    df['newness'] = 'n/a'
    df['status'] = 'n/a'
    df['unsold_di'] = prmt.NaT_proxy
    df['unsold_dl'] = prmt.NaT_proxy
    df['units'] = 'MMTCO2e'
    
    # rename column with quantities of allowances from ser.name to 'quant'
    df = df.rename(columns={ser.name: 'quant'})
    df_MI = df.set_index(prmt.standard_MI_names)

    if prmt.verbose_log == True:
        logging.info(f"{inspect.currentframe().f_code.co_name} (end), for series {ser.name}")
    
    return(df_MI)


# In[ ]:


def convert_ser_to_df_MI_QC_alloc(ser, alloc_type):
    """
    For QC allocations, converts Series into MultiIndex df.
    
    Operates on both full allocations (for set aside) and initial allocations (to prepare to move into gen_acct).
    
    Housekeeping function.
    """
    
    logging.info(f"running {inspect.currentframe().f_code.co_name}")
    
    # TEST: check that 'QC_alloc' is in series name
    if 'QC_alloc' in ser.name:
        pass
    else:
        print(f"{prmt.test_failed_msg} Series name doesn't contain 'QC_alloc'. Wrong series passed?") # for UI
    # END OF TEST
    
    df = pd.DataFrame(ser)
    df.index.name = 'vintage'
    df = df.reset_index()
    
    if alloc_type == 'set_aside':
        df['acct_name'] = 'alloc_hold'
        df['inst_cat'] = 'QC_alloc_set_aside'
        df['date_level'] = prmt.NaT_proxy
    elif alloc_type == 'initial':
        df['acct_name'] = 'gen_acct'
        df['inst_cat'] = f'QC_alloc_{cq.date.year}'
        df['date_level'] = cq.date
    else:
        print(f"{prmt.test_failed_msg} Conversion was neither alloc_type 'set_aside' nor 'initial'.")
    
    df['auct_type'] = 'n/a'
    df['juris'] = 'QC'
    # vintage set above
    
    df['newness'] = 'n/a'
    df['status'] = 'n/a'
    df['unsold_di'] = prmt.NaT_proxy
    df['unsold_dl'] = prmt.NaT_proxy
    df['units'] = 'MMTCO2e'

    df = df.rename(columns={ser.name: 'quant'})

    df = df.set_index(prmt.standard_MI_names)

    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(df)


# In[ ]:


def quarter_period(year_quart):
    """
    Converts string year_quart (i.e., '2013Q4') into datetime quarterly period.
    """
    if prmt.verbose_log == True:
        logging.info(f"running {inspect.currentframe().f_code.co_name}")
    
    if isinstance(year_quart, pd.Period) == True:
        # don't need to change; already formatted as period
        period = year_quart
        
    else:
        period = pd.to_datetime(year_quart).to_period('Q')
    
    return(period)


# ## Functions: Initialization steps
# * load_input_files
# * initialize_CA_cap
# * initialize_CA_APCR
# * initialize_CA_advance
# * initialize_VRE_account
# * get_qauct_hist
# * get_compliance_events
# * late_surrender_adjustment_of_compliance_events
# * get_CIR_data_and_clean
# * clean_CIR_allowances
# * clean_CIR_offsets
# * get_VRE_retired_from_CIR
# * assign_EIM_outstanding
# * assign_bankruptcy_noncompliance
# * read_CA_alloc_data
# * initialize_elec_alloc
# * initialize_nat_gas_alloc
# * initialize_industrial_etc_alloc
# * read_annual_auction_notices
# * create_consign_historical_and_projection_annual
# * consign_upsample_historical_and_projection
#   * create_qauct_new_avail_consign
# * get_QC_inputs
# * get_QC_allocation_data
#   * calculate_QC_alloc_from_APCR__CIR_and_reserve_sales
# * read_emissions_historical_data
# * read_reserve_sales_historical

# In[ ]:


def load_input_files():
    """
    Load the model's data input files:
    * custom input file for the model
    * CARB's quarterly Compliance Instrument Report (CIR)
    
    New with Pandas 0.25: use openpyxl library (instead of xlrd) to read Excel files. 
    (Pandas will make openpyxl the default in the future.)
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    progress_bar_loading.wid.value += 1 # for progress_bar_loading
    
    input_file_name = 'WCI-RULES_data_input_file.xlsx'

    # download input file once from Google Cloud Platform, set as an attribute of object prmt    
    if prmt.run_online_GCP == True:
        input_file_URL = f'https://storage.googleapis.com/wci_model_online_file_hosting/{input_file_name}'
        prmt.input_file = pd.ExcelFile(input_file_URL)
        logging.info(f"read {input_file_name} from URL {input_file_URL}")
    else:
        print("Using local version of data input file.") # for UI
        input_file_path = f'/Users/masoninman/Dropbox/cap_and_trade_active_dev/data/{input_file_name}'
        prmt.input_file = pd.ExcelFile(input_file_path)
        logging.info(f"read {input_file_name} from path {input_file_path}")
          
    # get input file version
    contents_sheet = pd.read_excel(prmt.input_file, sheet_name='contents')

    data_input_file_version = contents_sheet.at[1, 'WCI-RULES model data input file']
    if "input file version" in data_input_file_version:
        data_input_file_version = data_input_file_version.split('input file version ')[1]
        data_input_file_version = data_input_file_version.split(' (')[0]
    else:
        print("Error! Wrong line read from data input file, for the file's version.") # for UI
    
    logging.info(f"version of data input file read: {data_input_file_version}")
    
    prmt.data_input_file_version = data_input_file_version
    
    # TEST: check whether the data input file is for the version of the model being run
    input_file_for_model_version = contents_sheet.at[2, 'WCI-RULES model data input file']
    input_file_for_model_version = input_file_for_model_version.split("version ")[1].split("(")[0]
    if input_file_for_model_version == prmt.model_version:
        pass
    else:
        print(f"Error! Data input file is for model version {input_file_for_model_version}") # for UI
        print(f"Error! (cont.) Currently running model version {prmt.model_version}") # for UI
        logging.info(f"Error! Data input file appears to be for the wrong version of the model.")
    # END OF TEST

    # ~~~~~~~~~~~~~
    # CIR quarterly
    CIR_file_name = 'Compliance_Instrument_Report.xlsx'
    
    # download CIR file once from Google Cloud Platform, set as an attribute of object prmt  
    if prmt.run_online_GCP == True:
        CIR_file_URL = f'https://storage.googleapis.com/wci_model_online_file_hosting/{CIR_file_name}'
        prmt.CIR_excel = pd.ExcelFile(CIR_file_URL)
        CIR_sheet_name_first = pd.ExcelFile(prmt.CIR_excel).sheet_names[0].replace(" ", "")
        logging.info(f"read {CIR_file_name} from URL {CIR_file_URL}, through {CIR_sheet_name_first}")

    else:
        print("Using local version of CIR file.") # for UI
        CIR_file_path = f'/Users/masoninman/Dropbox/cap_and_trade_active_dev/data/{CIR_file_name}'
        prmt.CIR_excel = pd.ExcelFile(CIR_file_path)
        CIR_sheet_name_first = pd.ExcelFile(prmt.CIR_excel).sheet_names[0].replace(" ", "")
        logging.info(f"read {CIR_file_name} from path {CIR_file_path}, through {CIR_sheet_name_first}")
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
# end load_input_files


# In[ ]:


def initialize_CA_cap():
    """
    CA cap quantities from § 95841. Annual Allowance Budgets for Calendar Years 2013-2050:
    * Table 6-1: 2013-2020 California GHG Allowance Budgets
    * Table 6-2: 2021-2031 California GHG Allowance Budgets
    * 2032-2050: equation for post-2031 cap
    """
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (start)")
    
    df = prmt.CA_cap_data[prmt.CA_cap_data['name']=='CA_cap']
    df = df.set_index('year')['data']
    df = df.loc[:2030]  
    
    # convert units from tCO2e to MMtCO2e
    df = df / 1e6
        
    df.name = 'CA_cap'
    
    prmt.CA_cap = df
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (end)")
    # no return
# end of initialize_CA_cap


# In[ ]:


def initialize_CA_APCR():
    """
    Quantities for APCR for budget years 2013-2020 defined as percentage of budget.   
    
    2013-2020 specified in regs § 95870(a):
    * (1) One percent of the allowances from budget years 2013-2014;
    * (2) Four percent of the allowances from budget years 2015-2017; and
    * (3) Seven percent of the allowances from budget years 2018-2020.
    
    2021-2030 quantities specified in regulations § 95871(a) and Table 8-2.
    
    Note that April 2019 regulations have higher quantity for 2021-2030 than specified in Oct 2017 regulations,
    so Table 8-2 changed. Quantity was increased by 2% of budgets for 2026-2030, which totaled ~22.7 M.
    """
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (start)")

    # for 2013-2020: get cap & reserve fraction from input file
    # calculate APCR quantities
    CA_APCR_fraction = prmt.CA_cap_data[prmt.CA_cap_data['name']=='CA_APCR_fraction']
    CA_APCR_fraction = CA_APCR_fraction.set_index('year')['data']
    ser = prmt.CA_cap * CA_APCR_fraction # CA_cap has units MMTCO2e
    ser = ser.loc[2013:2020]
    ser.name = 'CA_APCR_2013_2020'

    prmt.CA_APCR_2013_2020_MI = convert_ser_to_df_MI(ser)
    
    # ~~~~~~~~~~~~~~
    # for 2021-2030: get APCR quantities under old Oct 2017 regulations (§ 95871(a) and Table 8-2)
    ser = prmt.CA_cap_data[prmt.CA_cap_data['name']=='CA_APCR_Oct2017_regs']
    ser = ser.set_index('year')['data']
    
    # convert units from tCO2e to MMtCO2e
    ser = ser / 1e6

    # only keep through 2030
    ser = ser.loc[2021:2030]
    
    ser.name = 'CA_APCR_2021_2030_Oct2017'
    CA_APCR_2021_2030_Oct2017 = ser
    
    prmt.CA_APCR_2021_2030_Oct2017_MI = convert_ser_to_df_MI(CA_APCR_2021_2030_Oct2017)
    
    # ~~~~~~~~~~~~~~
    # for 2021-2031: get APCR quantities from input file (for Apr 2019 regulations)
    ser = prmt.CA_cap_data[prmt.CA_cap_data['name']=='CA_APCR_Apr2019_regs']
    ser = ser.set_index('year')['data']
    
    # convert units from tCO2e to MMtCO2e
    ser = ser / 1e6

    # only keep through 2030
    ser = ser.loc[2021:2030]
    
    # calculate additional quantities in Apr 2019 regs, above what was in Oct 2017 regs
    ser = ser - CA_APCR_2021_2030_Oct2017
    
    ser.name = 'CA_APCR_2021_2030_Apr2019_add_MI'
    CA_APCR_2021_2030_Apr2019_add_MI = ser
    
    prmt.CA_APCR_2021_2030_Apr2019_add_MI = convert_ser_to_df_MI(ser)  
    # ~~~~~~~~~~~~~~
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (end)")
    
    # no return
# end of initialize_CA_APCR


# In[ ]:


def initialize_CA_advance():
    """
    Fraction of CA cap that is set aside for advance, as defined in regulations.
    
    For 2013-2020: § 95870(b)
    For 2021-2030: § 95871(b)
    
    """
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (start)")
    
    CA_cap = prmt.CA_cap
    CA_cap_data = prmt.CA_cap_data
    
    CA_advance_fraction = CA_cap_data[CA_cap_data['name']=='CA_advance_fraction']
    CA_advance_fraction = CA_advance_fraction.set_index('year')['data']

    CA_advance = (CA_cap * CA_advance_fraction).fillna(0)
    CA_advance.name ='CA_advance'

    CA_advance_MI = convert_ser_to_df_MI(CA_advance)
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (end)")

    prmt.CA_advance_MI = CA_advance_MI
    # no return
# end of initialize_CA_advance


# In[ ]:


def initialize_VRE_account():
    """
    Transfers allowances from annual budgets to Voluntary Renewable Electricity (VRE) account.
    """
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (start)")
    
    CA_cap = prmt.CA_cap
    CA_cap_data = prmt.CA_cap_data

    VRE_fraction = CA_cap_data[CA_cap_data['name']=='CA_Voluntary_Renewable_fraction']
    VRE_fraction = VRE_fraction.set_index('year')['data']

    VRE_reserve = CA_cap * VRE_fraction

    for year in range(2021, 2030+1):
        VRE_reserve.at[year] = float(0)

    VRE_reserve.name = 'VRE_reserve'

    VRE_reserve_MI = convert_ser_to_df_MI(VRE_reserve)
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (end)")
    
    prmt.VRE_reserve_MI = VRE_reserve_MI
    # no return
# end of initialize_VRE_account


# In[ ]:


def get_qauct_hist():
    """
    Read historical auction data from data input file, for CA and QC.
    """
    
    logging.info(f"initialize: {inspect.currentframe().f_code.co_name} (start)")
    
    # qauct_hist is a full record of auction data, compiled from csvs using another notebook
    qauct_hist = pd.read_excel(prmt.input_file, sheet_name='quarterly auctions')

    # drop any rows with no entries; may be caused by openpyxl
    qauct_hist = qauct_hist.dropna(how='all')
    
    # change units from tCO2e to MMTCO2e
    qauct_hist = qauct_hist.drop('Units', axis=1)
    for col in ['Available', 'Sold']:
        qauct_hist[col] = qauct_hist[col] / 1e6
    
    # rename fields
    qauct_hist = qauct_hist.rename(columns={
        'Market': 'market',
        'Auction date': 'date_level', 
        'Auction type': 'auct_type', 
        'Jurisdiction': 'juris', 
        'Instrument category': 'inst_cat', 
        'Vintage': 'vintage'})
    
    # format 'date_level' as quarter period
    qauct_hist['date_level'] = pd.to_datetime(qauct_hist['date_level']).dt.to_period('Q')
    
    # set object attribute prmt.qauct_hist (df)
    prmt.qauct_hist = qauct_hist
    
    # set object attribute for latest date
    # used in functions: 
    # test_consistency_inputs_CIR_vs_qauct, cur_upsample_avail_state_owned_first_principles, create_auction_tabs
    prmt.latest_hist_qauct_date = prmt.qauct_hist['date_level'].max()
    
    logging.info(f"initialize: {inspect.currentframe().f_code.co_name} (end)")
    
    # no return; function sets object attributes
# end of get_qauct_hist


# In[ ]:


def create_qauct_new_avail_consign():
    """    
    Out of all consigned allowances, calculate which are redesignated, and therefore which are newly available.
    
    Draws on data from historical auction summary result reports.
    
    For consignment, any unsold in one quarter are always redesignated to auction in the following quarter.
    
    """
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (start)")
    
    # get historical data for quarterly auctions; 
    # filter to keep only consignment allowances
    df = prmt.qauct_hist.copy()
    df = df.loc[df['inst_cat']=='consign']

    # calculate unsold
    df['Unsold'] = df['Available'] - df['Sold']
    
    # exclude an anomaly: 9,301 allowances of vintage 2014 available (and sold) in 2017Q1 auction
    mask1 = df['vintage'] == 2014
    mask2 = df['date_level'] == quarter_period('2017Q1')
    mask = (mask1) & (mask2)
    # exclude masked row
    df = df.loc[~mask]

    # assign redesignated allowances: 
    # all consignment unsold in one quarter are necessarily redesignated to the following quarter's auction
    new_rows_list = [] # initialize
    for row in df.index:
        # write values to dictionary for the next quarter
        new_row_dict = {
            'market': df.at[row, 'market'], 
            'date_level': (pd.to_datetime(df.at[row, 'date_level'].to_timestamp()) + DateOffset(months=3)
                          ).to_period('Q'), 
            'auct_type': 'current', 
            'juris': 'CA', 
            'inst_cat': 'consign', 
            'vintage': df.at[row, 'vintage'], 
            'Available': np.NaN,
            'Unsold': np.NaN,
            'Redesignated': df.at[row, 'Unsold']}

        new_rows_list.append(new_row_dict)

    # turn dictionary into a df & append to df of historical data
    df = df.append(pd.DataFrame(new_rows_list), sort=True)
    
    # use groupby sum to combine rows for Available, Unsold, Redesignated; eliminates duplicates within metadata
    df = df.groupby(['market', 'date_level', 'auct_type', 'juris', 'inst_cat', 'vintage']).sum()
        
    # drop all rows with zero values
    df = df.loc[df['Available']!=0]

    # calculate newly available allowances: all those available that are not redesignated
    df['Newly available'] = df['Available'] - df['Redesignated']
    
    # drop extraneous columns
    df = df.reset_index()
    df = df.drop(['market', 'Available', 'Sold', 'Unsold', 'Redesignated'], axis=1)

    # set values for additional metadata columns, then set index as standard MI
    df['acct_name'] = 'limited_use' # consignment temporarily sit in limited_use, between alloc_hold and auct_hold
    df['newness'] = 'new'
    df['status'] = 'not_avail'
    df['unsold_di'] = prmt.NaT_proxy
    df['unsold_dl'] = prmt.NaT_proxy
    df['units'] = 'MMTCO2e'
    df = df.set_index(prmt.standard_MI_names)
    
    # change name of column
    df = df.rename(columns={'Newly available': 'quant'})
    
    # sort by index
    df = df.sort_index()
    
    consign_new_avail_hist = df
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (end)")
    
    return(consign_new_avail_hist)
# end of create_qauct_new_avail_consign


# In[ ]:


def get_compliance_events():
    """
    From annual compliance reports, create record of compliance events (quantities surrendered at specific times).
    
    Note that quantities surrendered are *not* the same as the covered emissions that have related obligations.
    """
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (start)")    
    
    # get record of retirements (by vintage) from annual compliance reports
    df = pd.read_excel(prmt.input_file, sheet_name='annual compliance reports')

    # drop all rows completely empty; empty rows may be caused by openpyxl
    df = df.dropna(how='all')
    
    df = df.set_index('year of compliance event')
    
    # drop rows with the following indices
    df = df.drop(['total for compliance period 2013-2014', 
                  'total for compliance period 2015-2017', 
                  'total for compliance period 2018-2020'])
    
    # drop non-quantity columns
    df = df.drop(['units',
                  'CA checksum', 
                  'QC checksum'], axis=1)
    df = df.dropna(how='all')
    
    # convert units from tCO2e to MMtCO2e
    df = df / 1e6

    prmt.CA_surrendered = df['CA entities surrendered total (all instruments)']
    prmt.QC_surrendered = df['QC entities surrendered total (all instruments)']
    
    # continue with CA-QC totals
    df = df.drop(['CA entities surrendered total (all instruments)', 
                  'QC entities surrendered total (all instruments)'], axis=1)
    
    # convert compliance report values into compliance events (transfers that occur each Nov)
    # sum allowances by vintage, combining surrenders by CA & QC entities
    df = df.copy()
    df.columns = df.columns.str.replace('CA entities surrendered ', '')
    df.columns = df.columns.str.replace('QC entities surrendered ', '')
    df.columns = df.columns.str.replace('allowance vintage ', '')
    df.columns.name = 'vintage or type'

    df = df.stack()
    df = pd.DataFrame(df, columns=['quant'])
    df = df.loc[df['quant'] > 0]
    df = df.groupby(['year of compliance event', 'vintage or type']).sum().reset_index()
    df['compliance_date'] = pd.to_datetime(df['year of compliance event'].astype(str)+'-11-01').dt.to_period('Q')

    # rename 'Early Reduction credits' & 'non-vintage allowances'
    df['vintage or type'] = df['vintage or type'].str.replace('Early Reduction credits', 'early_action')
    df['vintage or type'] = df['vintage or type'].str.replace('non-vintage allowances', 'APCR')

    df = df[['compliance_date', 'vintage or type', 'quant']].set_index(['compliance_date', 'vintage or type'])

    # run function to process late surrender
    df = late_surrender_adjustment_of_compliance_events(df)
    
    prmt.compliance_events = df
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (end)")
    
    # no return; func sets object attribute
# end of get_compliance_events


# In[ ]:


def late_surrender_adjustment_of_compliance_events(df):
    """
    There is only one known late surrender, which occurred for California for compliance period 1 (2013-2014).
    
    Comision Federal de Electricidad (utility based in Mexico) did not surrender any instruments.
    
    In 2016Q1, they did surrender 472,625 instruments, and the 2013-2014 Compliance Report was updated with that data.

    This function removes those allowances from 2015Q4 compliance event, and adds them as occurring in 2016Q1.
    
    This function runs within get_compliance_events, which creates prmt.compliance_events, modifying that df.
    
    If an entity doesn’t surrender allowances by the deadline, we assume (until we have information otherwise) 
    that they’ll eventually satisfy this obligation. So the obligation is still remaining. 
    Thus the model calculates the bank based on the obligations incurred excluding those permanently unfulfilled, 
    and therefore late surrenders don’t affect the banking calculation.
    """
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (start)")
    
    # prmt.compliance_events is used only for: 1. calculating if there are excess offsets, 2. CIR comparison
    # late surrender from Comision Federal de Electridad consisted of only allowances
    # so adjustment for it won't affect offsets; will only affect CIR comparison

    # dict of vintages of allowances and quantities in late surrender
    # source: California compliance report 2013-2014
    late_surrender_2016Q1 = {2013: 15778, 2014: 7908, 2015: 448939} # units tCO2e

    adj = pd.Series(late_surrender_2016Q1) / 1e6 # convert to MMTCO2e
    adj = pd.DataFrame(adj)
    adj = adj.reset_index()
    adj = adj.rename(columns={0: 'quant', 'index': 'vintage'})
    adj['compliance_date'] = quarter_period('2016Q1')
    adj['vintage'] = adj['vintage'].astype(str) # convert because df (argument) has vintages stored as str
    adj = adj.set_index(['compliance_date', 'vintage'])

    neg_adj = adj.copy() * -1
    neg_adj = neg_adj.reset_index()
    neg_adj['compliance_date'] = quarter_period('2015Q4')
    neg_adj = neg_adj.set_index(['compliance_date', 'vintage'])

    adj_and_neg_adj = adj.append(neg_adj)

    # append adj_and_neg_adj to df (argument)
    # then use groupby sum to add values for 2016Q1 and subtract from 2015Q4
    df = df.append(adj_and_neg_adj)
    df = df.groupby(df.index.names).sum()

    df = df.sort_index()
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (end)")
    
    return(df)
# end of late_surrender_adjustment_of_compliance_events


# In[ ]:


def get_CIR_data_and_clean():
    """
    Get historical data from Compliance Instrument Reports, iterating through all sheets.
    
    Function inputs (CIR file) have units tCO2e. 
    
    Function outputs have units MMtCO2e. Units converted in functions clean_CIR_allowances & clean_CIR_offsets.
    """

    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (start)")
    
    CIR_sheet_names = pd.ExcelFile(prmt.CIR_excel).sheet_names
    
    logging.info(f"CIR first (latest) sheet: {CIR_sheet_names[0]}")
    
    # initialize lists
    CIR_allowances_list = []
    CIR_offsets_list = []
    forest_buffer_stock = pd.DataFrame()
    
    for sheet in CIR_sheet_names:        
        # get records for each quarter
        one_quart = pd.read_excel(prmt.CIR_excel, header=6, sheet_name=sheet)
        
        # drop all rows completely empty; empty rows may be caused by openpyxl
        one_quart = one_quart.dropna(how='all')

        # record sheet name in a column of the df
        one_quart['quarter'] = sheet

        # look in first column ('Vintage'), find the rows labeled 'Allowances Subtotal' and 'Offset Credits Subtotal'
        # print(one_quart['Vintage'].tolist())
        # indices = [i for i, s in enumerate(mylist) if 'aa' in s]
        first_col_as_list = one_quart['Vintage'].astype(str).tolist()
        allow_subtot_index = [i for i, s in enumerate(first_col_as_list) if 'Allowances Subtotal' in s][0]
        offset_subtot_index = [i for i, s in enumerate(first_col_as_list) if 'Offset Credits Subtotal' in s][0]
        # note [0] at end of two lines above; this takes 0th item in list, which is an integer

        # get allowances:
        # use -1 to cut off 'Allowances Subtotal'
        one_quart_allow = one_quart.loc[0:allow_subtot_index-1]
        # get offsets:
        # use -1 to cut off 'Offset Credits Subtotal'
        one_quart_offset = one_quart.loc[allow_subtot_index+1:offset_subtot_index-1]

        CIR_allowances_list += [one_quart_allow]
        CIR_offsets_list += [one_quart_offset]
    
    # end of loop "for sheet in CIR_sheet_names:"
    
    # convert lists of dfs above into single dfs
    CIR_allowances = pd.concat(CIR_allowances_list, axis=0, sort=True)
    CIR_offsets = pd.concat(CIR_offsets_list, axis=0, sort=True)
    
    # call functions to clean up allowances and offsets; functions also convert units to MMtCO2e
    CIR_allowances = clean_CIR_allowances(CIR_allowances)
    CIR_offsets = clean_CIR_offsets(CIR_offsets)

    # combine cleaned versions of allowances and offsets
    # create CIR_historical (new df)
    prmt.CIR_historical = pd.concat([CIR_allowances, CIR_offsets], sort=True)
    # note this does not include Forest Buffer

    # create CIR_offsets_q_sums, used later for CIR comparison
    # these are sums across the different categories of offsets, 
    # but retain the full set of various accounts, & showing offsets in private vs. jurisdiction accounts
    df = CIR_offsets.copy().reset_index()
    df = df.drop(['Description', 'Vintage'], axis=1)
    df = df.set_index('date')
    prmt.CIR_offsets_q_sums = df
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (end)")
    
    # no return; func sets object attributes prmt.CIR_historical & prmt.CIR_offsets_q_sums
# end of get_CIR_data_and_clean


# In[ ]:


def clean_CIR_allowances(df):
    """
    Clean up results from concat of allowance data from individual CIR sheets.
    
    Runs within function get_CIR_data_and_clean.
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    df = df.reset_index(drop=True) 

    df.columns = df.columns.str.replace('\n', '')
    
    # combine and clean up columns with changing names across quarters:
    # new_list = [expression(i) for i in old_list if filter(i)]
    for col_type in ['Retirement', 
                     'Voluntary Renewable Electricity', 
                     'Limited Use Holding Account', 
                     'Environmental Integrity']:
    
        CIR_sel_cols = [col for col in df.columns if col_type in col]
        df[col_type] = df[CIR_sel_cols].sum(axis=1, skipna=True)

        for col in CIR_sel_cols:
            if '*' in col or '(' in col:
                df = df.drop(col, axis=1)

    df.insert(0, 'Description', df['Vintage'])
    for item in range(2013, 2030+1):
        df['Description'] = df['Description'].replace(item, 'vintaged allowances', regex=True)

    non_vintage_map = {'Non-Vintage Québec Early Action Allowances (QC)': 'early_action', 
                       'Non-Vintage Price Containment Reserve Allowances': 'APCR', 
                       'Allowances Subtotal': np.NaN}
    df['Vintage'] = df['Vintage'].replace(non_vintage_map)

    df['quarter'] = df['quarter'].str.replace(' ', '')
    df['quarter'] = pd.to_datetime(df['quarter']).dt.to_period('Q')
    
    for column in ['Auction + Issuance + Allocation', 'Compliance', 'General',
       'Invalidation', 'Reserve', 'Retirement',
       'Voluntary Renewable Electricity', 'Limited Use Holding Account',
       'Environmental Integrity', 'Total']:
        df[column] = df[column].astype(float)
    
    df = df.rename(columns={'quarter': 'date', 'Total': 'subtotal'})

    df = df.set_index(['date', 'Description', 'Vintage'])

    for column in df.columns:
        if 'Unnamed' in column:
            df = df.drop(column, axis=1)
    
    # convert units to MMTCO2e
    df = df/1e6
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(df)
# end of clean_CIR_allowances


# In[ ]:


def clean_CIR_offsets(df):
    """
    Clean up results from concat of offsets data from individual CIR sheets.
    
    Runs within function get_CIR_data_and_clean.
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
        
    df = df.reset_index(drop=True) 

    df.columns = df.columns.str.replace('\n', '')

    df = df.rename(columns={'Vintage': 'Offset type'})
    df['Offset type'] = df['Offset type'].str.rstrip().str.rstrip().str.rstrip('+').str.rstrip('*')

    df_names = df['Offset type'].unique().tolist()
    df_names.remove('California')
    df_names.remove('Québec')
    df_names.remove(np.NaN)

    df['Jurisdiction'] = df['Offset type']
    df = df.dropna(subset=['Jurisdiction'])

    for row in df.index:
        if df.at[row, 'Jurisdiction'] in df_names:
            df.at[row, 'Jurisdiction'] = np.NaN
    df['Jurisdiction'] = df['Jurisdiction'].fillna(method='ffill')
    df = df[df['Offset type'].isin(df_names)]

    for col in ['General', 'Total']:
        df[col] = df[col].astype(str)
        df[col] = df[col].str.replace('\+', '')
        df[col] = df[col].str.replace('5,043,925 5,017,043', '5017043')
        df[col] = df[col].astype(float)

    df['Offset type'] = df['Offset type'].str.rstrip(' (CA)')
    df['Offset type'] = df['Offset type'].str.rstrip(' (QC)')

    df['quarter'] = df['quarter'].str.replace(' ', '')
    df['quarter'] = pd.to_datetime(df['quarter']).dt.to_period('Q')
    df = df.rename(columns={'quarter': 'date'})
    
    # combine and clean up columns with changing names across quarters:
    # use list comprehension: new_list = [expression(i) for i in old_list if filter(i)]
    for col_type in ['Retirement', 
                     'Voluntary Renewable Electricity', 
                     'Limited Use Holding Account', 
                     'Environmental Integrity']:
    
        CIR_sel_cols = [col for col in df.columns if col_type in col]
        df[col_type] = df[CIR_sel_cols].sum(axis=1, skipna=True)

        for col in CIR_sel_cols:
            if '*' in col or '(' in col:
                df = df.drop(col, axis=1)
             
    for column in ['Auction + Issuance + Allocation', 'Compliance', 'General',
       'Invalidation', 'Reserve', 'Retirement',
       'Voluntary Renewable Electricity', 'Limited Use Holding Account',
       'Environmental Integrity', 'Total']:
        df[column] = df[column].astype(float)

    df = df.rename(columns={'Offset type': 'Description', 'Total': 'subtotal'})
    df = df.set_index(['date', 'Description', 'Jurisdiction'])

    for column in df.columns:
        if 'Unnamed' in column:
            df = df.drop(column, axis=1)
    
    # convert units to MMTCO2e
    df = df/1e6
    
    # sum over types of offsets, jurisdictions
    df = df.groupby('date').sum()
    
    # create new columns and create MultiIndex that can be concat with allowance data
    df['Description'] = 'offsets'
    df['Vintage'] = 'n/a'
    df = df.set_index([df.index, 'Description', 'Vintage'])
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(df)
# end clean_CIR_offsets


# In[ ]:


def get_VRE_retired_from_CIR():
    """
    For Voluntary Renewable Electricity (VRE) allowances.
    
    Quantities retired inferred from quarter-to-quarter decreases in VRE account, as shown in CIR.
    
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # as of the latest data available in the version of the Compliance Instrument Report fed in above
    VRE = prmt.CIR_historical[['Voluntary Renewable Electricity']]
    VRE = VRE.xs('vintaged allowances', level='Description')

    # rearrange to be able to calculate annual change (diff); negative of annual change is what was retired from VRE
    VRE = VRE.unstack(0)
    VRE.columns = VRE.columns.droplevel(0)
    VRE.columns.name = 'CIR_date'
    VRE.index.name = 'vintage'

    # use diff to find quarterly changes
    # (there were none retired in the initial CIR quarter, 2014Q2, 
    # so no problem with diff not calculating value for first CIR quarter)
    VRE_retired = VRE.T.diff().T * -1
    VRE_retired = VRE_retired.replace(-0.0, np.NaN)
    VRE_retired = VRE_retired.dropna(how='all')
    VRE_retired = VRE_retired.T
    VRE_retired = VRE_retired.dropna(how='all')
    VRE_retired = VRE_retired.stack()
    VRE_retired.name = 'quant'

    # convert to df
    VRE_retired = pd.DataFrame(VRE_retired)
    
    # set object attribute
    prmt.VRE_retired = VRE_retired
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    # no return; func sets object attribute prmt.VRE_retired
# end of get_VRE_retired_from_CIR


# In[ ]:


def assign_EIM_outstanding():
    """
    Get historical data for EIM Outstanding Emissions retirements and create projection.
    """
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (start)")
    
    # used saved df prmt.EIM_and_bankruptcy
    # (avoids openpyxl problem with reading the same Excel sheet twice)
    df = prmt.EIM_and_bankruptcy.copy()
    
    df = df.loc[df['description']=='EIM Outstanding Emissions by year incurred']
    
    # convert units from tCO2e to MMtCO2e
    df['data'] = df['data'] / 1e6
    
    ser = df.set_index('year')['data']
    
    # make projection for EIM; assume same as historical average so far
    hist_avg = ser.mean()
    ser = ser.fillna(value=hist_avg)
    
    ser.name = 'EIM_outstanding'
    ser.index.name = 'year incurred'
    
    ser = ser.loc[:2028]
    
    prmt.EIM_outstanding = ser
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (end)")
    # no return
# end of assign_EIM_outstanding


# In[ ]:


def assign_bankruptcy_noncompliance():
    """
    Handling of bankruptcy retirements based on CARB, "2018 Regulation Documents (Narrow Scope)": 
    https://www.arb.ca.gov/regact/2018/capandtradeghg18/capandtradeghg18.htm

    As of 2019Q2, the only known unfulfilled obligation due to bankruptcy that would be accounted for through 
    retirement was that from La Paloma Generating Company, LLC.; CARB stated in 2018 compliance report:
    "CARB will surrender 3,767,027 compliance instruments...".
    """
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (start)")
    
    df = prmt.EIM_and_bankruptcy.copy()
    
    df = df.loc[df['description']=='bankruptcy retirements']
    
    # convert units from tCO2e to MMtCO2e
    df['data'] = df['data'] / 1e6
    
    ser = df.set_index('year')['data']
    ser.name = 'bankruptcy_hist_proj'
    ser.index.name = 'year processed'
    
    # make projection that there will be no future bankruptcy retirements
    ser = ser.fillna(float(0))
    
    # only keep through 2028; later years would be retired from post-2030 allowances, which don't exist yet
    ser = ser.loc[:2028]
    
    prmt.bankruptcy_hist_proj = ser
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (end)")
    # no return; sets prmt.bankruptcy_hist_proj
# end of assign_bankruptcy_noncompliance


# In[ ]:


def read_CA_alloc_data():
    """    
    Reads historical allocation data, as well as cap adjustment factors
    
    CA allocations use cap adjustment factor from § 95891, Table 9-2
    
    note: Input file only includes the standard cap adjustment factors.
    
    If need be, can add to input file the non-standard for particular process intensive industries.
    """
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (start)")
    
    df = pd.read_excel(prmt.input_file, sheet_name='CA allocations')

    # drop all rows completely empty; empty rows may be caused by openpyxl
    df = df.dropna(how='all')
    
    # for rows with no entry in column 'data', drop the row
    df = df.dropna(subset=['data'])

    CA_alloc_data = df
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (end)")
    
    return(CA_alloc_data)
# end of read_CA_alloc_data


# In[ ]:


def initialize_elec_alloc():
    """
    California only: 2021-2030 Electrical Distribution Utility Sector Allocation (IOU & POU).

    2013-2020: § 95870(d)(1), with details specified in regs § 95892(a)(1) & § 95892(a)(2)
    2021-2030: § 95871(c)(1)
    details determined by 95892(a), with allocation quantities explicitly stated in § 95892 Table 9-4
    (data copied from pdf (opened in Adobe Reader) into Excel; saved in input file)
    but utilities not identified in Table 9-4 as IOU or POU
    so merge with 2013-2020 df, and then compute sums for whole time span 2013-2030
    (also note this does not go through 2031, as cap does)
    """

    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (start)")
    
    # create elec_alloc_2013_2020

    # read input file; 
    # has '-' for zero values in some cells; make those NaN, replace NaN with zero; then clean up strings
    df = pd.read_excel(prmt.input_file, sheet_name='CA elec alloc 2013-2020', na_values='-')
    
    # drop all rows completely empty; empty rows may be caused by openpyxl
    df = df.dropna(how='all')
    
    df = df.drop('units', axis=1)
    df = df.fillna(0)
    df = df.replace('\xa0', '', regex=True)

    # convert all data to int, which rounds down any fractional allowances
    for column in range(2013, 2020+1):
        df[column] = df[column].astype(int)

    df = df.rename(columns={'Utility Name': 'Utility Name (2013-2020)'})

    # in original file, total was in a row at the end, with no label
    # there was also an empty row between the total row and the rows with data by utility
    # both the total row and empty row have '0' as utility name, because of fillna(0) above
    # so only keep rows with 'Utility Name (2013-2020)' not 0
    df = df[df['Utility Name (2013-2020)']!=0]

    elec_alloc_2013_2020 = df
    
    # ~~~~~~~~~~~~~~~~~~~~
    
    # create elec_alloc_2021_2030
    df = pd.read_excel(prmt.input_file, sheet_name='CA elec alloc 2021-2030')
    
    # drop all rows completely empty; empty rows may be caused by openpyxl
    df = df.dropna(how='all')
    
    df = df.drop('units', axis=1)
    
    # clean up data, including in column headers
    # strip out line breaks (\xa0) & spaces & commas
    df = df.replace('\xa0', '', regex=True)
    df.columns = df.columns.str.strip('\xa0')
    df = df.rename(columns={'Utility': 'Utility Name'})
    df = df.set_index('Utility Name')
    df.columns = df.columns.astype(int)
    df = df.replace(',', '', regex=True)

    # convert all column names to int
    for column in range(2021, 2030+1):
        df[column] = df[column].astype(int)
    df = df.reset_index()

    # rename utilities according to map I created between 2013-2020 and 2021-2030 versions
    CA_util_names_map = pd.read_excel(prmt.input_file, sheet_name='CA util names map')
    
    # drop all rows completely empty; empty rows may be caused by openpyxl
    CA_util_names_map = CA_util_names_map.dropna(how='all')
    
    CA_util_names_map = CA_util_names_map.replace('\xa0', '', regex=True)
    CA_util_names_map.columns = CA_util_names_map.columns.str.strip('\xa0')

    df = pd.merge(df, CA_util_names_map, left_on='Utility Name', right_on='Utility Name (2021-2030)', how='outer')
    df = df.drop(['Utility Name', 'notes'], axis=1)

    elec_alloc_2021_2030 = df
    
    # ~~~~~~~~~~~~~~~~~~~~
    logging.info('initialize: create elec_alloc_IOU & elec_alloc_POU')
    
    # create elec_alloc_IOU & elec_alloc_POU (units MMTCO2e)
    df = pd.merge(elec_alloc_2013_2020, elec_alloc_2021_2030,
                  left_on='Utility Name (2013-2020)', right_on='Utility Name (2013-2020)', how='outer')

    df['Utility Type'] = df['Utility Type'].replace('COOP', 'POU')
    df = df.groupby('Utility Type').sum().T
    df.index = df.index.astype(int)
    df = df / 1e6
    
    # ~~~~~~~~~~~~~~~~~~~~
    # modify based on EIM outstanding retirements
    # CARB will reduce each utility's allocation based on that utility's EIM outstanding
    # but since the data on each utility's use of EIM is not public, as far as we know, 
    # the model assumes EIM outstanding for IOUs and POUs are proportional to their total allocations
    IOU_ratio = df['IOU'] / (df['IOU'] + df['POU'])
    
    EIM_IOU_to_retire = pd.Series() # initialize
    EIM_POU_to_retire = pd.Series() # initialize
    
    # calculate how much to reduce elec_alloc_IOU and elec_alloc_POU by
    for incurred_year in [2020]:
        # only EIM outstanding incurred in 2019Q2-Q4 are taken from EIM_outstanding
        # assume that Q2-Q4 is 3/4 of annual total
        EIM_IOU_to_retire.at[incurred_year+2] = prmt.EIM_outstanding.loc[incurred_year] * (3/4) * IOU_ratio.loc[incurred_year]
        EIM_POU_to_retire.at[incurred_year+2] = prmt.EIM_outstanding.loc[incurred_year] * (3/4) * (1 - IOU_ratio.loc[incurred_year])
        
    for incurred_year in range(2021, 2028+1):
        # EIM outstanding incurred in 2020-2028 are taken from EIM_outstanding
        # (for years after 2028, can't process because no allowances of vintages after 2030)
        EIM_IOU_to_retire.at[incurred_year+2] = prmt.EIM_outstanding.loc[incurred_year] * IOU_ratio.loc[incurred_year]
        EIM_POU_to_retire.at[incurred_year+2] = prmt.EIM_outstanding.loc[incurred_year] * (1 - IOU_ratio.loc[incurred_year])
    
    # reduce elec alloc by modifying df from previous section of this cell
    df['IOU'] = pd.concat([df['IOU'], -1*EIM_IOU_to_retire], axis=1).sum(axis=1)
    df['POU'] = pd.concat([df['POU'], -1*EIM_POU_to_retire], axis=1).sum(axis=1)
    
    # the quantities that are not allocated are retired at the appropriate time by retire_for_EIM_outstanding
    
    # ~~~~~~~~~~~~~~~~~~~~

    elec_alloc_IOU = df['IOU']
    elec_alloc_IOU.name = 'elec_alloc_IOU'
    elec_alloc_POU = df['POU']
    elec_alloc_POU.name = 'elec_alloc_POU'

    # elec_alloc_IOU and elec_alloc_POU are transferred to appropriate accounts later, in consignment section
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (end)")
    
    return(elec_alloc_IOU, elec_alloc_POU)
# end of initialize_elec_alloc


# In[ ]:


def initialize_nat_gas_alloc(CA_alloc_data):
    """
    California only: Calculates the natural gas allocations for all years to 2030.
    
    Allocations are pre-defined by regulations, based on natural gas emissions rate in 2011, 
    and cap adjustment factor.
    
    However, regulations don't state what the 2011 emissions rate was, so the function calculates it.
    
    The results of the function have been exactly the same or very close (within 1 allowance) of historical values.
    
    The function draws on historical data from annual allocation reports, stored in data input file.
    
    """
    # historical data from annual allocation reports; stored in input file
    # have to use these historical values to calculate 2011 natural gas supplier emissions
    # once 2011 natural gas supplier emissions has been calculated, can use equation in regulations for projections
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (start)")
    
    nat_gas_alloc = CA_alloc_data.copy()[CA_alloc_data['name']=='nat_gas_alloc']
    nat_gas_alloc['year'] = nat_gas_alloc['year'].astype(int)
    nat_gas_alloc = nat_gas_alloc.set_index('year')['data']
    
    # add data points with zeros to make later steps easier, and sort to put in order
    nat_gas_alloc.at[2013] = float(0)
    nat_gas_alloc.at[2014] = float(0)
    nat_gas_alloc = nat_gas_alloc.sort_index()
    
    # not clear from MRR which emissions are credited to natural gas suppliers, or which emissions regs are referring to
    # but can infer what emissions in 2011 ARB used for calculating allocations disbursed to date (2015-2017)
    # emissions in 2011 = reported allocations for year X / adjustment factor for year X
    # can calculate emissions in 2011 from this equation for any particular year;
    # to avoid rounding errors, can calculate mean of ratios from each year
    nat_gas_emissions_2011_inferred = (nat_gas_alloc.loc[2015:] / prmt.CA_cap_adjustment_factor).mean()

    # calculate allocations for all future years, which scale down based on cap adjustment factor
    nat_gas_last_hist_year = nat_gas_alloc.index.max()
    for future_year in range(nat_gas_last_hist_year+1, 2030+1):        
        nat_gas_alloc_future = nat_gas_emissions_2011_inferred * prmt.CA_cap_adjustment_factor.at[future_year]
        nat_gas_alloc.at[future_year] = nat_gas_alloc_future
        
    # convert units from allowances to million allowances (MMTCO2e)
    nat_gas_alloc = nat_gas_alloc / 1e6

    nat_gas_alloc.name = 'nat_gas_alloc'
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (end)")
    
    return(nat_gas_alloc)
# end of initialize_nat_gas_alloc


# In[ ]:


def initialize_industrial_etc_alloc(CA_alloc_data):
    """
    CA only: Gathers historical values for all categories of California allocations that vary year to year,
    based on industrial activity or energy consumption (aka variable allocations).
    
    Combines these variable allocations into one data set ("industrial and other allocations").
    """
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (start)")
    
    industrial_alloc = CA_alloc_data.copy()[CA_alloc_data['name'].isin(
        ['industrial_alloc', 'industrial_and_legacy_gen_alloc'])]
    industrial_alloc['year'] = industrial_alloc['year'].astype(int)
    industrial_alloc = industrial_alloc.set_index('year')['data']

    # convert units from allowances to million allowances (MMTCO2e)
    industrial_alloc = industrial_alloc/1e6

    industrial_alloc.name = 'industrial_alloc'
    
    CA_alloc_last_hist_yr = industrial_alloc.index.max()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    logging.info('initialize: water_alloc')
    water_alloc = CA_alloc_data.copy()[CA_alloc_data['name']=='water_alloc']
    water_alloc['year'] = water_alloc['year'].astype(int)
    water_alloc = water_alloc.set_index('year')
    water_alloc = water_alloc['data']
    water_alloc = water_alloc.astype(float)

    # § 95895(b): "2021 and subsequent years"
    # (calculate values 2021-2031, and also combine below with values 2015-2020)

    # for post-2020, method is:
    # allocation = 47,853 × cap_adjustment_factor (by year)

    # get base level (value 47,853 allowances; stored in input file)
    water_alloc_post_2020_base_level = CA_alloc_data.set_index('name').at['water_alloc_post_2020_base_level', 'data']

    for year in range(2021, 2030+1):
        water_alloc_year = water_alloc_post_2020_base_level * prmt.CA_cap_adjustment_factor[year]
        water_alloc.at[year] = water_alloc_year

    # convert units from allowances to million allowances (MMTCO2e)
    water_alloc = water_alloc / 1e6

    water_alloc.name = 'water_alloc'

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    logging.info('initialize: university_alloc')
    university_alloc = CA_alloc_data.copy()[CA_alloc_data['name']=='university_alloc']
    university_alloc['year'] = university_alloc['year'].astype(int)
    university_alloc = university_alloc.set_index('year')['data']

    university_alloc.name = 'university_alloc'

    # convert units from allowances to million allowances (MMTCO2e)
    university_alloc = university_alloc / 1e6

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    logging.info('initialize: legacy_gen_alloc')
    legacy_gen_alloc = CA_alloc_data.copy()[CA_alloc_data['name']=='legacy_gen_alloc']
    legacy_gen_alloc['year'] = legacy_gen_alloc['year'].astype(int)
    legacy_gen_alloc = legacy_gen_alloc.set_index('year')['data']

    # convert units from allowances to million allowances (MMTCO2e)
    legacy_gen_alloc = legacy_gen_alloc / 1e6

    legacy_gen_alloc.name = 'legacy_gen_alloc'
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    logging.info('initialize: thermal_output_alloc')
    
    # variable allocation
    thermal_output_alloc = CA_alloc_data.copy()[CA_alloc_data['name']=='thermal_output_alloc']
    thermal_output_alloc['year'] = thermal_output_alloc['year'].astype(int)
    thermal_output_alloc = thermal_output_alloc.set_index('year')['data']

    # convert units from allowances to million allowances (MMTCO2e)
    thermal_output_alloc = thermal_output_alloc / 1e6

    thermal_output_alloc.name = 'thermal_output_alloc'

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    logging.info('initialize: waste_to_energy_alloc')
    waste_to_energy_alloc = CA_alloc_data.copy()[CA_alloc_data['name']=='waste_to_energy_alloc']
    waste_to_energy_alloc['year'] = waste_to_energy_alloc['year'].astype(int)
    waste_to_energy_alloc = waste_to_energy_alloc.set_index('year')['data']

    # convert units from allowances to million allowances (MMTCO2e)
    waste_to_energy_alloc = waste_to_energy_alloc / 1e6

    waste_to_energy_alloc.name = 'waste_to_energy_alloc'

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    logging.info('initialize: LNG_supplier_alloc')
    # variable allocation
    LNG_supplier_alloc = CA_alloc_data.copy()[CA_alloc_data['name']=='LNG_supplier_alloc']
    LNG_supplier_alloc['year'] = LNG_supplier_alloc['year'].astype(int)
    LNG_supplier_alloc = LNG_supplier_alloc.set_index('year')['data']

    # convert units from allowances to million allowances (MMTCO2e)
    LNG_supplier_alloc = LNG_supplier_alloc / 1e6

    LNG_supplier_alloc.name = 'LNG_supplier_alloc'

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    industrial_etc_alloc_list = [industrial_alloc, water_alloc, university_alloc, legacy_gen_alloc, 
                                 thermal_output_alloc, waste_to_energy_alloc, LNG_supplier_alloc]

    industrial_etc_alloc = pd.concat(industrial_etc_alloc_list, axis=1).sum(axis=1)
    industrial_etc_alloc.name = 'industrial_etc_alloc_hist'

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # calculate what allocation would be in case for all assistance factors at 100% for 2018-2030
    # assume that the resulting allocation for each year would follow caps downward
    idealized = pd.Series()
    for year in range(2018, 2030+1):
        cap_adj_ratio_year = prmt.CA_cap_adjustment_factor.at[year] / prmt.CA_cap_adjustment_factor.at[2017]
        idealized.at[year] = industrial_etc_alloc.at[2017] * cap_adj_ratio_year

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # compare against ARB's projection from 2018-03-02 workshop presentation, slide 9
    # (as extracted using WebPlotDigitizer)
    df = pd.read_excel(prmt.input_file, sheet_name='CA allocations projection')
    
    # drop all rows completely empty; empty rows may be caused by openpyxl
    df = df.dropna(how='all')
    
    df = df.set_index('year')
    ser = df['industrial and other allocation [under Oct 2017 regulations; lower assistance factors 2018-2020]']
    ser = ser / 1e6 # convert units from tCO2e to MMTCO2e
    ser.name = 'industrial_etc_alloc_ARB_proj'
    ARB_proj = ser
    
    # ARB's graph shows industrial & other allocations somewhat higher (~ +0.5 M / year) over historical period
    # and somewhat lower (~ -0.5 M/year) than my projection based on 2017

    # there is uncertainty about what this projection will be, since it depends on activity
    # the two are within ~1.5%, which is close enough

    # true-ups to make up for lower assistance factors in 2018-2019 will be applied retroactively, in 2020 & 2021
    CA_trueups_retro = (idealized - ARB_proj).loc[2018:2019]
    CA_trueups_retro.index = CA_trueups_retro.index + 2
    CA_trueups_retro.name = 'CA_trueups_retro'

    # allocation for 2020 will use 100% assistance factor
    CA_additional_2020 = (idealized - ARB_proj).loc[2020:2020]
    CA_additional_2020.name = 'CA_additional_2020'

    # combine the 4 pieces: historical, projection with lower assistance factors, trueups_retro, and additional
    # this is what CARB has referred to as "industrial and other allocations"
    industrial_etc_alloc = pd.concat([industrial_etc_alloc.loc[:CA_alloc_last_hist_yr], 
                                      ARB_proj.loc[CA_alloc_last_hist_yr+1:], 
                                      CA_trueups_retro, 
                                      CA_additional_2020], 
                                     axis=1).sum(axis=1)
    industrial_etc_alloc.name = 'industrial_etc_alloc'
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (end)")
    
    return(industrial_etc_alloc)
# end of initialize_industrial_etc_alloc


# In[ ]:


def read_annual_auction_notices():
    """
    Reads data from annual auction notices.
    
    Currently, model only uses the consignment data.
    """
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (start)")
    
    df = pd.read_excel(prmt.input_file, sheet_name='annual auction notices')
    
    # drop all rows completely empty; empty rows may be caused by openpyxl
    df = df.dropna(how='all')

    # extract consignment data
    # drop any rows that do not have data entered; select subset of data and set index; set name
    df2 = df.dropna(subset=['data'])
    df2 = df2[df2['name']=='CA_consignment_annual'][['vintage', 'data']]
    df2 = df2.set_index('vintage')['data']
    df2.name = 'consign_ann'

    # convert units from tCO2e to MMtCO2e
    df2 = df2 / 1e6
    
    prmt.consign_ann_hist = df2
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (end)")
    
    # no return
# end of read_annual_auction_notices


# In[ ]:


def create_consign_historical_and_projection_annual(elec_alloc_IOU, elec_alloc_POU, nat_gas_alloc):
    """
    Create a projection for consignment quantities to 2030.
    
    Starts projection after the latest historical year with data on annual consignment.
    """
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (start)")
    
    # create consign_last_hist_yr, used for defining range to iterate over below
    consign_last_hist_yr = prmt.consign_ann_hist.index.max()
    
    # create new local df, consign_ann, which will include historical and projection
    consign_ann = prmt.consign_ann_hist.copy()
    # note that local variable consign_ann is modified below to add projection
    
    # IOUs have to consign 100% of their electricity allocation, so for them, consign = alloc
    # established by § 95892(b)(1)
    consign_elec_IOU = elec_alloc_IOU
    consign_elec_IOU.name = 'consign_elec_IOU'
    
    # POUs have to consign none of their electricity allocation
    # established by § 95892(b)(2)
    
    # natural gas allocation, minimum consignment portion:
    # set by § 95893(b)(1)(A), Table 9-5, and Table 9-6
    # values from tables above are in the input file
    CA_consign_regs = pd.read_excel(prmt.input_file, sheet_name='CA consign regs')
    
    # drop all rows completely empty; empty rows may be caused by openpyxl
    CA_consign_regs = CA_consign_regs.dropna(how='all')

    consign_nat_gas_min_fraction = CA_consign_regs[CA_consign_regs['name']=='CA_natural_gas_min_consign_fraction']
    consign_nat_gas_min_fraction = consign_nat_gas_min_fraction.set_index('year')['data']

    consign_nat_gas_min = nat_gas_alloc * consign_nat_gas_min_fraction
    consign_nat_gas_min.name = 'consign_nat_gas_min'
    
    # analysis of natural gas consignment:
    # if we assume that natural gas allocation is proportional to MRR covered emissions for nat gas distribution...
    # ... for each entity, for those entities that did receive an allocation, ...
    # ... then we can conclude that IOUs are consigning zero or negligible (~0.1 MMTCO2e) optional amounts...
    # ... above the minimum natural gas consignment
    # then actual nat gas consignment = minimum nat gas consignment
    consign_nat_gas = consign_nat_gas_min.copy()
    consign_nat_gas.name = 'consign_nat_gas'

    nat_gas_not_consign = pd.concat([nat_gas_alloc, -1*consign_nat_gas], axis=1).sum(axis=1).loc[2013:2030]
    nat_gas_not_consign.name = 'nat_gas_not_consign'
    
    # infer optional consignment amount (elec & nat gas)
    df = pd.concat([consign_ann,
                             -1*consign_elec_IOU,
                             -1*consign_nat_gas.fillna(0)], axis=1)
    df = df.sum(axis=1)
    df = df.loc[2013:consign_last_hist_yr]
    consign_opt = df
    
    # if IOUs are not consigning any optional amounts from their nat gas allocation, 
    # and we know IOUs must consign 100% of their electricity allocation,
    # then we can conclude that all of the consign optional is from POUs
    # and
    # if we assume that POUs are like IOUs in consigning only the minimum required from natural gas allocation,
    # then the optional POU consignment (in excess of the minimum for nat gas) would be from POUs' electricity allocation
    # (remember, POUs don't have to consign any of their electricity allocation)
    consign_elec_POU = consign_opt.copy()
    consign_elec_POU.name = 'consign_elec_POU'
    
    # calculate the mean fraction of the electricity POU allocation that was consigned 
    # (any electricity POU consignment is optional; none is required)
    consign_elec_POU_fraction = (consign_opt/elec_alloc_POU).mean()

    for year in range(consign_last_hist_yr+1, 2030+1):
        consign_elec_POU_year = elec_alloc_POU.at[year] * consign_elec_POU_fraction        
        consign_elec_POU.at[year] = consign_elec_POU_year
        
    elec_POU_not_consign = pd.concat([elec_alloc_POU, -1*consign_elec_POU], axis=1).sum(axis=1).loc[2013:2030]
    elec_POU_not_consign.name = 'elec_POU_not_consign'
    
    # consign_ann: calculate new values for projection years
    for year in range(consign_last_hist_yr+1, 2030+1):
        consign_ann.at[year] = consign_elec_IOU.at[year] + consign_elec_POU.at[year] + consign_nat_gas.at[year]
    
    # combine multiple series into one df for return    
    consign_series = [consign_ann, consign_elec_IOU, consign_nat_gas, consign_elec_POU, 
                      nat_gas_not_consign, elec_POU_not_consign]
    consign_df = pd.concat(consign_series, axis=1)
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (end)")
    
    return(consign_df)
# end of create_consign_historical_and_projection_annual


# In[ ]:


def consign_upsample_historical_and_projection(consign_ann):
    """
    Calculate quarterly values for consignment. 
    
    For latest year with historical data, infer average consignment in any remaining quarterly auctions.
    
    For projection years, calculate average consignment per quarter.
    """
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (start)")

    # get historical data for consignment newly available in each quarter
    consign_new_avail_hist = create_qauct_new_avail_consign()

    # create new df, starting with historical data, and later appending projection
    # (later will be set equal to prmt.df)
    df = consign_new_avail_hist.copy()

    # create template row for adding additional rows to df
    template = df.loc[df.index[-1:]]
    template.at[template.index, 'quant'] = float(0)
    
    if prmt.latest_hist_qauct_date.quarter < 4:
        # fill in missing quarters for last historical year

        # get annual total consigned in last historical year
        consign_ann_1y = consign_ann.at[prmt.latest_hist_qauct_date.year]

        # calculate total already newly available that year
        consign_1y_to_date = df.loc[
            df.index.get_level_values('date_level').year==prmt.latest_hist_qauct_date.year]['quant'].sum()

        # calculate remaining to consign
        consign_remaining = consign_ann_1y - consign_1y_to_date

        # number of remaining auctions
        num_remaining_auct = 4 - prmt.latest_hist_qauct_date.quarter

        # average consignment in remaining auctions
        avg_consign = consign_remaining / num_remaining_auct

        for proj_q in range(prmt.latest_hist_qauct_date.quarter+1, 4+1):
            proj_date = quarter_period(f"{prmt.latest_hist_qauct_date.year}Q{proj_q}")

            # create new row; update date_level and quantity
            consign_new_row = template.copy()
            mapping_dict = {'date_level': proj_date}
            consign_new_row = multiindex_change(consign_new_row, mapping_dict)
            consign_new_row.at[consign_new_row.index, 'quant'] = avg_consign
            
            # set new value in df
            df = df.append(consign_new_row)

    # for years after last historical data year (prmt.latest_hist_qauct_date.year)    
    for year in range(prmt.latest_hist_qauct_date.year+1, 2030+1):
        avg_consign = consign_ann.loc[year] / 4

        for quarter in [1, 2, 3, 4]:
            proj_date = quarter_period(f"{year}Q{quarter}")

            # create new row; update date_level and quantity
            consign_new_row = template.copy()
            mapping_dict = {'date_level': proj_date, 
                            'vintage': year}
            consign_new_row = multiindex_change(consign_new_row, mapping_dict)

            consign_new_row.at[consign_new_row.index, 'quant'] = avg_consign
            
            # set new value in df
            df = df.append(consign_new_row)
            
    # set object attribute
    prmt.consign_hist_proj_new_avail = df

    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (end)")

    # no return; func sets object attribute prmt.consign_hist_proj_new_avail
# end of consign_upsample_historical_and_projection


# In[ ]:


def get_QC_inputs():
    """
    Get values of parameters from data input file for QC cap, advance auctions, APCR.
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # get cap values from input sheet (derived from regs)
    df = pd.read_excel(prmt.input_file, sheet_name='QC cap data')
    
    # drop all rows completely empty; empty rows may be caused by openpyxl
    df = df.dropna(how='all')
    
    QC_cap_data = df
    
    # ~~~~~~~~~~~~~~~~~~~~
    # get cap quantities from input file
    df = QC_cap_data[QC_cap_data['name']=='QC_cap'].set_index('year')['data']
    
    # convert units from tCO2e to MMtCO2e
    df = df / 1e6
    
    QC_cap = df
    QC_cap.name = 'QC_cap'

    prmt.QC_cap = QC_cap
       
    # ~~~~~~~~~~~~~~~~~~~~

    # calculate advance for each year (2013-2030) on the basis that advance is 10% of cap
    # annual auction notice 2018 says: 
    # "Advance Auction Allowances Offered for Sale:
    # The Advance Auction budget represents 10 percent of the allowances from each of the jurisdiction’s allowance 
    # budgets that are created for the year three years subsequent to the current calendar year."
    QC_advance_fraction = QC_cap_data[QC_cap_data['name']=='QC_advance_fraction'].set_index('year')['data']
    QC_advance = QC_cap * QC_advance_fraction
    QC_advance.name = 'QC_advance'
    
    prmt.QC_advance_MI = convert_ser_to_df_MI(QC_advance)

    # ~~~~~~~~~~~~~~~~~~~~

    # calculate reserve quantities, using reserve fraction in input file, multiplied by cap amounts
    QC_APCR_fraction = QC_cap_data[QC_cap_data['name']=='QC_APCR_fraction'].set_index('year')['data']
    QC_APCR = QC_cap * QC_APCR_fraction
    QC_APCR.name = 'QC_APCR'
    
    prmt.QC_APCR_MI = convert_ser_to_df_MI(QC_APCR)

    # assume that QC will *not* increase its APCR
    # (even though CA did raise its APCR for 2021-2030, from the Oct 2017 to the Apr 2019 regulations)
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    # no return; sets prmt.QC_cap, prmt.QC_advance_MI, prmt.QC_APCR_MI
# end of get_QC_inputs


# In[ ]:


def get_QC_allocation_data():
    """
    From input file, import full data set on QC allocations.
    
    Separated by emissions year, date of allocation, and type of allocation (initial, true-up #1, etc.).
    
    """
    
    logging.info(f"initialize: {inspect.currentframe().f_code.co_name} (start)")

    # get more detailed allocation data (for hindcast)
    df = pd.read_excel(prmt.input_file, sheet_name='QC allocations')
    
    # drop all rows completely empty; empty rows may be caused by openpyxl
    df = df.dropna(how='all')
    
    # convert units to MMTCO2e
    df['quant'] = df['quantity to date']/1e6
       
    df = df.rename(columns={'allocation for emissions year': 'emission_year', 
                            'allocation type (cumulative up to stated allocation)': 'alloc_type',
                            'allocation quarter': 'allocation_quarter',
                           })
    
    df['allocation_quarter'] = pd.to_datetime(df['allocation date']).dt.to_period('Q')
    
    df = df.drop(['allocation date', 'quantity to date', 'quantity on date for true-ups', 'notes', 'units'], axis=1)
    
    df = df.set_index(['emission_year', 'alloc_type', 'allocation_quarter'])
    df = df.dropna()
    
    QC_alloc_hist = df
    # local variable; set equal to object attribute at end of function
    
    # ~~~~~~~~~~~~~~~~~~~~~~
    # isolate initial allocations
    QC_alloc_initial = QC_alloc_hist.loc[QC_alloc_hist.index.get_level_values('alloc_type')=='initial']
    QC_alloc_initial.index = QC_alloc_initial.index.droplevel('alloc_type')
    
    # make projection for initial allocations
    # take most recent historical data, assume future initial allocations will scale down with cap
    last_year = QC_alloc_initial.index.get_level_values('emission_year').max()

    df = QC_alloc_initial.loc[QC_alloc_initial.index.get_level_values('allocation_quarter').year==last_year]
    QC_alloc_initial_last_year = df['quant'].sum()
    
    # initialize and clear values
    QC_alloc_initial_proj = QC_alloc_initial.copy() # initialize
    QC_alloc_initial_proj['quant'] = float(0)
    QC_alloc_initial_proj = QC_alloc_initial_proj.loc[QC_alloc_initial_proj['quant']>0]
    
    # use cap_adjustment_factor
    # assume the initial allocations will always be in Q1
    for year in range(last_year+1, 2030+1):
        cap_adjustment_ratio = prmt.QC_cap.at[year]/prmt.QC_cap.at[last_year]
        QC_alloc_initial_proj_quant = QC_alloc_initial_last_year * cap_adjustment_ratio
        QC_alloc_initial_proj.at[(year, quarter_period(f'{year}Q1')), 'quant'] = QC_alloc_initial_proj_quant
    
    QC_alloc_initial = QC_alloc_initial.append(QC_alloc_initial_proj)
    QC_alloc_initial = QC_alloc_initial.sort_index()
    # local variable; set equal to object attribute at end of function
    
    # ~~~~~~~~~~~~~~~~~~~~~~
    # calculate true-ups for each distribution from cumulative data reported
    # (use diff to calculate difference between a given data point and previous one)
    # (each set has an initial value before true-ups, so diff starts with diff between initial and true-up #1)
    QC_alloc_trueups = QC_alloc_hist.groupby('emission_year').diff().dropna()
    QC_alloc_trueups.index = QC_alloc_trueups.index.droplevel('alloc_type')
    
    # make projection for true-up allocations, following after latest year with a first true-up (in Q3)
    Q3_trueup_mask = QC_alloc_trueups.index.get_level_values('allocation_quarter').quarter==3
    Q3_trueups = QC_alloc_trueups.copy().loc[Q3_trueup_mask]
    not_Q3_trueups = QC_alloc_trueups.loc[~Q3_trueup_mask]
    
    last_year = Q3_trueups.index.get_level_values('emission_year').max()
    
    # first true-ups are 25% of total estimated allocation, whereas initial alloc are 75% of total est. alloc
    # therefore first true-ups are one-third (25%/75%) of the initial true-up
    # in projection, do not model any further true-ups after first true-ups (assume no revisions of allocation)
    for year in range(last_year+1, 2030+1):
        init_last_year_plus1 = QC_alloc_initial.at[(year, f'{year}Q1'), 'quant']
        first_trueup_quant = init_last_year_plus1 / 3
        Q3_trueups.at[(year, quarter_period(f'{year+1}Q3')), 'quant'] = first_trueup_quant
        
    Q3_trueups = Q3_trueups.dropna()
    
    # recombine:
    QC_alloc_trueups = pd.concat([Q3_trueups, not_Q3_trueups], sort=True)
    QC_alloc_trueups = QC_alloc_trueups.sort_index()
    
    # separate negative true-ups
    QC_alloc_trueups = QC_alloc_trueups.loc[QC_alloc_trueups['quant']>0]
    QC_alloc_trueups_neg = QC_alloc_trueups.loc[QC_alloc_trueups['quant']<0]

    # local variable; set equal to object attribute at end of function
    # ~~~~~~~~~~~~~~~~~~~~~
    # calculate APCR for allocations & modify above
    APCR_alloc_distrib = calculate_QC_alloc_from_APCR__CIR_and_reserve_sales()
    
    df = pd.concat([QC_alloc_trueups, APCR_alloc_distrib], axis=1)
    df['quant_non_APCR'] = df['quant'].sub(df['quant_APCR'], fill_value=0)
    df.index.names = ['emission_year', 'allocation_quarter']
    
    # create new variable 
    QC_alloc_trueups_non_APCR = df
    
    # ~~~~~~~~~~~~~~~~~~~~~
    # also calculate full (est.) allocation for projection years
    # used for setting aside this quantity from cap, for initial alloc and first true-up
    
    # calculate full allocation (100%) from the initial allocation (75% of full quantity)
    QC_alloc_full_proj = QC_alloc_initial_proj * 100/75
    # local variable; set equal to object attribute at end of function
    
    # ~~~~~~~~~~~~~~~~~~~~~
    # QC allocations (initial + true-up) annual sums, by year distributed
    # (not used within the model, but useful for comparing against other projections)
    df = pd.concat([QC_alloc_initial, QC_alloc_trueups], axis=1)
    df.index = df.index.droplevel()
    df.index = df.index.year
    df = df.groupby(df.index).sum()
    df = df.sum(axis=1)
    QC_alloc_sums_by_year_dist = df
    
    # ~~~~~~~~~~~~~~~~~~~~~
    # set object attributes
    prmt.QC_alloc_hist = QC_alloc_hist
    prmt.QC_alloc_initial = QC_alloc_initial
    prmt.QC_alloc_trueups = QC_alloc_trueups # positive true-ups only
    prmt.QC_alloc_trueups_non_APCR = QC_alloc_trueups_non_APCR # positive true-ups only
    prmt.QC_alloc_trueups_neg = QC_alloc_trueups_neg
    prmt.QC_alloc_full_proj = QC_alloc_full_proj
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (end)")
    
    # no return; func sets object attributes
# end of get_QC_allocation_data


# In[ ]:


def calculate_QC_alloc_from_APCR__CIR_and_reserve_sales():
    """
    Calculates distributions of APCR allowances for allocations, based on CIRs and input sheet for reserve sales.
    
    CIRs show how many APCR allowances entered private hands, cumulatively.
    
    This function subtracts any reserve sales, based on input sheet "reserve sales".
    """
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (start)")
    
    # get APCR quantities distributed (from CIRs), either for allocations or reserve sales
    # (values are cumulative; units MMTCO2e)
    APCR_CIR = prmt.CIR_historical.xs(
        ('Non-Vintage Price Containment Reserve Allowances', 'APCR'), 
        level=(1, 2))

    df = APCR_CIR.copy()

    # fill in zero values for early quarters before start of CIRs, and for initial CIR quarter (2014Q2)
    early_quarters = ['2012Q4', '2013Q1', '2013Q2', '2013Q3', '2013Q4', '2014Q1', '2014Q2']
    for quarter in early_quarters:
        df.at[quarter_period(quarter)] = 0

    df = df.sort_index()
    df = df.diff()
    # set initial value as zero for diff
    df.at[quarter_period('2012Q4')] = 0

    # cumulative quarterly APCR distributions (for allocations or reserve sales)
    APCR_CIR_q = df[['General', 'Compliance', 'Retirement']].sum(axis=1)

    # ~~~~~~~~~~~~~~
    # subtract reserve sales from APCR quantities distributed
    # remainder is QC APCR distributions for allocations
    df = pd.DataFrame(APCR_CIR_q.sub(prmt.reserve_PCU_sales_q_hist, fill_value=0))
    df = df.rename(columns={0: 'quant_APCR'})
    
    # ~~~~~~~~~~~~~~
    # handle anomaly:
    # 47,454 allowances actually moved out of APCR in 2018Q3, and into government holding account
    # then these were moved to private accounts in 2018Q4
    # so shift timing of the transfer out from 2018Q4 to 2018Q3
    
    # this fixes a problem later in which the APCR allocation distribution doesn't correspond to an allocation
    # known from the QC allocation reports (recorded in data input file sheet 'QC allocations')
    
    df = df.reset_index()
    index_for_anomaly = df.loc[df['date'] == quarter_period('2018Q4')].index    
    df.at[index_for_anomaly, 'date'] = quarter_period('2018Q3')
    df = df.groupby('date').sum()
    
    # ~~~~~~~~~~~~~~~
    # attribute to particular emissions years (allocation intended to help cover emissions for a particular year)
    df['emission_year'] = df.index.year - 1
    
    # create new index with 'date' & 'emission_year'
    df = df.set_index([df['emission_year'], df.index]).drop('emission_year', axis=1)
    
    # keep only rows with a non-zero value
    df = df.loc[df['quant_APCR'] > 0]
    
    # ~~~~~~~~~~~~~~
    APCR_alloc_distrib = df
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (end)")
    
    return(APCR_alloc_distrib)
# end of calculate_QC_alloc_from_APCR__CIR_and_reserve_sales


# In[ ]:


def read_emissions_historical_data():   
    """
    Reads historical data on covered emissions and compliance obligations.
    
    In some CARB data sets, EIM Outstanding Emissions have been listed under compliance obligations.
    
    The data used here for compliance obligations excludes EIM Outstanding Emissions.
    """
    
    logging.info(f"initialize: {inspect.currentframe().f_code.co_name} (start)")
    
    df = pd.read_excel(prmt.input_file, sheet_name='emissions & obligations')

    # drop all rows completely empty; empty rows may be caused by openpyxl
    df = df.dropna(how='all')
    
    df = df[['year',
             'CA covered emissions', 
             'CA compliance obligations (excludes EIM Outstanding)', 
             'QC covered emissions']]
    df = df.rename(columns={'CA compliance obligations (excludes EIM Outstanding)': 
                            'CA obligations'})
    
    # set index; then set type as int (to avoid error later)
    df = df.set_index('year')
    
    df.index = df.index.astype(int)
    
    # convert units from tCO2e to MMtCO2e
    df = df / 1e6
    
    # set prmt.emissions_and_obligations for historical data; also used in emissions_projection
    prmt.emissions_and_obligations = df
    
    logging.info(f"initialize: {inspect.currentframe().f_code.co_name} (end)")
    # no return
# end of read_emissions_historical_data


# In[ ]:


def read_reserve_sales_historical():
    """
    Reads data on quarterly reserve sales from data input file.
    
    Result prmt.reserve_PCU_sales_q_hist used in:
    * calculate_QC_alloc_from_APCR__CIR_and_reserve_sales
    * private_bank_annual_metric_model_method
    
    """
    
    # get quarterly reserve sales from input sheet
    # units in input sheet are tCO2e
    df = pd.read_excel(prmt.input_file, sheet_name='reserve & PCU sales')
    df['date of sale'] = pd.to_datetime(df['date of sale']).dt.to_period('Q')
    df = df.set_index('date of sale')
    
    numerical_cols = list(df.columns)
    numerical_cols.remove('units')
    
    for col in numerical_cols:
        # convert from units of tCO2e to MMtCO2e
        df[col] = df[col] / 1e6
    
    # ~~~~~~~~~~~~~~
    prmt.CA_reserve_sales_q_hist = df['subtotal CA reserve & PCU sales'].sub(
        df['CA reserve sales, post-2020 Price Ceiling Units'], fill_value=0)
    
    prmt.QC_reserve_sales_q_hist = df['subtotal QC reserve sales']
    
    # ~~~~~~~~~~~~~~
    # exclude subtotal columns, total column, and units column
    # (remaining columns are only those for data entered by user)
    df2 = df.drop('units', axis=1)
    for col in df2.columns:
        if 'total' in col:
            df2 = df2.drop(col, axis=1)

    # drop rows that have no data entered in any column; 
    # then the maximum index entry is the latest date with historical data
    sale_latest_date = df2.dropna(how='all').index.max()
    # ~~~~~~~~~~~~~~
    
    df = df.loc[:sale_latest_date]
    
    ser = df['total CA + QC reserve & PCU sales'].astype(float)
    ser.name = 'reserve & PCU sales'
    ser.index.name = 'date'
    
    prmt.reserve_PCU_sales_q_hist = ser
    
    # no return
# end of read_reserve_sales_historical


# ## Functions: Tests
# * test_consistency_inputs_CIR_vs_qauct
# * test_consistency_inputs_annual_data
# * test_consistency_CA_alloc
# * test_cols_and_indexes_before_transfer
# * test_for_duplicated_indices
# * test_if_value_is_float_or_np_float64
# * test_for_negative_values
# * test_conservation_during_transfer
# * test_conservation_simple
# * test_conservation_against_full_budget

# In[ ]:


def test_consistency_inputs_CIR_vs_qauct(CA_alloc_latest_yr, QC_alloc_latest_yr):
    """
    Checks for consistency of dates in data inputs of Compliance Instrument Reports (CIRs) vs quarterly auction data.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")

    # calculate one quarter difference, for use in comparisons below
    one_QuarterEnd = quarter_period('2000Q2') - quarter_period('2000Q1')
    
    # get the first CIR sheet name
    CIR_sheet_name_first = pd.ExcelFile(prmt.CIR_excel).sheet_names[0].replace(" ", "")    
    CIR_sheet_name_first_date = pd.to_datetime(CIR_sheet_name_first).to_period('Q')

    # get the last CIR sheet name
    CIR_sheet_name_last = pd.ExcelFile(prmt.CIR_excel).sheet_names[-1].replace(" ", "")
    CIR_sheet_name_last_date = pd.to_datetime(CIR_sheet_name_last).to_period('Q')

    # check that CIR sheet names are in reverse chronological order
    if CIR_sheet_name_first_date.year > CIR_sheet_name_last_date.year:
        pass
    else:
        print(f"{prmt.test_failed_msg} Order of CIR sheets need to be in reverse chronological order, but it appears they are not.")
        print(pd.ExcelFile(prmt.CIR_excel).sheet_names)

    # get the year from CIR_sheet_name_first; compare against prmt.latest_hist_aauct_yr
    if prmt.latest_hist_aauct_yr - CIR_sheet_name_first_date.year == 1:
        # this could be the case at the end of a year or beginning of the next year, 
        # when all annual data is out before the first CIR has been released
        # check that the latest CIR is from Q4 of previous year
        if CIR_sheet_name_first_date.quarter == 4:
            pass
        else:
            print(f"{prmt.test_failed_msg} The CIR file appears to be out-of-date.")
            print(f"Latest CIR date: {CIR_sheet_name_first}. Latest historical allocation-auction data year: {prmt.latest_hist_aauct_yr}")
            
    elif prmt.latest_hist_aauct_yr - CIR_sheet_name_first_date.year == 0:
        if prmt.latest_hist_qauct_date - CIR_sheet_name_first_date == one_QuarterEnd:
            # CIR is one quarter behind the quarterly auction data
            pass
        
        elif prmt.latest_hist_qauct_date - CIR_sheet_name_first_date == (0 * one_QuarterEnd):
            # CIR has same date as the quarterly auction data
            pass

        else:
            print(f"{prmt.test_failed_msg} There is a problem with data inputs.")
            print(f"Latest CIR date: {CIR_sheet_name_first}. Latest quarterly auction data: {prmt.latest_hist_qauct_date}")

    elif prmt.latest_hist_aauct_yr - CIR_sheet_name_first_date.year == -1:
        # for latest year, a CIR is out, but one or more annual data points isn't entered yet
        # by the time of publication of first CIR for a given year (e.g., 2019Q1 in April 2019),
        # all the annual data for 2019 should be available
        print(f"{prmt.test_failed_msg} There is a problem with data inputs.")
        print(f"It may be that some annual data is missing for {CIR_sheet_name_first_date.year} (for auction quantities and/or allocation quantities).")
        print(f"latest consign year: {prmt.consign_ann_hist.index.max()}, CA_alloc_latest_yr: {CA_alloc_latest_yr}, QC_alloc_latest_yr: {QC_alloc_latest_yr}")
                
    else:                  
        # there is a problem with the data
        print(f"{prmt.test_failed_msg} There is a problem with data inputs (unknown edge case).")
        print(f"CIR_sheet_name_first_date.year: {CIR_sheet_name_first_date.year}; prmt.latest_hist_aauct_yr: {prmt.latest_hist_aauct_yr}")
        print(f"Latest CIR date: {CIR_sheet_name_first}. Latest quarterly auction data: {prmt.latest_hist_qauct_date}")
        
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")


# In[ ]:


def test_consistency_inputs_annual_data(CA_alloc_latest_yr, QC_alloc_latest_yr):
    """
    Checks for consistency of dates in annual data inputs (allocation, consignment, and annual auction data).
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")

    # check whether all three dates match;
    # if not, will still run, but it may be a sign of a problem with data entered in input file

    if prmt.consign_ann_hist.index.max() == CA_alloc_latest_yr:
        pass
        
        if CA_alloc_latest_yr == QC_alloc_latest_yr:
            pass
            
            if QC_alloc_latest_yr == prmt.latest_hist_aauct_yr:
                # all years match
                pass
            else:
                print("{prmt.test_failed_msg} In test_consistency_inputs_annual_data, encountered an unexpected edge case (error #1).") # for UI
        
        elif CA_alloc_latest_yr == QC_alloc_latest_yr + 1:
            # CA alloc data is one year ahead of QC alloc data
            # this is normal, and CA alloc data can be used in calculations, together with projection for QC alloc
            pass
        
        else:
            print("{prmt.test_failed_msg} In test_consistency_inputs_annual_data, encountered an unexpected edge case (error #2).") # for UI

    elif prmt.consign_ann_hist.index.max() == CA_alloc_latest_yr + 1:
        # consignment data is one year ahead of CA alloc data; this is normal
        # consignment data can be used in calculations, together with projection for allocation
        pass
    
        if CA_alloc_latest_yr == QC_alloc_latest_yr + 1:
            # CA alloc data is ahead of QC alloc data
            # this is normal, and CA alloc data can be used in calculations, together with projection for QC alloc
            pass
        
        elif CA_alloc_latest_yr == QC_alloc_latest_yr:
            # CA alloc data is in sync with QC alloc data; this is normal
            pass

        elif CA_alloc_latest_yr < QC_alloc_latest_yr:
            print("{prmt.test_failed_msg} CA allocation data is behind QC allocation data. There should be CA allocation data available.") # for UI
    
        else:
            print("{prmt.test_failed_msg} In test_consistency_inputs_annual_data, encountered an unexpected edge case (error #3).") # for UI
    
    elif prmt.consign_ann_hist.index.max() < CA_alloc_latest_yr:
        print("{prmt.test_failed_msg} CA consignment data is behind allocation data. There should be consignment data available.") # for UI

    else:
        print("{prmt.test_failed_msg} In test_consistency_inputs_annual_data, encountered an unexpected edge case (error #4).") # for UI
        
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")


# In[ ]:


def test_consistency_CA_alloc(CA_alloc_data):
    """
    Test CA allocation data for internal consistency.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    df = CA_alloc_data.copy()
    
    # get years for industrial allocations; includes those with 'industrial_and_legacy_gen_alloc'
    industrial = df[df['name'].str.contains('industrial_')]
    
    # nat_gas_alloc, university_alloc, waste_to_energy_alloc
    nat_gas = df[df['name']=='nat_gas_alloc']
    university = df[df['name'].str.contains('university_')]
    waste_to_energy = df[df['name'].str.contains('waste_to_energy_alloc')]
    
    # not included: legacy_gen_alloc, thermal_output_alloc, LNG_supplier_alloc
    
    alloc_latest_set = [industrial['year'].max(), 
                        nat_gas['year'].max(), 
                        university['year'].max(), 
                        waste_to_energy['year'].max()]
    
    if max(alloc_latest_set) == min(alloc_latest_set):
        # all the years are the same
        pass
    else:
        print(f"{prmt.test_failed_msg} In test_consistency_CA_alloc, the individual components of the allocation are not all up to the same year.") # for UI
        
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")


# In[ ]:


def test_cols_and_indexes_before_transfer(to_acct_MI):
    """
    Before transferring instruments from one account to another, check properties of the df to_acct_MI.
    """
    if prmt.verbose_log == True:
        logging.info(f"{inspect.currentframe().f_code.co_name} (start), for {to_acct_MI}")
    
    # check that to_acct_MI has only 1 column & that it has MultiIndex
    if len(to_acct_MI.columns)==1 and isinstance(to_acct_MI.index, pd.MultiIndex):
        
        if to_acct_MI.index.names == prmt.standard_MI_names:
            pass
        else:
            print(f"{prmt.test_failed_msg} to_acct_MI had MultiIndex, but names did not match standard_MI.")
    
        pass
    
    elif len(to_acct_MI.columns)>1:
        print(f"{prmt.test_failed_msg} df to_acct_MI has more than 1 column. Here's to_acct_MI:")
        print(to_acct_MI)
    
    elif len(to_acct_MI.columns)==0:
        print(f"{prmt.test_failed_msg} df to_acct_MI has no columns. Here's to_acct_MI:")
        print(to_acct_MI)
    
    else: # closing "if len(to_acct_MI.columns)==1..."
        print(f"{prmt.test_failed_msg} Something else going on with df to_acct_MI columns and/or index. Here's to_acct_MI:")
        print(to_acct_MI)
        
    if prmt.verbose_log == True:
        logging.info(f"{inspect.currentframe().f_code.co_name} (end)")


# In[ ]:


def test_for_duplicated_indices(df, parent_fn):
    """
    Test to check a dataframe (df) for duplicated indices, and if any, to show them (isolated and in context).
    """
    
    if prmt.verbose_log == True:
        logging.info(f"{inspect.currentframe().f_code.co_name}")

    dups = df.loc[df.index.duplicated(keep=False)]
    
    if dups.empty == False:
        print(f"When running {parent_fn}, test_for_duplicated_indices found duplicated indices, shown below:") # for UI
        print(dups) # for UI
        
        # get the acct_names that show up in duplicates
        dup_acct_names = dups.index.get_level_values('acct_name').unique().tolist()
        
    elif df[df.index.duplicated(keep=False)].empty == True:
        # test passed: there were no duplicated indices
        pass
    else:
        print(f"{prmt.test_failed_msg} During {parent_fn}, test for duplicated indices may not have run.") # for UI
        
    if prmt.verbose_log == True:
        logging.info(f"{inspect.currentframe().f_code.co_name} (end)")


# In[ ]:


def test_if_value_is_float_or_np_float64(test_input):
    
    if prmt.verbose_log == True:
        logging.info(f"{inspect.currentframe().f_code.co_name}")

    if isinstance(test_input, float)==False and isinstance(test_input, np.float64)==False:
        print(f"{prmt.test_failed_msg} Was supposed to be a float or np.float64. Instead was type: %s" % type(test_input))
    else:
        pass


# In[ ]:


def test_for_negative_values(df, parent_fn):
    """
    Checks whether specified df (usually all_accts) has any rows with negative values.
    
    If so, it finds values of acct_name for those rows. 
    
    Fn can show the full account for those with negative rows (need to make sure that code is uncommented).
    """
    
    if prmt.show_neg_msg == True:
    
        if prmt.verbose_log == True:
            logging.info(f"{inspect.currentframe().f_code.co_name} (start)")

        neg_cut_off = prmt.neg_cut_off

        non_deficits = df.loc[df.index.get_level_values('status')!='deficit']
        neg_values = non_deficits.loc[non_deficits['quant']<-abs(neg_cut_off)]

        if len(neg_values) > 0:
            print()
            print("Warning" + f"! During {parent_fn}, negative values in all_accts (other than deficits).")
            print(neg_values)
            print()

            # get acct_names with negative values
            neg_acct_names = neg_values.index.get_level_values('acct_name').unique().tolist()

            for neg_acct_name in neg_acct_names:
                print(f"There were negative values in acct_name {neg_acct_name}; here's the full account:")
                print(df.loc[df.index.get_level_values('acct_name')==neg_acct_name])

        else:
            pass
        
    else: # prmt.show_neg_msg == False
        pass


# In[ ]:


def test_conservation_during_transfer(all_accts, all_accts_sum_init, remove_name):
    """
    Test for conservation of allowances after a function has transferred allowances between accounts.
    """
    if prmt.verbose_log == True:
        logging.info(f"{inspect.currentframe().f_code.co_name}")
    
    # check for conservation of instruments within all_accts
    all_accts_end_sum = all_accts['quant'].sum()
    diff = all_accts_end_sum - all_accts_sum_init
    if abs(diff) > 1e-7:
        print(f"{prmt.test_failed_msg} For {cq.date}, in {inspect.currentframe().f_code.co_name}, instruments were not conserved. Diff: %s" % diff)
        print(f"Was for df named {remove_name}")
    else:
        pass


# In[ ]:


def test_conservation_simple(df, df_sum_init, parent_fn):
    """
    Test for conservation of allowances by comparing initial quantity against final quantity.
    
    Initial is set as local variable at the start of each function.
    """
    if prmt.verbose_log == True:
        logging.info(f"{inspect.currentframe().f_code.co_name}")
    
    df_sum_final = df['quant'].sum()
    diff = df_sum_final - df_sum_init
    
    if abs(diff) > 1e-7:
        print(f"{prmt.test_failed_msg} Simple conservation test for {cq.date}: Allowances not conserved in {parent_fn}.")
    else:
        pass


# In[ ]:


def test_conservation_against_full_budget(all_accts, juris, parent_fn):
    """
    Additional conservation check, using total allowance budget.
    """
    
    if prmt.verbose_log == True:
        logging.info(f"{inspect.currentframe().f_code.co_name}")
    
    if juris == 'CA':
        if cq.date <= quarter_period('2017Q4'):
            budget = prmt.CA_cap.loc[2013:2020].sum()
            
        # additional allowances vintage 2021-2030 assumed to have been added at start of 2018Q1 (Jan 1)
        # (all we know for sure is they were first included in 2017Q4 CIR, in early Jan 2018)
        # budget will be the same through 2030Q4, as far as we know at this point
        # but in some future year, perhaps 2028, post-2030 allowances would likely be added to the system
        elif cq.date == quarter_period('2018Q1'):
            budget = prmt.CA_cap.loc[2013:2030].sum()
        
        elif cq.date >= quarter_period('2018Q2') and cq.date <= quarter_period('2030Q4'):
            # net flow from ON that is credited toward CA is same as cap adjustment CA made in 2019Q2
            budget = prmt.CA_cap.loc[2013:2030].sum() + prmt.CA_cap_adj_for_ON_net_flow
            
        else:
            print("Post-2030 period; C&T program not authorized for this period.")
            
    elif juris == 'QC':
        if cq.date >= quarter_period('2013Q4') and cq.date <= quarter_period('2014Q1'):
            budget = prmt.QC_cap.loc[2013:2020].sum()

        elif cq.date >= quarter_period('2014Q2') and cq.date <= quarter_period('2017Q4'):
            # add Early Action allowances to budget
            budget = prmt.QC_cap.loc[2013:2020].sum() + 2.040026 
            # units: MMTCO2e

        # additional allowances vintage 2021-2030 assumed to have been added at start of 2018Q1 (Jan 1)
        # (all we know for sure is they were first included in 2017Q4 CIR)
        # budget will be the same through 2030Q4, as far as we know at this point
        # but in some future year, perhaps 2028, post-2030 allowances would likely be added to the system
        elif cq.date == quarter_period('2018Q1'):
            budget = prmt.QC_cap.loc[2013:2030].sum() + 2.040026
            # units: MMTCO2e

        elif cq.date >= quarter_period('2018Q2') and cq.date <= quarter_period('2030Q4'):
            # net flow from ON that is credited toward QC is same as cap adjustment QC made in 2019Q2
            budget = prmt.QC_cap.loc[2013:2030].sum() + 2.040026 + prmt.QC_cap_adj_for_ON_net_flow
            # units: MMTCO2e
            
        else:
            print("Error" + "! QC budget not defined after 2030.")
            
    diff = all_accts['quant'].sum() - budget

    if abs(diff) > 1e-7:
        print(f"{prmt.test_failed_msg} Full-budget conservation test for {cq.date}: Allowances not conserved in {parent_fn}.") # for UI
        print(f"(Final value minus full budget ({budget} M) was: {diff} M.)") # for UI
        # print(f"Was for auct_type: {auct_type}") # for UI
    else:
        pass
    
# end of test_conservation_against_full_budget


# ## Functions: Main processes
# (many also used for QC; however, list below excludes functions unique to QC, which are later in the model)
# * initialize_CA_auctions
# * create_annual_budgets_in_alloc_hold
# * transfer__from_alloc_hold_to_specified_acct
# * transfer_CA_alloc__from_alloc_hold
# * consign_groupby_sum_in_all_accts
# * transfer_consign__from_limited_use_to_auct_hold_2012Q4_and_make_available
# * process_CA_quarterly
#   * CA_state_owned_make_available
#   * redesignate_unsold_advance_as_advance
#   * process_auction_adv_all_accts
#   * unsold_update_status
#   * consign_make_available_incl_redes
#   * redesignate_unsold_current_auct
#     * calculate_max_cur_reintro
#     * reintro_update_unsold_1j
#   * process_auction_cur_CA_all_accts
#   * process_reserve_sales_historical
#   * adv_unsold_to_cur_all_accts
#   * transfer__from_VRE_acct_to_retirement
#   * transfer_consign__from_limited_use_to_auct_hold
# * transfer_CA_alloc__from_ann_alloc_hold_to_general
# * transfer_cur__from_alloc_hold_to_auct_hold_first_principles
# * cur_upsample_avail_state_owned_first_principles
# * upsample_advance_all_accts

# In[ ]:


def initialize_CA_auctions(all_accts):
    """
    Initializes first CA auction in 2012Q4 (also first for any juris in WCI market).
    
    This auction was anomalous, in that:
    1. There was only this single auction in 2012.
    2. The 2012Q4 current auction had available only consignment allowances (and no state-owned), 
    and they were a vintage ahead (2013).
    3. The 2012Q4 advance auction had available all vintage 2015 allowances at once.
    
    This function runs only once in each model run.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # create CA allowances v2013-v2020, put into alloc_hold
    all_accts = create_annual_budgets_in_alloc_hold(all_accts, prmt.CA_cap.loc[2013:2020])
    
    # pre-test for conservation of allowances
    # (sum_init has to be after creation of allowances in previous step)
    all_accts_sum_init = all_accts['quant'].sum()
    
    # transfer APCR allowances out of alloc_hold, into APCR_acct (for vintages 2013-2020)
    logging.info(f"running transfer__from_alloc_hold_to_specified_acct for prmt.CA_APCR_2013_2020_MI")
    all_accts = transfer__from_alloc_hold_to_specified_acct(
        all_accts, prmt.CA_APCR_2013_2020_MI, 2013, 2020)

    # transfer advance into auct_hold
    logging.info(f"running transfer__from_alloc_hold_to_specified_acct for prmt.CA_advance_MI")
    all_accts = transfer__from_alloc_hold_to_specified_acct(all_accts, prmt.CA_advance_MI, 2013, 2020)

    # transfer VRE allowances out of alloc_hold, into VRE_acct (for vintages 2013-2020)
    logging.info(f"running transfer__from_alloc_hold_to_specified_acct for prmt.VRE_reserve_MI")
    all_accts = transfer__from_alloc_hold_to_specified_acct(all_accts, prmt.VRE_reserve_MI, 2013, 2020)

    # allocations:
    # transfer alloc non-consign into ann_alloc_hold & alloc consign into limited_use    
    # alloc v2013 transferred in 2012Q4, before Q4 auction (same pattern as later years)
    # transfer out of alloc_hold to ann_alloc_hold or limited_use
    # (appropriate metadata is assigned to each set of allowances by convert_ser_to_df_MI_alloc)
    
    # transfer all the allocations at once (for one vintage)
    # (fn only processes one vintage at a time)
    all_accts = transfer_CA_alloc__from_alloc_hold(all_accts, prmt.CA_alloc_MI_all)

    # ~~~~~~~~~~~~~~~~~
    # CURRENT AUCTION (2012Q4 anomaly):
    # for current auction in 2012Q4, no state-owned allowances; only consign
    # consign annual amount in limited_use: get rid of distinctions between types of consign & groupby sum 
    all_accts = consign_groupby_sum_in_all_accts(all_accts)

    # put consignment allowances into auct_hold & make available
    all_accts = transfer_consign__from_limited_use_to_auct_hold_2012Q4_and_make_available(all_accts)
    
    # ~~~~~~~~~~~~~~~~~
    # ADVANCE AUCTION (2012Q4 anomaly):
    # remember: all vintage 2015 allowances were available at once in this auction
    # get all allowances aside for advance in auct_hold that are vintage 2015 (cq.date.year+3)
    adv_new_mask1 = all_accts.index.get_level_values('acct_name')=='auct_hold'
    adv_new_mask2 = all_accts.index.get_level_values('auct_type')=='advance'
    adv_new_mask3 = all_accts.index.get_level_values('vintage')==(cq.date.year+3)
    adv_new_mask = (adv_new_mask1) & (adv_new_mask2) & (adv_new_mask3)
    adv_new = all_accts.loc[adv_new_mask]
    all_accts_remainder = all_accts.loc[~adv_new_mask]
    
    # for this anomalous advance auction, all of these allowances were available in one auction
    # update metadata: change 'date_level' to '2012Q4' & status' to 'available'
    mapping_dict = {'date_level': quarter_period('2012Q4'),
                    'status': 'available'}
    adv_new = multiindex_change(adv_new, mapping_dict)
    
    # ~~~~~~~~~~~~~~~~~
    # recombine to create new version of all_accts
    all_accts = pd.concat([adv_new, all_accts_remainder], sort=True)
    
    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)
# end of initialize_CA_auctions


# In[ ]:


def create_annual_budgets_in_alloc_hold(all_accts, ser):
    """
    Creates allowances for each annual budget, in the Allocation Holding account (alloc_hold).
    
    Does this for each juris.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    df = pd.DataFrame(ser)
    
    if len(df.columns) == 1:
        df.columns = ['quant']
    else:
        print("Error" + "! In convert_cap_to_MI, len(df.columns) == 1 was False.")
        
    df.index.name = 'vintage'
    df = df.reset_index()

    # metadata for cap
    df['acct_name'] = 'alloc_hold'
    df['juris'] = ser.name.split('_')[0]
    df['inst_cat'] = 'cap'
    # vintage already assigned above
    df['auct_type'] = 'n/a'
    df['newness'] = 'n/a'
    df['status'] = 'n/a'
    df['date_level'] = prmt.NaT_proxy
    df['unsold_di'] = prmt.NaT_proxy
    df['unsold_dl'] = prmt.NaT_proxy
    df['units'] = 'MMTCO2e'
    
    df = df.set_index(prmt.standard_MI_names)
    
    all_accts = all_accts.append(df)
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)
# end of create_annual_budgets_in_alloc_hold


# In[ ]:


def transfer__from_alloc_hold_to_specified_acct(all_accts, to_acct_MI, vintage_start, vintage_end):   
    """
    Transfers allocations from allocation holding account (alloc_hold) to other accounts.
    
    Works for APCR (to APCR_acct), VRE (to VRE_acct), and advance (to auct_hold).
    
    Destination account is contained in to_acct_MI metadata.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    all_accts_sum_init = all_accts['quant'].sum()
    vintage_range = range(vintage_start, vintage_end+1)
    
    # check that to_acct_MI is a df with one column and MultiIndex
    if prmt.run_tests == True:
        test_cols_and_indexes_before_transfer(to_acct_MI)            
    
    # rename column of to_acct_MI, whatever it is, to 'quant'
    # filter to vintages specified
    to_acct_MI.columns = ['quant']
    to_acct_MI_in_vintage_range = to_acct_MI[to_acct_MI.index.get_level_values('vintage').isin(vintage_range)]
    
    # ~~~~~~~~~~~~~~~~
    # create df named remove, which is negative of to_acct_MI
    remove = -1 * to_acct_MI_in_vintage_range.copy()

    # set indices in remove df (version of to_acct_MI) to be same as from_acct
    mapping_dict = {'acct_name': 'alloc_hold', 
                    'inst_cat': 'cap', 
                    'auct_type': 'n/a', 
                    'newness': 'n/a', 
                    'status': 'n/a'}
    remove = multiindex_change(remove, mapping_dict)

    # ~~~~~~~~~~~~~~~~
    # if APCR, sum over all vintages, change vintage to 2200 (proxy for non-vintage)
    # then groupby sum to combine all into one set
    
    inst_cat_name = to_acct_MI.index.get_level_values('inst_cat').unique().tolist()
    
    if inst_cat_name == ['APCR']:
        mapping_dict = {'vintage': 2200}
        to_acct_MI_in_vintage_range = multiindex_change(to_acct_MI_in_vintage_range, mapping_dict)
        to_acct_MI_in_vintage_range = to_acct_MI_in_vintage_range.groupby(level=prmt.standard_MI_names).sum()

    elif len(inst_cat_name) != 1:
        print("Error" + f"! Was intended to be only one name, for APCR. inst_cat_name: {inst_cat_name}")
    
    else:
        pass

    # ~~~~~~~~~~~~~~~

    all_accts = pd.concat([all_accts, remove, to_acct_MI_in_vintage_range], 
                          sort=True).groupby(level=prmt.standard_MI_names).sum()
    
    if prmt.run_tests == True:
        name_of_allowances = to_acct_MI.index.get_level_values('inst_cat').unique().tolist()[0]
        test_conservation_during_transfer(all_accts, all_accts_sum_init, name_of_allowances)
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")

    return(all_accts)
# end of transfer__from_alloc_hold_to_specified_acct


# In[ ]:


def transfer_CA_alloc__from_alloc_hold(all_accts, to_acct_MI):
    """
    Moves allocated allowances from alloc_hold into private accounts (for non-consign) or limited_use (for consign).
    
    The destination account is specified in metadata (index level 'acct_name') in df to_acct_MI.
    
    Runs at the end of each year (except for anomalous years).
    
    Only processes one vintage at a time; vintage is cq.date.year + 1
    
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")

    all_accts_sum_init = all_accts['quant'].sum()

    if prmt.run_tests == True:
        test_cols_and_indexes_before_transfer(to_acct_MI)

    # change column name of to_acct_MI, but only if to_acct_MI is a df with one column and MultiIndex
    # rename column of to_acct_MI, whatever it is, to 'to_acct_MI_quant'
    to_acct_MI.columns = ['quant']
    
    # filter to specific vintage
    vintage_to_allocate = cq.date.year+1
    to_acct_MI_1v = to_acct_MI[to_acct_MI.index.get_level_values('vintage')==(vintage_to_allocate)]
    
    # set value of CA_latest_year_allocated; used for setting vintage of allowances retired for bankruptcy
    # (see function retire_for_bankruptcy)
    prmt.CA_latest_year_allocated = vintage_to_allocate
    
    # create df named remove, which is negative of to_acct_MI
    remove = -1 * to_acct_MI_1v

    # set indices in remove df (version of to_acct_MI) to be same as from_acct
    mapping_dict = {'acct_name': 'alloc_hold', 
                    'inst_cat': 'cap', 
                    'auct_type': 'n/a', 
                    'newness': 'n/a', 
                    'status': 'n/a'}
    remove = multiindex_change(remove, mapping_dict)

    # separate out any rows with negative values
    all_accts_pos = all_accts.loc[all_accts['quant']>0]
    all_accts_neg = all_accts.loc[all_accts['quant']<0]
    
    # combine dfs to subtract from from_acct & add to_acct_MI_1v
    # (groupby sum adds the positive values in all_accts_pos and the neg values in remove)
    all_accts_pos = pd.concat([all_accts_pos, remove, to_acct_MI_1v], sort=False)
    all_accts_pos = all_accts_pos.groupby(level=prmt.standard_MI_names).sum()
    
    # recombine pos & neg
    all_accts = all_accts_pos.append(all_accts_neg)

    if prmt.run_tests == True:
        inst_cat_to_acct = str(to_acct_MI.index.get_level_values('inst_cat').unique())
        test_conservation_during_transfer(all_accts, all_accts_sum_init, inst_cat_to_acct)
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)
# transfer_CA_alloc__from_alloc_hold


# In[ ]:


def consign_groupby_sum_in_all_accts(all_accts):
    """
    Sums all types of consignment allowances and assigns them inst_cat 'consign'.
    
    This overwrites old values of inst_cat (i.e., 'elec_alloc_IOU', etc.).
    
    Then this sums across the types of consignment allowances, to get a single annual value for consignment.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # pre-test for conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    mask1 = all_accts.index.get_level_values('acct_name')=='limited_use'
    mask2 = all_accts['quant'] > 0
    mask = (mask1) & (mask2)
    
    consigned = all_accts.loc[mask]
    remainder = all_accts.loc[~mask]
    
    mapping_dict = {'inst_cat': 'consign'}
    consigned = multiindex_change(consigned, mapping_dict)
    consigned = consigned.groupby(level=prmt.standard_MI_names).sum() 
    
    all_accts = consigned.append(remainder)
    
    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)
# consign_groupby_sum_in_all_accts


# In[ ]:


def transfer_consign__from_limited_use_to_auct_hold_2012Q4_and_make_available(all_accts):
    """
    Specified quantities in limited_use account of a particular vintage will be moved to auct_hold.

    Only for anomalous auction 2012Q4 (CA-only), in which vintage 2013 consignment were sold at current auction.
    """       
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # pre-test for conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    # look up quantity consigned in 2012Q4 from historical record (consign_2012Q4_quant)
    # (this anomalous fn runs only when cq.date = 2012Q4)
    consign_new_avail_hist = create_qauct_new_avail_consign()

    # get the first row quantity (but only if the date is 2012Q4)
    if consign_new_avail_hist.index.get_level_values('date_level')[0]==quarter_period('2012Q4'):
        consign_2012Q4_quant = consign_new_avail_hist.at[consign_new_avail_hist.index[0], 'quant']
        
        if prmt.run_tests == True: test_if_value_is_float_or_np_float64(consign_2012Q4_quant)
    else:
        print("Error! The df consign_new_avail_hist did not have 2012Q4 as first row; not sorted?")
    
    # get allowances in limited_use, inst_cat=='consign', for specified vintage
    # and calculate sum of that set
    mask1 = all_accts.index.get_level_values('acct_name')=='limited_use'
    mask2 = all_accts.index.get_level_values('inst_cat')=='consign'
    mask3 = all_accts.index.get_level_values('vintage')==cq.date.year+1
    mask = (mask1) & (mask2) & (mask3)
    consign_not_avail = all_accts.loc[mask]
    quant_not_avail = consign_not_avail['quant'].sum()
    
    if prmt.run_tests == True:
        if len(consign_not_avail) != 1:
            print(f"{prmt.test_failed_msg} Expected consign_not_avail to have 1 row. Here's consign_not_avail:")
            print(consign_not_avail)
            print("Here's all_accts.loc[mask1] (limited_use):")
            print(all_accts.loc[mask1])
    else:
        pass
    
    # split consign_not_avail to put only the specified quantity into auct_hold; 
    # rest stays in limited_use
    consign_avail = consign_not_avail.copy()
    
    # consign_avail and consign_not_avail have same index (before consign avail index updated below)
    # use this common index for setting new values for quantity in each df
    # (only works because each df is a single row, as tested for above)
    index_first_row = consign_avail.index[0]
    
    # set quantity in consign_avail, using consign_2012Q4_quant (quantity from historical record)
    consign_avail.at[index_first_row, 'quant'] = consign_2012Q4_quant
    
    # update metadata: put into auct_hold & make them available in cq.date (2012Q4)
    # this fn does not make these allowances available; this will occur in separate fn, at start of cq.date
    mapping_dict = {'acct_name': 'auct_hold', 
                    'newness': 'new', 
                    'date_level': cq.date, 
                    'status': 'available'}
    consign_avail = multiindex_change(consign_avail, mapping_dict)

    # update quantity in consign_not_avail, to remove those consigned for next_q
    consign_not_avail.at[index_first_row, 'quant'] = quant_not_avail - consign_2012Q4_quant
    
    # get remainder of all_accts
    all_accts_remainder = all_accts.loc[~mask]
    
    # recombine to get all_accts again
    all_accts = pd.concat([consign_avail, consign_not_avail, all_accts_remainder], sort=True)
    
    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    return(all_accts)


# In[ ]:


def process_CA_quarterly(all_accts):

    """
    Function that is used in the loop for each quarter, for each juris.
    
    Applies functions defined earlier, as well as additional rules
    
    Order of sales for each jurisdiction set by jurisdiction-specific functions called within process_quarter.
    
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # pre-test for conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    # object "scenario" holds the data for a particular scenario in various attributes (scenario_CA.avail_accum, etc.)

    # START-OF-QUARTER STEPS (INCLUDING START-OF-YEAR) ***********************************************
    
    # process retirements for bankruptcies        
    if cq.date.year >= 2020:
        # assume bankruptcy retirement will occur at start of Q4
        if cq.date.quarter == 4:
            all_accts = retire_for_bankruptcy(all_accts)
        else:
            pass
    
    else:
        # don't process bankruptcy retirement
        # note that for 2019Q2, processed at end of quarter
        pass
        
    # --------------------------------------------
    # process retirements for EIM Outstanding Emissions  
    if cq.date.quarter == 4: 
        if cq.date > quarter_period('2019Q2'):
            # apply Apr 2019 regulations, in which transfers are required to occur prior to compliance event
            # therefore process EIM Outstanding at start of Q4
            all_accts = retire_for_EIM_outstanding(all_accts)
        else:
            pass

    else: # cq.date.quarter != 4
        pass
    # --------------------------------------------
    
    # additional steps at the start of each quarter
    if cq.date.quarter == 1:        
        # start-of-year (Jan 1)
        # on Jan 1 each year, all alloc in ann_alloc_hold are transferred to comp_acct or gen_acct            
        all_accts = transfer_CA_alloc__from_ann_alloc_hold_to_general(all_accts)

        # for current auctions:
        # start-of-year (circa Jan 1): 
        # for current auction, state-owned, vintage==cq.date.year, transfer of annual quantity of allowances
        all_accts = transfer_cur__from_alloc_hold_to_auct_hold_first_principles(all_accts, 'CA')

        # for current auction, state-owned, sum newly avail & unsold adv, upsample, assign 'date_level'
        all_accts = cur_upsample_avail_state_owned_first_principles(all_accts, 'CA')

        # ~~~~~~~~~~~~~~~~~~~~~
        # for advance auctions:
        if cq.date.year >= 2013 and cq.date.year <= 2027:            
            # start-of-year (circa Jan 1): upsample of allowances for advance auction (before Q1 auctions)
            # note that the model does not attempt to simulate advance auctions for vintages after 2027
            all_accts = upsample_advance_all_accts(all_accts)
        else:
            pass
        
        # ~~~~~~~~~~~~~~~~~~~~~

        # for Q1, take snap (~Jan 5):
        # after transferring CA alloc out of ann_alloc_hold (Jan 1)
        # and before Q1 auctions (~Feb 15)
        take_snapshot_CIR(all_accts, 'CA')
    
    else: # cq.date.quarter != 1
        # for Q2-Q4, take snap before auction (no additional steps at the start of each quarter)
        take_snapshot_CIR(all_accts, 'CA')
    
    # END OF START-OF-QUARTER STEPS

    # ADVANCE AUCTION ********************************************************
    # process advance auctions through vintage 2030, which occur in years through 2027
    logging.info(f"within {inspect.currentframe().f_code.co_name}, start of advance auction")
    
    if cq.date.year <= 2027:
        # ADVANCE AUCTION: MAKE AVAILABLE   
        all_accts = CA_state_owned_make_available(all_accts, 'advance')

        # record available allowances (before process auction)
        scenario_CA.avail_accum = avail_accum_append(all_accts, scenario_CA.avail_accum, 'advance')

        # redesignation of unsold advance to later advance auction
        all_accts = redesignate_unsold_advance_as_advance(all_accts, 'CA')

        # ADVANCE AUCTION: PROCESS SALES - CA ONLY AUCTIONS
        all_accts = process_auction_adv_all_accts(all_accts, 'CA')

    else: # cq.date.year > 2027
        pass
    
    # CURRENT AUCTION ********************************************************
    logging.info("within process_quarter, start of current auction")
    
    # CA state-owned current: make available for cq.date
    all_accts = CA_state_owned_make_available(all_accts, 'current')

    # each quarter, prior to auction
    # consignment: for all allowances in auct_hold with date_level == cq.date, change status to 'available'
    all_accts = consign_make_available_incl_redes(all_accts)

    # redesignate any unsold allowances to auction (if any unsold, and if right conditions)
    all_accts = redesignate_unsold_current_auct(all_accts, 'CA')

    # record available allowances (before process auction)
    scenario_CA.avail_accum = avail_accum_append(all_accts, scenario_CA.avail_accum, 'current')

    # process auction
    all_accts = process_auction_cur_CA_all_accts(all_accts)
    
    # FINISHING AFTER AUCTION: ***************************************************************
    
    # handling unsold allowances that hit 24-month limit
    if cq.date <= quarter_period('2018Q4'):
        if cq.date == quarter_period('2018Q3'):
            # process EIM Outstanding at end of Q3
            # (needs to occur before transfer_unsold__from_auct_hold_to_APCR to reproduce 2018Q3 EIM retirement)
            all_accts = retire_for_EIM_outstanding(all_accts)

            # apply Oct 2017 regulations, which did not specify a timing for the transfer
            # this ensures transfer occurs that matches historical data, with transfer shown in 2018Q3 CIR
            # (starting 2019Q3, this function will be applied at start of Q4 each year)
            # check for unsold from current auctions, to roll over to APCR
            all_accts = transfer_unsold__from_auct_hold_to_APCR(all_accts)
            
        else:
            # up to 2018Q4, only retirement for EIM and only transfer of unsold to APCR occurred in 2018Q3
            pass
            
    elif cq.date == quarter_period('2019Q1'):
        # to match historical data, don't transfer unsold to APCR
        pass

    elif cq.date >= quarter_period('2019Q2'):
        # for 2019Q2 and after, process any unsold to APCR after each auction
        all_accts = transfer_unsold__from_auct_hold_to_APCR(all_accts)
        
        # note: this placement will process 2019Q2 historical transfer after the CIR snapshot for 2019Q1
            
    else:
        # don't do anything; EIM retirements for dates > 2019Q2 are processed at start of Q4
        pass
    
    # ~~~~~~~~~
    # bankruptcy retirement (from future vintage allowances in government holding accounts)
    if cq.date == quarter_period('2019Q2'):       
        # the only historical bankruptcy retirement occurred in 2019Q2, for La Paloma
        # occurred on June 27, 2019, according to note at bottom of 2019Q2 CIR
        all_accts = retire_for_bankruptcy(all_accts)
    else:
        # don't do anything; bankruptcy retirements for dates > 2019Q2 processed at start of Q4
        pass
    # ~~~~~~~~~
    
    if cq.date.quarter == 4:        
        # Q4 PROCESSING AFTER AUCTION **********************************************
        # this includes transfer of consigned portion of alloc into limited_use
        logging.info(f"for {cq.date}, Q4 processing after auction: start")      
            
        # note: the transfer allocation step below moves annual consigned allowances into limited_use
        # this needs to happen before allowances for Q1 of next year can be moved from limited_use to auct_hold
        if cq.date.year >= 2013:       
            # transfer allocations (consigned & not consigned)
         
            # transfer all allocations (required by Oct 24)
            # (fn only transfers 1 vintage at a time, vintage == cq.date.year + 1)
            all_accts = transfer_CA_alloc__from_alloc_hold(all_accts, prmt.CA_alloc_MI_all)

            # for consign, groupby sum to get rid of distinctions between types (IOU, POU)
            all_accts = consign_groupby_sum_in_all_accts(all_accts)

        else:
            # closing "if cq.date.year >= 2013:"
            # end of transfer allocation process
            pass
        
        # end-of-year: move advance unsold to current auction
        all_accts = adv_unsold_to_cur_all_accts(all_accts)  
        
        logging.info(f"for {cq.date}, Q4 processing after auction: end")
    
    else: 
        # closing "if cq.date.quarter == 4:"
        pass
    
    # END-OF-QUARTER (EVERY QUARTER) *****************************************
    logging.info("end-of-quarter processing (every quarter) - start")
    
    # process historical reserve sales
    all_accts = process_reserve_sales_historical(all_accts, 'CA')

    if prmt.run_tests == True:  
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_for_negative_values(all_accts, parent_fn)
    else:
        pass

    # check for VRE retirement (historical data only; assumes no future VRE retirements)
    all_accts = transfer__from_VRE_acct_to_retirement(all_accts)
    
    # steps after process_CA_quarterly
    # cap adjustment for net flow from Ontario (California's share of total ~13.1 M adjustment)
    if cq.date == quarter_period('2019Q2'):
        # CA cap adjustment occurred June 27, 2019 (according to note at bottom of 2019Q2 CIR)
        # (note that Quebec's cap adjustment was on July 10, 2019, in 2019Q3)
        all_accts = retire_for_net_flow_from_Ontario(all_accts, 'CA')
    else:
        pass
    
    if cq.date < quarter_period('2030Q4'):
        # transfer consignment allowances into auct_hold, for auction in following quarter
        # (each quarter, after auction)
        # have to do this *after* end-of-year transfer of consignment from alloc_hold to limited_use
        all_accts = transfer_consign__from_limited_use_to_auct_hold(all_accts)
    else:
        # no projection for what happens after 2030Q4, so no transfer to occur in 2030Q4
        pass
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # CLEANUP OF all_accts (each quarter)
    # get rid of fractional allowances, zeros, and NaN
    logging.info("cleanup of all_accts")
    
    all_accts = all_accts.loc[(all_accts['quant']>1e-7) | (all_accts['quant']<-1e-7)]
    all_accts = all_accts.dropna()
    # END OF CLEANUP OF all_accts
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # take snap_end at end of each quarter, add to list scenario_CA.snaps_end
    take_snapshot_end(all_accts, 'CA')
        
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)        
        test_conservation_against_full_budget(all_accts, 'CA', parent_fn)  
    
    logging.info("end-of-quarter processing (every quarter) - end")
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)
# end of process_CA_quarterly


# In[ ]:


def CA_state_owned_make_available(all_accts, auct_type):
    """
    State-owned allowances in auct_hold are made available when date_level == cq.date.
    
    Works for current auction and advance auction, as specified by argument auct_type.
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start), for auct_type {auct_type}")
    
    # pre-test for conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    # get allowances in auct_hold, for current auction, for date_level == cq.date
    mask1 = all_accts.index.get_level_values('acct_name')=='auct_hold'
    mask2 = all_accts.index.get_level_values('auct_type')==auct_type
    mask3 = all_accts.index.get_level_values('date_level')==cq.date
    mask4 = all_accts.index.get_level_values('status')=='not_avail'
    mask5 = all_accts['quant'] > 0
    mask = (mask1) & (mask2) & (mask3) & (mask4) & (mask5)
    
    # update status to 'available'
    avail = all_accts.loc[mask]
    mapping_dict = {'status': 'available'}
    avail = multiindex_change(avail, mapping_dict)
    
    # combine avail with remainder (~mask)
    all_accts = pd.concat([avail, all_accts.loc[~mask]], sort=True)
    
    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end), for auct_type {auct_type}")
    
    return(all_accts)
# end of CA_state_owned_make_available


# In[ ]:


def redesignate_unsold_advance_as_advance(all_accts, juris):
    """
    Redesignation of unsold allowances from advance auctions, to later advance auctions.
    
    Only applies to CA; QC does not have similar rule.
    
    Based on regulations:
    CA regs: § 95911(f)(3), particularly § 95911(f)(3)(C) [in force Apr 2019]
    QC regs: Section 54 (states that unsold advance will only be redesignated as current) [in force date 2014-10-22]
    
    For CA, if advance allowances remain unsold in one auction, they can be redesignated to a later advance auction.
    But this will only occur after two consecutive auctions have sold out (sold above the floor price).
    If any advance allowances remain unsold at the end of a calendar year, they are retained for 
    redesignation to a later current auction.
    
    Therefore the only situation in which allowances unsold in advance auctions can be redesignated 
    to another advance auction is if:
    1. some allowances are unsold in advance auction in Q1
    2. Q2 and Q3 advance auctions sell out
    
    Therefore the redesignations can only occur in Q4 of any given year.
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    if juris == 'CA':
        # check sales pct in Q1 of cq.date.year
        df = prmt.auction_sales_pcts_all.copy()
        df = df.loc[(df.index.get_level_values('market').str.contains(juris)) &
                    (df.index.get_level_values('auct_type')=='advance')]
        df.index = df.index.droplevel(['market', 'auct_type'])

        # if no sales pct for Q1 of cq.date.year (i.e., for CA in 2012, or QC in 2013), then return NaN
        try:
            sales_pct_adv_Q1 = df.at[f"{cq.date.year}Q1"]
        except:
            sales_pct_adv_Q1 = np.NaN

        if sales_pct_adv_Q1 < float(1) and cq.date.quarter == 4:        
            # auction does not sell out
            # then check sales pct in Q2 & Q3:
            sales_pct_adv_Q2 = df.at[f"{cq.date.year}Q2"]
            sales_pct_adv_Q3 = df.at[f"{cq.date.year}Q3"]

            if sales_pct_adv_Q2 == float(1) and sales_pct_adv_Q3 == float(1):
                # 100% of auctions sold; redesignate unsold from Q1, up to limit

                # first get the quantity available before redesignation
                # get allowances available for cq.date auction
                mask1 = all_accts.index.get_level_values('juris')==juris
                mask2 = all_accts.index.get_level_values('auct_type')=='advance'
                mask3 = all_accts.index.get_level_values('status')=='available'
                mask4 = all_accts.index.get_level_values('date_level')==cq.date
                mask5 = all_accts['quant'] > 0
                mask = (mask1) & (mask2) & (mask3) & (mask4) & (mask5)
                adv_avail_1j_1q_tot = all_accts[mask]['quant'].sum()          
                
                # max that can be redesignated is 25% of quantity already scheduled to be available
                max_redes_adv = 0.25 * adv_avail_1j_1q_tot

                # get unsold from advance Q1, retained in auction holding account
                unsold_adv_Q1 = all_accts.loc[(all_accts.index.get_level_values('acct_name')=='auct_hold') & 
                                              (all_accts.index.get_level_values('auct_type')=='advance') & 
                                              (all_accts.index.get_level_values('unsold_di')==f"{cq.date.year}Q1")]

                # TEST unsold_adv_Q1 number of rows; should be only a single row
                if len(unsold_adv_Q1) == 1:
                    pass

                else: 
                    # len(unsold_adv_Q1) != 1
                    print(f"{prmt.test_failed_msg} In {cq.date}, for {juris}, selection of unsold_adv_Q1 did not return a single row; here's unsold_adv_Q1:")
                    print(unsold_adv_Q1)
                    print()
                # END OF TEST

                # calculate quantity to be redesignated
                redes_adv_quant = min(max_redes_adv, unsold_adv_Q1['quant'].sum())

                # create new df and specify quantity redesignated
                redes_adv = unsold_adv_Q1.copy()
                redes_adv['quant'] = float(0)
                redes_adv.at[redes_adv.index[0], 'quant'] = redes_adv_quant

                # create to_remove df that will subtract from auct_hold
                to_remove = -1 * redes_adv.copy()

                # update metadata in redes_adv
                mapping_dict = {'newness': 'redes', 
                                'status': 'available', 
                                'date_level': cq.date}
                redes_adv = multiindex_change(redes_adv, mapping_dict)

                # recombine dfs to create redesignated in auct_hold, and to remove quantity from unsold not_avail
                all_accts = pd.concat([all_accts, redes_adv, to_remove], sort=False)
                all_accts = all_accts.groupby(level=prmt.standard_MI_names).sum() 

            else: 
                # end of "if sales_pct_adv_Q2 == float(1) ..."
                pass
        else: 
            # end of "if sales_pct_adv_Q1 < float(1)"
            pass
    
    else:
        # juris other than CA
        print("Error! redesignate_unsold_advance_as_advance applied to a juris other than CA.")
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)
# end of redesignate_unsold_advance_as_advance


# In[ ]:


def process_auction_adv_all_accts(all_accts, juris):
    """
    Process advance auctions for the specified jurisdiction.
    
    Calculates quantities sold based on percentages in auction_sales_pcts_all (historical and projected).
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # pre-test for conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    # get allowances available for cq.date auction
    mask1 = all_accts.index.get_level_values('juris') == juris
    mask2 = all_accts.index.get_level_values('auct_type') == 'advance'
    mask3 = all_accts.index.get_level_values('status') == 'available'
    mask4 = all_accts.index.get_level_values('date_level') == cq.date
    mask5 = all_accts['quant'] > 0
    mask = (mask1) & (mask2) & (mask3) & (mask4) & (mask5)

    adv_avail_1j_1q = all_accts[mask]
    remainder = all_accts[~mask]
    
    # get sales % for advance auctions, for this juris, for cq.date
    # (works for auctions whether linked or unlinked, i.e., CA-only and CA-QC)
    ser = prmt.auction_sales_pcts_all.copy()
    ser = ser.loc[(ser.index.get_level_values('market').str.contains(juris)) &
                  (ser.index.get_level_values('auct_type') =='advance')]
    ser.index = ser.index.droplevel(['market', 'auct_type'])
    sales_pct_adv_1j_1q = ser.at[cq.date]
    
    # for this juris, quantity allowances sold = available quantity * sales_pct_adv_1q
    sold_tot_1j_1q = adv_avail_1j_1q['quant'].sum() * sales_pct_adv_1j_1q
    
    # remaining: un-accumulator for all CA sales; initialize here; will be updated repeatedly below
    # if there was redes in previous step, this calculates the quantity using the updated version of adv_avail_1j_1q
    adv_remaining_to_sell_1j_1q = adv_avail_1j_1q['quant'].sum() * sales_pct_adv_1j_1q   
    
    # before iterating, sort index so that redes sell first
    adv_avail_1j_1q = adv_avail_1j_1q.sort_index(level=['newness'], ascending=[False])
    
    if sales_pct_adv_1j_1q == float(1):
        # then all sell:
        adv_sold_1j_1q = adv_avail_1j_1q.copy()
        
        # and none remain in adv_avail_1j_1q
        adv_avail_1j_1q['quant'] = float(0)
    
    elif sales_pct_adv_1j_1q < float(1):
        # then assign limited sales to particular sets of allowances
        # iterate through all rows for available allowances; remove those sold
        
        # create df to collect sold quantities; initialize with zeros
        # sort_index so that earliest vintages are drawn from first
        adv_avail_1j_1q = adv_avail_1j_1q.sort_index()
        
        adv_sold_1j_1q = adv_avail_1j_1q.copy()
        adv_sold_1j_1q['quant'] = float(0)
    
        for row in adv_avail_1j_1q.index:
            in_stock_row = adv_avail_1j_1q.at[row, 'quant']

            sold_from_row_quantity = min(in_stock_row, adv_remaining_to_sell_1j_1q)

            if sold_from_row_quantity > 1e-7:
                # update un-accumulator for jurisdiction
                adv_remaining_to_sell_1j_1q = adv_remaining_to_sell_1j_1q - sold_from_row_quantity   

                # update sold quantity & metadata     
                adv_sold_1j_1q.at[row, 'quant'] = sold_from_row_quantity

                # update adv_avail_1j_1q quantity (but not metadata)
                adv_avail_1j_1q.at[row, 'quant'] = in_stock_row - sold_from_row_quantity

            else: # sold_from_row_quantity <= 1e-7:
                pass
        # end of "for row in adv_avail_1j_1q.index:"
    else:
        print("Error" + "! Should not have reached this point; may be that sales_pct_adv_1j_1q == np.NaN")
        pass
    
    # those still remaining in adv_avail_1j_1q are unsold; update status from 'available' to 'unsold'
    adv_unsold_1j_1q = adv_avail_1j_1q
    mapping_dict = {'status': 'unsold'}
    adv_unsold_1j_1q = multiindex_change(adv_unsold_1j_1q, mapping_dict)
    
    # for those sold, update status from 'available' to 'sold' & update acct_name from 'auct_hold' to 'gen_acct'
    mapping_dict = {'status': 'sold', 
                    'acct_name': 'gen_acct'}
    adv_sold_1j_1q = multiindex_change(adv_sold_1j_1q, mapping_dict)
    
    # filter out any rows with zeros or fractional allowances
    adv_sold_1j_1q = adv_sold_1j_1q.loc[(adv_sold_1j_1q['quant']>1e-7) | (adv_sold_1j_1q['quant']<-1e-7)]
    adv_unsold_1j_1q = adv_unsold_1j_1q.loc[(adv_unsold_1j_1q['quant']>1e-7) | (adv_unsold_1j_1q['quant']<-1e-7)]
    
    # recombine
    all_accts = pd.concat([adv_sold_1j_1q, 
                           adv_unsold_1j_1q, 
                           remainder], 
                          sort=False)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # update status for all unsold
    all_accts = unsold_update_status(all_accts, 'advance')

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
    # clean-up
    all_accts = all_accts.loc[(all_accts['quant']>1e-7) | (all_accts['quant']<-1e-7)]
    
    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)
# end of fn process_auction_adv_all_accts


# In[ ]:


def unsold_update_status(all_accts, auct_type):
    """
    Operates after auction, on any allowances still remaining in auct_hold with date_level == cq.date.
    
    Operates for allowances from both current and advance auctions.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")

    # pre-test for conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    # for unsold, update metadata:
    # in all_accts, get any allowances remaining in auct_hold with date_level == cq.date
    # separate them out
    # change metadata: change newness to unsold & status to not_avail
    # recombine with remainder of all_accts
    unsold_mask1 = all_accts.index.get_level_values('acct_name')=='auct_hold'
    unsold_mask2 = all_accts.index.get_level_values('date_level')==cq.date
    unsold_mask3 = all_accts.index.get_level_values('auct_type')==auct_type
    unsold_mask4 = all_accts['quant'] > 0
    unsold_mask = (unsold_mask1) & (unsold_mask2) & (unsold_mask3) & (unsold_mask4)
    all_accts_unsold = all_accts.loc[unsold_mask]
    all_accts_remainder = all_accts.loc[~unsold_mask]
    
    if all_accts_unsold['quant'].sum() > 0:        
        # update metadata in all_accts_unsold
        mapping_dict = {'status': 'unsold',  
                        'unsold_dl': cq.date}
        all_accts_unsold = multiindex_change(all_accts_unsold, mapping_dict)
                
        # separate those with an unsold_di != prmt.NaT_proxy from those with unsold_di == prmt.NaT_proxy
        # for those with unsold_di == prmt.NaT_proxy (never unsold before), set new value of unsold_di to be cq.date; 
        # for the rest (were unsold before), don't change unsold_di
        unsold_before_mask = all_accts_unsold.index.get_level_values('unsold_di')==prmt.NaT_proxy
        unsold_di_NaT = all_accts_unsold.loc[unsold_before_mask]
        
        mapping_dict = {'unsold_di': cq.date}
        unsold_di_NaT = multiindex_change(unsold_di_NaT, mapping_dict)
        
        unsold_di_not_NaT = all_accts_unsold.loc[~unsold_before_mask]
        
        # recombine all_accts_remainder (above), unsold_di_NaT & unsold_di_not_NaT
        all_accts = pd.concat([all_accts_remainder, 
                               unsold_di_NaT,
                               unsold_di_not_NaT], sort=False)
    
    elif all_accts_unsold['quant'].sum() == 0.0:
        pass
        
    else: # all_accts_unsold['quant'].sum() is neither > 0 nor == 0; is it negative? NaN?
        print("Error" + "! all_accts_unsold['quant'].sum() should be a float that's either zero or positive.")
        
    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
        
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
        
    return(all_accts)
# end of unsold_update_status


# In[ ]:


def consign_make_available_incl_redes(all_accts):
    """
    Changes status of consignment allowances to 'available.'
    
    Runs at the start of each quarter, before that quarter's auction. 
    
    Operates on all consigned allowances in auct_hold. 
    
    So if there are unsold from previous quarter, these are redesinated.
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # pre-test for conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    # get consigned allowances in auct_hold
    mask1 = all_accts.index.get_level_values('acct_name')=='auct_hold'
    mask2 = all_accts.index.get_level_values('inst_cat')=='consign'
    consign_mask = (mask1) & (mask2)
    consign_avail = all_accts.loc[consign_mask]
    
    # change 'status' to 'available'
    mapping_dict = {'status': 'available'}
    consign_avail = multiindex_change(consign_avail, mapping_dict)
    
    # update metadata for redesignated allowances
    # for those that went unsold before (unsold_di != prmt.NaT_proxy):
    # change 'newness' to 'redes'
    # change 'date_level' to cq.date
    redes_mask = consign_avail.index.get_level_values('unsold_di') != prmt.NaT_proxy
    consign_redes = consign_avail.loc[redes_mask]
    
    mapping_dict = {'newness': 'redes', 
                    'date_level': cq.date}
    consign_redes = multiindex_change(consign_redes, mapping_dict)
    
    # recombine to make new version of all_accts
    all_accts = pd.concat([consign_redes, 
                           consign_avail.loc[~redes_mask],
                           all_accts.loc[~consign_mask]
                          ], sort=False)
    
    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
        
    return(all_accts)
# end of consign_make_available_incl_redes


# In[ ]:


def redesignate_unsold_current_auct(all_accts, juris):
    """
    Redesignates state-owned allowances that are eligible, changing 'status' to 'available'.
    
    Note that this function only redesignates unsold from current auctions to later current auctions. 
    
    (Consignment are redesignated by function consign_make_available_incl_redes.)
    
    (Unsold advance to later advance auctions are redesignated by function redesignate_unsold_advance_as_advance.)
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # pre-test for conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    previous_q = (pd.to_datetime(f'{cq.date.year}Q{cq.date.quarter}') - DateOffset(months=3)).to_period('Q')
    
    # ~~~~~~~~~~~~~~~~~~
    # check whether this quarter is eligible for reintroductions (for this juris)
    # get sell_out_counter, which is the number of consecutive current auctions that sold out, before cq.date
    if juris == 'CA':   
        cur_sell_out_counter = prmt.CA_cur_sell_out_counter.loc[cq.date]
        
    elif juris == 'QC':
        cur_sell_out_counter = prmt.QC_cur_sell_out_counter.loc[cq.date]
    
    if cur_sell_out_counter >= 2:
        reintro_eligibility = True
    elif cur_sell_out_counter in [0, 1]:
        reintro_eligibility = False
    else:
        print("Error" + "! Unknown edge case for value of reintro_eligibility")
    
    logging.info(f"in {cq.date} juris {juris}, cur_sell_out_counter: {cur_sell_out_counter}")
    logging.info(f"in {cq.date} juris {juris}, reintro_eligibility: {reintro_eligibility}")
    
    # ~~~~~~~~~~~~~~~~~~
    # run remainder of function only if reintro_eligibility == True
    if reintro_eligibility == True:
        # ***** redesignation of advance as advance is done by fn redesignate_unsold_advance_as_advance *****
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~
        # redesignate unsold current state-owned (aka reintro)
        if prmt.run_tests == True:
            # TEST: in all_accts, are available allowances only in auct_hold? & have only 'date_level'==cq.date? 
            # (if so, then selection below for auct_type current & status available will work properly)
            available_sel = all_accts.loc[all_accts.index.get_level_values('status')=='available']
            
            if available_sel.empty == False:
                # TEST: are avail only in auct_hold?
                if available_sel.index.get_level_values('acct_name').unique().tolist() != ['auct_hold']:
                    print(f"{prmt.test_failed_msg} Available allowances in account other than auct_hold. Here's available:") # for UI
                    print(available_sel) # for UI
                else:
                    pass
        
                # TEST: do avail have only date_level == cq.date?
                if available_sel.index.get_level_values('date_level').unique().tolist() != [cq.date]:
                    print(f"{prmt.test_failed_msg} Available allowances have date_level other than cq.date (%s). Here's available:" % cq.date) # for UI
                    print(available_sel) # for UI
                else:
                    pass
            
            else: # available_sel.empty == True
                print("Warning" + f"! In {cq.date}, {inspect.currentframe().f_code.co_name}, available_sel is empty.") # for UI
                print("Because available_sel is empty, show auct_hold:") # for UI
                print(all_accts.loc[all_accts.index.get_level_values('acct_name')=='auct_hold']) # for UI
            # END OF TEST

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~
        # calculate max reintro
        max_cur_reintro_1j_1q = calculate_max_cur_reintro(all_accts, juris)
        
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~
        # if conditions are right, reintro any state-owned allowances
        # including filter for only positive rows
        mask1 = all_accts.index.get_level_values('status')=='unsold'
        mask2 = all_accts.index.get_level_values('auct_type')=='current'
        mask3 = all_accts['quant']>0
        unsold_cur_sum = all_accts.loc[(mask1) & (mask2) & (mask3)]['quant'].sum()
        
        if unsold_cur_sum > 0:            
            all_accts = reintro_update_unsold_1j(all_accts, juris, max_cur_reintro_1j_1q)
            
        else: # unsold sum was not > 0, so no unsold to redesignate
            pass
        
    else: # reintro_eligibility == False; nothing to do
        pass
        
    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)
# end of redesignate_unsold_current_auct


# In[ ]:


def calculate_max_cur_reintro(all_accts, juris):
    """
    Calculate the maximum quantity of state-owned allowances that went unsold at current auction that can be reintroduced.

    Based on regulations:
    CA regs: § 95911(f)(3)(D) (in force Apr 2019)
    QC regs: Section 54 (in force date 2014-10-22)
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # select allowances available (state & consign), before redesignation of unsold current state-owned (aka reintro)
    cur_avail_mask1 = all_accts.index.get_level_values('auct_type')=='current'
    cur_avail_mask2 = all_accts.index.get_level_values('status')=='available'
    cur_avail_mask3 = all_accts.index.get_level_values('juris')==juris
    cur_avail_mask = (cur_avail_mask1) & (cur_avail_mask2) & (cur_avail_mask3)
    
    cur_avail_1j_1q = all_accts.loc[cur_avail_mask]
    cur_avail_1j_1q_tot = cur_avail_1j_1q['quant'].sum()

    # calculate maximum reintro quantity for specified juris
    max_cur_reintro_1j_1q = cur_avail_1j_1q_tot * 0.25
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")

    return(max_cur_reintro_1j_1q)
# end of calculate_max_cur_reintro


# In[ ]:


def reintro_update_unsold_1j(all_accts, juris, max_cur_reintro_1j_1q):
    """
    Takes unsold state-owned allowances, reintroduces some to auction based on rules:
    CA regs: § 95911(f)(3)(A) & (C) [in force Apr 2019]
    QC regs: Section 54 (paragraph 1) [in force date 2014-10-22] 
    
    This function is called only when reintro_eligibility == True.
    
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # pre-test for conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    mask1 = all_accts.index.get_level_values('status')=='unsold'
    mask2 = all_accts.index.get_level_values('acct_name')=='auct_hold'
    mask3 = all_accts.index.get_level_values('auct_type')=='current'
    mask4 = all_accts.index.get_level_values('inst_cat')==juris
    mask5 = all_accts['quant']>0
    mask = (mask1) & (mask2) & (mask3) & (mask4) & (mask5)
    
    # CA: add additional mask for 24-month limit
    if juris == 'CA':
        cut_off_date = pd.to_datetime(cq.date.to_timestamp() - DateOffset(years=2)).to_period('Q')
        # only those with unsold_di equal to or after the cut_off_date can be reintroduced
        mask_cut_off = all_accts.index.get_level_values('unsold_di') >= cut_off_date
        mask = mask & (mask_cut_off)
    else:
        pass
    
    reintro_eligible_1j = all_accts.loc[mask]
    
    remainder = all_accts.loc[~mask]
    
    if reintro_eligible_1j['quant'].sum() > 0:

        # accumulator: amount reintro in present auction
        reintro_1q_quant = 0 # initialize

        # un-accumulator: amount remaining to be introduced
        max_cur_reintro_1j_1q_remaining = max_cur_reintro_1j_1q
        
        # initialize df to collect all reintro
        reintro_1j_1q = prmt.standard_MI_empty.copy()
        
        # sort_index to ensure that earliest vintages are drawn from first
        reintro_eligible_1j = reintro_eligible_1j.sort_index()
        
        for row in reintro_eligible_1j.index:
            if max_cur_reintro_1j_1q_remaining == 0:
                break
            
            else:
                reintro_one_batch_quantity = min(max_cur_reintro_1j_1q_remaining,
                                                 reintro_eligible_1j.at[row, 'quant'])

                # update accumulator for amount reintro so far in present quarter (may be more than one batch)
                reintro_1q_quant += reintro_one_batch_quantity
               
                # update un-accumulator for max_cur_reintro_1j_1q_remaining (may be more than one batch)
                max_cur_reintro_1j_1q_remaining += -1*reintro_one_batch_quantity

                # copy reintro_eligible_1j before update; use to create reintro_1j_1q                
                # create copy of reintro_eligible_1j & clear quantities (set equal to zero float)
                reintro_one_batch = reintro_eligible_1j.copy()
                reintro_one_batch.index.name = 'reintro_one_batch'
                reintro_one_batch.name = 'reintro_one_batch'
                reintro_one_batch['quant'] = float(0)
                
                # set new value for 'quant'
                reintro_one_batch.at[row, 'quant'] = reintro_one_batch_quantity
    
                # put reintro for this row into df for collecting all reintro for this juris
                reintro_1j_1q = pd.concat([reintro_1j_1q, reintro_one_batch])
                
                # update reintro_eligible_1j to remove reintro_one_batch_quantity
                reintro_eligible_1j.at[row, 'quant'] = reintro_eligible_1j.at[row, 'quant'] - reintro_one_batch_quantity            

        # filter out rows with fractional allowances, zero, NaN
        reintro_1j_1q = reintro_1j_1q.loc[(reintro_1j_1q['quant']>1e-7) | (reintro_1j_1q['quant']<-1e-7)].dropna()
        reintro_1j_1q = reintro_1j_1q.dropna()
        
        # log the quantity reintroduced
        logging.info(f"in {cq.date} for juris {juris}, quantity reintro: {reintro_1j_1q['quant'].sum()}")
        
        # don't need to update acct_name; should still be auct_hold
        mapping_dict = {'newness': 'reintro', 
                        'status': 'available', 
                        'date_level': cq.date}
        reintro_1j_1q = multiindex_change(reintro_1j_1q, mapping_dict)

        # filter out zero rows
        reintro_eligible_1j = reintro_eligible_1j.loc[reintro_eligible_1j['quant']>0]
        reintro_1j_1q = reintro_1j_1q.loc[reintro_1j_1q['quant']>0]
        
        # concat to recreate all_accts
        # (alternative: create df of reintro to remove, then just concat all_accts_pos, to add, to remove)
        all_accts = pd.concat([reintro_1j_1q, reintro_eligible_1j, remainder], sort=True)
        all_accts = all_accts.groupby(level=prmt.standard_MI_names).sum()
        
    else: # if reintro_eligible_1j['quant'].sum() is not > 0
        pass
    
    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)

    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)
# end of reintro_update_unsold_1j


# In[ ]:


def process_auction_cur_CA_all_accts(all_accts):
    """
    Processes current auction for CA, applying the specified order of sales (when auctions don't sell out).
    
    Order of sales based on CA regs (Apr 2019), § 95911(f)(1): 
    1. Consigned allowances: § 95911(f)(1)(A)-(B)
    2. "Allowances Used to Fulfill an Untimely Surrender Obligation": § 95911(f)(1)(C)
    3. Redesignated allowances (state-owned, previously unsold): § 95911(f)(1)(D)
    4. Newly available state-owned allowances: § 95911(f)(1)(E)
    
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # pre-test for conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    if prmt.run_tests == True:
        # TEST: check that all available allowances are in auct_hold
        avail_for_test = all_accts.loc[all_accts.index.get_level_values('status')=='available']
        avail_for_test_accts = avail_for_test.index.get_level_values('acct_name').unique().tolist()
        if avail_for_test.empty == False:
            if avail_for_test_accts != ['auct_hold']:
                print(f"{prmt.test_failed_msg} Some available allowances were in an account other than auct_hold. Here's available:")
                print(avail_for_test)
            else: # avail_for_test_accts == ['auct_hold']
                pass
        else: # avail_for_test.empty == True
            print("Warning" + "! In process_auction_cur_CA_all_accts, avail_for_test is empty.")
        # END OF TEST
    
    # get sales % for current auctions, for this juris, for cq.date
    # (works for auctions whether linked or unlinked, i.e., CA-only and CA-QC)
    df = prmt.auction_sales_pcts_all.copy()
    df = df.loc[(df.index.get_level_values('market').str.contains('CA')) &
                (df.index.get_level_values('auct_type')=='current')]
    df.index = df.index.droplevel(['market', 'auct_type'])
    sales_fract_cur_1j_1q = df.at[cq.date]
    
    # get current available allowances
    # (it should be that all available allowances are in auct_hold)
    mask1 = all_accts.index.get_level_values('auct_type')=='current'
    mask2 = all_accts.index.get_level_values('status')=='available'
    mask3 = all_accts.index.get_level_values('date_level')==cq.date
    mask4 = all_accts.index.get_level_values('juris')=='CA'
    mask5 = all_accts['quant'] > 0
    mask = (mask1) & (mask2) & (mask3) & (mask4) & (mask5)
    cur_avail_CA_1q = all_accts.loc[mask]
    
    not_cur_avail_CA_1q = all_accts.loc[~mask]
    
    if sales_fract_cur_1j_1q == 1.0:
        # all available allowances are sold and transferred into gen_acct
        cur_sold_CA_1q = cur_avail_CA_1q
        mapping_dict = {'status': 'sold', 
                        'acct_name': 'gen_acct'}
        cur_sold_CA_1q = multiindex_change(cur_sold_CA_1q, mapping_dict)
        
        # recombine
        all_accts = pd.concat([cur_sold_CA_1q, not_cur_avail_CA_1q], sort=False)
        
    else: # sales_fract_cur_1j_1q != 1.0:
        # calculate quantity of CA allowances sold (and test that variable is a float)
        cur_sold_1q_tot_CA = cur_avail_CA_1q['quant'].sum() * sales_fract_cur_1j_1q
        
        if prmt.run_tests == True:
            test_if_value_is_float_or_np_float64(cur_sold_1q_tot_CA)

        # remaining: un-accumulator for all CA sales; initialize here; will be updated repeatedly below
        cur_remaining_to_sell_1q_CA = cur_sold_1q_tot_CA.copy()

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        # sales priority: consignment are first
        # use if statement (or alternative) for all types of consignment, 
        # because it is possible (although unlikely) that, in a particular quarter, entities may opt to consign 0
        # even if they must consign more than 0 for the whole year
        # earlier in model, amounts per quarter are calculated as one-quarter of annual total, but that may change in future

        # select consignment allowances (from allowances available in cq.date current auction)
        mask1 = all_accts.index.get_level_values('auct_type')=='current'
        mask2 = all_accts.index.get_level_values('status')=='available'
        mask3 = all_accts.index.get_level_values('date_level')==cq.date
        mask4 = all_accts.index.get_level_values('juris')=='CA'
        mask5 = all_accts.index.get_level_values('inst_cat')=='consign'
        mask6 = all_accts['quant'] > 0
        mask = (mask1) & (mask2) & (mask3) & (mask4) & (mask5) & (mask6)
        consign_avail_1q = all_accts.loc[mask]
        not_consign_avail_1q = all_accts.loc[~mask]
  
        # iterate through all rows for available allowances; remove those sold

        # start by creating df from avail, with values zeroed out
        consign_sold_1q = consign_avail_1q.copy()
        consign_sold_1q['quant'] = float(0)

        # in regulations, for consignment, no sales priority of redesignated vs. newly available
        # however, for simplicity and to match state-owned behavior, sort df so that redes will sell before new
        # first sort by vintage, ascending=True (redes will be same vintage or earlier than newly available)
        # then sort by newness, ascending=False (so that 'redes' will occur before 'new')
        consign_avail_1q = consign_avail_1q.sort_index(level=['vintage', 'newness'], ascending=[True, False])

        for row in consign_avail_1q.index:
            in_stock_row = consign_avail_1q.at[row, 'quant']

            sold_from_row_quantity = min(in_stock_row, cur_remaining_to_sell_1q_CA)

            if sold_from_row_quantity > 1e-7:
                # update un-accumulator for jurisdiction
                cur_remaining_to_sell_1q_CA = cur_remaining_to_sell_1q_CA - sold_from_row_quantity

                # update sold quantity
                consign_sold_1q.at[row, 'quant'] = sold_from_row_quantity

                # update avail quantity
                consign_avail_1q.at[row, 'quant'] = in_stock_row - sold_from_row_quantity

            else: # sold_from_row_quantity <= 1e-7:
                pass

        # update metadata for sold
        # for those sold, update status from 'available' to 'sold' & update acct_name from 'auct_hold' to 'gen_acct'
        mapping_dict = {'status': 'sold', 
                        'acct_name': 'gen_acct'}
        consign_sold_1q = multiindex_change(consign_sold_1q, mapping_dict)

        # for unsold, metadata is updated for all allowance types at once, at end of this function
        # unsold is what's left in avail df
        consign_unsold_1q = consign_avail_1q

        # recombine to create new version of all_accts
        all_accts = pd.concat([consign_sold_1q,
                               consign_unsold_1q,
                               not_consign_avail_1q], 
                              sort=False)
        # clean-up
        all_accts = all_accts.loc[(all_accts['quant']>1e-7) | (all_accts['quant']<-1e-7)]

        if prmt.run_tests == True:
            # TEST: conservation of allowances
            all_accts_after_consign_sales = all_accts['quant'].sum()
            diff = all_accts_after_consign_sales - all_accts_sum_init
            if abs(diff) > 1e-7:
                print(f"{prmt.test_failed_msg} Allowances not conserved in fn process_auction_cur_CA_all_accts, after consignment sales.") # for UI
                print("diff = all_accts_after_consign_sales - all_accts_sum_init:") # for UI
                print(diff) # for UI
                print("all_accts_sum_init: %s" % all_accts_sum_init) # for UI
                print("consign_sold_1q sum: %s" % consign_sold_1q['quant'].sum()) # for UI
                print("consign_unsold_1q sum: %s" % consign_unsold_1q['quant'].sum()) # for UI
                print("not_consign_avail_1q sum: %s" % not_consign_avail_1q['quant'].sum()) # for UI
            # END OF TEST

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        # sales priority: after consignment, reintro are next

        # extract reintro allowances from all_accts
        mask1 = all_accts.index.get_level_values('auct_type')=='current'
        mask2 = all_accts.index.get_level_values('status')=='available'
        mask3 = all_accts.index.get_level_values('date_level')==cq.date
        mask4 = all_accts.index.get_level_values('juris')=='CA'
        mask5 = all_accts.index.get_level_values('newness')=='reintro'
        mask6 = all_accts['quant'] > 0
        mask = (mask1) & (mask2) & (mask3) & (mask4) & (mask5) & (mask6)
        reintro_avail_1q = all_accts.loc[mask]
        not_reintro_avail_1q = all_accts.loc[~mask]

        # iterate through all rows for available allowances; remove those sold
        
        # start by creating df from avail, with values zeroed out
        # sort_index to ensure that earliest vintages are drawn from first
        reintro_avail_1q = reintro_avail_1q.sort_index()
        
        reintro_sold_1q = reintro_avail_1q.copy()
        reintro_sold_1q['quant'] = float(0)

        for row in reintro_avail_1q.index:
            in_stock_row = reintro_avail_1q.at[row, 'quant']

            sold_from_row_quantity = min(in_stock_row, cur_remaining_to_sell_1q_CA)

            if sold_from_row_quantity > 1e-7:
                # update un-accumulator for jurisdiction
                cur_remaining_to_sell_1q_CA = cur_remaining_to_sell_1q_CA - sold_from_row_quantity

                # update sold quantity & metadata
                reintro_sold_1q.at[row, 'quant'] = sold_from_row_quantity

                # update reintro_avail_1q quantity (but not metadata)
                reintro_avail_1q.at[row, 'quant'] = in_stock_row - sold_from_row_quantity

            else: # sold_from_row_quantity <= 1e-7:
                pass


        # using all_accts:
        # for those sold, update status from 'available' to 'sold' & update acct_name from 'auct_hold' to 'gen_acct'
        mapping_dict = {'status': 'sold', 
                        'acct_name': 'gen_acct'}
        reintro_sold_1q = multiindex_change(reintro_sold_1q, mapping_dict)

        # for unsold, metadata is updated for all allowance types at once, at end of this function
        # unsold is what's left in avail df
        reintro_unsold_1q = reintro_avail_1q

        # recombine
        all_accts = pd.concat([reintro_sold_1q,
                               reintro_unsold_1q,
                               not_reintro_avail_1q], 
                              sort=False)
        # clean-up
        all_accts = all_accts.loc[(all_accts['quant']>1e-7) | (all_accts['quant']<-1e-7)]

        if prmt.run_tests == True:
            # TEST: conservation of allowances
            all_accts_after_reintro_sales = all_accts['quant'].sum()
            diff = all_accts_after_reintro_sales - all_accts_sum_init
            if abs(diff) > 1e-7:
                print(f"{prmt.test_failed_msg} Allowances not conserved in fn process_auction_cur_CA_all_accts, after reintro sales.")
            # END OF TEST

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        # sales priority: state-owned allowances available for first time as current (including fka adv, if there are any)

        # extract state allowances new to current auctions (from all_accts)
        mask1 = all_accts.index.get_level_values('auct_type')=='current'
        mask2 = all_accts.index.get_level_values('status')=='available'
        mask3 = all_accts.index.get_level_values('date_level')==cq.date
        mask4 = all_accts.index.get_level_values('juris')=='CA'
        mask5 = all_accts.index.get_level_values('newness')=='new'
        mask6 = all_accts['quant'] > 0
        mask = (mask1) & (mask2) & (mask3) & (mask4) & (mask5) & (mask6)
        new_avail_1q = all_accts.loc[mask]
        not_new_avail_1q = all_accts.loc[~mask]

        # iterate through all rows for available allowances; remove those sold
        
        # start by creating df from avail, with values zeroed out
        # sort_index to ensure that earliest vintages are drawn from first
        new_avail_1q = new_avail_1q.sort_index()
        
        new_sold_1q = new_avail_1q.copy()
        new_sold_1q['quant'] = float(0)

        for row in new_avail_1q.index:
            in_stock_row = new_avail_1q.at[row, 'quant']

            sold_from_row_quantity = min(in_stock_row, cur_remaining_to_sell_1q_CA)

            if sold_from_row_quantity > 1e-7:
                # update un-accumulator for jurisdiction
                cur_remaining_to_sell_1q_CA = cur_remaining_to_sell_1q_CA - sold_from_row_quantity

                # update sold quantity & metadata
                new_sold_1q.at[row, 'quant'] = sold_from_row_quantity

                # update new_avail_1q quantity (but not metadata)
                new_avail_1q.at[row, 'quant'] = in_stock_row - sold_from_row_quantity

            else: # sold_from_row_quantity <= 1e-7:
                pass

        # using all_accts:
        # for those sold, update status from 'available' to 'sold' & update acct_name from 'auct_hold' to 'gen_acct'
        mapping_dict = {'status': 'sold', 
                        'acct_name': 'gen_acct'}
        new_sold_1q = multiindex_change(new_sold_1q, mapping_dict)

        # for unsold, metadata is updated for all allowance types at once, at end of this function
        # unsold is what's left in avail df
        new_unsold_1q = new_avail_1q

        # recombine & groupby sum
        all_accts = pd.concat([new_sold_1q,
                               new_unsold_1q,
                               not_new_avail_1q], 
                              sort=True).sort_index() 
        # all_accts = all_accts.groupby(level=prmt.standard_MI_names).sum()

        # clean-up
        all_accts = all_accts.loc[(all_accts['quant']>1e-7) | (all_accts['quant']<-1e-7)]
        
        if prmt.run_tests == True:
            # TEST: conservation of allowances
            all_accts_after_new_sales = all_accts['quant'].sum()
            diff = all_accts_after_new_sales - all_accts_sum_init
            if abs(diff) > 1e-7:
                print(f"{prmt.test_failed_msg} Allowances not conserved in fn process_auction_cur_CA_all_accts, after new sales.")
            # END OF TEST

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        # update status for all unsold
        all_accts = unsold_update_status(all_accts, 'current')

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        # filter out rows with fractional allowances or zero
        all_accts = all_accts.loc[(all_accts['quant']>1e-7) | (all_accts['quant']<-1e-7)].dropna()

    # end of if-else statement that began "if sales_fract_cur_1j_1q == 1.0)

    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
        
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")

    return(all_accts)
# end of process_auction_cur_CA_all_accts


# In[ ]:


def process_reserve_sales_historical(all_accts, juris):
    """
    For historical reserve sales in data input sheet, transfers allowances out of reserves to private accounts.
    
    Data input file specifies type of reserve allowance sales (e.g., California first tier).
    
    However WCI-RULES v1.1 doesn't distinguish between types of reserve allowances within each jurisdiction.
    
    So this function takes the subtotals for each jurisdiction and transfers allowances.
    
    The function draws first from the allowances in the main set of reserves (non-vintaged), then vintaged allowances.
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    if juris == 'CA':
        reserve_sales_1q = prmt.CA_reserve_sales_q_hist.at[cq.date]
    elif juris == 'QC':
        reserve_sales_1q = prmt.QC_reserve_sales_q_hist.at[cq.date]
    
    # pre-test for conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    if reserve_sales_1q > 0:
        
        # select allowances from all_accts
        mask1 = all_accts.index.get_level_values('juris')==juris
        mask2 = all_accts.index.get_level_values('acct_name')=='APCR_acct'
        mask = (mask1) & (mask2)
        potential = all_accts.loc[mask].sort_values(by='vintage', ascending=False)
        remainder = all_accts.loc[~mask]
        reserve_sales = potential.copy()

        reserve_sales_1q_remain = reserve_sales_1q # initialize

        for row in potential.index:
            if potential.at[row, 'quant'] >= reserve_sales_1q_remain:
                # add quantities to reserve_sales df
                reserve_sales.at[row, 'quant'] = reserve_sales_1q_remain

                # reduce quantity in potential
                potential.at[row, 'quant'] += -1 * reserve_sales_1q_remain

                # reduce reserve_sales_1q_remain
                reserve_sales_1q_remain += -1 * reserve_sales_1q_remain

            elif potential.at[row, 'quant'] < reserve_sales_1q_remain:
                # add quantities to reserve_sales df
                reserve_sales.at[row, 'quant'] = potential.at[row, 'quant']

                # remove all allowances from potential
                potential.at[row, 'quant'] += -1 * potential.at[row, 'quant']

                # reduce reserve_sales_1q_remain
                reserve_sales_1q_remain += -1 * potential.at[row, 'quant']

        # change metadata in reserve_sales
        mapping_dict = {'status': 'sold',
                        'acct_name': 'gen_acct', # transfers allowances to gen_acct (private)
                        'date_level': cq.date, # sets date_level to be the date the reserve sale occurred
                       }
        reserve_sales = multiindex_change(reserve_sales, mapping_dict)

        # recombine
        all_accts = pd.concat([potential, reserve_sales, remainder], sort=False).groupby(prmt.standard_MI_names).sum()            

    elif reserve_sales_1q == 0:
        pass
    
    else:
        print(f"Error! Unknown edge case for reserve_sales_1q: {reserve_sales_1q}") # for UI

    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
        
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
          
    return(all_accts)
# end of process_reserve_sales_historical


# In[ ]:


def adv_unsold_to_cur_all_accts(all_accts):
    """
    Function similar to adv_unsold_to_cur, but operating on all_accts.
    
    Takes any unsold allowances from advance auctions that are in auct_hold account,
    and updates metadata to change them into current auction allowances.
    
    Sums any unsold across all quarters in a calendar year, 
    (which will become part of total state-owned allowances to be made available in current auctions).
    
    Based on regulations:
    CA regs: § 95911(f)(3)(A), (C) & (D) [in force Apr 2019]
    QC regs: Section 54 (paragraph 2) [in force date 2014-10-22]
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # pre-test for conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    # isolate allowances unsold at advance auctions
    mask1 = all_accts.index.get_level_values('acct_name')=='auct_hold'
    mask2 = all_accts.index.get_level_values('auct_type')=='advance'
    mask3 = all_accts.index.get_level_values('status')=='unsold'
    mask4 = all_accts['quant'] > 0
    mask = (mask1) & (mask2) & (mask3) & (mask4)
    unsold_adv = all_accts.loc[mask]
    all_accts_remainder = all_accts.loc[~mask]
    
    # update metadata in all_accts, creating adv_redes_to_cur
    adv_redes_to_cur = unsold_adv.copy()
    mapping_dict = {'auct_type': 'current', 
                    'newness': 'new', 
                    'status': 'not_avail',
                    'date_level': prmt.NaT_proxy, 
                    'unsold_di': prmt.NaT_proxy, 
                    'unsold_dl': prmt.NaT_proxy}
    adv_redes_to_cur = multiindex_change(adv_redes_to_cur, mapping_dict)
    
    # groupby sum to combine all unsold from advance auctions of a particular vintage
    adv_redes_to_cur = adv_redes_to_cur.groupby(level=prmt.standard_MI_names).sum()
    
    # recombine adv_redes_to_cur with remainder
    all_accts = pd.concat([adv_redes_to_cur, all_accts_remainder], sort=True)

    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")

    return(all_accts)
# end of adv_unsold_to_cur_all_accts


# In[ ]:


def transfer__from_VRE_acct_to_retirement(all_accts):   
    """
    Transfers allocations from allocation holding account (alloc_hold) to other accounts.
    
    Works for APCR (to APCR_acct), VRE (to VRE_acct), and advance (to auct_hold).
    
    Destination account is contained in to_acct_MI metadata.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    all_accts_sum_init = all_accts['quant'].sum()

    try:
        VRE_retired_1q = prmt.VRE_retired.xs(cq.date, level='CIR_date', drop_level=False)

        VRE_retired_1q = VRE_retired_1q.reset_index()

        # record date of retirement as 'date_level'
        VRE_retired_1q = VRE_retired_1q.rename(columns={'CIR_date': 'date_level'})

        # create MultiIndex version of VRE_retired_1q, for doing removal and addition to all_accts
        df = VRE_retired_1q.copy()

        df['acct_name'] = 'VRE_acct'
        df['juris'] = 'CA'
        df['auct_type'] = 'n/a'
        df['inst_cat'] = 'VRE_reserve'
        # vintage already set (index level 'Vintage')
        df['newness'] = 'n/a'
        df['status'] = 'n/a'
        df['unsold_di'] = prmt.NaT_proxy
        df['unsold_dl'] = prmt.NaT_proxy
        df['units'] = 'MMTCO2e'

        # create MultiIndex version
        VRE_retired_1q_MI = df.set_index(prmt.standard_MI_names)

        to_remove = -1 * VRE_retired_1q_MI.copy()
        mapping_dict = {'date_level': prmt.NaT_proxy}
        to_remove = multiindex_change(to_remove, mapping_dict)

        to_transfer = VRE_retired_1q_MI.copy()
        mapping_dict = {'acct_name': 'retirement'}
        to_transfer = multiindex_change(to_transfer, mapping_dict)
        
        # concat with all_accts_pos, groupby sum, recombine with all_accts_neg
        all_accts_pos = all_accts.loc[all_accts['quant']>0]
        all_accts_pos = pd.concat([all_accts_pos, to_remove, to_transfer], sort=True).groupby(level=prmt.standard_MI_names).sum()
        all_accts_neg = all_accts.loc[all_accts['quant']<0]
        all_accts = all_accts_pos.append(all_accts_neg)

        logging.info(f"VRE retirement of {to_transfer['quant'].sum()} M.")
        
    except:
        # no VRE_retired for given date
        pass
    
    
    if prmt.run_tests == True:
        name_of_allowances = 'VRE_reserve'
        test_conservation_during_transfer(all_accts, all_accts_sum_init, name_of_allowances)
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)
# end of transfer__from_VRE_acct_to_retirement


# In[ ]:


def transfer_consign__from_limited_use_to_auct_hold(all_accts):
    """
    Specified quantities remaining in limited_use account of a particular vintage will be moved to auct_hold.

    Allowances consigned to auction must be transferred into auct_hold 75 days before the auction.
    CA regs: § 95910(d)(4).
    
    Runs at the end of each quarter, after auction processed for that quarter.
    
    So, i.e., for Q3 auction ~Aug 15, transfer would occur ~June 1 (in Q2), after Q2 auction (~May 15).
    
    These allowances will become available in the following auction (one quarter after cq.date).
    
    Since this is for consignment, which are only in CA, it doesn't apply to QC.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # pre-test for conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    # get quantity newly consigned in next_q (consign_next_q_quant)
    # vintage of these allowances will always be next_q.year 
    # (true even for anomalous CA auction in 2012Q4; other jurisdictions don't have consignment)
    # look up quantity consigned in next_q from historical record
    df = prmt.consign_hist_proj_new_avail.copy()
    
    # create next_q after cq.date (formatted as quarter)
    next_q = (pd.to_datetime(f'{cq.date.year}Q{cq.date.quarter}') + DateOffset(months=3)).to_period('Q')

    consign_next_q_quant = prmt.consign_hist_proj_new_avail.at[
        ('limited_use', # acct_name
         'CA', # juris
         'current', # auct_type
         'consign', # inst_cat
         next_q.year, # vintage
         'new', # newness
         'not_avail', # status
         next_q, # date_level
         prmt.NaT_proxy, # unsold_di
         prmt.NaT_proxy, # unsold_dl
         'MMTCO2e', # units
         ), 
        'quant']
    
    if prmt.run_tests == True:
        test_if_value_is_float_or_np_float64(consign_next_q_quant)
       
    # get allowances in limited_use, inst_cat=='consign', for specified vintage
    # and calculate sum of that set
    mask1 = all_accts.index.get_level_values('acct_name')=='limited_use'
    mask2 = all_accts.index.get_level_values('inst_cat')=='consign'
    mask3 = all_accts.index.get_level_values('vintage')==next_q.year
    mask4 = all_accts['quant'] > 0
    mask = (mask1) & (mask2) & (mask3) & (mask4)
    consign_not_avail = all_accts.loc[mask]
    quant_not_avail = consign_not_avail['quant'].sum()
    
    if prmt.run_tests == True:
        # TEST: check that consign_not_avail is only 1 row
        if len(consign_not_avail) != 1:
            print(f"{prmt.test_failed_msg} Expected consign_not_avail to have 1 row. Here's consign_not_avail:")
            print(consign_not_avail)
            print("Here's all_accts.loc[mask1] (limited_use):")
            print(all_accts.loc[mask1])
            print("Here's all_accts:")
            print(all_accts)
        # END OF TEST
    
    # split consign_not_avail to put only the specified quantity into auct_hold; 
    # rest stays in limited_use
    consign_avail = consign_not_avail.copy()
    
    # consign_avail and consign_not_avail have same index (before consign avail index updated below)
    # use this common index for setting new values for quantity in each df
    # (only works because each df is a single row, as tested for above)
    index_first_row = consign_avail.index[0]
    
    # set quantity in consign_avail, using consign_next_q_quant
    consign_avail.at[index_first_row, 'quant'] = consign_next_q_quant
    
    # update metadata: put into auct_hold
    # this fn does not make these allowances available; this will occur in separate fn, at start of cq.date
    mapping_dict = {'acct_name': 'auct_hold', 
                    'newness': 'new', 
                    'status': 'not_avail', 
                    'date_level': next_q}
    consign_avail = multiindex_change(consign_avail, mapping_dict)

    # update quantity in consign_not_avail, to remove those consigned for next_q
    consign_not_avail.at[index_first_row, 'quant'] = quant_not_avail - consign_next_q_quant
    
    # get remainder of all_accts
    all_accts_remainder = all_accts.loc[~mask]
    
    # recombine to get all_accts again
    all_accts = pd.concat([consign_avail, 
                           consign_not_avail, 
                           all_accts_remainder], 
                          sort=False)
    
    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)
# end of transfer_consign__from_limited_use_to_auct_hold


# In[ ]:


def transfer_CA_alloc__from_ann_alloc_hold_to_general(all_accts):
    """
    Transfers CA allocations out of annual allocation holding account, into general account.
    
    Transfers occur on Jan 1 of each year, per 95831(a)(6)(D) to (I).
    
    Note that Compliance Instrument Reports for Q4 of a given year are generated in early Jan of following year.
    So CIRs for Q4 include these Jan 1 tranfers of CA allocations out of government accounts and into private accounts.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # pre-test for conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    # get all allowances in acct_name == 'ann_alloc_hold' & juris == 'CA'
    mask1 = all_accts.index.get_level_values('acct_name') == 'ann_alloc_hold'
    mask2 = all_accts.index.get_level_values('juris') == 'CA'
    mask = (mask1) & (mask2)
    to_transfer = all_accts.loc[mask]
    remainder = all_accts.loc[~mask]
    
    # change metadata for ann_alloc_hold allowances, to move to compliance account
    mapping_dict = {'acct_name': 'gen_acct'}
    to_transfer = multiindex_change(to_transfer, mapping_dict)
    
    # recombine dfs
    all_accts = pd.concat([to_transfer, remainder])
    
    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)

    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)
# end of transfer_CA_alloc__from_ann_alloc_hold_to_general


# In[ ]:


def cur_upsample_avail_state_owned_first_principles(all_accts, juris):
    """
    Takes allowances in auct_hold and assigns specific quantities to each quarterly auction within a given year.
    
    Based on first principles; takes what is in auct_hold, divides by 4, assigns to each quarter.
    
    Only operates for state-owned allowances; consigned allowances are handled by a separate function.
    
    For Quebec's initial auction (2013Q4), special case in which annual total allowances available in 1 auction.
    
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # pre-test for conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    # ~~~~~~~~~~~~~~~
    # get auct_hold, state-owned, specified juris, with auct_type=='current'
    # also exclude any future vintage allowances (unsold advance retained in auct_hold)
    # select only "current" vintage == cq.date.year
    # exclude any negative values in auct_hold
    mask1 = all_accts.index.get_level_values('acct_name')=='auct_hold'
    mask2 = all_accts.index.get_level_values('juris')==juris
    mask3 = all_accts.index.get_level_values('auct_type')=='current'
    mask4 = all_accts.index.get_level_values('inst_cat')==juris
    mask5 = all_accts.index.get_level_values('vintage')==cq.date.year
    mask6 = all_accts['quant'] > 0
    mask = (mask1) & (mask2) & (mask3) & (mask4) & (mask5) & (mask6)
    annual_avail_1v = all_accts.loc[mask] 
    not_annual_avail_1v = all_accts.loc[~mask]

    list_of_avail_1qs = []
    
    if juris == 'QC' and cq.date==quarter_period('2013Q4'):
        # special case: transfer annual total allowances; no upsampling
        avail_2013Q4 = annual_avail_1v
        mapping_dict = {'date_level': quarter_period('2013Q4')}
        avail_2013Q4 = multiindex_change(avail_2013Q4, mapping_dict)        
        list_of_avail_1qs += [avail_2013Q4]
        
    else:
        avail_each_q = annual_avail_1v/4

        # iterate through quarters in cq.date.year
        for quarter in range(1, 4+1):            
            date_1q = quarter_period(f"{cq.date.year}Q{quarter}")
            avail_1q = avail_each_q.copy()
            mapping_dict = {'date_level': date_1q}
            avail_1q = multiindex_change(avail_1q, mapping_dict)

            list_of_avail_1qs += [avail_1q]

    all_accts = pd.concat(list_of_avail_1qs + [not_annual_avail_1v], sort=False)

    # clean-up; exclude fractional, zero, NaN rows
    all_accts = all_accts.loc[(all_accts['quant']>1e-10) | (all_accts['quant']<-1e-10)]
    
    # check for duplicate rows; if so, groupby sum for positive rows only
    dups = all_accts.loc[all_accts.index.duplicated(keep=False)]
    if dups.empty==False:
        all_accts_pos = all_accts.loc[all_accts['quant']>1e-7]
        all_accts_pos = all_accts_pos.groupby(level=prmt.standard_MI_names).sum()
        all_accts_neg = all_accts.loc[all_accts['quant']>-1e-7]
        all_accts = all_accts_pos.append(all_accts_neg)
        
    if prmt.run_tests == True:        
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_conservation_against_full_budget(all_accts, juris, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
        
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)
# cur_upsample_avail_state_owned_first_principles


# In[ ]:


def upsample_advance_all_accts(all_accts):
    """
    Takes annual quantities set aside for advance, upsamples to get quarterly quantities to be made available.
    
    Specifies date_level for each quarter, but does *not* assign status 'available'.
    """

    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # pre-test for conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    # select advance allowances to be upsampled
    # when cq.date.year >= 2013, 
    # then upsample vintage = cq.date.year + 3
    
    mask1 = all_accts.index.get_level_values('auct_type')=='advance'
    mask2 = all_accts.index.get_level_values('vintage')==(cq.date.year+3)
    mask3 = all_accts.index.get_level_values('acct_name')=='auct_hold'
    mask = (mask1) & (mask2) & (mask3)
    
    adv_to_upsample = all_accts.loc[mask]  
      
    each_quarter = adv_to_upsample / 4
    mapping_dict = {'status': 'not_avail'}
    each_quarter = multiindex_change(each_quarter, mapping_dict)
    
    all_quarters = prmt.standard_MI_empty.copy()
    for quarter in [1, 2, 3, 4]:
        one_quarter_date = quarter_period(f"{cq.date.year}Q{quarter}")
        one_quarter = each_quarter.copy() 
        mapping_dict = {'date_level': one_quarter_date}
        one_quarter = multiindex_change(one_quarter, mapping_dict)
        all_quarters = pd.concat([all_quarters, one_quarter], sort=True)

    # recombine:
    all_accts = pd.concat([all_quarters, all_accts.loc[~mask]], sort=True)
    
    if prmt.run_tests == True:
        # TEST: conservation of allowances just for upsampled part
        diff = all_quarters['quant'].sum() - adv_to_upsample['quant'].sum()
        if abs(diff) > 1e-7:
            print(f"{prmt.test_failed_msg} Allowances not conserved in upsample_advance_all_accts.")
        # END OF TEST
        
    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
        
    return(all_accts)
# end of upsample_advance_all_accts


# In[ ]:


def transfer_cur__from_alloc_hold_to_auct_hold_first_principles(all_accts, juris):
    """
    Transfers remaining cap allowances in alloc_hold to auct_hold, to become state-owned current.
    
    Operates for historical years and projection years.
    
    (For Quebec, remaining cap excludes allowances set aside for allocations.)
    
    Processes all allowances for a given year (with date_level year == cq.date year).
    
    Transfers occur at the start of each year (Jan 1).
    
    There may already be unsold from advance auctions in auct_hold; if so, this fn does groupby sum.
    
    Note: There is a separate fn for making the allowances in auct_hold available.
    
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # pre-test for conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    # get all allowances in alloc_hold, inst_cat=='cap', for specified vintage and juris
    mask1 = all_accts.index.get_level_values('acct_name')=='alloc_hold'
    mask2 = all_accts.index.get_level_values('vintage')==cq.date.year
    mask3 = all_accts.index.get_level_values('inst_cat')=='cap'
    mask4 = all_accts.index.get_level_values('juris')==juris
    mask5 = all_accts['quant'] > 0
    mask = (mask1) & (mask2) & (mask3) & (mask4) & (mask5)
    
    to_transfer = all_accts.loc[mask]
    remainder = all_accts.loc[~mask]
    
    # update metadata for state_alloc_hold, to put into auct_hold & turn into state-owned allowances
    mapping_dict = {'acct_name': 'auct_hold', 
                    'inst_cat': juris, 
                    'auct_type': 'current',
                    'newness': 'new',  
                    'status': 'not_avail'}
    to_transfer = multiindex_change(to_transfer, mapping_dict)
    
    all_accts = pd.concat([to_transfer, remainder], sort=False)
    
    dups = all_accts.loc[all_accts.index.duplicated(keep=False)]
    
    if dups.empty==False:
        # there are duplicated indices; need to do groupby sum
        all_accts_pos = all_accts.loc[all_accts['quant']>1e-7].groupby(level=prmt.standard_MI_names).sum()
        all_accts_neg = all_accts.loc[all_accts['quant']<-1e-7].groupby(level=prmt.standard_MI_names).sum()
        all_accts = all_accts_pos.append(all_accts_neg)
    
    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_conservation_against_full_budget(all_accts, juris, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")

    return(all_accts)
# end of transfer_cur__from_alloc_hold_to_auct_hold_first_principles


# ## Functions: Unique to QC 
# (run only within process_QC)
# * initialize_QC_auctions_2013Q4
# * convert_QC_alloc_set_aside
# * transfer_QC_alloc_init__from_alloc_hold
# * process_QC_quarterly
#   * QC_state_owned_make_available
#   * transfer_QC_alloc_trueups__from_alloc_hold
#     * transfer_QC_alloc_trueups__from_APCR
#   * transfer_QC_alloc_trueups_neg__to_reserve
# * QC_early_action_distribution

# In[ ]:


def initialize_QC_auctions_2013Q4(all_accts):
    """
    2013Q4 was the first Quebec auction.
    
    It was anomalous, in that:
    1. There was only this single auction in 2013.
    2. The 2013Q4 current auction had approximately a full year's worth of allowances available at once.
    3. However, the current auction quantity was not all the allowances leftover after allocations were distributed.
    4. The 2013Q4 advance auction had available all vintage 2016 allowances at once.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # all_accts (for QC) starts empty
    
    # create QC allowances v2013-v2020, put into alloc_hold
    all_accts = create_annual_budgets_in_alloc_hold(all_accts, prmt.QC_cap.loc[2013:2020])

    # pre-test for conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    logging.info(f"total allowances created: {all_accts_sum_init}")
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~   
    # transfer APCR allowances out of alloc_hold, into APCR_acct (for vintages 2013-2020)
    all_accts = transfer__from_alloc_hold_to_specified_acct(all_accts, prmt.QC_APCR_MI, 2013, 2020)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # QC regs (s. 38) [in force date 2012-09-01]:
    # all allowances not put in reserve account are transferred into "Minister's allocation account"
    # then allocations and auction quantities go from there to other accounts
    # in model, can leave all allowances in alloc_hold, and move allocations and auction quantities as specified
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # transfer advance into auct_hold
    all_accts = transfer__from_alloc_hold_to_specified_acct(all_accts, prmt.QC_advance_MI, 2013, 2020)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # process allocations
    
    # convert cap allowances to QC_alloc_set_aside, for full (est.) alloc quantity for one year
    all_accts = convert_QC_alloc_set_aside(all_accts)
    
    # transfer alloc out of alloc_hold to ann_alloc_hold
    # initial 75% of estimated alloc v2013 transferred in 2013Q4, before Q4 auction
    # (this was later than what would be the usual pattern in later years)
    
    # (appropriate metadata is assigned to each set of allowances by convert_ser_to_df_MI_alloc)             
    # convert each alloc Series into df with MultiIndex
    # then do the transfer for single vintage, cq.date.year+1
    # (the to_acct is already specified in metadata for each set of allowances)
    
    all_accts = transfer_QC_alloc_init__from_alloc_hold(all_accts)             

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # CURRENT AUCTION (2013Q4 anomaly)
    # all remaining allowances of vintage 2013 in alloc_hold to be made available at auction; move to auct_hold
    
    all_accts = transfer_cur__from_alloc_hold_to_auct_hold_first_principles(all_accts, 'QC')
    all_accts = cur_upsample_avail_state_owned_first_principles(all_accts, 'QC')
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # ADVANCE AUCTION (2013Q4 anomaly):
    # remember: all vintage 2016 allowances were available at once in this auction
    # get all allowances aside for advance in auct_hold that are vintage 2016 (cq.date.year+3)
    adv_new_mask1 = all_accts.index.get_level_values('acct_name')=='auct_hold'
    adv_new_mask2 = all_accts.index.get_level_values('auct_type')=='advance'
    adv_new_mask3 = all_accts.index.get_level_values('vintage')==2016
    adv_new_mask = (adv_new_mask1) & (adv_new_mask2) & (adv_new_mask3)
    adv_new = all_accts.loc[adv_new_mask]
    all_accts_remainder = all_accts.loc[~adv_new_mask]
    
    # for this anomalous advance auction, all of these allowances were available in one auction
    # update metadata: change 'date_level' to '2013Q4'
    # (later, metadata will be changed to available by function QC_state_owned_make_available)
    mapping_dict = {'date_level': quarter_period('2013Q4')}
    adv_new = multiindex_change(adv_new, mapping_dict)
    
    # recombine to create new version of all_accts
    all_accts = pd.concat([adv_new, all_accts_remainder], sort=False)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_conservation_against_full_budget(all_accts, 'QC', parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)

    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)
# end of initialize_QC_auctions_2013Q4


# In[ ]:


def convert_QC_alloc_set_aside(all_accts):
    """
    Converts cap allowances into set-aside for QC allocations.
    
    This is a bookkeeping device for separating allowances so that they will not be auctioned.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    all_accts_sum_init = all_accts['quant'].sum()
    
    # use QC_alloc_initial (df) to create QC_alloc_full_est (ser)
    df = (prmt.QC_alloc_initial.copy())/0.75
    df.index = df.index.droplevel('allocation_quarter')
    ser = df['quant']
    
    # select one vintage
    ser = ser.loc[cq.date.year:cq.date.year]
    # need name for this series; used in convert_ser_to_df_MI_QC_alloc
    ser.name = 'QC_alloc_full_est'
    # convert to MultiIndex df, and give df a name
    QC_alloc_full_est_1v_MI = convert_ser_to_df_MI_QC_alloc(ser, 'set_aside')
    QC_alloc_full_est_1v_MI.name = 'QC_alloc_full_est'
    
    # create df named remove, which is negative of to_acct_MI
    remove = -1 * QC_alloc_full_est_1v_MI
    
    # set indices in remove df (version of to_acct_MI) to be same as from_acct
    mapping_dict = {'acct_name': 'alloc_hold', 
                    'inst_cat': 'cap',
                    'date_level': prmt.NaT_proxy}
    remove = multiindex_change(remove, mapping_dict)

    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_duplicated_indices(remove, parent_fn)

    # separate out any rows with negative values
    all_accts_pos = all_accts.loc[all_accts['quant']>0]
    all_accts_neg = all_accts.loc[all_accts['quant']<0]
    
    # combine dfs to subtract from from_acct & add QC_alloc_full_est_1v_MI
    # (groupby sum adds the positive values in all_accts_pos and the neg values in remove)
    all_accts_pos = pd.concat([all_accts_pos, remove, QC_alloc_full_est_1v_MI], sort=True)
    all_accts_pos = all_accts_pos.groupby(level=prmt.standard_MI_names).sum()
    
    # recombine pos & neg
    all_accts = pd.concat([all_accts_pos, all_accts_neg], sort=False)
    
    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)

    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)
# end of convert_QC_alloc_set_aside


# In[ ]:


def transfer_QC_alloc_init__from_alloc_hold(all_accts):
    """
    Moves allocated allowances from alloc_hold into private accounts (gen_acct).
    
    Runs at the end of each year (except for in anomalous years).
    
    Only processes one vintage at a time; vintage is cq.date.year + 1 (except for in anomalous years).
    
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")

    all_accts_sum_init = all_accts['quant'].sum()
    
    # convert QC_alloc_initial (df) into QC_alloc_i (ser)
    QC_alloc_i = prmt.QC_alloc_initial.copy()
    QC_alloc_i.index = QC_alloc_i.index.droplevel('allocation_quarter')
    QC_alloc_i = QC_alloc_i['quant']
    
    QC_alloc_i_1v = QC_alloc_i.loc[cq.date.year:cq.date.year]
    QC_alloc_i_1v.name = f'QC_alloc'
    
    QC_alloc_i_1v_MI = convert_ser_to_df_MI_QC_alloc(QC_alloc_i_1v, 'initial')
    QC_alloc_i_1v_MI.name = 'QC_alloc_initial'
    
    # create df named remove, which is negative of to_acct_MI
    remove = -1 * QC_alloc_i_1v_MI

    # set indices in remove df (version of to_acct_MI) to be same as from_acct
    mapping_dict = {'acct_name': 'alloc_hold', 
                    'inst_cat': 'QC_alloc_set_aside',
                    'date_level': prmt.NaT_proxy}
    remove = multiindex_change(remove, mapping_dict)

    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_duplicated_indices(remove, parent_fn)

    # separate out any rows with negative values
    all_accts_pos = all_accts.loc[all_accts['quant']>0]
    all_accts_neg = all_accts.loc[all_accts['quant']<0]
    
    # combine dfs to subtract from from_acct & add QC_alloc_i_1v_MI
    # (groupby sum adds the positive values in all_accts_pos and the neg values in remove)
    all_accts_pos = pd.concat([all_accts_pos, remove, QC_alloc_i_1v_MI], sort=True)
    all_accts_pos = all_accts_pos.groupby(level=prmt.standard_MI_names).sum()
    
    # recombine pos & neg
    all_accts = all_accts_pos.append(all_accts_neg)
    
    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)

    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)
# end of transfer_QC_alloc_init__from_alloc_hold


# In[ ]:


def process_QC_quarterly(all_accts):

    """
    Function that is used in the loop for each quarter, for each juris.
    
    Applies functions defined earlier, as well as additional rules
    
    Order of sales for each jurisdiction set by jurisdiction-specific functions called within process_quarter.
    
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # pre-test for conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    # object "scenario" holds the data for a particular scenario in various attributes 
    # (scenario_QC.avail_accum, etc.)

    # START-OF-QUARTER STEPS (INCLUDING START-OF-YEAR) ***********************************************

    if cq.date.quarter == 1:
        # start-of-year (circa Jan 15): 
        # convert QC cap allowances to alloc_set_aside, for full (est.) alloc quantity
        all_accts = convert_QC_alloc_set_aside(all_accts)

        # start-of-year (circa Jan 1): for current auction, transfer of annual quantity of allowances
        all_accts = transfer_cur__from_alloc_hold_to_auct_hold_first_principles(all_accts, 'QC')

        all_accts = cur_upsample_avail_state_owned_first_principles(all_accts, 'QC')

        # ~~~~~~~~~~~~~~~~~~~~~
        # for advance auctions:
        if cq.date.year >= 2014 and cq.date.year <= 2027:  
            # start-of-year (circa Jan 1): upsample of allowances for advance auction (before Q1 auctions)
            # note that the model does not attempt to simulate advance auctions for vintages after 2027
            all_accts = upsample_advance_all_accts(all_accts)
        else:
            pass

        # for Q1, take snap (~Jan 5):
        # before transferring QC alloc out of ann_alloc_hold (~Jan 15)
        # and before Q1 auctions (~Feb 15)       
        take_snapshot_CIR(all_accts, 'QC')
        
        # start-of-year (Jan 15): transfer QC allocation, initial quantity (75% of estimated ultimate allocation)           
        all_accts = transfer_QC_alloc_init__from_alloc_hold(all_accts)
    
    else: # cq.date.quarter != 1
        # for Q2-Q4, take snap before auction (no additional steps at the start of each quarter)
        take_snapshot_CIR(all_accts, 'QC')
    
    # END OF START-OF-QUARTER STEPS
    
    
    # STEPS AFTER CIR SNAPSHOT, BUT BEFORE AUCTIONS ***************************
    # cap adjustment for net flow from Ontario (California's share of total ~13.1 M adjustment)
    if cq.date == quarter_period('2019Q3'):
        # Quebec's cap adjustment was on July 10, 2019 (according to note at bottom of 2019Q2 CIR)
        # note that CA cap adjustment occurred June 27, 2019 (in 2019Q2)
        all_accts = retire_for_net_flow_from_Ontario(all_accts, 'QC')
    else:
        pass

    
    # ADVANCE AUCTIONS ********************************************************
    # process advance auctions through vintage 2030, which occur in years through 2027
    logging.info(f"within {inspect.currentframe().f_code.co_name}, start of advance auction")
    
    if cq.date.year <= 2027:
        # ADVANCE AUCTION: MAKE AVAILABLE     
        all_accts = QC_state_owned_make_available(all_accts, 'advance')

        # for QC, no redesignation of unsold advance as advance

        # record available allowances (before process auction)
        scenario_QC.avail_accum = avail_accum_append(all_accts, scenario_QC.avail_accum, 'advance')

        # ADVANCE AUCTION: PROCESS SALES - QC ONLY AUCTIONS
        all_accts = process_auction_adv_all_accts(all_accts, 'QC')

    else: # cq.date.year > 2027
        pass
    
    # CURRENT AUCTION ********************************************************
    logging.info("within process_quarter, start of current auction")
    
    # QC state-owned current: make available for cq.date
    all_accts = QC_state_owned_make_available(all_accts, 'current')         

    all_accts = redesignate_unsold_current_auct(all_accts, 'QC')

    # record available allowances (before process auction)
    scenario_QC.avail_accum = avail_accum_append(all_accts, scenario_QC.avail_accum, 'current')

    # process auction
    all_accts = process_auction_cur_QC_all_accts(all_accts)
    
    # FINISHING AFTER AUCTION: ***************************************************************
    
    if cq.date.quarter == 4:        
        # Q4 PROCESSING AFTER AUCTION **********************************************
        # this includes transfer of consigned portion of alloc into limited_use
        logging.info(f"for {cq.date}, for QC, Q4 processing after auction: start")
        
        # end-of-year: move advance unsold to current auction
        all_accts = adv_unsold_to_cur_all_accts(all_accts)

        logging.info(f"for {cq.date}, Q4 processing after auction: end")
    
    else: 
        # closing "if cq.date.quarter == 4:"
        pass
    
    # END-OF-QUARTER (EVERY QUARTER) *****************************************
    logging.info("end-of-quarter processing (every quarter) - start")
    
    # process historical reserve sales
    all_accts = process_reserve_sales_historical(all_accts, 'QC')

    if prmt.run_tests == True:  
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_for_negative_values(all_accts, parent_fn)

    # September true-ups definitely after auction
    # May auctions might be before auction; not clear; will assume they occur after auctions as well
    # check for QC allocation true-ups; if any, transfer from alloc_hold to gen_acct       
    all_accts = transfer_QC_alloc_trueups__from_alloc_hold(all_accts)
    
    # process negative true-ups (QC only)
    all_accts = transfer_QC_alloc_trueups_neg__to_reserve(all_accts)
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # CLEANUP OF all_accts (each quarter)
    # get rid of fractional allowances, zeros, and NaN
    logging.info("cleanup of all_accts")
    
    all_accts = all_accts.loc[(all_accts['quant']>1e-7) | (all_accts['quant']<-1e-7)]
    all_accts = all_accts.dropna()
    # END OF CLEANUP OF all_accts
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
    # take snap_end at end of each quarter, add to list scenario_QC.snaps_end
    take_snapshot_end(all_accts, 'QC')
        
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
    logging.info("end-of-quarter processing (every quarter) - end")
    
    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)        
        test_conservation_against_full_budget(all_accts, 'QC', parent_fn)  
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)
# end of process_QC_quarterly


# In[ ]:


def QC_state_owned_make_available(all_accts, auct_type):
    """
    For any allowances in auct_hold, with date_level == cq.date, fn changes status to 'available'.
    
    Works for current auction and advance auction, as specified by argument auct_type.
    
    Currently works for QC-only auctions, which never met conditions for redesignation of unsold allowances.
    
    Need to rework the function to work for linked auctions.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
  
    # pre-test: conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    if auct_type in ['advance', 'current']:        
        # get allowances in auct_hold, for specified auct_type, for date_level == cq.date
        mask1 = all_accts.index.get_level_values('acct_name')=='auct_hold'
        mask2 = all_accts.index.get_level_values('auct_type')==auct_type
        mask3 = all_accts.index.get_level_values('date_level')==cq.date
        mask = (mask1) & (mask2) & (mask3)
        
        # to be available
        avail_1q = all_accts.loc[mask]
        
        # update status to 'available'
        mapping_dict = {'status': 'available'}
        avail_1q = multiindex_change(avail_1q, mapping_dict)

        # combine avail with remainder (~mask)
        all_accts = avail_1q.append(all_accts.loc[~mask])
        
    else: # auct_type not 'advance' or 'current'
        print("Error! In QC_state_owned_make_available, auct_type was neither 'current' nor 'advance';") # for UI
        print(f"auct_type was: {auct_type}") # for UI   
    
    if prmt.run_tests == True:
        # TEST: for conservation of allowances
        diff = all_accts['quant'].sum() - all_accts_sum_init
        if abs(diff) > 1e-7:
            print(f"{prmt.test_failed_msg} Allowances not conserved in {inspect.currentframe().f_code.co_name}.")
            print("(Test using initial and final values within fn.)")
            print(f"Was for auct_type: {auct_type}; diff is: {diff}")
        else:
            pass
        # END OF TEST

    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_conservation_against_full_budget(all_accts, 'QC', parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)

    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)
# end of QC_state_owned_make_available


# In[ ]:


def transfer_QC_alloc_trueups__from_alloc_hold(all_accts):
    """
    Transfer Quebec allocation true-ups from allocation holding account (alloc_hold) to private accounts (gen_acct).
    
    Includes hard-coded anomalies for Quebec use of APCR allowances, to represent shortfalls in alloc_hold.
    
    This function only processes positive true-ups.
    
    It draws on prmt.QC_alloc_trueups_non_APCR, which only contains positive true-ups.
    
    (Negative true-ups are handled by transfer_QC_alloc_trueups_neg__to_reserve.)
    
    (True-ups from APCR are handled by _________.)
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # pre-test: conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    # get all the allocation true-ups that occur in a particular quarter
    # (these are only positive true-ups)
    QC_alloc_trueup_1q = prmt.QC_alloc_trueups_non_APCR.loc[
        prmt.QC_alloc_trueups_non_APCR.index.get_level_values('allocation_quarter')==cq.date]

    if len(QC_alloc_trueup_1q) > 0:
        # there are true-ups to process for this quarter

        # from QC_alloc_trueup_1q, get all the emission years that there are true-ups for
        emission_years = QC_alloc_trueup_1q.index.get_level_values('emission_year').tolist()
        
        # iterate through all emission years that had trueups in cq.date        
        for emission_year in emission_years:            
            # get quantity of true-ups for specified emissions year (returns a Series)
            QC_alloc_trueup_1q_1y = QC_alloc_trueup_1q.xs(emission_year, 
                                                          level='emission_year', 
                                                          drop_level=True)
            
            # initialize un-accumulator: quantity remaining of true-ups to transfer
            trueup_remaining = QC_alloc_trueup_1q_1y['quant'].sum()
            
            # sub-fn: process APCR transfers to private accounts for allocations
            # (currently timing and values are hard-coded; could be instead derived from CIRs)
            all_accts, trueup_remaining = transfer_QC_alloc_trueups__from_APCR(all_accts, 
                                                                               trueup_remaining, 
                                                                               emission_year)
                
            cap_transfer = prmt.standard_MI_empty.copy() # initialize
            cap_remain = prmt.standard_MI_empty.copy() # initialize

            # TEST: QC_alloc_trueup_1q_1y should only be a single row
            if len(QC_alloc_trueup_1q_1y) != 1:
                print(f"{prmt.test_failed_msg} QC_alloc_trueup_1q_1y did not have 1 row. Here's QC_alloc_trueup_1q_1y:")
                print(QC_alloc_trueup_1q_1y)
            # END OF TEST

            # get allowances in alloc_hold, for juris == 'QC', and vintage == emission_year
            # only those of inst_cat == 'QC_alloc_set_aside'
            mask1 = all_accts.index.get_level_values('juris')=='QC'
            mask2 = all_accts.index.get_level_values('acct_name')=='alloc_hold'
            mask3 = all_accts.index.get_level_values('inst_cat')=='QC_alloc_set_aside'
            mask4 = all_accts.index.get_level_values('vintage')==emission_year
            mask5 = all_accts['quant'] > 0
            all_accts_trueup_mask = (mask1) & (mask2) & (mask3) & (mask4) & (mask5)
            trueup_potential = all_accts.loc[all_accts_trueup_mask].sort_values(by='vintage')
            remainder = all_accts.loc[~all_accts_trueup_mask]

            # overall method:
            # if not enough allowances, check for remaining cap allowances
            # if still not enough, create deficit
            # if known use of APCR historically, use that to cancel out deficit

            # create df of those transferred:
            # copy whole df trueup_potential, zero out values, then set new values in loop
            # sort_index to ensure that earliest vintages are drawn from first
            trueup_potential = trueup_potential.sort_index()

            # initialize df trueup_transfers
            trueup_transfers = trueup_potential.copy()  
            trueup_transfers['quant'] = float(0)

            trueup_potential_quant = trueup_potential['quant'].sum()

            for row in trueup_potential.index:
                potential_row_quant = trueup_potential.at[row, 'quant']
                trueup_to_transfer_quant = min(potential_row_quant, trueup_remaining)

                # update un-accumulator for jurisdiction
                trueup_remaining = trueup_remaining - trueup_to_transfer_quant

                # update trueup_potential
                trueup_potential.at[row, 'quant'] = potential_row_quant - trueup_to_transfer_quant

                # update trueup_transfers
                trueup_transfers.at[row, 'quant'] = trueup_to_transfer_quant

            if trueup_remaining > 1e-7:
                # there were insufficient QC_alloc_set_aside allowances for the true-up

                # check for remaining cap allowances of vintage == emission_year
                mask1 = remainder.index.get_level_values('juris')=='QC'
                mask2 = remainder.index.get_level_values('acct_name')=='alloc_hold'
                mask3 = remainder.index.get_level_values('inst_cat')=='cap'
                mask4 = remainder.index.get_level_values('vintage')==emission_year
                mask5 = remainder['quant'] > 0
                cap_remain_mask = (mask1) & (mask2) & (mask3) & (mask4) & (mask5)
                cap_remain = remainder.loc[cap_remain_mask].sort_values(by='vintage')
                remainder = remainder.loc[~cap_remain_mask]

                cap_remain_quant = cap_remain['quant'].sum()                     

                cap_transfer = cap_remain.copy()
                cap_transfer['quant'] = float(0)

                if cap_remain_quant > 0:
                    for row in cap_remain.index:

                        trueup_to_transfer_quant = min(cap_remain_quant, trueup_remaining)

                        cap_transfer.at[row, 'quant'] = trueup_to_transfer_quant

                        # update un-accumulator for jurisdiction
                        trueup_remaining = trueup_remaining - trueup_to_transfer_quant

                        # update cap_remain
                        cap_remain.at[row, 'quant'] = cap_remain_quant - trueup_to_transfer_quant

                    # if still not enough (trueup_remaining > 0), create a deficit of cap allowances
                else:
                    # no cap remain; if necessary, next create deficit
                    pass
            elif trueup_remaining == 0:
                # trueup_remaining was zero before needing to use cap allowances
                pass

            if trueup_remaining > 1e-7:
                # trueup_remaining is still > 0 after using up cap; need to create deficit

                # create deficit
                # take from cap, vintage = emission_year
                # (then compare against CIR to see how it matches)
                # set status = 'deficit'

                ser = pd.Series({emission_year: trueup_remaining})
                df = pd.DataFrame(ser)
                df.columns = ['quant']
                df.index.name = 'vintage'
                df = df.reset_index()

                df['acct_name'] = 'alloc_hold'
                df['juris'] = 'QC' # this function only applies to QC
                df['inst_cat'] = 'cap'
                # df['vintage'] = emission_year
                df['auct_type'] = 'n/a'
                df['newness'] = 'n/a'
                df['status'] = 'deficit'
                df['date_level'] = prmt.NaT_proxy
                df['unsold_di'] = prmt.NaT_proxy
                df['unsold_dl'] = prmt.NaT_proxy
                df['units'] = 'MMTCO2e'

                df = df.set_index(prmt.standard_MI_names)

                alloc_trueup = df.copy()
                deficit = df.copy() * -1 # to reverse the sign of the quant
                
                # update trueup_remaining
                trueup_remaining = 0 # because all trueup_remaining put into deficit      

                all_accts = pd.concat([all_accts, deficit, alloc_trueup], sort=False)

            elif trueup_remaining == 0:
                # no more trueup_remaining, so this set of trueups is done
                pass

            elif abs(trueup_remaining) < 1e-7:
                # trueup_remaining is partial allowance
                pass

            else:
                print(f"In transfer_QC_alloc_trueups__from_alloc_hold, for {cq.date}, unknown edge case; trueup_remaining: {trueup_remaining}") # for UI
                pass

            # TEST: trueup_remaining should be zero
            if abs(trueup_remaining) > 1e-7:
                print(f"{prmt.test_failed_msg} trueup_remaining was supposed to be zero, but was: {trueup_remaining}") # for UI
            # END OF TEST

            # update metadata for transferred allowances
            # record date of allocation in index level 'date_level'
            mapping_dict = {'acct_name': 'gen_acct',
                            'inst_cat': f'QC_alloc_{emission_year}', 
                            'date_level': cq.date}
            trueup_transfers = multiindex_change(trueup_transfers, mapping_dict)     

            # recombine trueup_transfers, trueup_potential (what's remaining), and the rest of all_accts
            all_accts = pd.concat([trueup_transfers, 
                                   trueup_potential, 
                                   cap_transfer,
                                   cap_remain,
                                   remainder], sort=False)

            # do groupby sum of pos & neg, recombine
            all_accts_pos = all_accts.loc[all_accts['quant']>1e-7].groupby(level=prmt.standard_MI_names).sum()
            all_accts_neg = all_accts.loc[all_accts['quant']<-1e-7].groupby(level=prmt.standard_MI_names).sum()
            all_accts = all_accts_pos.append(all_accts_neg)

        # end of "for emission_year in all_emissions_years:"
    
    else:
        # closing "if len(QC_alloc_trueup_1q) > 0:"
        pass
    
    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_during_transfer(all_accts, all_accts_sum_init, 'QC_alloc')
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)
# end of transfer_QC_alloc_trueups__from_alloc_hold


# In[ ]:


def transfer_QC_alloc_trueups__from_APCR(all_accts, trueup_remaining, emission_year):
    """
    Transfers allowances from APCR to private accounts for allocations. Applies only to QC.
    
    Emissions year (the timing emissions that the allocations are intended to cover) inferred to be the year prior.
    
    Modifies remaining true-ups for a given emission year. 
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # ***** SPECIAL CASES *****
    QC_alloc_trueups_from_APCR = prmt.QC_alloc_trueups_non_APCR.dropna(subset=['quant_APCR'])
    
    if cq.date in QC_alloc_trueups_from_APCR.index.get_level_values('allocation_quarter'):
        # draw from QC APCR, only taking non-vintage allowances (using 2200 as proxy)
        # (this excludes vintaged allowances added back to reserve through negative true-ups)
        mask1 = all_accts.index.get_level_values('acct_name')=='APCR_acct'
        mask2 = all_accts.index.get_level_values('juris')=='QC'
        mask3 = all_accts.index.get_level_values('vintage')==2200
        mask = (mask1) & (mask2) & (mask3)
        QC_ACPR_acct = all_accts.loc[mask]

        APCR_for_trueup_quant = prmt.QC_alloc_trueups_non_APCR.xs((cq.date.year-1, cq.date))['quant_APCR']
        
        inst_cat_new_name = f'QC_alloc_{emission_year}_APCR' # used to update metadata below
        
        # update quantity
        # (only if QC_APCR_acct has a single row, and the APCR quantity is > 0)
        if len(QC_ACPR_acct) == 1 and APCR_for_trueup_quant > 0:
            trueup_transfers = QC_ACPR_acct.copy()
            trueup_transfers.at[trueup_transfers.index[0], 'quant'] = APCR_for_trueup_quant
            
            # create remove df:
            remove = -1 * trueup_transfers.copy()

            # update metadata for trueup_transfers; record allocation distribution date as 'date_level'
            mapping_dict = {'acct_name': 'gen_acct', 
                            'inst_cat': inst_cat_new_name, 
                            'date_level': cq.date}
            trueup_transfers = multiindex_change(trueup_transfers, mapping_dict)

            # do groupby sum of pos & neg, recombine
            # concat all_accts, trueup_transfers, remove
            all_accts_pos = all_accts.loc[all_accts['quant']>1e-7]
            all_accts_pos = pd.concat([all_accts_pos, trueup_transfers, remove], sort=True)
            all_accts_pos = all_accts_pos.groupby(level=prmt.standard_MI_names).sum()
            all_accts_neg = all_accts.loc[all_accts['quant']<-1e-7]
            all_accts = all_accts_pos.append(all_accts_neg)

            # update trueup_remaining, for use in regular processing below
            
            # where emission_year is from fn transfer_QC_alloc_trueups__from_alloc_hold
            trueup_remaining = trueup_remaining - APCR_for_trueup_quant
            
        else:
            print("Error" + "! QC APCR expected to have a single row, but did not.") # for UI
            print("Method above for setting value doesn't work, and QC APCR true-up was not processed.") # for UI
            print("Show QC_ACPR_acct:") # for UI
            print(QC_ACPR_acct) # for UI
            
    else: # not cq.date == quarter
        pass
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")

    return(all_accts, trueup_remaining)
# end of transfer_QC_alloc_trueups__from_APCR


# In[ ]:


def transfer_QC_alloc_trueups_neg__to_reserve(all_accts):
    """
    For QC allocations true-ups that are negative, allowances are transferred from private to reserve account.
    
    This is based on historical practice, inferred from CIRs.
    
    We infer it is justified by the rule in regulation that APCR must be replenished, if used for allocations.
    
    Given the scale of negative true-ups and APCR distributions for allocations, it seems unlikely full replenishment
    will occur through this mechanism.
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # pre-test: conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    neg_q = prmt.QC_alloc_trueups_neg.loc[
        prmt.QC_alloc_trueups_neg.index.get_level_values('allocation_quarter')==cq.date]
    
    if len(neg_q) > 0:
        neg_q.index = neg_q.index.droplevel('allocation_quarter')
        for emission_year in neg_q.index:            
            # transfer allowances of this vintage from private accounts to reserve accounts
            # only transfer QC juris allowances, which had previously been distributed as allocations
            mask1 = all_accts.index.get_level_values('juris')=='QC'
            mask2 = all_accts.index.get_level_values('acct_name')=='gen_acct'
            mask3 = all_accts.index.get_level_values('inst_cat')==f'QC_alloc_{emission_year}'
            mask4 = all_accts.index.get_level_values('vintage')==emission_year
            mask5 = all_accts['quant'] > 0
            all_accts_trueup_neg_mask = (mask1) & (mask2) & (mask3) & (mask4) & mask5
            
            trueup_neg_potential = all_accts.loc[all_accts_trueup_neg_mask].sort_values(by='vintage')
            remainder = all_accts.loc[~all_accts_trueup_neg_mask]
            
            # modify trueup_neg_potential:
            # 1. zero out all values
            # 2. keep only the first row
            # 3. modify date_level to be cq.date
            # 4. modify quant to be the negative trueup quantity (with the negative sign)
            df = trueup_neg_potential.copy()
            df['quant'] = 0
            df = df.head(1)
            mapping_dict = {'date_level': cq.date}
            df = multiindex_change(df, mapping_dict)
            df.loc[df.index] = neg_q.loc[emission_year, 'quant']
            trueup_neg_to_subtract = df.copy()
                  
            # modify df to create set of allowances to add to reserve
            # 1. change sign to positive (multiply by -1)
            # 2. modify metadata: 'acct_name' == 'APCR_acct', 'auct_type' == 'reserve'
            df = df * -1
            mapping_dict = {'acct_name': 'APCR_acct', 
                            'auct_type': 'reserve'}
            df = multiindex_change(df, mapping_dict)
            trueup_neg_to_reserve = df.copy()

            all_accts = pd.concat([all_accts, trueup_neg_to_subtract, trueup_neg_to_reserve], sort=True)
            # no need to do groupby sums; metadata distinct for each set of allowances   
    
    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_during_transfer(all_accts, all_accts_sum_init, 'QC_alloc')
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)
# end of transfer_QC_alloc_trueups_neg__to_reserve


# In[ ]:


def QC_early_action_distribution(all_accts):
    """
    Create Early Action allowances and distribute them to gen_acct.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # for Early Action, use vintage 2199 as proxy non-vintage allowances
    # this keeps Early Action separate from APCR (vintage 2200)
    # data hard-coded into model, because one-off event
    ser = pd.Series({2199: 2.040026})

    df = pd.DataFrame(ser)
    df.columns = ['quant']
    df.index.name = 'vintage'
    df = df.reset_index()

    df['acct_name'] = 'gen_acct'
    df['auct_type'] = 'n/a'
    df['juris'] = 'QC'

    # acct_name set above
    df['date_level'] = prmt.NaT_proxy
    # juris set above
    # vintage set above
    df['inst_cat'] = 'early_action'
    # auct_type set above
    df['newness'] = 'n/a'
    df['status'] = 'n/a'
    df['unsold_di'] = prmt.NaT_proxy
    df['unsold_dl'] = prmt.NaT_proxy
    df['units'] = 'MMTCO2e'

    df = df.set_index(prmt.standard_MI_names)

    QC_early_action = df 
    
    all_accts = all_accts.append(QC_early_action)
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)
# end of QC_early_action_distribution


# ## Functions: Tracking (within master function)
# * avail_accum_append [tracking]
# * take_snapshot_end [tracking]
# * take_snapshot_CIR [tracking]

# In[ ]:


def avail_accum_append(all_accts, avail_accum, auct_type_specified):
    """
    Append allowances available at auction to avail_accum. Runs for advance and current auctions.
    """
    
    if prmt.verbose_log == True:
        logging.info(f"{inspect.currentframe().f_code.co_name}")
    
    # record allowances available in each auction
    avail_1q = all_accts.loc[(all_accts.index.get_level_values('status')=='available') & 
                             (all_accts.index.get_level_values('auct_type')==auct_type_specified)]

    # TEST
    if prmt.run_tests == True:
        if len(avail_1q) > 0:
            # check that all available allowances have date_level == cq.date
            avail_1q_dates = avail_1q.index.get_level_values('date_level').unique().tolist()
            if avail_1q_dates != [cq.date]:
                print(f"{prmt.test_failed_msg} Inside {inspect.currentframe().f_code.co_name}...")
                print(f"... for {cq.date}, auct_type {auct_type_specified}...")
                print(f"... available had some other date_level than cq.date. Here's avail_1q:")
                print(avail_1q)
                print()
            else:
                pass
            
        elif len(avail_1q) == 0:
            print(f"{prmt.test_failed_msg} Inside {inspect.currentframe().f_code.co_name}...")
            print(f"... for {cq.date}, auct_type {auct_type_specified}, available is empty df.")
            print()
    else:
        pass
    # END OF TEST
            
    avail_accum = avail_accum.append(avail_1q)
    
    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_for_duplicated_indices(avail_accum, parent_fn)
        test_for_negative_values(avail_accum, parent_fn)
        
    if prmt.verbose_log == True:
        logging.info(f"{inspect.currentframe().f_code.co_name} (end)")

    return(avail_accum)
# end of avail_accum_append


# In[ ]:


def take_snapshot_end(all_accts, juris):
    """
    Take a snapshot of all_accts at the end of each quarter.
    
    This is to enable later start of a scenario from any given ending point.
    
    """    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    snap_end = all_accts.copy()
    snap_end['snap_q'] = cq.date
    
    if juris == 'CA':
        scenario_CA.snaps_end += [snap_end]
    elif juris == 'QC':
        scenario_QC.snaps_end += [snap_end]

    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")

    # no return; updates object attributes
# end of take_snapshot_end


# In[ ]:


def take_snapshot_CIR(all_accts, juris):
    """
    Take a snapshot of all_accts, which is later modified for comparison with Compliance Instrument Report (CIR).
    
    snap_CIR labeled with a particular quarter is actually taken early in the following quarter.
    (Example: 2014Q4 snap_CIR is taken in early 2015Q1)
    
    This is following regulators' practice in CIR.
    
    So a snap_CIR taken early in cq.date is labeled as from previous_q (1 quarter before cq.date).
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    previous_q = (pd.to_datetime(f'{cq.date.year}Q{cq.date.quarter}') - DateOffset(months=3)).to_period('Q')
    
    snap_CIR = all_accts.copy()
    snap_CIR['snap_q'] = previous_q
    
    if juris == 'CA':
        scenario_CA.snaps_CIR += [snap_CIR]
    elif juris == 'QC':
        scenario_QC.snaps_CIR += [snap_CIR]

    logging.info(f"{inspect.currentframe().f_code.co_name} named {previous_q} (end)")

    # no return; updates object attributes
# end of take_snapshot_CIR


# ## Functions: Miscellaneous other
# * net_flow_from_Ontario_add_to_all_accts
# * retire_for_net_flow_from_Ontario

# In[ ]:


def net_flow_from_Ontario_add_to_all_accts(all_accts, juris):
    """
    When Ontario de-linked from WCI in 2018Q2, there was a net flow of 13.186967 M allowances into WCI.
    
    These can be attributed to particular vintages, following the approach in Near Zero's research note, 
    "Ontario’s exit exacerbates allowance overallocation in the Western Climate Initiative cap-and-trade program" 
    (July 16, 2018)
    
    This function adds allowances to all_accts with jurisdiction (juris) of 'ON' to represent this net flow.
    
    Note that because of mixing of allowances with Ontario, that for all vintages up to 2021, the juris assigned
    in all_accts can't be taken literally; CA and QC allowances would have been bought by ON-based entities,
    and vice versa.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # As noted in 2018Q2 CIR:
    # "As of that date, there are 13,186,967 more compliance instruments held in California and Québec accounts 
    # than the total number of compliance instruments issued by those two jurisdictions alone."
    
    # Net flow from Ontario by vintage calculated in Near Zero's research note, "Ontario’s exit exacerbates 
    # allowance overallocation in the Western Climate Initiative cap-and-trade program" (July 16, 2018).
    # Calculations based on the difference in vintaged allowances in the 2018Q2 CIR from the 2018Q1, 
    # and accounting for removal of the total quantity of Ontario vintaged (non-reserve) allowances.
    net_flow_from_ON_dict = {2016: -8.273491, 
                             2017:  8.681311, 
                             2018:  6.935795, 
                             2019: -0.059823, 
                             2020:  2.511752, 
                             2021:  3.391423}
    
    net_flow_from_ON_ser = pd.Series(net_flow_from_ON_dict)
        
    # convert Series to MultiIndex df with the following metadata:
    # (based on steps in function convert_ser_to_df_MI)
    df = pd.DataFrame(net_flow_from_ON_ser)
    df.index.name = 'vintage'
    df = df.reset_index()
    df['acct_name'] = 'gen_acct'
    df['juris'] = 'ON' # assign these allowances vintage 'ON' to distinguish from others
    df['inst_cat'] = 'n/a'
    # vintages already in Series net_flow_from_ON
    df['auct_type'] = 'n/a'
    df['newness'] = 'n/a'
    df['status'] = 'n/a'
    df['date_level'] = prmt.NaT_proxy
    df['unsold_di'] = prmt.NaT_proxy
    df['unsold_dl'] = prmt.NaT_proxy
    df['units'] = 'MMTCO2e'
    df = df.set_index(prmt.standard_MI_names)
    df = df.rename(columns={0: 'quant'})
    
    # set value of prmt.net_flow_from_ON; used also in CIR comparison
    prmt.net_flow_from_ON = df
    
    # 2019Q2 CIR notes at bottom:                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
    # "On June 27, 2019, California retired an equal amount of vintages 2021 through 2030 for a total of 11,340,792 
    # allowances. Québec retired 1,846,175 vintage 2017 allowances from the Auction Account on July 10, 2019."
    
    # set in initialization as prmt.CA_cap_adj_for_ON_net_flow & prmt.QC_cap_adj_for_ON_net_flow
    
    # assign share of Ontario net flow to each jurisdiction, based on the responsibility accepted in 2019
    CA_share = prmt.CA_cap_adj_for_ON_net_flow / net_flow_from_ON_ser.sum()
    QC_share = prmt.QC_cap_adj_for_ON_net_flow / net_flow_from_ON_ser.sum()
    
    # create allowances of juris == 'ON' within the all_accts df for each juris (CA & QC)
    if juris == 'CA':
        # then actually modifying all_accts_CA; all_accts is local variable name
        net_flow_from_ON_CA = prmt.net_flow_from_ON * CA_share
        
        # change inst_cat to record juris that took responsibility
        mapping_dict = {'inst_cat': 'net_flow_ON_to_CA'}
        net_flow_from_ON_CA = multiindex_change(net_flow_from_ON_CA, mapping_dict)
        
        # add allowances to all_accts
        all_accts = all_accts.append(net_flow_from_ON_CA)
        
    elif juris == 'QC':
        # then actually modifying all_accts_QC; all_accts is local variable name
        net_flow_from_ON_QC = prmt.net_flow_from_ON * QC_share
        
        # change inst_cat to record juris that took responsibility
        mapping_dict = {'inst_cat': 'net_flow_ON_to_QC'}
        net_flow_from_ON_QC = multiindex_change(net_flow_from_ON_QC, mapping_dict)
        
        # add allowances to all_accts
        all_accts = all_accts.append(net_flow_from_ON_QC)
        
    else:
        print(f'net_flow_from_Ontario_add_to_all_accts encountered unknown case for juris: {juris}') # for UI

    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)
# end of net_flow_from_Ontario_add_to_all_accts


# In[ ]:


def retire_for_net_flow_from_Ontario(all_accts, juris):
    """
    In 2019, CA & QC retired allowances to compensate for the net flow of allowances from Ontario.
    
    Quantities, details on vintages retired, and timing of retirements are described in 2019Q2 CIR.
    
    2019Q2 CIR noted (at bottom:                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
    "On June 27, 2019, California retired an equal amount of vintages 2021 through 2030 for a total of 11,340,792 
    allowances. Québec retired 1,846,175 vintage 2017 allowances from the Auction Account on July 10, 2019."
    
    Values set in initialization as prmt.CA_cap_adj_for_ON_net_flow & prmt.QC_cap_adj_for_ON_net_flow.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
        
    # pre-test: conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    if juris == 'CA':
        # calculate annual quantity for adjustment
        CA_cap_adj_ann = prmt.CA_cap_adj_for_ON_net_flow / len(range(2021, 2030+1))
        
        # transfer allowances of each vintage 2021-2030 from alloc_hold to retirement
        for vintage in range(2021, 2030+1):
            mask1 = all_accts.index.get_level_values('acct_name') == 'alloc_hold'
            mask2 = all_accts.index.get_level_values('inst_cat') == 'cap'
            mask3 = all_accts.index.get_level_values('vintage') == vintage
            mask = (mask1) & (mask2) & (mask3)
            masked = all_accts.loc[mask]
            
            # TEST: result should only be a single row
            if len(masked) == 1:
                pass
            else:
                print(f"in retire_for_net_flow_from_Ontario, for {juris}, selected df len != 1; len was: {len(masked)}") # for UI
            # END OF TEST
            
            # set new value for quantity
            df = masked.copy()
            df.loc[df.index, 'quant'] = CA_cap_adj_ann
            to_retire = df.copy()
            to_remove = -1 * to_retire.copy()
            
            # update metadata for to_retire
            mapping_dict = {'acct_name': 'retirement', 
                            'inst_cat': 'retired_for_ON'}
            to_retire = multiindex_change(to_retire, mapping_dict)
            
            # recombine
            all_accts = pd.concat([all_accts, to_retire, to_remove], sort=False)
            
        # groupby sum to remove quantities from alloc_hold (combine positive and negative rows)
        all_accts = all_accts.groupby(level=prmt.standard_MI_names).sum()
        
    elif juris == 'QC':
        # transfer allowances of vintage 2017 from auct_hold to retirement
        # infer that's what QC has done;
        # they have already distributed the main true-up for 2017 emissions, in September 2018
        # so the only sufficient set of vintage 2017 government-held allowances are those unsold in 2017
        mask1 = all_accts.index.get_level_values('acct_name') == 'auct_hold'
        mask2 = all_accts.index.get_level_values('inst_cat') == 'QC'
        mask3 = all_accts.index.get_level_values('status') == 'unsold'
        mask4 = all_accts.index.get_level_values('vintage') == 2017
        mask = (mask1) & (mask2) & (mask3) & (mask4)
        
        masked = all_accts.loc[mask]
        
        # TEST: result should only be a single row (because there was only 1 quarter in 2017 with unsold allowances)
        if len(masked) == 1:
            pass
        else:
            print(f"in retire_for_net_flow_from_Ontario, for {juris}, selected df len != 1; len was: {len(masked)}") # for UI
        # END OF TEST

        # set new value for quantity
        df = masked.copy()
        df.loc[df.index, 'quant'] = prmt.QC_cap_adj_for_ON_net_flow
        to_retire = df.copy()
        to_remove = -1 * to_retire.copy()
        
        # update metadata for to_retire
        mapping_dict = {'acct_name': 'retirement', 
                        'inst_cat': 'retired_for_ON'}
        to_retire = multiindex_change(to_retire, mapping_dict)

        # recombine
        all_accts = pd.concat([all_accts, to_retire, to_remove], sort=False)
        
        # groupby sum to remove quantities from alloc_hold (combine positive and negative rows)
        all_accts = all_accts.groupby(level=prmt.standard_MI_names).sum()
    
    else:
        print(f"Other juris specified that model is not set up to handle: {juris}") # for UI
    
    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_against_full_budget(all_accts, juris, parent_fn)
        test_conservation_during_transfer(all_accts, all_accts_sum_init, 'CA cap adjustment for net flow from ON') 
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)
# end of retire_for_net_flow_from_Ontario


# ## Functions: Quarterly processes
# * retire_for_EIM_outstanding
# * retire_for_bankruptcy
# * transfer_unsold__from_auct_hold_to_APCR
# * process_auction_cur_QC_all_accts

# In[ ]:


def retire_for_EIM_outstanding(all_accts):
    
    """
    For CA, moves allowances to Retirement account, to account for emissions not counted in Energy Imbalance Market.
    
    Function runs every year at the end of Q3.
    
    The EIM Outstanding emissions incurred in the following periods are handled in the following manner:
    
    Under Oct 2017 regulations (§ 95852(b)(1)(D))
    * incurred 2016: retired in 2018, from state-owned current allowances remaining unsold at more than 24 months.
    * incurred 2017: retired in 2018, from state-owned current allowances remaining unsold at more than 24 months.
    
    This occurs prior to processing transfer to APCR of the same pool, reducing that pool of allowances.

    This rule (§ 95852(b)(1)(D)) was deleted from April 2019 regulations.

    Under Apr 2019 regulations (§ 95852(l)(1), § 95892(a)(3)):
    * incurred 2018: will be retired in 2019, from state-owned allowances of vintage 2022 
    * incurred 2019Q1: will be retired in 2020, from state-owned allowances of vintage 2023 
    * incurred 2019Q2-Q4: will be retired in 2020Q3, from electricity allocations of vintage 2021 
    * incurred 2020: retired in 2021Q3, from electricity allocations of vintage 2022 
    * incurred 2021-2028: from electricity allocations, following same pattern as for EIM incurred in 2020
    * incurred after 2028: no retirement unless cap-and-trade program is extended beyond 2030
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # pre-test for conservation
    all_accts_sum_init = all_accts['quant'].sum()
    
    if cq.date.year in range(2018, 2029+1):
        # there are EIM outstanding to process
        # final year is in cq.date.year = 2029; that is the year when vintage 2030 are retired for EIM outstanding
        # and no higher vintages than 2030 exist

        if cq.date.year == 2018:          
            # Oct 2017 regulations applied; EIM retirements came from allowances unsold >24 months

            # get unsold CA state-owned current allowances in auct_hold, with unsold_di > 2 years (24 mo.) earlier

            # cut-off date: if allowances with unsold_di of this date or earlier remain unsold,
            # they are eligible to be retired for EIM

            # this function runs after current auction in cq.date, 
            # so any remaining unsold for 2 years at the time the function runs...
            # ... will still be unsold at the start of the next quarter, at which point they'll be unsold > 2 years

            # ----- QUANTITY TO RETIRE -----
            # in 2018, get the EIM Outstanding incurred 2016-2017
            EIM_remaining_to_retire = prmt.EIM_outstanding.loc[cq.date.year-2:cq.date.year-1].sum()

            # ----- ALLOWANCE POOL TO RETIRE FROM -----
            cut_off_date = pd.to_datetime(cq.date.to_timestamp() - DateOffset(years=2)).to_period('Q')
            
            # get unsold CA state-owned current allowances in auct_hold, with unsold_di >= 2 years (24 mo.) earlier
            mask1 = all_accts.index.get_level_values('acct_name')=='auct_hold'
            mask2 = all_accts.index.get_level_values('inst_cat')=='CA'
            mask3 = all_accts.index.get_level_values('auct_type')=='current'
            mask4 = all_accts.index.get_level_values('status')=='unsold'
            mask5 = all_accts.index.get_level_values('unsold_di')<=cut_off_date # see note below
            mask6 = all_accts['quant'] > 0
            mask = (mask1) & (mask2) & (mask3) & (mask4) & (mask5) & (mask6)
            
            vintage_to_retire = 'misc. (from unsold)'

            # note: for applying cut_off_date, uses <= (rather than ==)
            # because this is after the auctions in which allowances hit the 24-month limit
            
        elif cq.date.year == 2019:
            # April 2019 regulations apply
            # EIM outstanding incurred in 2018 will be retired in 2019, from vintage 2022 state-owned allowances

            # ----- QUANTITY TO RETIRE -----
            # in 2019, get the EIM Outstanding incurred in 2018
            EIM_remaining_to_retire = prmt.EIM_outstanding.loc[cq.date.year-1]

            # ----- ALLOWANCE POOL TO RETIRE FROM -----
            # get state-owned allowances still in alloc_hold
            mask1 = all_accts.index.get_level_values('acct_name')=='alloc_hold'
            mask2 = all_accts.index.get_level_values('juris')=='CA'
            mask3 = all_accts.index.get_level_values('inst_cat')=='cap'
            mask4 = all_accts['quant'] > 0
            vintage_to_retire = cq.date.year+3
            mask_vint = all_accts.index.get_level_values('vintage')==vintage_to_retire
            mask = (mask1) & (mask2) & (mask3) & (mask4) & (mask_vint)

        elif cq.date.year == 2020:
            # April 2019 regulations apply             
            # have to split EIM Outstanding incurred in 2019: Q1 & Q2-Q4
            
            # for EIM Outstanding incurred in 2019Q1

            # ----- QUANTITY TO RETIRE -----
            # assume EIM outstanding incurred in Q1 was 1/4 of annual total
            EIM_remaining_to_retire = prmt.EIM_outstanding.loc[cq.date.year-1] * (1/4)
            
            # ----- ALLOWANCE POOL TO RETIRE FROM -----
            # get state-owned allowances still in alloc_hold
            # (but for this set, there is no corresponding reduction in electricity allocation)
            mask1 = all_accts.index.get_level_values('acct_name')=='alloc_hold'
            mask2 = all_accts.index.get_level_values('juris')=='CA'
            mask3 = all_accts.index.get_level_values('inst_cat')=='cap'
            mask4 = all_accts['quant'] > 0
            vintage_to_retire = cq.date.year+3
            mask_vint = all_accts.index.get_level_values('vintage')==vintage_to_retire
            mask = (mask1) & (mask2) & (mask3) & (mask4) & (mask_vint)
            
            # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # SPECIAL CASE:
            # for EIM incurred 2019Q2-Q4, reduce electricity allocations for 2 years after year incurred,
            # which is same year as cq.date.year+1
            # (the modification of elec alloc occurs in initialize_elec_alloc)
            
            # assume EIM outstanding incurred in Q2-Q4 was 3/4 of annual total
            EIM_remaining_to_retire_2019Q2_Q4 = prmt.EIM_outstanding.loc[cq.date.year-1] * (3/4)
            
            # mask created below for special case of EIM_remaining_to_retire_2019Q2_Q4
            
        elif cq.date.year in range(2021, 2029+1):
            # April 2019 regulations apply

            # ----- QUANTITY TO RETIRE -----
            EIM_remaining_to_retire = prmt.EIM_outstanding.loc[cq.date.year-1]

            # ----- ALLOWANCE POOL TO RETIRE FROM -----
            # For EIM incurred 2020 and beyond, 
            # EIM outstanding reduce electricity allocations in the year cq.date.year+1
            # (in the year 2 years after EIM outstanding incurred).
            # Modification of elec alloc occurs in initialize_elec_alloc, and leaves allowances in alloc_hold.
            
            # retire cap allowances of the quantity that was not allocated, of vintage = cq.date.year+1
            
            # get state-owned allowances still in alloc_hold
            mask1 = all_accts.index.get_level_values('acct_name')=='alloc_hold'
            mask2 = all_accts.index.get_level_values('juris')=='CA'
            mask3 = all_accts.index.get_level_values('inst_cat')=='cap'
            mask4 = all_accts['quant'] > 0
            vintage_to_retire = cq.date.year+1
            mask_vint = all_accts.index.get_level_values('vintage')==vintage_to_retire
            mask = (mask1) & (mask2) & (mask3) & (mask4) & (mask_vint) 
            
        else:
            # cq.date.year is either:
            # 1. earlier than EIM retirements began, or 
            # 2. after the point at which retirements would have to be from post-2030 vintages
            pass
        
        # ----- RETIREMENT -----

        # unsold to potentially retire for EIM, based on mask created above
        # sort_index to ensure earliest vintages are drawn from first
        retire_potential = all_accts.copy().loc[mask]
        retire_potential = retire_potential.sort_index()
        
        # create df for adding transfers; copy of retire_potential, but with values zeroed out
        to_retire = retire_potential.copy()
        to_retire['quant'] = float(0)
        
        for row in retire_potential.index:            
            potential_row_quant = retire_potential.at[row, 'quant']
            to_retire_quant = min(potential_row_quant, EIM_remaining_to_retire)

            # update un-accumulator for jurisdiction
            EIM_remaining_to_retire += -1 * to_retire_quant

            # update retire_potential
            retire_potential.at[row, 'quant'] = potential_row_quant - to_retire_quant

            # update to_retire df
            to_retire.at[row, 'quant'] = to_retire_quant
            
            # vintage_to_retire = to_retire.loc[row].index.get_level_values('vintage') # for logging
            logging.info(f"for EIM Outstanding Emissions, in {cq.date}, retired {to_retire_quant} M of vintage {vintage_to_retire}")

        # what remains in retire_potential is not retired; to be concat with other pieces below
        
        mapping_dict = {'acct_name': 'retirement', 
                        'inst_cat': 'EIM_retire', 
                        'date_level': cq.date}
        to_retire = multiindex_change(to_retire, mapping_dict)
        
        # concat to_retire with all_accts remainder
        all_accts = pd.concat([all_accts.loc[~mask], retire_potential, to_retire], sort=True)
        all_accts = all_accts.groupby(level=prmt.standard_MI_names).sum()
        
        # ~~~~~~~~~~~~~
        # for special case of 2019Q2-Q4 elec alloc, use mask_2019Q2_Q4
        # do retirement for that set of allowances here
        
        if cq.date.year == 2020:
            # retire cap allowances of the quantity that was not allocated, of vintage = cq.date.year+1
            # (re-use mask1 to mask4 above)
            # get state-owned allowances still in alloc_hold
            mask1 = all_accts.index.get_level_values('acct_name')=='alloc_hold'
            mask2 = all_accts.index.get_level_values('juris')=='CA'
            mask3 = all_accts.index.get_level_values('inst_cat')=='cap'
            mask4 = all_accts['quant'] > 0
            vintage_to_retire = cq.date.year+1
            mask_vint = all_accts.index.get_level_values('vintage')==vintage_to_retire
            mask_2019Q2_Q4 = (mask1) & (mask2) & (mask3) & (mask4) & (mask_vint)
        
            # set variables to values for special case
            # (note that this runs after the initial set of EIM retirements in this year)
            
            # repeat general steps above
            # unsold to potentially retire for EIM, based on mask created above
            # sort_index to ensure earliest vintages are drawn from first
            retire_potential = all_accts.copy().loc[mask_2019Q2_Q4]
            retire_potential = retire_potential.sort_index()

            # create df for adding transfers; copy of retire_potential, but with values zeroed out
            to_retire = retire_potential.copy()
            to_retire['quant'] = float(0)

            for row in retire_potential.index:
                potential_row_quant = retire_potential.at[row, 'quant']
                to_retire_quant = min(potential_row_quant, EIM_remaining_to_retire_2019Q2_Q4)

                # update un-accumulator for jurisdiction
                EIM_remaining_to_retire_2019Q2_Q4 += -1 * to_retire_quant

                # update retire_potential
                retire_potential.at[row, 'quant'] = potential_row_quant - to_retire_quant

                # update to_retire
                to_retire.at[row, 'quant'] = to_retire_quant
                
                logging.info(f"in {cq.date}: retired {to_retire['quant'].sum()} M of vintage {vintage_to_retire} for EIM Outstanding Emissions")
            
            # what remains in retire_potential is not retired; to be concat with other pieces below

            mapping_dict = {'acct_name': 'retirement', 
                            'inst_cat': 'EIM_retire', 
                            'date_level': cq.date}
            to_retire = multiindex_change(to_retire, mapping_dict)

            # concat to_retire with all_accts remainder
            all_accts = pd.concat([all_accts.loc[~mask_2019Q2_Q4], retire_potential, to_retire], sort=True)
            all_accts = all_accts.groupby(level=prmt.standard_MI_names).sum()
        # ~~~~~~~~~~~~~

        if prmt.run_tests == True:
            name_of_allowances = 'EIM retirement'
            test_conservation_during_transfer(all_accts, all_accts_sum_init, name_of_allowances)
            parent_fn = str(inspect.currentframe().f_code.co_name)
            test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
            test_for_duplicated_indices(all_accts, parent_fn)
            test_for_negative_values(all_accts, parent_fn)

    else:
        # year not in range(2018, 2030+1)
        # no EIM Outstanding to process
        pass

    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
                             
    return(all_accts)
# end of retire_for_EIM_outstanding


# In[ ]:


def retire_for_bankruptcy(all_accts):
    """
    Retires allowances to account for unfulfilled emissions obligations due to bankruptcy.
    
    In regulations adopted April 2019, §95911(h) has the new rules for: "Retirement of Future Vintage Allowances 
    to Cover Unresolved Emissions Obligations Resulting from Covered Entity Bankruptcy"
    
    "ARB will retire allowances from the allowance budget two years after the current allowance budget year 
    that is not already allocated to entities..."
    
    Due to this requirement, under Apr 2019, bankruptcies can only be processed through 2028, 
    but not in 2029 or beyond, because the program is not authorized beyond 2030.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    process_bankruptcy_for_present_yr = False # initialize
    
    # check if regs allow for bankruptcy retirement
    if cq.date.year in prmt.bankruptcy_hist_proj.index.tolist() and prmt.bankruptcy_hist_proj.loc[cq.date.year]>0:
        # then process bankruptcy retirements
        
        # bankruptcy retirements come from annual budget of vintage two years after "current allowance budget year 
        # that is not already allocated to entities"; in 2019, that year is 2020, and two years later is 2022;
        # value of prmt.CA_latest_year_allocated set in function transfer_CA_alloc__from_alloc_hold.

        # get alloc_hold for specified vintage of allowances
        vintage_to_retire = prmt.CA_latest_year_allocated + 1 + 2
        
        mask1 = all_accts.index.get_level_values('acct_name') == 'alloc_hold'
        mask2 = all_accts.index.get_level_values('inst_cat') == 'cap'
        mask3 = all_accts.index.get_level_values('vintage') == vintage_to_retire
        mask = (mask1) & (mask2) & (mask3)

        # to avoid error "A value is trying to be set on a copy of a slice from a DataFrame."...
        # ... use .copy() when creating slice of potential 
        # ... & use .copy() in creating to_retire from potential
        potential = all_accts.copy().loc[mask]
        remainder = all_accts.loc[~mask]

        # run only if df has length = 1
        if len(potential) == 1:

            # repeat slice of all_accts, to get df to modify for retirement
            # set value equal to quantity specified in Series prmt.bankruptcy_hist_proj
            to_retire = potential.copy()
            to_retire.at[to_retire.index, 'quant'] = prmt.bankruptcy_hist_proj.at[cq.date.year]
            mapping_dict = {'acct_name': 'retirement', 
                            'inst_cat': 'bankruptcy', 
                            'date_level': cq.date}
            to_retire = multiindex_change(to_retire, mapping_dict)

            # update alloc_hold to have quantity remaining after retirement
            potential_original = potential['quant'].sum()
            potential_new = potential_original - prmt.bankruptcy_hist_proj.at[cq.date.year]
            potential.at[potential.index, 'quant'] = potential_new

            # recombine dfs:
            all_accts = pd.concat([remainder, potential, to_retire])

        else:
            print("Error" + "! potential was not a single row; here's the df:") # for UI
            print(potential)  
    
    else:
        # no bankruptcy retirement to process in this year
        pass
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)
# end of retire_for_bankruptcy


# In[ ]:


def transfer_unsold__from_auct_hold_to_APCR(all_accts):
    """
    For CA, transfers unsold stock to APCR if they have gone unsold for more than 24 months, 
    as long as they haven't already been retired for EIM removal.
    
    Based on CA regs (QC has no roll over rule):
    CA regs Apr 2019: § 95911(g)
    
    According to the Apr 2019 regs: "ARB will transfer these allowances no later than the surrender deadlines 
    specified in sections 95856(d) and (f)"
    
    So the latest the transfer could occur would be Nov 1 of each year (within Q4, before auction).
    
    Under Oct 2017 regs, there was no requirement for this to be processed at a particular time.
    Under those regs, the only set of allowances that hit the 24-month limit were transferred 2018Q3.

    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # pre-test for conservation
    all_accts_sum_init = all_accts['quant'].sum()
    
    # cut-off date: if allowances with unsold_di of this date or earlier remain unsold, they roll over to APCR
    # this function runs after current auction in cq.date, 
    # so any remaining unsold for 2 years at the time the function runs...
    # ... will still be unsold at the start of the next quarter, at which point they'll be unsold > 2 years (24 mo.)
    cut_off_date = pd.to_datetime(cq.date.to_timestamp() - DateOffset(years=2)).to_period('Q')
    
    # get unsold CA state-owned current allowances in auct_hold, with unsold_di > 2 years (24 mo.) earlier
    mask1 = all_accts.index.get_level_values('acct_name')=='auct_hold'
    mask2 = all_accts.index.get_level_values('inst_cat')=='CA'
    mask3 = all_accts.index.get_level_values('auct_type')=='current'
    mask4 = all_accts.index.get_level_values('status')=='unsold'
    mask5 = all_accts.index.get_level_values('unsold_di') <= cut_off_date # see note below
    mask6 = all_accts['quant'] > 0
    mask = (mask1) & (mask2) & (mask3) & (mask4) & (mask5) & (mask6)
    
    # for cut_off_date, used <= (rather than ==) because under Apr 2019 regs, 
    # allowances may be retained in auct_hold for longer, beyond the quarter in which they hit the cut_off_date

    # unsold to transfer to APCR
    df = all_accts.loc[mask]
    
    mapping_dict = {'acct_name': 'APCR_acct', 
                    'auct_type': 'reserve',
                    'newness': 'n/a',
                    'date_level': cq.date}
    df = multiindex_change(df, mapping_dict)
    
    unsold_to_transfer = df.copy()
    
    # concat unsold_to_transfer with all_accts remainder
    all_accts = pd.concat([all_accts.loc[~mask], unsold_to_transfer], sort=True)
    
    if prmt.run_tests == True:
        name_of_allowances = 'unsold transfer to APCR'
        test_conservation_during_transfer(all_accts, all_accts_sum_init, name_of_allowances)
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
    
    logging.info(f"in {cq.date}: transferred {unsold_to_transfer['quant'].sum()} M unsold to APCR")
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)
# end of transfer_unsold__from_auct_hold_to_APCR


# In[ ]:


def process_auction_cur_QC_all_accts(all_accts):
    """
    Processes current auction for QC, applying the specified order of sales (when auctions don't sell out).
    
    QC regulations don't appear to specify an order of sales, so the model assumes that QC will follow CA approach:
    * Redesignated (aka reintroduced) allowances sell first
    * Then newly available allowances.
    
    (See function process_auction_cur_CA_all_accts for more information.)
    
    QC does not have consigned allowances, so there are not complicating factors due to that.
    """

    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # pre-test
    all_accts_sum_init = all_accts['quant'].sum()
    
    if prmt.run_tests == True:
        # TEST: check that all available allowances are in auct_hold
        avail_for_test = all_accts.loc[all_accts.index.get_level_values('status')=='available']
        avail_for_test_accts = avail_for_test.index.get_level_values('acct_name').unique().tolist()
        if avail_for_test.empty == False:
            if avail_for_test_accts != ['auct_hold']:
                print(f"{prmt.test_failed_msg} Some available allowances were in an account other than auct_hold. Here's available:")
                print(avail_for_test)
            else: # avail_for_test_accts == ['auct_hold']
                pass
        else: # avail_for_test.empty == True
            print("Warning" + "! In process_auction_cur_QC_all_accts, avail_for_test is empty.") # for UI
        # END OF TEST
    
    # get sales % for current auctions, for this juris, for cq.date
    # (works for auctions whether linked or unlinked, i.e., QC-only and CA-QC)
    df = prmt.auction_sales_pcts_all.copy()
    df = df.loc[(df.index.get_level_values('market').str.contains('QC')) &
                (df.index.get_level_values('auct_type')=='current')]
    df.index = df.index.droplevel(['market', 'auct_type'])
    sales_fract_cur_1j_1q = df.at[cq.date]
    
    # get current available allowances
    # (it should be that all available allowances are in auct_hold)
    mask1 = all_accts.index.get_level_values('auct_type')=='current'
    mask2 = all_accts.index.get_level_values('status')=='available'
    mask3 = all_accts.index.get_level_values('date_level')==cq.date
    mask4 = all_accts.index.get_level_values('juris')=='QC'
    mask5 = all_accts['quant'] > 0
    mask = (mask1) & (mask2) & (mask3) & (mask4) & (mask5)
    cur_avail_QC_1q = all_accts.loc[mask]
    
    not_cur_avail_QC_1q = all_accts.loc[~mask]
    
    if sales_fract_cur_1j_1q == 1.0:
        # all available allowances are sold and transferred into gen_acct
        cur_sold_QC_1q = cur_avail_QC_1q
        mapping_dict = {'status': 'sold', 
                        'acct_name': 'gen_acct'}
        cur_sold_QC_1q = multiindex_change(cur_sold_QC_1q, mapping_dict)
        
        # recombine
        all_accts = pd.concat([cur_sold_QC_1q, not_cur_avail_QC_1q])
        
        if prmt.run_tests == True:
            name_of_allowances = 'after QC sell-out'
            test_conservation_during_transfer(all_accts, all_accts_sum_init, name_of_allowances)
            parent_fn = str(inspect.currentframe().f_code.co_name)
            test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
            test_for_duplicated_indices(all_accts, parent_fn)
            test_for_negative_values(all_accts, parent_fn)
        
    else: # sales_fract_cur_1j_1q != 1.0:
        # calculate quantity of QC allowances sold (and test that variable is a float)
        cur_sold_1q_tot_QC = cur_avail_QC_1q['quant'].sum() * sales_fract_cur_1j_1q
        test_if_value_is_float_or_np_float64(cur_sold_1q_tot_QC)

        # remaining: un-accumulator for all QC sales; initialize here; will be updated repeatedly below
        cur_remaining_to_sell_1q_QC = cur_sold_1q_tot_QC.copy()

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        # sales priority: for QC, reintro are first

        # extract reintro allowances from all_accts
        mask1 = all_accts.index.get_level_values('auct_type')=='current'
        mask2 = all_accts.index.get_level_values('status')=='available'
        mask3 = all_accts.index.get_level_values('date_level')==cq.date
        mask4 = all_accts.index.get_level_values('juris')=='QC'
        mask5 = all_accts.index.get_level_values('newness')=='reintro'
        mask6 = all_accts['quant'] > 0
        mask = (mask1) & (mask2) & (mask3) & (mask4) & (mask5) & (mask6)
        reintro_avail_1q = all_accts.loc[mask]
        not_reintro_avail_1q = all_accts.loc[~mask]

        # iterate through all rows for available allowances; remove those sold
        
        # start by creating df from avail, with values zeroed out
        # sort_index to ensure that earliest vintages are drawn from first
        reintro_avail_1q = reintro_avail_1q.sort_index()
        
        reintro_sold_1q = reintro_avail_1q.copy()
        reintro_sold_1q['quant'] = float(0)
        
        for row in reintro_avail_1q.index:
            in_stock_row = reintro_avail_1q.at[row, 'quant']

            sold_from_row_quantity = min(in_stock_row, cur_remaining_to_sell_1q_QC)

            if sold_from_row_quantity > 1e-7:
                # update un-accumulator for jurisdiction
                cur_remaining_to_sell_1q_QC = cur_remaining_to_sell_1q_QC - sold_from_row_quantity

                # update sold quantity & metadata
                reintro_sold_1q.at[row, 'quant'] = sold_from_row_quantity

                # update reintro_avail_1q quantity (but not metadata)
                reintro_avail_1q.at[row, 'quant'] = in_stock_row - sold_from_row_quantity

            else: # sold_from_row_quantity <= 1e-7:
                pass


        # for those sold, update status from 'available' to 'sold' & update acct_name from 'auct_hold' to 'gen_acct'
        mapping_dict = {'status': 'sold', 
                        'acct_name': 'gen_acct'}
        reintro_sold_1q = multiindex_change(reintro_sold_1q, mapping_dict)

        # for unsold, metadata is updated for all allowance types at once, at end of this function
        # unsold is what's left in avail df
        reintro_unsold_1q = reintro_avail_1q

        # recombine
        all_accts = pd.concat([reintro_sold_1q,
                               reintro_unsold_1q,
                               not_reintro_avail_1q], sort=False)
        
        # clean-up
        all_accts = all_accts.loc[(all_accts['quant']>1e-7) | (all_accts['quant']<-1e-7)]

        if prmt.run_tests == True:
            name_of_allowances = 'after reintro sold'
            test_conservation_during_transfer(all_accts, all_accts_sum_init, name_of_allowances)
            parent_fn = str(inspect.currentframe().f_code.co_name)
            test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
            test_for_duplicated_indices(all_accts, parent_fn)
            test_for_negative_values(all_accts, parent_fn)

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        # sales priority: state-owned allowances available for first time as current 
        # (including fka adv, if there are any)

        # extract state allowances new to current auctions (from all_accts)
        mask1 = all_accts.index.get_level_values('auct_type')=='current'
        mask2 = all_accts.index.get_level_values('status')=='available'
        mask3 = all_accts.index.get_level_values('date_level')==cq.date
        mask4 = all_accts.index.get_level_values('juris')=='QC'
        mask5 = all_accts.index.get_level_values('newness')=='new'
        mask6 = all_accts['quant'] > 0
        mask = (mask1) & (mask2) & (mask3) & (mask4) & (mask5) & (mask6)
        new_avail_1q = all_accts.loc[mask]
        not_new_avail_1q = all_accts.loc[~mask]

        # iterate through all rows for available allowances; remove those sold
        
        # start by creating df from avail, with values zeroed out
        # sort_index to ensure that earliest vintages are drawn from first
        new_avail_1q = new_avail_1q.sort_index()
        
        new_sold_1q = new_avail_1q.copy()
        new_sold_1q['quant'] = float(0)
        
        for row in new_avail_1q.index:
            in_stock_row = new_avail_1q.at[row, 'quant']

            sold_from_row_quantity = min(in_stock_row, cur_remaining_to_sell_1q_QC)

            if sold_from_row_quantity > 1e-7:
                # update un-accumulator for jurisdiction
                cur_remaining_to_sell_1q_QC = cur_remaining_to_sell_1q_QC - sold_from_row_quantity

                # update sold quantity & metadata
                new_sold_1q.at[row, 'quant'] = sold_from_row_quantity

                # update new_avail_1q quantity (but not metadata)
                new_avail_1q.at[row, 'quant'] = in_stock_row - sold_from_row_quantity

            else: # sold_from_row_quantity <= 1e-7:
                pass

        # using all_accts:
        # for those sold, update status from 'available' to 'sold' & update acct_name from 'auct_hold' to 'gen_acct'
        mapping_dict = {'status': 'sold', 
                        'acct_name': 'gen_acct'}
        new_sold_1q = multiindex_change(new_sold_1q, mapping_dict)
        
        # for unsold, metadata is updated for all allowance types at once, at end of this function
        # unsold is what's left in avail df
        new_unsold_1q = new_avail_1q

        # recombine & groupby sum
        all_accts = pd.concat([new_sold_1q,
                               new_unsold_1q,
                               not_new_avail_1q], 
                              sort=False)
        # all_accts = all_accts.groupby(prmt.standard_MI_names).sum()
        
        # clean-up
        all_accts = all_accts.loc[(all_accts['quant']>1e-7) | (all_accts['quant']<-1e-7)]

        if prmt.run_tests == True:
            name_of_allowances = 'after newly available sold'
            test_conservation_during_transfer(all_accts, all_accts_sum_init, name_of_allowances)
            parent_fn = str(inspect.currentframe().f_code.co_name)
            test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
            test_for_duplicated_indices(all_accts, parent_fn)
            test_for_negative_values(all_accts, parent_fn)
        
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        # update status for all unsold
        all_accts = unsold_update_status(all_accts, 'current')

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        if prmt.run_tests == True:
            name_of_allowances = 'after update sold'
            test_conservation_during_transfer(all_accts, all_accts_sum_init, name_of_allowances)
            parent_fn = str(inspect.currentframe().f_code.co_name)
            test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
            test_for_duplicated_indices(all_accts, parent_fn)
            test_for_negative_values(all_accts, parent_fn)

            # filter out rows with zero or fractional allowances (or NaN)
            all_accts = all_accts.loc[(all_accts['quant']>1e-7) | (all_accts['quant']<-1e-7)].dropna()
            all_accts = all_accts.dropna()

    # end of if-else statement that began "if sales_fract_cur_1j_1q == 1.0)

    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)

    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")

    return(all_accts)
# end of process_auction_cur_QC_all_accts


# ## Functions: Master function for CA & QC, and sub-functions
# * process_allowance_supply_CA_QC
# * get_auction_sales_pcts_all
# * get_auction_sales_pcts_historical
# * get_auction_sales_pcts_projection_from_user_settings
# * calculate_sell_out_counters
# * initialize_all_accts
# * process_CA
# * process_QC

# In[ ]:


def process_allowance_supply_CA_QC():
    """
    Overall function to run all initialization steps, then auctions etc. for CA & QC.
    
    Default is to revert to pre-run scenario in which all auctions after 2018Q3 sell out.
    
    Only run auctions if there are auctions that do not sell out.
    
    Key step is to run sub-functions process_CA & process_QC.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")

    if prmt.saved_auction_run_default == False:        
        print("Processing quarterly data:", end=' ') # for UI
        
        # get input: historical + projected quarterly auction data
        # sets object attribute prmt.auction_sales_pcts_all
        get_auction_sales_pcts_all()

        # calculate sell out counters (for CA & QC) based on prmt.auction_sales_pcts_all (from get_auction_sales_pcts_all)
        # sets prmt.CA_cur_sell_out_counter & prmt.QC_cur_sell_out_counter
        calculate_sell_out_counters()

        # initialize all_accts for both CA & QC
        all_accts_CA, all_accts_QC = initialize_all_accts()

        # create progress bars using updated start dates and quarters
        progress_bars_initialize_and_display()
        
        # process quarters for CA & QC
        all_accts_CA = process_CA(all_accts_CA)
        all_accts_QC = process_QC(all_accts_QC)

    elif prmt.saved_auction_run_default == True and auction_tabs.selected_index == 0:        
        # there is a saved run default, and the choice for a new run is default auction behavior        
        # use values for default run, as set by earlier run (when prmt.saved_auction_run_default == False)
        # snaps_end:
        scenario_CA.snaps_end = prmt.CA_snaps_end_default_run_end
        scenario_QC.snaps_end = prmt.QC_snaps_end_default_run_end
        
        # snaps_CIR:
        scenario_CA.snaps_CIR = prmt.CA_snaps_end_default_run_CIR
        scenario_QC.snaps_CIR = prmt.QC_snaps_end_default_run_CIR
        
        # clear all_accts_CA & all_accts_QC, to avoid them accidentally being used
        # instead used saved runs in scenario object attributes above
        all_accts_CA = prmt.standard_MI_empty.copy()
        all_accts_QC = prmt.standard_MI_empty.copy()

    else:
        # auction_tabs.selected_index is not 0, 
        # or there's a problem with prmt.saved_auction_run_default (neither True nor False)
        # either way, need to run auctions
        print("Processing quarterly data:", end=' ') # for UI
        
        # get input: historical + projected quarterly auction data
        # sets object attribute prmt.auction_sales_pcts_all
        get_auction_sales_pcts_all()

        # calculate sell out counters (for CA & QC) based on prmt.auction_sales_pcts_all (from get_auction_sales_pcts_all)
        # sets prmt.CA_cur_sell_out_counter & prmt.QC_cur_sell_out_counter
        calculate_sell_out_counters()

        # initialize all_accts for both CA & QC
        all_accts_CA, all_accts_QC = initialize_all_accts()

        # create progress bars using updated start dates and quarters
        progress_bars_initialize_and_display()
        
        # process quarters for CA & QC
        all_accts_CA = process_CA(all_accts_CA)    
        all_accts_QC = process_QC(all_accts_QC)
        
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")   

    return(all_accts_CA, all_accts_QC)
# end of process_allowance_supply_CA_QC


# In[ ]:


def get_auction_sales_pcts_all():
    """
    Combines sales percentages from historical sales data with those from projected sales data.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # call functions to get historical and projection data
    auction_sales_pcts_historical = get_auction_sales_pcts_historical()
    auction_sales_pcts_projection = get_auction_sales_pcts_projection_from_user_settings()
    
    # get date of last quarter of historical data, for eliminating overlap
    auction_sales_last_historical_q = auction_sales_pcts_historical.index.get_level_values('date_level').max()

    # remove overlapping quarters from auction_sales_pcts_projection
    df = auction_sales_pcts_projection.copy()
    df = df.loc[df.index.get_level_values('date_level') > auction_sales_last_historical_q]
    
    # append remaining projection to historical
    df = auction_sales_pcts_historical.append(df)
    df = df.astype(float)
    
    prmt.auction_sales_pcts_all = df
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")

    # no return; func sets object attribute
# end of get_auction_sales_pcts_all


# In[ ]:


def get_auction_sales_pcts_historical():
    """
    For auction data, calculates the percentage that sold in each auction.
    
    When there were separate markets (e.g., when California and Quebec held separate auctions prior to Nov 2013),
    the function calculates separate sales percentages for each market.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # create record of auction sales percentages (from qauct_hist)
    df = prmt.qauct_hist.copy()
    df = df[~df['inst_cat'].isin(['IOU', 'POU'])]
    df = df.groupby(['market', 'auct_type', 'date_level'])[['Available', 'Sold']].sum()
    df['sold_pct'] = df['Sold'] / df['Available']

    auction_sales_pcts_historical = df['sold_pct']
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(auction_sales_pcts_historical)
# end of get_auction_sales_pcts_historical


# In[ ]:


def get_auction_sales_pcts_projection_from_user_settings():
    """
    Read values for auction sales percentages in projection, as specified by user interface.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")

    proj = []
    market = 'CA-QC'

    # fill in projection using user settings for prmt.years_not_sold_out & prmt.fract_not_sold
    for year in range(2018, 2030+1):
        for quarter in [1, 2, 3, 4]:
            date_level = quarter_period(f"{year}Q{quarter}")

            # add current auction projections
            # any quarters that overlap with historical data will be discarded when hist & proj are combined
            auct_type = 'current' 
            if year in prmt.years_not_sold_out:
                proj += [(market, auct_type, date_level, (1 - prmt.fract_not_sold))]
            else:
                # set to prmt.fract_not_sold to 0% (sold is 100%) for all years not in prmt.years_not_sold_out
                proj += [(market, auct_type, date_level, 1.0)]

            # add advance auction projections; assume all auctions sell 100%
            # any quarters that overlap with historical data will be discarded when hist & proj are combined
            auct_type = 'advance'
            if year in prmt.years_not_sold_out:
                proj += [(market, auct_type, date_level, (1 - prmt.fract_not_sold))]
            else:
                # set to prmt.fract_not_sold to 0% (sold is 100%) for all years not in prmt.years_not_sold_out
                proj += [(market, auct_type, date_level, 1.0)]

    proj_df = pd.DataFrame(proj, columns=['market', 'auct_type', 'date_level', 'value'])
    ser = proj_df.set_index(['market', 'auct_type', 'date_level'])['value']
    ser = ser.sort_index()
    auction_sales_pcts_projection = ser
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")

    return(auction_sales_pcts_projection)
# end of get_auction_sales_pcts_projection_from_user_settings


# In[ ]:


def calculate_sell_out_counters():
    """
    Using historical auction record, calculate the number of consecutive auctions that sold out.
    
    (Only when sell_out_counter >= 2 can state-owned allowances previously unsold at current auction be reintroduced.)
    
    Sell out counter for a given quarter is how many consecutive auctions sold out BEFORE that quarter.
    
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    df = prmt.auction_sales_pcts_all.copy()
    
    for juris in ['CA', 'QC']:

        mask1 = df.index.get_level_values('market').str.contains(juris)
        mask2 = df.index.get_level_values('auct_type')=='current'
        mask = (mask1) & (mask2)
        juris_cur = df.loc[mask]
        juris_cur.index = juris_cur.index.get_level_values('date_level')
        juris_cur = juris_cur.sort_index()

        juris_cur_sell_out_counter = pd.Series() # initialize
            
        # set sell_out_counter to zero for first quarter
        juris_cur_sell_out_counter.loc[juris_cur.index[0]] = 0
        
        previous_row = juris_cur_sell_out_counter.index[0] # initialize
        
        for row in juris_cur.index[1:]:
            # did the previous quarter sell out?
            # if so, get value of sell_out_counter from previous quarter, add 1
            # if not, reset sell_out_counter to 0
            
            if juris_cur.loc[previous_row] == 1:
                # then add 1 to the sell_out_counter from the previous row
                juris_cur_sell_out_counter.loc[row] = juris_cur_sell_out_counter.loc[previous_row] + 1
            elif juris_cur.loc[previous_row] < 1:
                # auction didn't sell out; set sell out counter to 0
                juris_cur_sell_out_counter.loc[row] = 0
            else:
                print("Error" + "! Unknown edge case for calculating sell_out_counter for juris_cur_sell_out_counter.")

            # set value of previous_row to use for next iteration
            previous_row = row
        
        if juris == 'CA':
            prmt.CA_cur_sell_out_counter = juris_cur_sell_out_counter
        elif juris == 'QC':
            prmt.QC_cur_sell_out_counter = juris_cur_sell_out_counter
        else:
            pass

    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    # no return
# end of calculate_sell_out_counters


# In[ ]:


def process_CA(all_accts_CA):
    """
    Master function for CA, which initializes run and does all idiosyncratic transfers.
    
    Regular steps are within the sub-function process_CA_quarterly.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # set cq for CA
    # in initialize_all_accts, if online user settings, then sets new value for CA_start_date 
    # (using first_proj_yr_not_sold_out)
    cq.date = prmt.CA_start_date

    for quarter_year in prmt.CA_quarters:
        logging.info(f"******** start of {quarter_year} ********")

        # ONE-OFF STEPS:
        # PREP FOR process_CA_quarterly
        if cq.date == quarter_period('2012Q4'):
            all_accts_CA = initialize_CA_auctions(all_accts_CA)

        # decadal creation of allowances & transfers
        elif cq.date == quarter_period('2018Q1'):
            # occurs before process_CA_quarterly for 2018Q1, and therefore included in 2018Q1 snap
            # by including it here before any other steps in 2018, then can have consistent budget for 2018
            # occurring at start of 2018Q1, will affect 2017Q4 CIR

            # create CA allowances v2021-v2030, put into alloc_hold
            all_accts_CA = create_annual_budgets_in_alloc_hold(all_accts_CA, prmt.CA_cap.loc[2021:2030])

            # transfer advance into auct_hold
            all_accts_CA = transfer__from_alloc_hold_to_specified_acct(all_accts_CA, prmt.CA_advance_MI, 2021, 2030)
            
            # under Oct 2017 regulations, 
            # transfer 52.4 M CA APCR allowances out of alloc_hold, into government holding (for vintages 2021-2030)
            all_accts_CA = transfer__from_alloc_hold_to_specified_acct(
                all_accts_CA, prmt.CA_APCR_2021_2030_Oct2017_MI, 2021, 2030)
        
        # net flow from Ontario entering all_accts_CA
        elif cq.date == quarter_period('2018Q2'):
            all_accts_CA = net_flow_from_Ontario_add_to_all_accts(all_accts_CA, 'CA')
            
        # assume that transfer of APCR 2021-2030 will occur in 2021Q1 (this is the latest it could occur)
        # these allowances can't be sold until 2021Q1 at the earliest
        elif cq.date == quarter_period('2021Q1'):
            
            # transfer CA APCR allowances out of alloc_hold, into APCR_acct (for vintages 2021-2030)
            # this is the 52.4 M already converted into APCR allowances, but retained in alloc_hold
            # to replicate what occurred historically
            mask1 = all_accts_CA.index.get_level_values('acct_name')=='alloc_hold'
            mask2 = all_accts_CA.index.get_level_values('inst_cat')=='APCR'
            mask = (mask1) & (mask2)
            df = all_accts_CA.loc[mask]

            mapping_dict = {'acct_name': 'APCR_acct', 
                            'auct_type': 'reserve'}
            df = multiindex_change(df, mapping_dict)
            
            # recombine
            all_accts_CA = pd.concat([df, all_accts_CA.loc[~mask]], sort=False)
            
            # end of transfer of 52.4 M APCR from Oct 2017 regs
            
            # note that under regs adopted April 2019, there is an additional ~22.7 M of vintaged allowances 
            # that will be transferred from alloc_hold to APCR account, and converted to non-vintage allowances
            # ~~~~~~~~~~~~~~~~~~~~

            all_accts_CA = transfer__from_alloc_hold_to_specified_acct(
                all_accts_CA, prmt.CA_APCR_2021_2030_Apr2019_add_MI, 2021, 2030)
        
        else: # cq.date != quarter_period('2021Q1')
            pass

        # ***** PROCESS QUARTER FOR cq.date (START) *****
        # process_CA_quarterly includes take_snapshot_CIR
        
        all_accts_CA = process_CA_quarterly(all_accts_CA)
        
        # ***** PROCESS QUARTER FOR cq.date (END) *****
        
        # update progress bar
        if progress_bar_CA.wid.value <= len(prmt.CA_quarters):
            progress_bar_CA.wid.value += 1
                    
        logging.info(f"******** end of {cq.date} ********")
        logging.info("------------------------------------")
                
        # at end of each quarter, step cq.date to next quarter
        cq.step_to_next_quarter()
        
    # end of loop "for quarter_year in prmt.CA_quarters:"
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts_CA)
# end of process_CA


# In[ ]:


def process_QC(all_accts_QC):
    """
    Master function for QC, which initializes run and does all idiosyncratic transfers.
    
    Regular steps are within the sub-function process_QC_quarterly.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # initialize cq.date to QC_start_date
    # in initialize_all_accts, if online user settings, then sets new value for QC_start_date 
    # (using first_proj_yr_not_sold_out)
    cq.date = prmt.QC_start_date
    
    for quarter_year in prmt.QC_quarters:
        logging.info(f"******** start of {cq.date} ********")

        # one-off steps before main quarterly steps (and before CIR snapshot) **************************
        if cq.date == quarter_period('2013Q4'):
            # initialize QC auctions
            all_accts_QC = initialize_QC_auctions_2013Q4(all_accts_QC)
            
        elif cq.date == quarter_period('2018Q1'):
            # occurs before process_QC_quarterly for 2018Q1, and therefore included in 2018Q1 snap
            # by including it here before any other steps in 2018, then can have consistent budget for 2018
            
            # decadal creation of allowances & transfers
            # create QC allowances v2021-v2030, put into alloc_hold
            all_accts_QC = create_annual_budgets_in_alloc_hold(all_accts_QC, prmt.QC_cap.loc[2021:2030])

            # transfer QC APCR allowances out of alloc_hold, into APCR_acct (for vintages 2021-2030)
            # (QC APCR allowances still in alloc_hold, as of 2018Q2 CIR)
            all_accts_QC = transfer__from_alloc_hold_to_specified_acct(all_accts_QC, prmt.QC_APCR_MI, 2021, 2030)
            
            # transfer advance into auct_hold
            all_accts_QC = transfer__from_alloc_hold_to_specified_acct(all_accts_QC, prmt.QC_advance_MI, 2021, 2030)
        
        # net flow from Ontario entering all_accts_QC
        elif cq.date == quarter_period('2018Q2'):
            all_accts_QC = net_flow_from_Ontario_add_to_all_accts(all_accts_QC, 'QC')
        
        # end of one-off steps before main quarterly steps **************************
        

        # ***** PROCESS QUARTER FOR cq.date *****
        # process_QC_quarterly includes take_snapshot_CIR
        all_accts_QC = process_QC_quarterly(all_accts_QC)
        
        # ***** END OF PROCESS QUARTER FOR cq.date *****
  

        # one-off steps after main quarterly steps (and before CIR snapshot) **************************
    
        if cq.date == quarter_period('2014Q1'):
            # Early Action allowances distributed 2014Q1
            all_accts_QC = QC_early_action_distribution(all_accts_QC)
            
        # end of one-off steps after main quarterly steps **************************

        
        # update progress bar
        if progress_bar_QC.wid.value <= len(prmt.QC_quarters):
            progress_bar_QC.wid.value += 1
        
        # at end of each quarter, move cq.date to next quarter
        cq.step_to_next_quarter()
            
        logging.info(f"******** end of {cq.date} ********")
        logging.info("------------------------------------")
        
    # end of loops "for quarter_year in prmt.QC_quarters:"
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(scenario_QC, all_accts_QC)
# end of process QC quarters


# In[ ]:


def initialize_all_accts():
    """
    Create version of df all_accts for start of model run, for each juris (CA & QC).
    
    What is in this df at start of run depends on the time point at which the model run begins.
    
    Default is to use historical data + projection of all auctions selling out. 
    
    Model may run as forecast, in which case it defaults to pre-run results for all auctions selling out.
    
    Or model may run as hindcast + forecast, in which case it repeats historical steps.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # for initial conditions of market, set attributes of objects scenario_CA and scenario_QC
    # note that scenario attribute snaps_end is a *list* of dfs

    # clear out values, even when using saved default run;
    # these will be reset in process_allowance_supply_CA_QC

    scenario_CA.avail_accum = prmt.standard_MI_empty.copy()
    scenario_CA.snaps_CIR = []
    scenario_CA.snaps_end = []
    logging.info("initialized scenario_CA attributes for hindcast")

    scenario_QC.avail_accum = prmt.standard_MI_empty.copy()
    scenario_QC.snaps_CIR = []
    scenario_QC.snaps_end = []
    logging.info("initialized scenario_QC attributes for hindcast")

    # initialize all_accts_CA & all_accts_QC
    all_accts_CA = prmt.standard_MI_empty.copy()
    all_accts_QC = prmt.standard_MI_empty.copy()
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts_CA, all_accts_QC)
# end of initialize_all_accts


# ## Functions: Supply-demand calculations
# * supply_demand_calculations
#   * emissions_projection
#   * obligations_fulfilled_historical_calculation
#   * create_snaps_CAQC_toward_bank
#   * create_allow_vint_ann
#   * create_allow_nonvint_ann
#   * offsets_projection
#   * private_bank_annual_metric_model_method [code in following section]
#   * private_bank_annual_metric_paper_method [code in following section]
#   * calculate_reserve_account_metric_and_related [code in following section]
#   * calculate_government_holding_metric [code in following section]
#   * excess_offsets_calc

# In[ ]:


def supply_demand_calculations():
    """
    For emissions and offsets, get values by calling functions within this func.
    
    For auctions, use object attributes scenario_CA.snaps_end & scenario_QC.snaps_end, as calculated in model run.
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # ~~~~~~~~~~~~~~~~~~
    # EMISSIONS
    # sets attributes prmt.emissions_ann, prmt.emissions_ann_CA, prmt.emissions_ann_QC
    emissions_projection()
    
    obligations_fulfilled_historical_calculation()
    # sets value of prmt.CA_QC_obligations_fulfilled_hist
    
    # combine historical values in prmt.CA_QC_obligations_fulfilled_hist,
    # with projections from emissions_projection()
    emissions_ann_proj = prmt.emissions_ann.loc[prmt.CA_QC_obligations_fulfilled_hist.index.max()+1:]
    
    prmt.CA_QC_obligations_fulfilled_hist_proj = prmt.CA_QC_obligations_fulfilled_hist.append(emissions_ann_proj)
    # to calculate private bank below, prmt.CA_QC_obligations_fulfilled_hist_proj is subtracted from private holdings
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # GATHER ALL SUPPLY DATA
    snaps_end_Q4_CA_QC, snaps_CAQC_toward_bank = create_snaps_CAQC_toward_bank(scenario_CA, scenario_QC)
    
    # VINTAGED ALLOWANCES
    create_allow_vint_ann(snaps_CAQC_toward_bank) # sets prmt.allow_vint_ann
    
    # NON-VINTAGED ALLOWANCES
    create_allow_nonvint_ann(snaps_CAQC_toward_bank) # sets prmt.allow_nonvint_ann
    
    # OFFSET SUPPLY
    offsets_projection() # sets prmt.offsets_supply_q & prmt.offsets_supply_ann
    
    supply_ann_df = pd.concat([
        prmt.allow_vint_ann,
        prmt.allow_nonvint_ann, # does not include projected reserve & PCU sales
        prmt.offsets_supply_ann], 
        axis=1)
    
    # sum (which converts DataFrame to Series)
    supply_ann = supply_ann_df.sum(axis=1)
    supply_ann.name = 'supply_ann'
    prmt.supply_ann = supply_ann
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # PRIVATE BANK METRIC:
    # calculation of method developed for model   
    private_bank_annual_metric_model_method(supply_ann_df)
    # sets prmt.bank_cumul & prmt.reserve_PCU_sales_cumul

    # PRIVATE BANK METRIC modification:
    # for years with full historical data on the supply side,
    # use method from banking paper (Cullenward et al., 2019)
    private_bank_paper = private_bank_annual_metric_paper_method()
    
    # for private bank metric, use values calculated here for years up to prmt.supply_last_hist_yr   
    for year in private_bank_paper.index:
        # overwrite values in bank_cumul_pos with values from method used in banking paper (Cullenward et al., 2019)
        prmt.bank_cumul.at[year] = private_bank_paper.at[year]
      
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # RESERVE ACCOUNT METRIC:
    calculate_reserve_account_metric_and_related(snaps_end_Q4_CA_QC)
    # sets prmt.reserve_accts & prmt.reserve_sales_excl_PCU
        
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # UNSOLD METRIC: allowances unsold at current auction and retained in government holding accounts
    df = snaps_end_Q4_CA_QC.copy()
    
    mask1 = df.index.get_level_values('acct_name') == 'auct_hold'
    mask2 = df.index.get_level_values('auct_type') == 'current' # to exclude advance
    mask3 = df.index.get_level_values('status') == 'unsold'
    mask = (mask1) & (mask2) & (mask3)
    df = df.loc[mask]
    prmt.unsold_auct_hold_cur_sum = df.groupby('snap_yr')['quant'].sum()
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # GOVERNMENT HOLDING METRIC:
    calculate_government_holding_metric(snaps_end_Q4_CA_QC)
    # sets prmt.gov_holding & prmt.gov_plus_private
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
    # calculation of excess offsets beyond what could be used
    # (depends on temporal pattern of when offsets are added to supply)
    excess_offsets_calc() # sets prmt.excess_offsets
    
    # ~~~~~~~~~~~~
    
    # run create_export_df within supply_demand_calculations, 
    # so that the values of sliders etc are those used in the model run (and not what might be adjusted after run)
    create_export_df()
    # modifies attributes prmt.export_df & prmt.js_download_of_csv
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    # no return
# end of supply_demand_calculations


# In[ ]:


def emissions_projection():
    """
    Calculate projection for covered emissions based on user settings.
    
    Default is -2%/year change for both CA and QC.
    
    Default based on PATHWAYS projection in Scoping Plan case that "covered sector" emissions change would be ~ -2%/yr.
    
    That PATHWAYS projection only includes effects of direct policies, and not C&T.
    
    But it may serve as a useful proxy for the emissions trajectory with an oversupplied C&T program.
    
    Although PATHWAYS "covered sector" emissions is ~10% higher than covered emissions, 
    we assume the annual change is a reasonable representation of expectations for covered emissions.
    
    Projections for QC emissions have the same annual percentage changes as CA emissions.
    
    Note that the default projection in this model may differ from that in the Near Zero banking note (2019),
    leading to differences in the calculation of the private bank.
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    progress_bar_loading.wid.value += 1

    # use prmt.emissions_and_obligations, set by read_emissions_historical_data
    # convert each into Series
    CA_em_hist = prmt.emissions_and_obligations['CA covered emissions'].dropna()
    QC_em_hist = prmt.emissions_and_obligations['QC covered emissions'].dropna()

    # create new Series, which will have projections appended
    CA_em_all = CA_em_hist.copy()
    QC_em_all = QC_em_hist.copy()
    
    CA_em_hist_last_yr = CA_em_hist.index.max()
    QC_em_hist_last_yr = QC_em_hist.index.max()
    
    # ~~~~~~~~~~
    
    # then calculate emissions based on the slider values
    if emissions_tabs.selected_index == 0:
        # simple settings
        logging.info("using emissions settings (simple)")
        # get user specified emissions annual change
        # calculate emissions trajectories to 2030
        for year in range(CA_em_hist_last_yr+1, 2030+1):
            CA_em_all.at[year] = CA_em_all.at[year-1] * (1 + em_pct_CA_simp.slider.value)
            QC_em_all.at[year] = QC_em_all.at[year-1] * (1 + em_pct_QC_simp.slider.value)
        
    elif emissions_tabs.selected_index == 1:
        # advanced settings
        logging.info("using emissions settings (advanced)")
        
        if CA_em_hist_last_yr <= 2020:
            for year in range(CA_em_hist_last_yr+1, 2020+1):
                CA_em_all.at[year] = CA_em_all.at[year-1] * (1 + em_pct_CA_adv1.slider.value)
                QC_em_all.at[year] = QC_em_all.at[year-1] * (1 + em_pct_QC_adv1.slider.value)
        else:
            # don't create this slider
            pass
        
        if CA_em_hist_last_yr <= 2025:
            for year in range(max(2021, CA_em_hist_last_yr+1), 2025+1):
                CA_em_all.at[year] = CA_em_all.at[year-1] * (1 + em_pct_CA_adv2.slider.value)
                QC_em_all.at[year] = QC_em_all.at[year-1] * (1 + em_pct_QC_adv2.slider.value)
        else:
            # don't create this slider
            pass

        if CA_em_hist_last_yr <= 2030:
            for year in range(max(2026, CA_em_hist_last_yr+1), 2030+1):
                CA_em_all.at[year] = CA_em_all.at[year-1] * (1 + em_pct_CA_adv3.slider.value)
                QC_em_all.at[year] = QC_em_all.at[year-1] * (1 + em_pct_QC_adv3.slider.value)
        else:
            # don't create this slider
            pass
        
    elif emissions_tabs.selected_index == 2:        
        # custom scenario input through text box
        custom = parse_emissions_text(em_text_input_CAQC_obj.wid.value)
        
        if isinstance(custom, str):
            if custom == 'blank' or custom == 'missing_slash_t' or custom == 'misformatted':
                # revert to default; relevant error_msg set in parse_emissions_text

                # calculate default
                for year in range(CA_em_hist_last_yr+1, 2030+1):
                    CA_em_all.at[year] = CA_em_all.at[year-1] * (1 + -0.02)
                    QC_em_all.at[year] = QC_em_all.at[year-1] * (1 + -0.02)
            else:
                error_msg = "Error" + "! Unknown problem with input (possibly formatting issue). Reverting to default of -2%/year."
                logging.info(error_msg)
                prmt.error_msg_post_refresh += [error_msg]  

        elif isinstance(custom, pd.Series):
            if custom.index.min() > CA_em_hist_last_yr+1 or custom.index.max() < 2030:
                # then projection is missing years

                error_msg = "Error" + f"! Projection needs to cover each year from {CA_em_hist_last_yr+1} to 2030. Reverting to default of -2%/year."
                logging.info(error_msg)
                prmt.error_msg_post_refresh += [error_msg]

                # calculate default
                for year in range(CA_em_hist_last_yr+1, 2030+1):
                    CA_em_all.at[year] = CA_em_all.at[year-1] * (1 + -0.02)
                    QC_em_all.at[year] = QC_em_all.at[year-1] * (1 + -0.02)

            elif custom.index.min() <= CA_em_hist_last_yr+1 and custom.index.max() >= 2030:
                # projection has all needed years

                # keep only years from 2017 to 2030
                custom = custom.loc[(custom.index >= CA_em_hist_last_yr+1) & (custom.index <= 2030)]

                # *** ASSUMPTION ***
                # assume that CA emissions are a proportional share of the projected CA+QC emissions
                # proportion is based on CA portion of CA+QC caps (~84.8%) over projection period 2015-2030
                # (because that starts from when broad caps began to be used, in 2015)
                CA_caps_2015_2030 = prmt.CA_cap.loc[2015:2030].sum()
                CAQC_caps_2015_2030 = pd.concat([prmt.CA_cap.loc[2015:2030], prmt.QC_cap.loc[2015:2030]]).sum()
                CA_proportion = CA_caps_2015_2030 / CAQC_caps_2015_2030

                CA_em_all = CA_proportion * custom
                QC_em_all = (1 - CA_proportion) * custom

                # fill in historical data; don't let user override historical data
                CA_em_all = pd.concat([CA_em_hist.loc[2013:CA_em_hist_last_yr], CA_em_all], axis=0)
                QC_em_all = pd.concat([QC_em_hist.loc[2013:QC_em_hist_last_yr], QC_em_all], axis=0)

        else:
            error_msg = "Error" + "! Unknown problem with input (possibly formatting issue). Reverting to default of -2%/year."
            logging.info(error_msg)
            prmt.error_msg_post_refresh += [error_msg]

        # end of "if custom == 'blank'..."
        
    else: 
        # emissions_tabs.selected_index is not 0, 1, or 2
        error_msg = "Error" + "! Tab index is out of permitted range. Reverting to default of -2%/year."
        logging.info(error_msg)
        prmt.error_msg_post_refresh += [error_msg]
        
        # calculate default
        for year in range(CA_em_hist_last_yr+1, 2030+1):
            CA_em_all.at[year] = CA_em_all.at[year-1] * (1 + -0.02)
            QC_em_all.at[year] = QC_em_all.at[year-1] * (1 + -0.02)

    # end of "if emissions_tabs.selected_index == 0:"
            
    # set attributes (need jurisdiction emissions for offset calculations)
    prmt.emissions_ann_CA = CA_em_all
    prmt.emissions_ann_QC = QC_em_all
    prmt.emissions_ann = pd.concat([CA_em_all, QC_em_all], axis=1).sum(axis=1)
    
    # set names for all series
    prmt.emissions_ann.name = 'emissions_ann'
    prmt.emissions_ann_CA.name = 'emissions_ann_CA'
    prmt.emissions_ann_QC.name = 'emissions_ann_QC'
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    # no returns; sets attributes
# end of emissions_projection


# In[ ]:


def obligations_fulfilled_historical_calculation():
    """
    For historical data, calculates the compliance obligations that were satified by instruments surrendered.
    
    As of 2019Q1, the only major unfulfilled obligation was in 2018, for Compliance Period 2 (2015-2017).
    This was the La Paloma bankruptcy, which CARB notes in the compliance report for 2015-2017:
    
    "La Paloma Generating Company, LLC (CA1017) surrendered compliance instruments for emissions initially 
    assigned to it before a change of ownership occurred, and a bankruptcy court identified the new purchaser 
    (CXA La Paloma (CA2683)) as a separate legal entity responsible for emissions only from the effective sale 
    date forward.  Since the new entity had not crossed the emissions threshold, per the court decision, its 
    emissions generated no compliance obligation for the compliance period.  The total compliance obligation 
    value does not include the amount of emissions generated by the new facility owner following the sale date. 
    CARB will surrender 3,767,027 compliance instruments using the mechanism described for unfulfilled compliance 
    obligations due to bankruptcy proceedings under newly adopted section 95911(h) which is expected to go into 
    effect on April 1, 2019."
    
    The model uses this data to calculate retirements from private holdings, and thus the remaining private bank.
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # get compliance obligations from input sheet 'emissions & obligations'
    # index is for years obligations incurred
    
    # for CA, obligations have been different from emissions
    CA_oblig = prmt.emissions_and_obligations['CA obligations']

    # calculate compliance obligations due
    # for CA, there are annual compliance obligations of 30% of the prior year's emissions
    compl_period_close_years = [2015, 2018, 2021, 2024, 2027, 2030]   

    # use list comprehension: new_list = [expression(i) for i in old_list if filter(i)]
    ann_compl_years = [year for year in list(range(2014, 2030+1)) if year not in compl_period_close_years]

    # for CA, no compliance obligation due in 2013; for subsequent years, calculate due based on obligations incurred
    CA_due = pd.Series()
    for due_year in range(2014, 2030+1):
        if due_year in ann_compl_years:
            CA_due.at[due_year] = CA_oblig[due_year-1]*0.3
        elif due_year == 2015:
            # special case for Compliance Period 1, which was only two years (2013-2014)
            CA_due.at[due_year] = CA_oblig[due_year-2]*0.7 + CA_oblig[due_year-1]
        else:
            # other years in which remaining obligations for the compliance period are due
            CA_due.at[due_year] = CA_oblig[due_year-3]*0.7 + CA_oblig[due_year-2]*0.7 + CA_oblig[due_year-1]

    CA_surrendered_hist = prmt.CA_surrendered.loc[prmt.CA_surrendered > 0].dropna()

    # calculate unfulfilled obligations
    # (only to check results; not used below)
    CA_unfulfilled = pd.concat([CA_due, -1*CA_surrendered_hist], axis=1).sum(axis=1)

    # ~~~~~~~~~~~
    # for QC, obligations have been the same as emissions
    QC_oblig = prmt.emissions_and_obligations['QC covered emissions']

    QC_surrendered_hist = prmt.QC_surrendered.loc[prmt.QC_surrendered > 0].dropna()

    QC_due = pd.Series()
    for due_year in range(2014, 2030+1):
        if due_year in ann_compl_years:
            QC_due.at[due_year] = 0
        elif due_year == 2014:
            # special case for Compliance Period 1, which was only two years (2013-2014)
            QC_due.at[due_year] = QC_oblig.loc[due_year-2:due_year-1].sum()
        else:
            # other years in which remaining obligations for the compliance period are due
            QC_due.at[due_year] = QC_oblig.loc[due_year-3:due_year-1].sum()

    # calculate unfulfilled obligations
    QC_unfulfilled = pd.concat([QC_due, -1*QC_surrendered_hist], axis=1).sum(axis=1)

    # ~~~~~~~~~~~
    # combine CA & QC unfulfilled obligations
    # then subtract them from CA & QC obligations incurred in the year prior

    ser = CA_unfulfilled.copy()
    ser.index = ser.index - 1
    CA_unfulfilled_against_yr_prior = ser

    ser = QC_unfulfilled.copy()
    ser.index = ser.index - 1
    QC_unfulfilled_against_yr_prior = ser

    ser = pd.concat([CA_oblig, 
                     QC_oblig, 
                     -1*CA_unfulfilled_against_yr_prior, 
                     -1*QC_unfulfilled_against_yr_prior], 
                    axis=1).sum(axis=1)
    
    # only keep rows with values greater than zero, which means only rows with historical data
    ser = ser.loc[ser > 0]

    # set value of prmt.CA_QC_obligations_fulfilled_hist
    # used to calculate annual bank, by subtracting from private holdings
    prmt.CA_QC_obligations_fulfilled_hist = ser
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    # no return
# end of obligations_fulfilled_historical_calculation


# In[ ]:


def create_snaps_CAQC_toward_bank(scenario_CA, scenario_QC):
    """
    Create local variable snaps_end_Q4_CA_QC; use different source depending on scenario/settings
    Use copy to avoid modifying object attributes.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")

    # use full auction results generated on initialization
    # stored as scenario_CA.snaps_end & scenario_QC.snaps_end
    # (those are lists of dfs; need to add the lists to concat all dfs in the combined list)
    df = pd.concat(scenario_CA.snaps_end + scenario_QC.snaps_end, axis=0, sort=False)

    # convert to period
    df['snap_q'] = pd.to_datetime(df['snap_q'].astype(str)).dt.to_period('Q')

    # keep only Q4
    snaps_end_Q4_CA_QC = df.loc[df['snap_q'].dt.quarter==4].copy()
    
    # create col 'snap_yr' to replace col 'snap_q'
    snaps_end_Q4_CA_QC['snap_yr'] = snaps_end_Q4_CA_QC['snap_q'].dt.year
    snaps_end_Q4_CA_QC = snaps_end_Q4_CA_QC.drop(columns=['snap_q'])

    # select only the allowances in private accounts (general account and compliance account)
    private_acct_mask = snaps_end_Q4_CA_QC.index.get_level_values('acct_name').isin(['gen_acct', 'comp_acct'])
    snaps_CAQC_toward_bank = snaps_end_Q4_CA_QC.loc[private_acct_mask]
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(snaps_end_Q4_CA_QC, snaps_CAQC_toward_bank)
# end of create_snaps_CAQC_toward_bank


# In[ ]:


def create_allow_vint_ann(snaps_CAQC_toward_bank):
    """
    From snaps at end of each year, collect and sum all vintaged allowances in private accounts.
    
    These are allowances sold at auction or distributed as allocations.
    
    The values are prior to any retirements for compliance obligations.
    
    The totals are only those vintages up to the year of the banking metric.
    
    The values exclude VRE allowances (which are in VRE account, or transferred to retirement).
    
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")

    df = snaps_CAQC_toward_bank.copy()

    mask1 = df.index.get_level_values('vintage') <= df['snap_yr']
    mask2 = df.index.get_level_values('acct_name').isin(['gen_acct', 'comp_acct'])
    # note that mask2 will get vintages up to banking metric year, and also filter out non-vintage allowances
    mask = (mask1) & (mask2)
    df = df.loc[mask]
    
    # ~~~~~~~~~~~~~~~~

    # result contains allowances sold at advance and current auctions, as well as allowances freely allocated
    # (returns to using df derived from snaps_CAQC_toward_bank)
    df = df.groupby('snap_yr').sum()
    df.index.name = 'snap_yr'
    
    # convert to Series by only selecting ['quant']; give Series a name
    allow_vintaged_cumul = df['quant']
    allow_vintaged_cumul.name = 'allow_vintaged_cumul'
    
    # ~~~~~~~~~~~~~~
    # get historical data
    # insert value for initial quarter (since diff turns that into NaN)
    allow_vint_ann = allow_vintaged_cumul.diff()
    first_year = allow_vint_ann.index.min()
    allow_vint_ann.at[first_year] = allow_vintaged_cumul.at[first_year]
    allow_vint_ann.name = 'allow_vint_ann'
    
    prmt.allow_vint_ann = allow_vint_ann
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    # no return
# end of create_allow_vint_ann


# In[ ]:


def create_allow_nonvint_ann(snaps_CAQC_toward_bank):
    """
    From snaps at end of each year, collect and sum all non-vintaged allowances in private accounts.
    
    These include:
    * Early Action allowances distributed (QC only)
    * APCR allowances distributed as part of allocation true-ups (QC only)
    * APCR allowances sold in historical reserve sales
    
    Does *not* include projected reserve sales; those are handled later in supply_demand_calculations.
    
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")

    df = snaps_CAQC_toward_bank.copy()

    # note: APCR assigned vintage 2200; Early Action assigned vintage 2199
    mask1 = df.index.get_level_values('vintage') >= 2199
    mask2 = df.index.get_level_values('acct_name').isin(['gen_acct', 'comp_acct'])
    mask = (mask1) & (mask2)
    df = df.loc[mask]
    
    df = df.groupby('snap_yr').sum()
    df.index.name = 'snap_yr'
    allow_nonvint_cumul = df['quant']
    allow_nonvint_cumul.name = 'allow_nonvint_cumul'

    # insert value for initial quarter (since diff turns that into NaN)
    allow_nonvint_ann = allow_nonvint_cumul.diff()
    first_year = allow_nonvint_ann.index.min()
    allow_nonvint_ann.at[first_year] = allow_nonvint_cumul.at[first_year]
    allow_nonvint_ann.name = 'allow_nonvint_ann'
    
    prmt.allow_nonvint_ann = allow_nonvint_ann
    # no return
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
# end of create_allow_nonvint_ann


# In[ ]:


def offsets_projection():
    """
    Create projection for offset issuance.
    
    If there is partial data for a given year, will fill in remaining quarters with projection based on user settings.
    
    That is, user settings for rate of offset issuance will apply to all quarters without historical data.
    
    For CA, limits for each period based on § 95854(b) and § 95854(c).
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")

    offsets_priv_hist = prmt.CIR_offsets_q_sums[['General', 'Compliance']].sum(axis=1)
    offsets_priv_hist.name = 'offsets_priv_hist'
    
    # get offsets retired for compliance obligations
    # (derived from input file, sheet "annual compliance reports")
    offsets_compl_oblig_hist = prmt.compliance_events.xs('offsets', level='vintage or type')
    offsets_compl_oblig_hist_cumul = offsets_compl_oblig_hist.cumsum()
    offsets_compl_oblig_hist_cumul.rename(columns={'quant': 'offsets_compl_cumul'}, inplace=True)

    # calculate cumulative offsets added to supply
    # (excludes any offsets that were retired anomalously--that is, not for compliance obligations)
    df = pd.concat([offsets_priv_hist, offsets_compl_oblig_hist_cumul], axis=1)
    
    # exclude any rows in which there's a mismatch between CIR and compliance data
    # (that is, compliance data is ahead of CIR)
    df = df.dropna(subset=['offsets_priv_hist'])
    df = df.ffill()
    offsets_supply_hist_cumul = df.sum(axis=1)

    # BANKING METRIC: supply: offsets
    # B = A' + N + **O** - E

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # HISTORICAL 
    # get quarterly values derived from CIR and annual compliance reports
    # insert value for initial quarter (since diff turns that into NaN)
    offsets_supply_q = offsets_supply_hist_cumul.diff()
    first_q = offsets_supply_q.index.min()
    offsets_supply_q.at[first_q] = offsets_supply_hist_cumul.at[first_q]
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # PROJECTION TO FILL OUT REMAINING QUARTERS IN YEAR WITH PARTIAL DATA
    # if a year has only partial quarterly data, make projection for remainder of year
    off_hist_latest_date = offsets_supply_q.index.max()
    prmt.off_proj_first_date = pd.to_datetime(off_hist_latest_date.to_timestamp() + DateOffset(months=3)).to_period('Q')

    if off_hist_latest_date.quarter < 4:
        
        # then there is a partial year of data
        # create projection for remainder of year, based on user setting
        # get user specified offsets use rate, as % of limit (same rate for all periods)    
        if offsets_tabs.selected_index == 0:
            # simple version of user settings
            if prmt.off_proj_first_date.year in range(2013, 2020+1):
                offset_rate_CA = off_pct_of_limit_CAQC.slider.value * 0.08
            elif prmt.off_proj_first_date.year in range(2021, 2025+1):
                offset_rate_CA = off_pct_of_limit_CAQC.slider.value * 0.04
            elif prmt.off_proj_first_date.year in range(2026, 2030+1):
                offset_rate_CA = off_pct_of_limit_CAQC.slider.value * 0.06
            else:
                pass
            offset_rate_QC = off_pct_of_limit_CAQC.slider.value * 0.08
            
            # fill in any remaining quarters using quarterly emissions & the user-specified offset rate
            offset_supply_user_q_avg_CA = (prmt.emissions_ann_CA.at[off_hist_latest_date.year]/4) * offset_rate_CA
            offset_supply_user_q_avg_QC = (prmt.emissions_ann_QC.at[off_hist_latest_date.year]/4) * offset_rate_QC
            offset_supply_user_q_avg = offset_supply_user_q_avg_CA + offset_supply_user_q_avg_QC
            
            for quarter in range(prmt.off_proj_first_date.quarter, 4+1):
                year_q = quarter_period(f'{off_hist_latest_date.year}Q{quarter}')
                offsets_supply_q.at[year_q] = offset_supply_user_q_avg
            
        elif offsets_tabs.selected_index == 1:
            # advanced version of user settings
            if prmt.off_proj_first_date.year in range(2013, 2020+1):
                # for CA & QC separately, using period 1 sliders
                offset_rate_CA = off_pct_CA_adv1.slider.value
                offset_rate_QC = off_pct_QC_adv1.slider.value

            elif prmt.off_proj_first_date.year in range(2021, 2025+1):
                # for CA & QC separately, using period 2 sliders
                offset_rate_CA = off_pct_CA_adv2.slider.value
                offset_rate_QC = off_pct_QC_adv2.slider.value

            elif prmt.off_proj_first_date.year in range(2026, 2030+1):
                # for CA & QC separately, for period 3 sliders
                offset_rate_CA = off_pct_CA_adv3.slider.value
                offset_rate_QC = off_pct_QC_adv3.slider.value
                
            else:
                print("Error" + "! Edge case within 'elif offsets_tabs.selected_index == 1'")
            
            offset_supply_user_q_avg_CA = prmt.emissions_ann_CA.at[off_hist_latest_date.year] * offset_rate_CA / 4
            offset_supply_user_q_avg_QC = prmt.emissions_ann_QC.at[off_hist_latest_date.year] * offset_rate_QC / 4
            offset_supply_user_q_avg = offset_supply_user_q_avg_CA + offset_supply_user_q_avg_QC
            
            # fill in df        
            for quarter in range(off_hist_latest_date.quarter+1, 4+1):
                year_q = quarter_period(f'{off_hist_latest_date.year}Q{quarter}')
                offsets_supply_q.at[year_q] = offset_supply_user_q_avg
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # COMPARE COMPLIANCE DATA VS PROJECTION
    # if there is compliance data for a year in which Q4 CIR is not yet available to show supply,
    # then compare the projected supply for that year against compliance data
    # if compliance surrender was larger than projected supply, there must have been addition to supply
    # that occurred in Oct prior to compliance event
    
    # create df as above; get final row; check whether value for CIR is NaN
    priv_compl = pd.concat([offsets_priv_hist, offsets_compl_oblig_hist_cumul], axis=1)
    
    latest_priv_hist_quant = priv_compl.loc[priv_compl.index[-1]].loc['offsets_priv_hist']
    
    if pd.isna(latest_priv_hist_quant) == True and priv_compl.index[-1].quarter == 4:
        # then compliance data is in model ahead of CIR data
        # so check annual offsets for compliance against supply in Q3 from CIR
        compl_latest_year = offsets_compl_oblig_hist.loc[priv_compl.index[-1], 'quant']

        Q3_priv_hist_quant = priv_compl.loc[priv_compl.index[-2]].loc['offsets_priv_hist']
        
        if compl_latest_year > Q3_priv_hist_quant:
            # there must have been additional offset issuance in October prior to compliance event
            # this is the minimum gross addition to private accounts in Q4
            # compare against projection from above to see if projection was enough
            inferred_min_issuance = compl_latest_year - Q3_priv_hist_quant
            
            proj_Q4 = offsets_supply_q.loc[priv_compl.index[-1]]
            
            if proj_Q4 < inferred_min_issuance:
                # update projection quantity to be add_issuance
                offsets_supply_q.at[priv_compl.index[-1]] = inferred_min_issuance
                
                logging.info(f"User setting for offset projection was overridden, based on historical compliance;")
                logging.info(f"inferred minimum issuance in {priv_compl.index[-1]}Q4 was {inferred_min_issuance} M.")
            
            else:
                # then we don't have any reason to infer additional offsets issued in October before compliance event
                # will use Q4 projection as calculated in initial projection
                pass

        else:
            # then we don't have any reason to infer additional offsets issued in October before compliance event
            # will use Q4 projection as calculated in initial projection
            pass
    else:
        # compliance data is not ahead of CIR data, so there is no additional data to draw on
        pass
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # CALCULATE ANNUAL OFFSETS
    # after checking quarterly projection above
    offsets_supply_ann = offsets_supply_q.resample('A').sum()
    offsets_supply_ann.index = offsets_supply_ann.index.year.astype(int)
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # PROJECTION BEYOND LAST YEAR WITH HISTORICAL DATA
    # as default, use ARB's assumption for 2021-2030, from Post-2020 analysis (0.75, or 75% of limit)
    # set earlier as prmt.offset_rate_fract_of_limit_default = 0.75
    
    logging.info(f"offset_rate_fract_of_limit_default: {prmt.offset_rate_fract_of_limit_default}")
    
    # note that this is about the same as what historical analysis through 2018Q2 gives
    # from 2018Q2 CIR, ~100 M offsets cumulative supply
    # cumulative CA-QC covered emissions through 2018Q2 were 1666 M ***if*** emissions fell 2%/yr after 2016
    # which means offsets issued through 2018Q2 were about 6.0% of emissions
    # with the offset limit for CA & QC over this period set at 8%, 
    # then the issuance is 75% of the limit
    # and that's the same as ARB's assumption (although ARB didn't state a rationale)
    
    # the offset_rate_fract_of_limit_default sets the default value in offset sliders

    # ~~~~~~~~~
    
    # get values from sliders 
    # (before user does first interaction, will be based on default set above)

    if offsets_tabs.selected_index == 0:
        # simple settings
        logging.info("using offsets settings (simple)")
        
        # get user specified offsets use rate, as % of limit (same rate for all periods)
        if prmt.off_proj_first_date.year+1 <= 2020:
            for year in range(max(2020, off_hist_latest_date.year+1), 2020+1):
                # for CA & QC together
                offset_rate_ann_CAQC = off_pct_of_limit_CAQC.slider.value * 0.08    
                offsets_supply_ann.at[year] = prmt.emissions_ann.at[year] * offset_rate_ann_CAQC
                
        else:
            # don't create this slider for period < 2020
            pass
        
        if prmt.off_proj_first_date.year+1 <= 2025:
            for year in range(max(2021, off_hist_latest_date.year+1), 2025+1):
                # for CA & QC separately
                offset_rate_CA = off_pct_of_limit_CAQC.slider.value * 0.04
                offset_rate_QC = off_pct_of_limit_CAQC.slider.value * 0.08

                offsets_supply_ann_CA_1y = prmt.emissions_ann_CA.at[year] * offset_rate_CA
                offsets_supply_ann_QC_1y = prmt.emissions_ann_QC.at[year] * offset_rate_QC

                # combine CA & QC
                offsets_supply_ann.at[year] = offsets_supply_ann_CA_1y + offsets_supply_ann_QC_1y
        else:
            # don't create this slider
            pass

        if prmt.off_proj_first_date.year+1 <= 2030:
            for year in range(max(2026, off_hist_latest_date.year+1), 2030+1):
                # for CA & QC separately
                offset_rate_CA = off_pct_of_limit_CAQC.slider.value * 0.06
                offset_rate_QC = off_pct_of_limit_CAQC.slider.value * 0.08

                offsets_supply_ann_CA_1y = prmt.emissions_ann_CA.at[year] * offset_rate_CA
                offsets_supply_ann_QC_1y = prmt.emissions_ann_QC.at[year] * offset_rate_QC

                # combine CA & QC
                offsets_supply_ann.at[year] = offsets_supply_ann_CA_1y + offsets_supply_ann_QC_1y
        else:
            # don't create this slider
            pass

    elif offsets_tabs.selected_index == 1:
        # advanced settings
        logging.info("using offsets settings (advanced)")
        
        if off_hist_latest_date.year+1 <= 2020:
            for year in range(max(2020, off_hist_latest_date.year+1), 2020+1):
                # for CA & QC separately, using period 1 sliders
                offset_rate_CA = off_pct_CA_adv1.slider.value
                offset_rate_QC = off_pct_QC_adv1.slider.value

                offsets_supply_ann_CA_1y = prmt.emissions_ann_CA.at[year] * offset_rate_CA
                offsets_supply_ann_QC_1y = prmt.emissions_ann_QC.at[year] * offset_rate_QC

                # combine CA & QC
                offsets_supply_ann.at[year] = offsets_supply_ann_CA_1y + offsets_supply_ann_QC_1y
        else:
            # don't calculate offsets_supply_ann for this range
            pass

        if off_hist_latest_date.year+1 <= 2025:
            for year in range(max(2021, off_hist_latest_date.year+1), 2025+1):
                # for CA & QC separately, using period 2 sliders
                offset_rate_CA = off_pct_CA_adv2.slider.value
                offset_rate_QC = off_pct_QC_adv2.slider.value

                offsets_supply_ann_CA_1y = prmt.emissions_ann_CA.at[year] * offset_rate_CA
                offsets_supply_ann_QC_1y = prmt.emissions_ann_QC.at[year] * offset_rate_QC

                # combine CA & QC
                offsets_supply_ann.at[year] = offsets_supply_ann_CA_1y + offsets_supply_ann_QC_1y
        else:
            # don't calculate offsets_supply_ann for this range
            pass

        if off_hist_latest_date.year+1 <= 2030:
            for year in range(max(2026, off_hist_latest_date.year+1), 2030+1):
                # for CA & QC separately, for period 3 sliders
                offset_rate_CA = off_pct_CA_adv3.slider.value
                offset_rate_CA = off_pct_CA_adv3.slider.value
                offset_rate_QC = off_pct_QC_adv3.slider.value

                offsets_supply_ann_CA_1y = prmt.emissions_ann_CA.at[year] * offset_rate_CA
                offsets_supply_ann_QC_1y = prmt.emissions_ann_QC.at[year] * offset_rate_QC

                # combine CA & QC
                offsets_supply_ann.at[year] = offsets_supply_ann_CA_1y + offsets_supply_ann_QC_1y
        else:
            # don't calculate offsets_supply_ann for this range
            pass

    else:
        # offsets_tabs.selected_index is not 0 or 1
        print("Error" + "! offsets_tabs.selected_index was not one of the expected values (0 or 1).")

    offsets_supply_ann.name = 'offsets_supply_ann'
    
    # calculate quarterly values for all years
    # first get all annual supply full year projections
    df = offsets_supply_ann.loc[offsets_supply_q.index.year.max()+1:]

    # divide by 4, reassign index to quarterly, fill in missing data
    # (have to put in 2031 value as placeholder, so that resample will go through end of 2030)
    df = df / 4
    df.at[2031] = 0
    df.index = pd.to_datetime(df.index.astype(str) + 'Q1').to_period('Q')
    df = df.resample('Q').ffill()
    df = df.drop(quarter_period('2031Q1'))

    # append the quarterly projections to the quarterly data 
    # (historical data; also, if latest historical year has only partial data, projection for remainder of year)
    offsets_supply_q = offsets_supply_q.append(df)

    offsets_supply_q.name = 'offsets_supply_q'
    
    prmt.offsets_supply_ann = offsets_supply_ann
    prmt.offsets_supply_q = offsets_supply_q
    # no return
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
# end of offsets_projection


# In[ ]:


def excess_offsets_calc():
    """
    Calculate whether the offset supply (as specified by user) exceeds what could be used through 2030.
    
    For all compliance periods *except* period #5 (for emissions 2024-2026):
    assume ARB allows emitters to go up to max for whole compliance period, 
    regardless of offset use in annual compliance events during that compliance period.
    
    For compliance period #5, for CA, max offsets are applied separately to emissions 2024-2025 and emissions 2026,
    based on CA regulations adopted by ARB Dec 2018.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")

    # get historical record of offsets used for compliance
    offsets_used_hist = prmt.compliance_events.loc[
        prmt.compliance_events.index.get_level_values('vintage or type')=='offsets']
    
    # get the latest year with compliance event data
    latest_comp_y = prmt.compliance_events.index.get_level_values('compliance_date').max().year
    
    # initialize offsets_avail (value is then iteratively updated below)
    # offsets used in CP1
    offsets_used_in_completed_periods = offsets_used_hist[
        offsets_used_hist.index.get_level_values('compliance_date').year.isin([2014, 2015])]['quant'].sum()

    # initialize first_em_year, which is first year of emissions for each compliance period
    # (starting with the first 3-year compliance period, Compliance Period 2, 2015-2017)
    first_em_year = 2015
    
    # compliance period #2 obligations for emissions 2015-2017 (due Nov 1, 2018)
    if latest_comp_y < first_em_year+3:
        # latest CIR data is before 2018Q4, so simulate compliance period #2 obligations
        
        # offsets available for use in compliance period #2
        # Q3 and Q4 below refer to year of compliance event (first_em_year+3)
        offsets_supply_at_end_Q3 = prmt.offsets_supply_q.loc[:quarter_period(f'{first_em_year+3}Q3')].sum()
        offsets_supply_Q4_first_mo = prmt.offsets_supply_q.at[quarter_period(f'{first_em_year+3}Q4')] / 3
        # Q4 first month above is an approximation
        offsets_supply_at_event = offsets_supply_at_end_Q3 + offsets_supply_Q4_first_mo
        offsets_avail = offsets_supply_at_event - offsets_used_in_completed_periods
        
        # max offsets are 8% for both CA & QC; 
        max_off_p2_CA = prmt.emissions_ann_CA.loc[first_em_year:first_em_year+2].sum() * 0.08
        max_off_p2_QC = prmt.emissions_ann_QC.loc[first_em_year:first_em_year+2].sum() * 0.08
        
        # CA + QC: calculate the max offsets that could be used, given the offsets projection (prmt.offsets_supply_q)
        # minimum of: max that could be used in p2 & offsets available at time of p2
        max_off_p2_given_off_proj = min((max_off_p2_CA + max_off_p2_QC), offsets_avail)

        # update offsets_avail to remove max offset use
        offsets_avail += -1 * max_off_p2_given_off_proj
        offsets_used_in_completed_periods += max_off_p2_given_off_proj

    else:
        pass

    # ~~~~~~~~~~~~~~~~~~~~
    
    # add to offsets_used_in_completed_periods, to reflect actual use
    offsets_used_in_completed_periods += offsets_used_hist[
        offsets_used_hist.index.get_level_values('compliance_date').year.isin(
            list(range(first_em_year+1, first_em_year+4)))]['quant'].sum()

    first_em_year += 3 # step forward 3 years
    
    # compliance period #3 obligations for emissions 2018-2020 (due Nov 1, 2021)
    if latest_comp_y < first_em_year+3:
        # latest CIR data is before 2021Q4, so simulate compliance period #3 obligations
        
        # offsets available for use in compliance period #3
        # Q3 and Q4 below refer to year of compliance event (first_em_year+3)
        offsets_supply_at_end_Q3 = prmt.offsets_supply_q.loc[:quarter_period(f'{first_em_year+3}Q3')].sum()
        offsets_supply_Q4_first_mo = prmt.offsets_supply_q.at[quarter_period(f'{first_em_year+3}Q4')] / 3
        # Q4 first month above is an approximation

        offsets_supply_at_event = offsets_supply_at_end_Q3 + offsets_supply_Q4_first_mo
        offsets_avail = offsets_supply_at_event - offsets_used_in_completed_periods 
        
        # max offsets are 8% for CA & QC
        max_off_p3_CA = prmt.emissions_ann_CA.loc[first_em_year:first_em_year+2].sum() * 0.08
        max_off_p3_QC = prmt.emissions_ann_QC.loc[first_em_year:first_em_year+2].sum() * 0.08
            
        # CA + QC: calculate the max offsets that could be used, given the offsets projection (prmt.offsets_supply_q)
        # minimum of: max that could be used in p3 & offsets available at time of p3
        max_off_p3_given_off_proj = min((max_off_p3_CA + max_off_p3_QC), offsets_avail)

        # update offsets_avail to remove max offset use
        offsets_avail += -1 * max_off_p3_given_off_proj
        offsets_used_in_completed_periods += max_off_p3_given_off_proj
        
    else:
        pass

    # ~~~~~~~~~~~~~~~~~~~~
    
    offsets_used_in_completed_periods += offsets_used_hist[
        offsets_used_hist.index.get_level_values('compliance_date').year.isin(
            list(range(first_em_year+1, first_em_year+4)))]['quant'].sum()

    first_em_year += 3 # step forward 3 years

    # compliance period #4 obligations for emissions 2021-2023 (due Nov 1, 2024)
    if latest_comp_y < first_em_year+3:
        # latest CIR data is before 2021Q4, so simulate compliance period #4 obligations
        
        # offsets available for use in compliance period #4
        # Q3 and Q4 below refer to year of compliance event (first_em_year+3)
        offsets_supply_at_end_Q3 = prmt.offsets_supply_q.loc[:quarter_period(f'{first_em_year+3}Q3')].sum()
        offsets_supply_Q4_first_mo = prmt.offsets_supply_q.at[quarter_period(f'{first_em_year+3}Q4')] / 3
        # Q4 first month above is an approximation
        offsets_supply_at_event = offsets_supply_at_end_Q3 + offsets_supply_Q4_first_mo
        offsets_avail = offsets_supply_at_event - offsets_used_in_completed_periods 
        
        # max offsets are 4% for CA & 8% for QC
        max_off_p4_CA = prmt.emissions_ann_CA.loc[first_em_year:first_em_year+2].sum() * 0.04
        max_off_p4_QC = prmt.emissions_ann_QC.loc[first_em_year:first_em_year+2].sum() * 0.08
        
        # CA + QC: calculate the max offsets that could be used, given the offsets projection (prmt.offsets_supply_q)
        # minimum of: max that could be used in p4 & offsets available at time of p4
        max_off_p4_given_off_proj = min((max_off_p4_CA + max_off_p4_QC), offsets_avail)

        # update offsets_avail to remove max offset use
        offsets_avail += -1 * max_off_p4_given_off_proj
        offsets_used_in_completed_periods += max_off_p4_given_off_proj
        
    else:
        pass

    # ~~~~~~~~~~~~~~~~~~~~
    offsets_used_in_completed_periods += offsets_used_hist[
        offsets_used_hist.index.get_level_values('compliance_date').year.isin(
            list(range(first_em_year+1, first_em_year+4)))]['quant'].sum()

    first_em_year += 3 # step forward 3 years

    # compliance period #5 obligations for emissions 2024-2026 (due in full Nov 1, 2027)

    # ***IMPORTANT NOTE***
    # this compliance period is anomalous for CA because of change in offset max use under AB 398 from 4% to 6%,
    # which doesn't match with timing of compliance period deadline

    if latest_comp_y < first_em_year+3:
        # latest CIR data is before 2021Q4, so simulate compliance period #5 obligations
        
        # offsets available for use in compliance period #5
        # Q3 and Q4 below refer to year of compliance event (first_em_year+3)
        offsets_supply_at_end_Q3 = prmt.offsets_supply_q.loc[:quarter_period(f'{first_em_year+3}Q3')].sum()
        offsets_supply_Q4_first_mo = prmt.offsets_supply_q.at[quarter_period(f'{first_em_year+3}Q4')] / 3
        # Q4 first month above is an approximation
        offsets_supply_at_event = offsets_supply_at_end_Q3 + offsets_supply_Q4_first_mo
        offsets_avail = offsets_supply_at_event - offsets_used_in_completed_periods 
        
        # for CA, max offsets are 4% for emissions incurred in 2024-2025, 6% for emissions incurred in 2026
        # for QC, max offsets are 8% of emissions for all years 2024-2026
 
        max_off_CA_2024_2025 = prmt.emissions_ann_CA.loc[first_em_year:first_em_year+1].sum() * 0.04
        max_off_CA_2026 = prmt.emissions_ann_CA.loc[first_em_year+2].sum() * 0.06
        max_off_p5_QC = prmt.emissions_ann_QC.loc[first_em_year:first_em_year+2].sum() * 0.08

        max_off_p5 = max_off_CA_2024_2025 + max_off_CA_2026 + max_off_p5_QC
        
        # CA + QC: calculate the max offsets that could be used, given the offsets projection (prmt.offsets_supply_q)
        # minimum of: max that could be used in p5 & offsets available at time of p5
        max_off_p5_given_off_proj = min((max_off_p5), offsets_avail)

        # update offsets_avail to remove max offset use
        offsets_avail += -1 * max_off_p5_given_off_proj
        offsets_used_in_completed_periods += max_off_p5_given_off_proj
        
    else:
        pass

    # ~~~~~~~~~~~~~~~~~~~~
    
    offsets_used_in_completed_periods += offsets_used_hist[
        offsets_used_hist.index.get_level_values('compliance_date').year.isin(
            list(range(first_em_year+1, first_em_year+4)))]['quant'].sum()

    first_em_year += 3 # step forward 3 years
    
    # compliance period #6 obligations for emissions 2027-2029 (due Nov 1, 2030)

    if latest_comp_y < first_em_year+3:
        # latest CIR data is before 2021Q4, so simulate compliance period #6 obligations
        
        # offsets available for use in compliance period #6
        # Q3 and Q4 below refer to year of compliance event (first_em_year+3)
        offsets_supply_at_end_Q3 = prmt.offsets_supply_q.loc[:quarter_period(f'{first_em_year+3}Q3')].sum()
        offsets_supply_Q4_first_mo = prmt.offsets_supply_q.at[quarter_period(f'{first_em_year+3}Q4')] / 3
        # Q4 first month above is an approximation
        offsets_supply_at_event = offsets_supply_at_end_Q3 + offsets_supply_Q4_first_mo
        offsets_avail = offsets_supply_at_event - offsets_used_in_completed_periods 
        
        # max offsets are 6% for CA & 8% for QC
        max_off_p6_CA = prmt.emissions_ann_CA.loc[first_em_year:first_em_year+2].sum() * 0.06
        max_off_p6_QC = prmt.emissions_ann_QC.loc[first_em_year:first_em_year+2].sum() * 0.08
        
        # CA + QC: calculate the max offsets that could be used, given the offsets projection (prmt.offsets_supply_q)
        # minimum of: max that could be used in p6 & offsets available at time of p6
        max_off_p6_given_off_proj = min((max_off_p6_CA + max_off_p6_QC), offsets_avail)

        # update offsets_avail to remove max offset use
        offsets_avail += -1 * max_off_p6_given_off_proj
        offsets_used_in_completed_periods += max_off_p6_given_off_proj
        
    else:
        pass

    # ~~~~~~~~~~~~~~~~~~~~
    # after assuming max offset use, see if any offsets remaining in offsets_avail
    # if so, these are excess offsets
    # show warning only if the excess is significant (> 5 MMTCO2e)
    # note: when offset settings at 100% of limit (and other settings at default), there can be ~3 M excess 
    # this is due to mismatches in timing of offset supply and compliance obligations
    if offsets_avail > 5: # units MMTCO2e
        prmt.excess_offsets = offsets_avail
        
        # round off for display
        excess_int = int(round(prmt.excess_offsets, 0))
        
        error_msg_1 = "Warning" + "! The scenario has significant excess offsets, beyond what could be used by the end of 2030."        
        error_msg_2 = f"The excess of offsets was {excess_int} MMTCO2e."
        logging.info(error_msg_1)
        logging.info(error_msg_2)
        prmt.error_msg_post_refresh += [error_msg_1]
        prmt.error_msg_post_refresh += [error_msg_2]
        prmt.error_msg_post_refresh += [" "] # line break
        
    else:
        prmt.excess_offsets = 0
        pass
    
    # no return; set object attribute above
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")

# end of excess_offsets_calc


# ## Functions: Calculate metrics & compare with CIR
# * private_bank_annual_metric_model_method
# * turn_snap_into_CIR
# * turn_snap_into_CIR_for_private_bank_metric
# * turn_snap_into_CIR_for_private_bank_metric_projection
# * private_bank_annual_metric_paper_method
# * compliance_period_metrics_historical
# * compliance_period_metrics_projection
# * compile_annual_metrics_for_export
# * compile_compliance_period_metrics_for_export

# In[ ]:


def private_bank_annual_metric_model_method(supply_ann_df):
    """
    Method of calculating Private Bank metric originally developed for the model.
    
    For years with full historical data on the supply side, values are overwritten using method from 
    Near Zero's banking paper (Cullenward et al., 2019).  
    
    For all projection years, the method in this function is used for calculating the Private Bank.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # modify supply_ann_df to include additional columns, including cumulative values
    df = supply_ann_df.copy()

    # calculate balance prior to any projected reserve & PCU sales
    # note: at this point, 'allow_nonvint_ann' does not include *projected* reserve & PCU sales
    df['obligations'] = prmt.CA_QC_obligations_fulfilled_hist_proj
    df['balance_ann'] = supply_ann_df.sum(axis=1) - df['obligations']
    df['balance_cumul'] = df['balance_ann'].cumsum()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # HISTORICAL RESERVE SALES
    
    # Note: allow_nonvint_ann above already includes any historical reserve sales for calculating balance,
    # together with other distributions of nonvint allowances (APCR for allocations & Early Action allowances).
    # Use reserve_PCU_sales_cumul_hist to represent historical reserve sales, 
    # which may occur before bank is exhausted.
    
    # start from historical record of cumulative reserve sales (prmt.reserve_PCU_sales_q_hist)
    # convert index to annual & calculate annual sums
    # for historical years, use historical values to overwrite any modeled values
    ser = prmt.reserve_PCU_sales_q_hist.copy()
    ser.index = ser.index.year
    ser = ser.groupby(ser.index).sum()
    reserve_PCU_sales_ann_hist = ser
    
    # drop year 2012; metrics not calculated for that year
    # (we know value was zero, so dropping it doesn't affect any calculations)
    reserve_PCU_sales_ann_hist = reserve_PCU_sales_ann_hist.drop(2012)
    reserve_PCU_sales_cumul_hist = reserve_PCU_sales_ann_hist.cumsum()
    
    for year in reserve_PCU_sales_cumul_hist.index:
        df.at[year, 'reserve_PCU_ann'] = reserve_PCU_sales_ann_hist.at[year]
        df.at[year, 'reserve_PCU_cumul'] = reserve_PCU_sales_cumul_hist.at[year]

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # determine starting year for projection of reserve/PCU sales
    if prmt.reserve_PCU_sales_q_hist.index[-1].quarter < 4:
        # partial year of historical data on reserve/PCU sales
        # start projection with that partial year
        reserve_PCU_sales_proj_start_year = prmt.reserve_PCU_sales_q_hist.index[-1].year

    elif prmt.reserve_PCU_sales_q_hist.index[-1].quarter == 4:
        # full year of historical data on reserve/PCU sales
        # start projection with following year
        reserve_PCU_sales_proj_start_year = prmt.reserve_PCU_sales_q_hist.index[-1].year + 1

    # create projection of reserve & PCU sales, starting from first full projection year
    for year in range(reserve_PCU_sales_proj_start_year, 2030+1):
        if df.at[year, 'balance_cumul'] >= 0:
            # no more reserve/PCU sales required           
            reserve_PCU_ann_sales = 0
            
            # if this is a partial year projection, no *additional* reserve/PCU sales are required
            # any historical reserve/PCU sales would be included already in 'allow_nonvint_ann'
            # and in 'reserve_PCU_ann' & 'reserve_PCU_cumul'            

        elif df.at[year, 'balance_cumul'] < 0:
            # without reserve sales, there would be a supply shortfall in this year
            # calculate reserve & PCU sales required to achieve balance of 0
            
            # note that this function iteratively updates 'balance_cumul' values, 
            # so that if balance_cumul had gone negative in year prior, it would trigger reserve sales
            # and values for balance_cumul in that year and all later years were revised to reflect reserve sales
            reserve_PCU_ann_sales = -1 * df.at[year, 'balance_cumul']
            
        else:
            print(f"Error! Unexpected value for balance_cumul in year: {df.at[year, 'balance_cumul']}") # for UI

        # update or fill in values for reserve sales
        if year==prmt.reserve_PCU_sales_q_hist.index[-1].year and prmt.reserve_PCU_sales_q_hist.index[-1].quarter<4:
            # partial year; update existing value
            df.at[year, 'reserve_PCU_ann'] = df.at[year, 'reserve_PCU_ann'] + reserve_PCU_ann_sales
                  
            # cumulative update is sum of:
            # previous year value & historical data from input file & additional reserve/PCU sales
            df.at[year, 'reserve_PCU_cumul'] = sum([df.at[year-1, 'reserve_PCU_cumul'],
                                                    df.at[year, 'reserve_PCU_cumul'], 
                                                    reserve_PCU_ann_sales])
        else: 
            # full projection years; set new value
            df.at[year, 'reserve_PCU_ann'] = reserve_PCU_ann_sales
            df.at[year, 'reserve_PCU_cumul'] = sum([df.at[year-1, 'reserve_PCU_cumul'],
                                                    reserve_PCU_ann_sales])
        
        # update balance_ann to reflect reserve & PCU sales in year
        df.at[year, 'balance_ann'] += reserve_PCU_ann_sales

        # update balance_cumul to reflect reserve & PCU sales
        # including for future years 
        # (so that in next iteration, balance_cumul reflects prior year reserve & PCU sales)
        for year2 in range(year, df.index.max()+1):
            df.at[year2, 'balance_cumul'] += reserve_PCU_ann_sales

        # update allow_nonvint_ann to reflect projected reserve & PCU sales
        df.at[year, 'allow_nonvint_ann'] += reserve_PCU_ann_sales

    # ~~~~~~~~~~~~~~~
    
    # set attributes
    prmt.bank_cumul = df['balance_cumul']
    prmt.reserve_PCU_sales_cumul = df['reserve_PCU_cumul']
    
    # no return
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
# end of private_bank_annual_metric_model_method


# In[ ]:


def calculate_reserve_account_metric_and_related(snaps_end_Q4_CA_QC):
    """
    Calculates the reserve account metric (Cullenward et al., 2019).
    
    Also calculates when reserve accounts are exhausted, 
    and thus separates Price Ceiling Unit sales from reserve sales.
    
    """
    # same as in banking paper (Cullenward et al. 2019)
    # counts all allowances in reserve accounts (aka APCR)
    
    # snaps contain reserve accounts after all additions, 
    # APCR removals for allocations and historical reserve sales
    # but do not include APCR removals for *projected* reserve sales
    # *projected* reserve sales are handled here, after end of processing main supply functions
    df = snaps_end_Q4_CA_QC.copy()
    df = df.loc[df.index.get_level_values('acct_name')=='APCR_acct']
    reserve_accts_before_sales = df.groupby('snap_yr')['quant'].sum()
    
    # drop the value for 2012; none of the other metrics are being calculated for that year
    reserve_accts_before_sales = reserve_accts_before_sales.drop(2012)
    
    # subtract reserve_PCU_sales_cumul from reserve accounts
    reserve_balance = reserve_accts_before_sales.sub(prmt.reserve_PCU_sales_cumul)
    
    reserve_shortfall = pd.Series()
    for year in reserve_balance.index:
        if reserve_balance.at[year] >= 0:
            # set values to be zero
            reserve_shortfall.at[year] = 0
        elif reserve_balance.at[year] < 0:
            reserve_shortfall.at[year] = -1 * reserve_balance.at[year]
            # shortfall is a positive value
        
    # assume PCU sales will fill in for any reserve shortfall
    PCU_sales_cumul = reserve_shortfall
    PCU_sales_cumul.name = 'PCU_sales_cumul'
    
    # create reserve_accts: balance + PCU sales; minimum should be zero
    reserve_accts = reserve_balance.add(PCU_sales_cumul)
    reserve_accts.name = 'reserve_accts'

    # calculate reserve sales alone (excluding PCU from reserve_PCU_sales_cumul)
    reserve_sales_excl_PCU_cumul = prmt.reserve_PCU_sales_cumul.sub(PCU_sales_cumul)
    
    # set object attributes
    prmt.PCU_sales_cumul = PCU_sales_cumul
    prmt.reserve_accts = reserve_accts
    prmt.reserve_sales_excl_PCU = reserve_sales_excl_PCU_cumul
    
    # no return
# end of calculate_reserve_account_metric_and_related


# In[ ]:


def turn_snap_into_CIR(yr_quart_period, snaps_CAQC):
    """
    Takes model results and reformats for comparison against Compliance Instrument Report (CIR) for historical data.
    
    Date of snap, as labeled by regulators, saved as yr_quart_period; formatted as quarterly period.
       
    Note that snaps are actually taken early in the following quarter, e.g., 2014Q4 snap is taken in early 2015Q1.
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # select particular quarter to convert to CIR
    df = snaps_CAQC[snaps_CAQC.index.get_level_values('snap_q')==yr_quart_period]
    
    # APCR: change vintage to 'APCR'
    mask = df.index.get_level_values('inst_cat').str.contains('APCR') # also selects e.g., 'alloc_2016_APCR'
    APCR = df.loc[mask]
    mapping_dict = {'vintage': 'APCR'}
    APCR = multiindex_change(APCR, mapping_dict)
    
    # recombine APCR & non-APCR
    df = df.loc[~mask].append(APCR)
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Early Action (aka Early Reduction): change vintage to be 'early_action'
    mask = df.index.get_level_values('inst_cat')=='early_action'
    early_action = df.loc[mask]
    mapping_dict = {'vintage': 'early_action'}
    early_action = multiindex_change(early_action, mapping_dict)
    
    # recombine Early Action and non-Early Action
    df = df.loc[~mask].append(early_action)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # "non-vintage allowances" are only APCR: change vintage to be 'APCR'
    mask = df.index.get_level_values('inst_cat')=='APCR'
    APCR_allowances = df.loc[mask]
    mapping_dict = {'vintage': 'APCR'}
    APCR_allowances = multiindex_change(APCR_allowances, mapping_dict)
    
    # recombine APCR allowances and non-APCR
    df = df.loc[~mask].append(APCR_allowances)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # combine alloc_hold, ann_alloc_hold, and auct_hold into one group ('A_I_A')
    # ('A_I_A' is shorthand for column in Compliance Instrument Report "Auction + Issuance + Allocation")
    # note: issuance account is only for offsets, which are not in snaps
    mask = df.index.get_level_values('acct_name').isin(['alloc_hold', 'ann_alloc_hold', 'auct_hold'])
    A_I_A = df.loc[mask]
    mapping_dict = {'acct_name': 'A_I_A'}
    A_I_A = multiindex_change(A_I_A, mapping_dict)
    
    # recombine A_I_A and rest
    df = df.loc[~mask].append(A_I_A)
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # combine gen_acct & comp_acct, because we can't identify a priori reasons for moves
    # can only recreate observed moves
    # so it is useful to compare total of gen_acct + comp_acct in historical record vs. model
    mask = df.index.get_level_values('acct_name').isin(['gen_acct', 'comp_acct'])
    gen_comp = df.loc[mask]
    mapping_dict = {'acct_name': 'gen_comp'}
    gen_comp = multiindex_change(gen_comp, mapping_dict)
    
    # append gen_comp to the rest
    df = df.loc[~mask].append(gen_comp)
    
    # groupby sum to combine all allowances of a particular vintage, or particular type of non-vintage (i.e., APCR)
    df = df.groupby(['acct_name', 'vintage']).sum()
    
    # reshape
    df = df.unstack(0)
    df.columns = df.columns.droplevel(0)
    
    allowances_modeled = df

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # OFFSETS: HISTORICAL
    # add historical offset data from CIR of specified quarter

    if yr_quart_period.year == 2013:
        print("This function doesn't yet handle year 2013.") 
        
    if yr_quart_period.year > 2013:
        df2 = prmt.CIR_offsets_q_sums.loc[prmt.CIR_offsets_q_sums.index==yr_quart_period]

        # TEST: should only be a single row
        if prmt.run_tests == True:
            if len(df2) != 1:
                print(f"{prmt.test_failed_msg} Selection of offsets did not return a single row.")
                if len(df2) == 0:
                    print(f"{prmt.test_failed_msg} Selection of offsets returned zero rows.")
                elif len(df2) > 1:
                    print(f"{prmt.test_failed_msg} Selection of offsets returned more than 1 row.")
                else:
                    print(f"{prmt.test_failed_msg} Selection of offsets had some other error; check into it.")
            else:
                pass
            # END OF TEST

        if len(df2) == 1:
            df2 = df2.drop('subtotal', axis=1)
            df2 = df2.rename(columns={'Auction + Issuance + Allocation': 'A_I_A',
                                      'Compliance': 'comp_acct', 
                                      'Environmental Integrity (QC)': 'env_integrity', 
                                      'General': 'gen_acct', 
                                      'Limited Use Holding Account (CA)': 'limited_use', 
                                      'Reserve': 'APCR_acct', 
                                      'Invalidation': 'invalidation',
                                      'Voluntary Renewable Electricity (CA)': 'VRE_acct', 
                                      'Retirement': 'retirement'})

            # change index that is date of CIR report into metadata indicating that these are offsets
            df2.index = ['offsets']

            df2['gen_comp'] = df2[['gen_acct', 'comp_acct']].sum(axis=1)
            df2 = df2.drop(['gen_acct', 'comp_acct'], axis=1)

            offsets_hist = df2

        else:
            # don't create offsets_hist; line below will hit error, because offsets_hist not defined
            pass

    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # RECOMBINE:
    CIR_snap = pd.concat([allowances_modeled, offsets_hist], sort=True)
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
    CIR_snap['subtotal'] = CIR_snap.sum(axis=1)
    
    # add columns with NaN (if any are missing from list above)
    for col in prmt.CIR_columns:
        if col not in CIR_snap.columns:
            CIR_snap[col] = np.NaN
    
    # reorder columns & change index type to str
    CIR_snap = CIR_snap.reindex(columns=prmt.CIR_columns)
    CIR_snap.index = CIR_snap.index.astype(str)
    
    # fill all NaN with zeros
    CIR_snap = CIR_snap.fillna(0.0)
    
    # name index
    CIR_snap.index.name = 'vintage/type'
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # RETIREMENTS 
    # only for allowances
    # (would be redundant to do similar comparison for offsets, 
    # because data for offsets is drawn from CIR, so comparison wouldn't tell us anything)
    
    df = prmt.compliance_events.copy()
    df = df.loc[df.index.get_level_values('vintage or type')!='offsets']
    df = df.loc[df.index.get_level_values('compliance_date')<=yr_quart_period]
    
    for row in df.index:
        # get vintage and quantity
        vintage = row[1]
        
        retired = df.at[row, 'quant']
        
        # for specified vintage, transfer that quantity from gen_comp to retirement
        CIR_snap.at[vintage, 'gen_comp'] = CIR_snap.at[vintage, 'gen_comp'] - retired
        CIR_snap.at[vintage, 'retirement'] = CIR_snap.at[vintage, 'retirement'] + retired
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
    # calculate totals
    for col in CIR_snap.columns:
        CIR_snap.at['totals (incl. offsets)', col] = CIR_snap[col].sum()
        
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(CIR_snap)
# end of turn_snap_into_CIR


# In[ ]:


def turn_snap_into_CIR_for_private_bank_metric(yr_quart_period, snaps_CAQC):
    """
    Takes model results and reformats for comparison against Compliance Instrument Report (CIR) for historical data.
    
    Date of snap, as labeled by regulators, saved as yr_quart_period; formatted as quarterly period.
    
    Note that snaps are actually taken early in the following quarter, e.g., 2014Q4 snap is taken in early 2015Q1.
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # select particular quarter to convert to CIR
    df = snaps_CAQC[snaps_CAQC.index.get_level_values('snap_q')==yr_quart_period]
    
    # APCR: change vintage to 'APCR'
    mask = df.index.get_level_values('inst_cat').str.contains('APCR') # also selects e.g., 'alloc_2016_APCR'
    APCR = df.loc[mask]
    mapping_dict = {'vintage': 'APCR'}
    APCR = multiindex_change(APCR, mapping_dict)
    
    # recombine APCR & non-APCR
    df = df.loc[~mask].append(APCR)
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Early Action (aka Early Reduction): change vintage to be 'early_action'
    mask = df.index.get_level_values('inst_cat')=='early_action'
    early_action = df.loc[mask]
    mapping_dict = {'vintage': 'early_action'}
    early_action = multiindex_change(early_action, mapping_dict)
    
    # recombine Early Action and non-Early Action
    df = df.loc[~mask].append(early_action)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # "non-vintage allowances" are only APCR: change vintage to be 'APCR'
    mask = df.index.get_level_values('inst_cat')=='APCR'
    APCR_allowances = df.loc[mask]
    mapping_dict = {'vintage': 'APCR'}
    APCR_allowances = multiindex_change(APCR_allowances, mapping_dict)
    
    # recombine APCR allowances and non-APCR
    df = df.loc[~mask].append(APCR_allowances)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # combine alloc_hold, ann_alloc_hold, and auct_hold into one group ('A_I_A')
    # ('A_I_A' is shorthand for column in Compliance Instrument Report "Auction + Issuance + Allocation")
    # note: issuance account is only for offsets, which are not in snaps
    mask = df.index.get_level_values('acct_name').isin(['alloc_hold', 'ann_alloc_hold', 'auct_hold'])
    A_I_A = df.loc[mask]
    mapping_dict = {'acct_name': 'A_I_A'}
    A_I_A = multiindex_change(A_I_A, mapping_dict)
    
    # recombine A_I_A and rest
    df = df.loc[~mask].append(A_I_A)
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # combine gen_acct & comp_acct, because we can't identify a priori reasons for moves
    # can only recreate observed moves
    # so it is useful to compare total of gen_acct + comp_acct in historical record vs. model
    mask = df.index.get_level_values('acct_name').isin(['gen_acct', 'comp_acct'])
    gen_comp = df.loc[mask]
    mapping_dict = {'acct_name': 'gen_comp'}
    gen_comp = multiindex_change(gen_comp, mapping_dict)
    
    # append gen_comp to the rest
    df = df.loc[~mask].append(gen_comp)
    
    # groupby sum to combine all allowances of a particular vintage, or particular type of non-vintage (i.e., APCR)
    df = df.groupby(['acct_name', 'vintage']).sum()
    
    # reshape
    df = df.unstack(0)
    df.columns = df.columns.droplevel(0)
    
    allowances_modeled = df

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # OFFSETS: HISTORICAL
    # add historical offset data from CIR of specified quarter
      
    if yr_quart_period.year == 2013:
        # no record of offsets issued in 2013; assume they are zero
        pass
    
    elif yr_quart_period.year > 2013:
        df2 = prmt.CIR_offsets_q_sums.loc[prmt.CIR_offsets_q_sums.index==yr_quart_period]

        # TEST: should only be a single row
        if prmt.run_tests == True:
            if len(df2) != 1:
                print(f"{prmt.test_failed_msg} Selection of offsets did not return a single row.")
                if len(df2) == 0:
                    print(f"{prmt.test_failed_msg} Selection of offsets returned zero rows.")
                    pass
                elif len(df2) > 1:
                    print(f"{prmt.test_failed_msg} Selection of offsets returned more than 1 row.")
                else:
                    print(f"{prmt.test_failed_msg} Selection of offsets had some other error; check into it.")
            else:
                pass
        # END OF TEST

        if len(df2) == 1:
            df2 = df2.drop('subtotal', axis=1)
            df2 = df2.rename(columns={'Auction + Issuance + Allocation': 'A_I_A',
                                      'Compliance': 'comp_acct', 
                                      'Environmental Integrity (QC)': 'env_integrity', 
                                      'General': 'gen_acct', 
                                      'Limited Use Holding Account (CA)': 'limited_use', 
                                      'Reserve': 'APCR_acct', 
                                      'Invalidation': 'invalidation',
                                      'Voluntary Renewable Electricity (CA)': 'VRE_acct', 
                                      'Retirement': 'retirement'})

            # change index that is date of CIR report into metadata indicating that these are offsets
            df2.index = ['offsets']
            df2['gen_comp'] = df2[['gen_acct', 'comp_acct']].sum(axis=1)
            df2 = df2.drop(['gen_acct', 'comp_acct'], axis=1)
            offsets_hist = df2

        else:
            # don't create offsets_hist; line below will hit error, because offsets_hist not defined
            pass
    
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # RECOMBINE:
    if yr_quart_period.year == 2013:
        CIR_snap = allowances_modeled
        
    elif yr_quart_period.year > 2013:
        CIR_snap = pd.concat([allowances_modeled, offsets_hist], sort=True)
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
    CIR_snap['subtotal'] = CIR_snap.sum(axis=1)
    
    # add columns with NaN (if any are missing from list above)
    for col in prmt.CIR_columns:
        if col not in CIR_snap.columns:
            CIR_snap[col] = np.NaN
    
    # reorder columns & change index type to str
    CIR_snap = CIR_snap.reindex(columns=prmt.CIR_columns)
    CIR_snap.index = CIR_snap.index.astype(str)
    
    # fill all NaN with zeros
    CIR_snap = CIR_snap.fillna(0.0)
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # RETIREMENTS
    # note: offsets_hist used above is only for private holdings; already accounts for retirements
    # therefore only retirements of allowances are calculated below; offsets not included
    df = prmt.compliance_events.copy()
    df = df.loc[df.index.get_level_values('vintage or type')!='offsets']
    df = df.loc[df.index.get_level_values('compliance_date')<=yr_quart_period]
    
    for row in df.index:
        # get vintage and quantity
        vintage = row[1]
        
        retired = df.at[row, 'quant']
        
        # for specified vintage, transfer that quantity from gen_comp to retirement
        CIR_snap.at[vintage, 'gen_comp'] = CIR_snap.at[vintage, 'gen_comp'] - retired
        CIR_snap.at[vintage, 'retirement'] = CIR_snap.at[vintage, 'retirement'] + retired
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(CIR_snap)
# end of turn_snap_into_CIR_for_private_bank_metric


# In[ ]:


def turn_snap_into_CIR_for_private_bank_metric_projection(yr_quart_period, snaps_CAQC):
    """
    Takes model results and reformats for comparison against Compliance Instrument Report (CIR) for historical data.
    
    Date of snap, as labeled by regulators, saved as yr_quart_period; formatted as quarterly period.
    
    Note that snaps are actually taken early in the following quarter, e.g., 2014Q4 snap is taken in early 2015Q1.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # select particular quarter to convert to CIR
    df = snaps_CAQC[snaps_CAQC.index.get_level_values('snap_q')==yr_quart_period]
    
    # APCR: change vintage to 'APCR'
    mask = df.index.get_level_values('inst_cat').str.contains('APCR') # also selects e.g., 'alloc_2016_APCR'
    APCR = df.loc[mask]
    mapping_dict = {'vintage': 'APCR'}
    APCR = multiindex_change(APCR, mapping_dict)
    
    # recombine APCR & non-APCR
    df = df.loc[~mask].append(APCR)
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Early Action (aka Early Reduction): change vintage to be 'early_action'
    mask = df.index.get_level_values('inst_cat')=='early_action'
    early_action = df.loc[mask]
    mapping_dict = {'vintage': 'early_action'}
    early_action = multiindex_change(early_action, mapping_dict)
    
    # recombine Early Action and non-Early Action
    df = df.loc[~mask].append(early_action)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # "non-vintage allowances" are only APCR: change vintage to be 'APCR'
    mask = df.index.get_level_values('inst_cat')=='APCR'
    APCR_allowances = df.loc[mask]
    mapping_dict = {'vintage': 'APCR'}
    APCR_allowances = multiindex_change(APCR_allowances, mapping_dict)
    
    # recombine APCR allowances and non-APCR
    df = df.loc[~mask].append(APCR_allowances)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # combine alloc_hold, ann_alloc_hold, and auct_hold into one group ('A_I_A')
    # ('A_I_A' is shorthand for column in Compliance Instrument Report "Auction + Issuance + Allocation")
    # note: issuance account is only for offsets, which are not in snaps
    mask = df.index.get_level_values('acct_name').isin(['alloc_hold', 'ann_alloc_hold', 'auct_hold'])
    A_I_A = df.loc[mask]
    mapping_dict = {'acct_name': 'A_I_A'}
    A_I_A = multiindex_change(A_I_A, mapping_dict)
    
    # recombine A_I_A and rest
    df = df.loc[~mask].append(A_I_A)
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # combine gen_acct & comp_acct, because we can't identify a priori reasons for moves
    # can only recreate observed moves
    # so it is useful to compare total of gen_acct + comp_acct in historical record vs. model
    mask = df.index.get_level_values('acct_name').isin(['gen_acct', 'comp_acct'])
    gen_comp = df.loc[mask]
    mapping_dict = {'acct_name': 'gen_comp'}
    gen_comp = multiindex_change(gen_comp, mapping_dict)
    
    # append gen_comp to the rest
    df = df.loc[~mask].append(gen_comp)
    
    # groupby sum to combine all allowances of a particular vintage, or particular type of non-vintage (i.e., APCR)
    df = df.groupby(['acct_name', 'vintage']).sum()
    
    # reshape
    df = df.unstack(0)
    df.columns = df.columns.droplevel(0)
    
    allowances_modeled = df
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # rename:
    CIR_snap = allowances_modeled
    
    # calculate sums
    CIR_snap['subtotal'] = CIR_snap.sum(axis=1)
    
    # make a copy (perhaps to avoid copy of a slice warning)
    CIR_snap_allowances_before_retirements = CIR_snap.copy()
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(CIR_snap_allowances_before_retirements)
# end of turn_snap_into_CIR_for_private_bank_metric_projection


# In[ ]:


def private_bank_annual_metric_paper_method():
    """
    Method for calculating the Private Bank metric, in accordance with methods in the paper Cullenward et al., 2019
    ("Tracking banking in the Western Climate Initiative cap-and-trade program")
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # concat the snaps_CIR for each juris:
    # scenario_CA.snaps_CIR and scenario_QC.snaps_CIR are lists of dfs;
    # combine the two lists, then concat all dfs in the combined list.
    # note: snaps have standard_MI index, and additional data column 'snap_q' (in addition to 'quant');
    # snap_q gets moved into index in the groupby step below

    df = pd.concat(scenario_CA.snaps_CIR + scenario_QC.snaps_CIR, sort=False)
    mapping_dict = {'juris': 'CA-QC'}
    df = multiindex_change(df, mapping_dict)
    df = df.groupby(['snap_q'] + prmt.standard_MI_names).sum()
    snaps_CIR_CAQC_grouped = df

    supply_last_hist_yr_Q4 = str(prmt.supply_last_hist_yr)+'Q4'

    Q4_historical_quarters = pd.date_range(
        start=quarter_period('2013Q4').to_timestamp(),
        end=quarter_period(supply_last_hist_yr_Q4).to_timestamp() + DateOffset(years=1), 
        freq='A').to_period('Q')

    private_bank_paper = pd.Series()

    for quarter_year_period in Q4_historical_quarters:

        CIR_snap_q = turn_snap_into_CIR_for_private_bank_metric(quarter_year_period, snaps_CIR_CAQC_grouped)    
        
        if quarter_year_period.year == 2013:
            # fill in rows for offsets & early_action
            for column in CIR_snap_q.columns:
                CIR_snap_q.at['offsets', column] = float(0)
                CIR_snap_q.at['early_action', column] = float(0)

        else:
            # df already has row for offsets
            pass

        priv_offsets = CIR_snap_q.at['offsets', 'gen_comp']
        
        # sum non-vintaged allowances
        priv_nonvintage = sum([CIR_snap_q.at['APCR', 'gen_comp'], 
                               CIR_snap_q.at['early_action', 'gen_comp']])
        
        # sum vintaged allowances, of vintages <= year of metric
        df = CIR_snap_q.drop(['offsets', 'APCR', 'early_action'])
        df.index = df.index.astype(int)
        ser = df['gen_comp'].loc[:quarter_year_period.year]
        priv_vintaged = ser.sum()
        
        supply_toward_bank = sum([priv_vintaged, 
                                  priv_nonvintage,
                                  priv_offsets
                                 ])

        # fill in one year of obligations after end of historical data, based on user input
        # latest year with full historical supply data is usually 1 year ahead of latest year with emissions data
        # (full supply data known by following Jan., whereas covered emissions data not known until following Nov.)
        total_obligations_toward_bank = prmt.emissions_and_obligations.loc[:quarter_year_period.year][
            ['CA obligations', 'QC covered emissions']].sum(axis=1).sum()

        if quarter_year_period.year == prmt.supply_last_hist_yr:
            total_obligations_toward_bank += prmt.emissions_ann.loc[prmt.supply_last_hist_yr]
        else:
            # don't need to fill in banking metric for years that use historical emissions data
            pass
        
        # note: prmt.compliance_events is the actual quantities surrendered
        mask = prmt.compliance_events.index.get_level_values('compliance_date').year <= quarter_year_period.year
        fulfilled_toward_bank = prmt.compliance_events.loc[mask]['quant'].sum()

        # hard-coded: permanently_unfulfilled
        permanently_unfulfilled_dict = {2014: 0.029906, # for Lake Shore Mojave, LLC 
                                        2017: 3.767027, # for La Paloma bankruptcy
                                       }
        permanently_unfulfilled = pd.Series(permanently_unfulfilled_dict)
        permanently_unfulfilled_toward_bank = permanently_unfulfilled.loc[:quarter_year_period.year].sum()

        outstanding_obligations = sum([total_obligations_toward_bank, 
                                       -1 * fulfilled_toward_bank, 
                                       -1 * permanently_unfulfilled_toward_bank])

        private_bank_1y = supply_toward_bank - outstanding_obligations
        
        private_bank_paper.at[quarter_year_period.year] = private_bank_1y
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(private_bank_paper)
# end of private_bank_annual_metric_paper_method


# In[ ]:


def calculate_government_holding_metric(snaps_end_Q4_CA_QC):
    """
    Matches the method in the banking paper (Cullenward et al. 2019),
    
    Includes all allowances in government holding accounts, of vintages up to current year.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    df = snaps_end_Q4_CA_QC.copy()
    gov_hold_mask1 = df.index.get_level_values('acct_name').isin(['auct_hold', 'alloc_hold'])
    gov_hold_mask2 = df.index.get_level_values('vintage') <= df['snap_yr']
    gov_hold_mask = (gov_hold_mask1) & (gov_hold_mask2)
    df = df.loc[gov_hold_mask]
    df = df.groupby('snap_yr')['quant'].sum()
    df.name = 'gov_holding_allow'

    # for gov_holding, also get offsets in government holding accounts at the end of each year
    df2 = prmt.CIR_offsets_q_sums['Auction + Issuance + Allocation']
    df2 = df2.loc[df2.index.quarter==4]
    df2.index = df2.index.year
    df2.name = 'gov_holding_offsets'
    # for projection, assume zero offsets in gov holding
    
    # sum allowances (df) and offsets (df2)
    prmt.gov_holding = pd.concat([df, df2], axis=1).sum(axis=1)
    
    # only used for graphing
    prmt.gov_plus_private = pd.concat([prmt.gov_holding, prmt.bank_cumul], axis=1).sum(axis=1)
    
    # no return
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
# end of calculate_government_holding_metric


# In[ ]:


def compliance_period_metrics_historical():
    """
    Calculates Compliance Period metrics, following method in Near Zero's banking paper (Cullenward et al., 2019).
    
    This function handles only metrics for historical data, since there can be idiosyncrasies in historical data.
    
    (E.g., use of future vintages of allowances, making the Private Bank metric higher than it otherwise would be;
    This method of calculating metric does not include an adjustment for such use of future vintages.)
    
    This function processes year <= compliance_latest_year.
    
    The function compliance_period_metrics_historical processes year > compliance_latest_year.
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # initialization steps
    CP_metrics_hist = pd.DataFrame() # initialization
    events = prmt.compliance_events.copy() # used in later steps

    # use prmt.compliance_events to determine what compliance events have occurred historically at time of model run
    compliance_latest_year = prmt.compliance_events.index.get_level_values('compliance_date').unique().year.max()

    # create lists of final compliance events 
    # (the compliance events that, for CA, require satisfying all remaining obligations for a compliance period)
    Q3_before_final_compliance_events_historical = [] # initialize as empty list

    for year in [2015, 2018, 2021, 2024, 2027, 2030]:
        if year <= compliance_latest_year:
            # add to list Q3_before_final_compliance_events_historical
            Q3_before_final_compliance_events_historical += [str(year) + 'Q3']
        else:
            pass
    
    # create snaps_CIR_CAQC_grouped, used to convert to CIR_snap_q 
    df = pd.concat(scenario_CA.snaps_CIR + scenario_QC.snaps_CIR, sort=False)
    mapping_dict = {'juris': 'CA-QC'}
    df = multiindex_change(df, mapping_dict)
    df = df.groupby(['snap_q'] + prmt.standard_MI_names).sum()
    snaps_CIR_CAQC_grouped = df

    # iterate for each historical compliance period
    for quarter_year in Q3_before_final_compliance_events_historical:

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # formatting steps

        # convert to Period format
        quarter_year_period = quarter_period(quarter_year)

        # convert snaps into CIR format
        CIR_snap_q = turn_snap_into_CIR_for_private_bank_metric(quarter_year_period, snaps_CIR_CAQC_grouped)

        # for 2013, fill in rows for offsets & early_action
        if quarter_year_period.year == 2013:
            # fill in rows for offsets & early_action
            for column in CIR_snap_q.columns:
                CIR_snap_q.at['offsets', column] = float(0)
                CIR_snap_q.at['early_action', column] = float(0)
        else:
            # df already has rows for offsets & early_action
            pass

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Private Allowances CP metric

        # sum non-vintaged allowances
        priv_nonvintage = sum([CIR_snap_q.at['APCR', 'gen_comp'], 
                               CIR_snap_q.at['early_action', 'gen_comp']])

        # sum vintaged allowances, up to vintage 1 less than year of final compliance event
        ser = CIR_snap_q.drop(['offsets', 'APCR', 'early_action'], axis=0)
        ser.index = ser.index.astype(int) 
        ser = ser['gen_comp'].loc[:quarter_year_period.year-1]
        priv_vintaged = ser.sum()

        # Current and historical year allowances in private accounts, as of Q3 CIR 
        # (banking paper spreadsheet, sheet 'Metrics - CP', row 37)
        allow_curr = priv_vintaged + priv_nonvintage

        Q4_event = quarter_period(str(quarter_period(quarter_year).year)+'Q4')

        # calculate allowances surrendered in final compliance events
        # (banking paper spreadsheet, sheet 'Metrics - CP', row 38)
        event = events.loc[events.index.get_level_values('compliance_date')==Q4_event]
        event_allow = event.loc[event.index.get_level_values('vintage or type')!='offsets']
        event_allow_sum = event_allow['quant'].sum()

        # calculate future vintage allowances surrendered in final compliance events
        # (banking paper spreadsheet, sheet 'Metrics - CP', row 39)
        mask1 = event_allow.index.get_level_values('vintage or type') != 'offsets'
        mask2 = event_allow.index.get_level_values('vintage or type') != 'early_action'
        mask3 = event_allow.index.get_level_values('vintage or type') != 'APCR'
        mask = (mask1) & (mask2) & (mask3)
        df2 = event_allow.loc[mask]
        df2.index = df2.index.droplevel('compliance_date').astype(int)
        event_allow_future = df2.loc[Q4_event.year:]
        event_allow_future_sum = event_allow_future['quant'].sum()

        # Private Allowances CP metric
        # (banking paper spreadsheet, sheet 'Metrics - CP', row 41)
        private_allow = allow_curr - (event_allow_sum - event_allow_future_sum)

        CP_metrics_hist.at[quarter_year_period.year, 'Private Allowances'] = private_allow

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Private Offsets CP metric
        # (banking paper spreadsheet, sheet 'Metrics - CP', row 46)

        # Offsets in private accounts, as of Q3 CIR
        # (banking paper spreadsheet, sheet 'Metrics - CP', row 44)
        priv_offsets = CIR_snap_q.at['offsets', 'gen_comp']

        # calculate offsets surrendered in final compliance events
        # (banking paper spreadsheet, sheet 'Metrics - CP', row 45)
        event_offsets_sum = event.loc[event.index.get_level_values('vintage or type')=='offsets']['quant'].sum()

        private_offsets = priv_offsets - event_offsets_sum

        CP_metrics_hist.at[quarter_year_period.year, 'Private Offsets'] = private_offsets

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Private Instruments CP metric
        # (not included in banking paper)
        
        private_inst = private_allow + private_offsets
        
        CP_metrics_hist.at[quarter_year_period.year, 'Private Instruments'] = private_inst
        
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Government Allowances CP metric
        # (banking paper spreadsheet, sheet 'Metrics - CP', row 55)

        # sum vintaged allowances, up to vintage 1 less than year of final compliance event
        ser = CIR_snap_q.drop(['offsets', 'APCR', 'early_action'], axis=0)
        ser.index = ser.index.astype(int) 
        ser = ser['A_I_A'].loc[:quarter_year_period.year-1]
        gov_vintaged = ser.sum()

        # exclude gov nonvintaged; nonvintaged are generally only temporarily held, prior to transferring elsewhere

        CP_metrics_hist.at[quarter_year_period.year, 'Government Allowances'] = gov_vintaged

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Government Offsets CP metric
        # (banking paper spreadsheet, sheet 'Metrics - CP', row 58)
        gov_offsets = CIR_snap_q.at['offsets', 'A_I_A']

        CP_metrics_hist.at[quarter_year_period.year, 'Government Offsets'] = gov_offsets

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Reserve Accounts CP metric
        # (banking paper spreadsheet, sheet 'Metrics - CP', row 65)

        # sum all instruments in APCR account
        APCR_tot = CIR_snap_q['APCR_acct'].sum()

        APCR_tot_mod = APCR_tot # initialization; will be modified below

        # if prior to 2021, exclude APCR allowances from post-2020 budgets

        # for QC APCR:
        if quarter_year_period > quarter_period('2018Q1') and quarter_year_period < quarter_period('2021Q1'):
            # subtract QC APCR from budgets 2021-2030
            QC_APCR_2021_2030 = prmt.QC_APCR_MI.loc[prmt.QC_APCR_MI.index.get_level_values('vintage')>2020]['quant'].sum()
            APCR_tot_mod += -1 * QC_APCR_2021_2030
        else:
            pass

        # adjustment for APCR allowances temporarily held in government holding accounts
        if quarter_year_period == quarter_period('2018Q3'):
            # In 2018Q3 CIR, there was an anomaly in which 47,454 QC APCR allowances were temporarily stored 
            # in Gov Holding, on the way to being transferred to private accounts.
            # In the banking paper, these are attributed to the Reserve Accounts CP metric.
            APCR_tot_mod += 0.047454 # units MMTCO2e

        # adjust reserve accounts for reserve sales
        # Reserve Accounts CP metric based on quantity in the account as of Q3,
        # in a year with a final compliance event (e.g., 2021).
        # If we assume that reserve sales occur in Q4 (reserve sales held at end of December),
        # to make up for any deficit in normal instrument supplies, 
        # then the CP metric would be affected only by reserve sales up to the prior year (e.g., 2020Q4).
        reserve_sales_as_of_prior_yr = prmt.reserve_sales_excl_PCU.loc[quarter_year_period.year]
        APCR_tot_mod = APCR_tot_mod - reserve_sales_as_of_prior_yr
        
        if APCR_tot_mod < 0:
            PCU_sales_cumul = -1 * APCR_tot_mod
            APCR_tot_mod = float(0)
        else:
            pass
            
        # note: 
        # CP metrics for PCU_sales_cumul and reserve_sales_as_of_prior_yr 
        # are not currently included in export_df
       
        CP_metrics_hist.at[quarter_year_period.year, 'Reserve Accounts'] = APCR_tot_mod

    CP_metrics_hist = CP_metrics_hist.T

    CP_metrics_hist = CP_metrics_hist.rename(columns={2015: '2013-2014', 
                                            2018: '2015-2017'})

    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(CP_metrics_hist)
# end of compliance_period_metrics_historical


# In[ ]:


def compliance_period_metrics_projection():
    """
    Calculates Compliance Period metrics, following method in banking paper (Cullenward et al., 2019).
    
    This function handles only metrics for projected data, avoiding the idiosyncrasies with historical data.
        
    This function processes year > compliance_latest_year.
    
    The function compliance_period_metrics_historical processes year <= compliance_latest_year.    
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # initialization steps
    CP_metrics_proj = pd.DataFrame() # initialization
    events = prmt.compliance_events.copy() # historical only; used in later steps

    # use prmt.compliance_events to determine what compliance events have occurred historically at time of model run
    compliance_latest_year = prmt.compliance_events.index.get_level_values('compliance_date').unique().year.max()

    # create lists of final compliance events 
    # (the compliance events that, for CA, require satisfying all remaining obligations for a compliance period)
    Q3_before_final_compliance_events_projection = [] # initialize as empty list

    final_compliance_years = [2015, 2018, 2021, 2024, 2027, 2030]
    for year in final_compliance_years:
        if year > compliance_latest_year:
            # add to list Q3_before_final_compliance_events_projection
            Q3_before_final_compliance_events_projection += [str(year) + 'Q3']
        else:
            pass
    
    events_proj = pd.DataFrame() # initialize

    # calculate compliance surrenders for projection
    for year in range(2019, 2030+1):
        if year > compliance_latest_year:
            if year not in final_compliance_years:
                # for CA, annual obligation due
                CA_ann_surr = 0.3 * prmt.emissions_ann_CA.loc[year-1]
                events_proj.at[str(year)+'Q4', 'CA'] = CA_ann_surr

            else:
                # for CA, remainder of obligation due
                # for QC, total obligation due
                CA_final_surr = sum([0.7 * prmt.emissions_ann_CA.loc[year-3], 
                                     0.7 * prmt.emissions_ann_CA.loc[year-2], 
                                     1.0 * prmt.emissions_ann_CA.loc[year-1]])
                events_proj.at[str(year)+'Q4', 'CA'] = CA_final_surr

                QC_final_surr = sum([prmt.emissions_ann_QC.loc[year-3], 
                                     prmt.emissions_ann_QC.loc[year-2], 
                                     prmt.emissions_ann_QC.loc[year-1]])
                events_proj.at[str(year)+'Q4', 'QC'] = QC_final_surr
    events_proj['CA-QC'] = events_proj.sum(axis=1)
    
    # set index to use Period format
    events_proj.index = pd.to_datetime(events_proj.index).to_period('Q')

    # ------------------    
    # create snaps_CIR_CAQC_grouped
    df = pd.concat(scenario_CA.snaps_CIR + scenario_QC.snaps_CIR, sort=False)
    mapping_dict = {'juris': 'CA-QC'}
    df = multiindex_change(df, mapping_dict)
    df = df.groupby(['snap_q'] + prmt.standard_MI_names).sum()
    snaps_CIR_CAQC_grouped = df

    # iterate for each projection compliance period
    for quarter_year in Q3_before_final_compliance_events_projection:

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # formatting steps

        # convert to Period format
        quarter_year_period = quarter_period(quarter_year)

        # convert snaps into CIR format
        CIR_snap_allowances_before_retirements = turn_snap_into_CIR_for_private_bank_metric_projection(
            quarter_year_period, snaps_CIR_CAQC_grouped)

        # for 2013, fill in rows for early_action
        if quarter_year_period.year == 2013:
            for column in CIR_snap_allowances_before_retirements.columns:
                CIR_snap_allowances_before_retirements.at['early_action', column] = float(0)
        else:
            # df already has row for early_action
            pass
        
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # separate allowances into vintaged and non-vintaged

        df = CIR_snap_allowances_before_retirements.copy()
        df_vint = df.drop(['APCR', 'early_action'])
        df_vint.index = df_vint.index.astype(int)
            
        df_vint_up_to_prev_yr = df_vint.loc[:quarter_year_period.year-1]
        
        df_non_vint = df.loc[df.index.isin(['APCR', 'early_action'])]
        
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        
        # PRIVATE INSTRUMENTS:
        # total allowances in gen_comp, up to Q3 before compliance event of interest
        # (factors in historical retirements)
        
        priv_allow_vint = df_vint_up_to_prev_yr['gen_comp'].sum()
        
        priv_allow_nonvint = df_non_vint['gen_comp'].sum()
        
        private_allow_before_retirements_sum = priv_allow_vint + priv_allow_nonvint
        
        # allowances retired in all historical compliance events
        # (exclude offsets; remainder are allowances, vintaged and non-vintaged)
        allow_retired_hist_sum = events.loc[
            events.index.get_level_values('vintage or type')!='offsets']['quant'].sum()
        
        private_allow_after_hist_retire = private_allow_before_retirements_sum - allow_retired_hist_sum
        
        # total offsets in prmt.offsets_supply_q, up to Q3 before compliance event of interest
        # (does not factor in historical retirements)
        df = prmt.offsets_supply_q.copy()
        df = df.loc[df.index <= quarter_year_period]
        offsets_issued_sum = df.sum()
        
        # offsets surrendered in all historical compliance events
        # (banking paper spreadsheet, sheet 'Metrics - CP', row 45)
        offsets_retired_hist_sum = events.loc[
            events.index.get_level_values('vintage or type')=='offsets']['quant'].sum()
        
        private_offsets_after_hist_retire = offsets_issued_sum - offsets_retired_hist_sum
        
        # combine allowances and offsets
        private_inst_after_hist_retire = private_allow_after_hist_retire + private_offsets_after_hist_retire
        
        # calculate projected retirements (of allowances + offsets) through the final compliance event (Q4)
        compliance_cut_off = quarter_period(pd.to_datetime(quarter_year) + DateOffset(months=3))
        proj_retire = events_proj.loc[events_proj.index <= compliance_cut_off]['CA-QC']
        proj_retire_sum = proj_retire.sum()
        
        private_inst_bank = private_inst_after_hist_retire - proj_retire_sum
        
        CP_metrics_proj.at[quarter_year_period.year, 'Private Bank'] = private_inst_bank
        
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Government Allowances CP metric
        # (banking paper spreadsheet, sheet 'Metrics - CP', row 55)
        
        # note: these should not change over time, because in the idealization of projections, 
        # for scenarios in which all auctions sell out,
        # then all later allowances that could count toward this CP metric are already allocated or sold at auction

        # sum vintaged allowances, up to vintage 1 less than year of final compliance event
        gov_vintaged = df_vint_up_to_prev_yr['A_I_A'].sum()

        # exclude gov nonvintaged; nonvintaged are generally only temporarily held, prior to transferring elsewhere

        CP_metrics_proj.at[quarter_year_period.year, 'Government Allowances'] = gov_vintaged

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Government Offsets CP metric
        # (banking paper spreadsheet, sheet 'Metrics - CP', row 58)
        
        # assume it is zero for future years 
        # (that is, offsets are not stored temporarily in government holding accounts)
        gov_offsets = float(0)
        
        CP_metrics_proj.at[quarter_year_period.year, 'Government Offsets'] = gov_offsets

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Reserve Accounts CP metric
        # (banking paper spreadsheet, sheet 'Metrics - CP', row 65)

        # sum all instruments in APCR account
        APCR_tot = CIR_snap_allowances_before_retirements['APCR_acct'].sum()

        APCR_tot_mod = APCR_tot # initialization; will be modified below

        # adjust reserve accounts for reserve sales
        # Reserve Accounts CP metric based on quantity in the account as of Q3,
        # in a year with a final compliance event (e.g., 2021).
        # If we assume that reserve sales occur in Q4 (reserve sales held at end of December),
        # to make up for any deficit in normal instrument supplies, 
        # then the CP metric would be affected only by reserve sales up to the prior year (e.g., 2020Q4).       
        prior_yr = quarter_year_period.year - 1
        reserve_sales_as_of_prior_yr = prmt.reserve_sales_excl_PCU.loc[prior_yr]
        APCR_tot_mod = APCR_tot_mod - reserve_sales_as_of_prior_yr
        
        # if reserve sales (cumul.) exceed reserves, zero out reserves
        # if reserve sales (cumul.) exceed reserves, create price ceiling unit sales
        if APCR_tot_mod < 0:
            PCU_sales_cumul = -1 * APCR_tot_mod
            APCR_tot_mod = float(0)
        else:
            pass       
            
        # note: 
        # CP metrics for PCU_sales_cumul and reserve_sales_as_of_prior_yr 
        # are not currently included in export_df
            
        CP_metrics_proj.at[quarter_year_period.year, 'Reserve Accounts'] = APCR_tot_mod

    CP_metrics_proj = CP_metrics_proj.T

    CP_metrics_proj = CP_metrics_proj.rename(columns={2021: '2018-2020', 
                                                      2024: '2021-2023', 
                                                      2027: '2024-2026', 
                                                      2030: '2027-2029'})
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(CP_metrics_proj)
# end of compliance_period_metrics_projection


# In[ ]:


def compile_annual_metrics_for_export():
    """
    Compiles annual banking metrics (e.g., Private Bank) and other annual metrics (e.g., Reserve Sales).
    
    Puts into a single DataFrame, annual_metrics, which is progressively appended to with later functions,
    to add Compliance Period metrics and metadata, and then reformatted for downloading through the user interface.
    
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # create empty DataFrame (which will be filled in with data by this function)
    empty_index = list(range(2013, 2030+1))
    empty_columns = ['Annual data and banking metrics']
    empty_df = pd.DataFrame(index=empty_index, columns=empty_columns)
    empty_df = empty_df.fillna(' ')
    
    caps_export = pd.concat([prmt.CA_cap, prmt.QC_cap], axis=1, sort=True).sum(axis=1)
    caps_export.name = 'California + Quebec caps (annual)'
    
    emissions_export = prmt.emissions_ann.copy()
    emissions_export.name = 'Covered Emissions (annual)'
    
    obligations_export = prmt.CA_QC_obligations_fulfilled_hist_proj.copy()
    obligations_export.name = 'Compliance Obligations (annual)'
    
    supply_export = prmt.supply_ann.copy()
    supply_export.name = 'Private Supply (annual additions) [excludes sales of Reserves and Price Ceiling Units]'
    
    bank_export = prmt.bank_cumul.copy()
    bank_export.name = 'Private Bank (cumulative)'
    
    unsold_export = prmt.unsold_auct_hold_cur_sum.copy()
    unsold_export.name = 'Unsold Allowances (cumulative)'
    
    reserve_sales_export = prmt.reserve_sales_excl_PCU.copy()
    reserve_sales_export.name = 'Reserve Sales (cumulative)'
    # note reserve_sales used here exclude Price Ceiling Unit (PCU) sales
    
    PCU_sales_cumul_export = prmt.PCU_sales_cumul
    PCU_sales_cumul_export.name = 'Price Ceiling Unit Sales (cumulative)'
    
    reserve_accts_export = prmt.reserve_accts.copy()
    reserve_accts_export.name = 'Reserve Accounts (cumulative)'
    
    gov_holding_export = prmt.gov_holding.copy()
    gov_holding_export.name = 'Government Holding Accounts (cumulative)'
    
    annual_metrics = pd.concat(
        [empty_df, 
         caps_export, 
         emissions_export, 
         obligations_export,
         supply_export,
         bank_export,
         # unsold_export, # no longer exporting
         gov_holding_export,
         reserve_sales_export,
         PCU_sales_cumul_export,
         reserve_accts_export,
        ], 
        axis=1)
    annual_metrics = annual_metrics.fillna(0)
    annual_metrics.index.name = 'year'
    
    # transpose df
    annual_metrics = annual_metrics.T
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(annual_metrics)
# end of compile_annual_metrics_for_export


# In[ ]:


def compile_compliance_period_metrics_for_export():
    """
    Compiles and reorganizes data for Compliance Period metrics for Private Bank, etc.
    
    Runs sub-functions compliance_period_metrics_historical and compliance_period_metrics_projection.
    
    Runs within function create_export_df.
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")

    # historical
    CP_metrics_hist = compliance_period_metrics_historical()

    # projection
    CP_metrics_proj = compliance_period_metrics_projection()

    # combine historical & projection
    CP_metrics_all = pd.concat([CP_metrics_hist, CP_metrics_proj], axis=1, sort=False)

    # for historical metrics, fill in Private Bank values (sum of Private Allowances and Private Offsets)
    CP_metrics_all.at['Private Bank', '2013-2014'] = sum(
        [CP_metrics_all.at['Private Allowances', '2013-2014'], 
         CP_metrics_all.at['Private Offsets', '2013-2014']])

    CP_metrics_all.at['Private Bank', '2015-2017'] = sum(
        [CP_metrics_all.at['Private Allowances', '2015-2017'],
         CP_metrics_all.at['Private Offsets', '2015-2017']])
    
    # for Private Bank, zero out negative values
    # (when Private Bank is exhausted, there must be reserve sales, and perhaps also Price Ceiling Unit sales)
    # (reserve & PCU sales not shown in Compliance Period metrics)
    for column in CP_metrics_all.columns:
        if CP_metrics_all.at['Private Bank', column] < 0:
            # zero out the value; bank can't be negative
            # there must be reserve sales; those aren't tracked explicitly in CP metrics,
            # but quantities remaining in reserve accounts are tracked
            CP_metrics_all.at['Private Bank', column] = float(0)

            CP_metrics_all.at['Private Bank', column] = float(0)
        else:
            pass
    
    # reorder rows
    CP_metrics_index_order = ['Private Allowances', 'Private Offsets', 'Private Bank', 
                              'Government Allowances', 'Government Offsets', 'Reserve Accounts',
                             ]
    
    CP_metrics_all = CP_metrics_all.reindex(CP_metrics_index_order)
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # rename index entries to add "(cumulative)" where relevant
    
    index_list = list(CP_metrics_all.index)

    index_list_new = []
    for item in index_list:
        if item in ['Private Allowances', 'Private Offsets', 'Private Bank', 
                    'Government Allowances', 'Government Offsets', 'Reserve Accounts']:
            index_list_new += [str(item)+ ' (cumulative)']
            
        else:
            index_list_new += [item]

    CP_metrics_all.index = index_list_new
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # create empty DataFrame (which will be filled in with data by this function)
    df = pd.DataFrame(
        [['2013-2014', '   '], 
         ['2015-2017', '   '], 
         ['2018-2020', '   '], 
         ['2021-2023', '   '], 
         ['2024-2026', '   '], 
         ['2027-2029', '   ']], 
        index=['2013-2014', '2015-2017', '2018-2020', '2021-2023', '2024-2026', '2027-2029'])
    df = df.T
    df = df.reindex(['   ', 'Compliance Period banking metrics'])
    
    # put data from above into empty df
    df = df.append(CP_metrics_all, sort=False)
    
    # place each CP metric under the year in which the final compliance event occurred for that period
    # (e.g., final compliance event for CP2 (2015-2017) was Nov 1, 2018)
    # this is because CP metrics use data through Q3 of the year of the final compliance event
    df = df.rename(columns={
        '2013-2014': 2015, 
        '2015-2017': 2018, 
        '2018-2020': 2021, 
        '2021-2023': 2024, 
        '2024-2026': 2027, 
        '2027-2029': 2030})
    
    CP_metrics = df   
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    return(CP_metrics)
# end of compile_compliance_period_metrics_for_export


# ## Functions: User interface

# In[ ]:


def progress_bars_initialize_and_display():
    """
    Sets initial value of progress bars that show model processing quarters for CA & QC, then displays the bars.
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # for CA, create progress bar using iPython widget IntProgress
    # at end of each quarter, value increases by 1
    prmt.progress_bar_CA_count = 0 # reinitialize widget progress bar count
    progress_bar_CA.wid.value = prmt.progress_bar_CA_count
    progress_bar_CA.wid.max = len(prmt.CA_quarters)
    
    display(progress_bar_CA.wid) # display the bar

    # for QC, create progress bar using iPython widget IntProgress
    # at end of each quarter, value increases by 1
    prmt.progress_bar_QC_count = 0 # reinitialize widget progress bar
    progress_bar_QC.wid.value = prmt.progress_bar_QC_count
    progress_bar_QC.wid.max = len(prmt.QC_quarters)

    display(progress_bar_QC.wid) # display the bar
    
    # note: bars' values are updated at end of each step through loop
            
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
# end of progress_bars_initialize_and_display


# In[ ]:


def create_emissions_pct_sliders():
    """
    Create sliders that are used for user inputs of parameters for emissions projections.
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # extract each juris as a Series
    CA_em_hist = prmt.emissions_and_obligations['CA covered emissions'].dropna()
    QC_em_hist = prmt.emissions_and_obligations['QC covered emissions'].dropna()
    
    CA_em_hist_last_yr = CA_em_hist.index.max()
    QC_em_hist_last_yr = QC_em_hist.index.max()
    
    # check whether the data series make sense
    if CA_em_hist_last_yr == QC_em_hist_last_yr:
        prmt.emissions_last_hist_yr = CA_em_hist_last_yr
    elif CA_em_hist_last_yr == QC_em_hist_last_yr+1:
        # California's latest historical data for covered emissions is a year ahead of Quebec's
        prmt.emissions_last_hist_yr = min(CA_em_hist_last_yr, QC_em_hist_last_yr)
    elif QC_em_hist_last_yr == CA_em_hist_last_yr+1:
        # Quebec's latest historical data for covered emissions is a year ahead of California's
        prmt.emissions_last_hist_yr = min(CA_em_hist_last_yr, QC_em_hist_last_yr)
    else:
        print("There is a problem with historical data for covered emissions.") # for UI
        print(f"From input sheet, California's historical data is through {CA_em_hist_last_yr} and Quebec's is through {QC_em_hist_last_yr}.") # for UI
        prmt.emissions_last_hist_yr = min(CA_em_hist_last_yr, QC_em_hist_last_yr)
    
    # ~~~~~~~~~~~~~~~~~~~~
    # simple
    # create slider widgets as attributes of objects defined earlier
    em_pct_CA_simp.slider = widgets.FloatSlider(value=-0.02, min=-0.07, max=0.03, step=0.001,
                                                description=f"{prmt.emissions_last_hist_yr+1}-2030",
                                                continuous_update=False, 
                                                readout_format='.1%'
                                               )

    em_pct_QC_simp.slider = widgets.FloatSlider(value=-0.02, min=-0.07, max=0.03, step=0.001,
                                                description=f"{prmt.emissions_last_hist_yr+1}-2030", 
                                                continuous_update=False, 
                                                readout_format='.1%'
                                               )
    # ~~~~~~~~~~~~~~~~~~~~
    # advanced
    # create slider widgets as attributes of objects defined earlier
    
    description_em1 = '' # initialize
    description_em2 = '' # initialize
    description_em3 = '' # initialize
    
    if prmt.emissions_last_hist_yr+1 < 2020:
        start_yr = max(2013, prmt.emissions_last_hist_yr+1)
        description_em1 = f"{start_yr}-2020"
    elif prmt.emissions_last_hist_yr+1 == 2020:
        description_em1 = "2020"
    else:
        pass
    
    if prmt.emissions_last_hist_yr+1 < 2025:
        start_yr = max(2021, prmt.emissions_last_hist_yr+1)
        description_em2 = f"{start_yr}-2025"
    elif prmt.emissions_last_hist_yr+1 == 2025:
        description_em2 = "2025"
    else:
        pass
    
    if prmt.emissions_last_hist_yr+1 < 2030:
        start_yr = max(2026, prmt.emissions_last_hist_yr+1)
        description_em3 = f"{start_yr}-2030"
    elif prmt.emissions_last_hist_yr+1 == 2030:
        description_em3 = "2030"
    else:
        pass
    
    em_pct_CA_adv1.slider = widgets.FloatSlider(value=-0.02, min=-0.07, max=0.03, step=0.001,
                                                description=description_em1, 
                                                continuous_update=False, 
                                                readout_format='.1%')
    em_pct_CA_adv2.slider = widgets.FloatSlider(value=-0.02, min=-0.07, max=0.03, step=0.001,
                                                description=description_em2,
                                                continuous_update=False, 
                                                readout_format='.1%')
    em_pct_CA_adv3.slider = widgets.FloatSlider(value=-0.02, min=-0.07, max=0.03, step=0.001,
                                                description=description_em3, 
                                                continuous_update=False, 
                                                readout_format='.1%')

    em_pct_QC_adv1.slider = widgets.FloatSlider(value=-0.02, min=-0.07, max=0.03, step=0.001, 
                                                description=description_em1,
                                                continuous_update=False, 
                                                readout_format='.1%')
    em_pct_QC_adv2.slider = widgets.FloatSlider(value=-0.02, min=-0.07, max=0.03, step=0.001,
                                                description=description_em2,
                                                continuous_update=False, 
                                                readout_format='.1%')
    em_pct_QC_adv3.slider = widgets.FloatSlider(value=-0.02, min=-0.07, max=0.03, step=0.001,
                                                description=description_em3,
                                                continuous_update=False, 
                                                readout_format='.1%')
    # no return
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
# end of create_emissions_pct_sliders


# In[ ]:


def parse_emissions_text(text_input):
    """
    If user inputs custom emissions pathway, this function parses the text pasted in.
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # strip spaces from ends of text input:
    text_input = text_input.strip()
    
    if '\t' in text_input:
        text_input = text_input.split(' ')
        text_input = [x.replace(',', '') for x in text_input] #  if ',' in x]
        text_input = [x.replace('\t', ', ') for x in text_input] #  if '\t' in x]

        df = pd.DataFrame([sub.split(', ') for sub in text_input])
        
        if len(df.columns) > 2:
            # may be that the two columns copied and pasted were not adjacent
            # if there are column that are all NaN, drop them
            df = df.replace('', np.NaN)
            df = df.dropna(axis=1, how='all')  
        else:
            # continue with steps below
            pass
        
        if len(df.columns) == 2:

            if df.columns[0] == 0:
                try:
                    df.columns = ['year', 'emissions_ann']

                except:
                    error_msg = "Error" + "! Custom emissions data may have formatting problem. Reverting to default of -2%/year."
                    print(error_msg) # for UI
                    logging.info(error_msg)
                    prmt.error_msg_post_refresh += [error_msg]
                    custom = 'misformatted'
            else:
                pass
                
            # in case year col was formatted with decimal places, remove them to get int
            df['year'] = df['year'].str.split('.').str[0]

            try:
                int(df.loc[0, 'year'])
            except:
                df = df.drop(0) # drops row

            try:
                df['year'] = df['year'].astype(int)
                df = df.set_index('year')

                try:
                    df['emissions_ann'] = df['emissions_ann'].astype(float)
                    custom = df['emissions_ann']
                except:
                    error_msg = "Error" + "! Custom emissions data may have formatting problem. Reverting to default of -2%/year."
                    print(error_msg) # for UI
                    logging.info(error_msg)
                    prmt.error_msg_post_refresh += [error_msg]
                    custom = 'misformatted'

            except:
                error_msg = "Error" + "! Custom auction may have formatting problem. Reverting to default of -2%/year."
                print(error_msg) # for UI
                logging.info(error_msg)
                prmt.error_msg_post_refresh += [error_msg]
                custom = 'misformatted'

            try:
                if custom.mean() > 1000 or custom.mean() < 50:
                    error_msg = "Warning" + "! The emissions data might not have units of MMTCO2e."
                    print(error_msg) # for UI
                    logging.info(error_msg)
                    prmt.error_msg_post_refresh += [error_msg]
                    # no change to custom

            except:
                print("Warning! Was not able to check whether data is realistic.")
            
                
        else: # len(df.columns) != 2
            error_msg = "Error" + "! Custom emissions data may have formatting problem. Reverting to default of -2%/year."
            print(error_msg) # for UI
            logging.info(error_msg)
            prmt.error_msg_post_refresh += [error_msg]
            custom = 'misformatted'
                
    # continuation of if '\t' in text_input
    elif text_input == '':
        # will lead to error msg and revert to default inside fn emissions_projection
        error_msg = "Error" + "! Custom auction data was blank. Reverting to default of -2%/year."
        print(error_msg) # for UI
        logging.info(error_msg)
        prmt.error_msg_post_refresh += [error_msg]
        custom = 'blank'

    else: # if '\t' not in text_input:
        error_msg = "Error" + "! Problem with custom data (possibly formatting problem). Reverting to default of -2%/year."
        print(error_msg) # for UI
        logging.info(error_msg)
        prmt.error_msg_post_refresh += [error_msg]

        # override text_input value, for triggering default calculation in fn emissions_projection
        custom = 'missing_slash_t'

    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(custom)
# end of parse_emissions_text


# In[ ]:


def create_offsets_pct_sliders():
    """
    Default for CA & QC in period 2019-2020 is based on historical average calculated for 2013-2017.
    (See variable prmt.offset_rate_fract_of_limit_default.)
    
    Defaults for CA in 2021-2025 & 2026-2030 are based on ARB assumption in Post-2020 analysis.
    
    In advanced settings, Period 1: 2019-2020; Period 2: 2021-2025; Period 3: 2026-2030
    
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # calculate first projection quarter for offsets
    offset_last_hist_q = prmt.CIR_historical.index.get_level_values('date').max().to_timestamp()
    offset_first_proj_q = pd.to_datetime(offset_last_hist_q + DateOffset(months=3)).to_period('Q')
    
    # ~~~~~~~~~~~~~~~~~~~~
    
    # simple
    # create slider widget as attribute of object defined earlier
    off_pct_of_limit_CAQC.slider = widgets.FloatSlider(
        value=prmt.offset_rate_fract_of_limit_default, 
        min=0, max=1.0, step=0.01,
        description=f"{str(offset_first_proj_q)}-2030", continuous_update=False, readout_format='.0%')
    
    # use ARB assumption for all years 2019-2030, which fits with hist data
    # this default can be based on the values in advanced settings below, 
    # but then also depend on emissions projection, because it will be an average over the whole period 2019-2030

    # ~~~~~~~~~~~~~~~~~~~~
    
    description_off1 = '' # initialize 
    description_off2 = '' # initialize 
    description_off3 = '' # initialize 
    
    if offset_first_proj_q.year < 2020:
        start_q = max(quarter_period('2013Q1'), offset_first_proj_q)
        description_off1 = f"{start_q}-2020"
    elif offset_first_proj_q >= quarter_period('2020Q1') and offset_first_proj_q < quarter_period('2020Q4'):
        start_q = max(quarter_period('2013Q1'), offset_first_proj_q)
        description_off1 = f"{start_q}-2020Q4"
    elif offset_first_proj_q == quarter_period('2020Q4'):
        description_off1 = "2020Q4"
    else:
        pass
    
    if offset_first_proj_q.year < 2021:
        description_off2 = "2021-2025"
    elif offset_first_proj_q.year >= 2021 and offset_first_proj_q.year <= 2025:
        if offset_first_proj_q.year < 2025:
            start_q = max(quarter_period('2021Q1'), offset_first_proj_q)
            description_off2 = f"{start_q}-2025"
        elif offset_first_proj_q >= quarter_period('2025Q1') and offset_first_proj_q < quarter_period('2025Q4'):
            start_q = max(quarter_period('2021Q1'), offset_first_proj_q)
            description_off2 = f"{start_q}-2025Q4"
        elif offset_first_proj_q == quarter_period('2025Q4'):
            description_off2 = "2025Q4"
        else:
            pass
    
    if offset_first_proj_q.year < 2026:
        description_off3 = "2026-2030"
    elif offset_first_proj_q.year >= 2026 and offset_first_proj_q.year <= 2030:
        if offset_first_proj_q.year < 2030:
            start_q = max(quarter_period('2026Q1'), offset_first_proj_q)
            description_off3 = f"{start_q}-2030"                
        elif offset_first_proj_q >= quarter_period('2030Q1') and offset_first_proj_q < quarter_period('2030Q4'):
            start_q = max(quarter_period('2026Q1'), offset_first_proj_q)
            description_off3 = f"{start_q}-2030Q4"
        elif offset_first_proj_q == quarter_period('2030Q4'):
            description_off3 = "2030Q4"
        else:
            pass
    
    # advanced
    # create slider widgets as attributes of objects defined earlier   
    off_pct_CA_adv1.slider = widgets.FloatSlider(
        value=0.08*prmt.offset_rate_fract_of_limit_default, 
        # for period 1, default based on historical data for WCI; legal limit is 8%
        min=0.0, max=0.10, step=0.001,
        description=description_off1, readout_format='.1%', continuous_update=False)
    
    off_pct_CA_adv2.slider = widgets.FloatSlider(
        value=0.04*prmt.offset_rate_fract_of_limit_default, 
        # CA legal limit in period 2 is 4%
        min=0.0, max=0.10, step=0.001, 
        description=description_off2, readout_format='.1%', continuous_update=False)
    
    off_pct_CA_adv3.slider = widgets.FloatSlider(
        value=0.06*prmt.offset_rate_fract_of_limit_default, 
        # CA legal limit in period 3 is 6%
        min=0.0, max=0.10, step=0.001, 
        description=description_off3, readout_format='.1%', continuous_update=False)

    off_pct_QC_adv1.slider = widgets.FloatSlider(
        value=0.08*prmt.offset_rate_fract_of_limit_default, 
        # for period 1, default based on historical data for WCI; legal limit is 8%
        min=0.0, max=0.10, step=0.001, 
        description=description_off1, readout_format='.1%', continuous_update=False)
    
    off_pct_QC_adv2.slider = widgets.FloatSlider(
        value=0.08*prmt.offset_rate_fract_of_limit_default, 
        # QC legal limit in period 2 is 8%
        min=0.0, max=0.10, step=0.001, 
        description=description_off2, readout_format='.1%', continuous_update=False)

    off_pct_QC_adv3.slider = widgets.FloatSlider(
        value=0.08*prmt.offset_rate_fract_of_limit_default, 
        # QC legal limit in period 3 is 8%
        min=0.0, max=0.10, step=0.001, 
        description=description_off3, readout_format='.1%', continuous_update=False)
    
    # no return
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
# end of create_offsets_pct_sliders


# In[ ]:


def create_figures():
    """
    Creates the two figures shown in the user interface:
    * 'Emissions & instrument supplies (annual)'
    * 'Private Bank & Government Holdings (cumulative)'
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # ~~~~~~~~~~~~~~~~~~~~~
    
    # Figure 1. CA-QC emissions vs. instrument supplies & cap
    p1 = figure(title='Emissions & instrument supplies (annual)',
                height = 500, width = 600,
                x_range=(2012.5, 2030.5),
                y_range=(0, 550),
                tools='save',
               )

    p1.yaxis.axis_label = "MMTCO2e / year"
    p1.xaxis.major_label_standoff = 10
    p1.xaxis.minor_tick_line_color = None
    p1.yaxis.minor_tick_line_color = None
    p1.outline_line_color = "white"
    p1.min_border_right = 15
    p1.title.text_font_size = "16px"
    
    cap_CAQC = pd.concat([prmt.CA_cap, prmt.QC_cap], axis=1).sum(axis=1)
    cap_CAQC_line = p1.line(cap_CAQC.index, cap_CAQC, color='DarkGray', line_width=3.5)
    
    # use prmt.supply_last_hist_yr for identifying last year with full set of supply data
    sup_off_CAQC_line_hist = p1.line(prmt.supply_ann.loc[:prmt.supply_last_hist_yr].index,
                                     prmt.supply_ann.loc[:prmt.supply_last_hist_yr], 
                                     color='mediumblue', line_width=3.5) 
    
    sup_off_CAQC_line_proj = p1.line(prmt.supply_ann.loc[prmt.supply_last_hist_yr:].index, 
                                     prmt.supply_ann.loc[prmt.supply_last_hist_yr:],
                                     color='dodgerblue', line_width=3.5, 
                                    )

    em_CAQC_line_hist = p1.line(prmt.emissions_ann.loc[:prmt.emissions_last_hist_yr].index,
                                prmt.emissions_ann.loc[:prmt.emissions_last_hist_yr],
                                color='orangered', line_width=3.5)
    
    em_CAQC_line_proj = p1.line(prmt.emissions_ann.loc[prmt.emissions_last_hist_yr:].index, 
                                prmt.emissions_ann.loc[prmt.emissions_last_hist_yr:],
                                color='orange', line_width=3.5, 
                               )
    
    legend = Legend(items=[
        (f'Covered emissions (historical, up to {prmt.emissions_last_hist_yr})', [em_CAQC_line_hist]),
        (f'Covered emissions (projection)', [em_CAQC_line_proj]),
        (f'Instrument supplies* (historical, up to {prmt.supply_last_hist_yr})', [sup_off_CAQC_line_hist]),
        (f'Instrument supplies* (projection)', [sup_off_CAQC_line_proj]),
        ('Caps', [cap_CAQC_line]),
        ('*Supplies exclude sales of Reserves and Price Ceiling Units', [])
    ],
                    label_text_font_size="14px",
                    location=(0, 0),
                    border_line_color=None)

    p1.add_layout(legend, 'below')

    em_CAQC_fig = p1
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Figure 2. CA-QC Private Bank and Government Holdings (cumul.) + reserve sales

    # set values of y_max & y_min:
    # create default values, and change if plotted values would go off the chart  
    
    # set y_max using gov_plus_private
    if prmt.gov_plus_private.max() > 700:
        y_max = (int(prmt.gov_plus_private.max() / 100) + 1) * 100
    else:
        y_max = 700 # default    
    
    # set y_min using prmt.reserve_PCU_sales_cumul
    # note: prmt.reserve_PCU_sales_cumul.min() is positive
    if prmt.reserve_PCU_sales_cumul.max() > 300:
        y_min = -1*(int(prmt.reserve_PCU_sales_cumul.max() / 100) + 1) * 100
    else:
        y_min = -300 # default
        
    # ~~~~~~
    p2 = figure(title='Private Bank & Government Holdings (cumulative)',
                height = 600, width = 700,
                x_range=(2012.5, 2030.5),
                y_range=(y_min, y_max),
                tools='save',
               )
    
    p2.xaxis.axis_label = "at end of each year"
    p2.xaxis.major_label_standoff = 10
    p2.xaxis.minor_tick_line_color = None
    
    p2.yaxis.axis_label = "MMTCO2e"   
    p2.yaxis.minor_tick_line_color = None
    
    p2.outline_line_color = "white"
    p2.min_border_right = 15
    p2.title.text_font_size = "16px"
    
    p2.xgrid.grid_line_color = None # hide vertical grid lines
    
    # ~~~~~~
    gov_vbar = p2.vbar(
        prmt.gov_plus_private.index,
        top=prmt.gov_plus_private,
        width=1,
        color='LightSkyBlue',
        line_width=1, line_color='dimgray'
    )
    bank_vbar = p2.vbar(
        prmt.bank_cumul.index,
        top=prmt.bank_cumul,
        width=1,
        color='CornflowerBlue',
        line_width=1, line_color='dimgray'
    )
    reserve_PCU_vbar = p2.vbar(
        prmt.reserve_PCU_sales_cumul.index,
        top=-1*prmt.reserve_PCU_sales_cumul, # change to negative values
        width=1,
        color='tomato',
        line_width=1, line_color='dimgray'
    )

    # ~~~~~~~~~~~~
    # Annotations:
    # add vertical line for divider between full historical data vs. projection (partial or full)    
    p2_historical_end = Span(location=prmt.emissions_last_hist_yr+0.5, 
                             dimension='height', 
                             line_color='black', line_dash='dashed', line_width=1)
    p2.add_layout(p2_historical_end)
    
    # Annotation Label for "historical" and "projection"
    horiz_displacement_paper = 0.5 # units: years; displacement in horizontal direction

    # calculate vertical placement of labels:
    
    # ALWAYS-BOTTOM METHOD:
    # using default y_min=-300 & y_max=700 (unless values exceeded), then place labels at bottom always
    displacement_factor_bottom = 0.04
    vertical_placement = y_min + displacement_factor_bottom*(y_max - y_min)
    
#     # AUTO-ADJUST METHOD:
#     # delete block of code below if not using; could put into notes about issue
#     # check if plotted data values are close to y_max
#     # if so, flip to bottom of graph
#     displacement_factor_auto = 0.08
#     max_values = prmt.gov_plus_private.loc[prmt.supply_last_hist_yr:prmt.supply_last_hist_yr+4].max()
#     if y_max - max_values > displacement_factor_auto*(y_max - y_min)+10:
#         vertical_placement = y_max - displacement_factor_auto*(y_max - y_min)
#     else:
#         if y_min < 0:
#             vertical_placement = y_min + displacement_factor_auto*(y_max - y_min)
#         else:
#             vertical_placement = 0
    
    citation1 = Label(x=prmt.emissions_last_hist_yr + 0.5 - horiz_displacement_paper, 
                      y=vertical_placement, 
                      text='historical', 
                      text_font_size="14px", 
                      text_align = 'right',
                     )

    citation2 = Label(x=prmt.emissions_last_hist_yr + 0.5 + horiz_displacement_paper, 
                      y=vertical_placement, 
                      text='projection', 
                      text_font_size="14px", 
                      text_align = 'left',
                     )

    p2.add_layout(citation1)
    p2.add_layout(citation2)
    
    # ~~~~~~~~~~~

    legend = Legend(items=[('Private Bank', [bank_vbar]),
                           ('Government Holding Accounts', [gov_vbar]),
                           ('Sales of Reserves & Price Ceiling Units', [reserve_PCU_vbar])
                          ],
                    location=(0, 0),
                    label_text_font_size="14px",
                    border_line_color=None)

    p2.add_layout(legend, 'below')

    bank_CAQC_fig_bar = p2

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Figure 1 & Figure 2

    prmt.fig_em_bank = gridplot([em_CAQC_fig, bank_CAQC_fig_bar], 
                                ncols=2, 
                                plot_width=450, plot_height=550,
                                toolbar_location='right',
                                toolbar_options={'logo': None},
                                merge_tools=True,
                               )
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    # no returns; sets object attribute prmt.fig_em_bank
# end of create_figures


# In[ ]:


def create_emissions_tabs():
    """
    Creates tabs for user interface for choosing type of input for emissions.
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # create the widgets (as attributes of objects)
    create_emissions_pct_sliders()
    
    # ~~~~~~~~~~~~~~~~~~
    # arrange emissions sliders (simple) & ui

    # set captions
    em_simp_caption_col0 = widgets.Label(value="California")
    em_simp_caption_col1 = widgets.Label(value="Québec")
    
    # create VBox with caption & slider
    em_simp_col0 = widgets.VBox([em_simp_caption_col0, em_pct_CA_simp.slider])
    em_simp_col1 = widgets.VBox([em_simp_caption_col1, em_pct_QC_simp.slider])

    # put each column into HBox
    emissions_simp_ui = widgets.HBox([em_simp_col0, em_simp_col1])
    
    # put whole set of captions + sliders into VBox with header
    year = prmt.emissions_last_hist_yr + 1
    em_simp_text = f"Choose the annual percentage change for each jurisdiction, for the projection ({year}-2030)."
    em_simp_header = widgets.Label(value=em_simp_text)
    emissions_simp_ui_w_header = widgets.VBox([em_simp_header, emissions_simp_ui])
    
    # ~~~~~~~~~~~~~~~~~~~
    # arrange emissions sliders (advanced) & ui

    # set captions
    em_adv_caption_col0 = widgets.Label(value="California")
    em_adv_caption_col1 = widgets.Label(value="Québec")

    # create lists for VBox
    em_adv_col0_list = [em_adv_caption_col0]
    em_adv_col1_list = [em_adv_caption_col1]

    if prmt.emissions_last_hist_yr < 2020:
        em_adv_col0_list = [em_pct_CA_adv1.slider]
        em_adv_col1_list = [em_pct_QC_adv1.slider]
    else:
        pass
        
    if prmt.emissions_last_hist_yr < 2025:
        em_adv_col0_list += [em_pct_CA_adv2.slider]
        em_adv_col1_list += [em_pct_QC_adv2.slider]

    else:
        pass
    
    if prmt.emissions_last_hist_yr < 2030:
        em_adv_col0_list += [em_pct_CA_adv3.slider]
        em_adv_col1_list += [em_pct_QC_adv3.slider]
    else:
        pass
        
    em_adv_col0 = widgets.VBox(em_adv_col0_list)
    em_adv_col1 = widgets.VBox(em_adv_col1_list)

    # put each column into HBox
    emissions_adv_ui = widgets.HBox([em_adv_col0, em_adv_col1])
    
    # put whole set of captions + sliders into VBox with header
    em_adv_header = widgets.Label(value="Choose the annual percentage change for each jurisdiction, for each of the specified time spans.")
    emissions_adv_ui_w_header = widgets.VBox([em_adv_header, emissions_adv_ui])

    # ~~~~~~~~~~~~~~~~~~~~
    # custom emissions input

    em_text_input_CAQC_obj.wid = widgets.Text(
        value='',
        placeholder='Paste data here',
        # description='CA + QC:',
        disabled=False
    )

    em_text_input_CAQC_cap = widgets.Label(value="Enter annual emissions data (sum of California and Québec)")
    
    em_custom_footnote = widgets.HTML(value=em_custom_footnote_text)
    
    em_text_input_CAQC_ui = widgets.VBox([
        # caption_CA_QC_indiv, emissions_text_CA, emissions_text_QC, 
        em_text_input_CAQC_cap, em_text_input_CAQC_obj.wid, 
        em_custom_footnote
    ])
    
    # ~~~~~~~~~~~~~~~~~~~~
    
    tab = widgets.Tab()
    tab.children = [emissions_simp_ui_w_header, 
                    emissions_adv_ui_w_header, 
                    em_text_input_CAQC_ui]
    tab.set_title(0, 'simple')
    tab.set_title(1, 'advanced')
    tab.set_title(2, 'custom')
    
    emissions_tabs = tab
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(emissions_tabs)
# end of create_emissions_tabs


# In[ ]:


def create_auction_tabs():
    """
    Creates tabs for user interface for choosing type of input for auctions.
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # create auction settings: simple
    
    # create widget, which is just a text label; the user has no options
    cap1 = f"The default setting is that all future auctions (after {prmt.latest_hist_qauct_date}) sell out.<br>"
    cap2 = "To use this default assumption, leave this tab open."
    auction_simp_caption_col0 = widgets.HTML(value=cap1 + cap2)

    # put into ui
    auction_simp_ui = widgets.HBox([auction_simp_caption_col0])
    
    # ~~~~~~~~~~~~~~~~~~~
    # create auction settings: advanced
    auction_first_proj_date = pd.to_datetime(
        prmt.latest_hist_qauct_date.to_timestamp() + DateOffset(months=3)).to_period('Q')
    year_list = list(range(auction_first_proj_date.year, 2030+1))

    # create widgets for "years not sold out" and "% not sold" (as attributes of objects)
    years_not_sold_out_obj.wid = widgets.SelectMultiple(
        options=year_list,
        value=[],
        rows=len(year_list),
        description='years',
        disabled=False)
    
    fract_not_sold_obj.wid = widgets.FloatSlider(min=0.0, max=1.0, step=0.01,
                                                 description="% unsold", continuous_update=False, 
                                                 readout_format='.0%')
    
    # put widgets in boxes for ui & create final ui
    years_pct_HBox = widgets.HBox([years_not_sold_out_obj.wid, fract_not_sold_obj.wid])
    auction_adv_ui = widgets.VBox([years_pct_HBox])

    text1 = f"Choose particular years in which future auctions would have a portion of allowances go unsold (after the latest historical auction in {prmt.latest_hist_qauct_date}).<br>"
    text2 = "To select multiple years, hold down 'ctrl' (Windows) or 'command' (Mac), or to select a range of years, hold down Shift and click the start and end of the range.<br>"
    text3 = "Then use the slider to choose the percentage of allowances that go unsold in the auctions (both current and advance) in the years selected."
    auction_adv_ui_header_text = text1 + text2 + text3
    auction_adv_ui_header = widgets.HTML(value=auction_adv_ui_header_text)
    auction_adv_ui_w_header = widgets.VBox([auction_adv_ui_header, auction_adv_ui])
    
    # ~~~~~~~~~~~~~~~~~~~
    # format auction_tabs for simple & advanced
    
    children = [auction_simp_ui, auction_adv_ui_w_header]
    
    tab = widgets.Tab()
    tab.children = children
    tab.set_title(0, 'simple')
    tab.set_title(1, 'advanced')
    
    auction_tabs = tab
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(auction_tabs)
# end of create_auction_tabs


# In[ ]:


def create_offsets_tabs():
    """
    Creates tabs for user interface for choosing type of input for offsets.
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # create the sliders (as attributes of objects)
    create_offsets_pct_sliders()
    
    # ~~~~~~~~~~~~~~~~~~~
    # create offsets sliders (simple) & ui
    # uses slider: off_pct_of_limit_CAQC.slider
    off_simp_header = widgets.Label(value="Choose the offset supply, as a percentage of the limit that can be surrendered for compliance obligations arising in each year.")
    off_simp_caption = widgets.Label(value="California & Québec")
    off_simp_footer = widgets.Label(value="For California, the limits for each time period are 8% (2018-2020), 4% (2021-2025), and 6% (2026-2030). For Québec, the limit is 8% for all years.")
    off_simp_ui_w_header = widgets.VBox([off_simp_header, 
                                         off_simp_caption, 
                                         off_pct_of_limit_CAQC.slider, 
                                         off_simp_footer])

    # ~~~~~~~~~~~~~~~~~~~
    # create offsets sliders (advanced) & ui

    off_adv_header = widgets.Label(value=f"Choose the offset supply as a percentage of covered emissions, for each jurisdiction, for each time span.")

    off_adv_caption_col0 = widgets.Label(value="California")
    off_adv_caption_col1 = widgets.Label(value="Québec")

    off_adv_col0_list = [off_adv_caption_col0]
    off_adv_col1_list = [off_adv_caption_col1]

    if prmt.CIR_offsets_q_sums.index.max().year < 2020:
        off_adv_col0_list = [off_pct_CA_adv1.slider]
        off_adv_col1_list = [off_pct_QC_adv1.slider]
    else:
        pass
        
    if prmt.CIR_offsets_q_sums.index.max().year < 2025:
        off_adv_col0_list += [off_pct_CA_adv2.slider]
        off_adv_col1_list += [off_pct_QC_adv2.slider]
    else:
        pass
    
    if prmt.CIR_offsets_q_sums.index.max().year < 2030:
        off_adv_col0_list += [off_pct_CA_adv3.slider]
        off_adv_col1_list += [off_pct_QC_adv3.slider]
    else:
        pass
        
    off_adv_col0 = widgets.VBox(off_adv_col0_list)
    off_adv_col1 = widgets.VBox(off_adv_col1_list)
    
    off_adv_ui = widgets.HBox([off_adv_col0, off_adv_col1])

    off_adv_footer1 = widgets.Label(value="For California, the limits for each time period are 8% (2018-2020), 6% (2021-2025), and 4% (2026-2030). For Québec, the limit is 8% for all years.")
    off_adv_footer2 = widgets.Label(value="Warning: The sliders above may allow you to set offsets supply higher than the quantity that could be used through 2030. (See \"About carbon offsets\" below.)")
    
    off_adv_ui_w_header = widgets.VBox([off_adv_header, off_adv_ui, off_adv_footer1, off_adv_footer2])

    # ~~~~~~~~~~~~~~~~~~~~
    
    children = [off_simp_ui_w_header, 
                off_adv_ui_w_header]

    tab = widgets.Tab()
    tab.children = children
    tab.set_title(0, 'simple')
    tab.set_title(1, 'advanced')
    
    offsets_tabs = tab
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(offsets_tabs) 
# end of create_offsets_tabs


# In[ ]:


def compile_metadata_for_export():
    """
    Compiles metadata for export that explains the set-up for the model run, including:
    * model version
    * user settings for emissions, auctions, and offsets
    * warning messages
    
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    descrip_list = [] # initialize    
    metadata_list = [] # initialize
    metadata_list_of_tuples = [] # initialize
    
    descrip_list += ['WCI-RULES model version']
    metadata_list += [f'{prmt.model_version}']
    
    descrip_list += ['data input file version']
    metadata_list += [f'{prmt.data_input_file_version}']

    if emissions_tabs.selected_index == 0:        
        # user choice: simple emissions
        descrip_list += [
            f"emissions annual % change CA, {em_pct_CA_simp.slider.description}",
            f"emissions annual % change QC, {em_pct_QC_simp.slider.description}"
        ]
        metadata_list += [str(100*em_pct_CA_simp.slider.value)+'%', 
                          str(100*em_pct_QC_simp.slider.value)+'%']

    elif emissions_tabs.selected_index == 1:
        # user choice: advanced emissions
        if prmt.emissions_last_hist_yr+1 <= 2020:
            descrip_list += [f"emissions annual % change CA, {em_pct_CA_adv1.slider.description}", 
                             f"emissions annual % change QC, {em_pct_QC_adv1.slider.description}"]
            metadata_list += [str(100*em_pct_CA_adv1.slider.value)+'%', 
                              str(100*em_pct_QC_adv1.slider.value)+'%']
        else:
            pass
        if prmt.emissions_last_hist_yr+1 <= 2025:
            descrip_list += [f"emissions annual % change CA, {em_pct_CA_adv2.slider.description}", 
                             f"emissions annual % change QC, {em_pct_QC_adv2.slider.description}"]
            metadata_list += [str(100*em_pct_CA_adv2.slider.value)+'%', 
                              str(100*em_pct_QC_adv2.slider.value)+'%']
        else:
            pass
        if prmt.emissions_last_hist_yr+1 <= 2030:
            descrip_list += [f"emissions annual % change CA, {em_pct_CA_adv3.slider.description}", 
                             f"emissions annual % change QC, {em_pct_QC_adv3.slider.description}"]
            metadata_list += [str(100*em_pct_CA_adv3.slider.value)+'%', 
                              str(100*em_pct_QC_adv3.slider.value)+'%']
        else:
            pass

    elif emissions_tabs.selected_index == 2:
        # user choice: custom emissions
        descrip_list += ['custom emissions']
        metadata_list += ['see values above']

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    if auction_tabs.selected_index == 0:
        # user choice: simple auction (all sell out)
        descrip_list += [f'auctions: all future auctions after {prmt.latest_hist_qauct_date} sell 100%']
        metadata_list += ['']

    elif auction_tabs.selected_index == 1:
        descrip_list += ['auctions: years that did not sell out',
                         'auctions: % unsold']
        metadata_list += [list(years_not_sold_out_obj.wid.value),
                          str(100*fract_not_sold_obj.wid.value)+'%']

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    if offsets_tabs.selected_index == 0:
        # user choice: simple offsets
        descrip_list += [
            'offset supply as % of limit' # 'off_pct_of_limit_CAQC'
        ]
        metadata_list += [str(100*off_pct_of_limit_CAQC.slider.value)+'%']

    elif offsets_tabs.selected_index == 1:   
        # user choice: advanced offsets

        if prmt.off_proj_first_date.year <= 2020:
            # for CA & QC separately, for period 1 sliders
            descrip_list += [f"offset supply as % of emissions, CA {off_pct_CA_adv1.slider.description}", 
                             f"offset supply as % of emissions, QC {off_pct_QC_adv1.slider.description}"]
            metadata_list += [off_pct_CA_adv1.slider.value, 
                              off_pct_QC_adv1.slider.value]
        else:
            pass   
            
        if prmt.off_proj_first_date.year <= 2025:
            # for CA & QC separately, for period 2 sliders
            descrip_list += [f"offset supply as % of emissions, CA {off_pct_CA_adv2.slider.description}", 
                             f"offset supply as % of emissions, QC {off_pct_QC_adv2.slider.description}"]
            metadata_list += [off_pct_CA_adv2.slider.value, 
                              off_pct_QC_adv2.slider.value]
        else:
            pass
            
        if prmt.off_proj_first_date.year <= 2030:
            # for CA & QC separately, for period 3 sliders
            descrip_list += [f"offset supply as % of emissions, CA {off_pct_CA_adv3.slider.description}", 
                             f"offset supply as % of emissions, QC {off_pct_QC_adv3.slider.description}"]
            metadata_list += [off_pct_CA_adv3.slider.value, 
                              off_pct_QC_adv3.slider.value]
        else:
            pass

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # compile metadata_list_of_tuples
    for element_num in range(len(metadata_list)):
        metadata_list_of_tuples += [(descrip_list[element_num], metadata_list[element_num])]

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # add warning about excess offsets (if any)   
    if prmt.excess_offsets > 0:
        metadata_list_of_tuples += [("Scenario has excess offsets at end of 2030:", 
                                     f"{int(round(prmt.excess_offsets, 0))} MMTCO2e")]
    else:
        pass
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # add warning about reverting to default auctions
    
    for element_num in range(len(prmt.error_msg_post_refresh)):
        if 'No years selected for auctions with unsold allowances' in prmt.error_msg_post_refresh[element_num]:
            metadata_list_of_tuples += [("Warning"+ "! No years selected for auctions with unsold allowances",
                                         "Defaulted to scenario: all auctions sell out")]
        else:
            pass
        
        if 'Auction percentage unsold was set to zero' in prmt.error_msg_post_refresh[element_num]:
            metadata_list_of_tuples += [("Warning" + "! Auction percentage unsold was set to zero",
                                         "Defaulted to scenario: all auctions sell out")]
        else:
            pass
                             
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # rename column names so that append will work with main export_df 
    # first element in dictionary is to create empty row
    metadata_df = pd.DataFrame(pd.Series({'': '',
                                          'setting descriptions': 'setting values', 
                                          'units': 'million metric tons CO2-equivalent (MMtCO2e)',
                                         }), 
                               columns=[2013])
    metadata_df.index.name = 'year'
    
    metadata_data = pd.DataFrame(metadata_list_of_tuples, columns=['year', 2013])
    metadata_data = metadata_data.set_index('year')
    metadata_df = metadata_df.append(metadata_data)
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(metadata_df)
# end of compile_metadata_for_export


# In[ ]:


def create_export_df():
    """
    Creates DataFrame that is can be saved as a csv from the user interface.
    
    This output includes sections for:
    * Annual data and banking metrics
    * Compliance Period metrics
    * user settings that characterize the scenario
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
       
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # compile annual metrics 
    annual_metrics = compile_annual_metrics_for_export()

    # compile compliance period metrics
    CP_metrics = compile_compliance_period_metrics_for_export()

    # compile metadata
    metadata_df = compile_metadata_for_export()
    
    # create metadata_df from concat of above dfs
    export_df = pd.concat([annual_metrics, CP_metrics, metadata_df], sort=False)
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~    
    # FINAL FORMATTING STEPS
    # set attribute
    prmt.export_df = export_df
    
    prmt.js_download_of_csv = """
    var csv = '%s';
    
    var filename = '%s';
    var blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    if (navigator.msSaveBlob) { // IE 10+
        navigator.msSaveBlob(blob, filename);
    } else {
        var link = document.createElement("a");
        if (link.download !== undefined) { // feature detection
            // Browsers that support HTML5 download attribute
            var url = URL.createObjectURL(blob);
            link.setAttribute("href", url);
            link.setAttribute("download", filename);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    }
    """ % (prmt.export_df.to_csv(index=True).replace('\n','\\n').replace("'","\'"), 
           f'WCI-RULES_cap_and_trade_model_results_{prmt.save_timestamp}.csv')

    # no return
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
# end of create_export_df


# In[ ]:


def supply_demand_button_on_click(b):
    """
    Defines behavior when button "Run supply-demand calculations" is pressed.
    
    The function is run (the button is "clicked") in initializing model, then runs again when user clicks button.
    """
    # set new value of prmt.save_timestamp
    prmt.save_timestamp = time.strftime('%Y-%m-%d_%H%M%S', time.localtime())
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    logging.info("***********************************************")
    logging.info("start of new model run, with user settings")
    logging.info(f"prmt.save_timestamp: {prmt.save_timestamp}")
    logging.info("***********************************************")
    
    supply_demand_button.disabled = True
    supply_demand_button.style.button_color = '#A9A9A9'
    
    save_csv_button.disabled = True
    save_csv_button.style.button_color = '#A9A9A9'
    
    prmt.error_msg_post_refresh = [] # initialize
    
    if auction_tabs.selected_index == 0:       
        # then no custom auction; default to all sell out
        
        # reinitialize prmt values for years_not_sold_out & fract_not_sold
        prmt.years_not_sold_out = ()
        prmt.fract_not_sold = float(0)
        
        all_accts_CA, all_accts_QC = process_allowance_supply_CA_QC()
    
    elif auction_tabs.selected_index == 1:
        # then run custom auctions
        
        # set values in object prmt to be new values from user input
        # this sends the user settings to the model so they'll be used in processing auctions
        prmt.years_not_sold_out = years_not_sold_out_obj.wid.value
        prmt.fract_not_sold = fract_not_sold_obj.wid.value      
        
        if prmt.years_not_sold_out != () and prmt.fract_not_sold > 0:            
            # process new auctions
            # (includes initialize_all_accts and creation of progress bars)
            all_accts_CA, all_accts_QC = process_allowance_supply_CA_QC()
            
            # print("Finalizing results...") # for UI
            
        elif prmt.years_not_sold_out == ():            
            error_msg = "Warning" + "! No years selected for auctions with unsold allowances. Defaulted to scenario: all auctions sell out." # for UI
            logging.info(error_msg)
            prmt.error_msg_post_refresh += [error_msg]
            line_break = " "
            prmt.error_msg_post_refresh += [line_break]
            
            # reset prmt values for years_not_sold_out & fract_not_sold
            # prmt.years_not_sold_out = () # already true
            prmt.fract_not_sold = float(0)
            
        elif prmt.fract_not_sold == float(0):            
            error_msg = "Warning" + "! Auction percentage unsold was set to zero. Defaulted to scenario: all auctions sell out." # for UI
            logging.info(error_msg)
            prmt.error_msg_post_refresh += [error_msg]
            line_break = " "
            prmt.error_msg_post_refresh += [line_break]
            
            # reset prmt values for years_not_sold_out & fract_not_sold
            prmt.years_not_sold_out = ()
            # prmt.fract_not_sold = float(0) # already true
            
        else:            
            error_msg = "Warning" + "! Unknown error. Defaulted to scenario: all auctions sell out." # for UI
            logging.info(error_msg)
            prmt.error_msg_post_refresh += [error_msg]
            line_break = " "
            prmt.error_msg_post_refresh += [line_break]
            
            # reset prmt values for years_not_sold_out & fract_not_sold
            prmt.years_not_sold_out = ()
            prmt.fract_not_sold = float(0)
    
    supply_demand_calculations()

    # create & display new graph, using new data
    create_figures()

    # clear output of this cell (button and old graph)
    clear_output(wait=True)
    
    show(prmt.fig_em_bank)  
    
    # enable run button and change color
    supply_demand_button.style.button_color = 'PowderBlue'
    supply_demand_button.disabled = False

    # enable save button and change color
    save_csv_button.style.button_color = 'PowderBlue'
    save_csv_button.disabled = False
    
    # display buttons again
    display(widgets.HBox([supply_demand_button, save_csv_button]))
    
    if prmt.error_msg_post_refresh != []:
        for element in prmt.error_msg_post_refresh:
            print(element) # for UI
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
# end of supply_demand_button_on_click


# In[ ]:


def save_csv_on_click(b):
    """
    Defines behavior when user clicks "Save results & settings (csv)" button.
    """
    logging.info(f"{inspect.currentframe().f_code.co_name}")
    
    save_csv_button.style.button_color = '#A9A9A9'
    save_csv_button.disabled = True

    display(Javascript(prmt.js_download_of_csv))
# end of save_csv_on_click


# #### end of functions

# # START OF MODEL RUN

# In[ ]:


logging.info("WCI-RULES model log")
logging.info("***********************************************")
logging.info("start of new model run, with default settings")
logging.info(f"prmt.save_timestamp: {prmt.save_timestamp}")
logging.info("***********************************************")

# run functions to download files
load_input_files()

# set CA_cap_data
# retain this (rather than using read_excel repeatedly on this sheet) 
# because with openpyxl, if the same sheet is read twice, it seems to set the data to be blank
df = pd.read_excel(prmt.input_file, sheet_name='CA cap data')

# drop all rows completely empty; empty rows may be caused by openpyxl
df = df.dropna(how='all')

prmt.CA_cap_data = df

logging.info("read input sheet 'CA cap data'")

# set CA_cap_adjustment_factor
ser = prmt.CA_cap_data[prmt.CA_cap_data['name']=='CA_cap_adjustment_factor'].set_index('year')['data']
prmt.CA_cap_adjustment_factor = ser

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~

# set prmt.EIM_and_bankruptcy
# added this (rather than using read_excel repeatedly on this sheet) 
# because with openpyxl, if the same sheet is read twice, it seems to set the data to be blank
df = pd.read_excel(prmt.input_file, sheet_name='EIM & bankruptcy')

# drop all rows completely empty; empty rows may be caused by openpyxl
df = df.dropna(how='all')

prmt.EIM_and_bankruptcy = df

logging.info("read input sheet 'EIM & bankruptcy'")

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
read_reserve_sales_historical() # sets prmt.reserve_PCU_sales_q_hist & prmt.reserve_sale_latest_date


# # Create scenarios

# In[ ]:


# update values in object prmt using functions

progress_bar_loading.wid.value += 1
# print("Initializing data... " , end='') # for UI

initialize_CA_cap() # sets prmt.CA_cap

initialize_CA_APCR() 
# sets prmt.CA_APCR_2013_2020_MI, prmt.CA_APCR_2021_2030_Oct2017_MI, prmt.CA_APCR_2021_2030_Apr2019_add_MI

initialize_CA_advance() # sets prmt.CA_advance_MI
initialize_VRE_account() # sets prmt.VRE_reserve_MI

# get input: historical quarterly auction data
get_qauct_hist()

# set object attribute prmt.supply_last_hist_yr (integer), based on prmt.qauct_hist
prmt.supply_last_hist_yr = prmt.qauct_hist.loc[prmt.qauct_hist['date_level'].dt.quarter==4]['date_level'].max().year

# set compliance_events; sets object attribute prmt.compliance_events
get_compliance_events()

# ~~~~~~~~~~~~
# sets object attributes prmt.CIR_historical & prmt.CIR_offsets_q_sums
get_CIR_data_and_clean()

# get historical data for VRE; assume no more retirements
# sets object attribute prmt.VRE_retired
get_VRE_retired_from_CIR()

# ~~~~~~~~~~~~
# initialization of details for EIM Outstanding Emissions and bankruptcy retirements
assign_EIM_outstanding() 
# sets value prmt.EIM_outstanding; used for modifying consignment
# must run before initialize_elec_alloc, because EIM outstanding values modify elec alloc

assign_bankruptcy_noncompliance() # sets value of prmt.bankruptcy_hist_proj


# In[ ]:


# read CA data
# initialization of allocations
CA_alloc_data = read_CA_alloc_data()
elec_alloc_IOU, elec_alloc_POU = initialize_elec_alloc()
nat_gas_alloc = initialize_nat_gas_alloc(CA_alloc_data)
industrial_etc_alloc = initialize_industrial_etc_alloc(CA_alloc_data)

# ~~~~~~~~~~~~
read_annual_auction_notices() # sets prmt.consign_ann_hist

# initialization of consignment vs. non-consignment
# run fn create_consign_historical_and_projection_annual
consign_df = create_consign_historical_and_projection_annual(elec_alloc_IOU, elec_alloc_POU, nat_gas_alloc)

# upsample consignment; sets object attribute prmt.consign_hist_proj_new_avail
consign_upsample_historical_and_projection(consign_df['consign_ann'])

# ~~~~~~~~~~~~
# convert all allocations into MI (for all vintages) & put into one df; 
# set as object attribute prmt.CA_alloc_MI_all
CA_alloc_consign_dfs = [consign_df['consign_elec_IOU'], 
                        consign_df['consign_elec_POU'], 
                        consign_df['consign_nat_gas']]
CA_alloc_dfs_not_consign = [industrial_etc_alloc, 
                            consign_df['elec_POU_not_consign'], 
                            consign_df['nat_gas_not_consign']]
CA_alloc_dfs = CA_alloc_consign_dfs + CA_alloc_dfs_not_consign
CA_alloc_MI_list = []
for alloc in CA_alloc_dfs:
    alloc_MI = convert_ser_to_df_MI_CA_alloc(alloc)
    CA_alloc_MI_list += [alloc_MI]
prmt.CA_alloc_MI_all = pd.concat(CA_alloc_MI_list)


# In[ ]:


# read QC data
get_QC_inputs() # sets prmt.QC_cap, prmt.QC_advance, prmt.QC_APCR

get_QC_allocation_data()
# sets object attributes:
# prmt.QC_alloc_hist, prmt.QC_alloc_initial, 
# prmt.QC_alloc_trueups, prmt.QC_alloc_trueups_non_APCR, prmt.QC_alloc_trueups_neg, 
# prmt.QC_alloc_full_proj


# In[ ]:


read_emissions_historical_data() 
# sets prmt.emissions_and_obligations, used in create_emissions_pct_sliders & emissions_projection


# In[ ]:


# set latest year with auction data
# get latest year in CA consignment data, CA allocation data, & QC allocation data

# last year of CA alloc historical data
CA_alloc_latest_yr = CA_alloc_data[CA_alloc_data['name'].str.contains('industrial')]['year'].max().astype(int)

# last year of QC alloc historical data
QC_alloc_hist_init = prmt.QC_alloc_hist[prmt.QC_alloc_hist.index.get_level_values('alloc_type')=='initial']
QC_alloc_latest_yr = QC_alloc_hist_init.index.get_level_values('emission_year').max()

# set object attribute prmt.latest_hist_alloc_yr:
prmt.latest_hist_alloc_yr = min(CA_alloc_latest_yr, QC_alloc_latest_yr)

# take minimum of latest year for that set of three
# (if don't have all three, can't infer how to split up the auction data by jurisdiction and vintage)
prmt.latest_hist_aauct_yr = min(prmt.consign_ann_hist.index.max(), CA_alloc_latest_yr, QC_alloc_latest_yr)

# test data for internal consistency
if prmt.run_tests == True:
    test_consistency_inputs_CIR_vs_qauct(CA_alloc_latest_yr, QC_alloc_latest_yr)
    test_consistency_inputs_annual_data(CA_alloc_latest_yr, QC_alloc_latest_yr)
    test_consistency_CA_alloc(CA_alloc_data)


# ## Create classes and objects
# * Scenario_juris
# * Em_pct
# * Em_text_input_CAQC
# * Years_not_sold_out
# * Fract_not_sold
# * Off_pct
# * Progress_bar_auction

# In[ ]:


# initialization of classes Scenario_juris, Em_pct, etc.

progress_bar_loading.wid.value += 1
# print("Creating scenarios... " , end='') # for UI

# ~~~~~~~~~~~
class Scenario_juris:
    def __init__(self, 
                 avail_accum, 
                 snaps_CIR, 
                 snaps_end):
        self.avail_accum = avail_accum # initialize as empty
        self.snaps_CIR = snaps_CIR # initialize as empty
        self.snaps_end = snaps_end # initialize as empty

# make an instance of Scenario for CA hindcast starting in 2012Q4
scenario_CA = Scenario_juris(
    avail_accum=prmt.standard_MI_empty.copy(),
    snaps_CIR=[],
    snaps_end=[],
)
logging.info("created object scenario_CA")

# make an instance of Scenario for QC hindcast starting in 2013Q4
scenario_QC = Scenario_juris(
    avail_accum=prmt.standard_MI_empty.copy(),
    snaps_CIR=[],
    snaps_end=[],
)
logging.info("created object scenario_QC")

# ~~~~~~~~~~~
# create class Em_pct
class Em_pct:
    def __init__(self, slider): # default
        self.slider = slider # this attribute will be set equal to a widget, which has various properties (value, etc.)

# create new objects (instances of Em_pct); these are empty but will be filled by fn emissions_pct_sliders
em_pct_CA_simp = Em_pct([])
em_pct_QC_simp = Em_pct([])
em_pct_CA_adv1 = Em_pct([]) # period 1, i.e., 2019-2020
em_pct_QC_adv1 = Em_pct([])
em_pct_CA_adv2 = Em_pct([]) # period 2, i.e., 2021-2025
em_pct_QC_adv2 = Em_pct([])
em_pct_CA_adv3 = Em_pct([]) # period 3, i.e., 2026-2030
em_pct_QC_adv3 = Em_pct([])

# ~~~~~~~~~~~
class Em_text_input_CAQC():
    def __init__(self, wid):
        self.wid = wid # this attribute will be set equal to a widget, which has various properties (value, etc.)

# create new object (instance of the class Em_text_input_CAQC)
# starts empty, but will be filled by fn emissions_projection
em_text_input_CAQC_obj = Em_text_input_CAQC([])   

# ~~~~~~~~~~~
class Years_not_sold_out:
    def __init__(self, wid):
        self.wid = wid # this attribute will be set equal to a widget, which has various properties (value, etc.)
    
# create new object (instance of the class Years_not_sold_out)
# starts empty, but will be filled by fn create_auction_tabs
years_not_sold_out_obj = Years_not_sold_out([])

# ~~~~~~~~~~~
class Fract_not_sold():
    def __init__(self, wid):
        self.wid = wid # this attribute will be set equal to a widget, which has various properties (value, etc.)
        
# create new object (instance of the class Fract_not_sold)
# starts empty, but will be filled by fn create_auction_tabs
fract_not_sold_obj = Fract_not_sold([])

# ~~~~~~~~~~~
# create class Off_pct
class Off_pct:
    def __init__(self, slider): # default
        self.slider = slider # this attribute will be set equal to a widget, which has various properties (value, etc.)

# create new objects (instances of off_pct); these are empty but will be filled by fn create_offsets_pct_sliders
off_pct_of_limit_CAQC = Off_pct([])

off_pct_CA_adv1 = Off_pct([]) # period 1, i.e., 2019-2020
off_pct_QC_adv1 = Off_pct([])

off_pct_CA_adv2 = Off_pct([]) # period 2, i.e., 2021-2025
off_pct_QC_adv2 = Off_pct([])

off_pct_CA_adv3 = Off_pct([]) # period 3, i.e., 2026-2030
off_pct_QC_adv3 = Off_pct([])

# ~~~~~~~~~~~
class Progress_bar_auction:
        bar = ""    

        def __init__(self, wid):
            self.wid = wid # object will be instantiated using iPython widget as wid

        def create_progress_bar(wid):
            progress_bar = Progress_bar_auction(wid)
            return progress_bar

# create objects
progress_bar_CA = Progress_bar_auction.create_progress_bar(
    widgets.IntProgress(
        value=prmt.progress_bar_CA_count,
        min=0,
        max=len(prmt.CA_quarters),
        step=1,
        description='California:',
        bar_style='', # 'success', 'info', 'warning', 'danger' or ''
        orientation='horizontal',
    ))

progress_bar_QC = Progress_bar_auction.create_progress_bar(
    widgets.IntProgress(
        value=prmt.progress_bar_QC_count,
        min=0,
        max=len(prmt.QC_quarters),
        step=1,
        description='Québec:',
        bar_style='', # 'success', 'info', 'warning', 'danger' or ''
        orientation='horizontal',
    ))


# # Run supply-side umbrella function
# (process_allowance_supply_CA_QC)

# In[ ]:


if prmt.saved_auction_run_default == False:
    # run hindcast from the start of the WCI system
    all_accts_CA, all_accts_QC = process_allowance_supply_CA_QC()
    
    # after processing auctions, save the results for default run
    # snaps_end:
    prmt.CA_snaps_end_default_run_end = scenario_CA.snaps_end
    prmt.QC_snaps_end_default_run_end = scenario_QC.snaps_end
    
    # snaps_CIR:
    prmt.CA_snaps_end_default_run_CIR = scenario_CA.snaps_CIR
    prmt.QC_snaps_end_default_run_CIR = scenario_QC.snaps_CIR

    # since values saved above, set new value for prmt.saved_auction_run_default
    prmt.saved_auction_run_default = True
else:
    # will use saved run for default auction settings
    pass


# In[ ]:


figure_explainer_text = "<p>Above, the figure on the left shows covered emissions compared with the supply of compliance instruments (allowances and offsets) that enter private market participants’ accounts through auction sales or direct allocations from WCI governments. The instrument supplies shown exclude sales of reserve allowances (California and Québec) and Price Ceiling Units (California only).</p><br><p>The model tracks the private bank of allowances, defined as the number of allowances held in private accounts in excess of compliance obligations those entities face under the program in any given year. When the supply of compliance instruments entering private accounts is greater than covered emissions in a given year, the private bank increases. When the supply of compliance instruments entering private accounts is less than covered emissions, the private bank decreases.</p><br><p>The figure on the right shows the running total of compliance instruments banked in private accounts. In addition, the graph shows any allowances that went unsold in auctions. These allowances are held in government accounts until they are either reintroduced at a later auction or removed from the normal auction supply subject to market rules.</p><br><p>If the private bank is exhausted, the model simulates reserve sales to meet any remaining outstanding compliance obligations, based on the user-defined emissions projection. Starting in 2021, if the supply of allowances held in government-controlled reserve accounts is exhausted, then an unlimited quantity of instruments called “price ceiling units” will be available at a price ceiling to meet any remaining compliance obligations. The model tracks the sale of reserve allowances and price ceiling units in a single composite category.</p><br><p>For more information about the banking metric used here, see Near Zero's Sep. 2018 report, <a href='http://www.nearzero.org/wp/2018/09/12/tracking-banking-in-the-western-climate-initiative-cap-and-trade-program/' target='_blank'>Tracking Banking in the Western Climate Initiative Cap-and-Trade Program</a href>.</p>"
# changed text to "Above" when moving the accordion to below the figure
# ~~~~~~~~~~~~~~~~~~

latest_emissions_data_year = prmt.emissions_and_obligations.dropna(how='all').index.max()

em_explainer_text = f"<p>The WCI cap-and-trade program covers emissions from electricity suppliers, large industrial facilities, and natural gas and transportation fuel distributors.</p><br><p>By default, the model uses a projection in which covered emissions decrease 2% per year, starting from emissions in {latest_emissions_data_year} (the latest year with official reporting data). Users can specify higher or lower emissions scenarios using the available settings.</p><br><p>A 2% rate of decline follows ARB's 2017 Scoping Plan scenario for California emissions, which includes the effects of prescriptive policy measures (e.g., the Renewables Portfolio Standard for electricity), but does not incorporate effects of the cap-and-trade program.</p><br><p>Note that PATHWAYS, the model ARB used to generate the Scoping Plan scenario, does not directly project covered emissions in California. Instead, the PATHWAYS model tracks emissions from four economic sectors called “covered sectors,” which together constitute about ~10% more emissions than the “covered emissions” that are actually subject to the cap-and-trade program in California. For more information, see Near Zero's May 2018 <a href='http://www.nearzero.org/wp/2018/05/07/ready-fire-aim-arbs-overallocation-report-misses-its-target/' target='_blank'>report on this discrepancy</a href>. Users can define their own emission projections to explore any scenario they like, as the model makes no assumptions about future emissions aside from what the user provides.</p>"

# ~~~~~~~~~~~~~~~~~~
# note: no <br> between <p> and </p> for this text block
first_emissions_proj_year = latest_emissions_data_year + 1
em_custom_footnote_text = f"<p>Copy and paste from data table in Excel.</p><p>Format: column for years on left, column for emissions data on right. Please copy only the data, without headers (<a href='https://storage.googleapis.com/wci_model_online_file_hosting/Excel_copy_example.png' target='_blank'>see example</a href>).</p><p>Projection must cover each year from {first_emissions_proj_year} to 2030. (Data entered for years prior to {first_emissions_proj_year} and after 2030 will be discarded.)</p><p>Units must be million metric tons CO<sub>2</sub>e/year (MMTCO2e).</p><p>"

# ~~~~~~~~~~~~~~~~~~

auction_explainer_text = f"<p>WCI quarterly auctions include two separate offerings: a current auction of allowances with vintage years equal to the current calendar year (as well as any earlier vintages of allowances that went unsold and are being reintroduced), and a separate advance auction featuring a limited number of allowances with a vintage year equal to three years in the future.</p><br><p>By default, the model assumes that all future auctions sell out. However, users can specify a custom percentage of allowances to go unsold at auction in one or more years. This percentage applies to both current and advance auctions, in each quarter of the user-specified years.</p><br><p>To date, most current auctions have sold out. But in 2016 and 2017, ~143 million current allowances went unsold as sales collapsed over several auctions. Pursuant to market rules, as of Q2 2019, most of these allowances were reintroduced for sale in current auctions, and all of those made available were sold.</p><br><p>Out of ~118 million California state-owned allowances that went unsold in current auctions in 2016-2017, ~80 million were reintroduced and sold. Because of limits on how many state-owned allowances can be reintroduced per auction, ~38 million remained unsold for more than 24 months, at which point they were removed from the normal auction supply; of those, ~1 million were retired in 2018 to account for Energy Imbalance Market (EIM) Outstanding Emissions, and the remaining ~37 million were transferred to California’s market reserve account.</p><br><p>Québec's current regulations do not contain a similar stipulation for removal of unsold allowances from the normal auction supply.</p><br><p> For more information on this <q>self correction</q> mechanism, see <a href='http://www.nearzero.org/wp/2018/05/23/californias-self-correcting-cap-and-trade-auction-mechanism-does-not-eliminate-market-overallocation/' target='_blank'>Near Zero's May 2018 report</a href>.</p>"

# ~~~~~~~~~~~~~~~~~~

offsets_explainer_text = f"<p>In addition to submitting allowances to satisfy their compliance obligations, entities subject to the cap-and-trade program can also submit a certain number of offset credits instead. These credits represent emission reductions that take place outside of the cap-and-trade program and are credited pursuant to an approved offset protocol.</p><br><p>For California, the limits on offset usage are equal to a percentage of a covered entity’s compliance obligations: through 2020, the limit is 8%; from 2021 through 2025, the limit is 4%; and from 2026 through 2030, the limit is 6%. For Québec, the limit is 8% for all years.</p><br><p>The model incorporates actual offset supply through Q{prmt.CIR_historical.index.get_level_values('date').max().quarter} {prmt.CIR_historical.index.get_level_values('date').max().year}, based on ARB’s Q{prmt.CIR_historical.index.get_level_values('date').max().quarter} {prmt.CIR_historical.index.get_level_values('date').max().year} compliance instrument report for the WCI system. By default, the model assumes offset supply in any year is equivalent to three-quarters of the limit in each jurisdiction, reflecting ARB’s assumptions in the 2018 AB 398 rulemaking. Users can specify a higher or lower offset supply using the available settings.</p><br><p>Like allowances, offsets can also be banked for future use. Thus, we include offsets in our banking calculations. If the user-specified offset supply exceeds what can be used through 2030, given the user-specified emissions projection, then the model calculates this excess and warns the user.</p><br><p>For more on offsets, see Near Zero’s Mar. 2018 report, <a href='http://www.nearzero.org/wp/2018/03/15/interpreting-ab-398s-carbon-offsets-limits/' target='_blank'>Interpreting AB 398’s Carbon Offset Limits</a href>. For more information on offset credits’ role in banking, see Near Zero's Sep. 2018 report, <a href='http://www.nearzero.org/wp/2018/09/12/tracking-banking-in-the-western-climate-initiative-cap-and-trade-program/' target='_blank'>Tracking Banking in the Western Climate Initiative Cap-and-Trade Program</a href>.</p>"


# In[ ]:


# create widgets for explainer text boxes
figure_html = widgets.HTML(
    value=figure_explainer_text,
    # placeholder='Some HTML',
    # description='',
)
figure_explainer_accord = widgets.Accordion(
    children=[figure_html], 
    layout=widgets.Layout(width="650px")
)
figure_explainer_accord.set_title(0, 'About supply-demand balance and banking')
figure_explainer_accord.selected_index = None


# In[ ]:


# create tabs for emissions, auction, offsets
emissions_tabs = create_emissions_tabs()
auction_tabs = create_auction_tabs()
offsets_tabs = create_offsets_tabs()

# prepare data for default graph
supply_demand_calculations()


# In[ ]:


# ~~~~~~~~~~
em_explainer_html = widgets.HTML(value=em_explainer_text)

em_explainer_accord = widgets.Accordion(
    children=[em_explainer_html], 
    layout=widgets.Layout(width="650px")
)
em_explainer_accord.set_title(0, 'About covered emissions')
em_explainer_accord.selected_index = None

emissions_tabs_explainer = widgets.VBox([emissions_tabs, em_explainer_accord])

emissions_title = widgets.HTML(value="<h4>Demand projection: covered emissions</h4>")

emissions_tabs_explainer_title = widgets.VBox([emissions_title, emissions_tabs_explainer])

# ~~~~~~~~~~

auct_explain_html = widgets.HTML(value=auction_explainer_text)

auct_explain_accord = widgets.Accordion(
    children=[auct_explain_html], 
    layout=widgets.Layout(width="650px")
)
auct_explain_accord.set_title(0, 'About allowance auctions')
auct_explain_accord.selected_index = None

auction_tabs_explainer = widgets.VBox([auction_tabs, auct_explain_accord])

auction_title = widgets.HTML(value="<h4>Supply projection: allowances auctioned</h4>")

auction_tabs_explainer_title = widgets.VBox([auction_title, auction_tabs_explainer])

# ~~~~~~~~~~
offsets_explainer_html = widgets.HTML(value=offsets_explainer_text)

offsets_explainer_accord = widgets.Accordion(
    children=[offsets_explainer_html],
    layout=widgets.Layout(width="650px")
)
offsets_explainer_accord.set_title(0, 'About carbon offsets')
offsets_explainer_accord.selected_index = None

offsets_tabs_explainer = widgets.VBox([offsets_tabs, offsets_explainer_accord])

offsets_title = widgets.HTML(value="<h4>Supply projection: offsets sales</h4>")

offsets_tabs_explainer_title = widgets.VBox([offsets_title, offsets_tabs_explainer])


# #### create figures & display them

# In[ ]:


create_figures()

# create_button_supply_demand()
# create supply-demand button (but don't show it until display step below)
supply_demand_button = widgets.Button(description="Run supply-demand calculations", 
                                      layout=widgets.Layout(width="250px"))
supply_demand_button.style.button_color = 'PowderBlue'

# define action on button click
supply_demand_button.on_click(supply_demand_button_on_click)
# ~~~~~~~~~~~~~    
# starts enabled; becomes disabled after file saved; becomes re-enabled after a new model run
save_csv_button = widgets.Button(description="Save results & settings (csv)", 
                                 disabled = False,
                                 layout=widgets.Layout(width="250px"),
                                 )
save_csv_button.style.button_color = 'PowderBlue' # '#A9A9A9'

save_csv_button.on_click(save_csv_on_click)


# In[ ]:


if __name__ == '__main__': 
    # show content that is cleared when user chooses to re-run the model 
    
    # show figures
    show(prmt.fig_em_bank)
    
    # show supply-demand button & save csv button & save graphs button
    display(widgets.HBox([supply_demand_button, save_csv_button]))


# In[ ]:


# keep displays below in separate cell from displays above, 
# because displays above get cleared with each new run
if __name__ == '__main__':
    display(figure_explainer_accord)
    
    # display each of the three tab sets (emissions, auctions, offsets)
    display(emissions_tabs_explainer_title)
    display(auction_tabs_explainer_title)
    display(offsets_tabs_explainer_title)


# In[ ]:


# end of model run
logging.info(f"WCI-RULES model log; end of run {prmt.save_timestamp}")


# ## end of model run & interface code

