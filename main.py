from copy import deepcopy
import time
import threading
import numpy as np

from MethodsConfiguration import MethodsConfiguration
from Optimizer import *

from Configuration import Configuration

from sklearn import svm
from sklearn.neural_network import MLPClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier

from sklearn.model_selection import train_test_split
from sklearn.datasets import make_classification
from sklearn.utils import shuffle

TREE_KEY = 'tree'
FOREST_KEY = 'forest'
ANN_KEY = 'ann'
SVM_KEY = 'svm'


def get_seed():
    t = time.time() - int(time.time())
    t *= 1000000
    return int(t)


def main():
    print "cross validation example with artificial dataset"

    x_all, y_all = make_classification(n_samples=Configuration.N_SAMPLES, n_features=10, n_redundant=0)

    open_file_with_header(SVM_KEY)
    open_file_with_header(ANN_KEY)
    open_file_with_header(TREE_KEY)
    open_file_with_header(FOREST_KEY)

    for n_samples in Configuration.n_samples_arr:
        result_dict = dict()

        result_dict[SVM_KEY] = list(), list()
        result_dict[ANN_KEY] = list(), list()
        result_dict[TREE_KEY] = list(), list()
        result_dict[FOREST_KEY] = list(), list()

        for i in range(Configuration.RUNS_FOR_SAMPLE + 1):
            single_result_dict = optimize_and_score(x_all, y_all, n_samples) # score_ho, score_cv

            append_to_result_array(single_result_dict, result_dict, SVM_KEY)
            append_to_result_array(single_result_dict, result_dict, ANN_KEY)
            append_to_result_array(single_result_dict, result_dict, TREE_KEY)
            append_to_result_array(single_result_dict, result_dict, FOREST_KEY)

        append_result_to_file(SVM_KEY, n_samples, result_dict)
        append_result_to_file(ANN_KEY, n_samples, result_dict)
        append_result_to_file(TREE_KEY, n_samples, result_dict)
        append_result_to_file(FOREST_KEY, n_samples, result_dict)


def append_to_result_array(single_result_dict, result_dict, KEY):
    score_ho_arr, score_cv_arr = result_dict[KEY]
    score_ho, score_cv = single_result_dict[KEY]

    score_ho_arr.append(score_ho)
    score_cv_arr.append(score_cv)


def append_result_to_file(key, n_samples, result_dict):
    score_ho_arr, score_cv_arr = result_dict[key]
    with open('results/' + key + '.dat', 'a') as file:
        file.write(str(n_samples) + \
                   "\t" + str(np.mean(score_ho_arr)) + "\t" + str(np.std(score_ho_arr)) + \
                   "\t" + str(np.mean(score_cv_arr)) + "\t" + str(np.std(score_cv_arr)) + \
                   "\n")


def open_file_with_header(name):
    with open('results/' + name + '.dat', 'a') as file:
        file.write("#holdout_n \t #score_ho \t #score_ho_std \t #score_cv \t #score_cv_std \n")


def optimize_and_score(x_all, y_all, holdout_n):
    x_train, y_train, x_test, y_test, x_val, y_val = prepare_data(x_all, y_all, holdout_n)

    config_cv = determine_parameters_all(x_train, y_train, x_test, y_test, 10)
    config_ho = determine_parameters_all(x_train, y_train, x_test, y_test, 1)

    ho_score_dict = score_with_config(config_ho, x_train, y_train, x_test, y_test, x_val, y_val)
    cv_score_dict = score_with_config(config_cv, x_train, y_train, x_test, y_test, x_val, y_val)

    result_dict = dict()

    for ho_key, cv_key in zip(ho_score_dict, cv_score_dict):
        assert ho_key == cv_key
        result_dict[ho_key] = ho_score_dict[ho_key], cv_score_dict[ho_key]

    return result_dict


def prepare_data(x_all, y_all, holdout_n):
    x_holdout, x_without_holdout, y_holdout, y_without_holdout = train_test_split(x_all, y_all, train_size=holdout_n,
                                                                                  random_state=get_seed())


    shuffle(x_holdout, y_holdout, random_state=get_seed())
    x_train, x_test, y_train, y_test = train_test_split(x_holdout, y_holdout, test_size=0.4, random_state=get_seed())
    x_val, x_test, y_val, y_test  = train_test_split(x_test, y_test, test_size=0.5, random_state=get_seed())

    return x_train, y_train, x_test, y_test, x_val, y_val    


def score_with_config(config, x_train, y_train, x_test, y_test, x_val, y_val):
    SVM, ann, tree, forest = clfs_with_config(config)

    score_dict = dict()

    score_dict[SVM_KEY]    = score_model(x_train, y_train, x_test, y_test, x_val, y_val, SVM)
    score_dict[ANN_KEY]    = score_model(x_train, y_train, x_test, y_test, x_val, y_val, ann)
    score_dict[FOREST_KEY] = score_model(x_train, y_train, x_test, y_test, x_val, y_val, tree)
    score_dict[TREE_KEY]   = score_model(x_train, y_train, x_test, y_test, x_val, y_val, forest)

    return score_dict


def clfs_with_config(config):    
    SVM = svm.SVC(kernel='linear', C=config.svm.C)

    ann = MLPClassifier(solver=config.ann.solver,
                        max_iter=Configuration.ANN_MAX_ITERATIONS,
                        alpha=config.ann.alpha,
                        hidden_layer_sizes=(config.ann.hidden_neurons,),
                        learning_rate='adaptive')

    tree = DecisionTreeClassifier(max_depth=config.decision_tree.max_depth)

    forest = RandomForestClassifier(max_depth=config.random_forest.max_depth,
                                    n_estimators=config.random_forest.n_estimators)

    return SVM, ann, tree, forest


def determine_parameters_all(x_train, y_train, x_test, y_test, n_fold):
    print "determine parameters"
    config = MethodsConfiguration()

    print config.toDict()

    threads = list()

    svm_opt = SVM_Optimizer(x_train, y_train, x_test, y_test, n_fold)
    ann_opt = ANN_Optimizer(x_train, y_train, x_test, y_test, n_fold)
    tree_opt = DecisionTree_Optimizer(x_train, y_train, x_test, y_test, n_fold)
    forest_opt = RandomForest_Optimizer(x_train, y_train, x_test, y_test, n_fold)

    threads.append(threading.Thread(target=determine_parameters, args=(svm_opt,)))
    threads.append(threading.Thread(target=determine_parameters, args=(ann_opt,)))
    threads.append(threading.Thread(target=determine_parameters, args=(tree_opt,)))
    threads.append(threading.Thread(target=determine_parameters, args=(forest_opt,)))

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    config.svm = svm_opt.svm
    config.ann = ann_opt.ann
    config.decision_tree = tree_opt.decision_tree
    config.random_forest = forest_opt.random_forest

    print config.toDict()

    return config


def determine_parameters(optimizer):
    print 'determine parameters ', optimizer.__class__.__name__
    optimizer.optimize()


def score_model(x_train, y_train, x_test, y_test, x_val, y_val, classifier):
    x_train = np.concatenate((x_test, x_train), axis=0)
    y_train = np.concatenate((y_test, y_train), axis=0)

    classifier.fit(x_train, y_train)

    return classifier.score(x_val, y_val)
    

if __name__ == '__main__':
    main()
