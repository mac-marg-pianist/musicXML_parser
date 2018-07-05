
""" Recurrent Neural Network.
A Recurrent Neural Network (LSTM) implementation example using TensorFlow library.
This example is using the MNIST database of handwritten digits (http://yann.lecun.com/exdb/mnist/)
Links:
    [Long Short Term Memory](http://deeplearning.cs.cmu.edu/pdfs/Hochreiter97_lstm.pdf)
    [MNIST Dataset](http://yann.lecun.com/exdb/mnist/).
Author: Aymeric Damien
Project: https://github.com/aymericdamien/TensorFlow-Examples/
"""

from __future__ import print_function
import tensorflow as tf
import tensorflow.contrib.rnn as rnn
import tensorflow.contrib.keras as keras
import numpy as np
import math
import matplotlib.pyplot as plt
import matplotlib
import pickle

# Training Parameters
learning_rate = 0.00001
# training_steps = 10000
training_epochs = 70
batch_size = 6
display_step = 200
training_ratio = 0.9

# Network Parameters
num_input = 2
timesteps = 50 # timesteps
num_hidden = 128 # hidden layer num of features
num_output = 3 # loudness, articulation, ioi
input_length = 11


with open("pairs_data.dat", "rb") as f:
    dataset = pickle.load(f)

def make_windowed_data(features,input_length):
    feature_array = np.asarray(features)
    windowed_feature = []
    left_margin = (input_length-1)/2
    right_margin = (input_length - 1) / 2 +1

    # print(left_margin, right_margin)
    for i in range(feature_array.shape[0]):
        if i >= left_margin and i+right_margin<feature_array.shape[0]:
            temp_windowed = feature_array[i-left_margin:i+right_margin,:]
        elif i <left_margin:
            padding = left_margin-i
            temp_windowed = feature_array[:i+right_margin,:]
            temp_windowed = np.pad(temp_windowed, ((padding,0), (0,0)) , 'constant')
        else:
            padding = (i+right_margin) - feature_array.shape[0]
            temp_windowed = feature_array[i-left_margin:feature_array.shape[0],:]
            temp_windowed = np.pad(temp_windowed, ((0, padding), (0,0)) , 'constant')
        if not temp_windowed.shape[0] == input_length:
            print(temp_windowed.shape)
        windowed_feature.append(temp_windowed)
    windowed_feature = np.asarray(windowed_feature)
    # print(windowed_feature.shape)
    return windowed_feature

complete_xy = []
for piece in dataset:
    for perform in piece:
        train_x = []
        train_y = []
        for feature in perform:
            if not feature['IOI_ratio'] == None:
                # train_x.append( [ feature['pitch_interval'],feature['duration_ratio'],feature['beat_position']  ] )
                train_x.append( [ feature['pitch_interval'],feature['duration_ratio'] ] )
                train_y.append([ feature['IOI_ratio'], feature['articulation'] ,feature['loudness'] ])
        # windowed_train_x = make_windowed_data(train_x, input_length )
        complete_xy.append([train_x, train_y])

def get_mean_and_sd(performances, target_data, target_dimension):
    sum = 0
    squared_sum = 0
    count = 0
    for perf in performances:
        samples = perf[target_data]
        for sample in samples:
            value = sample[target_dimension]
            sum += value
            squared_sum += value*value
            count += 1
    data_mean = sum / count
    data_std = (squared_sum/count - data_mean **2) ** 0.5
    return data_mean, data_std

complete_xy_normalized = []
means = [[],[]]
stds = [[],[]]
for i1 in (0, 1):
    for i2 in range(3):
        if i1==0 and i2==2:
            continue
        mean_value, std_value = get_mean_and_sd(complete_xy, i1, i2)
        means[i1].append(mean_value)
        stds[i1].append(std_value)

for performance in complete_xy:
    complete_xy_normalized.append([])
    for index1 in (0, 1):
        complete_xy_normalized[-1].append([])
        for sample in performance[index1]:
            new_sample = []
            for index2 in (0, 1, 2):
                if index1 == 0 and index2 == 2:
                    continue
                new_sample.append((sample[index2]-means[index1][index2])/stds[index1][index2])
            complete_xy_normalized[-1][index1].append(new_sample)

complete_xy_orig = complete_xy
print(len(complete_xy), len(complete_xy))
complete_xy = complete_xy_normalized




# complete_xy = np.asarray(complete_xy)
# perform_num = complete_xy.shape[0]
perform_num = len(complete_xy)
train_perf_num = int(perform_num * training_ratio)
train_xy = complete_xy[:train_perf_num]
test_xy = complete_xy[train_perf_num:]



# tf Graph input
X = tf.placeholder("float", [None, timesteps, num_input])
Y = tf.placeholder("float", [None, timesteps, num_output])

# Define weights
weights = {
    'out': tf.Variable(tf.random_normal([num_hidden, num_output]))
}
biases = {
    'out': tf.Variable(tf.random_normal([num_output]))
}

