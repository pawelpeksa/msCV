from hyperopt import fmin, tpe, space_eval, hp

from sklearn.tree import DecisionTreeClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn import svm
from sklearn.model_selection import cross_val_score

import numpy as np

from Configuration import Configuration
from MethodsConfiguration import *


class Optimizer():
    def __init__(self, x_train, y_train, x_test, y_test, n_folds=10):
        self._x_train = x_train
        self._y_train = y_train

        self._x_test = x_test
        self._y_test = y_test

        self._n_folds = n_folds

        self._iteration = 1

    def optimize(self):
        result = fmin(fn=self._objective, space=self._hyper_space, algo=tpe.suggest,
                    max_evals=Configuration.HYPEROPT_EVALS_PER_SEARCH)
        return space_eval(self._hyper_space, result)

    def _objective(self, classifier):
        self._iteration += 1

    	if self._n_folds == 1:
            classifier.fit(self._x_train, self._y_train)
    	    score = classifier.score(self._x_test, self._y_test)
    	else:
    	    x = np.concatenate((self._x_test, self._x_train), axis=0)
    	    y = np.concatenate((self._y_test, self._y_train), axis=0)

            score_arr = cross_val_score(classifier, self._x_test, self._y_test, cv=self._n_folds, n_jobs=-1)
            score = np.mean(score_arr)

        return -score

    def _print_progress(self, classifier_str):
        print classifier_str, 'optimizer progress:', str(
            (self._iteration / float(Configuration.HYPEROPT_EVALS_PER_SEARCH)) * 100), '%'

    def _init_hyper_space(self):
        raise NotImplementedError('Should have implemented this')


DEPTH_KEY = 'depth'
ESTIMATORS_KEY = 'estimators'

class RandomForest_Optimizer(Optimizer):
    def __init__(self, x_train, y_train, x_test, y_test, n_folds=10,
                 depth_begin=1, depth_end=15,
                 estimators_begin=2, estimators_end=15):
        Optimizer.__init__(self, x_train, y_train, x_test, y_test, n_folds)

        self._depth_begin = depth_begin
        self._depth_end = depth_end
        self._estimators_begin = estimators_begin
        self._estimators_end = estimators_end

        self.random_forest = RandomForest()

        self._init_hyper_space()

    def _init_hyper_space(self):
        self._hyper_space = [hp.choice(DEPTH_KEY, np.arange(self._depth_begin, self._depth_end + 1)),
                             hp.choice(ESTIMATORS_KEY, np.arange(self._depth_begin, self._depth_end + 1))]

    def _objective(self, args):
        Optimizer._print_progress(self, 'random forest')
        depth, estimators = args

        assert depth > 0 and estimators > 0, 'depth <= 0 or estimators <= 0'

        forest = RandomForestClassifier(max_depth=depth, n_estimators=estimators)
        score = Optimizer._objective(self, forest)

        return score

    def optimize(self):
        result = Optimizer.optimize(self)

        self.random_forest.max_depth = result[0]
        self.random_forest.n_estimators = result[1]


C_KEY = 'C'

class SVM_Optimizer(Optimizer):
    def __init__(self, x_train, y_train, x_test, y_test, n_folds=10, C_begin=2**-5, C_end=2):
        Optimizer.__init__(self, x_train, y_train, x_test, y_test, n_folds)

        self._C_begin = C_begin
        self._C_end = C_end

        self.svm = SVM()

        self._init_hyper_space()


    def _init_hyper_space(self):
        self._hyper_space = hp.uniform(C_KEY, self._C_begin, self._C_end)

    def _objective(self, args):
        Optimizer._print_progress(self, 'svm')
        C = args

        assert C > 0, 'C <= 0'

        SVM = svm.SVC(kernel='linear', C=C)
        score = Optimizer._objective(self, SVM)

        return score

    def optimize(self):
        result = Optimizer.optimize(self)

        self.svm.C = result


DEPTH_KEY = 'depth'

class DecisionTree_Optimizer(Optimizer):
    def __init__(self, x_train, y_train, x_test, y_test, n_folds=10,
                 depth_begin=1, depth_end=15):
        Optimizer.__init__(self, x_train, y_train, x_test, y_test, n_folds)

        self._depth_begin = depth_begin
        self._depth_end = depth_end

        self.decision_tree = DecisionTree()

        self._init_hyper_space()

    def _init_hyper_space(self):
        self._hyper_space = hp.choice(DEPTH_KEY, np.arange(self._depth_begin, self._depth_end + 1))

    def _objective(self, args):
        Optimizer._print_progress(self, 'decision tree')
        depth = args

        assert depth > 0, 'depth <= 0'

        tree = DecisionTreeClassifier(max_depth=depth)
        score = Optimizer._objective(self, tree)

        return score

    def optimize(self):
        result = Optimizer.optimize(self)

        self.decision_tree.max_depth = result


SOLVER_KEY = 'solver'
ALPHA_KEY = 'alpha'
HIDDEN_NEURONS_KEY = 'hidden_neurons'

class ANN_Optimizer(Optimizer):
    def __init__(self, x_train, y_train, x_test, y_test, n_folds=10,
                 hid_neurons_begin=1, hid_neurons_end=10,
                 alpha_begin=1, alpha_end=10):
        Optimizer.__init__(self, x_train, y_train, x_test, y_test, n_folds)

        self._hid_neurons_begin = hid_neurons_begin
        self._hid_neurons_end = hid_neurons_end

        self._alpha_begin = alpha_begin
        self._alpha_end = alpha_end

        self.ann = ANN()

        self._solvers = ['lbfgs', 'sgd', 'adam']
        self._init_hyper_space()

    def _init_hyper_space(self):
        self._hyper_space = [
            hp.choice(HIDDEN_NEURONS_KEY, np.arange(self._hid_neurons_begin, self._hid_neurons_end + 1)),
            hp.choice(SOLVER_KEY, self._solvers),
            hp.uniform(ALPHA_KEY, self._alpha_begin, self._alpha_end)]

    def _objective(self, args):
        Optimizer._print_progress(self, 'ann')
        hidden_neurons, solver, alpha = args

        assert hidden_neurons > 0 , 'hidden_neurons <= 0'

        ann = MLPClassifier(solver=solver,
                            max_iter=Configuration.ANN_OPIMIZER_MAX_ITERATIONS,
                            alpha=alpha,
                            hidden_layer_sizes=(hidden_neurons,),
                            random_state=1,
                            learning_rate='adaptive')

        score = Optimizer._objective(self, ann)

        return score

    def optimize(self):
        result = Optimizer.optimize(self)

        self.ann.hidden_neurons = result[0]
        self.ann.solver = result[1]
        self.ann.alpha = result[2]
