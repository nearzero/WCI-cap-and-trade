
# coding: utf-8

# <img src="https://github.com/masoninman/binder-test/blob/master/images/Near_Zero_logo_tiny.jpg?raw=true" alt="Drawing" align="right" style="width: 200px"/>
# 
# # <span style="color:DarkBlue">Western Climate Initiative cap-and-trade model</span>
# 
# ## Developed by [Near Zero](http://nearzero.org)
# 
# ### Version 1.0.2 (Oct 18, 2018)
# 
# This model simulates the supply-demand balance of the Western Climate Initiative cap-and-trade program, jointly operated by California and Quebec.
# 
# ---
# 
# © Copyright 2018 by [Near Zero](http://nearzero.org). This work is licensed under a [Creative Commons Attribution-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-sa/4.0/).
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

def create_progress_bar_loading():
    # define class Progress_bar
    class Progress_bar_loading:
        bar = ""    

        def __init__(self, wid):
            self.wid = wid # object will be instantiated using iPython widget as wid

        def create_progress_bar(wid):
            progress_bar = Progress_bar_loading(wid)
            return progress_bar

    # create objects
    progress_bar_loading = Progress_bar_loading.create_progress_bar(
        widgets.IntProgress(
            value=0, # initialize
            min=0,
            max=6,
            step=1,
            description='Loading:',
            bar_style='', # 'success', 'info', 'warning', 'danger' or ''
            orientation='horizontal',
        ))

    return(progress_bar_loading)


# In[ ]:


progress_bar_loading = create_progress_bar_loading()
display(progress_bar_loading.wid)


# In[ ]:


progress_bar_loading.wid.value += 1
print("importing libraries") # potential for progress_bar_loading

import pandas as pd
from pandas.tseries.offsets import *
import numpy as np

import time
# from time import sleep
import datetime as dt
from datetime import datetime

import os
import inspect # for getting name of current function
import logging

# pd.__version__, np.__version__


# In[ ]:


import bokeh

from bokeh.plotting import figure, show, output_notebook # save
# from bokeh.models.tools import SaveTool
from bokeh.models import Legend
from bokeh.layouts import gridplot
from bokeh.palettes import Viridis, Blues, YlOrBr # note: Viridis is a dict; viridis is a function

# # for html markup box
# from bokeh.io import output_file, show

# use if working offline; also might help with Binder loading
from bokeh.resources import INLINE

output_notebook(resources=INLINE, hide_banner=True)
# hide_banner gets rid of message "BokehJS ... successfully loaded"

from bokeh.document import Document
from bokeh.models.layouts import Column


# In[ ]:


# initialize logging
save_timestamp = time.strftime('%Y-%m-%d_%H%M', time.localtime())

# start logging
# to save logs, need to update below with the correct strings and selection for your desired directory
try:
    if os.getcwd().split('/')[4] == 'cap_and_trade_active_dev':
        LOG_PATH = os.getcwd() + '/logs'
        logging.basicConfig(filename=f"{LOG_PATH}/WCI_cap_trade_log_{save_timestamp}.txt", 
                            filemode='a',  # choices: 'w' or 'a'
                            level=logging.INFO)
    else:
        # don't save log
        pass
except:
    pass


# In[ ]:


class Prmt():
    """
    Class to create object prmt that has parameters used throughout the model as its attributes.
    """
    
    def __init__(self):
        
        self.model_version = '1.0.1'
        
        self.online_settings_auction = True # will be overridden below for testing; normally set by user interface
        self.years_not_sold_out = () # set by user interface
        self.fract_not_sold = float(0) # set by user interface
        
        self.run_hindcast = False # set to true to start model run at beginning of each market (2012Q4/2013Q4)
        
        self.run_tests = True
        self.verbose_log = True
        self.test_failed_msg = 'Test failed!:'   
        
        self.CA_post_2020_regs = 'Proposed_Regs_Sep_2018'
        self.QC_post_2020_regs = 'Proposed_Regs_Sep_2018'
        # regs choices are: 'Regs_Oct_2017', 'Preliminary_Discussion_Draft', 'Proposed_Regs_Sep_2018'
        
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
        
        self.blob_master = "https://github.com/nearzero/WCI-cap-and-trade/blob/master"
        # overridden below if cwd is local copy of repo WCI-Private
        
        self.input_file_raw_url_short = "/data/data_input_file.xlsx?raw=true"
        self.CIR_raw_url_short = "/data/CIR_file.xlsx?raw=true"
        
        self.snaps_end_Q4 = '' # value filled in by fn download_input_files
        self.snaps_end_Q4_sum = '' # value filled in by fn download_input_files
        
        self.CA_cap_adjustment_factor = '' # value filled in by fn download_input_files
        
        self.NaT_proxy = pd.to_datetime('2200Q1').to_period('Q')
        
        self.standard_MI_names = ['acct_name', 'juris', 'auct_type', 'inst_cat', 'vintage', 'newness', 'status', 
                                  'date_level', 'unsold_di', 'unsold_dl', 'units']
        
        # create empty index; can be used for initializing all dfs
        self.standard_MI_index = pd.MultiIndex(levels=[[]]*len(self.standard_MI_names),
                                               labels=[[]]*len(self.standard_MI_names),
                                               names=self.standard_MI_names)
        
        self.standard_MI_empty = pd.DataFrame(index=self.standard_MI_index, columns=['quant'])
        
        self.CIR_columns = ['gen_comp', 'limited_use', 'VRE_acct', 'A_I_A', 'retirement', 'APCR_acct', 
                            'env_integrity', 'early_action', 'subtotal']
        
        self.progress_bar_CA_count = 0 # initialize
        self.progress_bar_QC_count = 0 # initialize
        
        self.offset_rate_fract_of_limit = 0.75 # see func offsets_projection for rationale
        
        self.use_fake_data = False # used for testing 
        
        # ~~~~~~~~~~~~~~~~~        
        
        # set other variables to be blank; will be reset below using functions    
        self.qauct_hist = ''
        self.auction_sales_pcts_all = ''   
        self.CA_cap = ''
        self.CA_APCR_MI = ''
        self.CA_advance_MI = ''
        self.VRE_reserve_MI = ''

        self.CA_alloc_MI_all = ''
        self.consign_hist_proj = ''
        
        self.QC_cap = ''
        self.QC_advance_MI = ''
        self.QC_APCR_MI = ''
        self.QC_alloc_initial = ''
        self.QC_alloc_trueups = ''
        self.QC_alloc_full_proj = ''
        
        self.qauct_hist = ''
        self.auction_sales_pcts_all = ''
        self.qauct_new_avail = ''

        self.compliance_events = ''
        self.VRE_retired = ''
        self.CIR_historical = ''
        self.CIR_offsets_q_sums = ''
        
        self.loading_msg_pre_refresh = []
        self.error_msg_post_refresh = []
        
        self.input_file = ''
        self.CIR_excel = ''
        self.CA_cap_data = ''
        
        self.emissions_ann = ''
        self.emissions_ann_CA = ''
        self.emissions_ann_QC = ''
        self.supply_ann = ''
        self.bank_cumul_pos = ''
        self.balance = ''
        self.unsold_auct_hold_cur_sum = ''
        self.reserve_sales = ''
        
        self.Fig_1_2 = ''
        self.js_download_of_csv = ''
        self.export_df = ''

# ~~~~~~~~~~~~~~~~~~
# create object prmt (instance of class Prmt), after which it can be filled with more entries below
prmt = Prmt()


# In[ ]:


# for testing using private repo or branch of public repo, ensure download of input file from correct location

if os.getcwd() == "/Users/masoninman/Dropbox/WCI-Private":
    # working within private repo
    
    # override prmt.blob_master
    prmt.blob_master = "/Users/masoninman/Dropbox/WCI-Private"
    
    # override prmt.input_file_raw_url_short to remove suffix "?raw=true"
    prmt.input_file_raw_url_short = "/data/data_input_file.xlsx"
    
    # override CIR file url to remove suffix "?raw=true"
    prmt.CIR_raw_url_short = "/data/CIR_file.xlsx"
    
elif os.getcwd() == "/Users/masoninman/Dropbox/WCI-cap-and-trade":
    # working within local clone of public repo
    
    # override prmt.blob_master
    prmt.blob_master = "/Users/masoninman/Dropbox/WCI-cap-and-trade"
    
    # override prmt.input_file_raw_url_short to remove suffix "?raw=true"
    prmt.input_file_raw_url_short = "/data/data_input_file.xlsx"
    
    # override CIR file url to remove suffix "?raw=true"
    prmt.CIR_raw_url_short = "/data/CIR_file.xlsx"


# In[ ]:


def load_input_files():
    
    progress_bar_loading.wid.value += 1
    print("importing data") # potential for progress_bar_loading
    
    # download each file once from Github, set each as an attribute of object prmt

    # main input_file
    try:
        prmt.input_file = pd.ExcelFile(prmt.input_file_raw_url_short)
        # logging.info("downloaded input file from short url")
        # prmt.loading_msg_pre_refresh += ["Loading input file..."] # for UI
    except:
        prmt.input_file = pd.ExcelFile(prmt.blob_master + prmt.input_file_raw_url_short)
        logging.info("downloaded input file using full url")
        # prmt.loading_msg_pre_refresh += ["Downloading input file..."] # for UI

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # CIR quarterly
    try:
        prmt.CIR_excel = pd.ExcelFile(prmt.CIR_raw_url_short)
        logging.info("downloaded CIR file using short url")
    except:
        prmt.CIR_excel = pd.ExcelFile(prmt.blob_master + prmt.CIR_raw_url_short)
        logging.info("downloaded CIR file using full url")


# In[ ]:


def snaps_end_Q4_all_sell_initialize():
    """
    Modifies format of object attribute prmt.snaps_end_Q4:
    * formats date columns to be in date format
    * sets MultiIndex = prmt.standard_MI_names, leaves 'snap_q' as column
    
    """
    
    # read snaps_end_Q4 from input_file sheet, set new value for object attribute
    prmt.snaps_end_Q4 = pd.read_excel(prmt.input_file, sheet_name='snaps end Q4 all sell out', header=1)
    
    # format columns as Period (quarters)
    for col in ['snap_q', 'date_level', 'unsold_di', 'unsold_dl']:
        if isinstance(col, pd.Period):
            pass
        else:
            prmt.snaps_end_Q4[col] = pd.to_datetime(prmt.snaps_end_Q4[col]).dt.to_period('Q')
    
    # restore np.NaN (replacing the way Excel saves them)
    for col in ['auct_type', 'inst_cat', 'newness', 'status']:
        prmt.snaps_end_Q4[col] = prmt.snaps_end_Q4[col].replace(np.NaN, 'n/a')
        
    # set MultiIndex as standard_MI_names; snap_q will remain as column next to 'quant'
    prmt.snaps_end_Q4 = prmt.snaps_end_Q4.set_index(prmt.standard_MI_names)
    
    # calculate sum (for testing); set as new value of object attribute
    prmt.snaps_end_Q4_sum = prmt.snaps_end_Q4['quant'].sum()
    
    # no return; modifies object attributes


# In[ ]:


# run function to download files
load_input_files()

# get snaps_end_Q4
snaps_end_Q4_all_sell_initialize()

# set CA_cap_data
prmt.CA_cap_data = pd.read_excel(prmt.input_file, sheet_name='CA cap data')
logging.info("read CA_cap_data")

# set CA_cap_adjustment_factor
prmt.CA_cap_adjustment_factor = prmt.CA_cap_data[
    prmt.CA_cap_data['name']=='CA_cap_adjustment_factor'].set_index('year')['data']


# In[ ]:


# modified slightly from WCI_model_explainer_text_v2.py (2018-10-10)

figure_explainer_text = "<p>Above, the figure on the left shows covered emissions compared with the supply of compliance instruments (allowances and offsets) that enter private market participants’ accounts through auction sales or direct allocations from WCI governments.</p><br><p>The model tracks the private bank of allowances, defined as the number of allowances held in private accounts in excess of compliance obligations those entities face under the program in any given year. When the supply of compliance instruments entering private accounts is greater than covered emissions in a given year, the private bank increases. When the supply of compliance instruments entering private accounts is less than covered emissions, the private bank decreases.</p><br><p>The figure on the right shows the running total of compliance instruments banked in private accounts. In addition, the graph shows any allowances that went unsold in auctions. These allowances are held in government accounts until they are either reintroduced at a later auction or removed from the normal auction supply subject to market rules.</p><br><p>If the private bank is exhausted, the model simulates reserve sales to meet any remaining outstanding compliance obligations, based on the user-defined emissions projection. Starting in 2021, if the supply of allowances held in government-controlled reserve accounts is exhausted, then an unlimited quantity of instruments called “price ceiling units” will be available at a price ceiling to meet any remaining compliance obligations. The model tracks the sale of reserve allowances and price ceiling units in a single composite category.</p><br><p>For more information about the banking metric used here, see Near Zero's Sep. 2018 report, <a href='http://www.nearzero.org/wp/2018/09/12/tracking-banking-in-the-western-climate-initiative-cap-and-trade-program/' target='_blank'>Tracking Banking in the Western Climate Initiative Cap-and-Trade Program</a href>.</p>"
# changed text to "Above" when moving the accordion to below the figure
# ~~~~~~~~~~~~~~~~~~

em_explainer_text = "<p>The WCI cap-and-trade program covers emissions from electricity suppliers, large industrial facilities, and natural gas and transportation fuel distributors.</p><br><p>By default, the model uses a projection in which covered emissions decrease 2% per year, starting from emissions in 2016 (the latest year with official reporting data). Users can specify higher or lower emissions scenarios using the available settings.</p><br><p>A 2% rate of decline follows ARB's 2017 Scoping Plan scenario for California emissions, which includes the effects of prescriptive policy measures (e.g., the Renewables Portfolio Standard for electricity), but does not incorporate effects of the cap-and-trade program.</p><br><p>Note that PATHWAYS, the model ARB used to generate the Scoping Plan scenario, does not directly project covered emissions in California. Instead, the PATHWAYS model tracks emissions from four economic sectors called “covered sectors,” which together constitute about ~10% more emissions than the “covered emissions” that are actually subject to the cap-and-trade program in California. For more information, see Near Zero's May 2018 <a href='http://www.nearzero.org/wp/2018/05/07/ready-fire-aim-arbs-overallocation-report-misses-its-target/' target='_blank'>report on this discrepancy</a href>. Users can define their own emission projections to explore any scenario they like, as the model makes no assumptions about future emissions aside from what the user provides.</p>"

# ~~~~~~~~~~~~~~~~~~
# note: no <br> between <p> and </p> for this text block
em_custom_footnote_text = "<p>Copy and paste from data table in Excel.</p><p>Format: column for years on left, column for emissions data on right. Please copy only the data, without headers (<a href='https://github.com/nearzero/WCI-cap-and-trade/blob/master/images/Excel_copy_example.png?raw=true' target='_blank'>see example</a href>).</p><p>Projection must cover each year from 2017 to 2030. (Data entered for years prior to 2017 and after 2030 will be discarded.)</p><p>Units must be million metric tons CO<sub>2</sub>e/year (MMTCO2e).</p><p>"

# ~~~~~~~~~~~~~~~~~~

auction_explainer_text = "<p>WCI quarterly auctions include two separate offerings: a current auction of allowances with vintage years equal to the current calendar year (as well as any earlier vintages of allowances that went unsold and are being reintroduced), and a separate advance auction featuring a limited number of allowances with a vintage year equal to three years in the future.</p><br><p>By default, the model assumes that all future auctions sell out. However, users can specify a custom percentage of allowances to go unsold at auction in one or more years. This percentage applies to both current and advance auctions, in each quarter of the user-specified years.</p><br><p>To date, most current auctions have sold out. But in 2016 and 2017, 143 million current allowances went unsold as sales collapsed over several auctions. Pursuant to market rules, most of these allowances are now being reintroduced for sale in current auctions.</p><br><p>If California state-owned allowances remain unsold for more than 24 months, they are removed from the normal auction supply and transferred to the market reserve accounts. Quebec's current regulations do not contain a similar stipulation. We calculate that this self-correction mechanism will remove 38 – 52 million previously unsold allowances from the normal auction supply, with the exact amount dependent on the outcomes of the next two quarterly auctions. The remaining 91 – 105 million allowance will have been reintroduced at auction.</p><br><p>For more information, see Near Zero's May 2018 <a href='http://www.nearzero.org/wp/2018/05/23/californias-self-correcting-cap-and-trade-auction-mechanism-does-not-eliminate-market-overallocation/' target='_blank'>report on this <q>self correction</q> mechanism</a href>.</p>"

# ~~~~~~~~~~~~~~~~~~

offsets_explainer_text = "<p>In addition to submitting allowances to satisfy their compliance obligations, entities subject to the cap-and-trade program can also submit a certain number of offset credits instead. These credits represent emission reductions that take place outside of the cap-and-trade program and are credited pursuant to an approved offset protocol.</p><br><p>For California, the limits on offset usage are equal to a percentage of a covered entity’s compliance obligations: through 2020, the limit is 8%; from 2021 through 2025, the limit is 4%; and from 2026 through 2030, the limit is 6%. For Quebec, the limit is 8% for all years.</p><br><p>The model incorporates actual offset supply through Q3 2018, based on ARB’s Q3 2018 compliance instrument report for the WCI system. By default, the model assumes offset supply in any year is equivalent to three-quarters of the limit in each jurisdiction, reflecting ARB’s assumptions in the current proposed cap-and-trade regulations. Users can specify a higher or lower offset supply using the available settings.</p><br><p>Like allowances, offsets can also be banked for future use. Thus, we include offsets in our banking calculations. If the user-specified offset supply exceeds what can be used through 2030, given the user-specified emissions projection, then the model calculates this excess and warns the user.</p><br><p>For more on offsets, see Near Zero’s Mar. 2018 report, <a href='http://www.nearzero.org/wp/2018/03/15/interpreting-ab-398s-carbon-offsets-limits/' target='_blank'>Interpreting AB 398’s Carbon Offset Limits</a href>. For more information on offset credits’ role in banking, see Near Zero's Sep. 2018 report, <a href='http://www.nearzero.org/wp/2018/09/12/tracking-banking-in-the-western-climate-initiative-cap-and-trade-program/' target='_blank'>Tracking Banking in the Western Climate Initiative Cap-and-Trade Program</a href>.</p>"


# # AUCTION METADATA KEY

# **newness:**
# * 'new' (fka 'newly available'; means *never* before introduced)
# * 'reintro' (we use "reintroduction" only for state-owned that went unsold in current & are brought back again)
# * 'redes' [defunct?]
# 
# **status:**
# * 'available'
# * 'sold'
# * 'unsold' (use for unsold stock; can be made available under right circumstances)
# * 'not_avail'
# 
# **auct_type:**
# * 'current'
# * 'advance'
# * 'reserve'
# 
# **juris:** (jurisdiction)
# * CA, QC, ON
# 
# **inst_cat:**
# * 'CA'
# * 'CA_alloc'
# * 'consign' (could be elec or nat gas, IOU or POU)
# * 'QC'
# * 'QC\_alloc\_[year]'
# * 'ON'
# * 'QC\_alloc\_[year]\_APCR' (anomalous; only used once so far)
# 
# **date_level:**
# * for auctions, it is either:
#   * the latest date in which allowances were auctioned
#   * the future date in which they're scheduled to be auctioned
# * for allocations, it is the date in which they were distributed
# * for retirements (i.e., VRE), it is the date in which they were retired

# # HOUSEKEEPING FUNCTIONS

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
    
    (Now apparently used only in initialization for CA and QC auctions.)
    
    Housekeeping function.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start), for {ser.name}")
    
    df = pd.DataFrame(ser)
    
    if len(df.columns==1):
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
    if 'APCR' in ser.name:
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
    
    Housekeeping function
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
        # TO DO: ¿also change inst_cat?
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