def frame_wise_projection(input, feature_dim, out_dim):
    with tf.variable_scope('projection') as scope:
        kernel = tf.get_variable('weight', shape=[1, feature_dim, 1, out_dim],
                                 initializer=tf.contrib.layers.xavier_initializer())
        conv = tf.nn.conv2d(input, kernel, [1, 1, 1, 1], padding='VALID')
        biases = tf.get_variable('biases', [out_dim], initializer=tf.constant_initializer(0.0))
        output = tf.nn.bias_add(conv, biases)
        output = tf.squeeze(output, axis=2, name='output')
    return output

def keras_frame_wise_projection(input, feature_dim, out_dim):
    # input.shape [?, time_step, hidden_size]
    fc_input = tf.reshape(input, (-1, input.shape[2]))
    fc = tf.contrib.layers.fully_connected(fc_input, out_dim)
    fc_reshaped = tf.reshape(fc, (-1, input.shape[1], out_dim))
    return fc_reshaped

def RNN(x, weights, biases):

    # Prepare data shape to match `rnn` function requirements
    # Current data input shape: (batch_size, timesteps, n_input)
    # Required shape: 'timesteps' tensors list of shape (batch_size, n_input)

    # Unstack to get a list of 'timesteps' tensors of shape (batch_size, n_input)
    x = tf.unstack(x, timesteps, 1)

    # Define a lstm cell with tensorflow
    lstm_cell = rnn.BasicLSTMCell(num_hidden, forget_bias=1.0, name='lstm1')
    lstm_cell2 = rnn.BasicLSTMCell(num_hidden, forget_bias=1.0, activation=tf.nn.sigmoid)

    # lstm_cell = rnn.BasicLSTMCell(num_hidden, forget_bias=1.0)

    # Get lstm cell output
    outputs, states = rnn.static_rnn(lstm_cell, x, dtype=tf.float32)
    # outputs = tf.transpose(outputs, [1, 0, 2])
    # print(outputs.shape)
    print(outputs)
    with tf.variable_scope('secondlayer') as scope:
        outputs, states = rnn.static_rnn(lstm_cell2, outputs, dtype=tf.float32)
    outputs = tf.transpose(outputs, [1, 0, 2])
    outputs = tf.stack(outputs)
    # num_layers = 2
    # rnn_tuple_state = tuple(
    #     [tf.nn.rnn_cell.LSTMStateTuple(state_per_layer_list[idx][0], state_per_layer_list[idx][1])
    #      for idx in range(num_layers)]
    # )
    # cell = tf.nn.rnn_cell.LSTMCell(state_size, state_is_tuple=True)
    # cell = tf.nn.rnn_cell.MultiRNNCell([cell] * 3, state_is_tuple=True)
    # outputs, states = tf.nn.rnn(cell, x, initial_state=rnn_tuple_state)

    # Linear activation, using rnn inner loop last output
    # output_list =  [tf.matmul(output, weights['out']) + biases['out'] for output in outputs]
    # hypothesis = tf.concat(output_list, 1)
    print(outputs.shape)
    expand = tf.expand_dims(outputs, axis =-1)
    print(expand.shape)
    hypothesis = frame_wise_projection(expand, num_hidden , num_output)
    # hypothesis2 = keras_frame_wise_projection(outputs, num_hidden, num_output)
    print(hypothesis.shape)
    # hypothesis =tf.matmul(outputs, weights['out']) + biases['out']
    cost = tf.reduce_mean(tf.square(hypothesis - Y))
    optimizer= tf.train.AdamOptimizer(learning_rate=learning_rate).minimize(cost)

    return hypothesis, cost, optimizer, tf.train.Saver(max_to_keep=1)
def FCN(x):
    # reg = 0.0001
    reg = 0.00001
    X = tf.reshape(x, [-1, timesteps, num_input])
    Fc1 = tf.contrib.layers.fully_connected(inputs=X, num_outputs=128, activation_fn=tf.nn.selu,
                                            weights_regularizer=tf.contrib.layers.l2_regularizer(scale=reg))
    Fc2 = tf.contrib.layers.fully_connected(inputs=Fc1, num_outputs=128, activation_fn=tf.nn.selu,
                                            weights_regularizer=tf.contrib.layers.l2_regularizer(scale=reg))
    Fc3 = tf.contrib.layers.fully_connected(inputs=Fc2, num_outputs=128, activation_fn=tf.nn.selu,
                                            weights_regularizer=tf.contrib.layers.l2_regularizer(scale=reg))
    Fc4 = tf.contrib.layers.fully_connected(inputs=Fc3, num_outputs=128, activation_fn=tf.nn.selu,
                                            weights_regularizer=tf.contrib.layers.l2_regularizer(scale=reg))
    # max_pool = tf.nn.max_pool(tf.expand_dims(tf.expand_dims(Fc5,1),-1),[1,1,32,1],[1,1,1,1], 'VALID')
    # Fc6 = tf.contrib.layers.fully_connected(inputs=Fc5, num_outputs=16, activation_fn=tf.nn.selu, weights_regularizer = tf.contrib.layers.l2_regularizer(scale=reg))
    # Fc7 = tf.contrib.layers.fully_connected(inputs=Fc6, num_outputs=16, activation_fn=tf.nn.selu, weights_regularizer = tf.contrib.layers.l2_regularizer(scale=reg))

    hypothesis = tf.contrib.layers.fully_connected(inputs=Fc4, num_outputs=3, activation_fn=tf.nn.relu)
    cost = tf.reduce_mean(tf.square(hypothesis - Y))
    optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate).minimize(cost)

    return hypothesis, cost, optimizer, tf.train.Saver(max_to_keep=1)


