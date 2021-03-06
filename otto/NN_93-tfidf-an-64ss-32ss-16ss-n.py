import os
# import random
from timeit import default_timer as cpu_time

import pandas as pd
# from pandas import np

from sklearn import preprocessing
# from sklearn.decomposition import PCA
# from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
# from sklearn.linear_model import LogisticRegression
# import sklearn.preprocessing, sklearn.decomposition, sklearn.linear_model, sklearn.pipeline

# from sklearn.naive_bayes import GaussianNB
# from sklearn.linear_model import LogisticRegression
# from sklearn.ensemble import RandomForestClassifier
# from sklearn.svm import LinearSVC

from pybrain.tools.customxml.networkwriter import NetworkWriter

from pug.ann import util as ann
from pug.nlp import util as nlp
import util as otto

# from sklearn_pandas import DataFrameMapper
# from sklearn_pandas import cross_val_score

try:
    DATA_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data', '')
    SUBMISSIONS_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'submissions', '')
except:
    DATA_PATH = os.path.join('data', '')
    SUBMISSIONS_PATH = os.path.join('submissions', '')

df = pd.DataFrame.from_csv(DATA_PATH + "train.csv")
df_submission = pd.DataFrame.from_csv(DATA_PATH + "sample_submission.csv")

class_labels = list(df_submission.columns)
feature_labels = list(df.columns[:-1])  # 93 features, last col is target (true classification)
target_labels = list(df.columns[-1:])

assert(set(class_labels) == set(df[df.columns[-1]]))
assert(sorted(class_labels) == list(class_labels))

# transform counts into Term Frequency x Inverse Document Frequency (normalized term frequency) features
tfidf = TfidfTransformer()

print('Computing TFIDF (normalized feature frequency) from training set features...')
t0 = cpu_time()
df_freq = pd.DataFrame(tfidf.fit_transform(df[feature_labels].values).toarray(),
                       index=df.index, columns=feature_labels)
df_freq = otto.anscombe(df_freq)
df_freq = (df_freq - df_freq.mean()) / df_freq.std()
print("Computing the TFIDF took {} sec of the CPU's time.".format(cpu_time() - t0))

df_binarized = otto.binarize_text_categories(df, class_labels=class_labels, target_column='target')
for c in df_binarized.columns:
    df_freq[c] = df_binarized[c]

ds = ann.dataset_from_dataframe(df_freq, normalize=False, delays=[0], inputs=feature_labels, outputs=class_labels,
                                verbosity=1)
nn = ann.ann_from_ds(ds, N_hidden=[64, 32, 16], hidden_layer_type=['SteepSigmoid', 'SteepSigmoid', 'SteepSigmoid'],
                     output_layer_type='SteepSigmoid', verbosity=1)

trainer = ann.build_trainer(nn, ds=ds, verbosity=1)
trainer.trainUntilConvergence(maxEpochs=80, validationProportion=0.1, verbose=True)

NetworkWriter.writeToFile(trainer.module, nlp.make_timetag() + '.xml')

# columns = feature_labels + target_labels + ['Predicted--{}'.format(outp) for outp in target_labels]
predicted_prob = pd.np.clip(pd.DataFrame((pd.np.array(trainer.module.activate(i))
                                         for i in df_freq[feature_labels].values),
                                         columns=class_labels), 0, 1)

log_losses = [round(otto.log_loss(ds['target'], otto.normalize_dataframe(predicted_prob).values, method=m).sum(), 3)
              for m in 'ksfohe']
print('The log losses for the training set were {}'.format(log_losses))
# df = pd.DataFrame(table, columns=columns, index=df.index[max(delays):])


# ################################################################################
# ########## Predict labels for Validation/Test Set for Kaggle submission
# #

df_test = pd.DataFrame.from_csv(DATA_PATH + "test.csv")
test_ids = df_test.index.values

# transform counts into Term Frequency x Inverse Document Frequency (normalized term frequency) features
tfidf = TfidfTransformer()

print('Transforming the validation set features into a TFIDF frequency matrix...')
df_test = pd.DataFrame(tfidf.fit_transform(df_test[feature_labels].values).toarray(),
                       index=test_ids, columns=feature_labels)
print('Finished transforming the test data using the trained TFIDF.')

# columns = feature_labels + target_labels + ['Predicted--{}'.format(outp) for outp in target_labels]
df_test = pd.DataFrame((pd.np.array(trainer.module.activate(i)) for i in df_test.values),
                       index=test_ids, columns=class_labels)
otto.submit(df_test)