def convert_ser_to_df_MI_QC_alloc(ser):
    """
    Converts certain Series into MultiIndex df. Works for QC allocation.
    
    Will put the QC_alloc into gen_acct.
    
    Housekeeping function.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    df = pd.DataFrame(ser)
    df.index.name = 'vintage'
    df = df.reset_index()
    
    if 'QC_alloc' in ser.name:
        df['acct_name'] = 'gen_acct'
        df['auct_type'] = 'n/a'
        df['juris'] = 'QC'
        # vintage set above
        df['inst_cat'] = f'QC_alloc_{cq.date.year}'
        df['date_level'] = cq.date
        df['newness'] = 'n/a'
        df['status'] = 'n/a'
        df['unsold_di'] = prmt.NaT_proxy
        df['unsold_dl'] = prmt.NaT_proxy
        df['units'] = 'MMTCO2e'
        
        df = df.rename(columns={'QC_alloc': 'quant'})
    
    else: # closing 'if alloc.name in
        print("Error" + "!: Series name is not in list above. Metadata not added.")

    df = df.set_index(prmt.standard_MI_names)

    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(df)


# In[ ]:


# NEW FOR ONLINE (updated version)

def quarter_period(year_quart):
    """
    Converts string year_quart (i.e., '2013Q4') into datetime quarterly period.
    """
    
    if isinstance(year_quart, pd.Period) == True:
        period = year_quart
        
    else:
        period = pd.to_datetime(year_quart).to_period('Q')
    
    return(period)


# # INITIALIZATION FUNCTIONS

# In[ ]:


def get_qauct_hist():
    """
    Read historical auction data from file qauct_hist.
    
    Covers all auctions through 2018Q3, for CA, QC, ON
    """
    
    logging.info(f"initialize: {inspect.currentframe().f_code.co_name} (start)")
    
    # qauct_hist is a full record of auction data, compiled from csvs using another notebook
    qauct_hist = pd.read_excel(prmt.input_file, sheet_name='quarterly auct hist')
    
    # rename field 'auction date' to 'date_level'
    qauct_hist = qauct_hist.rename(columns={'auction date': 'date_level'})
    
    # format 'date_level' as quarter period
    qauct_hist['date_level'] = pd.to_datetime(qauct_hist['date_level']).dt.to_period('Q')
    
    # set object attribute
    prmt.qauct_hist = qauct_hist
    
    # no return; func sets object attribute


# In[ ]:


def get_auction_sales_pcts_all():
    """
    Combine historical and projection, and clean up to remove overlap.
    """
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (start)")
    
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

    # no return; func sets object attribute


# In[ ]:


def get_auction_sales_pcts_historical():
    """
    Calculates historical auction sales percentages, drawing from historical record (qauct_hist).
    """
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (start)")
    
    # create record of auction sales percentages (from qauct_hist)
    df = prmt.qauct_hist.copy()
    df = df[~df['inst_cat'].isin(['IOU', 'POU'])]
    df = df.groupby(['market', 'auct_type', 'date_level'])[['Available', 'Sold']].sum()
    df['sold_pct'] = df['Sold'] / df['Available']

    auction_sales_pcts_historical = df['sold_pct']
    
    return(auction_sales_pcts_historical)


# In[ ]:


def get_auction_sales_pcts_projection_from_user_settings():
    """
    Read values for auction sales percentages in projection, as specified by user interface.
    """
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (start)")
    
    years_not_sold_out = prmt.years_not_sold_out
    fract_not_sold = prmt.fract_not_sold
    
    if prmt.online_settings_auction == True:
        proj = []
        market = 'CA-QC'   
        
        # fill in projection using user settings for years_not_sold_out & fract_not_sold
        for year in range(2018, 2030+1):
            for quarter in [1, 2, 3, 4]:
                date_level = quarter_period(f"{year}Q{quarter}")
                
                # add current auction projections
                # any quarters that overlap with historical data will be discarded when hist & proj are combined
                auct_type = 'current' 
                if year in years_not_sold_out:
                    proj += [(market, auct_type, date_level, (1 - fract_not_sold))]
                else:
                    # set to fract_not_sold to 0% (sold is 100%) for all years not in years_not_sold_out
                    proj += [(market, auct_type, date_level, 1.0)]
        
                # add advance auction projections; assume all auctions sell 100%
                # any quarters that overlap with historical data will be discarded when hist & proj are combined
                auct_type = 'advance'
                if year in years_not_sold_out:
                    proj += [(market, auct_type, date_level, (1 - fract_not_sold))]
                else:
                    # set to fract_not_sold to 0% (sold is 100%) for all years not in years_not_sold_out
                    proj += [(market, auct_type, date_level, 1.0)]
        
        proj_df = pd.DataFrame(proj, columns=['market', 'auct_type', 'date_level', 'value'])
        ser = proj_df.set_index(['market', 'auct_type', 'date_level'])['value']
        ser = ser.sort_index()
        auction_sales_pcts_projection = ser
        
    else:    
        # model will use default auction sales projection of 100% sales every quarter after 2018Q3
        pass
    
    return(auction_sales_pcts_projection)


# In[ ]:


def initialize_CA_cap():
    """
    CA cap quantities from § 95841. Annual Allowance Budgets for Calendar Years 2013-2050:
    * Table 6-1: 2013-2020 California GHG Allowance Budgets
    * Table 6-2: 2021-2031 California GHG Allowance Budgets
    * 2032-2050: equation for post-2031 cap
    """
    
    CA_cap_data = prmt.CA_cap_data
    
    CA_cap = CA_cap_data[CA_cap_data['name']=='CA_cap']
    CA_cap = CA_cap.set_index('year')['data']
    CA_cap = CA_cap.loc[:2030]
    CA_cap.name = 'CA_cap'

    logging.info('initialize: CA_cap')
    
    return(CA_cap)


# In[ ]:


def initialize_CA_APCR():
    """
    In current regs (Oct 2017), quantities for APCR for budget years 2013-2020 defined as percentage of budget.   
    2013-2020 specified in regs § 95870(a):
    * (1) One percent of the allowances from budget years 2013-2014;
    * (2) Four percent of the allowances from budget years 2015-2017; and
    * (3) Seven percent of the allowances from budget years 2018-2020.

    In current regs (Oct 2017), quantities for APCR for budget years 2021-2030 defined as total quantities.
    (See § 95871(a) and Table 8-2 (as of Oct 2017))
    
    In proposed new regs (Sep 2018), quantities for APCR for budget years 2021-2030 defined as total quantities.
    (See § 95871(a) and Table 8-2 (as of Sep 2018), which is updated from Oct 2017 version of regs)
    """
    
    logging.info('initialize_CA_APCR')

    CA_cap = prmt.CA_cap
    CA_cap_data = prmt.CA_cap_data
    CA_post_2020_regs = prmt.CA_post_2020_regs

    # for 2013-2020: get cap & reserve fraction from input file
    # calculate APCR amounts
    CA_APCR_fraction = CA_cap_data[CA_cap_data['name']=='CA_APCR_fraction']
    CA_APCR_fraction = CA_APCR_fraction.set_index('year')['data']
    CA_APCR_2013_2020 = CA_cap * CA_APCR_fraction
    CA_APCR_2013_2020 = CA_APCR_2013_2020.loc[2013:2020]

    # for 2021-2031: get APCR amounts from input file
    CA_APCR_2021_2031 = CA_cap_data[CA_cap_data['name']=='CA_APCR']
    CA_APCR_2021_2031 = CA_APCR_2021_2031.set_index('year')['data']

    # only keep through 2030
    CA_APCR_2021_2030 = CA_APCR_2021_2031.loc[2021:2030]

    CA_APCR = CA_APCR_2013_2020.append(CA_APCR_2021_2030)
    CA_APCR.name = 'CA_APCR'

    # new regulations for CA:
    if prmt.CA_post_2020_regs in ['Preliminary_Discussion_Draft', 'Proposed_Regs_Sep_2018']:
        # move additional 2% of cap for 2026-2030 to APCR; 
        # do this by removing equal amount from each annual budget 2021-2030
        # as stated in "Price Concepts" paper, this is 2.272600 MMTCO2e per year
        # and as stated in the "Post-2020 Caps" paper, it would be a total of ~22.7M allowances
        CA_APCR_extra_sum = CA_cap.loc[2026:2030].sum() * 0.02
        CA_APCR_extra_ann = CA_APCR_extra_sum / len(range(2021, 2030+1))
        CA_APCR_new_2021_2030 = CA_APCR.loc[2021:2030] + CA_APCR_extra_ann
        CA_APCR = CA_APCR.loc[2013:2020].append(CA_APCR_new_2021_2030)
    # if other proposals for new regulations, but them here
    else:
        pass
    
    CA_APCR_MI = convert_ser_to_df_MI(CA_APCR)

    logging.info('initialize: CA_APCR')
    
    return(CA_APCR_MI)


# In[ ]:


def initialize_CA_advance():
    """
    Fraction of CA cap that is set aside for advance is defined in regulations.
    
    For 2013-2020: § 95870(b)
    For 2021-2030: § 95871(b)
    
    """
    
    logging.info('initialize: CA_advance')
    
    CA_cap = prmt.CA_cap
    CA_cap_data = prmt.CA_cap_data
    
    CA_advance_fraction = CA_cap_data[CA_cap_data['name']=='CA_advance_fraction']
    CA_advance_fraction = CA_advance_fraction.set_index('year')['data']

    CA_advance = (CA_cap * CA_advance_fraction).fillna(0)
    CA_advance.name ='CA_advance'

    CA_advance_MI = convert_ser_to_df_MI(CA_advance)

    return(CA_advance_MI)


# In[ ]:


def initialize_VRE_reserve():
    """
    DOCSTRINGS
    """
    logging.info('initialize_VRE_reserve')
    
    CA_cap = prmt.CA_cap
    CA_cap_data = prmt.CA_cap_data

    VRE_fraction = CA_cap_data[CA_cap_data['name']=='CA_Voluntary_Renewable_fraction']
    VRE_fraction = VRE_fraction.set_index('year')['data']

    VRE_reserve = CA_cap * VRE_fraction

    for year in range(2021, 2030+1):
        VRE_reserve.at[year] = float(0)

    VRE_reserve.name = 'VRE_reserve'

    VRE_reserve_MI = convert_ser_to_df_MI(VRE_reserve)
    
    return(VRE_reserve_MI)


# In[ ]:


def read_CA_alloc_data():
    """    
    Reads historical allocation data, as well as cap adjustment factors
    
    CA allocations use cap adjustment factor from § 95891, Table 9-2
    
    note: Input file only includes the standard cap adjustment factors.
    
    If need be, can add to input file the non-standard for particular process intensive industries.
    """
    logging.info('read_CA_alloc_data')
    
    CA_alloc_data = pd.read_excel(prmt.input_file, sheet_name='CA alloc data')
    
    return(CA_alloc_data)


# In[ ]:


def initialize_elec_alloc():
    """
    2021-2030 Electrical Distribution Utility Sector Allocation (IOU & POU):

    2021-2030: § 95871(c)(1)
    details determined by 95892(a), with allocation quantities explicitly stated in § 95892 Table 9-4
    (data copied from pdf (opened in Adobe Reader) into Excel; saved in input file)
    but utilities not identified in Table 9-4 as IOU or POU
    so merge with 2013-2020 df, and then compute sums for whole time span 2013-2030
    (also note this does not go through 2031, as cap does)
    """

    logging.info('initialize_elec_alloc')
    
    # create elec_alloc_2013_2020

    # read input file; 
    # has '-' for zero values in some cells; make those NaN, replace NaN with zero; then clean up strings
    df = pd.read_excel(prmt.input_file, sheet_name='CA elec alloc 2013-2020', na_values='-')
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

    elec_alloc_IOU = df['IOU']
    elec_alloc_IOU.name = 'elec_alloc_IOU'
    elec_alloc_POU = df['POU']
    elec_alloc_POU.name = 'elec_alloc_POU'

    # elec_alloc_IOU and elec_alloc_POU are transferred to appropriate accounts later, in consignment section
    
    return(elec_alloc_IOU, elec_alloc_POU)


# In[ ]:


def initialize_nat_gas_alloc(CA_alloc_data):
    # historical data from annual allocation reports; stored in input file
    # have to use these historical values to calculate 2011 natural gas supplier emissions
    # once 2011 natural gas supplier emissions has been calculated, can use equation in regulations for projections

    CA_cap_adjustment_factor = prmt.CA_cap_adjustment_factor
    
    logging.info('initialize: nat_gas_alloc')
    
    nat_gas_alloc = CA_alloc_data.copy()[CA_alloc_data['name']=='nat_gas_alloc']
    nat_gas_alloc['year'] = nat_gas_alloc['year'].astype(int)
    nat_gas_alloc = nat_gas_alloc.set_index('year')['data']

    # not clear from MRR which emissions are credited to natural gas suppliers, or which emissions regs are referring to
    # but can infer what emissions in 2011 ARB used for calculating allocations disbursed to date (2015-2017)
    # emissions in 2011 = reported allocations for year X / adjustment factor for year X
    # can calculate emissions in 2011 from this equation for any particular year;
    # to avoid rounding errors, can calculate mean of ratios from each year
    nat_gas_emissions_2011_inferred = (nat_gas_alloc / CA_cap_adjustment_factor).mean()

    # get last historical year of nat_gas_alloc
    nat_gas_alloc_last_year = nat_gas_alloc.index[-1]

    # calculate allocation for all future years
    for future_year in range(nat_gas_alloc_last_year, 2031+1):
        nat_gas_alloc_future = nat_gas_emissions_2011_inferred * CA_cap_adjustment_factor.at[future_year]
        nat_gas_alloc.at[future_year] = nat_gas_alloc_future

    # add data points with zeros to make later steps easier
    nat_gas_alloc.at[2013] = float(0)
    nat_gas_alloc.at[2014] = float(0)

    # convert units from allowances to MILLION allowances (MMTCO2e)
    nat_gas_alloc = nat_gas_alloc / 1e6

    nat_gas_alloc.name = 'nat_gas_alloc'
    
    return(nat_gas_alloc)


# In[ ]:


def initialize_industrial_etc_alloc(CA_alloc_data):
    
    CA_cap_adjustment_factor = prmt.CA_cap_adjustment_factor
    
    logging.info('initialize: industrial_alloc')
    
    industrial_alloc = CA_alloc_data.copy()[CA_alloc_data['name'].isin(['industrial_alloc', 'industrial_and_legacy_gen_alloc'])]
    industrial_alloc['year'] = industrial_alloc['year'].astype(int)
    industrial_alloc = industrial_alloc.set_index('year')['data']

    # convert units from allowances to MILLION allowances (MMTCO2e)
    industrial_alloc = industrial_alloc/1e6

    industrial_alloc.name = 'industrial_alloc'

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
        water_alloc_year = water_alloc_post_2020_base_level * CA_cap_adjustment_factor[year]
        water_alloc.at[year] = water_alloc_year

    # convert units from allowances to MILLION allowances (MMTCO2e)
    water_alloc = water_alloc / 1e6

    water_alloc.name = 'water_alloc'

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    logging.info('initialize: university_alloc')
    university_alloc = CA_alloc_data.copy()[CA_alloc_data['name']=='university_alloc']
    university_alloc['year'] = university_alloc['year'].astype(int)
    university_alloc = university_alloc.set_index('year')['data']

    university_alloc.name = 'university_alloc'

    # convert units from allowances to MILLION allowances (MMTCO2e)
    university_alloc = university_alloc / 1e6

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    logging.info('initialize: legacy_gen_alloc')
    legacy_gen_alloc = CA_alloc_data.copy()[CA_alloc_data['name']=='legacy_gen_alloc']
    legacy_gen_alloc['year'] = legacy_gen_alloc['year'].astype(int)
    legacy_gen_alloc = legacy_gen_alloc.set_index('year')['data']

    # convert units from allowances to MILLION allowances (MMTCO2e)
    legacy_gen_alloc = legacy_gen_alloc / 1e6

    legacy_gen_alloc.name = 'legacy_gen_alloc'
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    logging.info('initialize: thermal_output_alloc')
    
    # variable allocation
    thermal_output_alloc = CA_alloc_data.copy()[CA_alloc_data['name']=='thermal_output_alloc']
    thermal_output_alloc['year'] = thermal_output_alloc['year'].astype(int)
    thermal_output_alloc = thermal_output_alloc.set_index('year')['data']

    # convert units from allowances to MILLION allowances (MMTCO2e)
    thermal_output_alloc = thermal_output_alloc / 1e6

    thermal_output_alloc.name = 'thermal_output_alloc'

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    logging.info('initialize: waste_to_energy_alloc')
    waste_to_energy_alloc = CA_alloc_data.copy()[CA_alloc_data['name']=='waste_to_energy_alloc']
    waste_to_energy_alloc['year'] = waste_to_energy_alloc['year'].astype(int)
    waste_to_energy_alloc = waste_to_energy_alloc.set_index('year')['data']

    # convert units from allowances to MILLION allowances (MMTCO2e)
    waste_to_energy_alloc = waste_to_energy_alloc / 1e6

    waste_to_energy_alloc.name = 'waste_to_energy_alloc'

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    logging.info('initialize: LNG_supplier_alloc')
    # variable allocation
    LNG_supplier_alloc = CA_alloc_data.copy()[CA_alloc_data['name']=='LNG_supplier_alloc']
    LNG_supplier_alloc['year'] = LNG_supplier_alloc['year'].astype(int)
    LNG_supplier_alloc = LNG_supplier_alloc.set_index('year')['data']

    # convert units from allowances to MILLION allowances (MMTCO2e)
    LNG_supplier_alloc = LNG_supplier_alloc / 1e6

    LNG_supplier_alloc.name = 'LNG_supplier_alloc'

    industrial_etc_alloc_list = [industrial_alloc, water_alloc, university_alloc, legacy_gen_alloc, 
                             thermal_output_alloc, waste_to_energy_alloc, LNG_supplier_alloc]

    industrial_etc_alloc = pd.concat(industrial_etc_alloc_list, axis=1).sum(axis=1)
    industrial_etc_alloc.name = 'industrial_etc_alloc_hist'

    # calculate what allocation would be in case for all assistance factors at 100% for 2018-2020
    # assume that the resulting allocation for each year would be:

    idealized = pd.Series()
    for year in range(2018, 2030+1):
        cap_adj_ratio_year = CA_cap_adjustment_factor.at[year] / CA_cap_adjustment_factor.at[2017]
        idealized.at[year] = industrial_etc_alloc.at[2017] * cap_adj_ratio_year

    # compare against ARB's projection from 2018-03-02 workshop presentation, slide 9
    # (as extracted using WebPlotDigitizer)
    ARB_proj = pd.read_excel(prmt.input_file, sheet_name='ARB allocs to 2030')
    ARB_proj = ARB_proj[['year', 'industrial and other allocation (estimate) [WPD]']].set_index('year')
    ARB_proj = ARB_proj[ARB_proj.columns[0]]
    ARB_proj.name = 'industrial_etc_alloc_ARB_proj'

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

    # identify last historical year of data
    last_hist_year = industrial_alloc.index[-1]

    # combine the 4 pieces: historical, projection with lower assistance factors, trueups_retro, and additional
    industrial_etc_alloc = pd.concat([industrial_etc_alloc.loc[:last_hist_year], 
                                      ARB_proj.loc[last_hist_year+1:], 
                                      CA_trueups_retro, 
                                      CA_additional_2020], 
                                     axis=1).sum(axis=1)
    industrial_etc_alloc.name = 'industrial_etc_alloc'
    
    return(industrial_etc_alloc)


# In[ ]:


def create_consign_historical_and_projection_annual(elec_alloc_IOU, elec_alloc_POU, nat_gas_alloc):
    """
    Create a projection for consignment quantities to 2030.
    
    For now, will have specific start year (2019).
    
    TO DO: Generalize to start projection after the latest historical year with data on annual consignment.
    """
    
    logging.info('create_consign_historical_and_projection_annual')
    
    # calculate annual consignment from input file
    consign_ann = pd.read_excel(prmt.input_file, sheet_name='consign annual')
    consign_ann = consign_ann[consign_ann['name']=='CA_consignment_annual'][['vintage', 'data']]
    consign_ann = consign_ann.set_index('vintage')['data']
    consign_ann.name = 'consign_ann'
    
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

    consign_nat_gas_min_fraction = CA_consign_regs[CA_consign_regs['name']=='CA_natural_gas_min_consign_fraction']
    consign_nat_gas_min_fraction = consign_nat_gas_min_fraction.set_index('year')['data']

    consign_nat_gas_min = nat_gas_alloc * consign_nat_gas_min_fraction
    consign_nat_gas_min.name = 'consign_nat_gas_min'
    
    # analysis of natural gas consignment:
    # if we assume that natural gas allocation is proportional to MRR covered emissions for natural gas distribution...
    # ... for each entity, for those entities that did receive an allocation...
    # ... then we can conclude that IOUs are consigning zero or negligible (~0.1 MMTCO2e) optional amounts...
    # ... above the minimum natural gas consignment
    # then actual nat gas consignment = minimum nat gas consignment
    consign_nat_gas = consign_nat_gas_min.copy()
    consign_nat_gas.name = 'consign_nat_gas'
    
    nat_gas_not_consign = pd.concat([nat_gas_alloc, -1*consign_nat_gas], axis=1).sum(axis=1).loc[2013:2030]
    nat_gas_not_consign.name = 'nat_gas_not_consign'
    
    # infer optional consignment amount (elec & nat gas)
    consign_opt = (consign_ann - consign_elec_IOU - consign_nat_gas.fillna(0)).loc[2013:2030]
    
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

    for year in range(2019, 2030+1):
        consign_elec_POU_year = elec_alloc_POU.at[year] * consign_elec_POU_fraction        
        consign_elec_POU.at[year] = consign_elec_POU_year
        
    elec_POU_not_consign = pd.concat([elec_alloc_POU, -1*consign_elec_POU], axis=1).sum(axis=1).loc[2013:2030]
    elec_POU_not_consign.name = 'elec_POU_not_consign'
    
    
    # ~~~~~~~~~~~~~~~~~~~~~~
    # if we want to distinguish nat gas consign IOU vs POU, 
    # could assume that nat gas allocations are proportional to nat gas distribution covered emissions from each entity
    # note that not all IOUs with natural gas distribution covered emissions (according to MRR) received allocations
    # but all POUs with natural gas distribution covered emissions (according to MRR) did receive allocations

    # note that we only have emissions data for 2015-2016
    # so to split nat gas allocations for 2017-2018 between IOU and POU, 
    # would need to assume each entity receiving an allocation had the same percentage of emissions as in historical data
    # ~~~~~~~~~~~~~~~~~~~~~~
    
    
    # consign_ann: calculate new values for projection years
    for year in range(2019, 2030+1):
        consign_ann.at[year] = consign_elec_IOU.at[year] + consign_elec_POU.at[year] + consign_nat_gas.at[year]
    
    # TO DO: create named tuple for all consigned & not consigned dfs; output this named tuple
    
    return(consign_ann, consign_elec_IOU, consign_nat_gas, consign_elec_POU, nat_gas_not_consign, elec_POU_not_consign)


# In[ ]:


def consign_upsample_historical_and_projection(consign_ann):
    # QUARTERLY VALUES: GET HISTORICAL & CALCULATE PROJECTIONS
    
    qauct_new_avail = prmt.qauct_new_avail
    
    consign_q_hist = qauct_new_avail.loc[qauct_new_avail.index.get_level_values('inst_cat')=='consign']
    
    last_cur_hist_q = consign_q_hist.index.get_level_values('date_level').max()

    # create template row for adding additional rows to consign_hist_proj
    consign_1q_template = consign_q_hist.loc[consign_q_hist.index[-1:]]
    consign_1q_template.at[consign_1q_template.index, 'quant'] = float(0)

    if last_cur_hist_q.quarter < 4:
        # fill in missing quarters for last historical year
        
        # get annual total consigned
        consign_ann_1y = consign_ann.at[last_cur_hist_q.year]
        
        # calculate total already newly available that year
        df = consign_q_hist.loc[consign_q_hist.index.get_level_values('date_level').year==last_cur_hist_q.year]
        consign_1y_to_date = df['quant'].sum()
        
        # calculate remaining to consign
        consign_remaining = consign_ann_1y - consign_1y_to_date

        # number of remaining auctions:
        num_remaining_auct = 4 - last_cur_hist_q.quarter
        
        # average consignment in remaining auctions
        avg_consign = consign_remaining / num_remaining_auct
        
        consign_hist_proj = consign_q_hist.copy()
        
        for proj_q in range(last_cur_hist_q.quarter+1, 4+1):
            proj_date = quarter_period(f"{last_cur_hist_q.year}Q{proj_q}")
            
            # create new row; update date_level and quantity
            consign_new_row = consign_1q_template.copy()
            mapping_dict = {'date_level': proj_date}
            consign_new_row = multiindex_change(consign_new_row, mapping_dict)
            consign_new_row.at[consign_new_row.index, 'quant'] = avg_consign
            
            # set new value in consign_hist_proj
            consign_hist_proj = consign_hist_proj.append(consign_new_row)
        
    # for years after last historical data year (last_cur_hist_q.year)    
    for year in range(last_cur_hist_q.year+1, 2030+1):
        avg_consign = consign_ann.loc[year] / 4
        
        for quarter in [1, 2, 3, 4]:
            proj_date = quarter_period(f"{year}Q{quarter}")

            # create new row; update date_level and quantity
            consign_new_row = consign_1q_template.copy()
            mapping_dict = {'date_level': proj_date, 
                            'vintage': year}
            consign_new_row = multiindex_change(consign_new_row, mapping_dict)
            
            consign_new_row.at[consign_new_row.index, 'quant'] = avg_consign
        
            # set new value in consign_hist_proj
            consign_hist_proj = consign_hist_proj.append(consign_new_row)
    
    prmt.consign_hist_proj = consign_hist_proj
    
    # no return; func sets object attribute prmt.consign_hist_proj


# In[ ]:


def get_QC_allocation_data():
    """
    From input file, import full data set on QC allocations.
    
    Separated by emissions year, date of allocation, and type of allocation (initial, true-up #1, etc.).
    
    """
    
    logging.info(f"initialize: {inspect.currentframe().f_code.co_name} (start)")

    # get more detailed allocation data (for hindcast)
    QC_alloc_hist = pd.read_excel(prmt.input_file, sheet_name='QC alloc data full')
    QC_alloc_hist['allocation quarter'] = pd.to_datetime(QC_alloc_hist['allocation date']).dt.to_period('Q')
    
    # convert units to MMTCO2e
    QC_alloc_hist['quant'] = QC_alloc_hist['quantity to date (tons CO2e)']/1e6
    
    QC_alloc_hist = QC_alloc_hist.drop(['before or after quarterly auction', 
                                        'allocation date',
                                        'quantity to date (tons CO2e)',
                                        'quantity on date for true-ups (tons CO2e)', 
                                        'notes'], 
                                       axis=1)
    
    QC_alloc_hist = QC_alloc_hist.set_index(['allocation for emissions year',
                                             'allocation type',
                                             'allocation quarter'])
    
    # ~~~~~~~~~~~~~~~~~~~~~~
    # isolate initial allocations
    QC_alloc_initial = QC_alloc_hist.loc[QC_alloc_hist.index.get_level_values('allocation type')=='initial']
    QC_alloc_initial.index = QC_alloc_initial.index.droplevel('allocation type')
    
    # make projection for initial allocations
    # take most recent historical data, assume future initial allocations will scale down with cap
    last_year = QC_alloc_initial.index.get_level_values('allocation for emissions year').max()

    df = QC_alloc_initial.loc[QC_alloc_initial.index.get_level_values('allocation quarter').year==last_year]
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
    
    # ~~~~~~~~~~~~~~~~~~~~~~
    # calculate true-ups for each distribution from cumulative data reported
    # (use diff to calculate difference between a given data point and previous one)
    # (each set has an initial value before true-ups, so diff starts with diff between initial and true-up #1)
    QC_alloc_trueups = QC_alloc_hist.groupby('allocation for emissions year').diff().dropna()
    QC_alloc_trueups.index = QC_alloc_trueups.index.droplevel('allocation type')
    
    # make projection for true-up allocations, following after latest year with a first true-up (in Q3)
    Q3_trueup_mask = QC_alloc_trueups.index.get_level_values('allocation quarter').quarter==3
    Q3_trueups = QC_alloc_trueups.copy().loc[Q3_trueup_mask]
    not_Q3_trueups = QC_alloc_trueups.loc[~Q3_trueup_mask]
    
    last_year = Q3_trueups.index.get_level_values('allocation for emissions year').max()
    
    # first true-ups are 25% of total estimated allocation, whereas initial alloc are 75% of total est. alloc
    # therefore first true-ups are one-third (25%/75%) of the initial true-up
    # in projection, do not model any further true-ups after first true-ups (assume no revisions of allocation)
    for year in range(last_year+1, 2030+1):
        init_last_year_plus1 = QC_alloc_initial.at[(year, f'{year}Q1'), 'quant']
        first_trueup_quant = init_last_year_plus1 / 3
        Q3_trueups.at[(year, quarter_period(f'{year+1}Q3')), 'quant'] = first_trueup_quant
        
    Q3_trueups = Q3_trueups.dropna()
    
    # recombine:
    QC_alloc_trueups = pd.concat([Q3_trueups, not_Q3_trueups])
    
    # ~~~~~~~~~~~~~~~~~~~~~
    # also calculate full (est.) allocation for projection years
    # used for setting aside this quantity from cap, for initial alloc and first true-up
    
    # calculate full allocation (100%) from the initial allocation (75% of full quantity)
    QC_alloc_full_proj = QC_alloc_initial_proj * 100/75
    
    # set object attributes
    prmt.QC_alloc_initial = QC_alloc_initial
    prmt.QC_alloc_trueups = QC_alloc_trueups
    prmt.QC_alloc_full_proj = QC_alloc_full_proj
    
    # no return; func sets object attributes


# In[ ]:


def get_compliance_events():
    """
    From compliance reports, create record of compliance events (quantities surrendered at specific times).
    
    Note that quantities surrendered are *not* the same as the covered emissions that have related obligations.
    
    """
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (start)")    
    
    # get record of retirements (by vintage) from compliance reports
    df = pd.read_excel(prmt.input_file, sheet_name='annual compliance reports')
    df = df.set_index('year of compliance event')

    df = df.drop('for 2013-2014 full compliance period')
    df = df.drop(['CA checksum', 'QC checksum'], axis=1)
    df = df.drop(['CA entities retired total (all instruments)', 
                                                  'QC entities retired total (all instruments)'], axis=1)
    df = df.dropna(how='all')

    # convert compliance report values into compliance events (transfers that occur each Nov)
    # sum allowances by vintage, combining surrenders by CA & QC entities
    df = df.copy()
    df.columns = df.columns.str.replace('CA entities retired ', '')
    df.columns = df.columns.str.replace('QC entities retired ', '')
    df.columns = df.columns.str.replace('allowance vintage ', '')
    df.columns.name = 'vintage or type'

    df = df.stack()
    df = pd.DataFrame(df, columns=['quant'])
    df = df.loc[df['quant'] > 0]
    df = df.groupby(['year of compliance event', 'vintage or type']).sum().reset_index()
    df['compliance_date'] = pd.to_datetime(df['year of compliance event'].astype(str)+'-11-01').dt.to_period('Q')

    # rename 'Early Reduction credits'
    df['vintage or type'] = df['vintage or type'].str.replace('Early Reduction credits', 'early_action')

    df = df[['compliance_date', 'vintage or type', 'quant']].set_index(['compliance_date', 'vintage or type'])

    prmt.compliance_events = df
    
    # no return; func sets object attribute


# # TEST FUNCTIONS

# In[ ]:


def test_cols_and_indexes_before_transfer(to_acct_MI):
    """
    {{{INSERT DOCSTRINGS}}}
    """
    if prmt.verbose_log == True:
        logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # check that to_acct_MI has only 1 column & that it has MultiIndex
    if len(to_acct_MI.columns)==1 and isinstance(to_acct_MI.index, pd.MultiIndex):
        pass # test passed
    
    elif len(to_acct_MI.columns)>1:
        print(f"{prmt.test_failed_msg} df to_acct_MI has more than 1 column. Here's to_acct_MI:")
        print(to_acct_MI)
    
    elif len(to_acct_MI.columns)==0:
        print(f"{prmt.test_failed_msg} df to_acct_MI has no columns. Here's to_acct_MI:")
        print(to_acct_MI)
    
    else: # closing "if len(to_acct_MI.columns)==1..."
        print(f"{prmt.test_failed_msg} Something else going on with df to_acct_MI columns and/or index. Here's to_acct_MI:")
        print(to_acct_MI)


# In[ ]:


def test_for_duplicated_indices(df, parent_fn):
    """
    Test to check a dataframe (df) for duplicated indices, and if any, to show them (isolated and in context).
    """
    
    if prmt.verbose_log == True:
        logging.info(f"{inspect.currentframe().f_code.co_name}")

    dups = df.loc[df.index.duplicated(keep=False)]
    
    if dups.empty == False:
        print(f"{prmt.test_failed_msg} df.index.duplicated when running {parent_fn}; here are duplicated indices:")
        print(dups)
        
        # get the acct_names that show up in duplicates
        dup_acct_names = dups.index.get_level_values('acct_name').unique().tolist()
        
#         for dup_acct_name in dup_acct_names:
#             print(f"During {parent_fn}, dups in acct_name {dup_acct_name}; here's the full account:")
#             print(df.loc[df.index.get_level_values('acct_name')==dup_acct_name])
    elif df[df.index.duplicated(keep=False)].empty == True:
        # test passed: there were no duplicated indices
        pass
    else:
        print(f"{prmt.test_failed_msg} During {parent_fn}, was meant to be check for duplicated indices.")


# In[ ]:


def test_if_value_is_float_or_np_float64(test_input):
    
    if prmt.verbose_log == True:
        logging.info(f"{inspect.currentframe().f_code.co_name} (start)")

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
    
    if prmt.verbose_log == True:
        logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # check for conservation of instruments within all_accts
    all_accts_end_sum = all_accts['quant'].sum()
    diff = all_accts_end_sum - all_accts_sum_init
    if abs(diff) > 1e-7:
        print(f"{prmt.test_failed_msg}: In {inspect.currentframe().f_code.co_name}, instruments were not conserved. Diff: %s" % diff)
        print(f"Was for df named {remove_name}")
    else:
        pass


# In[ ]:


def test_conservation_simple(df, df_sum_init, parent_fn):
    
    if prmt.verbose_log == True:
        logging.info(f"{inspect.currentframe().f_code.co_name}")
    
    df_sum_final = df['quant'].sum()
    diff = df_sum_final - df_sum_init
    
    if abs(diff) > 1e-7:
        print(f"{prmt.test_failed_msg} Allowances not conserved in {parent_fn}")
    else:
        pass


# In[ ]:


def test_conservation_against_full_budget(all_accts, juris, parent_fn):
    """additional conservation check, using total allowance budget"""

    CA_cap = prmt.CA_cap
    QC_cap = prmt.QC_cap
    
    if juris == 'CA':
        if cq.date <= quarter_period('2017Q4'):
            budget = CA_cap.loc[2013:2020].sum()
            
        # additional allowances vintage 2021-2030 assumed to have been added at start of 2018Q1 (Jan 1)
        # (all we know for sure is they were first included in 2017Q4 CIR)
        # budget will be the same through 2030Q4, as far as we know at this point
        # but in some future year, perhaps 2028, post-2030 allowances would likely be added to the system
        elif cq.date >= quarter_period('2018Q1') and cq.date <= quarter_period('2030Q4'):
            budget = CA_cap.loc[2013:2030].sum()
        else:
            print("Need to fill in CA budget after 2030, if those in Oct 2017 regs are retained.")
            
    elif juris == 'QC':
        if cq.date == quarter_period('2013Q4'):
            budget = QC_cap.loc[2013:2020].sum()

        elif cq.date >= quarter_period('2014Q1') and cq.date <= quarter_period('2017Q4'):
            # add Early Action allowances to budget
            budget = QC_cap.loc[2013:2020].sum() + 2.040026 # units: MMTCO2e

        # additional allowances vintage 2021-2030 assumed to have been added at start of 2018Q1 (Jan 1)
        # (all we know for sure is they were first included in 2017Q4 CIR)
        # budget will be the same through 2030Q4, as far as we know at this point
        # but in some future year, perhaps 2028, post-2030 allowances would likely be added to the system
        elif cq.date >= quarter_period('2018Q1') and cq.date <= quarter_period('2030Q4'):
            budget = QC_cap.loc[2013:2030].sum() + 2.040026 # units: MMTCO2e

        else:
            print("Error" + "! QC budget not defined after 2030.")

    elif juris == 'ON':
        # only represent net flow from ON into CA-QC; 
        # these may be any juris, but for purposes of tracking they are recorded as juris 'ON'
        
        if cq.date < quarter_period('2018Q2'):
            budget = 0
        
        # as noted in 2018Q2 CIR: 
        # "As of [July 3, 2018], there are 13,186,967 more compliance instruments held in California and Québec 
        # accounts than the total number of compliance instruments issued by those two jurisdictions alone."
  
        elif cq.date >= quarter_period('2018Q2') and cq.date <= quarter_period('2017Q4'):
            # add Early Action allowances to budget
            budget = 13.186967 # units: MMTCO2e
    
    else:
        print("Error" + f"! Some other juris not in list; juris is: {juris}")
            
    diff = all_accts['quant'].sum() - budget

    if abs(diff) > 1e-7:
        print(f"{prmt.test_failed_msg} Allowances not conserved in {parent_fn}.")
        print(f"(Final value minus full budget ({budget} M) was: {diff} M.)")
        # print(f"Was for auct_type: {auct_type}")
    else:
        pass


# In[ ]:


def test_snaps_end_Q4_sum():
    """Check for modifications to snaps_end_Q4 by checking sum."""
    
    if prmt.snaps_end_Q4['quant'].sum() == prmt.snaps_end_Q4_sum:
        # no change to sum of prmt.snaps_end_Q4; equal to original sum calculated in model initialization
        pass
    else:
        print(f"{prmt.test_failed_msg} snaps_end_Q4 sum has changed from initial value.")


# # MAIN FUNCTIONS

# In[ ]:


def create_annual_budgets_in_alloc_hold(all_accts, ser):
    """
    Creates allowances for each annual budget, in the Allocation Holding account (alloc_hold).
    
    Does this for each juris.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    df = pd.DataFrame(ser)
    
    if len(df.columns==1):
        df.columns = ['quant']
    else:
        print("Error" + "! In convert_cap_to_MI, len(df.columns==1) was False.")
        
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
    
    if prmt.run_tests == True:
        test_cols_and_indexes_before_transfer(to_acct_MI)            
    
    # change column name of to_acct_MI, but only if to_acct_MI is a df with one column and MultiIndex
    # rename column of to_acct_MI, whatever it is, to 'to_acct_MI_quant'
    # filter to vintages specified
    to_acct_MI.columns = ['quant']
    to_acct_MI_in_vintage_range = to_acct_MI[to_acct_MI.index.get_level_values('vintage').isin(vintage_range)]
    
    # ~~~~~~~~~~~~~~~`
    # create df named remove, which is negative of to_acct_MI; rename column
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
    to_acct_name = to_acct_MI.index.get_level_values('acct_name').unique().tolist()
    
    if to_acct_name == ['APCR_acct']:        
        mapping_dict = {'vintage': 2200}
        to_acct_MI_in_vintage_range = multiindex_change(to_acct_MI_in_vintage_range, mapping_dict)
        to_acct_MI_in_vintage_range = to_acct_MI_in_vintage_range.groupby(level=prmt.standard_MI_names).sum()

    elif len(to_acct_name) != 1:
        print("Error" + "! There was more than one to_acct_name in df that was intended to be for APCR_acct only.")
    
    else:
        pass
    # ~~~~~~~~~~~~~~~

    # separate out any rows with negative values
    all_accts_pos = all_accts.loc[all_accts['quant']>0]
    all_accts_neg = all_accts.loc[all_accts['quant']<0]
    
    # combine dfs to subtract from from_acct & add to_acct_MI_1v
    # (groupby sum adds the positive values in all_accts_pos and the neg values in remove)
    all_accts_pos = pd.concat([all_accts_pos, remove, to_acct_MI_in_vintage_range], sort=True)
    all_accts_pos = all_accts_pos.groupby(level=prmt.standard_MI_names).sum()
    
    # recombine pos & neg
    all_accts = all_accts_pos.append(all_accts_neg)
    
    if prmt.run_tests == True:
        name_of_allowances = to_acct_MI.index.get_level_values('inst_cat').unique().tolist()[0]
        test_conservation_during_transfer(all_accts, all_accts_sum_init, name_of_allowances)
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")

    return(all_accts)


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
    to_acct_MI_1v = to_acct_MI[to_acct_MI.index.get_level_values('vintage')==(cq.date.year+1)]
    
    # create df named remove, which is negative of to_acct_MI; rename column
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


# In[ ]:


def transfer__from_VRE_acct_to_retirement(all_accts):   
    """
    Transfers allocations from allocation holding account (alloc_hold) to other accounts.
    
    Works for APCR (to APCR_acct), VRE (to VRE_acct), and advance (to auct_hold).
    
    Destination account is contained in to_acct_MI metadata.
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    VRE_retired = prmt.VRE_retired
    
    all_accts_sum_init = all_accts['quant'].sum()

    try:
        VRE_retired_1q = VRE_retired.xs(cq.date, level='CIR_date', drop_level=False)

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
        mapping_dict = {'acct_name': 'retirement', 
                        'status': 'retired'}
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


# In[ ]:


def transfer_consign__from_limited_use_to_auct_hold_2012Q4_and_make_available(all_accts):
    """
    Specified quantities in limited_use account of a particular vintage will be moved to auct_hold.

    Only for anomalous auction 2012Q4 (CA-only), in which vintage 2013 consignment were sold at current auction.
    """       
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    qauct_new_avail = prmt.qauct_new_avail
    
    # pre-test for conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
        
    # look up quantity consigned in 2012Q4 from historical record (consign_2012Q4)
    # this anomalous fn runs when cq.date = 2012Q4
    quarter_2012Q4 = quarter_period('2012Q4')
    consign_2012Q4_vintage = 2013
    consign_2012Q4 = qauct_new_avail.at[('auct_hold', 'CA', 'current', 'consign', consign_2012Q4_vintage, 
                                             'new', 'not_avail', quarter_2012Q4, prmt.NaT_proxy, prmt.NaT_proxy),
                                           'quant'].sum()
    
    if prmt.run_tests == True:
        test_if_value_is_float_or_np_float64(consign_2012Q4)
    
    # get allowances in limited_use, inst_cat=='consign', for specified vintage
    # and calculate sum of that set
    mask1 = all_accts.index.get_level_values('acct_name')=='limited_use'
    mask2 = all_accts.index.get_level_values('inst_cat')=='consign'
    mask3 = all_accts.index.get_level_values('vintage')==cq.date.year+1
    mask = (mask1) & (mask2) & (mask3)
    consign_not_avail = all_accts.loc[mask]
    quant_not_avail = consign_not_avail['quant'].sum()
    
    if prmt.run_tests == True:
        # TEST:
        if len(consign_not_avail) != 1:
            print(f"{prmt.test_failed_msg} Expected consign_not_avail to have 1 row. Here's consign_not_avail:")
            print(consign_not_avail)
            print("Here's all_accts.loc[mask1] (limited_use):")
            print(all_accts.loc[mask1])
        # END OF TEST
    
    # split consign_not_avail to put only the specified quantity into auct_hold; 
    # rest stays in limited_use
    consign_avail = consign_not_avail.copy()
    
    # consign_avail and consign_not_avail have same index (before consign avail index updated below)
    # use this common index for setting new values for quantity in each df
    # (only works because each df is a single row, as tested for above)
    index_first_row = consign_avail.index[0]
    
    # set quantity in consign_avail, using consign_2012Q4 (input/argument for this function)
    consign_avail.at[index_first_row, 'quant'] = consign_2012Q4
    
    # update metadata: put into auct_hold & make them available in cq.date (2012Q4)
    # this fn does not make these allowances available; this will occur in separate fn, at start of cq.date
    mapping_dict = {'acct_name': 'auct_hold', 
                    'newness': 'new', 
                    'date_level': cq.date, 
                    'status': 'available'}
    consign_avail = multiindex_change(consign_avail, mapping_dict)

    # update quantity in consign_not_avail, to remove those consigned for next_q
    consign_not_avail.at[index_first_row, 'quant'] = quant_not_avail - consign_2012Q4
    
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


def create_qauct_new_avail():
    """
    Create new df qauct_new_avail.
    
    Runs within initialize_model_run (so can't use modelInitialization)
    """
    
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (start)")

    qauct_hist = prmt.qauct_hist
    
    # create df: only newly available
    df = qauct_hist.copy()
    df = df.drop(['market', 'Available', 'Sold', 'Unsold' , 'Redesignated'], axis=1) 
    df = df.rename(columns={'Newly available': 'quant'})

    # add other metadata rows to make it include all prmt.standard_MI_names
    df['acct_name'] = 'auct_hold'
    df['newness'] = 'new'
    df['status'] = 'not_avail' # will become available, but isn't yet
    df['unsold_di'] = prmt.NaT_proxy
    df['unsold_dl'] = prmt.NaT_proxy
    df['units'] = 'MMTCO2e'

    df = df.set_index(prmt.standard_MI_names)
    
    # rename & copy (to avoid problem with slices)
    qauct_new_avail = df.copy()
        
    prmt.qauct_new_avail = qauct_new_avail
    # no return; func sets object attribute prmt.qauct_new_avail


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
    all_accts = transfer__from_alloc_hold_to_specified_acct(all_accts, prmt.CA_APCR_MI, 2013, 2020)

    # transfer advance into auct_hold
    all_accts = transfer__from_alloc_hold_to_specified_acct(all_accts, prmt.CA_advance_MI, 2013, 2020)

    # transfer VRE allowances out of alloc_hold, into VRE_acct (for vintages 2013-2020)
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


# In[ ]:


def process_CA_quarterly(all_accts):

    """
    Function that is used in the loop for each quarter, for each juris.
    
    Applies functions defined earlier, as well as additional rules
    
    Order of sales for each jurisdiction set by jurisdiction-specific functions called within process_quarter.
    
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    latest_historical_year_cur = prmt.qauct_new_avail.index.get_level_values('date_level').year.max()
    
    # pre-test for conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    # object "scenario" holds the data for a particular scenario in various attributes (scenario_CA.avail_accum, etc.)

    # START-OF-QUARTER STEPS (INCLUDING START-OF-YEAR) ***********************************************
    
    # process retirements for EIM and bankruptcies (CA only)
    if cq.date.quarter == 4:
        
        # process EIM Outstanding in Q4, prior to auctions (required to be done before Nov 1 compliance deadline)
        # retire any allowances to account for EIM Outstanding Emissions
        all_accts = retire_for_EIM_outstanding(all_accts)

        # process bankruptcy retirements at same time
        # retire any allowances to account for bankruptcies
        all_accts = retire_for_bankruptcy(all_accts)

    else: # cq.date.quarter != 4
        pass

    
    # --------------------------------------------
    
    if cq.date.quarter == 1:
        # start-of-year (Jan 1)
        # on Jan 1 each year, all alloc in ann_alloc_hold are transferred to comp_acct or gen_acct            
        all_accts = transfer_CA_alloc__from_ann_alloc_hold_to_general(all_accts)

        if cq.date.year <= latest_historical_year_cur:
            # start-of-year (Jan 1???): 
            # for current auction, state-owned, vintage==cq.date.year, transfer of annual quantity of allowances
            all_accts = transfer_cur__from_alloc_hold_to_auct_hold_historical(all_accts, 'CA')

            # for current auction, state-owned, sum newly avail & unsold adv, upsample, assign 'date_level'
            all_accts = cur_upsample_avail_state_owned_historical(all_accts, 'CA')

        elif cq.date.year > latest_historical_year_cur:
            # start-of-year (Jan 1???): 
            # for current auction, state-owned, vintage==cq.date.year, transfer of annual quantity of allowances
            all_accts = transfer_cur__from_alloc_hold_to_auct_hold_projection(all_accts, 'CA')

            # for current auction, state-owned, sum newly avail & unsold adv, upsample, assign date_level
            all_accts = cur_upsample_avail_state_owned_projection(all_accts, 'CA')

        if cq.date.year >= 2013 and cq.date.year <= 2027:  
            # start-of-year (Jan 1???): upsample of allowances for advance auction (before Q1 auctions)
            # note that the model does not attempt to simulate advance auctions for vintages after 2027
            all_accts = upsample_advance_all_accts(all_accts)
        else:
            pass

#         # for Q1, take snap (~Jan 5):
#         # after transferring CA alloc out of ann_alloc_hold (Jan 1)
#         # and before Q1 auctions (~Feb 15)  
#         take_snapshot_CIR(all_accts, 'CA')
    
    else: # cq.date.quarter != 1
#         # for Q2-Q4, take snap before auction (no special steps at the start of each quarter)
#         take_snapshot_CIR(all_accts, 'CA')
        pass
    
    # END OF START-OF-QUARTER STEPS

    # ADVANCE AUCTIONS ********************************************************
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
    
    # use new version of fn for updating reintro eligibility
    update_reintro_eligibility('CA')
    
    if cq.date.quarter == 4:        
        # Q4 PROCESSING AFTER AUCTION **********************************************
        # this includes transfer of consigned portion of alloc into limited_use
        logging.info(f"for {cq.date}, Q4 processing after auction: start")
        
        # end-of-year: move advance unsold to current auction
        all_accts = adv_unsold_to_cur_all_accts(all_accts)        
        
        # check for unsold from current auctions, to retire for bankruptcies
        # TO DO: ADD NEW FUNCTION
            
        # note: the transfer allocation step below moves annual consigned allowances into limited_use
        # this needs to happen before allowances for Q1 of next year can be moved from limited_use to auct_hold
        if cq.date.year >= 2013:       
            # transfer allocations (consigned & not consigned)
         
            # transfer all allocations
            # (fn only transfers 1 vintage at a time, vintage == cq.date.year + 1)
            all_accts = transfer_CA_alloc__from_alloc_hold(all_accts, prmt.CA_alloc_MI_all)

            # disabled func below; at the moment, it is only set up for QC
            # all_accts = transfer_cur__from_alloc_hold_to_auct_hold_new_avail_anomalies(all_accts, 'CA')
            
            # for consign, groupby sum to get rid of distinctions between types (IOU, POU)
            all_accts = consign_groupby_sum_in_all_accts(all_accts)

        else:
            # closing "if cq.date.year >= 2013:"
            # end of transfer allocation process
            pass
        
        logging.info(f"for {cq.date}, Q4 processing after auction: end")
    
    else: 
        # closing "if cq.date.quarter == 4:"
        pass
    
    # END-OF-QUARTER (EVERY QUARTER) *****************************************
    logging.info("end-of-quarter processing (every quarter) - start")
    
    if prmt.run_tests == True:  
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_for_negative_values(all_accts, parent_fn)
        
    # check for unsold from current auctions, to roll over to APCR
    all_accts = transfer_unsold__from_auct_hold_to_APCR(all_accts)

    # check for VRE retirement (historical data only; assumes no future VRE retirements)
    all_accts = transfer__from_VRE_acct_to_retirement(all_accts)

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
    
    logging.info("end-of-quarter processing (every quarter) - end")
    
    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)        
        test_conservation_against_full_budget(all_accts, 'CA', parent_fn)  
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)
# end of process_CA_quarterly