hypothesis, cost, optimizer,saver = RNN(X, weights, biases)

# logits = RNN(X, weights, biases)
# print(logits.shape)
# prediction = tf.nn.softmax(logits)
# # result = logits
#
# # Define loss and optimizer
# # loss_op = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(
#     # logits=logits, labels=Y))
# loss_op = tf.reduce_mean(tf.square(logits - Y))
# optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate)
# train_op = optimizer.minimize(loss_op)
#
# # Evaluate model (with test logits, for dropout to be disabled)
# correct_pred = tf.equal(tf.argmax(prediction, 1), tf.argmax(Y, 1))
# accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float32))

# Initialize the variables (i.e. assign their default value)
init = tf.global_variables_initializer()



# Start training
with tf.Session() as sess:

    # Run the initializer
    sess.run(init)

    for epoch in range(training_epochs):
        for xy_tuple in train_xy:
            train_x = np.asarray(xy_tuple[0])
            train_y = np.asarray(xy_tuple[1])
            data_size = train_x.shape[0]
            total_batch_num = int(math.ceil(data_size / (timesteps *batch_size )))
            # print(data_size, batch_size, total_batch_num)

            for step in range(total_batch_num-1):
                batch_x = train_x[step*batch_size*timesteps:(step+1)*batch_size*timesteps]
                batch_y = train_y[step*batch_size*timesteps:(step+1)*batch_size*timesteps]

                # print(batch_x.shape, batch_y.shape)
                batch_x = batch_x.reshape((batch_size, timesteps, num_input))
                batch_y = batch_y.reshape((batch_size, timesteps, num_output ))
                # Run optimization op (backprop)

                # batch_x = np.zeros((batch_x.shape)) + step % 5 - 2
                # batch_y = np.zeros((batch_y.shape)) + step % 5 - 2
                # for s in range(batch_size):
                #     batch_x[s,:,0] = list(range(timesteps))
                #     batch_y[s,:,0] = list(range(timesteps))
                #     batch_y[s, :, 0] = (batch_y[s,:,0])/50 - 1
                #     batch_x[s, :, 0] = batch_x[s,:,0]/100 -0.5

                # if step == 0:
                #     print(batch_x, batch_y)

                sess.run(optimizer, feed_dict={X: batch_x, Y: batch_y})

            # if step % display_step == 0 or step == 1:
                # Calculate batch loss and accuracy
        loss, x, y = sess.run([cost, X,Y], feed_dict={X: batch_x, Y: batch_y})
        # plt.plot(x[0,:,0])
        # plt.plot(y[:,0,0]+1)
        # plt.show()
        # break
        print("Epoch " + str(epoch) + ", Epoch Loss= " + \
            "{:.4f}".format(loss))

    print("Optimization Finished!")


    # test
    perform = test_xy[0]
    test_x = np.asarray(perform[0])
    test_x = test_x[:(test_x.shape[0]//timesteps) * timesteps]
    test_x = test_x.reshape((-1, timesteps, num_input))
    print(test_x.shape)
    test_y = np.asarray(perform[1])
    # test_y = test_y.reshape((timesteps,batch_size,  num_output ))
    # prediction = sess.run(hypothesis, feed_dict={X: test_x})
    prediction = sess.run(hypothesis, feed_dict={X: test_x})
    prediction = prediction.reshape((-1, num_output))
    print(prediction.shape)

    # Calculate accuracy for 128 mnist test images
    # test_len = 128
    # test_data = mnist.test.images[:test_len].reshape((-1, timesteps, num_input))
    # test_label = mnist.test.labels[:test_len]
    # print("Testing Accuracy:", \
    #     sess.run(accuracy, feed_dict={X: test_data, Y: test_label}))


# print(test_y[:,0])


ground_truth_IOI = test_y[:,0]
prediction_IOI = prediction[:,0]
matplotlib.use('Agg')
plt.plot(ground_truth_IOI)
plt.hold(True)
plt.plot(prediction_IOI)
plt.show()

