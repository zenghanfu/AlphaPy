##############################################################
#
# Package  : AlphaPy
# Module   : data
# Version  : 1.0
# Copyright: Mark Conway
# Date     : July 29, 2015
#
##############################################################


#
# Imports
#

import _pickle as pickle
from datetime import datetime
from datetime import timedelta
from enum import Enum, unique
from frame import Frame
from frame import frame_name
from frame import read_frame
from globs import FEEDS
from globs import PSEP
from globs import SSEP
from globs import WILDCARD
import logging
import numpy as np
import pandas as pd
import pandas_datareader.data as web
from scipy import sparse
from sklearn.preprocessing import LabelEncoder
from unbalanced_dataset import BalanceCascade
from unbalanced_dataset import ClusterCentroids
from unbalanced_dataset import EasyEnsemble
from unbalanced_dataset import NearMiss
from unbalanced_dataset import NeighbourhoodCleaningRule
from unbalanced_dataset import OverSampler
from unbalanced_dataset import SMOTE
from unbalanced_dataset import SMOTEENN
from unbalanced_dataset import SMOTETomek
from unbalanced_dataset import TomekLinks
from unbalanced_dataset import UnderSampler



#
# Initialize logger
#

logger = logging.getLogger(__name__)


#
# Sampling Methods
#

@unique
class SamplingMethod(Enum):
    under_random = 1
    under_tomek = 2
    under_cluster = 3
    under_nearmiss = 4
    under_ncr = 5
    over_random = 6
    over_smote = 7
    over_smoteb = 8
    over_smotesv = 9
    overunder_smote_tomek = 10
    overunder_smote_enn = 11
    ensemble_easy = 12
    ensemble_bc = 13


#
# Function load_data
#

def load_data(directory, filename, extension, separator,
              features, target, return_labels=True):
    """
    Read in data from the given directory in a given format.
    """

    logger.info("Loading Data")

    # read in file
    df = read_frame(directory, filename, extension, separator)
    # assign target and drop it if necessary
    if target in df.columns:
        y = df[target].values
        y = LabelEncoder().fit_transform(y)
        logger.info("Dropping target %s from data frame", target)
        df = df.drop([target], axis=1)
    elif return_labels:
        logger.info("Target ", target, " not found")
        raise Exception('Target not found')
    # extract features
    if features == WILDCARD:
        X = df
    else:
        X = df[features]
    # labels are returned usually only for training data
    if return_labels:
        return X, y
    else:
        return X


#
# Function shuffle_data
#

def shuffle_data(model):
    """
    Shuffle training data
    """

    logger.info("Shuffling Training Data")

    # Extract model parameters.

    seed = model.specs['seed']
    shuffle = model.specs['shuffle']

    # Extract model data.

    X_train = model.X_train
    y_train = model.y_train

    # Shuffle data

    if shuffle:
        np.random.seed(seed)
        new_indices = np.random.permutation(y_train.size)
        model.X_train = X_train[new_indices]
        model.y_train = y_train[new_indices]

    return model


#
# Function sample_data
#

