#feature transformation
#class module 4.3
""" 

Feature transformation is a part of Feature Engineering,
a crucial step in the machine learning pipeline. It involves 
modifying the representation of features to make them more 
suitable for modeling.

Note: subject may not correlate to the class, I'm currently at 4.3

Here: Normalization (Min Max Scaler)


Resources
https://medium.com/@datasciencejourney100_83560/feature-transformation-bb3db66fa4fe

Note: 
log normalization is suitable when the data contains only positive values, as the logarithm is not defined for zero or negative values.


"""


from sklearn.preprocessing import MinMaxScaler
import numpy as np

# Assuming X is your feature matrix
X = np.array([[1, 2, 3],
              [4, 5, 6],
              [700, 800, 900]])

scaler = MinMaxScaler()
X_minmax = scaler.fit_transform(X)

print("Original Data:\n", X)
print("\nMin-Max Scaled Data:\n", X_minmax)
