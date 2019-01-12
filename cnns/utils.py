"""
Name: Ciaran Cooney
Date: 12/01/2019
Description: Functions required for data processing and training of 
CNNs on imagined speech EEG data.
"""

import pickle
import os
import numpy as np 
import pandas as pd

def load_subject_eeg(subject_id, vowels):
    """ 
    returns eeg data corresponding to words and vowels 
    given a subject identifier.
    Parameters:
      subject_id: subject identifier, str()
      vowels: bool, if True: include vowel data in returned.
      
    Output:
      data and labels. Either for words only or for both vowels and words
    """

    data_folder = 'data_folder\\imagined_speech/S{}/post_ica/'.format(subject_id)
    words_file = 'raw_array_ica.pickle'
    vowels_file = 'raw_array_vowels_ica.pickle'
    
    with open(data_folder + words_file, 'rb') as f:
        file = pickle.load(f)
      
    w_data = file['raw_array'][:][0]
    w_labels = file['labels']
    if vowels == False:
        return w_data, w_labels

    elif vowels:
        try:
            with open(data_folder + vowels_file, 'rb') as f:
                file = pickle.load(f)
        except:
            with open(data_folder1 + vowels_file, 'rb') as f:
                file = pickle.load(f)
        v_data = file['raw_array'][:][0]
        v_labels = file['labels']
    return w_data, v_data, w_labels, v_labels


def eeg_to_3d(data, epoch_size, n_events, n_chan):

"""
function to return a 3D EEG data format from a 2D input.
Parameters:
  data: 2D np.array of EEG
  epoch_size: number of samples per trial, int
  n_events: number of trials, int
  n_chan: number of channels, int
  
Output:
  np.array of shape n_events * n_chans * n_samples
"""
    idx, a, x = ([] for i in range(3))
    [idx.append(i) for i in range(0,data.shape[1],epoch_size)]
    
    for j in data:
        [a.append([j[idx[k]:idx[k]+epoch_size]]) for k in range(len(idx))]
        
    for i in range(n_events):
        x.append([a[i],a[i+n_events],a[i+n_events*2],a[i+n_events*3],a[i+n_events*4],a[i+n_events*5]])
    
    return np.reshape(np.array(x),(n_events,n_chan,epoch_size))
    
def balanced_subsample(features, targets, random_state=12):
    """
    function for balancing datasets by randomly-sampling data
    according to length of smallest class set.
    """
    from sklearn.utils import resample
    unique, counts = np.unique(targets, return_counts=True)
    unique_classes = dict(zip(unique, counts))
    mnm = len(targets)
    for i in unique_classes:
        if unique_classes[i] < mnm:
            mnm = unique_classes[i]

    X_list, y_list = [],[]
    for unique in np.unique(targets):
        idx = np.where(targets == unique)
        X = features[idx]
        y = targets[idx]
        
        X1, y1 = resample(X,y,n_samples=mnm, random_state=random_state)
        X_list.append(X1)
        y_list.append(y1)
    
    balanced_X = X_list[0]
    balanced_y = y_list[0]
    
    for i in range(1, len(X_list)):
        balanced_X = np.concatenate((balanced_X, X_list[i]))
        balanced_y = np.concatenate((balanced_y, y_list[i]))

    return balanced_X, balanced_y
    
def format_data(data_type, subject_id, epoch):
    """
    Returns data into format required for inputting to the CNNs.

    Parameters:
        data_type: str()
        subject_id: str()
        epoch: length of single trials, int
    """

    if data_type == 'words':
        data, labels = load_subject_eeg(subject_id, vowels=False)
        n_chan = len(data)
        data = eeg_to_3d(data, epoch, int(data.shape[1] / epoch), n_chan).astype(np.float32)
        labels = labels.astype(np.int64)
        labels[:] = [x - 6 for x in labels] # zero-index the labels
    elif data_type == 'vowels':
        _, data, _, labels = load_subject_eeg(subject_id, vowels=True)
        n_chan = len(data)
        data = eeg_to_3d(data, epoch, int(data.shape[1] / epoch), n_chan).astype(np.float32)
        labels = labels.astype(np.int64)
        labels[:] = [x - 1 for x in labels]
    elif data_type == 'all_classes':
        w_data, v_data, w_labels, v_labels = load_subject_eeg(subject_id, vowels=True)
        n_chan = len(w_data)
        words = eeg_to_3d(w_data, epoch, int(w_data.shape[1] / epoch), n_chan).astype(np.float32)
        vowels = eeg_to_3d(v_data, epoch, int(v_data.shape[1] / epoch), n_chan).astype(np.float32)
        data = np.concatenate((words, vowels), axis=0)
        labels = np.concatenate((w_labels, v_labels)).astype(np.int64)
        labels[:] = [x - 1 for x in labels]

    return data, labels

def current_loss(model_loss):
    """
    Returns the minimum validation loss from the 
    trained model
    """
    losses_list = []
    [losses_list.append(x) for x in model_loss]
    return np.min(np.array(losses_list))
    

def predict(model, X_test, batch_size, iterator, threshold_for_binary_case=None):
    """
    Load torch model and make predictions on new data.
    Parameters:
      model: torch.model object
      X_test: test dataset, np.array
      batch_size: int
      iterator: iterator method to use, e.g. balanced_batch_size_iterator
      threshold_for_binary_case: None
      
    Output:
      numpy array of predicted labels
    """
    all_preds = []
    with th.no_grad():
        for b_X, _ in iterator.get_batches(SignalAndTarget(X_test, X_test), False):
            b_X_var = np_to_var(b_X)
            all_preds.append(var_to_np(model(b_X_var)))

        pred_labels = compute_pred_labels_from_trial_preds(
                    all_preds, threshold_for_binary_case)
    return pred_labels