def sample_data(model):
    """
    For imbalanced classes, try oversampling or undersampling.
    """

    logger.info("Sampling Data")

    # Extract model parameters.

    sampling_method = model.specs['sampling_method']
    sampling_ratio = model.specs['sampling_ratio']
    target = model.specs['target']
    target_value = model.specs['target_value']
    verbosity = model.specs['verbosity']

    # Extract model data.

    X_train = model.X_train
    y_train = model.y_train

    # Calculate the sampling ratio if one is not provided.

    if sampling_ratio > 0.0:
        ratio = sampling_ratio
    else:
        uv, uc = np.unique(y_train, return_counts=True)
        ratio = (uc[not target_value] / uc[target_value]) - 1.0
    logger.info("Sampling Ratio for target %s [%r]: %f",
                target, target_value, ratio)

    # Choose the sampling method.

    if sampling_method == SamplingMethod.under_random:
        sampler = UnderSampler(verbose=verbosity)
    elif sampling_method == SamplingMethod.under_tomek:
        sampler = TomekLinks(verbose=verbosity)
    elif sampling_method == SamplingMethod.under_cluster:
        sampler = ClusterCentroids(verbose=verbosity)
    elif sampling_method == SamplingMethod.under_nearmiss:
        sampler = NearMiss(version=1, verbose=verbosity)
    elif sampling_method == SamplingMethod.under_ncr:
        sampler = NeighbourhoodCleaningRule(size_ngh=51, verbose=verbosity)
    elif sampling_method == SamplingMethod.over_random:
        sampler = OverSampler(ratio=ratio, verbose=verbosity)
    elif sampling_method == SamplingMethod.over_smote:
        sampler = SMOTE(ratio=ratio, verbose=verbosity, kind='regular')
    elif sampling_method == SamplingMethod.over_smoteb:
        sampler = SMOTE(ratio=ratio, verbose=verbosity, kind='borderline1')
    elif sampling_method == SamplingMethod.over_smotesv:
        sampler = SMOTE(ratio=ratio, verbose=verbosity, kind='svm')
    elif sampling_method == SamplingMethod.overunder_smote_tomek:
        sampler = SMOTETomek(ratio=ratio, verbose=verbosity)
    elif sampling_method == SamplingMethod.overunder_smote_enn:
        sampler = SMOTEENN(ratio=ratio, verbose=verbosity)
    elif sampling_method == SamplingMethod.ensemble_easy:
        sampler = EasyEnsemble(verbose=verbosity)
    elif sampling_method == SamplingMethod.ensemble_bc:
        sampler = BalanceCascade(verbose=verbosity)
    else:
        raise TypeError("Unknown Sampling Method")

    # Get the newly sampled features.

    X, y = sampler.fit_transform(X_train, y_train)

    logger.info("Original Samples : %d", X_train.shape[0])
    logger.info("New Samples      : %d", X.shape[0])

    # Store the new features in the model.

    model.X_train = X
    model.y_train = y

    return model


#
# Function get_remote_data
#

def get_remote_data(group,
                    start = datetime.now() - timedelta(365),
                    end = datetime.now()):
    gam = group.members
    feed = FEEDS[group.space.subject]
    for item in gam:
        logger.info("Getting %s data from %s to %s", item, start, end)
        df = web.DataReader(item, feed, start, end)
        df.reset_index(level=0, inplace=True)
        df = df.rename(columns = lambda x: x.lower().replace(' ',''))
        newf = Frame(item.lower(), group.space, df)
    return


#
# Function load_from_cache
#

def load_from_cache(filename, use_cache=True):
    """
    Attempt to load data from cache.
    """
    data = None
    read_mode = 'rb' if '.pkl' in filename else 'r'
    if use_cache:
        try:
            path = SSEP.join(["cache", filename])
            with open(path, read_mode) as f:
                data = pickle.load(f)
        except IOError:
            pass
    return data


#
# Function save_dataset
#

def save_dataset(filename, X, X_test, features=None, features_test=None):
    """
    Save the training and test sets augmented with the given features.
    """
    if features is not None:
        assert features.shape[1] == features_test.shape[1], "features mismatch"
        if sparse.issparse(X):
            features = sparse.lil_matrix(features)
            features_test = sparse.lil_matrix(features_test)
            X = sparse.hstack((X, features), 'csr')
            X_test = sparse.hstack((X_test, features_test), 'csr')
        else:
            X = np.hstack((X, features))
            X_test = np.hstack((X_test, features_test))
    # Save data to disk
    logger.info("> saving %s to disk", filename)
    pickle_file = PSEP.join([filename, "pkl"])
    pickle_path = SSEP.join(["cache", pickle_file])
    with open(pickle_path, 'wb') as f:
        pickle.dump((X, X_test), f, pickle.HIGHEST_PROTOCOL)