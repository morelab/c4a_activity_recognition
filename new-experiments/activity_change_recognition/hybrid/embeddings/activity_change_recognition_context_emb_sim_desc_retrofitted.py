import json
import sys
import numpy as np
import pandas as pd
import argparse

from sklearn import preprocessing
from pylab import *
from math import sqrt

from utils.activity_change_preprocessing import *
from utils.activity_change_save_results import *
from utils.activity_change_evaluation import *

from embeddings_utils.create_embedding_matrix import *
from context_similarity.calculate_context_similarity import *

import multiprocessing
from gensim.models import Word2Vec

# Kasteren dataset DIR
DIR = '../../kasteren_house_a/'
# Kasteren dataset file
DATASET_CSV = DIR + 'base_kasteren_reduced'
# List of unique actions in the dataset
UNIQUE_ACTIONS = DIR + 'unique_actions.json'
# Context information for the actions in the dataset
CONTEXT_OF_ACTIONS = DIR + 'context_model.json'

def main(argv):
    np.set_printoptions(threshold=sys.maxsize)
    np. set_printoptions(suppress=True)
    # parse args
    parser = argparse.ArgumentParser()
    parser.add_argument("--results_dir",
                        type=str,
                        default='results',
                        nargs="?",
                        help="Dir for results")
    parser.add_argument("--results_folder",
                        type=str,
                        default='word2vec_context_desc_retrofitted_location',
                        nargs="?",
                        help="Folder for results")
    parser.add_argument("--vector_file",
                        type=str,
                        default='0_execution_location_retrofitted.vector',
                        nargs="?",
                        help="Vector file with retrofitted action vectors")
    parser.add_argument("--train_or_test",
                        type=str,
                        default='train',
                        nargs="?",
                        help="Specify train or test data")
    parser.add_argument("--embedding_size",
                        type=int,
                        default=50,
                        nargs="?",
                        help="Embedding size for word2vec algorithm")
    parser.add_argument("--window_size",
                        type=int,
                        default=1,
                        nargs="?",
                        help="Window size for word2vec algorithm")
    parser.add_argument("--context_window_size",
                        type=int,
                        default=2,
                        nargs="?",
                        help="Context window size for CPD algorithm")
    parser.add_argument("--iterations",
                        type=int,
                        default=5,
                        nargs="?",
                        help="Iterations for word2vec algorithm")
    parser.add_argument("--exe",
                        type=int,
                        default=30,
                        nargs="?",
                        help="Number of executions")
    args = parser.parse_args()
    print('Loading dataset...')
    sys.stdout.flush()
    # dataset of actions and activities
    DATASET = DATASET_CSV + "_" + args.train_or_test + ".csv"
    df_dataset = pd.read_csv(DATASET, parse_dates=[[0, 1]], header=None, index_col=0, sep=' ')
    df_dataset.columns = ['sensor', 'action', 'event', 'activity']
    df_dataset.index.names = ["timestamp"]
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
    # change point detection
    window_size = args.window_size
    context_window_size = args.context_window_size
    iterations = args.iterations
    exe = args.exe
    embedding_size = args.embedding_size
    vector_file = args.vector_file
    RESULTS_DIR = "/" + args.results_dir + "/" + args.results_folder + "/context_window_" + str(context_window_size) + "_window_" + str(window_size) + "_iterations_" + str(iterations) + "_embedding_size_" + str(embedding_size) + "/" + args.train_or_test + "/"
    # create dirs for saving results
    create_dirs(RESULTS_DIR, word2vec=True)
    # check actions input shape
    print("Input action shape: " + str(X.shape))
    # repeat exe iterations
    results_1 = np.zeros((4,10,30))
    results_5 = np.zeros((4,10,30))
    results_10 = np.zeros((4,10,30))
    detection_delays = np.zeros((10,30))
    models = []
    for e in range(0, exe):
        # create embedding matrix from word2vec retrofitted vector file
        embedding_action_matrix, unknown_actions = create_action_embedding_matrix_from_file(tokenizer_action, vector_file, embedding_size)
        # calculate context similarities using word2vec embeddings
        similarities = []
        similarities.append(1.0)
        for i in range(1, len(X)):
            context_similarity = calculate_context_similarity(X, embedding_action_matrix, i, context_window_size)
            similarities.append(context_similarity)
        # prepare change detection with offset using different min_dist values
        counter_min_dist = 0
        min_dists = [0.0, 0.001, 0.01, 0.1]
        for min_dist in min_dists:
            cf_matrix_1 = get_conf_matrix_with_offset_strategy_desc(similarities, y, timestamps, min_dist, 1)
            cf_matrix_5 = get_conf_matrix_with_offset_strategy_desc(similarities, y, timestamps, min_dist, 5)
            cf_matrix_10 = get_conf_matrix_with_offset_strategy_desc(similarities, y, timestamps, min_dist, 10)
            # TPR, TNR, FPR, G-MEAN for exact change point detection
            TN, FP, FN, TP = cf_matrix_1.ravel()
            TPR = TP/(TP+FN)
            TNR = TN/(TN+FP)
            FPR = FP/(FP+TN)
            G_MEAN = sqrt(TPR * TNR)
            results_1[0][counter_min_dist][e] = TPR
            results_1[1][counter_min_dist][e] = TNR
            results_1[2][counter_min_dist][e] = FPR
            results_1[3][counter_min_dist][e] = G_MEAN
            # TPR, TNR, FPR, G-MEAN for 5 second offset change point detection
            TN, FP, FN, TP = cf_matrix_5.ravel()
            TPR = TP/(TP+FN)
            TNR = TN/(TN+FP)
            FPR = FP/(FP+TN)
            G_MEAN = sqrt(TPR * TNR)
            results_5[0][counter_min_dist][e] = TPR
            results_5[1][counter_min_dist][e] = TNR
            results_5[2][counter_min_dist][e] = FPR
            results_5[3][counter_min_dist][e] = G_MEAN
            # TPR, TNR, FPR, G-MEAN for 10 second offset change point detection
            TN, FP, FN, TP = cf_matrix_10.ravel()
            TPR = TP/(TP+FN)
            TNR = TN/(TN+FP)
            FPR = FP/(FP+TN)
            G_MEAN = sqrt(TPR * TNR)
            results_10[0][counter_min_dist][e] = TPR
            results_10[1][counter_min_dist][e] = TNR
            results_10[2][counter_min_dist][e] = FPR
            results_10[3][counter_min_dist][e] = G_MEAN
            # detection delay
            detection_delay = get_detection_delay(similarities, y, timestamps, min_dist)
            detection_delays[counter_min_dist][e] = detection_delay
            counter_min_dist += 1
    # save population of results to file
    for min_dist_num in range(0, len(min_dists)):
        save_pop_results_to_file(RESULTS_DIR, results_1, 1, min_dist_num)
        save_pop_results_to_file(RESULTS_DIR, results_5, 5, min_dist_num)
        save_pop_results_to_file(RESULTS_DIR, results_10, 10, min_dist_num)
        np.savetxt(RESULTS_DIR + 'detection_delays/' + str(min_dist_num) + '_detection_delay' + '.csv', detection_delays[min_dist_num])
    # save trained models
    model_num = 0
    for model in models:
        model.save(RESULTS_DIR + 'word2vec_models/' + str(model_num) + '_execution.model')
        model_num += 1

if __name__ == "__main__":
    main(sys.argv)