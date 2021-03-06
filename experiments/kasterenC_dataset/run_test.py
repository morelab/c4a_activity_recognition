# -*- coding: utf-8 -*-
"""
Created on Tue Feb 11 15:32:42 2014

@author: gazkune
"""

import sys, time
sys.path.append('../..')

from pattern_model_matching.PatternModelMatching import main as pm_main
from ar_evaluator.AREvaluator import main as ar_main




def main(argv):
    # Pattern Model Matching arguments
    eamsfile = "eams.json"
    patternsfile = "test_kasterenC.csv.annotated"
    adlogfile = "kasterenC_log.txt"
    contextmodelfile = "context_model.json"
    pmoutputfile = "pm_output.csv"
    
    # AR Evaluator arguments
    groundtruth = "kasterenC_groundtruth.csv"
    evaluable = "pm_output.csv"
    
    # Call PatternModelMatching
    arguments = ['PatternModelMatching.py', '-e', eamsfile, '-a', patternsfile, '-l', adlogfile, '-c', contextmodelfile, '-o', pmoutputfile]
    pm_main(arguments)
    time.sleep(1)       
                   
    # Call AR Evaluator
    arguments = ['AREvaluator.py', '-g', groundtruth, '-e', evaluable]
    ar_main(arguments)
       
if __name__ == "__main__":
   main(sys.argv)
