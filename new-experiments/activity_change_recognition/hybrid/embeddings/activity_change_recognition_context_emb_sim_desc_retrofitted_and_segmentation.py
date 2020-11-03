import json
import sys
import numpy as np
import pandas as pd
import argparse

from sklearn import preprocessing
from pylab import *
from math import sqrt

from utils.activity_change_preprocessing import *

from embeddings_utils.create_embedding_matrix import *
from embeddings_utils.perform_activity_change_desc import *
from context_similarity.calculate_context_similarity import *

import multiprocessing
from gensim.models import Word2Vec

def main(argv):
    np.set_printoptions(threshold=sys.maxsize)
    np. set_printoptions(suppress=True)
    # parse args
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_dir",
                        type=str,
                        default="../../kasteren_house_a",
                        nargs="?",
                        help="Dataset dir")
    parser.add_argument("--dataset_file",
                        type=str,
                        default="kasterenA_groundtruth.csv",
                        nargs="?",
                        help="Dataset file")
    parser.add_argument("--results_dir",
                        type=str,
                        default='results/kasteren_house_a',
                        nargs="?",
                        help="Dir for results")
    parser.add_argument("--results_folder",
                        type=str,
                        default='word2vec_context_desc_retrofitted_activities',
                        nargs="?",
                        help="Folder for results")
    parser.add_argument("--graph_dir",
                        type=str,
                        default='results/kasteren_house_a',
                        nargs="?",
                        help="Graph dir")
    parser.add_argument("--graph_folder",
                        type=str,
                        default='word2vec_context',
                        nargs="?",
                        help="Graph folder")
    parser.add_argument("--graph",
                        type=str,
                        default='activities',
                        nargs="?",
                        help="Graph used")
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
    parser.add_argument("--min_dist",
                        type=float,
                        default=0.1,
                        nargs="?",
                        help="Min distance to perform desc strategy CPD")
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
    # change point detection
    window_size = args.window_size
    context_window_size = args.context_window_size
    iterations = args.iterations
    embedding_size = args.embedding_size
    # check actions input shape
    print("Input action shape: " + str(X.shape))
    models = []
    # create embedding matrix from word2vec retrofitted vector file
    vector_file = args.graph_dir + "/" + args.graph_folder + "/" + "context_window_" + str(context_window_size) + "_window_" + str(window_size) + "_iterations_" + str(iterations) + "_embedding_size_" + str(embedding_size) + "/" + "train" + "/word2vec_models/" + "0_execution_retrofitted_" + str(args.graph) + ".vector"
    embedding_action_matrix, unknown_actions = create_action_embedding_matrix_from_file(tokenizer_action, vector_file, embedding_size)
    # calculate context similarities using word2vec embeddings
    similarities = []
    similarities.append(1.0)
    for i in range(1, len(X)):
        context_similarity = calculate_context_similarity(X, embedding_action_matrix, i, context_window_size)
        similarities.append(context_similarity)
    # prepare change detection with offset using different min_dist values
    min_dist = args.min_dist
    change_points = get_change_points_desc(similarities, min_dist)
    label = 'Activity'
    label_number = 0
    labels = []
    for i in range(0, len(X)):
        if change_points[i] == 0:
            labels.append(label + ' ' + str(label_number))
        else:
            label_number += 1
            labels.append(label + ' ' + str(label_number))
    df_dataset['Predicted_Segment'] = labels
    # write to file
    RESULTS_DIR = "/" + args.results_dir + "/" + args.results_folder + "/context_window_" + str(context_window_size) + "_window_" + str(window_size) + "_iterations_" + str(iterations) + "_embedding_size_" + str(embedding_size) + "/" + args.train_or_test + "/"
    df_dataset.to_csv(RESULTS_DIR + "segmentation.csv")
    # mark experiment end
    print('... Experiment finished ...')
    print('Results saved to: ' + RESULTS_DIR)
    print('... ... ... ... ... ... ...')

if __name__ == "__main__":
    main(sys.argv)