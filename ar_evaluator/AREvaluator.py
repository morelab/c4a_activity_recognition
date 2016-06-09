# -*- coding: utf-8 -*-
"""
This class evaluates the results of the activity recognition process. It
calculates both the confusion matrix and the precision, recall and F1 metrics.

In the case of the metrics it calculates the three types of averages: micro, 
macro and weighted. As this is a multiclass classification problem use either 
macro or weighted values, dependign if the dataset is balanced or unbalanced.
"""
import ast
import getopt
import itertools
import json
import sys

import numpy as np
import pandas as pd
from sklearn import metrics

from ConfusionMatrix import ConfusionMatrix

class AREvaluator:
    
    def __init__(self, groundtruth, evaluable):        
        self.groundtruth = pd.read_csv(groundtruth, parse_dates=[[0, 1]], header=None, index_col=0, sep=' ')
        self.groundtruth.columns = ['sensor', 'action', 'event', 'activity']
        self.groundtruth.index.names = ["timestamp"]
        
        self.evaluable = pd.read_csv(evaluable, parse_dates=True, index_col=0, converters={'detected_activities': ast.literal_eval})

        # List of activities in the groundtruth dataset        
        self.activities = self.groundtruth.activity.unique()
        #self.activities = ['MakeChocolate', 'MakeCoffee', 'BrushTeeth', 'WashHands', 'MakePasta', 'ReadBook', 'None', 'WatchTelevision']
        # Initialize the confusion matrix
        self.cm = ConfusionMatrix(self.activities)
        
        
    # First evaluation method. 
    # The idea is to take the patterns in evaluable, take the start and end time of the pattern
    # and look at the same time section of the groundtruth file. Extract the activities of the groundtruth
    # for that section and compare with the activities of evaluable. The objetive is to create a confusion
    # matrix.    
    def evaluate1(self):
        # Initialize start and prev_pat
        start = self.evaluable.index[0]
        prev_pat = self.evaluable.loc[start, 'pattern']
        print 'First pattern:', prev_pat
        # iterate through evaluable        
        for i in xrange(1, len(self.evaluable)):
            ts = self.evaluable.index[i]
            pat = self.evaluable.loc[ts, 'pattern']
            if pat != prev_pat:
                end = self.evaluable.index[i-1]
                # At this point, start and end have the right values for a discovered pattern                
                gt_activities = self.extractGroundTruthActivities(start, end)
                ev_activities = self.evaluable.loc[end, 'detected_activities']
                print "Pattern:", prev_pat, "(", start, ",", end, ")"
                print "   GT:", gt_activities
                print "   EV:", ev_activities
                self.updateConfusionMatrix(gt_activities, ev_activities)
                # Now update prev_pat and start
                prev_pat = pat
                start = ts
            
        
    # Method to return the activities that appear in the groundtruth for the section defined
    # by start and end, which are timestamps
    def extractGroundTruthActivities(self, start, end):
        #print '   extractGTActivities: start', start, ', end', end        
        return list(self.groundtruth.loc[start:end, 'activity'].unique())
         
    
    # Method to update the confusion matrix given the groundtruth activities
    # and detected activities of a given section of time
    def updateConfusionMatrix(self, gt_activities, ev_activities):
        # Treat None activities in groundtruth which appear with other activities
        if len(gt_activities) > 1:
            try:
                i = gt_activities.index('None')
                gt_activities.pop(i)
            except ValueError:
                None
                
        # Now we can compare both lists
        hits = np.intersect1d(np.array(gt_activities), np.array(ev_activities))
        hits = hits.tolist()
        for i in xrange(len(hits)):
            self.cm.update(hits[i], hits[i])
            
        for i in xrange(len(hits)):
            gt_activities.remove(hits[i])
            ev_activities.remove(hits[i])
            
        
        while len(gt_activities) > 0 or len(ev_activities) > 0:
            if len(gt_activities) == 0:
                self.cm.update(ev_activities[0], 'None')
                ev_activities.remove(ev_activities[0])
            elif len(ev_activities) == 0:
                self.cm.update('None', gt_activities[0])
                gt_activities.remove(gt_activities[0])
            else:
                print '??', ev_activities[0]
                self.cm.update(ev_activities[0], gt_activities[0])
                gt_activities.remove(gt_activities[0])
                ev_activities.remove(ev_activities[0])
                
    def calculate_evaluation_metrics(self, y_ground_truth, y_predicted):
        """Calculates the evaluation metrics (precision, recall and F1) for the
        predicted examples. It calculates the micro, macro and weighted values
        of each metric.
        
        Usage example:
            y_ground_truth = ['make_coffe', 'brush_teeth', 'wash_hands']
            y_predicted = ['make_pasta', 'none', 'none']
            metrics = calculate_evaluation_metrics (y_ground_truth, y_predicted)
    
        Parameters
        ----------
        y_ground_truth : list
            Classes that appear in the ground truth.
    
        y_predicted: list
            Predicted classes. Take into account that the must follow the same
            order as in y_ground_truth
       
        Returns
        -------
        metric_results : dict
            Dictionary with the values for the metrics (precision, recall and 
            f1)    
        """
        
        metric_types =  ['micro', 'macro', 'weighted']
        metric_results = {
            'precision' : {},
            'recall' : {},
            'f1' : {}        
        }
        
        for t in metric_types:
            metric_results['precision'][t] = metrics.precision_score(y_ground_truth, y_predicted, average = t)
            metric_results['recall'][t] = metrics.recall_score(y_ground_truth, y_predicted, average = t)
            metric_results['f1'][t] = metrics.f1_score(y_ground_truth, y_predicted, average = t)
            
        return metric_results
           
               
                

########################################################################################################################          
 
"""
Function to parse arguments from command line
Input:
    argv -> command line arguments
Output:
    inputfile -> log file generated by AD (custom format)

"""

def parseArgs(argv):
   groundtruth = ''
   evaluable = ''
      
   try:
      opts, args = getopt.getopt(argv,"hg:e:",["gfile=", "efile="])
   except getopt.GetoptError:
      print 'AREvaluator.py -g <groundtruth> -e <evaluable>'
      sys.exit(2)
   for opt, arg in opts:
      if opt == '-h':
         print 'AREvaluator.py -g <groundtruth> -e <evaluable>'
         sys.exit()
      elif opt in ("-g", "--gfile"):
         groundtruth = arg
      elif opt in ("-e", "--efile"):
         evaluable = arg
      
         
   return groundtruth, evaluable
  
"""
Main function
"""
def main(argv):
    # call the argument parser 
   [groundtruth, evaluable] = parseArgs(argv[1:])
   print 'Provided arguments:'       
   print groundtruth, evaluable
   
   evaluator = AREvaluator(groundtruth, evaluable)
   print evaluator.groundtruth.head(10)
   print '-------------------------------------------'
   print evaluator.evaluable.head(10)
   evaluator.evaluate1()
   evaluator.cm.plot()
   
   
   
if __name__ == "__main__":
   main(sys.argv)
   