# -*- coding: utf-8 -*-
"""
Created on Tue Mar  1 14:59:24 2016

@author: gazkune
"""


"""
This tool is to transform datasets generated by synthetic_data_generator.py 
format to CASAS AL format
timestamp, sensorID, Activity, start/end -> timestamp sensorLocation sensorID Activity
"""

import sys, getopt
import numpy as np
import time, datetime
import pandas as pd
import json, csv

"""
Function to parse arguments from command line
Input:
    argv -> command line arguments
Output:
    inputfile -> file where synthetic data generation is defined (special format)
    outputfile -> file to write the generated data (csv format)   
"""

def parseArgs(argv):
   inputfile = ''
   bfile = ''
   tfile = ''
   contextfile = ''
   try:
      opts, args = getopt.getopt(argv,"hi:c:b:t:",["ifile=","cfile=", "bfile=", "tfile="])
   except getopt.GetoptError:
      print 'dataset-transformer.py -i <inputfile> -c <contextfile> -b <baseoutputfile> -t <testoutputfile>'
      sys.exit(2)
   for opt, arg in opts:
      if opt == '-h':
         print 'dataset-transformer.py -i <inputfile> -c <contextfile> -b <baseoutputfile> -t <testoutputfile>'
         sys.exit()
      elif opt in ("-i", "--ifile"):
         inputfile = arg
      elif opt in ("-c", "--cfile"):
         contextfile = arg
      elif opt in ("-b", "--bfile"):
         bfile = arg
      elif opt in ("-t", "--tfile"):
         tfile = arg
   
   return inputfile, contextfile, bfile, tfile

"""
Function to parse context_file, a json file where activities, sensors and objects
are described in terms of type and location
Input:
    context_file -> file where activities, objects and sensors are described (json format)
Output:
    activities -> dict of activities with their properties
    objects -> dict with objects with their properties
    sensors -> dict with sensors with their properties
"""

def parseDescription(context_file):
    description = json.loads(open(context_file).read())
    
    activities = description['activities']
    objects = description['objects']
    sensors = description['sensors']
    
    return activities, objects, sensors

"""
Function to transform the dataset to CASAS AL format using pandas.DataFrame
Input:
    input_df: pd.DataFrame in synthetic_data_generator format
    contextfile_name: the file name for the context knowledge file (activities, objects, sensors)
Output:
    base_df: pd.DataFrame in CASAS format [timestamp, location, sensorID, ON, Activity] with real Activity tags
    test_df: pd.DataFrame in CASAS format [timestamp, location, sensorID, ON, Activity] with 'Other_Activity' tags for testing purposes
"""
def transformDataset(input_df, contextfile_name):
    # copy input_df    
    base_df = input_df.copy(deep=True)
        
    # Remove the last column [start_end]
    base_df = base_df.drop('start_end', 1)
        
    # Insert new column with 'ON' values after 'sensor' column -> idx = 1
    values = ['ON']*len(base_df.index)
    base_df.insert(1, 'state', values)
        
    # Use context file to insert sensor locations in the first column -> idx = 0
    locations = []
    # TODO: uncomment for context model processig
    #activities, objects, sensors = parseDescription(contextfile_name)
    for i in base_df.index:
        sensor = base_df['sensor'][i]
        # TODO: uncomment for context model and location processing
        #location = objects[sensors[sensor]['attached-to']]['location']        
        #locations.append(location)
    
    # Testing different positions for locations with AL tool
    #base_df.insert(0, 'location', locations)
    #base_df.insert(1, 'location', locations)
    base_df.insert(0, 'sensor2', base_df['sensor'].tolist())
    
    #print base_df.head(50)
    
    # base_df is generated; now copy to test_df and change 'activity' column
    test_df = base_df.copy(deep=True)
    test_df['activity'] = ['Other_Activity']*len(test_df)
    
    #print '---------------------------'
    #print test_df.head(50)
    
    return base_df, test_df

"""
Main function
"""

def main(argv):
    # call the argument parser 
   [inputfile_name, contextfile_name, bfile_name, tfile_name] = parseArgs(argv[1:])
   print 'Provided arguments:'       
   print inputfile_name
   print contextfile_name
   print bfile_name
   print tfile_name
   
   # Read the annotated_file and build a DataFrame 
   input_df = pd.read_csv(inputfile_name, parse_dates=True, index_col=0)
   
   [base_df, test_df] = transformDataset(input_df, contextfile_name)

   # Write results to provided CSV files, using blank spaces as separators
   # First fo all separate index timestamp into two columns
   dates = []
   times = []
   for i in xrange(len(base_df)):
       aux = str(base_df.index[i])
       [date, timed] = aux.split(' ')
       dates.append(date)
       times.append(timed)
       
       
   #print dates
   #print times
   base_df.insert(0, 'time', times)
   base_df.insert(0, 'date', dates)
   base_df.to_csv(bfile_name, sep=' ', index=None, header=None)
   
   test_df.insert(0, 'time', times)
   test_df.insert(0, 'date', dates)
   test_df.to_csv(tfile_name, sep=' ', index=None, header=None)
   

if __name__ == "__main__":
   main(sys.argv)