# In[ ]:


def process_QC_quarterly(all_accts):

    """
    Function that is used in the loop for each quarter, for each juris.
    
    Applies functions defined earlier, as well as additional rules
    
    Order of sales for each jurisdiction set by jurisdiction-specific functions called within process_quarter.
    
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    latest_historical_year_cur = prmt.qauct_new_avail.index.get_level_values('date_level').year.max()
    
    # pre-test for conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    # object "scenario" holds the data for a particular scenario in various attributes (scenario_QC.avail_accum, etc.)

    # START-OF-QUARTER STEPS (INCLUDING START-OF-YEAR) ***********************************************

    if cq.date.quarter == 1:
        # start-of-year (Jan 1???): transfer of allowances for current auction

        if cq.date.year <= latest_historical_year_cur:
            # start-of-year (Jan 1???): for current auction, transfer of annual quantity of allowances
            all_accts = transfer_cur__from_alloc_hold_to_auct_hold_historical(all_accts, 'QC')

            # calculate
            all_accts = transfer_cur__from_alloc_hold_to_auct_hold_new_avail_anomalies(all_accts, 'QC')

            all_accts = cur_upsample_avail_state_owned_historical(all_accts, 'QC')

        elif cq.date.year > latest_historical_year_cur:
            # start-of-year (Jan 1???): for current auction, transfer of annual quantity of allowances
            all_accts = transfer_cur__from_alloc_hold_to_auct_hold_projection(all_accts, 'QC')

            # start-of-year (Jan 1???): for current auction, sum newly avail & unsold adv, upsample, assign date_level
            all_accts = cur_upsample_avail_state_owned_projection(all_accts, 'QC')


        if cq.date.year >= 2014 and cq.date.year <= 2027:  
            # start-of-year (Jan 1???): upsample of allowances for advance auction (before Q1 auctions)
            # note that the model does not attempt to simulate advance auctions for vintages after 2027
            all_accts = upsample_advance_all_accts(all_accts)
        else:
            pass

#         # for Q1, take snap (~Jan 5):
#         # before transferring QC alloc out of ann_alloc_hold (~Jan 15)
#         # and before Q1 auctions (~Feb 15)
#         take_snapshot_CIR(all_accts, 'QC')

        # start-of-year (Jan 15): transfer QC allocation, initial quantity (75% of estimated ultimate allocation)           
        all_accts = transfer_QC_alloc_init__from_alloc_hold(all_accts)
    
    else: # cq.date.quarter != 1
#         # for Q2-Q4, take snap before auction (no special steps at the start of each quarter)
#         take_snapshot_CIR(all_accts, 'QC')
        pass
    
    # END OF START-OF-QUARTER STEPS

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
    
    # use new version of fn for updating reintro eligibility
    update_reintro_eligibility('QC')
    
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
    
    if prmt.run_tests == True:  
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_for_negative_values(all_accts, parent_fn)

    # September true-ups definitely after auction
    # May auctions might be before auction; not clear; will assume they occur after auctions as well
    # check for QC allocation true-ups; if any, transfer from alloc_hold to gen_acct       
    all_accts = transfer_QC_alloc_trueups__from_alloc_hold(all_accts)
    
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


# In[ ]:


def avail_accum_append(all_accts, avail_accum, auct_type_specified):
    """
    Append allowances available at auction to avail_accum. Runs for advance and current auctions.
    """
    
    if prmt.verbose_log == True:
        logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # record allowances available in each auction
    avail_1q = all_accts.loc[(all_accts.index.get_level_values('status')=='available') & 
                             (all_accts.index.get_level_values('auct_type')==auct_type_specified)]

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
            
    avail_accum = avail_accum.append(avail_1q)
    
    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_for_duplicated_indices(avail_accum, parent_fn)
        test_for_negative_values(avail_accum, parent_fn)

    return(avail_accum)


# In[ ]:


def CA_state_owned_make_available(all_accts, auct_type):
    """
    State-owned allowances in auct_hold are made available when date_level == cq.date.
    
    Works for current auction and advance auction; specified by argument auct_type.
    
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


# In[ ]:


def redesignate_unsold_advance_as_advance(all_accts, juris):
    """
    Redesignation of unsold allowances from advance auctions, to later advance auctions.
    
    Only applies to CA; QC does not have similar rule.
    
    Based on regulations:
    CA: [CA regs Oct 2017], § 95911(f)(3)
    QC: [QC regs Jan 2018], Section 54. states that unsold advance will only be redesignated as current
    
    If advance allowances remain unsold in one auction, they can be redesignated to a later advance auction.
    But this will only occur after two consecutive auctions have sold out (sold above the floor price).
    If any advance allowances remain unsold at the end of a calendar year, they are retained for 
    redesignation to a later current auction.
    
    Therefore the only situation in which allowances unsold in advance auctions can be redesignated 
    to another advance auction is if:
    1. some allowances are unsold in advance auction in Q1
    2. Q2 and Q3 advance auctions sell out
    And therefore the redesignations can only occur in Q4 of any given year
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
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
        
#         # for debugging
#         if use_fake_data == True:
#             # for 2017Q4, override actual value for adv sales in 2017Q2; set to 100%
#             # this allows redesignation of unsold from 2017Q1 in 2017Q4
#             if cq.date == quarter_period('2017Q4'):
#                 sales_pct_adv_Q2 = float(1)
#         # end debugging
        
        if sales_pct_adv_Q2 == float(1) and sales_pct_adv_Q3 == float(1):
            # 100% of auction sold; redesignate unsold from Q1, up to limit
            
            # first get the quantity available before reintro
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
            
            if len(unsold_adv_Q1) == 1:
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
                # len(unsold_adv_Q1) != 1
                print("Error" + "! Selection of unsold_adv_Q1 did not return a single row; here's unsold_adv_Q1:")
                print(unsold_adv_Q1)
                print()
        else: 
            # end of "if sales_pct_adv_Q2 == float(1) ..."
            pass
    else: 
        # end of "if sales_pct_adv_Q1 < float(1)"
        pass
    
    return(all_accts)


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
    # clean-up
    all_accts = all_accts.loc[(all_accts['quant']>1e-7) | (all_accts['quant']<-1e-7)]

    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)


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


# In[ ]:


def redesignate_unsold_current_auct(all_accts, juris):
    """
    Redesignates state-owned allowances that are eligible, changing 'status' to 'available'.
    
    (Consignment are redesignated by fn make)
    
    Note that this function only redesignates unsold from current auctions to later current auctions. 
    
    This function doesn't redesignate unsold advance to later advance auctions.
    
    For applicable regs, see docstrings in functions called below: 
    redes_consign & reintro_update_unsold_all_juris
    
    """
    
    if juris == 'CA':
        cur_sell_out_counter = scenario_CA.cur_sell_out_counter
        reintro_eligibility = scenario_CA.reintro_eligibility
    elif juris == 'QC':
        cur_sell_out_counter = scenario_QC.cur_sell_out_counter
        reintro_eligibility = scenario_QC.reintro_eligibility
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    logging.info(f"in {cq.date} juris {juris}, cur_sell_out_counter: {cur_sell_out_counter}")
    logging.info(f"in {cq.date} juris {juris}, reintro_eligibility: {reintro_eligibility}")
    
    # pre-test for conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    # only do things in this function if reintro_eligibility == True
    if reintro_eligibility == True:

        # ***** redesignation of advance as advance is done by fn redesignate_unsold_advance_as_advance *****
        
        # ***** redesignation of consignment is done by fn consign_make_available_incl_redes *****

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~
        # redesignate unsold current state-owned (aka reintro)

        if prmt.run_tests == True:
            # TEST: in all_accts, are available allowances only in auct_hold? & have only 'date_level'==cq.date? 
            # (if so, then selection below for auct_type current & status available will work properly)
            available_sel = all_accts.loc[all_accts.index.get_level_values('status')=='available']
            
            if available_sel.empty == False:
                # TEST: are avail only in auct_hold?
                if available_sel.index.get_level_values('acct_name').unique().tolist() != ['auct_hold']:
                    print(f"{prmt.test_failed_msg} Available allowances in account other than auct_hold. Here's available:")
                    print(available_sel)
                else:
                    pass
        
                # TEST: do avail have only date_level == cq.date?
                if available_sel.index.get_level_values('date_level').unique().tolist() != [cq.date]:
                    print(f"{prmt.test_failed_msg} Available allowances have date_level other than cq.date (%s). Here's available:" % cq.date)
                    print(available_sel)
                else:
                    pass
            
            else: # available_sel.empty == True
                print("Warning" + f"! In {cq.date}, {inspect.currentframe().f_code.co_name}, available_sel is empty.")
                print("Because available_sel is empty, show auct_hold:")
                print(all_accts.loc[all_accts.index.get_level_values('acct_name')=='auct_hold'])
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


# In[ ]:


def calculate_max_cur_reintro(all_accts, juris):
    """
    Calculate the maximum quantity of state-owned allowances that went unsold at current auction that can be reintroduced.

    Based on regulations:
    CA: [CA regs Oct 2017], § 95911(f)(3)(C)
    QC: [QC regs Sep 2017], Section 54
    ON: [ON regs Jan 2018], Section 58(4)3
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


# In[ ]:


