# -*- coding: utf-8 -*-
"""Xception.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1lrO2095lHJCiT6hJXHWCrD0NW30suJHO
"""

import tensorflow as tf
import sys
import os
import numpy as np
import pandas as pd
import seaborn as sns
import itertools
import sklearn
from tensorflow import keras
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.xception import preprocess_input, decode_predictions
from tensorflow.keras import layers
from tensorflow.keras.preprocessing.image import ImageDataGenerator

from google.colab import drive
drive.mount('/content/drive')

datagen = ImageDataGenerator(validation_split=0.2)

train_ds = datagen.flow_from_directory(
    '/content/drive/MyDrive/Thesis Works/Lung cancer dataset/Train',
    target_size=(224, 224),
    batch_size=16,
    color_mode="rgb",
    subset="training",
    seed=50,
    class_mode="binary",
    shuffle=True)

val_ds = datagen.flow_from_directory(
    '/content/drive/MyDrive/Thesis Works/Lung cancer dataset/Test',
    target_size=(224, 224),
    batch_size=16,
    color_mode="rgb",
    subset="validation",
    seed=50,
    class_mode="binary",
    shuffle=True)

test_generator = ImageDataGenerator()
test_data_generator = test_generator.flow_from_directory(
    '/content/drive/MyDrive/Thesis Works/Lung cancer dataset/Test',   
    target_size=(224, 224),
    batch_size=16,
    color_mode="rgb",
    shuffle=False)

import matplotlib.pyplot as plt

data_augmentation = keras.Sequential(
    [layers.experimental.preprocessing.RandomFlip("horizontal_and_vertical"), 
     layers.experimental.preprocessing.RandomRotation(0.2),])

# build the model
base_model = keras.applications.Xception(
    include_top=False,  # Do not include the ImageNet classifier at the top.
    weights="imagenet",   # Load weights pre-trained on ImageNet.
    input_tensor=None,
    input_shape=(224, 224, 3),
    pooling=max,
    classes=2,
    classifier_activation="softmax")

# Freeze the base_model
base_model.trainable = False

# Create new model on top
inputs = keras.Input(shape=(224, 224, 3))
x = data_augmentation(inputs)  # Apply random data augmentation (GPU method)

# Pre-trained Imagenet weights requires that input be normalized
# from (0, 255) to a range (-1., +1.), the normalization layer
# does the following, outputs = (inputs - mean) / sqrt(var)
norm_layer = keras.layers.experimental.preprocessing.Normalization()
mean = np.array([127.5] * 3)
var = mean ** 2
# Scale inputs to [-1, +1]
x = norm_layer(x)
#norm_layer.set_weights([mean, var])

# The base model contains batchnorm layers. We want to keep them in inference mode
# when we unfreeze the base model for fine-tuning, so we make sure that the
# base_model is running in inference mode here.
x = base_model(x, training=False)
x = keras.layers.GlobalMaxPooling2D()(x)
x = keras.layers.Dropout(0.2)(x)  # Regularize with dropout
outputs = keras.layers.Dense(1)(x)
model = keras.Model(inputs, outputs)

model.summary()

#train the top layer
model.compile(
    optimizer=keras.optimizers.Adam(),
    loss=keras.losses.BinaryCrossentropy(from_logits=True),
    metrics=[keras.metrics.BinaryAccuracy()])

history =model.fit_generator(train_ds, 
    steps_per_epoch=train_ds.samples / train_ds.batch_size, 
    epochs=30, 
    validation_data=val_ds,
    validation_steps=val_ds.samples / val_ds.batch_size,
    verbose=1)

# Fine tuning
base_model.trainable = True
model.summary()

model.compile(
    optimizer=keras.optimizers.Adam(1e-5),  # Low learning rate
    loss=keras.losses.BinaryCrossentropy(from_logits=True),
    metrics=[keras.metrics.BinaryAccuracy()],
)

# fit_generator() is normally useful if you cannot fit your data into your main → ResourceExhaustedError:
history = model.fit_generator(train_ds, 
    steps_per_epoch=train_ds.samples / train_ds.batch_size, 
    epochs=20 , 
    validation_data=val_ds,
    validation_steps=val_ds.samples / val_ds.batch_size,
    verbose=1)

#Evaluate model
validation_steps = 20

loss0,accuracy0 = model.evaluate(val_ds, steps = validation_steps)

print("loss: {:.2f}".format(loss0))
print("accuracy: {:.2f}".format(accuracy0))

#learning curves
# accuracy
plt.plot(history.history['binary_accuracy'])
plt.plot(history.history['val_binary_accuracy'])
plt.title('model accuracy')
plt.ylabel('accuracy')
plt.xlabel('epoch')
plt.legend(['train', 'validation'], loc='upper left')
plt.show()

#loss
plt.plot(history.history['loss'])
plt.plot(history.history['val_loss'])
plt.title('model loss')
plt.ylabel('loss')
plt.xlabel('epoch')
plt.legend(['train', 'validation'], loc='upper left')
plt.show()

#confusion matrix
#1.Predict classes
from sklearn.metrics._plot.confusion_matrix import ConfusionMatrixDisplay
from tensorflow.keras.preprocessing.image import ImageDataGenerator

test_steps_per_epoch = np.math.ceil(test_data_generator.samples / test_data_generator.batch_size)

predictions = model.predict_generator(test_data_generator, steps=test_steps_per_epoch)

# Get most likely class
predicted_classes = [1 * (x[0]>=0.5) for x in predictions]

# 2.Get ground-truth classes and class-labels
true_classes = test_data_generator.classes
class_labels = list(test_data_generator.class_indices.keys()) 

# 3. Use scikit-learn to get statistics
from sklearn.metrics import confusion_matrix,classification_report

print(class_labels)

print(confusion_matrix(test_data_generator.classes, predicted_classes))
cm=confusion_matrix(test_data_generator.classes, predicted_classes)

cm_disp= ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=['Affected', 'Normal'])

cm_disp.plot()