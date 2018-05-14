import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


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
      plt.plot([el, el], [-0.5, spectrogram.shape[-1] - 0.5], color='red', linewidth=1, linestyle="--", alpha=0.8)


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
      plt.plot([el, el], [0.5, spec.shape[-1] - 0.5], color='red', linewidth=1, linestyle="--", alpha=0.8)
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

