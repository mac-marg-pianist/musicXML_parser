from __future__ import division

import numpy as np
import math
from numpy.lib.stride_tricks import as_strided
import os
import json
import pickle
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import ntpath
import fnmatch


def array2stack(array, length, hop=None):
    if hop is None:
        hop = length
    assert (array.shape[0]-length) % hop == 0, 'length of array is not fit. l={:d}, length={:d}, hop={:d}'\
        .format(array.shape[0], length, hop)
    strides = array.strides
    stack = as_strided(array, ((array.shape[0] - length)//hop + 1, length, array.shape[1]),
                       (strides[0]*hop, strides[0], strides[1]))
    return stack


def overlap_stack2array(stack):
    # TODO: what if hop != stack.shape[1]//2 ?
    hop = stack.shape[1] // 2
    length = (stack.shape[0] + 1) * hop
    array = np.zeros((length, stack.shape[2]))
    array[:hop//2, :] = stack[0, :hop//2,:]
    for n in xrange(stack.shape[0]):
        array[n*hop + hop//2: n*hop + 3*hop//2, :] = stack[n, hop//2: 3*hop//2, :]
    array[(stack.shape[0]-1)*hop + 3*hop//2:, :] = stack[stack.shape[0]-1, 3*hop//2:, :]

    return array


def onset2delayed(onset, delay_len=10):
    rolled_onset = np.zeros(onset.shape)
    for k in range(delay_len):
        temp = np.roll(onset, k, axis=0)
        temp[0, :] = 0
        weight = math.sqrt((delay_len - k) / float(delay_len))
        rolled_onset += temp * weight
    rolled_onset[rolled_onset > 1] = 1
    return rolled_onset


def save_config(config,):
    if not os.path.exists(config.save_dir):
        os.makedirs(config.save_dir)
    param_path = os.path.join(config.save_dir, "params.json")
    with open(param_path, 'w') as fp:
        json.dump(config.__dict__, fp, indent=4, sort_keys=True)


def record_as_text(config, text):
    if not os.path.exists(config.save_dir):
        os.makedirs(config.save_dir)
    record_txt = config.save_dir + '/' + 'summary.txt'
    f = open(record_txt, 'a')
    f.write(text)
    f.close()


def my_imshow(array, interpolation='nearest', origin='bottom', aspect='auto', cmap='gray', **kwargs):
    plt.imshow(array, interpolation=interpolation, origin=origin, aspect=aspect, cmap=cmap, **kwargs)


def plot_piano_roll(piano_roll, plot_range=None, segment_len=None):
    if not plot_range:
        plot_range = [0, piano_roll.shape[0]]
    my_imshow(piano_roll[plot_range[0]: plot_range[1]].T, vmin=0, vmax=1, cmap=plt.get_cmap('gray_r'))
    x_ticks_sec = range(plot_range[0] // 100, plot_range[1] // 100)
    plt.xticks([el * 100 for el in x_ticks_sec], x_ticks_sec)
    octaves = range(piano_roll.shape[-1] // 12)
    plt.yticks(octaves, [str(el + 21) for el in octaves])
    plt.colorbar(ticks=[0, 1], pad=0.01, aspect=10)
    if segment_len:
        edges = range(segment_len * plot_range[0] // segment_len, segment_len * plot_range[1] // segment_len)
        for el in edges:
            plt.plot([el, el], [-0.5, piano_roll.shape[-1] - 0.5], color='red', linewidth=1, linestyle="--", alpha=0.8)


def plot_spectrogram(spectrogram, plot_range=None, segment_len=100):
    if not plot_range:
        plot_range = [0, spectrogram.shape[0]]
    my_imshow(spectrogram[plot_range[0]: plot_range[1]].T, cmap=plt.get_cmap('gray_r'))
    x_ticks_sec = range(plot_range[0] // 100, plot_range[1] // 100)
    plt.xticks([el * 100 for el in x_ticks_sec], x_ticks_sec)
    plt.colorbar(pad=0.01, aspect=10)
    if segment_len:
        edges = range(segment_len * plot_range[0] // segment_len, segment_len * plot_range[1] // segment_len)
        for el in edges:
            plt.plot([el, el], [-0.5, spectrogram.shape[-1] -0.5], color='red', linewidth=1, linestyle="--", alpha=0.8)


def plot_train_pair(spec, pred, label, seg_len=None, title='', savename=None, max_len=1000):
    plot_range = [0, np.min([spec.shape[0], max_len])]
    plt.figure(figsize=(20, 10))
    plt.subplot(311)
    plt.title(title)
    my_imshow(spec[plot_range[0]: plot_range[1]].T, cmap=plt.get_cmap('gray_r'))
    x_ticks_sec = range(plot_range[0] // 100, plot_range[1] // 100)
    plt.xticks([el * 100 for el in x_ticks_sec], x_ticks_sec)
    plt.colorbar(pad=0.01, aspect=10)
    if seg_len:
        edges = range(plot_range[0], plot_range[1], seg_len)
        for el in edges:
            plt.plot([el, el], [0.5, spec.shape[-1] -0.5], color='red', linewidth=1, linestyle="--", alpha=0.8)
    plt.ylim([0, spec.shape[-1]])
    plt.subplot(312)

    my_imshow(pred[plot_range[0]: plot_range[1]].T, vmin=0, vmax=1, cmap=plt.get_cmap('gray_r'))
    x_ticks_sec = range(plot_range[0] // 100, plot_range[1] // 100)
    plt.xticks([el * 100 for el in x_ticks_sec], x_ticks_sec)
    plt.colorbar(ticks=[0, 1], pad=0.01, aspect=10)
    if seg_len:
        edges = range(plot_range[0], plot_range[1], seg_len)
        for el in edges:
            plt.plot([el, el], [0.5, pred.shape[-1] - 0.5], color='red', linewidth=1, linestyle="--", alpha=0.8)
    plt.ylim([0, pred.shape[-1]])
    plt.subplot(313)
    my_imshow(label[plot_range[0]: plot_range[1]].T, vmin=0, vmax=1, cmap=plt.get_cmap('gray_r'))
    x_ticks_sec = range(plot_range[0] // 100, plot_range[1] // 100)
    plt.xticks([el * 100 for el in x_ticks_sec], x_ticks_sec)
    plt.colorbar(ticks=[0, 1], pad=0.01, aspect=10)
    if seg_len:
        edges = range(plot_range[0], plot_range[1], seg_len)
        for el in edges:
            plt.plot([el, el], [0.5, label.shape[-1] - 0.5], color='red', linewidth=1, linestyle="--", alpha=0.8)
    plt.ylim([0, label.shape[-1]])
    if savename:
        plt.savefig(savename)
    plt.close()


def get_data_list(set_name, set_num=1):
    f = open('data_list/config{:d}_{}.txt'.format(set_num, set_name), 'rb')
    data_list = f.readlines()
    for n in xrange(len(data_list)):
        data_list[n] = data_list[n].replace('\n', '')
    f.close()
    data_list.sort()
    return data_list


def pad2d(feature, seg_len):
    if feature.shape[0] % seg_len != 0:
        pad_len = seg_len - feature.shape[0] % seg_len
        feature = np.pad(feature, ((0, pad_len), (0, 0)), 'constant')
    return feature


def normalize(feature, mean, std):
    return np.divide((feature - mean[None, :]), std[None, :], where=(std[None, :] != 0))


def maybe_make_dir(dir_name):
    if not os.path.isdir(dir_name):
        os.makedirs(dir_name)


def change_name_extension(file_name, new_ext):
    if new_ext[0] is not '.':
        new_ext = '.' + new_ext

    return os.path.splitext(file_name)[0] + new_ext


def split_path_from_path(file_path):
    head, tail = ntpath.split(file_path)
    return head, tail


def save_obj(obj, name):
    save_name = change_name_extension(name, '.pkl')
    with open(save_name, 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)


def load_obj(name):
    save_name = change_name_extension(name, '.pkl')
    with open(save_name, 'rb') as f:
        return pickle.load(f)


def find_files_in_subdirs(folder, regexp):
    matches = []
    for root, dirnames, filenames in os.walk(folder):
        for filename in fnmatch.filter(filenames, regexp):
            matches.append(os.path.join(root, filename))
    return matches