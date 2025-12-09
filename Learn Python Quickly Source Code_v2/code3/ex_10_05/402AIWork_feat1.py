#feature transformation
#4.3
""" 

Feature transformation is a part of Feature Engineering,
a crucial step in the machine learning pipeline. It involves 
modifying the representation of features to make them more 
suitable for modeling.

Note: subject may not correlate to the class, I'm currently at 4.3

Here: Log normalization


Resources
https://medium.com/@datasciencejourney100_83560/feature-transformation-bb3db66fa4fe

Note: 
log normalization is suitable when the data contains only positive values, as the logarithm is not defined for zero or negative values.


"""

import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

# Sample data with right-skewed distribution
data = np.array([1, 10, 100, 1000, 10000])

# Set up the figure
plt.figure(figsize=(8, 5))

# KDE plot for log-normalized data
sns.kdeplot(data, color='green', fill=True, label='Unnormalized Data')


# Log normalize the data
log_normalized_data = np.log(data)

# Set up the figure
plt.figure(figsize=(8, 5))

# KDE plot for log-normalized data
sns.kdeplot(log_normalized_data, color='green', fill=True, label='Log-normalized Data')

# Add labels and title
plt.xlabel('Log-normalized Values')
plt.ylabel('Probability Density')
plt.title('Kernel Density Estimation (KDE) Plot')

# Add a legend
plt.legend()

# Show the plot
plt.show()