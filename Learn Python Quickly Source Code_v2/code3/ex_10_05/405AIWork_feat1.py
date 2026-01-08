""" 

Feature transformation is a part of Feature Engineering,
a crucial step in the machine learning pipeline. It involves 
modifying the representation of features to make them more 
suitable for modeling.

Note: subject may not correlate to the class, I'm currently at 4.3

Here: Standardization


Resources
https://medium.com/@datasciencejourney100_83560/feature-transformation-bb3db66fa4fe



"""

import numpy as np
from sklearn import svm
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# 1. Generate some dummy data (replace with your actual data)
X = np.array([
    [1, 0.5],    # Single clap, short interval (e.g., stop)
    [2, 0.2],    # Double clap, short interval (e.g., start)
    [2, 0.8],    # Double clap, longer interval (e.g., wait)
    [3, 0.3],    # Triple clap, short interval (e.g., reset)
    [1, 0.7],
    [2, 0.1],
    [3, 0.5]
])
y = np.array(["stop", "start", "wait", "reset", "stop", "start", "reset"])

# 2. Split data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

# 3. Create and train an SVM classifier
clf = svm.SVC(gamma=0.001, C=100)
clf.fit(X_train, y_train)

# 4. Make predictions
y_pred = clf.predict(X_test)

# 5. Evaluate the model
print(classification_report(y_test, y_pred))