def reintro_update_unsold_1j(all_accts, juris, max_cur_reintro_1j_1q):
    """
    Takes unsold allowances, reintro some based on rules.
    
    This function is called only when reintro_eligibility == True.
    
    Rules on redesignation of unsold state-owned allowances (aka reintroduction):
    CA: [CA regs Oct 2017], § 95911(f)(3)(B) & (C)
    QC: [QC regs Sep 2017], Section 54 (paragraph 1)
    ON: [ON regs Jan 2018], Section 58(4)1
    
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
    
    # QC anomalies: add additional masks:
    if cq.date == quarter_period('2015Q2'):
        # only reintro vintage 2013
        mask6 = all_accts.index.get_level_values('vintage')==2013
        mask = mask & (mask6)
        
        reintro_eligible_1j = all_accts.loc[mask]
        
    elif cq.date == quarter_period('2015Q3') or cq.date == quarter_period('2015Q4'):
        # block reintro
        reintro_eligible_1j = prmt.standard_MI_empty.copy()
        
    else:
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
                
                # set new value for 'quant'; delete rows with zero quantity
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


# In[ ]:


def process_auction_cur_CA_all_accts(all_accts):
    """
    Processes current auction for CA, applying the specified order of sales (when auctions don't sell out).
    
    Order of sales based on regs:
    CA: [CA regs Oct 2017], § 95911(f)(1)

    CA: for consignment, how to split sales between entities:
    [CA regs Oct 2017], § 95911(f)(2)    
    
    Notes: Once it is confirmed to be working properly, this could be simplified by:
    1. not re-doing filtering from scratch each batch of allowances
    2. finishing new fn avail_to_sold_all_accts, to avoid repetitive code
    
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
            print("Warning" + "! avail_for_test is empty.")
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
        mapping_dict = {'status': 'sold', 'acct_name': 'gen_acct'}
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
        # (code adapted from avail_to_sold)

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
                print(f"{prmt.test_failed_msg} Allowances not conserved in fn process_auction_cur_CA_all_accts, after consignment sales.")
                print("diff = all_accts_after_consign_sales - all_accts_sum_init:")
                print(diff)
                print("all_accts_sum_init: %s" % all_accts_sum_init)
                print("consign_sold_1q sum: %s" % consign_sold_1q['quant'].sum())
                print("consign_unsold_1q sum: %s" % consign_unsold_1q['quant'].sum())
                print("not_consign_avail_1q sum: %s" % not_consign_avail_1q['quant'].sum())
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
        # (code adapted from avail_to_sold)
        
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
        # (code adapted from avail_to_sold)
        
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
        # all_accts = all_accts.groupby(prmt.standard_MI_names).sum()

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
        all_accts = unsold_update_status(all_accts)

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


def update_reintro_eligibility(juris):
    """
    Updates reintro_eligibility (attribute of object) based on results of cq.date auction.
    
    Selects auction sales percentages for specified jurisdiction (to handle separate markets).
    
    For citation of regs about reintro for each jurisdiction, see docstring for reintro_update_unsold_1j.
    """
    
    # set local variables cur_sell_out_counter & reintro_eligibility
    # (corresponding attributes of objects scenario_CA & scenario_QC are set at end of func)
    if juris == 'CA':
        cur_sell_out_counter = scenario_CA.cur_sell_out_counter
        reintro_eligibility = scenario_CA.reintro_eligibility
    elif juris == 'QC':
        cur_sell_out_counter = scenario_QC.cur_sell_out_counter
        reintro_eligibility = scenario_QC.reintro_eligibility
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    logging.info(f"in {cq.date} for {juris}, cur_sell_out_counter is {cur_sell_out_counter} before update")
    logging.info(f"in {cq.date} for {juris}, reintro_eligibility is {reintro_eligibility} before update")
    
    # get sales % for advance auctions, for this juris, for cq.date
    # (works for auctions both linked and unlinked, i.e., inputting juris=='CA' works for CA-only and CA-QC auctions)
    df = prmt.auction_sales_pcts_all.copy()
    df = df.loc[(df.index.get_level_values('market').str.contains(juris)) &
                (df.index.get_level_values('auct_type')=='current')]
    df.index = df.index.droplevel(['market', 'auct_type'])
    sales_pct_cur_1j_1q = df.at[cq.date]
    
    # if sales_pct_cur_1j_1q is 1, returns True; else False
    cur_sell_out = sales_pct_cur_1j_1q == float(1)

    if cur_sell_out == True:
        cur_sell_out_counter = cur_sell_out_counter + 1
    elif cur_sell_out == False:
        # reset value
        cur_sell_out_counter = 0
    else:
        print("Error" + "!: cur_sell_out is neither True nor False.")

    if cur_sell_out_counter < 2:
        reintro_eligibility = False
    elif cur_sell_out_counter >= 2:
        reintro_eligibility = True
    else:
        print("Error" + "!: cur_sell_out_counter has a problem")

    logging.info(f"in {cq.date} for {juris}, cur_sell_out_counter is {cur_sell_out_counter} after update")
    logging.info(f"in {cq.date} for {juris}, reintro_eligibility is {reintro_eligibility} after update")
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    # update attributes of objects scenario_CA & scenario_QC
    if juris == 'CA':
        scenario_CA.cur_sell_out_counter = cur_sell_out_counter
        scenario_CA.reintro_eligibility = reintro_eligibility
    elif juris == 'QC':
        scenario_QC.cur_sell_out_counter = cur_sell_out_counter
        scenario_QC.reintro_eligibility = reintro_eligibility

    # using object attributes, no return from this func


# In[ ]:


def transfer_consign__from_limited_use_to_auct_hold(all_accts):
    """
    Specified quantities remaining in limited_use account of a particular vintage will be moved to auct_hold.

    Allowances consigned must be transferred into auct_hold 75 days before the auction in which they will be available.
    CA regs: § 95910(d)(4).
    
    Runs at the end of each quarter, after auction processed for that quarter.
    
    So, i.e., for Q3 auction ~Aug 15, transfer would occur ~June 1 (in Q2), after Q2 auction (~May 15).
    
    These allowances will become available in the following auction (one quarter after cq.date).
    
    Since this is for consignment, which are only in CA, it doesn't apply to QC or ON.
    """       
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # pre-test for conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    # create next_q after cq.date (formatted as quarter)
    next_q = (pd.to_datetime(f'{cq.date.year}Q{cq.date.quarter}') + DateOffset(months=3)).to_period('Q')
    
    # get quantity consigned in next_q (consign_next_q_quant)
    # vintage of these allowances will always be next_q.year 
    # (true even for anomalous CA auction in 2012Q4; other jurisdictions don't have consignment)
    # look up quantity consigned in next_q from historical record
    consign_next_q_quant = prmt.consign_hist_proj.at[
        ('auct_hold', 'CA', 'current', 'consign', next_q.year, 'new', 'not_avail', next_q, 
         prmt.NaT_proxy, prmt.NaT_proxy, 'MMTCO2e'), 
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


# In[ ]:


def transfer_cur__from_alloc_hold_to_auct_hold_historical(all_accts, juris):
    """
    Transfer the known historical quantities of allowances available in current auctions.
    
    Processes all allowances for a given year (with date_level year == cq.date year).
    
    Occurs at the start of each year (Jan 1).
    
    Transfers specified allowances from alloc_hold to auct_hold.
    
    Operates only for newly available allowances, as specified manually in input file sheet 'qauct 2012-2017'.
    
    Operates only for state-owned allowances.
    
    Note: There is a separate fn for making the allowances in auct_hold available.

    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # pre-test for conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~    
    # get the historical data for cq.date.year
    df = prmt.qauct_new_avail.copy()
    mask1 = df.index.get_level_values('inst_cat')==juris
    mask2 = df.index.get_level_values('auct_type')=='current'
    mask3 = df.index.get_level_values('date_level').year==cq.date.year
    mask4 = df.index.get_level_values('vintage')==cq.date.year
    avail_1v = df.loc[(mask1) & (mask2) & (mask3) & (mask4)]
    
    # if partial year of historical data, fill in remaining auctions
    # in avail_1v, get the max date_level, and then the quarter of that max date
    max_quarter = avail_1v.index.get_level_values('date_level').max().quarter

    for quarter in range(max_quarter+1, 4+1):  
        # only enters loop if max_quarter < 4, which means partial year of data; 
        # make projection for remaining quarters,
        # assume that future auctions will be same on average as auctions in year-to-date
        
        # quantity of allowances newly available so far in cq.date.year
        avail_1v_tot_so_far = avail_1v['quant'].sum()
        
        # average quantity per auction
        avail_1v_avg = avail_1v_tot_so_far / max_quarter
        
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~
        # fill in remaining auctions
        
        # create new df and template row for appending to it
        avail_1v_plus = avail_1v.copy()
        template_row = avail_1v.loc[avail_1v_plus.index[-1:]]
        
        # determine new quarterly date for auction, set in level 'date_level'
        future_date = quarter_period(f"{cq.date.year}Q{quarter}")
        mapping_dict = {'date_level': future_date}
        template_row = multiindex_change(template_row, mapping_dict)

        # set new quantity
        template_row.at[template_row.index, 'quant'] = avail_1v_avg

        # append to historical plus
        avail_1v_plus = avail_1v_plus.append(template_row)
        
        # set the extended historical record to have same name as original df
        avail_1v = avail_1v_plus

    # end of "for quarter in range(max_quarter+1, 4+1):"
    
    # Now there is a full year of data (either historical, or historical + projection for remaining quarters)
    
    # calculate total to be available, of current vintage (vintage == cq.date.year)
    avail_1v_tot = avail_1v['quant'].sum()
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~
    # already in auct_hold (state-owned), current vintage
    # (unsold advance also added to auct_hold)
    # may be multiple rows
    mask1 = all_accts.index.get_level_values('inst_cat')==juris
    mask2 = all_accts.index.get_level_values('auct_type')=='current' # probably redundant
    mask3 = all_accts.index.get_level_values('vintage')==cq.date.year
    mask4 = all_accts.index.get_level_values('acct_name')=='auct_hold'
    mask5 = all_accts['quant'] > 0
    mask = (mask1) & (mask2) & (mask3) & (mask4) & (mask5)

    # calculate quantity of current vintage already in auct_hold
    auct_hold_1v_tot = all_accts.loc[mask]['quant'].sum()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~
    # calculate quantity to transfer: only those needed to get avail_1v_tot into auct_hold
    to_transfer_tot = avail_1v_tot - auct_hold_1v_tot

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~
    # from alloc_hold, get cap allowances of specified juris & vintage, to be drawn from
    mask1 = all_accts.index.get_level_values('acct_name')=='alloc_hold'
    mask2 = all_accts.index.get_level_values('juris')==juris
    mask3 = all_accts.index.get_level_values('inst_cat')=='cap'
    mask4 = all_accts.index.get_level_values('vintage')==cq.date.year
    mask5 = all_accts['quant'] > 0
    mask = (mask1) & (mask2) & (mask3) & (mask4) & (mask5)

    # split all_accts into two parts (for alloc_hold & not auct_hold)
    alloc_hold_1v = all_accts.loc[mask]
    not_alloc_hold = all_accts.loc[~mask]

    alloc_hold_1v_tot = alloc_hold_1v['quant'].sum()

    diff = alloc_hold_1v_tot - to_transfer_tot

    if diff < 1e-7:
        # there are just enough allowances in alloc_hold *or* there is a shortfall in alloc_hold

        # then transfer everything in alloc_hold to auct_hold
        # (will wind up with negative values in auct_hold after cur_upsample_avail_state_owned_historical)
        from_alloc_hold = alloc_hold_1v.copy()
        mapping_dict = {'acct_name': 'auct_hold', 
                        'auct_type': 'current', 
                        'inst_cat': juris, 
                        'newness': 'new', 
                        'status': 'not_avail'}
        from_alloc_hold = multiindex_change(from_alloc_hold, mapping_dict)

        # recreate all_accts
        # note: removed deficit that had been calculated before
        all_accts = pd.concat([not_alloc_hold, from_alloc_hold], sort=True)

        # groupby sum, splitting all_accts into pos & neg
        all_accts_pos = all_accts.loc[all_accts['quant']>0]
        all_accts_neg = all_accts.loc[all_accts['quant']<0]
        all_accts_pos = all_accts_pos.groupby(level=prmt.standard_MI_names).sum()
        all_accts = all_accts_pos.append(all_accts_neg)

    elif diff > 1e-7:
        # excess allowances in alloc_hold, so leave remainder in alloc_hold
        # (reminder: diff = alloc_hold_1v_tot - to_transfer_tot)

        # split alloc_hold allowances into part needed and part left behind
        from_alloc_hold = alloc_hold_1v.copy()
        from_alloc_hold.at[from_alloc_hold.index, 'quant'] = to_transfer_tot

        mapping_dict = {'acct_name': 'auct_hold', 
                        'auct_type': 'current', 
                        'inst_cat': juris, 
                        'newness': 'new', 
                        'status': 'not_avail'}
        from_alloc_hold = multiindex_change(from_alloc_hold, mapping_dict)
    
        remainder_alloc_hold = alloc_hold_1v.copy()
        # reminder: diff = alloc_hold_1v_tot - to_transfer_tot
        remainder_alloc_hold.at[remainder_alloc_hold.index, 'quant'] = diff
        # no change to metadata needed

        # concat 
        all_accts = pd.concat([not_alloc_hold, from_alloc_hold, remainder_alloc_hold], sort=True)

        # groupby sum, splitting all_accts into pos & neg
        all_accts_pos = all_accts.loc[all_accts['quant']>0].groupby(level=prmt.standard_MI_names).sum()
        all_accts_neg = all_accts.loc[all_accts['quant']<0].groupby(level=prmt.standard_MI_names).sum()
        all_accts = all_accts_pos.append(all_accts_neg)

    else:
        print(f"Shouldn't reach this point; diff is: {diff}")
    
    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_conservation_against_full_budget(all_accts, juris, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)


# In[ ]:


def cur_upsample_avail_state_owned_historical(all_accts, juris):
    """
    Takes allowances in auct_hold and assigns specific quantities to each auction within a given year.
    
    This isn't really an upsample, but it accomplishes the same end, of assigning quarterly quantities.
    
    Does this based on historical data.
    
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
    
    # ~~~~~~~~~~~~~~~
    # get historical data for how much newly available in each auction (quact_mod is only newly available)
    # select only "current" vintage == cq.date.year
    df = prmt.qauct_new_avail.copy()
    hist_1v = df.loc[(df.index.get_level_values('inst_cat')==juris) &
                  (df.index.get_level_values('auct_type')=='current') &
                  (df.index.get_level_values('date_level').year==cq.date.year) & 
                  (df.index.get_level_values('vintage')==cq.date.year)]
        
    max_date_cur = hist_1v.index.get_level_values('date_level').max()
    latest_hist_year_cur = max_date_cur.year
    latest_hist_quarter_cur = max_date_cur.quarter
    
    # ~~~~~~~~~~~~~~~~
    # create hist_proj, in which projection will be added to historical
    hist_proj = hist_1v.copy()
    
    if cq.date.year == latest_hist_year_cur and latest_hist_quarter_cur < 4:
        # special case of partial year historical data
        # need to fill in additional quarters, based on what's remaining in auct_hold
        
        # calculate number of remaining quarters
        num_remaining_q = 4 - latest_hist_quarter_cur
        
        # remaining after historical quantities are made available prior to cq.date
        remaining_tot = annual_avail_1v['quant'].sum() - hist_1v['quant'].sum()
        
        # average newly available per remaining quarter
        avg_remaining = remaining_tot / num_remaining_q
        
        latest_hist_q = hist_1v.loc[hist_1v.index.get_level_values('date_level')==max_date_cur]
        
        # create proj_quarter, with new value (avg_remaining)
        proj_qs = latest_hist_q.copy()
        proj_qs.at[proj_qs.index, 'quant'] = avg_remaining # will fail if latest_hist_q is > 1 row
        
        # iterate through projection quarters (starting 1 quarter after latest_hist_quarter_cur)
        for quarter in range(latest_hist_quarter_cur+1, 4+1):            
            date_1q = quarter_period(f"{cq.date.year}Q{quarter}")
            proj_1q = proj_qs.copy()
            mapping_dict = {'date_level': date_1q}
            proj_1q = multiindex_change(proj_1q, mapping_dict)
            
            hist_proj = pd.concat([hist_proj, proj_1q])
        
        all_accts = pd.concat([hist_proj, not_annual_avail_1v], sort=True)
            
    else: 
        # reached in 2 cases: 
        # case 1. cq.date.year < latest_hist_year_cur
        # case 2. latest_hist_year_cur == cq.date.year and latest_hist_quarter_cur == 4:
        # (this fn only runs if cq.date.year <= latest_hist_year_cur)
        
        # there is a full year of historical data for cq.date.year; 
        # simply use historical data
        
        # if hist_1v was more than was in alloc_hold, create deficit
        hist_excess = hist_1v['quant'].sum() - annual_avail_1v['quant'].sum()
        if hist_excess > 1e-7:
            # create deficit in alloc_hold
            # take row annual_avail_1v, update value
            deficit = annual_avail_1v.copy()
            deficit.at[deficit.index, 'quant'] = -1 * hist_excess
            
            # update metadata
            mapping_dict = {'status': 'deficit', 
                            'date_level': cq.date}
            deficit = multiindex_change(deficit, mapping_dict)
            
            all_accts = pd.concat([hist_1v, not_annual_avail_1v, deficit], sort=True)
            
        else:
            all_accts = pd.concat([hist_1v, not_annual_avail_1v], sort=True)
            

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


# In[ ]:


def transfer_cur__from_alloc_hold_to_auct_hold_projection(all_accts, juris):
    """
    For projection, transfers all allowances remaining in alloc_hold to become state-owned current.
    
    Processes all allowances for a given year (with date_level year == cq.date year).
    
    Occurs at the start of each year (Jan 1).
    
    Transfers specified allowances from alloc_hold to auct_hold.
    
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
    
    # ~~~~~~~~~~~~~~~~~~~~~~~
    # for QC, set aside portion for full true-up (as initial estimated)
    # first true-ups are distributed in Q3 of year after the initial allocation
    if juris == 'QC':
        # split to_transfer into two parts: set_aside_for_alloc and to_transfer
        # will work only if:
        # 1. to_transfer df is only 1 row
        # 2. (cq.date.year, f"{cq.date.year+1}Q1") is unique in QC_alloc_full_proj
        
        # look up quantity that's set aside for full alloc
        set_aside_for_alloc_quant = prmt.QC_alloc_full_proj.at[(cq.date.year, f"{cq.date.year}Q1"), 'quant']
    
        # create set_aside_for_alloc (df with 1 row)
        set_aside_for_alloc = to_transfer.copy()
        set_aside_for_alloc.at[set_aside_for_alloc.index[0], 'quant'] = set_aside_for_alloc_quant
        
        # update value in to_transfer
        to_transfer_init = to_transfer.at[to_transfer.index[0], 'quant']
        to_transfer.at[to_transfer.index[0], 'quant'] = to_transfer_init - set_aside_for_alloc_quant
        
    else: 
        # juris != 'QC'
        set_aside_for_alloc = prmt.standard_MI_empty.copy()
    # ~~~~~~~~~~~~~~~~~~~~~~~  
    
    # update metadata for state_alloc_hold, to put into auct_hold & turn into state-owned allowances
    mapping_dict = {'acct_name': 'auct_hold', 
                    'inst_cat': juris, 
                    'auct_type': 'current',
                    'newness': 'new',  
                    'status': 'not_avail'}
    to_transfer = multiindex_change(to_transfer, mapping_dict)
    
    all_accts = pd.concat([to_transfer, set_aside_for_alloc, remainder], sort=False)    
    
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


# In[ ]:


def cur_upsample_avail_state_owned_projection(all_accts, juris):
    """
    For current auctions in a given year, sums newly available and advance unsold; upsamples and assigns date_level.
    
    This is idealized method for projections, in which one-quarter of annual total is available in each auction.
    
    Operates on specified juris, to keep current allowances of each jurisdiction separate.
    
    """

    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # pre-test for conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    dups = all_accts.loc[all_accts.index.duplicated(keep=False)]
    if dups.empty==False:
        # there are duplicated indices; need to do groupby sum
        print("Warning" + "! There are duplicated indices; need to do groupby sum.")
        all_accts_pos = all_accts.loc[all_accts['quant']>1e-7].groupby(level=prmt.standard_MI_names).sum()
        all_accts_neg = all_accts.loc[all_accts['quant']<-1e-7].groupby(level=prmt.standard_MI_names).sum()
        all_accts = all_accts_pos.append(all_accts_neg)
    
    # get all current allowances in auct_hold, for specified vintage and juris
    mask1 = all_accts.index.get_level_values('acct_name')=='auct_hold'
    mask2 = all_accts.index.get_level_values('juris')==juris
    mask3 = all_accts.index.get_level_values('vintage')==cq.date.year
    mask4 = all_accts.index.get_level_values('auct_type')=='current'
    # select state-owned allowances; those with inst_cat same as juris
    mask5 = all_accts.index.get_level_values('inst_cat')==juris
    mask6 = all_accts['quant'] > 0
    mask = (mask1) & (mask2) & (mask3) & (mask4) & (mask5) & (mask6)
    auct_hold = all_accts.loc[mask]
    not_auct_hold = all_accts.loc[~mask]
    
    if prmt.run_tests == True:
        # tests: check that selection above has 'status'=='not_avail' & 'newness'=='new'
        if auct_hold.index.get_level_values('newness').unique().tolist() != ['new']:
            print(f"{prmt.test_failed_msg} auct_hold had entries with newness != 'new'")
        if auct_hold.index.get_level_values('status').unique().tolist() != ['not_avail']:
            print(f"{prmt.test_failed_msg} auct_hold had entries with status != 'not_avail'")
    
    # take total from above, divide by 4 to get average annual quantity
    each_quarter = auct_hold / 4
    
    # create empty df; quarterly quantities with metadata for each quarter will be put into this df
    upsampled_to_q = prmt.standard_MI_empty.copy()
    
    for quarter in [1, 2, 3, 4]:
        one_quarter_date = quarter_period(f"{cq.date.year}Q{quarter}")
        one_quarter = each_quarter.copy()
        mapping_dict = {'date_level': one_quarter_date}
        one_quarter = multiindex_change(one_quarter, mapping_dict)
        upsampled_to_q = pd.concat([upsampled_to_q, one_quarter])

    all_accts = upsampled_to_q.append(not_auct_hold)
    
    if prmt.run_tests == True:        
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_conservation_against_full_budget(all_accts, juris, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
        
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)


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
    # specifying acct_name=='auct_hold' shouldn't be necessary, but doesn't hurt
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


# In[ ]:


def adv_unsold_to_cur_all_accts(all_accts):
    """
    Function similar to adv_unsold_to_cur, but operating on all_accts.
    
    Takes any unsold allowances from advance auctions that are in auct_hold account,
    and updates metadata to change them into current auction allowances.
    
    Sums any unsold across all quarters in a calendar year, 
    (which will become part of total state-owned allowances to be made available in current auctions).
    
    Based on regulations:
    CA: [CA regs Oct 2017], § 95911(f)(3)(B) & (D)
    QC: [QC regs Sep 2017], Section 54 (paragraph 2)
    ON: [ON regs Jan 2018], Section 58(4)2
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


# In[ ]:


def unsold_update_status(all_accts):
    """
    Operates after auction, on any allowances still remaining in auct_hold with date_level == cq.date.
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
    unsold_mask3 = all_accts['quant'] > 0
    unsold_mask = (unsold_mask1) & (unsold_mask2) & (unsold_mask3)
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
        print("Error" + "! all_accts_unsold['quant'] should be a float that's either zero or positive.")
    
    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
        
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
        
    return(all_accts)


# In[ ]:


def transfer_cur__from_alloc_hold_to_auct_hold_new_avail_anomalies(all_accts, juris):
    """
    Force unsold allowances to be reintro (made available again) to reflect anomalies in historical data.
    
    Right now, only set up for QC.
    
    Anomalies are transfers from alloc_hold to auct_hold for vintages < cq.date.year.
    
    (Normal transfers, in "historical" version of this function, are for vintage == cq.date.year.)
    
    Occurs at the start of each year (Jan 1).
    
    Transfers specified allowances from alloc_hold to auct_hold.
    
    Operates only for newly available allowances, as specified manually in input file sheet 'quarterly auct hist'.
    
    Operates only for state-owned allowances.
    
    Note: There is a separate fn for making the allowances in auct_hold available.

    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # pre-test for conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    # get the historical data for those allowances with vintages < date_level year
    df = prmt.qauct_new_avail.copy()
    hist_to_be_avail_anom = df.loc[(df.index.get_level_values('inst_cat')==juris) & 
                                   (df.index.get_level_values('auct_type')=='current') &
                                   (df.index.get_level_values('date_level')==cq.date) & 
                                   (df.index.get_level_values('vintage')<df.index.get_level_values('date_level').year)]
    
    if hist_to_be_avail_anom.empty == False:

        to_remove = -1 * hist_to_be_avail_anom.copy()
        # set metadata to match cap allowances in alloc_hold
        mapping_dict = {'acct_name': 'alloc_hold', 
                        'auct_type': 'n/a', 
                        'inst_cat': 'cap', 
                        'newness': 'n/a', 
                        'status': 'n/a', 
                        'date_level': prmt.NaT_proxy}
        to_remove = multiindex_change(to_remove, mapping_dict)

        to_transfer = hist_to_be_avail_anom.copy()
        # acct_name: no change needed
        # inst_cat: no change needed
        # auct_type: no change needed
        # status: no change needed
        # newness: no change needed
        # date_level: no change needed

        # concat with all_accts_pos
        all_accts_pos = all_accts.loc[all_accts['quant']>0]
        all_accts_pos = pd.concat([all_accts_pos, to_remove, to_transfer], sort=True)
        all_accts_pos = all_accts_pos.groupby(level=prmt.standard_MI_names).sum()
        
        # recombine
        all_accts_neg = all_accts.loc[all_accts['quant']<0]
        all_accts = all_accts_pos.append(all_accts_neg)
        
    else: # hist_to_be_avail_anom.empty == True:
        pass
        
    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_conservation_against_full_budget(all_accts, juris, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)


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
    VRE_retired = VRE_retired.T.dropna()
    VRE_retired = VRE_retired.stack()
    VRE_retired.name = 'quant'

    # convert to df
    VRE_retired = pd.DataFrame(VRE_retired)
    
    # set object attribute
    prmt.VRE_retired = VRE_retired
    
    # no return; func sets object attribute prmt.VRE_retired


# ## HINDCAST FUNCTIONS UNIQUE TO QC

# In[ ]:


def initialize_QC_auctions_2013Q4(all_accts):
    """
    2013Q4 was the first QC auction (and first for any juris in WCI market).
    
    It was anomalous, in that:
    1. There was only this single auction in 2012.
    2a. The 2013Q4 current auction had approximately a full year's worth of allowances available at once.
    2b. However, the current auction quantity was not all the allowances leftover after allocations were distributed.
    3. The 2013Q4 advance auction had available all vintage 2016 allowances at once.
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
    # QC regs (s. 38): all allowances not put in reserve account are transferred into "Minister's allocation account"
    # then allocations and auction quantities go from there to other accounts
    # in model, can leave all allowances in alloc_hold, and move allocations and auction quantities as specified
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # transfer advance into auct_hold
    all_accts = transfer__from_alloc_hold_to_specified_acct(all_accts, prmt.QC_advance_MI, 2013, 2020)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # transfer alloc out of alloc_hold to ann_alloc_hold
    
    # initial 75% of estimated alloc v2013 transferred in 2013Q4, before Q4 auction
    # (this was later than what would be the usual pattern in later years)
    
    # (appropriate metadata is assigned to each set of allowances by convert_ser_to_df_MI_alloc)             
    # convert each alloc Series into df with MultiIndex
    # then do the transfer for single vintage, cq.date.year+1
    # (the to_acct is already specified in metadata for each set of allowances)
    
    all_accts = transfer_QC_alloc_init__from_alloc_hold(all_accts)             

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # CURRENT AUCTION:
    # look up quantity available in 2013Q4 auction; 
    # move that quantity from alloc_hold to auct_hold
    # specify from vintage 2013
    # note: the split between historical and projected data occurs within the fn below
    # (so it is different than CA, which uses two different functions)

    all_accts = transfer_cur__from_alloc_hold_to_auct_hold_historical(all_accts, 'QC')
    all_accts = cur_upsample_avail_state_owned_historical(all_accts, 'QC')

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # ADVANCE AUCTION (2013Q4 anomaly):
    # remember: all vintage 2016 allowances were available at once in this auction
    # get all allowances aside for advance in auct_hold that are vintage 2016 (cq.date.year+3)
    adv_new_mask1 = all_accts.index.get_level_values('acct_name')=='auct_hold'
    adv_new_mask2 = all_accts.index.get_level_values('auct_type')=='advance'
    adv_new_mask3 = all_accts.index.get_level_values('vintage')==(cq.date.year+3)
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
        pass
    
    
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


# In[ ]:


def transfer_QC_alloc_init__from_alloc_hold(all_accts):
    """
    Moves allocated allowances from alloc_hold into private accounts (gen_acct).
    
    Runs at the end of each year (except for in anomalous years).
    
    Only processes one vintage at a time; vintage is cq.date.year + 1 (except for in anomalous years).
    
    (If there's an anomalous transfer, i.e., for QC in 2013, would need to change this.
    Could add if statement: if cq.date=='2013Q4', then for QC, do XYZ.)
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")

    all_accts_sum_init = all_accts['quant'].sum()
    
    # convert QC_alloc_initial (df) into QC_alloc_i (ser)
    QC_alloc_i = prmt.QC_alloc_initial.copy()
    QC_alloc_i.index = QC_alloc_i.index.droplevel('allocation quarter')
    QC_alloc_i = QC_alloc_i['quant']
    
    QC_alloc_i_1v = QC_alloc_i.loc[cq.date.year:cq.date.year]
    QC_alloc_i_1v.name = f'QC_alloc'
    
    QC_alloc_i_1v_MI = convert_ser_to_df_MI_QC_alloc(QC_alloc_i_1v)

    QC_alloc_i_1v_MI.name = 'QC_alloc_initial'
        
    to_acct_MI_1v = QC_alloc_i_1v_MI
    
    # create df named remove, which is negative of to_acct_MI; rename column
    remove = -1 * to_acct_MI_1v
    # remove.columns = ['remove_quant']

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
    
    # combine dfs to subtract from from_acct & add to_acct_MI_1v
    # (groupby sum adds the positive values in all_accts_pos and the neg values in remove)
    all_accts_pos = pd.concat([all_accts_pos, remove, to_acct_MI_1v], sort=True)
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


# In[ ]:


def transfer_QC_alloc_trueups__from_alloc_hold(all_accts):
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    QC_alloc_trueups = prmt.QC_alloc_trueups
    
    # pre-test: conservation of allowances
    all_accts_sum_init = all_accts['quant'].sum()
    
    # get all the allocation true-ups that occur in a particular quarter       
    QC_alloc_trueup_1q = QC_alloc_trueups.loc[QC_alloc_trueups.index.get_level_values('allocation quarter')==cq.date]
    
    if len(QC_alloc_trueup_1q) > 0:
        # there are true-ups to process for this quarter

        # from QC_alloc_trueup_1q, get all the emission years that there are true-ups for
        emission_years = QC_alloc_trueup_1q.index.get_level_values('allocation for emissions year').tolist()

        # iterate through all emission years that had trueups in cq.date
        for emission_year in emission_years:
            # initialize transfer_accum; resets for each emission_year
            transfer_accum = prmt.standard_MI_empty.copy()
            
            # get quantity of true-ups for specified emissions year (returns a Series)
            QC_alloc_trueup_1q_1y = QC_alloc_trueup_1q.xs(emission_year, 
                                                          level='allocation for emissions year', 
                                                          drop_level=True)
            
            # initialize un-accumulator: quantity remaining of true-ups to transfer
            trueup_remaining = QC_alloc_trueup_1q_1y['quant'].sum()
            
            # ***** SPECIAL CASE *****
            # hard code anomaly in 2016Q3, in which APCR allowances were apparently used 
            # for true-up alloc for emission year 2015
            if cq.date == quarter_period('2016Q3') and emission_year == 2015:                
                # transfer 0.826677 M from QC APCR to gen_acct
                mask1 = all_accts.index.get_level_values('acct_name')=='APCR_acct'
                mask2 = all_accts.index.get_level_values('juris')=='QC'
                mask = (mask1) & (mask2)
                QC_ACPR_acct = all_accts.loc[mask]
                
                APCR_for_trueup_quant = 0.826677 # units: MMTCO2e
                inst_cat_new_name = f"QC_alloc_2015_APCR" # used to update metadata below
                
                # create trueup_transfers df
                trueup_transfers = QC_ACPR_acct.copy()
                
                # update quantity:
                if len(trueup_transfers) == 1:
                    trueup_transfers.at[trueup_transfers.index[0], 'quant'] = APCR_for_trueup_quant
                else:
                    print("Error" + "! There was more than one APCR row; method above for setting value doesn't work.")
                
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
                trueup_remaining = trueup_remaining - APCR_for_trueup_quant
                
            else:
                pass
            # ***** SPECIAL CASE *****
            
            
            # if positive true-ups (usual case)
            if trueup_remaining > 0:
                                              
                # TEST: QC_alloc_trueup_1q_1y should only be a single row
                if len(QC_alloc_trueup_1q_1y) != 1:
                    print(f"{prmt.test_failed_msg} QC_alloc_trueup_1q_1y did not have 1 row. Here's QC_alloc_trueup_1q_1y:")
                    print(QC_alloc_trueup_1q_1y)
                # END OF TEST

                # get allowances in alloc_hold, for juris == 'QC', and vintage >= emission_year
                # but exclude allowances set aside for advance auctions
                mask1 = all_accts.index.get_level_values('juris')=='QC'
                mask2 = all_accts.index.get_level_values('acct_name')=='alloc_hold'
                mask3 = all_accts.index.get_level_values('inst_cat')=='cap'
                mask4 = all_accts.index.get_level_values('vintage')>=emission_year
                mask5 = all_accts['quant'] > 0
                all_accts_trueup_mask = (mask1) & (mask2) & (mask3) & (mask4) & (mask5)
                trueup_potential = all_accts.loc[all_accts_trueup_mask].sort_values(by='vintage')
                
                # try to draw from alloc_hold allowances of vintage == emission_year
                # if not enough allowances, go to the next vintage
                
                # create df of those transferred:
                # copy whole df trueup_potential, zero out values, then set new values in loop
                # sort_index to ensure that earliest vintages are drawn from first
                trueup_potential = trueup_potential.sort_index()
                
                trueup_transfers = trueup_potential.copy()  
                trueup_transfers['quant'] = float(0)
                # note: trueup_transfers winds up with zero rows because it is not built up from appending rows
                # it is updated by setting new values as needed
                
                for row in trueup_potential.index:
                    potential_row_quant = trueup_potential.at[row, 'quant']
                    trueup_to_transfer_quant = min(potential_row_quant, trueup_remaining)

                    # update un-accumulator for jurisdiction
                    trueup_remaining = trueup_remaining - trueup_to_transfer_quant

                    # update trueup_potential
                    trueup_potential.at[row, 'quant'] = potential_row_quant - trueup_to_transfer_quant

                    # update trueup_transfers
                    trueup_transfers.at[row, 'quant'] = trueup_to_transfer_quant
                    
                # update metadata for transferred allowances
                # record date of allocation in index level 'date_level'
                mapping_dict = {'acct_name': 'gen_acct',
                                'inst_cat': f'QC_alloc_{emission_year}', 
                                'date_level': cq.date}
                trueup_transfers = multiindex_change(trueup_transfers, mapping_dict)
                
                # recombine transfer_accum, trueup_potential (what's remaining), and the rest of all_accts
                all_accts = pd.concat([trueup_transfers, 
                                       trueup_potential, 
                                       all_accts[~all_accts_trueup_mask]], sort=False)
                
                # do groupby sum of pos & neg, recombine
                all_accts_pos = all_accts.loc[all_accts['quant']>1e-7].groupby(level=prmt.standard_MI_names).sum()
                all_accts_neg = all_accts.loc[all_accts['quant']<-1e-7].groupby(level=prmt.standard_MI_names).sum()
                all_accts = all_accts_pos.append(all_accts_neg)

            # if negative true-ups
            elif trueup_remaining < 0:
                # print(f"There was negative true-up of {trueup_remaining} M; negative true-ups not implemented currently.")
                # see boneyard for old code on negative true-ups
                pass
            
            else:
                # closing if trueup_remaining > 0, elif trueup_remaining < 0
                print(f"No QC true-ups processed; show QC_alloc_trueup_1q_1y: {QC_alloc_trueup_1q_1y}.")
                pass            

        # end of "for emission_year in emission_years:"
    
    else:
        # closing "if len(QC_alloc_trueup_1q) > 0:"
        pass
        
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    if prmt.run_tests == True:
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_during_transfer(all_accts, all_accts_sum_init, 'QC_alloc')
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_negative_values(all_accts, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
    
    # after end of "for emission_year in emission_years:"
    return(all_accts)


# #### end of functions

# # REGULATIONS

# ## CA cap (divided into different types)

# ### CA advance
# * set in regs § 95870(b) & § 95871(b): for all years 2015-2031, 10% of cap
# * allowances are offered in advance auctions held 3 years prior to their vintage
# * started with vintage 2015 allowances offered in 2012 (first auction, held 2012-11)
# * for budget years 2013-2020: "Upon creation of the Auction Holding Account, the Executive Officer shall transfer 10 percent of the allowances from budget years 2015-2020 to the Auction Holding Account.
# * for budget years 2021-2030: "The Executive Officer shall transfer 10 percent of the allowances from budget years 2021 and beyond to the Auction Holding Account."

# ### CA Voluntary Renewable Electricity Reserve Account (aka VRE_reserve)
# * set in regs § 95870(c): 0.5% of cap for 2013-2014, 0.25% of cap for 2015-2020
# * there are no Voluntary Renewable Electricity Reserve Account allowances after 2020
# * these are counted as non-vintage allowances, but can keep them here with year of cap they derive from
# * these are not used toward compliance obligations, so once they are created, they are permanently removed from C&T supply
# * for accounts: "Upon creation of the Voluntary Renewable Electricity Reserve Account, the Executive Officer shall transfer allowances to the Voluntary Renewable Electricity Reserve Account..."

# ### CA allocations:
# * note: in the model, CA is the only jurisdiction with various types of allocations specified
# * so industrial_alloc, etc., are only for CA
# * for QC & ON, simply have alloc_QC and alloc_ON
# * for accounts: "The Executive Officer will allocate to the limited use holding account and allowance allocation holding account pursuant to sections 95892(b) and 95831(a)(6) for each electrical distribution utility by October 24 of each calendar year from 2013-2019 for allocations from 2014-2020 annual allowance budgets."
#  * so only move out of alloc_hold on that date in each year

# #### CA allocation: Electrical Distribution Utility Sector Allocation (CA)
# 2013-2020: § 95870(d)(1), with details specified in regs § 95892(a)(1) & § 95892(a)(2): 
# * allocation = [base value] * [annual cap adjustment factors]
#  * base value: in 95870(d)(1), specified as 97.7 million allowances per year
#  * annual cap adjustment factors: in 95891 Table 9-2: Cap Adjustment Factor, c, Standard Activities
#  * percentage of elec alloc for each utility in 95892 Table 9-3
#  * details by utility in: https://www.arb.ca.gov/cc/capandtrade/allowanceallocation/edu-ng-allowancedistribution/electricity-allocation.xlsx
# 
# ARB's numbers also in this pdf:
# "Annual Allocation to Electrical Distribution Utilities (EDU) under the Cap-and-Trade Regulation (Regulation) Rev. 2/4/2015"
# https://www.arb.ca.gov/cc/capandtrade/allowanceallocation/edu-ng-allowancedistribution/electricity-allocation.pdf
# 
# (Note there was an earlier version Rev. 8/1/2014, but the sums there were off significantly from the total electricity allocation. Perhaps they made an error, which they corrected with 2/4/2015 version.)
# 
# However, both of the pdfs say: "This list neither substitutes for nor supplements the provisions of the Regulation and is intended to provide information about allowance allocation to EDUs based on the best available information as of the creation date indicated in the header. This is not a regulatory document."
# 
# Danny's numbers matched 2015 version of pdf above.
# 
# When I calculate based on the regs (including percentages in Table 9-3), and ROUND UP the allocation for each utility, then I get the same numbers as the totals in ARB's 2015 version, except that ARB's totals are 1 allowance (1 tCO2e) higher for 2019 & 2020.
# 
# Anyway, use ARB's numbers (in 2017 Excel file) because that's what they published, they're close enough, and we won't know what they actually allocate for 2019 & 2020 for a while.

# 2021-2030 Electrical Distribution Utility Sector Allocation (IOU & POU):
# * 2021-2030: § 95871(c)(1)
# * details determined by 95892(a), with allocation quantities explicitly stated in § 95892 Table 9-4
# * (data copied from pdf (opened in Adobe Reader) into Excel; saved in input file)
# * but utilities not identified in Table 9-4 as IOU or POU
# * so merge with 2013-2020 df, and then compute sums for whole time span 2013-2030
# * (also note this does not go through 2031, as cap does)

# #### CA allocation: Natural Gas Supplier Sector
# for 2015-2020, § 95870(h); method described in § 95893 [specifically § 95893(a)]:
# * note: natural gas supplier allocations only began in 2015
# * allowances = [emissions in 2011] * [annual adjustment factor for natural gas]
#  * emissions: calculated per methods in §95852(c):
#    * "Suppliers of Natural Gas. A supplier of natural gas covered under § 95811(c) and § 95812(d) has a compliance obligation for every metric ton CO2e of GHG emissions that would result from full combustion or oxidation of all fuel delivered to end users in California..."
#  * annual adjustment factor for natural gas is the CA_cap_adjustment_factor
# 
# for 2021 and beyond, § 95871(g)
# * method is "pursuant to sections § 95893(b) and § 95831(a)(6)"
# * § 95893(b): if entities don't specify consignment amount, full allocation will be consigned
# * allocation quantities specified by § 95893(a), which is the same for 2015-2020 as for 2021-2030
# 
# problem:
# * the category of emissions specified in § 95852(c) don't seem to reported anywhere on their own (i.e, in MRR)
# * regulations don't state what the value was in 2011
# 
# solution: 
# * infer what the emissions in 2011 were that ARB used in its calculations
# * emissions in 2011 = reported allocations for year X / adjustment factor for year X
# * using this equation, can calculate emissions in 2011 from the allocation and adjustment factor for any particular year
# * double-checked results by comparing multiple years (i.e., X = 2015, 2016, 2017, 2018)

# In[ ]:


# note: method above very closely recreated historical values, 
# but was sometimes off by 1 allowance (one time high, one time low)

# for 2015, was exactly right (45.356999)
# for 2016, gave 44.444094 instead of historical value of 44.444093
# for 2017, gave 43.579236 instead of historical value of 44.579237
# for 2018, was exactly right (42,666,330)


# ### CA allocation: Industrial & other
# Following ARB's approach in 2018-03-02 workshop presentation (slide 9), group allocations into "industrial & other"
# 
# Other category includes:
# * Public Wholesale Water Agencies
# * University Covered Entities and Public Service Facilities
# * Legacy Contract Generators (already included with Industrial, from 2018 allocation report)
# * thermal output
# * waste-to-energy
# * LNG suppliers
# 
# Then after the latest historical data for allocations, use ARB's projection for what allocations would be for the "industrial & other" category, if assistance factors in 2018-2020 were retained at 50%/75% for high/medium risk sub-sectors.
# 
# In that projection, assistance factors are 100% for years 2021-2030, so that projection shows their expectation for allocations, excluding any true-ups to make up (retroactively) for lower assistance factors 2018-2020.

# #### CA allocation: Industrial
# * (variable allocation)
# * rules for calculating for 2013-2020: § 95870(e)
# * rules for calculating for 2021 and beyond: § 95871(d)
# * more details in § 95891. ALLOCATION FOR INDUSTRY ASSISTANCE
# 
# notes on assistance factors:
# * in 2018, assistance factors followed regs as of Oct 2017, in Table 8-1:
#  * sub-sectors with "low" leakage risk were assigned industry assistance factor of 50%
#  * sub-sectors with "medium" leakage risk were assigned industry assistance factor of 75%
# * in 2018, ARB proposed to raise assistance factors for all sub-sectors to 100%, including making retroactive allocations
# * model uses current regulations, and actual allocation for 2018
# 
# other notes:
# * in 2018 allocation report, legacy contract generation allocation included with industrial allocation
# * in 2017, legacy contract generation allocation was 0.37 MMTCO2e, and had been decreasing
# * in 2018, this allocation would be < 1% of the category industrial allocation + legacy contract allocation

# #### Allocation to Public Wholesale Water Agencies:
# (fixed allocation)
# * 2013-2020: § 95870(d)(2)
#  * details in § 95895(a) and § 95895 Table 9-7: "Allocation to Each Public Wholesale Water Agency" [2015-2020]
#  
#  
# * 2021 and beyond: § 95871(c)(2)
#  * details in § 95895(b)

# #### CA allocation: Allocation to University Covered Entities and Public Service Facilities
# * (variable allocation)
# * 2013-2020: § 95870(f)
# * 2021 and beyond: § 95871(e)

# #### CA allocation: Allocation to Legacy Contract Generators
# * (variable allocation)
# * 2013-2020: § 95870(g)
# * 2021 and beyond: § 95871(f)
# * recall that for 2018, this allocation was included in industrial allocation

# #### CA allocation: thermal output
# 
# full name, as listed in annual allocation reports: 
# 
# "Allocation to Facilities with Limited Exemption of Emissions from the Producton of Qualified Thermal Output"
# 
# Related: § 95852(j) "Limited Exemption of Emissions from the Production of Qualified Thermal Output."
# * "From 2013 through the year before which natural gas suppliers are required to consign 100% of allocated allowances to auction pursuant to Table 9-5 or 9-6..." 
# * Note: natural gas suppliers have to consign 100% in 2030 and beyond
# * regs don't specify exact amount, except that it's zero from 2030 onward
# * values 2015-2016 from annual allocation reports; no values 2013-2014, nor 2017-2018
# * NZ INTERNAL: see Trello card for this; it's about thermal output & waste-to-energy (https://trello.com/c/F10WGo7z)
# 
# Mason's reading (May 2018): 
# * This appears to have been a limited-time allocation. Model assumes it's zero from 2017 onward.
# * Annual allocation report had allocations for "qualified thermal output" of vintage 2015 (for 2013 emissions) and vintage 2016 allowances (for 2014 emissions), as stated on first page of allocations reports. 
# * These allocations may have been to satisfy emissions obligations incurred under an earlier version of the regulations that did not include this exemption.

# #### CA allocation: Waste-to-Energy
# * (variable allocation)
# * regs don't specify exact amount; values 2015-2018 from annual allocation reports
# * note that 2018 value is the sum of allocations for three facilities:
#  * 100063 – Southeast Resource Recovery Facility (SERRF)
#  * 100064 – LACSD - Commerce Refuse To Energy
#  * 101264 – Covanta - Stanislaus, Inc
# * Related: § 95852(k): "Limited Exemption of Emissions for Waste-to-Energy Facilities"

# #### CA allocation: LNG suppliers
# * full name: "Suppliers of Liquefied Natural Gas and Compressed Natural Gas"
# * § 95852(l)(1), "Limited Exemption for Emissions from LNG Suppliers," describes exemption
# * This category had an allocation in 2018, for emissions with compliance obligations in second compliance period (2015-2017). This category is given the limited exemption for emissions in years from 2018 onward.
# * Note that regulations specify that there could be a true-up of the allocation, from vintage 2019 (§ 95852(l)(1))
# * According to 2016 ISOR, will not have any compliance obligation for years 2018 and after, so no more allocations for this category after 2017 (except for true-up noted above).
#  * NZ INTERNAL: see https://trello.com/c/wPnfBr2B) 

# #### CA allocation: industrial & other

# ## Quebec: inputs
# 
# * get amount of newly available current allowances for Canadian provinces
# * they don't have consignment, so this is only state-owned allowances being introduced for the first time
# * (reminder: this category does not include unsold adv reintro as cur)

# **Quebec regulations:**
# 
# full version: http://legisquebec.gouv.qc.ca/en/ShowDoc/cr/Q-2,%20r.%2046.1
# 
# cap amounts (to 2020): 
# * from Quebec Environment Quality Act (chapter Q-2), r. 15.2
# * http://legisquebec.gouv.qc.ca/en/ShowDoc/cr/Q-2,%20r.%2015.2
# * Published Gazette Officielle du Québec, December 19, 2012, Vol. 144, No. 51 (http://www2.publicationsduquebec.gouv.qc.ca/dynamicSearch/telecharge.php?type=1&file=2389.PDF)
# 
# cap amounts (2021-2030):
# * from Quebec Environment Quality Act (chapter Q-2), r. 15.3
# * http://legisquebec.gouv.qc.ca/en/ShowDoc/cr/Q-2,%20r.%2015.3
# * Published in Gazette Officielle du Québec, August 31, 2017, Vol. 149, No. 35A (http://www2.publicationsduquebec.gouv.qc.ca/dynamicSearch/telecharge.php?type=1&file=103120.pdf)
# 
# advance auction amounts: 
# * amounts to be made available for advance auction do not seem to be specified in regulations
#  * NZ INTERNAL: see https://trello.com/c/3btJGiM7
# * in practice, amounts made available in advance auction have been exactly 10% of annual caps
# * WCI annual auction notice for 2018 states: "Advance Auction Allowances Offered for Sale: The Advance Auction budget represents 10 percent of the allowances from each of the jurisdiction’s allowance budgets that are created for the year three years subsequent to the current calendar year."
# 
# reserve amounts: 
# * from Quebec Environment Quality Act (chapter Q-2), r. 46.1, s. 38
# * http://legisquebec.gouv.qc.ca/en/showversion/cr/Q-2,%20r.%2046.1?code=se:38&pointInTime=20180119
# 
# allocations (variable):
# * from Quebec Environment Quality Act (chapter Q-2), r. 46.1, s. 39.
#  * http://legisquebec.gouv.qc.ca/en/showversion/cr/Q-2,%20r.%2046.1?code=se:39&pointInTime=20180119
# * from Quebec Environment Quality Act (chapter Q-2), r. 46.1, s. 41.
#  * http://legisquebec.gouv.qc.ca/en/ShowDoc/cr/Q-2,%20r.%2046.1
# 
# remainder (cap - advance - reserve - allocation) goes to current auction as state-owned allowances
# * based on historical practice

# In[ ]:


def get_QC_inputs():
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # get record of retirements (by vintage) from compliance reports
    QC_cap_data = pd.read_excel(prmt.input_file, sheet_name='QC cap data')

    # get cap amounts from input file
    QC_cap = QC_cap_data[QC_cap_data['name']=='QC_cap'].set_index('year')['data']
    QC_cap.name = 'QC_cap'

    # ~~~~~~~~~~~~~~~~~~~~

    # calculate advance for each year (2013-2030) on the basis that advance is 10% of cap
    # annual auction notice 2018 says: 
    # "Advance Auction Allowances Offered for Sale:
    # The Advance Auction budget represents 10 percent of the allowances from each of the jurisdiction’s allowance 
    # budgets that are created for the year three years subsequent to the current calendar year."
    QC_advance_fraction = QC_cap_data[QC_cap_data['name']=='QC_advance_fraction'].set_index('year')['data']
    QC_advance = QC_cap * QC_advance_fraction
    QC_advance.name = 'QC_advance'

    # ~~~~~~~~~~~~~~~~~~~~

    # calculate reserve quantities, using reserve fraction in input file, multiplied by cap amounts
    QC_APCR_fraction = QC_cap_data[QC_cap_data['name']=='QC_APCR_fraction'].set_index('year')['data']
    QC_APCR = QC_cap * QC_APCR_fraction
    QC_APCR.name = 'QC_APCR'

    # new regulations for QC:
    # assume that QC will *not* increase its APCR, as ARB informally suggested it would for post-2020
    
    return(QC_cap, QC_advance, QC_APCR)


# ## historical data from CIR: allowances, offsets, VRE retirements
# CIR = Compliance Instrument Reports

# In[ ]:


def get_CIR_data_and_clean():
    # code here is for files that have the latest sheets covering jurisdictions CA, QC, ON;
    # if using earlier file as input, need to change jurisidictions in file name

    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (start)")

    CIR_sheet_names = pd.ExcelFile(prmt.CIR_excel).sheet_names
    
    # initialize lists
    CIR_allowances_list = []
    CIR_offsets_list = []
    # forest_buffer_stock = pd.DataFrame()
    
    for sheet in CIR_sheet_names:        
        # get records for each quarter
        one_quart = pd.read_excel(prmt.CIR_excel, header=6, sheet_name=sheet)
            
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

#         # get forest buffer amounts out of notes at bottom of each sheet:
#         buffer_prefix = '\+ There are an additional '
#         buffer_suffix = ' U.S. Forest Project Offset Credits in the CARB Forest Buffer Account. '

#         # get forest buffer account amounts
#         first_col_as_list = one_quart['Vintage'].astype(str).tolist()
#         forest_buffer_index = [i for i, s in enumerate(first_col_as_list) if 'Forest Buffer' in s]
#         if len(forest_buffer_index) > 0:
#             forest_buffer = first_col_as_list[forest_buffer_index[0]]
#             forest_buffer = int(forest_buffer.lstrip(buffer_prefix).rstrip(buffer_suffix).replace(',', ''))
#         else:
#             forest_buffer = 0
#         forest_buffer_stock = forest_buffer_stock.append({'quarter': sheet, 'forest buffer stock': forest_buffer}, ignore_index=True)
    
    # end of loop "for sheet in CIR_sheet_names:"
    
    # convert lists of dfs above into single dfs
    CIR_allowances = pd.concat(CIR_allowances_list, axis=0, sort=True)
    CIR_offsets = pd.concat(CIR_offsets_list, axis=0, sort=True)
    
    # call functions to clean up allowances and offsets
    CIR_allowances = clean_CIR_allowances(CIR_allowances)
    CIR_offsets = clean_CIR_offsets(CIR_offsets)

    # combine cleaned versions of allowances and offsets
    # create CIR_historical (new df)
    prmt.CIR_historical = pd.concat([CIR_allowances, CIR_offsets], sort=True)
    # note this does not include Forest Buffer; 
    # see "CA-QC-ON quarterly compliance instrument report - wrangling data 2018-03-06.ipynb"

    # create CIR_offsets_q_sums, used later for CIR comparison
    # these are sums across the different categories of offsets, 
    # but retain the full set of various accounts, & showing offsets in private vs. jurisdiction accounts
    df = CIR_offsets.copy().reset_index()
    df = df.drop(['Description', 'Vintage'], axis=1)
    df = df.set_index('date')
    prmt.CIR_offsets_q_sums = df
        
    # no return; func sets object attributes prmt.CIR_historical & prmt.CIR_offsets_q_sums


# In[ ]:


def clean_CIR_allowances(CIR_allowances):
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    CIR_allowances = CIR_allowances.reset_index(drop=True) 

    CIR_allowances.columns = CIR_allowances.columns.str.replace('\n', '')
    
    # combine and clean up columns with changing names across quarters:
    # new_list = [expression(i) for i in old_list if filter(i)]
    for col_type in ['Retirement', 
                     'Voluntary Renewable Electricity', 
                     'Limited Use Holding Account', 
                     'Environmental Integrity']:
    
        CIR_sel_cols = [col for col in CIR_allowances.columns if col_type in col]
        CIR_allowances[col_type] = CIR_allowances[CIR_sel_cols].sum(axis=1, skipna=True)

        for col in CIR_sel_cols:
            if '*' in col or '(' in col:
                CIR_allowances = CIR_allowances.drop(col, axis=1)

    CIR_allowances.insert(0, 'Description', CIR_allowances['Vintage'])
    for item in range(2013, 2030+1):
        CIR_allowances['Description'] = CIR_allowances['Description'].replace(item, 'vintaged allowances', regex=True)

    non_vintage_map = {'Non-Vintage Québec Early Action Allowances (QC)': 'early_action', 
                       'Non-Vintage Price Containment Reserve Allowances': 'APCR', 
                       'Allowances Subtotal': np.NaN}
    CIR_allowances['Vintage'] = CIR_allowances['Vintage'].replace(non_vintage_map)

    CIR_allowances['quarter'] = CIR_allowances['quarter'].str.replace(' ', '')
    CIR_allowances['quarter'] = pd.to_datetime(CIR_allowances['quarter']).dt.to_period('Q')
    CIR_allowances = CIR_allowances.rename(columns={'quarter': 'date', 'Total': 'subtotal'})

    CIR_allowances = CIR_allowances.set_index(['date', 'Description', 'Vintage'])

    # convert units to MMTCO2e
    CIR_allowances = CIR_allowances/1e6
    
    return(CIR_allowances)


# In[ ]:


def clean_CIR_offsets(CIR_offsets):
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
        
    CIR_offsets = CIR_offsets.reset_index(drop=True) 

    CIR_offsets.columns = CIR_offsets.columns.str.replace('\n', '')

    CIR_offsets = CIR_offsets.rename(columns={'Vintage': 'Offset type'})
    CIR_offsets['Offset type'] = CIR_offsets['Offset type'].str.rstrip().str.rstrip().str.rstrip('+').str.rstrip('*')
    # could also use map (wrapped in list), or translate, or ...

    CIR_offsets_names = CIR_offsets['Offset type'].unique().tolist()
    CIR_offsets_names.remove('California')
    CIR_offsets_names.remove('Québec')
    CIR_offsets_names.remove(np.NaN)

    CIR_offsets['Jurisdiction'] = CIR_offsets['Offset type']
    CIR_offsets = CIR_offsets.dropna(subset=['Jurisdiction'])

    for row in CIR_offsets.index:
        if CIR_offsets.at[row, 'Jurisdiction'] in CIR_offsets_names:
            CIR_offsets.at[row, 'Jurisdiction'] = np.NaN
    CIR_offsets['Jurisdiction'] = CIR_offsets['Jurisdiction'].fillna(method='ffill')
    CIR_offsets = CIR_offsets[CIR_offsets['Offset type'].isin(CIR_offsets_names)]

    for col in ['General', 'Total']:
        CIR_offsets[col] = CIR_offsets[col].astype(str)
        CIR_offsets[col] = CIR_offsets[col].str.replace('\+', '')
        CIR_offsets[col] = CIR_offsets[col].str.replace('5,043,925 5,017,043', '5017043')
        CIR_offsets[col] = CIR_offsets[col].astype(float)

    CIR_offsets['Offset type'] = CIR_offsets['Offset type'].str.rstrip(' (CA)')
    CIR_offsets['Offset type'] = CIR_offsets['Offset type'].str.rstrip(' (QC)')

    CIR_offsets['quarter'] = CIR_offsets['quarter'].str.replace(' ', '')
    CIR_offsets['quarter'] = pd.to_datetime(CIR_offsets['quarter']).dt.to_period('Q')
    CIR_offsets = CIR_offsets.rename(columns={'quarter': 'date'})

    
    # combine and clean up columns with changing names across quarters:
    # new_list = [expression(i) for i in old_list if filter(i)]
    for col_type in ['Retirement', 
                     'Voluntary Renewable Electricity', 
                     'Limited Use Holding Account', 
                     'Environmental Integrity']:
    
        CIR_sel_cols = [col for col in CIR_offsets.columns if col_type in col]
        CIR_offsets[col_type] = CIR_offsets[CIR_sel_cols].sum(axis=1, skipna=True)

        for col in CIR_sel_cols:
            if '*' in col or '(' in col:
                CIR_offsets = CIR_offsets.drop(col, axis=1)
                
    CIR_offsets['General'] = CIR_offsets['General'].astype(float)
    CIR_offsets['Total'] = CIR_offsets['Total'].astype(float)

    CIR_offsets = CIR_offsets.rename(columns={'Offset type': 'Description', 
                                              'Total': 'subtotal'})
    # CIR_offsets['Vintage'] = 'n/a'
    CIR_offsets = CIR_offsets.set_index(['date', 'Description', 'Jurisdiction'])

    # convert units to MMTCO2e
    CIR_offsets = CIR_offsets/1e6

    # sum over types of offsets, jurisdictions
    CIR_offsets = CIR_offsets.groupby('date').sum()

    CIR_offsets['Description'] = 'offsets'
    CIR_offsets['Vintage'] = 'n/a'

    CIR_offsets = CIR_offsets.set_index([CIR_offsets.index, 'Description', 'Vintage'])
    
    return(CIR_offsets)


# # FUNCTIONS to process auctions

# In[ ]:


def retire_for_EIM_outstanding(all_accts):
    
    """
    For CA, moves allowances to Retirement account, to account for emissions not counted in Energy Imbalance Market.
    
    Under current regs (Oct 2017), § 95852(b)(1)(D):
    "EIM Outstanding Emissions. Beginning January 1, 2018, ARB will retire current vintage allowances designated by 
    ARB for auction pursuant to section 95911(f)(3) that remain unsold in the Auction Holding Account for more than 
    24 months in the amount of EIM Outstanding Emissions as defined in section 95111(h) of MRR."
    
    It seems that under current regs, if the Auction Holding Account no longer has CA allowances that have been
    there for more than 24 months, then there is no stipulation for removing allowances from other pools.
    
    Regarding proposed new regs:
    
    CARB's "Post-2020 Caps" proposal said: 
    "Retirement of allowances to account for 'missing' imported electricity emissions in the Energy Imbalance Market... 
    could be several million allowances a year from 2018 through 2020...."
    &
    "This value is currently unknown for the period between 2018 and 2020, but could be tens of millions of allowances.
    Thus, it is anticipated that there will be fewer pre-2021 unused allowances available to help with meeting 
    post-2020 obligations."
    
    (The "tens of millions" apparently refers to cumulative over 2018-2020, 
    which would seem to imply they're thinking of annual average ~7 M or higher.)
    
    
    Proposed new regs:
    
    Proposed 95911(h)(2): Starting in 2019, 2018 + Q1 2019 EIM Outstanding Emissions will be retired from 
    the budget year two years after the current budget year. 
    
    Those will be retired by 2019Q4 and 2020Q4, respectively.
    Would come from vintage 2021 and 2022, respectively.
    
    § 95852(b)(1)(D): Starting in Q2 2019, EIM Purchasers will have compliance obligations, which
    "shall be calculated pursuant to MRR section 95111(h)(3)."
    
    For EIM Outstanding Emissions (those beyond what carries a compliance obligation):
    § 95852(b)(1)(E):
    (1) up to Mar 31, 2019, "calculated pursuant to MRR section 95111(h)(1)"
    (1) starting Apr 1, 2019, "calculated pursuant to MRR section 95111(h)(2)"
    
    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # pre-test for conservation
    all_accts_sum_init = all_accts['quant'].sum()
    
    # cut-off date: if allowances with unsold_di of this date or earlier remain unsold,
    # they are eligible to be retired for EIM
    
    # this function runs after current auction in cq.date, 
    # so any remaining unsold for 2 years at the time the function runs...
    # ... will still be unsold at the start of the next quarter, at which point they'll be unsold > 2 years
    cut_off_date = quarter_period(f"{cq.date.year-2}Q{cq.date.quarter}")
    
    if cq.date.year in [2018, 2019, 2020]:
        if prmt.CA_post_2020_regs == 'Regs_Oct_2017':
            # EIM outstanding processed using Oct 2017 version of regulations
            # then draw EIM retirements from unsold
            # get unsold CA state-owned current allowances in auct_hold, with unsold_di > 2 years (24 mo.) earlier
            mask1 = all_accts.index.get_level_values('acct_name')=='auct_hold'
            mask2 = all_accts.index.get_level_values('inst_cat')=='CA'
            mask3 = all_accts.index.get_level_values('auct_type')=='current'
            mask4 = all_accts.index.get_level_values('status')=='unsold'
            mask5 = all_accts.index.get_level_values('unsold_di') <= cut_off_date # see note below
            mask6 = all_accts['quant'] > 0
            mask = (mask1) & (mask2) & (mask3) & (mask4) & (mask5) & (mask6)

            # note: for applying cut_off_date, should be sufficient to use unsold_di==cut_off_date, but used <= to be safe

            # unsold to potentially retire for EIM
            retire_potential = all_accts.copy().loc[mask]
        
        elif prmt.CA_post_2020_regs in ['Preliminary_Discussion_Draft', 'Proposed_Regs_Sep_2018']:
            if cq.date.year == 2018:
                # EIM outstanding processed using Oct 2017 version of regulations
                # then draw EIM retirements from unsold
                # get unsold CA state-owned current allowances in auct_hold, with unsold_di > 2 years (24 mo.) earlier
                mask1 = all_accts.index.get_level_values('acct_name')=='auct_hold'
                mask2 = all_accts.index.get_level_values('inst_cat')=='CA'
                mask3 = all_accts.index.get_level_values('auct_type')=='current'
                mask4 = all_accts.index.get_level_values('status')=='unsold'
                mask5 = all_accts.index.get_level_values('unsold_di') <= cut_off_date # see note below
                mask6 = all_accts['quant'] > 0
                mask = (mask1) & (mask2) & (mask3) & (mask4) & (mask5) & (mask6)

                # note: for applying cut_off_date, should be sufficient to use unsold_di==cut_off_date, but used <= to be safe

                # unsold to potentially retire for EIM
                retire_potential = all_accts.copy().loc[mask]

            elif cq.date.year in [2019, 2020]:
                # EIM outstanding processed using (proposed) Sep 2018 version of regulations
                # then draw EIM retirements from cap allowances in alloc_hold
                # assume this would come from vintage == cq.date.year + 2
                # (because cq.date.year allowances already distributed to various purposes by the time EIM processed)
                mask1 = all_accts.index.get_level_values('acct_name') == 'alloc_hold'
                mask2 = all_accts.index.get_level_values('juris') == 'CA'
                mask3 = all_accts.index.get_level_values('inst_cat') == 'cap'
                mask4 = all_accts.index.get_level_values('vintage') == cq.date.year + 2
                mask5 = all_accts['quant'] > 0
                mask = (mask1) & (mask2) & (mask3) & (mask4) & (mask5)

                # cap to potentially retire for EIM
                retire_potential = all_accts.copy().loc[mask]

        else:
            # cq.date.year is not 2018 or 2019
            pass
        
        # then process retirements, using mask and retire_potential set above
        
        # get quantity to be retired in cq.date.year; 
        # initialization of variable that will be updated
        EIM_retirements = assign_EIM_retirements()
        
        EIM_remaining = EIM_retirements.at[cq.date.year]
        
        # create df for adding transfers; copy of retire_potential, but with values zeroed out
        # sort_index to ensure earliest vintages are drawn from first
        retire_potential = retire_potential.sort_index()
        to_retire = retire_potential.copy()
        to_retire['quant'] = float(0)
        
        for row in retire_potential.index:
            potential_row_quant = retire_potential.at[row, 'quant']
            to_retire_quant = min(potential_row_quant, EIM_remaining)

            # update un-accumulator for jurisdiction
            EIM_remaining += -1 * to_retire_quant

            # update retire_potential
            retire_potential.at[row, 'quant'] = potential_row_quant - to_retire_quant

            # update to_retire
            to_retire.at[row, 'quant'] = to_retire_quant
            
        # what remains in retire_potential is not retired; to be concat with other pieces below
        
        mapping_dict = {'acct_name': 'retirement', 
                        'inst_cat': 'EIM_retire', 
                        'date_level': cq.date}
        to_retire = multiindex_change(to_retire, mapping_dict)
        
        # concat to_retire with all_accts remainder
        all_accts = pd.concat([all_accts.loc[~mask], retire_potential, to_retire], sort=True)
            
        logging.info(f"in {cq.date}: retired {to_retire['quant'].sum()} M for EIM Outstanding Emissions")
        
        
    else:
        # end of "if cq.date.year in [2018, 2019]:"
        # no EIM retirements
        pass

    if prmt.run_tests == True:
        name_of_allowances = 'EIM retirement'
        test_conservation_during_transfer(all_accts, all_accts_sum_init, name_of_allowances)
        parent_fn = str(inspect.currentframe().f_code.co_name)
        test_conservation_simple(all_accts, all_accts_sum_init, parent_fn)
        test_for_duplicated_indices(all_accts, parent_fn)
        test_for_negative_values(all_accts, parent_fn)

    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)


# In[ ]:


def retire_for_bankruptcy(all_accts):
    
    """
    No bankruptcy retirements under current regs (Oct 2017).
    
    In proposed new regs (Sep 2018), bankruptcy retirements added in 95911(h)(1).
    
    95911(h)(1): Starting in 2019, allowances will be retired to account for outstanding compliance obligations 
    due to bankruptcy, from the budget two years after the current budget year.
    
    Starting in 2019, allowances will be retired to account for outstanding compliance obligations due to bankruptcy,
    from the budget two years after the current budget year.

    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")

    bankruptcy_retirements = assign_bankruptcy_retirements()
    
    if prmt.CA_post_2020_regs in ['Preliminary_Discussion_Draft', 'Proposed_Regs_Sep_2018']:
        if cq.date.year in bankruptcy_retirements.index.tolist():
            # bankruptcy retirements come from annual budgets
            # If processed in Q4 of each year, would have to come out of annual budget for following year
            # so bankruptcy retirement in 2019Q4 would come from 2020 annual budget

            # get alloc_hold for vintage == cq.date.year + 2
            mask1 = all_accts.index.get_level_values('acct_name') == 'alloc_hold'
            mask2 = all_accts.index.get_level_values('vintage') == cq.date.year + 2
            mask = (mask1) & (mask2)

            # to avoid error "A value is trying to be set on a copy of a slice from a DataFrame."...
            # ... use .copy() when creating slice of alloc_hold_yr_plus_2 
            # ... & use .copy() in creating to_retire from alloc_hold_yr_plus_2
            alloc_hold_yr_plus_2 = all_accts.copy().loc[mask]
            remainder = all_accts.loc[~mask]

            # run only if df has length = 1
            if len(alloc_hold_yr_plus_2) == 1:

                # repeat slice of all_accts, to get df to modify for retirement
                # set value equal to quantity specified in Series bankruptcy_retirements
                to_retire = alloc_hold_yr_plus_2.copy()
                to_retire.at[to_retire.index, 'quant'] = bankruptcy_retirements.at[cq.date.year]
                mapping_dict = {'acct_name': 'retirement', 
                                'inst_cat': 'bankruptcy', 
                                'date_level': cq.date, }
                to_retire = multiindex_change(to_retire, mapping_dict)
                
                # update alloc_hold to have quantity remaining after retirement
                alloc_hold_yr_plus_2_original = alloc_hold_yr_plus_2['quant'].sum()
                alloc_hold_yr_plus_2_new = alloc_hold_yr_plus_2_original - bankruptcy_retirements.at[cq.date.year]
                alloc_hold_yr_plus_2.at[alloc_hold_yr_plus_2.index, 'quant'] = alloc_hold_yr_plus_2_new

                # recombine dfs:
                all_accts = pd.concat([remainder, alloc_hold_yr_plus_2, to_retire])

            else:
                print("Error" + "! alloc_hold_yr_plus_2 was not a single row; here's the df:")
                print(alloc_hold_yr_plus_2)
        else: # cq.date.year not in bankruptcy_retirements.index.tolist()
            # no other known planned retirements for bankruptcies; no projection for future bankruptcies
            pass   
    else: 
        # current regs (Oct 2017) don't include bankruptcy
        pass
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts)


# In[ ]:


def transfer_unsold__from_auct_hold_to_APCR(all_accts):
    """
    For CA, transfers unsold stock to APCR if they have gone unsold for more than 24 months, 
    as long as they haven't already been retired for EIM removal.
    
    Based on CA regs (QC & ON have no roll over rule):
    [CA regs Oct 2017], § 95911(g)

    """
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # pre-test for conservation
    all_accts_sum_init = all_accts['quant'].sum()
    
    # cut-off date: if allowances with unsold_di of this date or earlier remain unsold, they roll over to APCR
    # this function runs after current auction in cq.date, 
    # so any remaining unsold for 2 years at the time the function runs...
    # ... will still be unsold at the start of the next quarter, at which point they'll be unsold > 2 years
    cut_off_date = quarter_period(f"{cq.date.year-2}Q{cq.date.quarter}")
    
    # get unsold CA state-owned current allowances in auct_hold, with unsold_di > 2 years (24 mo.) earlier
    mask1 = all_accts.index.get_level_values('acct_name')=='auct_hold'
    mask2 = all_accts.index.get_level_values('inst_cat')=='CA'
    mask3 = all_accts.index.get_level_values('auct_type')=='current'
    mask4 = all_accts.index.get_level_values('status')=='unsold'
    mask5 = all_accts.index.get_level_values('unsold_di') <= cut_off_date # see note below
    mask6 = all_accts['quant'] > 0
    mask = (mask1) & (mask2) & (mask3) & (mask4) & (mask5) & (mask6)
    
    # note: for applying cut_off_date, should be sufficient to use unsold_di==cut_off_date, but used <= to be safe

    # unsold to transfer to APCR
    df = all_accts.loc[mask]
    
    mapping_dict = {'acct_name': 'APCR_acct', 
                    'auct_type': 'reserve'}
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


# In[ ]:


def process_auction_cur_QC_all_accts(all_accts):
    """
    Processes current auction for QC, applying the specified order of sales (when auctions don't sell out).
    
    Order of sales based on regs:
    QC: _______ 
    
    Notes: Once it is confirmed to be working properly, this could be simplified by:
    1. not re-doing filtering from scratch each batch of allowances
    2. finishing new fn avail_to_sold_all_accts, to avoid repetitive code
    
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
            print("Warning" + "! avail_for_test is empty.")
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
        # (code adapted from avail_to_sold)
        
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

        # sales priority: state-owned allowances available for first time as current (including fka adv, if there are any)

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
        # (code adapted from avail_to_sold)
        
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
        all_accts = unsold_update_status(all_accts)

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


# In[ ]:


# create current quarter (cq) as object (instance of class Cq)
class Cq:
    def __init__(self, date):
        self.date = date
        
    def step_to_next_quarter(self):
        if self.date < prmt.model_end_date:
            self.date = (pd.to_datetime(f'{self.date.year}Q{self.date.quarter}') + DateOffset(months=3)).to_period('Q')
        else:
            pass
        
# create new object qc
cq = Cq(quarter_period('2012Q4'))


# In[ ]:


# update values in object prmt using functions

progress_bar_loading.wid.value += 1
print("getting data from input file") # potential for progress_bar_loading

prmt.CA_cap = initialize_CA_cap()
prmt.CA_APCR_MI = initialize_CA_APCR()
prmt.CA_advance_MI = initialize_CA_advance()
prmt.VRE_reserve_MI = initialize_VRE_reserve()

# get input: historical quarterly auction data
get_qauct_hist()

# get input: historical + projected quarterly auction data
# sets object attribute prmt.auction_sales_pcts_all
get_auction_sales_pcts_all()
    
# set qauct_new_avail; sets object attribute prmt.qauct_new_avail
create_qauct_new_avail()

# set compliance_events; sets object attribute prmt.compliance_events
get_compliance_events()

# ~~~~~~~~~~~~

# sets object attributes prmt.CIR_historical & prmt.CIR_offsets_q_sums
get_CIR_data_and_clean()

# get historical data for VRE; assume no more retirements
# sets object attribute prmt.VRE_retired
get_VRE_retired_from_CIR()

# ~~~~~~~~~~~~

# initialization of allocations
CA_alloc_data = read_CA_alloc_data()
elec_alloc_IOU, elec_alloc_POU = initialize_elec_alloc()
nat_gas_alloc = initialize_nat_gas_alloc(CA_alloc_data)
industrial_etc_alloc = initialize_industrial_etc_alloc(CA_alloc_data)

# initialization of consignment vs. non-consignment
# run fn create_consign_historical_and_projection_annual (many returns)
consign_ann, consign_elec_IOU, consign_nat_gas, consign_elec_POU, nat_gas_not_consign, elec_POU_not_consign = create_consign_historical_and_projection_annual(
    elec_alloc_IOU, elec_alloc_POU, nat_gas_alloc)

# upsample consignment; sets object attribute prmt.consign_hist_proj
consign_upsample_historical_and_projection(consign_ann)

# convert all allocations into MI (for all vintages) & put into one df; set as object attribute prmt.CA_alloc_MI_all
CA_alloc_consign_dfs = [consign_elec_IOU, consign_elec_POU, consign_nat_gas]
CA_alloc_dfs_not_consign = [industrial_etc_alloc, elec_POU_not_consign, nat_gas_not_consign]
CA_alloc_dfs = CA_alloc_consign_dfs + CA_alloc_dfs_not_consign
CA_alloc_MI_list = []
for alloc in CA_alloc_dfs:
    alloc_MI = convert_ser_to_df_MI_CA_alloc(alloc)
    CA_alloc_MI_list += [alloc_MI]
prmt.CA_alloc_MI_all = pd.concat(CA_alloc_MI_list)

# ~~~~~~~~~~~~

prmt.QC_cap, QC_advance, QC_APCR = get_QC_inputs()
prmt.QC_APCR_MI = convert_ser_to_df_MI(QC_APCR)
prmt.QC_advance_MI = convert_ser_to_df_MI(QC_advance)

get_QC_allocation_data()
# sets object attributes prmt.QC_alloc_initial, prmt.QC_alloc_trueups, prmt.QC_alloc_full_proj


# In[ ]:


# DEFINE CLASSES, CREATE OBJECTS

progress_bar_loading.wid.value += 1
print("creating scenarios")

# ~~~~~~~~~~~
# initialization
class Scenario_juris:
    def __init__(self, 
                 avail_accum, 
                 cur_sell_out_counter, 
                 reintro_eligibility, 
                 snaps_CIR, 
                 snaps_end):
        self.avail_accum = avail_accum # initialize as empty
        self.cur_sell_out_counter = cur_sell_out_counter # initialize as empty
        self.reintro_eligibility = reintro_eligibility # initialize as empty
        self.snaps_CIR = snaps_CIR # initialize as empty
        self.snaps_end = snaps_end # initialize as empty

# make an instance of Scenario for CA hindcast starting in 2012Q4
scenario_CA = Scenario_juris(
    avail_accum=prmt.standard_MI_empty.copy(),
    cur_sell_out_counter=0,
    reintro_eligibility=False,
    snaps_CIR=[],
    snaps_end=[],
)
logging.info("created object scenario_CA")

# make an instance of Scenario for QC hindcast starting in 2013Q4
scenario_QC = Scenario_juris(
    avail_accum=prmt.standard_MI_empty.copy(),
    cur_sell_out_counter=0,
    reintro_eligibility=False, 
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
# starts empty, but will be filled by fn ______
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
        description='Quebec:',
        bar_style='', # 'success', 'info', 'warning', 'danger' or ''
        orientation='horizontal',
    ))


# # START OF MODEL RUN

# ## USER PARAMETERS

# In[ ]:


def assign_EIM_retirements():
    """
    Assign quantities for EIM Outstanding Emissions retirements in 2018, 2019, and 2020.
    
    These are for EIM Outstanding Emissions incurred in 2017, 2018, and 2019Q1.
    
    As of Oct. 2018, there was no clear data on quantities to be retired for EIM Outstanding Emissions.
    
    Therefore values here are set to zero until more information is available.
    
    """
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (start)")

    EIM_retirements_dict = {2018: 0, 
                            2019: 0, 
                            2020: 0 / 4}
    
    EIM_retirements = pd.Series(EIM_retirements_dict)
    EIM_retirements.name = 'EIM_retirements'
    EIM_retirements.index.name = 'year processed'
    
    return(EIM_retirements)
    
# ~~~~~~~~~~~~~~~~~~

def assign_bankruptcy_retirements():
    """
    Handling of bankruptcy retirements based on "2018 Regulation Documents (Narrow Scope)": 
    https://www.arb.ca.gov/regact/2018/capandtradeghg18/capandtradeghg18.htm
    
    Quantity for 2019 based on ARB statement in ARB, "Supporting Material for Assessment of Post-2020 Caps" (Apr 2018):
    https://www.arb.ca.gov/cc/capandtrade/meetings/20180426/carb_post2020caps.pdf
    "Approximately 5 million allowances to be retired in response to a recent bankruptcy"
    """
    logging.info(f"initialization: {inspect.currentframe().f_code.co_name} (start)")
    
    # bankruptcy retirements (units MMTCO2e)
    # add additional key and value pairs below, if more bankruptcies are identified
    bankruptcy_retirements_dict = {2019: 5}

    bankruptcy_retirements = pd.Series(bankruptcy_retirements_dict)
    bankruptcy_retirements.name = 'bankruptcy_retirements'
    bankruptcy_retirements.index.name = 'year processed'
    
    return(bankruptcy_retirements)


# In[ ]:


def initialize_all_accts():
    """
    Create version of df all_accts for start of model run, for each juris (CA & QC).
    
    What is in this df at start of run depends on the time point at which the model run begins.
    
    Default is to use historical data + projection of all auctions selling out. 
    
    Model may run as forecast, in which case it defaults to pre-run results for all auctions selling out.
    
    Or model may run as hindcast + forecast, in which case it repeats historical steps.
    """
    
    progress_bar_loading.wid.value += 1
    print("initializing accounts") # potential for progress_bar_loading
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")

    # if there are user settings from online model, override defaults above
    # but do this only if years_not_sold_out is *not* and empty list & prmt.fract_not_sold > 0.0
    # if prmt.years_not_sold_out is empty and/or prmt.fract_not_sold==1.0, then don't need to do run
    # already have results in pre-run scenario in which all auctions after 2018Q3 sell out

    # should be able to remove wrapping if statement below; 
    # this func (initialize_all_accts) is called only if these conditions were already found to be true
    
    if prmt.run_hindcast == True:        
        # for initial conditions of market
        # set attributes of objects scenario_CA and scenario_QC
        # note that scenario attribute snaps_end is a *list* of dfs
        scenario_CA.avail_accum = prmt.standard_MI_empty.copy()
        scenario_CA.cur_sell_out_counter = 0
        scenario_CA.reintro_eligibility = False
        scenario_CA.snaps_end = []
        logging.info("initialized scenario_CA attributes for hindcast")
        
        scenario_QC.avail_accum = prmt.standard_MI_empty.copy()
        scenario_QC.cur_sell_out_counter = 0
        scenario_QC.reintro_eligibility = False
        scenario_QC.snaps_end = []
        logging.info("initialized scenario_QC attributes for hindcast")

        # initialize all_accts_CA & all_accts_QC
        all_accts_CA = prmt.standard_MI_empty.copy()
        all_accts_QC = prmt.standard_MI_empty.copy()

    elif prmt.run_hindcast == False and prmt.years_not_sold_out != () and prmt.fract_not_sold > 0.0:       
        
        # DELETE; no need to reinitialize
#         # reinitialize all_accts_CA & all_accts_QC
#         all_accts_CA = prmt.standard_MI_empty.copy()
#         all_accts_QC = prmt.standard_MI_empty.copy()

        # get the first year of projection with auctions that don't sell out
        first_proj_yr_not_sold_out = prmt.years_not_sold_out[0]

        # set new values for start dates
        # use default projection (all sell out) for all years that sell out
        # start calculating projection from first year that doesn't sell out
        prmt.CA_start_date = quarter_period(f"{first_proj_yr_not_sold_out}Q1")
        prmt.QC_start_date = quarter_period(f"{first_proj_yr_not_sold_out}Q1")
        
        # CA: generate (revised) list of quarters to iterate over (inclusive)
        # range has DateOffset(months=3) at the end, because end of range is not included in the range generated
        prmt.CA_quarters = pd.date_range(start=quarter_period(prmt.CA_start_date).to_timestamp(), 
                                         end=quarter_period(prmt.CA_end_date).to_timestamp() + DateOffset(months=3),
                                         freq='Q').to_period('Q')

        # QC: generate (revised) list of quarters to iterate over (inclusive)
        # range has DateOffset(months=3) at the end, because end of range is not included in the range generated
        prmt.QC_quarters = pd.date_range(start=quarter_period(prmt.QC_start_date).to_timestamp(),
                                         end=quarter_period(prmt.QC_end_date).to_timestamp() + DateOffset(months=3),
                                         freq='Q').to_period('Q')
        
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        
        # get output of model results for historical + projection of all sell out        
        # get from object attribute prmt.snaps_end_Q4
        
        # create mask for only the years snap_q.year < first_proj_yr_not_sold_out
        # prmt.snaps_end_Q4 has snaps_q as column next to 'quant'
        # this makes it ready to use as attribute (Scenario.snaps_end)
        test_snaps_end_Q4_sum()
        up_to_year_mask = prmt.snaps_end_Q4['snap_q'].dt.year < first_proj_yr_not_sold_out

        # create masks for each juris
        CA_mask = prmt.snaps_end_Q4.index.get_level_values('juris') == 'CA'
        QC_mask = prmt.snaps_end_Q4.index.get_level_values('juris') == 'QC'
        
        # use these masks below to set object attributes scenario_CA.snaps_end and scenario_QC.snaps_end
        
        # ~~~~~~~
        
        # snaps_CIR
        # if restoring snaps_CIR, follow same pattern as above for snaps_end
        
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # TO DO: add avail_accum from all sell out scenario
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        
        # set attributes of objects scenario_CA and scenario_QC
        # note that scenario attribute snaps_end is a *list* of dfs
        scenario_CA.avail_accum = prmt.standard_MI_empty.copy() # need to fill in with results prior to start_date
        scenario_CA.cur_sell_out_counter = 5 # was 4 after 2018Q3; would be > 4 if more auctions sold out
        scenario_CA.reintro_eligibility = True
        scenario_CA.snaps_end = [prmt.snaps_end_Q4.loc[(up_to_year_mask) & (CA_mask)]]
        logging.info("updated scenario_CA attributes")
        
        scenario_QC.avail_accum = prmt.standard_MI_empty.copy() # need to fill in with results prior to start_date
        scenario_QC.cur_sell_out_counter = 5 # was 4 after 2018Q3; would be > 4 if more auctions sold out
        scenario_QC.reintro_eligibility = True
        scenario_QC.snaps_end = [prmt.snaps_end_Q4.loc[(up_to_year_mask) & (QC_mask)]]
        logging.info("updated scenario_QC attributes")

        # create mask to choose 1 quarter to use as starting point for model run
        one_quarter_mask = prmt.snaps_end_Q4['snap_q'].dt.year == first_proj_yr_not_sold_out - 1

        # use together with jurisdiction masks created earlier
        
        # select only the one quarter; drop column 'snap_q'
        all_accts_CA = prmt.snaps_end_Q4.loc[(one_quarter_mask) & (CA_mask)]
        all_accts_CA = all_accts_CA.drop(columns=['snap_q'])
        
        all_accts_QC = prmt.snaps_end_Q4.loc[(one_quarter_mask) & (QC_mask)]
        all_accts_QC = all_accts_QC.drop(columns=['snap_q'])
    
    elif prmt.run_hindcast == False and prmt.years_not_sold_out != () and prmt.fract_not_sold > 0.0:
        # use pre-run scenario for supply-demand balance
        # drawn directly from prmt.snaps_end_Q4 [ck]
        pass
    
    else:
        print("Unknown condition; shouldn't have reached here.")
    
    # end of "prmt.years_not_sold_out != () ... "
    
    # DELETE: don't need this additional UI step; this function goes quickly now
#     print("Processing auctions...", end=' ') # for UI
    
    # note: after this function finishes, model next runs process_auctions_CA_QC, process_CA & process_QC
    # then goes into supply_demand_calculations
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts_CA, all_accts_QC)

# end of initialize_all_accts


# In[ ]:


def progress_bars_initialize_and_display():
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
            
# end of progress_bars_initialize_and_display


# ## California

# In[ ]:


# %%snakeviz

def process_CA(all_accts_CA):
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
        else:
            pass
            
        # decadal creation of allowances & transfers
        if cq.date == quarter_period('2018Q1'):
            # occurs before process_CA_quarterly for 2018Q1, and therefore included in 2018Q1 snap
            # by including it here before any other steps in 2018, then can have consistent budget for 2018

            # create CA, QC, and ON allowances v2021-v2030, put into alloc_hold
            all_accts_CA = create_annual_budgets_in_alloc_hold(all_accts_CA, prmt.CA_cap.loc[2021:2030])

            # transfer advance into auct_hold
            all_accts_CA = transfer__from_alloc_hold_to_specified_acct(all_accts_CA, prmt.CA_advance_MI, 
                                                                       2021, 2030)

        # projection that APCR 2021-2030 will occur in 2018Q4
        elif cq.date == quarter_period('2018Q4'): 
            # transfer CA APCR allowances out of alloc_hold, into APCR_acct (for vintages 2021-2030)
            # (not yet; CA APCR allowances still in alloc_hold, as of 2018Q2 CIR)
            # note: quantities in APCR 2021-2030 are affected by model setting for CA_post_2020_regs
            all_accts_CA = transfer__from_alloc_hold_to_specified_acct(all_accts_CA, prmt.CA_APCR_MI, 
                                                                       2021, 2030)
        else:
            pass

        # ***** PROCESS QUARTER FOR cq.date (START) *****

        all_accts_CA = process_CA_quarterly(all_accts_CA)

        # ***** PROCESS QUARTER FOR cq.date (END) *****

        # update progress bar
        if progress_bar_CA.wid.value <= len(prmt.CA_quarters):
            progress_bar_CA.wid.value += 1
                    
        # at end of each quarter, step cq.date to next quarter
        cq.step_to_next_quarter()

        logging.info(f"******** end of {cq.date} ********")
        logging.info("------------------------------------")
        
    # end of loop "for quarter_year in prmt.CA_quarters:"
    
    return(all_accts_CA)
# end of process CA quarters


# ## Quebec

# In[ ]:


# %%snakeviz

def process_QC(all_accts_QC):
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # initialize cq.date to QC_start_date
    # in initialize_all_accts, if online user settings, then sets new value for QC_start_date 
    # (using first_proj_yr_not_sold_out)
    cq.date = prmt.QC_start_date
    
    for quarter_year in prmt.QC_quarters:
        logging.info(f"******** start of {cq.date} ********")

        # one-off steps **************************
        if cq.date == quarter_period('2013Q4'):
            # initialize QC auctions
            all_accts_QC = initialize_QC_auctions_2013Q4(all_accts_QC)

        elif cq.date == quarter_period('2014Q1'):
            # Early Action allowances distributed 2014Q1
            all_accts_QC = QC_early_action_distribution(all_accts_QC)
            
        elif cq.date == quarter_period('2018Q1'):
            # occurs before process_QC_quarterly for 2018Q1, and therefore included in 2018Q1 snap
            # by including it here before any other steps in 2018, then can have consistent budget for 2018
            
            # decadal creation of allowances & transfers
            # create QC, QC, and ON allowances v2021-v2030, put into alloc_hold
            all_accts_QC = create_annual_budgets_in_alloc_hold(all_accts_QC, prmt.QC_cap.loc[2021:2030])

            # transfer QC APCR allowances out of alloc_hold, into APCR_acct (for vintages 2021-2030)
            # (QC APCR allowances still in alloc_hold, as of 2018Q2 CIR)
            all_accts_QC = transfer__from_alloc_hold_to_specified_acct(all_accts_QC, prmt.QC_APCR_MI, 2021, 2030)

            # transfer advance into auct_hold
            all_accts_QC = transfer__from_alloc_hold_to_specified_acct(all_accts_QC, prmt.QC_advance_MI, 2021, 2030)
        
        else:
            pass
        # end of one-off steps **************************
        

        # ***** PROCESS QUARTER FOR cq.date *****
        
        all_accts_QC = process_QC_quarterly(all_accts_QC)
        
        # ***** END OF PROCESS QUARTER FOR cq.date *****
  
        # update progress bar
        if progress_bar_QC.wid.value <= len(prmt.QC_quarters):
            progress_bar_QC.wid.value += 1
        
        # at end of each quarter, move cq.date to next quarter
        cq.step_to_next_quarter()
            
        logging.info(f"******** end of {cq.date} ********")
        logging.info("------------------------------------")
        
    # end of loops "for quarter_year in prmt.QC_quarters:"
    
    return(scenario_QC, all_accts_QC)

# end of process QC quarters


# ## CA-QC results

# In[ ]:


def process_auctions_CA_QC():
    """
    Overall function to run all initialization steps, then auctions etc. for CA & QC.
    
    Default is to revert to pre-run scenario in which all auctions after 2018Q3 sell out.
    
    Only run auctions if there are auctions that do not sell out.
    """

    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")

    print("Running auctions:", end=' ') # for UI
    
    # initialize all_accts for both CA & QC
    all_accts_CA, all_accts_QC = initialize_all_accts()

    # create progress bars using updated start dates and quarters
    progress_bars_initialize_and_display()

    # process quarters for CA & QC
    all_accts_CA = process_CA(all_accts_CA)
    all_accts_QC = process_QC(all_accts_QC)
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (end)")
    
    return(all_accts_CA, all_accts_QC)


# In[ ]:


if prmt.run_hindcast == True:
    # then do hindcast from the start of the WCI system
    # (model default is for prmt.run_hindcast = False)
    all_accts_CA, all_accts_QC = process_auctions_CA_QC()
else: 
    # then prmt.run_hindcast == False
    # using pre-run scenario prmt.snaps_end_Q4 (in which all sell out) as starting point
    # all_accts_CA, all_accts_QC were set in initialize_all_accts
    pass


# # BANKING METRIC

# In[ ]:


def emissions_projection():
    """
    Calculate projection for covered emissions based on user settings.
    
    Default is -2%/year change for both CA and QC.
    
    Default based on PATHWAYS projection in Scoping Plan case that "covered sector" emissions change would be ~ -2%/yr.
    
    Although "covered sector" emissions ~10% higher than covered emissions, for annual change it's a good proxy.
    
    Model assumes QC will make same annual change as CA.
    """
    logging.info(f"{inspect.currentframe().f_code.co_name}")
    
    progress_bar_loading.wid.value += 1
    print("creating emissions projection") # potential for progress_bar_loading

    cov_em_df = pd.read_excel(prmt.input_file, sheet_name='covered emissions')
    cov_em_df = cov_em_df.drop(['source CA', 'source QC', 'units'], axis=1)
    cov_em_df = cov_em_df.set_index('year')

    # convert each into Series
    CA_em_hist = cov_em_df['CA'].dropna()
    QC_em_hist = cov_em_df['QC'].dropna()

    # create new Series, which will have projections appended
    CA_em_all = CA_em_hist.copy()
    QC_em_all = QC_em_hist.copy()

    last_hist_year = CA_em_hist.index[-1]
    
    if emissions_tabs.selected_index == 0:
        # simple settings
        logging.info("using emissions settings (simple)")
        # get user specified emissions annual change
        # calculate emissions trajectories to 2030
        for year in range(last_hist_year+1, 2030+1):
            CA_em_all.at[year] = CA_em_all.at[year-1] * (1 + em_pct_CA_simp.slider.value)
            QC_em_all.at[year] = QC_em_all.at[year-1] * (1 + em_pct_QC_simp.slider.value)
        
    elif emissions_tabs.selected_index == 1:
        # advanced settings
        logging.info("using emissions settings (advanced)")
        for year in range(last_hist_year+1, 2020+1):
            CA_em_all.at[year] = CA_em_all.at[year-1] * (1 + em_pct_CA_adv1.slider.value)
            QC_em_all.at[year] = QC_em_all.at[year-1] * (1 + em_pct_QC_adv1.slider.value)
            
        for year in range(2020+1, 2025+1):
            CA_em_all.at[year] = CA_em_all.at[year-1] * (1 + em_pct_CA_adv2.slider.value)
            QC_em_all.at[year] = QC_em_all.at[year-1] * (1 + em_pct_QC_adv2.slider.value)
            
        for year in range(2025+1, 2030+1):
            CA_em_all.at[year] = CA_em_all.at[year-1] * (1 + em_pct_CA_adv3.slider.value)
            QC_em_all.at[year] = QC_em_all.at[year-1] * (1 + em_pct_QC_adv3.slider.value)
        
    elif emissions_tabs.selected_index == 2:        
        # custom scenario input through text box
        custom = parse_emissions_text(em_text_input_CAQC_obj.wid.value)
        
        if isinstance(custom, str):
            if custom == 'blank' or custom == 'missing_slash_t' or custom == 'misformatted':
                # revert to default; relevant error_msg set in parse_emissions_text

                # calculate default
                for year in range(last_hist_year+1, 2030+1):
                    CA_em_all.at[year] = CA_em_all.at[year-1] * (1 + -0.02)
                    QC_em_all.at[year] = QC_em_all.at[year-1] * (1 + -0.02)
            else:
                error_msg = "Error" + "! Unknown problem with input (possibly formatting issue). Reverting to default of -2%/year."
                logging.info(error_msg)
                prmt.error_msg_post_refresh += [error_msg]  

        elif isinstance(custom, pd.Series):
            if custom.index.min() > 2017 or custom.index.max() < 2030:
                # projection is missing years

                error_msg = "Error" + "! Projection needs to cover each year from 2017 to 2030. Reverting to default of -2%/year."
                logging.info(error_msg)
                prmt.error_msg_post_refresh += [error_msg]

                # calculate default
                for year in range(last_hist_year+1, 2030+1):
                    CA_em_all.at[year] = CA_em_all.at[year-1] * (1 + -0.02)
                    QC_em_all.at[year] = QC_em_all.at[year-1] * (1 + -0.02)

            elif custom.index.min() <= 2017 and custom.index.max() >= 2030:
                # projection has all needed years

                # keep only years from 2017 to 2030
                custom = custom.loc[(custom.index >= 2017) & (custom.index <= 2030)]

                # *** ASSUMPTION ***
                # assume that CA emissions are a proportional share of the projected CA+QC emissions
                # proportion is based on CA portion of CA+QC caps (~84.6%) over projection period 2017-2030
                CA_caps_2017_2030 = prmt.CA_cap.loc[2017:2030].sum()
                CAQC_caps_2017_2030 = pd.concat([prmt.CA_cap.loc[2017:2030], prmt.QC_cap.loc[2017:2030]]).sum()
                CA_proportion = CA_caps_2017_2030 / CAQC_caps_2017_2030

                CA_em_all = CA_proportion * custom
                QC_em_all = (1 - CA_proportion) * custom

                # fill in historical data; don't let user override historical data
                CA_em_all = pd.concat([CA_em_hist.loc[2013:2016], CA_em_all], axis=0)
                QC_em_all = pd.concat([QC_em_hist.loc[2013:2016], QC_em_all], axis=0)

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
        for year in range(last_hist_year+1, 2030+1):
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
        
    # no returns; sets attributes
# end of emissions_projection


# In[ ]:


def offsets_projection():
    """
    DOCSTRING
    """
    logging.info(f"{inspect.currentframe().f_code.co_name}")

    offsets_priv_hist = prmt.CIR_offsets_q_sums[['General', 'Compliance']].sum(axis=1)

    # get offsets retired for compliance obligations from input file, sheet "annual compliance reports"
    offsets_compl_oblig_hist = prmt.compliance_events.xs('offsets', level='vintage or type')

    offsets_compl_oblig_hist_cumul = offsets_compl_oblig_hist.cumsum()

    # calculate cumulative offsets added to supply
    # (excludes any offsets that were retired anomalously--that is, not for compliance obligations)
    df = pd.concat([offsets_priv_hist, offsets_compl_oblig_hist_cumul], axis=1)
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

    # # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # PROJECTION TO FILL OUT REMAINING QUARTERS IN YEAR WITH PARTIAL DATA
    # if a year has only partial quarterly data, make projection for remainder of year
    last_hist_date = offsets_supply_q.index[-1]

    if last_hist_date.year == 2018:
        # hard-code in projection for 2018
        # because we know there was a very large forestry project issuance in 2017Q4-2018Q1
        for quarter in range(last_hist_date.quarter+1, 4+1):
            # assume Q4 same as Q2-Q3 average

            # get 2018Q2-Q3 average
            offsets_2018Q2 = offsets_supply_q.at[quarter_period('2018Q2')]
            offsets_2018Q3 = offsets_supply_q.at[quarter_period('2018Q3')]
            offsets_2018Q2_Q3_avg = (offsets_2018Q2 + offsets_2018Q3) / 2

            # calculate projection
            year_q = quarter_period(f'2018Q{quarter}')
            offsets_supply_q.at[year_q] = offsets_2018Q2_Q3_avg

    else:
        for quarter in range(last_hist_date.quarter+1, 4+1):
            # use average of previous 4 quarters
            offsets_supply_past_4Q = offsets_supply_q.loc[offsets_supply_q.index[-4]:]
            offsets_supply_past_4Q_avg = offsets_supply_past_4Q.sum() / 4

            logging.info("offsets_supply_past_4Q_avg: {offsets_supply_past_4Q_avg}")

            # use average values to calculate
            year_q = quarter_period(f'{last_hist_date.year}Q{quarter}')
            offsets_supply_q.at[year_q] = offsets_supply_past_4Q_avg

    # end of projection to fill out last historical year with partial data

    # calculate annual offset totals
    offsets_supply_ann = offsets_supply_q.resample('A').sum()
    offsets_supply_ann.index = offsets_supply_ann.index.year.astype(int)
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # PROJECTION BEYOND LAST YEAR WITH HISTORICAL DATA
    # use ARB's assumption for 2021-2030, from Post-2020 analyis
    prmt.offset_rate_fract_of_limit = 0.75
    
    # note that this is about the same as what historical analysis through 2018Q2 gives
    # from 2018Q2 CIR, ~100 M offsets cumulative supply
    # cumulative CA-QC covered emissions through 2018Q2 were 1666 M ***if*** emissions fell 2%/yr after 2016
    # which means offsets issued through 2018Q2 were about 6.0% of emissions
    # with the offset limit for CA & QC over this period set at 8%, 
    # then the issuance is 75% of the limit
    # and that's the same as ARB's assumption (although ARB didn't state a rationale)
    
    # the offset_rate_fract_of_limit above also sets the default value in offset sliders

    # ~~~~~~~~~
    
    # get values from sliders 
    # (before user does first interaction, will be based on default set above)
    
    # print(f"show offsets_tabs.selected_index for default case: {offsets_tabs.selected_index}")
    
    if offsets_tabs.selected_index == 0:
        # simple settings
        logging.info("using offsets settings (simple)")
        
        # get user specified offsets use rate, as % of limit (same rate for all periods)
        for year in range(last_hist_date.year+1, 2020+1):
            # for CA & QC together
            offset_rate_ann = off_pct_of_limit_CAQC.slider.value * 0.08
            offsets_supply_ann.at[year] = prmt.emissions_ann.at[year] * offset_rate_ann
            
        for year in range(2020+1, 2025+1):
            # for CA & QC separately
            offset_rate_CA = off_pct_of_limit_CAQC.slider.value * 0.04
            offset_rate_QC = off_pct_of_limit_CAQC.slider.value * 0.08
            
            offsets_supply_ann_CA_1y = prmt.emissions_ann_CA.at[year] * offset_rate_CA
            offsets_supply_ann_QC_1y = prmt.emissions_ann_QC.at[year] * offset_rate_QC
            
            # combine CA & QC
            offsets_supply_ann.at[year] = offsets_supply_ann_CA_1y + offsets_supply_ann_QC_1y
            
        for year in range(2025+1, 2030+1):
            # for CA & QC separately
            offset_rate_CA = off_pct_of_limit_CAQC.slider.value * 0.06
            offset_rate_QC = off_pct_of_limit_CAQC.slider.value * 0.08
            
            offsets_supply_ann_CA_1y = prmt.emissions_ann_CA.at[year] * offset_rate_CA
            offsets_supply_ann_QC_1y = prmt.emissions_ann_QC.at[year] * offset_rate_QC
            
            # combine CA & QC
            offsets_supply_ann.at[year] = offsets_supply_ann_CA_1y + offsets_supply_ann_QC_1y
            
    elif offsets_tabs.selected_index == 1:
        # advanced settings
        logging.info("using offsets settings (advanced)")
        
        for year in range(last_hist_date.year+1, 2020+1):
            # for CA & QC separately, using period 1 sliders
            offset_rate_CA = off_pct_CA_adv1.slider.value
            offset_rate_QC = off_pct_QC_adv1.slider.value
            
            offsets_supply_ann_CA_1y = prmt.emissions_ann_CA.at[year] * offset_rate_CA
            offsets_supply_ann_QC_1y = prmt.emissions_ann_QC.at[year] * offset_rate_QC
            
            # combine CA & QC
            offsets_supply_ann.at[year] = offsets_supply_ann_CA_1y + offsets_supply_ann_QC_1y
            
        for year in range(2020+1, 2025+1):
            # for CA & QC separately, using period 2 sliders
            offset_rate_CA = off_pct_CA_adv2.slider.value
            offset_rate_QC = off_pct_QC_adv2.slider.value
            
            offsets_supply_ann_CA_1y = prmt.emissions_ann_CA.at[year] * offset_rate_CA
            offsets_supply_ann_QC_1y = prmt.emissions_ann_QC.at[year] * offset_rate_QC
            
            # combine CA & QC
            offsets_supply_ann.at[year] = offsets_supply_ann_CA_1y + offsets_supply_ann_QC_1y
            
        for year in range(2025+1, 2030+1):
            # for CA & QC separately, for period 3 sliders
            offset_rate_CA = off_pct_CA_adv3.slider.value
            offset_rate_QC = off_pct_QC_adv3.slider.value
            
            offsets_supply_ann_CA_1y = prmt.emissions_ann_CA.at[year] * offset_rate_CA
            offsets_supply_ann_QC_1y = prmt.emissions_ann_QC.at[year] * offset_rate_QC
            
            # combine CA & QC
            offsets_supply_ann.at[year] = offsets_supply_ann_CA_1y + offsets_supply_ann_QC_1y

    else:
        # offsets_tabs.selected_index is not 0 or 1
        print("Error" + "! offsets_tabs.selected_index was not one of the expected values (0 or 1).")

    offsets_supply_ann.name = 'offsets_supply_ann'
    
    # calculate quarterly values for all years
    # first get all annual supply full year projections
    df = offsets_supply_ann.loc[offsets_supply_q.index.year[-1]+1:]

    # divide by 4, reassign index to quarterly, fill in missing data (Q2-Q4)
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
    
    return(offsets_supply_q, offsets_supply_ann)
# end of offsets_projection


# In[ ]:


def excess_offsets_calc(offsets_supply_q):
    """
    Calculate whether the offset supply (as specified by user) exceeds what could be used through 2030.
    
    For all compliance periods *except* period #5 (for emissions 2024-2026):
    assume ARB allows emitters to go up to max for whole compliance period, 
    regardless of offset use in annual compliance events during that compliance period.
    
    For compliance period #5, for CA, max offsets are applied separately to emissions 2024-2025 and emissions 2026.
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")

    # get historical record of offsets used for compliance
    offsets_used_hist = prmt.compliance_events.loc[
        prmt.compliance_events.index.get_level_values('vintage or type')=='offsets']
    
    # get the latest year with compliance event data
    latest_comp_y = prmt.compliance_events.index.get_level_values('compliance_date').max().year

    # initialize first_em_year, which is first year of emissions for each compliance period
    first_em_year = 2015
    
    # initialize offsets used
    offsets_used_in_completed_periods = 0
    
    # initialize offsets_avail (value is iteratively updated below)
    # offsets used in previous completed periods
    offsets_used_in_completed_periods += offsets_used_hist[
        offsets_used_hist.index.get_level_values('compliance_date').year<=first_em_year]['quant'].sum()
    
#     # offsets available for use in compliance period #1 (initialization)
#     offsets_supply_at_end_2015Q3 = offsets_supply_q.loc[:quarter_period(f'{first_em_year}Q3')].sum()
#     offsets_supply_2015Q4_first_mo = offsets_supply_q.at[quarter_period(f'{first_em_year}Q4')] / 3
#     # Q4 first month above is an approximation
#     offsets_supply_at_p1_event = offsets_supply_at_end_2015Q3 + offsets_supply_2015Q4_first_mo
#     offsets_avail = offsets_supply_at_p1_event - offsets_used_in_completed_periods   

    # compliance period #2 obligations for emissions 2015-2017 (due Nov 1, 2018)
    if latest_comp_y < first_em_year+3:
        # latest CIR data is before 2018Q4, so simulate compliance period #2 obligations
        
        # offsets available for use in compliance period #2
        # Q3 and Q4 below refer to year of compliance event (first_em_year+3)
        offsets_supply_at_end_Q3 = offsets_supply_q.loc[:quarter_period(f'{first_em_year+3}Q3')].sum()
        offsets_supply_Q4_first_mo = offsets_supply_q.at[quarter_period(f'{first_em_year+3}Q4')] / 3
        # Q4 first month above is an approximation
        offsets_supply_at_event = offsets_supply_at_end_Q3 + offsets_supply_Q4_first_mo
        offsets_avail = offsets_supply_at_event - offsets_used_in_completed_periods
        
        # max offsets are 8% for both CA & QC; 
        max_off_p2_CA = prmt.emissions_ann_CA.loc[first_em_year:first_em_year+2].sum() * 0.08
        max_off_p2_QC = prmt.emissions_ann_QC.loc[first_em_year:first_em_year+2].sum() * 0.08
        
        # CA + QC: calculate the max offsets that could be used, given the offsets projection (offsets_supply_q)
        # minimum of: max that could be used in p2 & offsets available at time of p2
        max_off_p2_given_off_proj = min((max_off_p2_CA + max_off_p2_QC), offsets_avail)

#         # for debugging
#         print(f"max: {max_off_p2_CA + max_off_p2_QC}; avail: {offsets_avail}; %: {offsets_avail/(max_off_p2_CA + max_off_p2_QC)}")
#         if (max_off_p2_CA + max_off_p2_QC) > offsets_avail:
#             print("Compliance period 2: Offset use would be limited by available offsets")
#         elif (max_off_p2_CA + max_off_p2_QC) <= offsets_avail:
#             print("Compliance period 2: Offset use could be maxed out.")
            
        # update offsets_avail to remove max offset use
        offsets_avail += -1 * max_off_p2_given_off_proj
        offsets_used_in_completed_periods += max_off_p2_given_off_proj
        
#         print(f"show offsets_avail after p2 retirements: {offsets_avail}") # for db
#         print() # for db

    else:
        pass

    # ~~~~~~~~~~~~~~~~~~~~
    first_em_year += 3 # step forward 3 years

    # compliance period #3 obligations for emissions 2018-2020 (due Nov 1, 2021)
    if latest_comp_y < first_em_year+3:
        # latest CIR data is before 2021Q4, so simulate compliance period #3 obligations
        
        # offsets available for use in compliance period #3
        # Q3 and Q4 below refer to year of compliance event (first_em_year+3)
        offsets_supply_at_end_Q3 = offsets_supply_q.loc[:quarter_period(f'{first_em_year+3}Q3')].sum()
        offsets_supply_Q4_first_mo = offsets_supply_q.at[quarter_period(f'{first_em_year+3}Q4')] / 3
        # Q4 first month above is an approximation
        offsets_supply_at_event = offsets_supply_at_end_Q3 + offsets_supply_Q4_first_mo
        offsets_avail = offsets_supply_at_event - offsets_used_in_completed_periods 
        
        # max offsets are 8% for CA & QC
        max_off_p3_CA = prmt.emissions_ann_CA.loc[first_em_year:first_em_year+2].sum() * 0.08
        max_off_p3_QC = prmt.emissions_ann_QC.loc[first_em_year:first_em_year+2].sum() * 0.08
            
        # CA + QC: calculate the max offsets that could be used, given the offsets projection (offsets_supply_q)
        # minimum of: max that could be used in p3 & offsets available at time of p3
        max_off_p3_given_off_proj = min((max_off_p3_CA + max_off_p3_QC), offsets_avail)

#         # for debugging
#         print(f"max: {max_off_p3_CA + max_off_p3_QC}; avail: {offsets_avail}; %: {offsets_avail/(max_off_p3_CA + max_off_p3_QC)}")
#         if (max_off_p3_CA + max_off_p3_QC) > offsets_avail:
#             print("Compliance period 3: Offset use would be limited by available offsets")
#         elif (max_off_p3_CA + max_off_p3_QC) <= offsets_avail:
#             print("Compliance period 3: Offset use could be maxed out.")
        
        # update offsets_avail to remove max offset use
        offsets_avail += -1 * max_off_p3_given_off_proj
        offsets_used_in_completed_periods += max_off_p3_given_off_proj
        
#         print(f"show offsets_avail after p3 retirements: {offsets_avail}") # for db
#         print() # for db
        
    else:
        pass

    # ~~~~~~~~~~~~~~~~~~~~
    first_em_year += 3 # step forward 3 years

    # compliance period #4 obligations for emissions 2021-2023 (due Nov 1, 2024)
    if latest_comp_y < first_em_year+3:
        # latest CIR data is before 2021Q4, so simulate compliance period #4 obligations
        
        # offsets available for use in compliance period #4
        # Q3 and Q4 below refer to year of compliance event (first_em_year+3)
        offsets_supply_at_end_Q3 = offsets_supply_q.loc[:quarter_period(f'{first_em_year+3}Q3')].sum()
        offsets_supply_Q4_first_mo = offsets_supply_q.at[quarter_period(f'{first_em_year+3}Q4')] / 3
        # Q4 first month above is an approximation
        offsets_supply_at_event = offsets_supply_at_end_Q3 + offsets_supply_Q4_first_mo
        offsets_avail = offsets_supply_at_event - offsets_used_in_completed_periods 
        
        # max offsets are 4% for CA & 8% for QC
        max_off_p4_CA = prmt.emissions_ann_CA.loc[first_em_year:first_em_year+2].sum() * 0.04
        max_off_p4_QC = prmt.emissions_ann_QC.loc[first_em_year:first_em_year+2].sum() * 0.08
        
        # CA + QC: calculate the max offsets that could be used, given the offsets projection (offsets_supply_q)
        # minimum of: max that could be used in p4 & offsets available at time of p4
        max_off_p4_given_off_proj = min((max_off_p4_CA + max_off_p4_QC), offsets_avail)

#         # for debugging
#         print(f"max: {max_off_p4_CA + max_off_p4_QC}; avail: {offsets_avail}; %: {offsets_avail/(max_off_p4_CA + max_off_p4_QC)}")
#         if (max_off_p4_CA + max_off_p4_QC) > offsets_avail:
#             print("Compliance period 4: Offset use would be limited by available offsets")
#         elif (max_off_p4_CA + max_off_p4_QC) <= offsets_avail:
#             print("Compliance period 4: Offset use could be maxed out.")

        # update offsets_avail to remove max offset use
        offsets_avail += -1 * max_off_p4_given_off_proj
        offsets_used_in_completed_periods += max_off_p4_given_off_proj
        
#         print(f"show offsets_avail after p4 retirements: {offsets_avail}") # for db
#         print() # for db
        
    else:
        pass

    # ~~~~~~~~~~~~~~~~~~~~
    first_em_year += 3 # step forward 3 years

    # compliance period #5 obligations for emissions 2024-2026 (due in full Nov 1, 2027)

    # ***IMPORTANT NOTE***
    # this compliance period is anomalous for CA because of change in offset max use under AB 398 from 4% to 6%,
    # which doesn't match with timing of compliance period deadline

    if latest_comp_y < first_em_year+3:
        # latest CIR data is before 2021Q4, so simulate compliance period #5 obligations
        
        # offsets available for use in compliance period #5
        # Q3 and Q4 below refer to year of compliance event (first_em_year+3)
        offsets_supply_at_end_Q3 = offsets_supply_q.loc[:quarter_period(f'{first_em_year+3}Q3')].sum()
        offsets_supply_Q4_first_mo = offsets_supply_q.at[quarter_period(f'{first_em_year+3}Q4')] / 3
        # Q4 first month above is an approximation
        offsets_supply_at_event = offsets_supply_at_end_Q3 + offsets_supply_Q4_first_mo
        offsets_avail = offsets_supply_at_event - offsets_used_in_completed_periods 
        
        # for CA, max offsets are 4% for emissions incurred in 2024-2025, 6% for emissions incurred in 2026
        # for QC, max offsets are 8% of emissions for all years 2024-2026
 
        max_off_CA_2024_2025 = prmt.emissions_ann_CA.loc[first_em_year:first_em_year+1].sum() * 0.04
        max_off_CA_2026 = prmt.emissions_ann_CA.loc[first_em_year+2].sum() * 0.06
        max_off_p5_QC = prmt.emissions_ann_QC.loc[first_em_year:first_em_year+2].sum() * 0.08

        max_off_p5 = max_off_CA_2024_2025 + max_off_CA_2026 + max_off_p5_QC
        
        # CA + QC: calculate the max offsets that could be used, given the offsets projection (offsets_supply_q)
        # minimum of: max that could be used in p5 & offsets available at time of p5
        max_off_p5_given_off_proj = min((max_off_p5), offsets_avail)

#         # for debugging
#         print(f"max: {max_off_p5}; avail: {offsets_avail}; %: {offsets_avail/(max_off_p5)}")
#         if (max_off_p5) > offsets_avail:
#             print("Compliance period 5: Offset use would be limited by available offsets")
#         elif (max_off_p5) <= offsets_avail:
#             print("Compliance period 5: Offset use could be maxed out.")
        
        # update offsets_avail to remove max offset use
        offsets_avail += -1 * max_off_p5_given_off_proj
        offsets_used_in_completed_periods += max_off_p5_given_off_proj
        
#         print(f"show offsets_avail after p5 retirements: {offsets_avail}") # for db
#         print() # for db
        
    else:
        pass

    # ~~~~~~~~~~~~~~~~~~~~
    first_em_year += 3 # step forward 3 years

    # compliance period #6 obligations for emissions 2027-2029 (due Nov 1, 2030)

    if latest_comp_y < first_em_year+3:
        # latest CIR data is before 2021Q4, so simulate compliance period #6 obligations
        
        # offsets available for use in compliance period #6
        # Q3 and Q4 below refer to year of compliance event (first_em_year+3)
        offsets_supply_at_end_Q3 = offsets_supply_q.loc[:quarter_period(f'{first_em_year+3}Q3')].sum()
        offsets_supply_Q4_first_mo = offsets_supply_q.at[quarter_period(f'{first_em_year+3}Q4')] / 3
        # Q4 first month above is an approximation
        offsets_supply_at_event = offsets_supply_at_end_Q3 + offsets_supply_Q4_first_mo
        offsets_avail = offsets_supply_at_event - offsets_used_in_completed_periods 
        
        # max offsets are 6% for CA & 8% for QC
        max_off_p6_CA = prmt.emissions_ann_CA.loc[first_em_year:first_em_year+2].sum() * 0.06
        max_off_p6_QC = prmt.emissions_ann_QC.loc[first_em_year:first_em_year+2].sum() * 0.08
        
        # CA + QC: calculate the max offsets that could be used, given the offsets projection (offsets_supply_q)
        # minimum of: max that could be used in p6 & offsets available at time of p6
        max_off_p6_given_off_proj = min((max_off_p6_CA + max_off_p6_QC), offsets_avail)

#         # for debugging
#         print(f"max: {max_off_p6_CA + max_off_p6_QC}; avail: {offsets_avail}; %: {offsets_avail/(max_off_p6_CA + max_off_p6_QC)}")
#         if (max_off_p6_CA + max_off_p6_QC) > offsets_avail:
#             print("Compliance period 6: Offset use would be limited by available offsets")
#         elif (max_off_p6_CA + max_off_p6_QC) <= offsets_avail:
#             print("Compliance period 6: Offset use could be maxed out.")
#         # end debugging
        
        # update offsets_avail to remove max offset use
        offsets_avail += -1 * max_off_p6_given_off_proj
        offsets_used_in_completed_periods += max_off_p6_given_off_proj
        
#         print(f"show offsets_avail after p6 retirements: {offsets_avail}") # for db
#         print() # for db
        
    else:
        pass

    # ~~~~~~~~~~~~~~~~~~~~
    # after assuming max offset use, see if any offsets remaining in offsets_avail
    # if so, these are excess offsets
    # show warning only if the excess is significant (> 5 MMTCO2e)
    # note: when offset settings at 100% of limit, there can be ~3 M excess 
    # this is due to mismatches in timing of offset supply and compliance obligations
    if offsets_avail > 5: # units MMTCO2e
        prmt.excess_offsets = offsets_avail
        
        # round off for display
        excess_int = int(round(prmt.excess_offsets, 0))
        
        error_msg_1 = "Warning" + "! The scenario's settings led to excess offsets beyond what could be used by the end of 2030."
        logging.info(error_msg_1)
        prmt.error_msg_post_refresh += [error_msg_1]
        error_msg_2 = f"The excess of offsets was {excess_int} MMTCO2e."
        logging.info(error_msg_2)
        prmt.error_msg_post_refresh += [error_msg_2]
        line_break = " "
        prmt.error_msg_post_refresh += [line_break]
        
    else:
        prmt.excess_offsets = 0
        pass
    
    # no return; set object attribute above  

# end of excess_offsets_calc


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
    
    # AUCTIONS
    # results stored in object attributes scenario_CA.snaps_end & scenario_QC.snaps_end
    # (either default values or from new custom run)
    # these object attributes are accessed directly by supply_demand_calculations
    
    # NET FLOW FROM ON:
    # As noted in 2018Q2 CIR:
    # "As of that date, there are 13,186,967 more compliance instruments held in California and Québec accounts 
    # than the total number of compliance instruments issued by those two jurisdictions alone."
    net_flow_from_ON = 13.186967
    # added into allow_vintaged_cumul below, attributed to 2018
    
    # OFFSETS: calculated later in this func
    
    # ~~~~~~~~~~~~~~~~~~
    
    # BANKING METRIC: supply: allowances

    # create local variable snaps_end_Q4_CA_QC; use different source depending on scenario/settings
    # use copy to avoid modifying object attributes 
    # (either prmt.snaps_end_Q4 or scenario_CA.snaps_end & scenario_QC.snaps_end)
    
    if prmt.run_hindcast == True:
        # use new auction results in scenario_CA.snaps_end & scenario_QC.snaps_end
        # scenario_CA.snaps_end & scenario_QC.snaps_end are lists; concat all dfs in the combined list
        df = pd.concat(scenario_CA.snaps_end + scenario_QC.snaps_end, axis=0, sort=False)

        # keep only Q4
        snaps_end_Q4_CA_QC = df.loc[df['snap_q'].dt.quarter==4].copy()
    
    elif prmt.run_hindcast == False:
        if prmt.years_not_sold_out == () or prmt.fract_not_sold == float(0):
            # no new auction results; use default pre-run: prmt.snaps_end_Q4
            test_snaps_end_Q4_sum()
            snaps_end_Q4_CA_QC = prmt.snaps_end_Q4.copy()

        else:
            # there are new auction results in scenario_CA.snaps_end & scenario_QC.snaps_end
            # scenario_CA.snaps_end & scenario_QC.snaps_end are lists; concat all dfs in the combined list
            df = pd.concat(scenario_CA.snaps_end + scenario_QC.snaps_end, axis=0, sort=False)

            # keep only Q4
            snaps_end_Q4_CA_QC = df.loc[df['snap_q'].dt.quarter==4].copy()
        
    # create col 'snap_yr' to replace col 'snap_q'
    snaps_end_Q4_CA_QC['snap_yr'] = snaps_end_Q4_CA_QC['snap_q'].dt.year
    snaps_end_Q4_CA_QC = snaps_end_Q4_CA_QC.drop(columns=['snap_q'])

    # select only the allowances in private accounts (general account and compliance account)
    private_acct_mask = snaps_end_Q4_CA_QC.index.get_level_values('acct_name').isin(['gen_acct', 'comp_acct'])
    snaps_CAQC_toward_bank = snaps_end_Q4_CA_QC.loc[private_acct_mask]
    
    # ~~~~~~~~~~~~~~
    # ### allowances with vintages
    # B = **A'** + N + O - E

    # A': vintaged allowances sold or distributed
    # (before retirements for compliance, as is the case with all_accts & snaps)

    # specifically, of vintages up to year of banking metric
    # and excluding VRE allowances
    # filter snaps for allowances in gen_acct & comp_acct excludes VRE & unsold
    df = snaps_CAQC_toward_bank.copy()

    # mask1 = df.index.get_level_values('vintage') <= df.index.get_level_values('snap_q').year
    mask1 = df.index.get_level_values('vintage') <= df['snap_yr']
    mask2 = df.index.get_level_values('acct_name').isin(['gen_acct', 'comp_acct'])
    # note that mask2 will get vintages up to banking metric year, and also filter out non-vintage allowances
    mask = (mask1) & (mask2)
    df = df.loc[mask]

    # result contains allowances sold at advance and current auctions, as well as allowances freely allocated

    df = df.groupby('snap_yr').sum()
    df.index.name = 'snap_yr'
    
    # convert to Series by only selecting ['quant']
    allow_vintaged_cumul = df['quant']
    allow_vintaged_cumul.name = 'allow_vintaged_cumul'
    
    # get historical data
    # insert value for initial quarter (since diff turns that into NaN)
    allow_vint_ann = allow_vintaged_cumul.diff()
    first_year = allow_vint_ann.index.min()
    allow_vint_ann.at[first_year] = allow_vintaged_cumul.at[first_year]
    allow_vint_ann.name = 'allow_vint_ann'
    
    # add net flow from ON to 2018
    allow_vint_ann.at[2018] = allow_vint_ann.at[2018] + net_flow_from_ON
    
    # ~~~~~~~~~~~~~~
    # ### allowances with no vintage (APCR, Early Action)
    # B = A' + **N** + O - E

    # N: non-vintaged allowances (APCR and Early Action) in private accounts
    # (before retirements for compliance, as is the case with all_accts & snaps)

    df = snaps_CAQC_toward_bank.copy()

    # APCR assigned vintage 2200
    # Early Action assigned vintage 2199

    mask1 = df.index.get_level_values('vintage') >= 2199
    mask2 = df.index.get_level_values('acct_name').isin(['gen_acct', 'comp_acct'])

    mask = (mask1) & (mask2)
    df = df.loc[mask]

    df = df.groupby('snap_yr').sum()
    df.index.name = 'snap_yr'
    allow_nonvint_cumul = df['quant']
    allow_nonvint_cumul.name = 'allow_nonvint_cumul'

    # get historical data
    # insert value for initial quarter (since diff turns that into NaN)
    allow_nonvint_ann = allow_nonvint_cumul.diff()
    first_year = allow_nonvint_ann.index.min()
    allow_nonvint_ann.at[first_year] = allow_nonvint_cumul.at[first_year]
    allow_nonvint_ann.name = 'allow_nonvint_ann'

    # ~~~~~~~~~~~~~~
    # OFFSET SUPPLY:
    offsets_supply_q, offsets_supply_ann = offsets_projection()
    
    # calculation of excess offsets beyond what could be used
    # (depends on temporal pattern of when offsets are added to supply)
    # sets prmt.excess_offsets
    excess_offsets_calc(offsets_supply_q)

    # ~~~~~~~~~~~~~~
    
    # BANKING METRIC: calculation
    # BANOE method: annual
    # B = A' + N + O - E
    emissions_ann_neg = -1 * prmt.emissions_ann
    emissions_ann_neg.name = 'emissions_ann_neg'
    
    dfs_to_concat = [allow_vint_ann,
                     allow_nonvint_ann,
                     offsets_supply_ann,
                     prmt.emissions_ann,
                     emissions_ann_neg]
    bank_elements = pd.concat(dfs_to_concat, axis=1)
    
    bank_elements['bank_ann'] = bank_elements[['allow_vint_ann', 
                                               'allow_nonvint_ann',
                                               'offsets_supply_ann', 
                                               'emissions_ann_neg']].sum(axis=1)

    bank_elements = bank_elements.drop('emissions_ann_neg', axis=1)
    
    bank_elements['bank_cumul'] = bank_elements['bank_ann'].cumsum()
    
    # ~~~~~~~~~~~~~~
    # RESERVE SALES (& MODIFY BANKING METRIC)
    bank_cumul = bank_elements['bank_cumul']
    # here, bank_cumul_pos still could have negative values; below, those are overwritten with zeros

    reserve_sales_cumul = pd.Series() # initialize
    
    for year in bank_cumul.index:
        if bank_cumul.at[year] < 0:
            if year == 2013:
                reserve_sales_cumul.at[year] = -1 * bank_cumul.at[year]
                # (here, bank_cumul in the year is neg, reserve sales are positive)
                
            else: # year > 2013:                
                # if bank is negative, put those into reserve_sales
                # add to cumulative reserve sales over time
                reserve_sales_cumul.at[year] = reserve_sales_cumul.at[year-1] + (-1 * bank_cumul.at[year])
                # (here, bank_cumul in the year is neg, reserve sales are positive)
            
            # add *annual* reserve sales to bank_cumul, for all years from year to end
            # get annual reserves sales using diff of cumulative reserve sales
            for revision_year in range(year, bank_cumul.index.max()+1):
                bank_cumul.at[revision_year] = bank_cumul.at[revision_year] + reserve_sales_cumul.diff().at[year]
                # (here, bank_cumul in the year is neg, reserve sales are positive)
    
        else:
            if year == 2013:
                reserve_sales_cumul.at[year] = 0
                
            else: # year > 2013:
                # if bank is positive, leave bank as is, and cumulative reserve sales are same as previous year
                reserve_sales_cumul.at[year] = reserve_sales_cumul.at[year-1]
    
    reserve_sales = reserve_sales_cumul

    # create version of bank with only positive values (and if not positive, then zero)
    bank_cumul_pos = bank_cumul.copy()
    for year in bank_cumul.index:
        if bank_cumul.at[year] < 0:
            bank_cumul_pos.at[year] == 0
        else:
            pass
    
    # ~~~~~~~~~~~~~~
    # BALANCE METRIC: bank + unsold current allowances
    # note there are also allowances not in gen_acct or comp_acct:
    # unsold allowances, held in auct_hold
    # unsold APCR allowances, held in APCR_acct
    # VRE, held in VRE_acct
    
    df = snaps_end_Q4_CA_QC.copy()
    
    mask1 = df.index.get_level_values('acct_name') == 'auct_hold'
    mask2 = df.index.get_level_values('auct_type') == 'current' # to exclude advance
    mask3 = df.index.get_level_values('status') == 'unsold'
    mask = (mask1) & (mask2) & (mask3)
    df = df.loc[mask]
    unsold_cur_sum = df.groupby('snap_yr')['quant'].sum()

    # note that this is the year-end value of unsold in stock
    # so for 2017, it is the value in 2017Q4, after ~14 M allowances were reintro & sold in the 2017Q4 auction
    # the peak value was after 2017Q1 auction, with ~141 M unsold

    # balance = bank + unsold current allowances
    balance = pd.concat([bank_elements['bank_cumul'], unsold_cur_sum], axis=1).sum(axis=1)

    # note there are QC alloc held back for first true-up, which are retained in alloc_hold;
    # these could arguably be included in bank, but would add only ~4 M to annual supply each year (~1% of total supply)
    
    # ~~~~~~~~~~~~~~
    supply_ann = pd.concat([
        allow_vint_ann,
        allow_nonvint_ann,
        offsets_supply_ann], 
        axis=1).sum(axis=1)
    supply_ann.name = 'supply_ann'
    
    # ~~~~~~~~~~~~
    # set attributes 
    prmt.supply_ann = supply_ann
    prmt.bank_cumul_pos = bank_cumul_pos
    prmt.unsold_auct_hold_cur_sum = unsold_cur_sum
    prmt.balance = balance
    prmt.reserve_sales = reserve_sales
    
#     bank_source.data = dict(x=bank_elements.index, y=bank_elements['bank_cumul'])
#     balance_source.data = dict(x=balance.index, y=balance.values)
#     reserve_source.data = dict(x=reserve_sales.index, y=reserve_sales.values)
    
    # run create_export_df within supply_demand_calculations, 
    # so that the values of sliders etc are those used in the model run (and not what might be adjusted after run)
    create_export_df()
    # modifies attributes prmt.export_df & prmt.js_download_of_csv
    
    # no return
# end of supply_demand_calculations


# In[ ]:


def create_emissions_pct_sliders():
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # simple
    # create slider widgets as attributes of objects defined earlier
    em_pct_CA_simp.slider = widgets.FloatSlider(value=-0.02, min=-0.07, max=0.03, step=0.005, 
                                                description="2017-2030", continuous_update=False, 
                                                readout_format='.1%'
                                               )

    em_pct_QC_simp.slider = widgets.FloatSlider(value=-0.02, min=-0.07, max=0.03, step=0.005, 
                                                description="2017-2030", continuous_update=False, 
                                                readout_format='.1%'
                                               )
    
    # ~~~~~~~~~~~~~~~~~~~~
    
    # advanced
    # create slider widgets as attributes of objects defined earlier
    em_pct_CA_adv1.slider = widgets.FloatSlider(value=-0.02, min=-0.07, max=0.03, step=0.005, 
                                                    description="2017-2020", continuous_update=False, 
                                                    readout_format='.1%')
    em_pct_CA_adv2.slider = widgets.FloatSlider(value=-0.02, min=-0.07, max=0.03, step=0.005, 
                                                    description="2021-2025", continuous_update=False, 
                                                    readout_format='.1%')
    em_pct_CA_adv3.slider = widgets.FloatSlider(value=-0.02, min=-0.07, max=0.03, step=0.005, 
                                                    description="2026-2030", continuous_update=False, 
                                                    readout_format='.1%')

    em_pct_QC_adv1.slider = widgets.FloatSlider(value=-0.02, min=-0.07, max=0.03, step=0.005, 
                                                    description="2017-2020", continuous_update=False, 
                                                    readout_format='.1%')
    em_pct_QC_adv2.slider = widgets.FloatSlider(value=-0.02, min=-0.07, max=0.03, step=0.005, 
                                                    description="2021-2025", continuous_update=False, 
                                                    readout_format='.1%')
    em_pct_QC_adv3.slider = widgets.FloatSlider(value=-0.02, min=-0.07, max=0.03, step=0.005, 
                                                    description="2026-2030", continuous_update=False, 
                                                    readout_format='.1%')
    # no return
# end of create_emissions_pct_sliders


# In[ ]:


def parse_emissions_text(text_input):
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # strip spaces from ends of text input:
    text_input = text_input.strip()
    
    if '\t' in text_input:
        # print("Probably from Excel")
        text_input = text_input.split(' ')
        text_input = [x.replace(',', '') for x in text_input] #  if ',' in x]
        text_input = [x.replace('\t', ', ') for x in text_input] #  if '\t' in x]


        df = pd.DataFrame([sub.split(', ') for sub in text_input])

        if df.columns[0] == 0:
            df.columns = ['year', 'emissions_ann']
        else:
            print("Error" + "! df didn't come out as expected")

        # in case year col was formatted with decimal places, remove them to get int
        df['year'] = df['year'].str.split('.').str[0]

        try:
            int(df.loc[0, 'year'])
            # print("OK!")
        except:
            df = df.drop(0)
            # print("dropped row")

        try:
            df['year'] = df['year'].astype(int)
            df = df.set_index('year')
            
            try:
                df['emissions_ann'] = df['emissions_ann'].astype(float)
                custom = df['emissions_ann']
            except:
                error_msg = "Error" + "! Custom auction may have formatting problem. Reverting to default of -2%/year."
                logging.info(error_msg)
                prmt.error_msg_post_refresh += [error_msg]
                custom = 'misformatted'
                
        except:
            error_msg = "Error" + "! Custom auction may have formatting problem. Reverting to default of -2%/year."
            logging.info(error_msg)
            prmt.error_msg_post_refresh += [error_msg]
            custom = 'misformatted'

        try:
            if custom.mean() > 1000 or custom.mean() < 50:
                error_msg = "Warning" + "! The emissions data might not have units of MMTCO2e."
                logging.info(error_msg)
                prmt.error_msg_post_refresh += [error_msg]
                # no change to custom
                
        except:
            print("Was not able to check whether data is realistic.")

    elif text_input == '':
        # will lead to error msg and revert to default inside fn emissions_projection
        error_msg = "Error" + "! Custom auction data was blank. Reverting to default of -2%/year."
        logging.info(error_msg)
        prmt.error_msg_post_refresh += [error_msg]
        custom = 'blank'
    
    else: # if '\t' not in text_input:
        error_msg = "Error" + "! Problem with custom data (possibly formatting problem). Reverting to default of -2%/year."
        logging.info(error_msg)
        prmt.error_msg_post_refresh += [error_msg]
        # no change to custom
        
        # override text_input value, for triggering default calculation in fn emissions_projection
        custom = 'missing_slash_t'
        
    return(custom)
# end of parse_emissions_text


# In[ ]:


def create_offsets_pct_sliders():
    """
    Default for CA & QC in period 2019-2020 is based on historical average calculated for 2013-2017.
    (See variable prmt.offset_rate_fract_of_limit.)
    
    Defaults for CA in 2021-2025 & 2026-2030 are based on ARB assumption in Post-2020 analysis.
    
    In advanced settings, Period 1: 2019-2020; Period 2: 2021-2025; Period 3: 2026-2030
    
    """
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # simple
    # create slider widget as attribute of object defined earlier
    off_pct_of_limit_CAQC.slider = widgets.FloatSlider(
        value=prmt.offset_rate_fract_of_limit, 
        min=0, max=1.0, step=0.01,
        description="2019-2030", continuous_update=False, readout_format='.0%')
    # use ARB assumption for all years 2019-2030, which fits with hist data
    # this default can be based on the values in advanced settings below, 
    # but then also depend on emissions projection, because it will be an average over the whole period 2019-2030

    # ~~~~~~~~~~~~~~~~~~~~
    
    # advanced
    # create slider widgets as attributes of objects defined earlier   
    off_pct_CA_adv1.slider = widgets.FloatSlider(
        value=0.08*prmt.offset_rate_fract_of_limit, # for period 1, based on historical data for WCI; limit is 8%
        min=0.0, max=0.10, step=0.005,
        description="2019-2020", readout_format='.1%', continuous_update=False)
    
    off_pct_CA_adv2.slider = widgets.FloatSlider(
        value=0.04*prmt.offset_rate_fract_of_limit, # CA limit in period 2 is 4%
        min=0.0, max=0.10, step=0.005, 
        description="2021-2025", readout_format='.1%', continuous_update=False)
    
    off_pct_CA_adv3.slider = widgets.FloatSlider(
        value=0.06*prmt.offset_rate_fract_of_limit, # CA limit in period 3 is 6%
        min=0.0, max=0.10, step=0.005, 
        description="2026-2030", readout_format='.1%', continuous_update=False)

    off_pct_QC_adv1.slider = widgets.FloatSlider(
        value=0.08*prmt.offset_rate_fract_of_limit, # for period 1, based on historical data for WCI; limit is 8%
        min=0.0, max=0.10, step=0.005, 
        description="2019-2020", readout_format='.1%', continuous_update=False)
    
    off_pct_QC_adv2.slider = widgets.FloatSlider(
        value=0.08*prmt.offset_rate_fract_of_limit, # QC limit in period 2 is 8%
        min=0.0, max=0.10, step=0.005, 
        description="2021-2025", readout_format='.1%', continuous_update=False)

    off_pct_QC_adv3.slider = widgets.FloatSlider(
        value=0.08*prmt.offset_rate_fract_of_limit, # QC limit in period 3 is 8%
        min=0.0, max=0.10, step=0.005, 
        description="2026-2030", readout_format='.1%', continuous_update=False)
    
    # no return
# end of create_offsets_pct_sliders


# In[ ]:


def create_figures():
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # ~~~~~~~~~~~~~~~~~~~~~
    
    # Figure 1. CA-QC emissions vs. instrument supplies & cap
    p1 = figure(title="emissions and instrument supplies (annual)",
                         height = 500, width = 600,
                         x_range=(2012.5, 2030.5),
                         y_range=(0, 500),
                         # toolbar_location="below",
                         # toolbar_sticky=False,
                        )

    p1.yaxis.axis_label = "MMTCO2e / year"
    p1.xaxis.major_label_standoff = 10
    p1.xaxis.minor_tick_line_color = None
    p1.yaxis.minor_tick_line_color = None
    p1.outline_line_color = "white"
    # p1.min_border_top = 10
    p1.min_border_right = 15
    p1.title.text_font_size = "16px"
    
    cap_CAQC = pd.concat([prmt.CA_cap, prmt.QC_cap], axis=1).sum(axis=1)
    cap_CAQC_line = p1.line(cap_CAQC.index, cap_CAQC, color='lightgrey', line_width=3.5)
    
    supply_last_hist_yr = 2017
    sup_off_CAQC_line_hist = p1.line(prmt.supply_ann.loc[:supply_last_hist_yr].index,
                                     prmt.supply_ann.loc[:supply_last_hist_yr], 
                                     color='mediumblue', line_width=3.5) 
    
    sup_off_CAQC_line_proj = p1.line(prmt.supply_ann.loc[supply_last_hist_yr:].index, 
                                     prmt.supply_ann.loc[supply_last_hist_yr:],
                                     color='dodgerblue', line_width=3.5, 
                                     # line_dash='dashed'
                                    ) 
    
    emissions_last_hist_yr = 2016
    em_CAQC_line_hist = p1.line(prmt.emissions_ann.loc[:emissions_last_hist_yr].index,
                                prmt.emissions_ann.loc[:emissions_last_hist_yr],
                                color='orangered', line_width=3.5)
    
    em_CAQC_line_proj = p1.line(prmt.emissions_ann.loc[emissions_last_hist_yr:].index, 
                                prmt.emissions_ann.loc[emissions_last_hist_yr:],
                                color='orange', line_width=3.5, 
                                # line_dash='dashed'
                               )
    
    legend = Legend(items=[('covered emissions (historical)', [em_CAQC_line_hist]),
                           ('covered emissions (projection)', [em_CAQC_line_proj]),
                           ('instrument supply* (historical)', [sup_off_CAQC_line_hist]),
                           ('instrument supply* (projection)', [sup_off_CAQC_line_proj]),
                           ('caps', [cap_CAQC_line]),
                           ('*supply shown here does not include reserve sales', [])
                          ],
                    label_text_font_size="14px",
                    location=(0, 0),
                    border_line_color=None)

    p1.add_layout(legend, 'below')

    em_CAQC_fig = p1
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Figure 2. CA-QC private bank and unsold current allowances (cumul.) + reserve sales

    # set y_max using balance_source, where balance is bank + unsold
    y_max = (int(prmt.balance.max() / 100) + 1) * 100

    if prmt.reserve_sales.max() == 0:
        y_min = 0
    else:
        # prmt.reserve_sales is always positive,
        # but reserve sales shown in graph are negative values, 
        # so need inverse of the max for this calculation of y_min
        y_min = (int(-1 * prmt.reserve_sales.max() / 100) - 1) * 100

    p2 = figure(title='private bank and unsold allowances (cumulative)',
                                   height = 600, width = 700,
                                   x_range=(2012.5, 2030.5),
                                   y_range=(y_min, y_max),
                                   # toolbar_location="below",
                                   # toolbar_sticky=False,
                                  )
    
    p2.xaxis.axis_label = "at end of each year"
    p2.xaxis.major_label_standoff = 10
    p2.xaxis.minor_tick_line_color = None
    
    p2.yaxis.axis_label = "MMTCO2e"   
    p2.yaxis.minor_tick_line_color = None
    
    p2.outline_line_color = "white"
    # p2.min_border_top = 10
    p2.min_border_right = 15
    p2.title.text_font_size = "16px"

    unsold_vbar = p2.vbar(prmt.balance.index,
                         top=prmt.balance,
                         width=1,
                         color=Viridis[6][4],
                         line_width=1, line_color='dimgray')
    
    bank_vbar = p2.vbar(prmt.bank_cumul_pos.index,
                        top=prmt.bank_cumul_pos,
                        width=1,
                        color=Viridis[6][3],
                        line_width=0.5, line_color='dimgray')

    reserve_vbar = p2.vbar(prmt.reserve_sales.index,
                           top=-1 * prmt.reserve_sales, # change to negative values
                           width=1,
                           color='tomato',
                           line_width=0.5, line_color='dimgray')
    
    # add vertical line for divider between full historical data vs. projection (partial or full)
    p2.line([emissions_last_hist_yr+0.5, emissions_last_hist_yr+0.5], 
            [y_min, y_max],
            line_color='black',         
            line_width=1, 
            line_dash='dashed')

    legend = Legend(items=[('private bank', [bank_vbar]),
                           ('unsold allowances', [unsold_vbar]),
                           ('reserve sales', [reserve_vbar])
                          ],
                    location=(0, 0),
                    label_text_font_size="14px",
                    border_line_color=None)

    p2.add_layout(legend, 'below')

    bank_CAQC_fig_bar = p2

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Figure 1 & Figure 2

    # note: for published paper, could add another plot next to em_CAQC_fig,
    # showing total unsold allowances (i.e., for 2016-2017, 141M)
    # and showing which were (ultimately) reintro & which were rolled over to APCR
    # see Github issue # 325

    prmt.Fig_1_2 = gridplot([em_CAQC_fig, bank_CAQC_fig_bar], ncols=2,
                            plot_width=450, plot_height=500,
                            toolbar_location="below", toolbar_options={'logo': None}
                           )
    
#     # configure so that no drag tools are active
#     prmt.Fig_1_2.toolbar.active_drag = None

#     # configure so that Bokeh chooses what (if any) scroll tool is active
#     prmt.Fig_1_2.toolbar.active_scroll = "auto"

#     # configure so that a specific PolySelect tap tool is active
#     prmt.Fig_1_2.toolbar.active_tap = poly_select

#     # configure so that a sequence of specific inspect tools are active
#     # note: this only works for inspect tools
#     prmt.Fig_1_2.toolbar.active_inspect = [hover_tool, crosshair_tool]
    
    # no returns; modifies object attributes
# end of create_figures


# In[ ]:


def supply_demand_button_on_click(b):
    
    logging.info("***********************************************")
    logging.info("start of new model run, with user settings")
    logging.info("***********************************************")
    
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    supply_demand_button.disabled = True
    supply_demand_button.style.button_color = '#A9A9A9'
    
    prmt.error_msg_post_refresh = [] # initialize
    
    if auction_tabs.selected_index == 0:
        # then no custom auction; default to all sell out
        
        # reinitialize prmt values for years_not_sold_out & fract_not_sold
        # (these are used in func supply_demand_calculations to determine whether to run new auctions)
        prmt.years_not_sold_out = ()
        prmt.fract_not_sold = float(0)
    
    elif auction_tabs.selected_index == 1:
        # then run custom auctions
        
        # set values in object prmt to be new values from user input
        # this sends the user settings to the model so they'll be used in processing auctions
        prmt.years_not_sold_out = years_not_sold_out_obj.wid.value
        prmt.fract_not_sold = fract_not_sold_obj.wid.value
        
        # set local variables to be prmt versions
        years_not_sold_out = prmt.years_not_sold_out
        fract_not_sold = prmt.fract_not_sold
        
        if years_not_sold_out != () and fract_not_sold > 0:
            # generate new data set auction_sales_pcts_all based on user settings & set object attribute
            # calculated using function get_auction_sales_pcts_all
            get_auction_sales_pcts_all()

            # process new auctions
            # (includes initialize_all_accts and creation of progress bars)
            all_accts_CA, all_accts_QC = process_auctions_CA_QC()
            
            # print("Finalizing results...") # for UI
            
        elif years_not_sold_out == ():
            # defaults to pre-run scenario in which all auctions sell out
            error_msg = "Warning" + "! No years selected for auctions with unsold allowances. Defaulted to scenario: all auctions sell out." # for UI
            logging.info(error_msg)
            prmt.error_msg_post_refresh += [error_msg]
            line_break = " "
            prmt.error_msg_post_refresh += [line_break]
            
            # reset prmt values for years_not_sold_out & fract_not_sold
            prmt.years_not_sold_out = ()
            prmt.fract_not_sold = float(0)
            
        elif fract_not_sold == 0.0:
            # defaults to pre-run scenario in which all auctions sell out
            error_msg = "Warning" + "! Auction percentage unsold was set to zero. Defaulted to scenario: all auctions sell out." # for UI
            logging.info(error_msg)
            prmt.error_msg_post_refresh += [error_msg]
            line_break = " "
            prmt.error_msg_post_refresh += [line_break]
            
            # reset prmt values for years_not_sold_out & fract_not_sold
            prmt.years_not_sold_out = ()
            prmt.fract_not_sold = float(0)
            
        else:
            # defaults to pre-run scenario in which all auctions sell out
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
    
    show(prmt.Fig_1_2)  
    
    # enable run button and change color
    supply_demand_button.style.button_color = 'PowderBlue'
    supply_demand_button.disabled = False

    # enable save button and change color
    save_csv_button.disabled = False
    save_csv_button.style.button_color = 'PowderBlue'
    
    # display buttons again
    display(widgets.HBox([supply_demand_button, save_csv_button]))
    
    if prmt.error_msg_post_refresh != []:
        for element in prmt.error_msg_post_refresh:
            print(element) # for UI
    
# end of supply_demand_button_on_click


# In[ ]:


def create_emissions_tabs():
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # create the widgets (as attributes of objects)
    create_emissions_pct_sliders()
    
    # ~~~~~~~~~~~~~~~~~~
    # arrange emissions sliders (simple) & ui

    # set captions
    em_simp_caption_col0 = widgets.Label(value="California")
    em_simp_caption_col1 = widgets.Label(value="Quebec")
    
    # create VBox with caption & slider
    em_simp_col0 = widgets.VBox([em_simp_caption_col0, em_pct_CA_simp.slider])
    em_simp_col1 = widgets.VBox([em_simp_caption_col1, em_pct_QC_simp.slider])

    # put each column into HBox
    emissions_simp_ui = widgets.HBox([em_simp_col0, em_simp_col1])
    
    # put whole set of captions + sliders into VBox with header
    em_simp_header = widgets.Label(value="Choose the annual percentage change for each jurisdiction, for the whole projection (2019-2030).")
    emissions_simp_ui_w_header = widgets.VBox([em_simp_header, emissions_simp_ui])
    
    # ~~~~~~~~~~~~~~~~~~~
    # arrange emissions sliders (advanced) & ui

    # set captions
    em_adv_caption_col0 = widgets.Label(value="California")
    em_adv_caption_col1 = widgets.Label(value="Quebec")

    # create VBox with caption & slider
    em_adv_col0 = widgets.VBox([em_adv_caption_col0, 
                                em_pct_CA_adv1.slider, 
                                em_pct_CA_adv2.slider, 
                                em_pct_CA_adv3.slider])
    em_adv_col1 = widgets.VBox([em_adv_caption_col1, 
                                em_pct_QC_adv1.slider, 
                                em_pct_QC_adv2.slider, 
                                em_pct_QC_adv3.slider])

    # put each column into HBox
    emissions_adv_ui = widgets.HBox([em_adv_col0, em_adv_col1])
    
    # put whole set of captions + sliders into VBox with header
    em_adv_header = widgets.Label(value="Choose the annual percentage change for each jurisdiction, for each of the specified time spans.")
    emissions_adv_ui_w_header = widgets.VBox([em_adv_header, emissions_adv_ui])

    # ~~~~~~~~~~~~~~~~~~~~
    # custom emissions input

#     emissions_text_CA = widgets.Text(
#         value='',
#         placeholder='Paste data here',
#         description='California:',
#         disabled=False
#     )
#     emissions_text_QC = widgets.Text(
#         value='',
#         placeholder='Paste data here',
#         description='Quebec:',
#         disabled=False
#     )
    em_text_input_CAQC_obj.wid = widgets.Text(
        value='',
        placeholder='Paste data here',
        # description='CA + QC:',
        disabled=False
    )

    # caption_CA_QC_indiv = widgets.Label(value="Enter data for California and Quebec separately")
    em_text_input_CAQC_cap = widgets.Label(value="Enter annual emissions data (sum of California and Quebec)")
    
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
    
    return(emissions_tabs)
    
# end of create_emissions_tabs


# In[ ]:


def create_auction_tabs():
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # create auction settings: simple
    
    # create widget, which is just a text label; the user has no options
    cap = "The default setting is that all auctions sell out.<br>To use this default assumption, leave this tab open."
    auction_simp_caption_col0 = widgets.HTML(value=cap)
    
    # TO DO: if we want to specify other pre-run scenarios besides all sell out,
    # then could use a RadioButton here to choose among the scenarios
    
    # put into ui
    auction_simp_ui = widgets.HBox([auction_simp_caption_col0])
    
    # ~~~~~~~~~~~~~~~~~~~
    # create auction settings: advanced
    year_list = list(range(2019, 2030+1))

    # create widgets for "years not sold out" and "% not sold" (as attributes of objects)
    years_not_sold_out_obj.wid = widgets.SelectMultiple(
        options=year_list,
        value=[],
        rows=len(year_list),
        description='years',
        disabled=False)
    
    fract_not_sold_obj.wid = widgets.FloatSlider(min=0.0, max=1.0, step=0.05,
                                                 description="% unsold", continuous_update=False, 
                                                 readout_format='.0%')
    
    # put widgets in boxes for ui & create final ui
    years_pct_HBox = widgets.HBox([years_not_sold_out_obj.wid, fract_not_sold_obj.wid])
    auction_adv_ui = widgets.VBox([years_pct_HBox])

    auction_adv_ui_header_text = "Choose particular years in which auctions would have a portion of allowances go unsold.<br>To select multiple years, hold down 'ctrl' (Windows) or 'command' (Mac), or to select a range of years, hold down Shift and click the start and end of the range.<br>Then choose the percentage of allowances that go unsold in the auctions (both current and advance) in the years selected."
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
    
    return(auction_tabs)
# end of create_auction_tabs


# In[ ]:


def create_offsets_tabs():
    logging.info(f"{inspect.currentframe().f_code.co_name} (start)")
    
    # create the sliders (as attributes of objects)
    create_offsets_pct_sliders()
    
    # ~~~~~~~~~~~~~~~~~~~
    # create emissions sliders (simple) & ui
    # uses slider: off_pct_of_limit_CAQC.slider
    off_simp_header = widgets.Label(value="Choose the offset supply, as a percentage of the limit that can be used.")
    off_simp_caption = widgets.Label(value="California & Quebec")
    off_simp_footer = widgets.Label(value="For California, the limits for each time period are 8% (2018-2020), 4% (2021-2025), and 6% (2026-2030). For Quebec, the limit is 8% for all years.")
    off_simp_ui_w_header = widgets.VBox([off_simp_header, 
                                         off_simp_caption, 
                                         off_pct_of_limit_CAQC.slider, 
                                         off_simp_footer])

    # ~~~~~~~~~~~~~~~~~~~
    # create emissions sliders (advanced) & ui

    off_adv_header = widgets.Label(value="Choose the offset supply as a percentage of covered emissions, for each jurisdiction, for each time span.")

    off_adv_caption_col0 = widgets.Label(value="California")
    off_adv_caption_col1 = widgets.Label(value="Quebec")
    off_adv_footer1 = widgets.Label(value="For California, the limits for each time period are 8% (2018-2020), 6% (2021-2025), and 4% (2026-2030). For Quebec, the limit is 8% for all years.")
    off_adv_footer2 = widgets.Label(value="Warning: The sliders above may allow you to set offsets supply higher than the quantity that could be used through 2030.")
    off_adv_col0 = widgets.VBox([off_adv_caption_col0, 
                                off_pct_CA_adv1.slider, 
                                off_pct_CA_adv2.slider, 
                                off_pct_CA_adv3.slider])
    
    off_adv_col1 = widgets.VBox([off_adv_caption_col1, 
                                off_pct_QC_adv1.slider, 
                                off_pct_QC_adv2.slider, 
                                off_pct_QC_adv3.slider])

    off_adv_ui = widgets.HBox([off_adv_col0, off_adv_col1])
    off_adv_ui_w_header = widgets.VBox([off_adv_header, off_adv_ui, off_adv_footer1, off_adv_footer2])

    # ~~~~~~~~~~~~~~~~~~~~
    
    children = [off_simp_ui_w_header, 
                off_adv_ui_w_header]

    tab = widgets.Tab()
    tab.children = children
    tab.set_title(0, 'simple')
    tab.set_title(1, 'advanced')
    
    offsets_tabs = tab
    
    return(offsets_tabs) 
# end of create_offsets_tabs


# In[ ]:


def create_export_df():
    
    # metadata for figure_for_export
    descrip_list = [f'WCI cap-and-trade model version {prmt.model_version}'] # initialize with model version number
    metadata_list = [f'https://github.com/nearzero/WCI-cap-and-trade/tree/v{prmt.model_version}'] # initialize with model version number
    metadata_list_of_tuples = [] # initialize

    if emissions_tabs.selected_index == 0:        
        # user choice: simple emissions
        descrip_list += [
            'emissions annual % change CA, 2017-2030', # 'em_pct_CA_simp',
            'emissions annual % change QC, 2017-2030'# 'em_pct_QC_simp',
        ]
        metadata_list += [str(100*em_pct_CA_simp.slider.value)+'%', 
                          str(100*em_pct_QC_simp.slider.value)+'%']

    elif emissions_tabs.selected_index == 1:
        # user choice: advanced emissions
        descrip_list += [
            'emissions annual % change CA, 2017-2020', # 'em_pct_CA_adv1.slider.value',
            'emissions annual % change CA, 2021-2025', # 'em_pct_CA_adv2.slider.value', 
            'emissions annual % change CA, 2026-2030', # 'em_pct_CA_adv3.slider.value', 
            'emissions annual % change QC, 2017-2020', # 'em_pct_QC_adv1.slider.value',
            'emissions annual % change QC, 2021-2025', # 'em_pct_QC_adv2.slider.value', 
            'emissions annual % change QC, 2026-2030', # 'em_pct_QC_adv3.slider.value', 
        ]
        metadata_list += [str(100*em_pct_CA_adv1.slider.value)+'%', 
                          str(100*em_pct_CA_adv2.slider.value)+'%', 
                          str(100*em_pct_CA_adv3.slider.value)+'%', 
                          str(100*em_pct_QC_adv1.slider.value)+'%', 
                          str(100*em_pct_QC_adv2.slider.value)+'%', 
                          str(100*em_pct_QC_adv3.slider.value)+'%']

    elif emissions_tabs.selected_index == 2:
        # user choice: custom emissions
        descrip_list += ['custom emissions']
        metadata_list += ['see values at left']

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    if auction_tabs.selected_index == 0:
        # user choice: simple auction (all sell out)
        descrip_list += ['simple auction']
        metadata_list += ['all sell out']

    elif auction_tabs.selected_index == 1:
        descrip_list += [
            'auctions: years that did not sell out', # 'years_not_sold_out_obj', 
            'auctions: % unsold', # 'fract_not_sold_obj'
        ]
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
        descrip_list += [
            'offset supply as % of emissions, CA, 2017-2020', # 'off_pct_CA_adv1.slider.value',
            'offset supply as % of emissions, CA, 2021-2025', # 'off_pct_CA_adv2.slider.value', 
            'offset supply as % of emissions, CA, 2026-2030', # 'off_pct_CA_adv3.slider.value', 
            'offset supply as % of emissions, QC, 2017-2020', # 'off_pct_QC_adv1.slider.value',
            'offset supply as % of emissions, QC, 2021-2025', # 'off_pct_QC_adv2.slider.value', 
            'offset supply as % of emissions, QC, 2026-2030', # 'off_pct_QC_adv3.slider.value', 
        ]
        metadata_list += [
            str(100*off_pct_CA_adv1.slider.value)+'%', 
            str(100*off_pct_CA_adv2.slider.value)+'%', 
            str(100*off_pct_CA_adv3.slider.value)+'%', 
            str(100*off_pct_QC_adv1.slider.value)+'%', 
            str(100*off_pct_QC_adv2.slider.value)+'%', 
            str(100*off_pct_QC_adv3.slider.value)+'%',
        ]

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # compile metadata_list_of_tuples
    for element_num in range(len(metadata_list)):
        metadata_list_of_tuples += [(descrip_list[element_num], metadata_list[element_num])]

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # add warning about excess offsets (if any)
    if prmt.excess_offsets > 0:
        metadata_list_of_tuples += [
            ("scenario has excess offsets at end of 2030:", 
             f"{int(round(prmt.excess_offsets, 0))} MMTCO2e")
        ]
    else:
        pass
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # add warning about reverting to default auctions
    
    for element_num in range(len(prmt.error_msg_post_refresh)):
        if 'No years selected for auctions with unsold allowances' in prmt.error_msg_post_refresh[element_num]:
            metadata_list_of_tuples += [
                ("Warning"+ "! No years selected for auctions with unsold allowances", 
                 "Defaulted to scenario: all auctions sell out")
            ]
        else:
            pass
        
        if 'Auction percentage unsold was set to zero' in prmt.error_msg_post_refresh[element_num]:
            metadata_list_of_tuples += [
                ("Warning" + "! Auction percentage unsold was set to zero", 
                 "Defaulted to scenario: all auctions sell out")
            ]
        else:
            pass
             
    metadata_df = pd.DataFrame(metadata_list_of_tuples, columns=['setting descriptions', 'setting values'])
    
    # shift index to align with data
    metadata_df.index = metadata_df.index + 2013
    
    emissions_export = prmt.emissions_ann.copy()
    emissions_export.name = 'CA-QC covered emissions [MMTCO2e/year]'
    
    supply_export = prmt.supply_ann.copy()
    supply_export.name = 'instrument supply additions (excluding reserve sales) [MMTCO2e/year]'
    
    bank_export = prmt.bank_cumul_pos.copy()
    bank_export.name = 'banked instruments (cumulative, at end of year) [MMTCO2e]'
    
    unsold_export = prmt.unsold_auct_hold_cur_sum.copy()
    unsold_export.name = 'unsold allowances of current vintage or earlier (remaining at end of year) [MMTCO2e]'
    
    reserve_export = prmt.reserve_sales.copy()
    reserve_export.name = 'reserve sales (cumulative, at end of year) [MMTCO2e]'
    
    export_df = pd.concat([emissions_export, 
                           supply_export,
                           bank_export,
                           unsold_export,
                           reserve_export,
                           metadata_df], 
                          axis=1)
    export_df.index.name = 'year'
    
    # set attribute
    prmt.export_df = export_df
    
    save_timestamp = time.strftime('%Y-%m-%d_%H%M%S', time.localtime())
    
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
           f'Near_Zero_WCI_cap_and_trade_model_results_{save_timestamp}.csv')

# end of create_export_df


# In[ ]:


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


if __name__ == '__main__': 
    # show figure_explainer_accord above figure
    display(figure_explainer_accord)


# In[ ]:


# create tabs for emissions, auction, offsets

emissions_tabs = create_emissions_tabs()
auction_tabs = create_auction_tabs()
offsets_tabs = create_offsets_tabs()

# prepare data for default graph
supply_demand_calculations()

# create supply-demand button (but don't show it until display step below)
supply_demand_button = widgets.Button(description="Run supply-demand calculations", 
                                      layout=widgets.Layout(width="250px"))

supply_demand_button.style.button_color = 'PowderBlue'

# ~~~~~~~~~~
em_explainer_html = widgets.HTML(
    value=em_explainer_text,
    # placeholder='Some HTML',
    # description='',
)

em_explainer_accord = widgets.Accordion(
    children=[em_explainer_html], 
    layout=widgets.Layout(width="650px")
)
em_explainer_accord.set_title(0, 'About covered emissions')
em_explainer_accord.selected_index = None

emissions_tabs_explainer = widgets.VBox([emissions_tabs, em_explainer_accord])

emissions_title = widgets.HTML(value="<h4>demand projection: covered emissions</h4>")

emissions_tabs_explainer_title = widgets.VBox([emissions_title, emissions_tabs_explainer])

# ~~~~~~~~~~

auct_explain_html = widgets.HTML(
    value=auction_explainer_text,
    # placeholder='Some HTML',
    # description='',
)

auct_explain_accord = widgets.Accordion(
    children=[auct_explain_html], 
    layout=widgets.Layout(width="650px")
)
auct_explain_accord.set_title(0, 'About allowance auctions')
auct_explain_accord.selected_index = None

auction_tabs_explainer = widgets.VBox([auction_tabs, auct_explain_accord])

auction_title = widgets.HTML(value="<h4>supply projection: allowances auctioned</h4>")

auction_tabs_explainer_title = widgets.VBox([auction_title, auction_tabs_explainer])

# ~~~~~~~~~~
offsets_explainer_html = widgets.HTML(
    value=offsets_explainer_text,
    # placeholder='Some HTML',
    # description='',
)

offsets_explainer_accord = widgets.Accordion(
    children=[offsets_explainer_html],
    layout=widgets.Layout(width="650px")
)
offsets_explainer_accord.set_title(0, 'About carbon offsets')
offsets_explainer_accord.selected_index = None

offsets_tabs_explainer = widgets.VBox([offsets_tabs, offsets_explainer_accord])

offsets_title = widgets.HTML(value="<h4>supply projection: offsets</h4>")

offsets_tabs_explainer_title = widgets.VBox([offsets_title, offsets_tabs_explainer])


# #### create figures & display them

# In[ ]:


# create two-panel figure
create_figures()

# when supply-demand button clicked, perform action
supply_demand_button.on_click(supply_demand_button_on_click)


# #### prepare for exports

# In[ ]:


# create button to save csv

# starts enabled; becomes disabled after file saved; becomes re-enabled after a new model run
save_csv_button = widgets.Button(description="Save results & settings (csv)", 
                                 disabled = False,
                                 layout=widgets.Layout(width="250px"),
                                 )
save_csv_button.style.button_color = 'PowderBlue' # '#A9A9A9'

# ~~~~~~~~~~~~~~
# define action on click
def save_csv_on_click(b):
    save_csv_button.style.button_color = '#A9A9A9'
    save_csv_button.disabled = True

    display(Javascript(prmt.js_download_of_csv))
# end of save_csv_on_click

# ~~~~~~~~~~~~~~
save_csv_button.on_click(save_csv_on_click)


# In[ ]:


if __name__ == '__main__':    
    show(prmt.Fig_1_2)
    
    # show supply-demand button & save csv button
    display(widgets.HBox([supply_demand_button, save_csv_button]))


# In[ ]:


if __name__ == '__main__':
    # display each of the three tab sets (emissions, auctions, offsets)
    display(emissions_tabs_explainer_title)
    display(auction_tabs_explainer_title)
    display(offsets_tabs_explainer_title)


# #### export snaps_end_all

# In[ ]:


# if __name__ == '__main__':
#     save_timestamp = time.strftime('%Y-%m-%d_%H%M', time.localtime())

#     if prmt.run_hindcast == True:    
        
#         # collect the snaps
#         df = pd.concat(scenario_CA.snaps_end + scenario_QC.snaps_end, axis=0, sort=False)
#         snaps_end_all_CA_QC = df
        
#         if prmt.years_not_sold_out == () and prmt.fract_not_sold == 0:
#             # export as "all sell out (hindcast)"
#             snaps_end_all_CA_QC.to_csv(os.getcwd() + '/' + f"snaps_end_all_CA_QC all sell out (hindcast) {save_timestamp}.csv")
        
#         else: 
#             # export as "some unsold (hindcast)"
#             snaps_end_all_CA_QC.to_csv(os.getcwd() + '/' + f"snaps_end_all_CA_QC some unsold (hindcast) {save_timestamp}.csv")

#     else: # prmt.run_hindcast == False
#         try:
#             # collect the snaps, select only Q4
#             df = pd.concat(scenario_CA.snaps_end + scenario_QC.snaps_end, axis=0, sort=False)
#             snaps_end_all_CA_QC = df.loc[df['snap_q'].dt.quarter==4].copy()
            
#             if prmt.years_not_sold_out == () and prmt.fract_not_sold == 0:
#                 # export as "all sell out (not hindcast)"
#                 snaps_end_all_CA_QC.to_csv(os.getcwd() + '/' + f"snaps_end_all_CA_QC all sell out (not hindcast) {save_timestamp}.csv")
#             else:
#                 # export as "some unsold (not hindcast)
#                 snaps_end_all_CA_QC.to_csv(os.getcwd() + '/' + f"snaps_end_all_CA_QC some unsold (not hindcast) {save_timestamp}.csv")
#         except:
#             # no results; initial run using defaults, so snaps are empty
#             # export would just be the same as prmt.snaps_end_Q4
#             pass


# #### export snaps_end_Q4

# In[ ]:


if __name__ == '__main__':
    save_timestamp = time.strftime('%Y-%m-%d_%H%M', time.localtime())

    if prmt.run_hindcast == True:    
        
        # collect the snaps, select only Q4
        df = pd.concat(scenario_CA.snaps_end + scenario_QC.snaps_end, axis=0, sort=False)
        snaps_end_Q4_CA_QC = df.loc[df['snap_q'].dt.quarter==4].copy()

        if prmt.years_not_sold_out == () and prmt.fract_not_sold == 0:
            # export as "all sell out (hindcast)"
            snaps_end_Q4_CA_QC.to_csv(os.getcwd() + '/' + f"snaps_end_Q4_CA_QC all sell out (hindcast) {save_timestamp}.csv")
        
        else: 
            # export as "some unsold (hindcast)"
            snaps_end_Q4_CA_QC.to_csv(os.getcwd() + '/' + f"snaps_end_Q4_CA_QC some unsold (hindcast) {save_timestamp}.csv")

    else: # prmt.run_hindcast == False
        try:
            # collect the snaps, select only Q4
            df = pd.concat(scenario_CA.snaps_end + scenario_QC.snaps_end, axis=0, sort=False)
            snaps_end_Q4_CA_QC = df.loc[df['snap_q'].dt.quarter==4].copy()
            
            if prmt.years_not_sold_out == () and prmt.fract_not_sold == 0:
                # export as "all sell out (not hindcast)"
                snaps_end_Q4_CA_QC.to_csv(os.getcwd() + '/' + f"snaps_end_Q4_CA_QC all sell out (not hindcast) {save_timestamp}.csv")
            else:
                # export as "some unsold (not hindcast)
                snaps_end_Q4_CA_QC.to_csv(os.getcwd() + '/' + f"snaps_end_Q4_CA_QC some unsold (not hindcast) {save_timestamp}.csv")
        except:
            # no results; initial run using defaults, so snaps are empty
            # export would just be the same as prmt.snaps_end_Q4
            pass


# In[ ]:


# if __name__ == '__main__':
#     save_timestamp = time.strftime('%Y-%m-%d_%H%M', time.localtime())
    
#     avail_accum_all = pd.concat([scenario_CA.avail_accum, scenario_QC.avail_accum], axis=0, sort=False)
    
#     avail_accum_all.to_csv(os.getcwd() + '/' + f"avail_accum_all all sell out {save_timestamp}.csv")


# # END OF MODEL
