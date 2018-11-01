import os
import time
import tensorflow as tf
from utils import *
from imresize import *
from metrics import *
import matplotlib.pyplot as plt
import pprint
import math
import numpy as np
import sys
import glob
from tqdm import tqdm


class Com(object):
# ==========================================================
# class initializer
# ==========================================================
    def __init__(self, sess, args):
        self.sess = sess
        self.args = args
        self.model()
        self.init_model()

# ==========================================================
# preprocessing
# ==========================================================
    def preprocess(self):
        pass



# ==========================================================
# build model
# ==========================================================
    def model(self):
        with tf.variable_scope("com") as scope:
            self.train_phase = tf.placeholder(tf.bool, name="trainphase_com")
            shared_inner_model_template = tf.make_template('shared_model', self.inner_model)

            self.images = tf.placeholder(tf.float32,[None, self.args.patch_size, self.args.patch_size, self.args.c_dim], name='images')
            self.labels = tf.placeholder(tf.float32, [None, self.args.patch_size, self.args.patch_size, self.args.c_dim],name='labels')
            self.pred = shared_inner_model_template(self.images)

            self.image_test = tf.placeholder(tf.float32,[1,None,None, self.args.c_dim]  ,name='images_test')
            self.label_test = tf.placeholder(tf.float32, [1, None,None, self.args.c_dim],name='labels_test')
            self.pred_test = shared_inner_model_template(self.image_test)



# ===========================================================
# inner model
# ===========================================================
    def inner_model(self,inputs):
    #----------------------------------------------------------------------------------
    # input layer
    #------------------------------------------------------------------------------------------
        with tf.variable_scope("input") as scope:
            conv_w = tf.get_variable("conv_w", [3, 3, self.args.c_dim, 64], initializer=tf.contrib.layers.xavier_initializer())
            conv_b = tf.get_variable("conv_b", [64], initializer=tf.constant_initializer(0))
            layer = tf.nn.bias_add(tf.nn.conv2d(inputs, conv_w, strides=[1, 1, 1, 1], padding='SAME'), conv_b)
            layer = tf.nn.relu(layer)


        with tf.variable_scope("down") as scope:
            conv_w = tf.get_variable("conv_w", [3, 3, 64, 64], initializer=tf.contrib.layers.xavier_initializer())
            conv_b = tf.get_variable("conv_b", [64], initializer=tf.constant_initializer(0))
            layer = tf.nn.bias_add(tf.nn.conv2d(layer, conv_w, strides=[1, self.args.scale, self.args.scale, 1], padding='SAME'), conv_b)
            #layer = tf.contrib.layers.batch_norm(layer, is_training=self.train_phase)
            layer = tf.nn.relu(layer)



        with tf.variable_scope("out") as scope:
            conv_w = tf.get_variable("conv_w", [3, 3, 64, self.args.c_dim], initializer=tf.contrib.layers.xavier_initializer())
            conv_b = tf.get_variable("conv_b", [self.args.c_dim], initializer=tf.constant_initializer(0))
            layer = tf.nn.bias_add(tf.nn.conv2d(layer, conv_w, strides=[1, 1, 1, 1], padding='SAME'), conv_b)

        pred = layer
        return pred
    #----------------------------------------------------------------------------------------


# ============================================================
    # other tensors related with training
# ============================================================
    def init_model(self):
        vars_com = tf.get_collection(tf.GraphKeys.GLOBAL_VARIABLES, scope="com")
        self.sess.run(tf.variables_initializer(var_list=vars_com))
        self.saver = tf.train.Saver(var_list=vars_com, max_to_keep=0)
        if self.cpkt_load(self.args.checkpoint_dir_com, self.args.cpkt_itr_com):
            print(" [*] Load SUCCESS")
        else:
            print(" [!] Load failed...")

    def cpkt_save(self, checkpoint_dir, step):
        model_name = "checks.model"
        model_dir = "checks"
        checkpoint_dir = os.path.join(checkpoint_dir, self.args.type, model_dir)

        if not os.path.exists(checkpoint_dir):
            os.makedirs(checkpoint_dir)

        self.saver.save(self.sess,
                        os.path.join(checkpoint_dir, model_name),
                        global_step=step)

    def cpkt_load(self, checkpoint_dir, checkpoint_itr):
        print(" [*] Reading checkpoints...")
        model_dir = "checks"
        checkpoint_dir = os.path.join(checkpoint_dir, self.args.type, model_dir)

        if checkpoint_itr == 0:
            print("train from scratch")
            return True

        elif checkpoint_dir == -1:
            ckpt = tf.train.latest_checkpoint(checkpoint_dir)

        else:
            ckpt = os.path.join(checkpoint_dir, "checks.model-" + str(checkpoint_itr))

        print(ckpt)
        if ckpt:
            self.saver.restore(self.sess, ckpt)
            return True
        else:
            return False



# ==========================================================
# functions
# ==========================================================
    def inference(self, input_img):
        if (np.max(input_img) > 10): input_img = (input_img / 255).astype(np.float32)

        size = input_img.shape
        if (len(input_img.shape) == 3):
            infer_image_input = input_img[:, :, 0].reshape(1, size[0], size[1], 1)
        else:
            infer_image_input = input_img.reshape(1, size[0], size[1], 1)

        sr_img = self.sess.run(self.pred_test, feed_dict={self.image_test: infer_image_input})
        # sr_img = np.expand_dims(sr_img,axis=-1)


        input_img = imresize(input_img,1/self.args.scale)

        if (len(input_img.shape) == 3):
            input_img[:, :, 0] = sr_img[0, :, :, 0]
        else:
            input_img = sr_img[0]

        return input_img