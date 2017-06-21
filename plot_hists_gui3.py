# -*- coding: utf-8 -*-
"""
Created on Wed Mar 08 17:27:01 2017

@author: DJ Pleshinger
"""

import numpy as np
from datetime import date
from datetime import timedelta

def get_bins(c, min_bin):
    """find bins with at least the min count over the threshold
    make sure less than 600 for noise spikes
    """
    
    b2a=np.where(c > min_bin)
    b2b=np.where(c < 500)  #elsiminates periodic noise trigger ~900
    b2c=np.intersect1d(b2a, b2b)   
    return b2c

def get_nearest(array, value):
    idx = (np.abs(array - value)).argmin()
    return idx

def fix_num(n):    
    """convert integer to string, add 0 if single digit"""
    
    if n < 10: n_s = '0' + str(n)
    else:
        n_s = str(n)
    return n_s

def ints_to_date(d, m, y):    
    """from integers for day month and year return date string,
    format yyyy_mm_dd
    """
    
    m_s = fix_num(m)
    d_s = fix_num(d)
    y_s = str(y)
    date_s = y_s + '_' + m_s + '_' + d_s   
    return date_s
    
##############################################################################
##############################################################################        
##############################################################################
##############################################################################        
##############################################################################        

def rates(box_num, start_date, end_date = None, threshold = None, path0 = None):
    """search bgo data for candidate events above user defined threshold""" 
    
    if not end_date:
        end_date = start_date
    
    start_d = int(start_date[8:10])
    start_m = int(start_date[5:7])
    start_y = int(start_date[0:4]) 
    start_day = date(start_y, start_m, start_d)
    
    end_d = int(end_date[8:10])
    end_m = int(end_date[5:7])
    end_y = int(end_date[0:4])
    end_day = date(end_y, end_m, end_d)
        
    data_2ms = []
    data_20us = []
    trig_info = []
        
    loop_day = start_day
    while loop_day < end_day + timedelta(1):
        
        date_str = ints_to_date(loop_day.day, loop_day.month, loop_day.year)
        
        folder = date_str[5:7] + '_' + date_str[0:4] + '/'
        if not path0: 
            path = 'D:/rates/' + box_num + '/' + folder
        else:
            path = path0 + box_num + '/' + folder
        dev1_file =  path + 'dev1_' + date_str[8:] + '.npy'
        dev2_file =  path + 'dev2_' + date_str[8:] + '.npy'
        hist_file = path + 'hist_' + date_str[8:] + '.npy'
        
        '''check that file exists'''
        try:
            hist_data = np.load(hist_file)
        except:
            pass
        '''check for data'''
        
        ave = np.sum(hist_data, axis=0)[1]/43200000
        std = np.sqrt((np.sum((hist_data-ave)**2, axis = 0)[1] + (43200000 - len(hist_data))*ave**2)/(43200000-1))
        
        min_bin = np.ceil(std*threshold + ave)
        
        bgo_triggers = get_bins(hist_data[:,1], min_bin)
        
        if len(bgo_triggers) > 0:
            for trig in bgo_triggers:
                temp = []
                trig_ts = hist_data[:,0][trig]
                xmin_bin = trig_ts - 0.5
                xmax_bin = trig_ts + 0.5
                xmi = get_nearest(hist_data[:,0], xmin_bin)
                xma = get_nearest(hist_data[:,0], xmax_bin)
                temp = [hist_data[:,1][xmi:xma],hist_data[:,0][xmi:xma]]
                data_2ms.append(temp)
                
                temp=[]
                xmin_bin = trig_ts - 5*.002
                xmax_bin = trig_ts + 6*.002
                xmi = get_nearest(hist_data[:,0], xmin_bin)
                xma = get_nearest(hist_data[:,0], xmax_bin)
                
                dev1_data = np.load(dev1_file)
                dev2_data = np.load(dev2_file)
                total_data = dev1_data[0] + dev1_data[1] + dev1_data[2] + dev2_data[0] + dev2_data[1] + dev2_data[2]
                for line in total_data:
                    if line < hist_data[:,0][xma] and line > hist_data[:,0][xmi]:
                        temp.append(line)
                bins_needed = np.ceil((xma - xmi) * .002 / .00002)
                bins_focus = np.linspace(hist_data[:,0][xmi], hist_data[:,0][xma],
                                         bins_needed + 1, dtype=np.float64)
                bgo_focus, bins_focus = np.histogram(temp, bins=bins_focus)
                data_20us.append([bgo_focus, bins_focus[:-1]])
                
                trig_info.append([ave, min_bin, date_str])
                
        loop_day = loop_day + timedelta(1)
        
    return data_2ms, data_20us, trig_info
