import json
import sys
import numpy as np
import pandas as pd
import argparse
import csv

from sklearn import preprocessing
from pylab import *
from math import sqrt

from utils.activity_change_preprocessing import *
from utils.activity_change_save_results import *
from utils.activity_change_evaluation import *

from change_point_detection_RuLSIF import *

def main(argv):
    np.set_printoptions(threshold=sys.maxsize)
    np. set_printoptions(suppress=True)
    # parse args
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_dir",
                        type=str,
                        default="../../../kasteren_house_a/reduced",
                        nargs="?",
                        help="Dataset dir")
    parser.add_argument("--dataset_file",
                        type=str,
                        default="base_kasteren_reduced.csv",
                        nargs="?",
                        help="Dataset file")
    parser.add_argument("--results_dir",
                        type=str,
                        default='results/kasteren_house_a/reduced',
                        nargs="?",
                        help="Dir for results")
    parser.add_argument("--results_folder",
                        type=str,
                        default='RuLSIF',
                        nargs="?",
                        help="Folder for results")
    parser.add_argument("--train_or_test",
                        type=str,
                        default='train',
                        nargs="?",
                        help="Specify train or test data")
    parser.add_argument("--n",
                        type=int,
                        default=2,
                        nargs="?",
                        help="Window size for n-real time algorithm")
    parser.add_argument("--k",
                        type=int,
                        default=30,
                        nargs="?",
                        help="Number of events to look when performing feature extraction")
    parser.add_argument("--alpha",
                        type=float,
                        default=0.01,
                        nargs="?",
                        help="RulSIF is equivalent to ulSIF when alpha=0.0")
    parser.add_argument("--exe",
                        type=int,
                        default=30,
                        nargs="?",
                        help="Number of executions")
    parser.add_argument("--plot",
                        type=bool,
                        default=False,
                        nargs="?",
                        help="Plot images")
    args = parser.parse_args()
    print('Loading dataset...')
    sys.stdout.flush()
    # dataset of actions and activities
    DATASET = args.dataset_dir + "/" + args.dataset_file.replace('.csv', '') + "_" + args.train_or_test + ".csv"
    df_dataset = pd.read_csv(DATASET, parse_dates=[[0, 1]], header=None, index_col=0, sep=' ')
    df_dataset.columns = ['sensor', 'action', 'event', 'activity']
    df_dataset.index.names = ["timestamp"]
    # list of unique actions in the dataset
    UNIQUE_ACTIONS = args.dataset_dir + "/" + 'unique_actions.json'
    # context information for the actions in the dataset
    CONTEXT_OF_ACTIONS = args.dataset_dir + "/" + 'context_model.json'
    # total actions and its names
    unique_actions = json.load(open(UNIQUE_ACTIONS, 'r'))
    total_actions = len(unique_actions)
    # context of actions
    context_of_actions = json.load(open(CONTEXT_OF_ACTIONS, 'r'))
    action_location = {}
    for key, values in context_of_actions['objects'].items():
        action_location[key] = values['location']
    # check action:location dict struct
    print(action_location)
    # check dataset struct
    print("Dataset")
    print(df_dataset)
    # prepare dataset
    X, timestamps, days, hours, seconds_past_midnight, y, tokenizer_action = prepare_x_y_activity_change(df_dataset)
    # transform action:location dict struct to action_index:location struct
    action_index = tokenizer_action.word_index
    action_index_location = {}
    for key, value in action_index.items():
        action_index_location[value] = action_location[key]
    # check action_index:location struct
    print(action_index_location)
    # check prepared dataset struct
    print("Actions")
    print(X)
    print("Activity change")
    print(y)
    # read offline generated feature vectors
    FEATURE_VECTORS_FILE = "/" + args.results_dir + "/" + "feature_extraction" + "/" + args.train_or_test + "/" + 'k_' + str(args.k) + '_feature_vectors.csv'
    with open(FEATURE_VECTORS_FILE) as f:
        reader = csv.reader(f)
        feature_vectors = list(reader)
        feature_vectors = np.array(feature_vectors)
        feature_vectors = feature_vectors.astype(np.float)
    # check feature vectors struct
    print("Feature vectors")
    print(feature_vectors)
    # change point detection
    n = args.n
    k = args.k
    alpha = args.alpha # equivalent to ulSIF when alpha=0.0
    exe = args.exe
    RESULTS_DIR = "/" + args.results_dir + "/" + args.results_folder + "/" + args.train_or_test + "/"
    # create dirs for saving results
    create_dirs(RESULTS_DIR, word2vec=False)
    print('Created dirs at: ' + RESULTS_DIR)
    # check actions input shape
    print("Input action shape: " + str(X.shape))
    # repeat exe iterations
    results_1 = np.zeros((4,10,exe))
    results_5 = np.zeros((4,10,exe))
    results_10 = np.zeros((4,10,exe))
    detection_delays = np.zeros((10,exe))
    for e in range(0, exe):
        # calculate scores using RulSIF
        scores_1 = change_detection(feature_vectors, n, alpha)
        scores_2 = change_detection(np.flip(feature_vectors, 0), n, alpha)
        scores_1 = np.array(scores_1)
        scores_2 = np.flip(np.array(scores_2), 0)
        scores_sum = np.sum(np.array([scores_1, scores_2]), axis=0)
        scores_sum = np.concatenate((np.zeros(2*n-2+k), scores_sum))
        min_max_scaler = preprocessing.MinMaxScaler()
        scores_sum_norm = min_max_scaler.fit_transform(scores_sum.reshape(-1, 1))
        # plot in pieces
        if args.plot:
            points = 50
            number_of_plots = int(ceil(len(y) / points))
            print("Number of plots: " + str(number_of_plots))
            for i in range(0, number_of_plots):
                offset = i * points
                y_sub = y[offset:offset+points]
                scores_sum_norm_sub = scores_sum_norm[offset:offset+points]
                if offset + points < len(scores_sum_norm):
                    t = list(range(offset, offset+points))
                else:
                    t = list(range(offset, len(scores_sum_norm)))
                fig, ax = plt.subplots()
                for j in range(0, len(y_sub)):
                    if y_sub[j] == 1:
                        ax.axvline(offset+j, 0, max(scores_sum_norm), c='k')
                ax.plot(t, scores_sum_norm_sub, color='r')
                ax.set(xlabel='x', ylabel='score')
                print("Saving plot with number: " + str(i))
                fig.savefig(RESULTS_DIR + "scores_and_cp_ts_" + str(i) + ".png")
        # prepare change detection with offset using different threshold values
        counter_threshold = 0
        for threshold in [x * 0.1 for x in range(0, 10)]:
            cf_matrix_1 = get_conf_matrix_with_offset_strategy(scores_sum_norm, y, timestamps, threshold, 1)
            cf_matrix_5 = get_conf_matrix_with_offset_strategy(scores_sum_norm, y, timestamps, threshold, 5)
            cf_matrix_10 = get_conf_matrix_with_offset_strategy(scores_sum_norm, y, timestamps, threshold, 10)
            # TPR, TNR, FPR, G-MEAN for exact change point detection
            TN, FP, FN, TP = cf_matrix_1.ravel()
            TPR = TP/(TP+FN)
            TNR = TN/(TN+FP)
            FPR = FP/(FP+TN)
            G_MEAN = sqrt(TPR * TNR)
            results_1[0][counter_threshold][e] = TPR
            results_1[1][counter_threshold][e] = TNR
            results_1[2][counter_threshold][e] = FPR
            results_1[3][counter_threshold][e] = G_MEAN
            # TPR, TNR, FPR, G-MEAN for 5 second offset change point detection
            TN, FP, FN, TP = cf_matrix_5.ravel()
            TPR = TP/(TP+FN)
            TNR = TN/(TN+FP)
            FPR = FP/(FP+TN)
            G_MEAN = sqrt(TPR * TNR)
            results_5[0][counter_threshold][e] = TPR
            results_5[1][counter_threshold][e] = TNR
            results_5[2][counter_threshold][e] = FPR
            results_5[3][counter_threshold][e] = G_MEAN
            # TPR, TNR, FPR, G-MEAN for 10 second offset change point detection
            TN, FP, FN, TP = cf_matrix_10.ravel()
            TPR = TP/(TP+FN)
            TNR = TN/(TN+FP)
            FPR = FP/(FP+TN)
            G_MEAN = sqrt(TPR * TNR)
            results_10[0][counter_threshold][e] = TPR
            results_10[1][counter_threshold][e] = TNR
            results_10[2][counter_threshold][e] = FPR
            results_10[3][counter_threshold][e] = G_MEAN
            # detection delay
            detection_delay = get_detection_delay(scores_sum_norm, y, timestamps, threshold)
            detection_delays[counter_threshold][e] = detection_delay
            counter_threshold += 1
    # save population of results to file
    for threshold_num in range(0, 10):
        save_pop_results_to_file(RESULTS_DIR, results_1, 1, threshold_num)
        save_pop_results_to_file(RESULTS_DIR, results_5, 5, threshold_num)
        save_pop_results_to_file(RESULTS_DIR, results_10, 10, threshold_num)
        np.savetxt(RESULTS_DIR + 'detection_delays/' + str(threshold_num) + '_detection_delay' + '.csv', detection_delays[threshold_num])
    # mark experiment end
    print('... Experiment finished ...')
    print('Results saved to: ' + RESULTS_DIR)
    print('... ... ... ... ... ... ...')

if __name__ == "__main__":
    main(sys.argv)